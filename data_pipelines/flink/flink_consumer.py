import json
import os
import sys
import time
import logging
import http.server
import threading
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from backend.app.core.database import SessionLocal
from backend.app.models.models import Transaction, Platform, PaymentMethod

# Setup path to import backend classes dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure Flink logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [FLINK] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FlinkProcessor")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Aligned topic mappings according to SentinelX Enterprise standards
RAW_TRANSACTIONS_TOPIC = "sentinelx.raw.transactions"
CLEAN_TRANSACTIONS_TOPIC = "sentinelx.clean.transactions"

RAW_PAYMENTS_TOPIC = "sentinelx.raw.payments"
CLEAN_PAYMENTS_TOPIC = "sentinelx.clean.payments"

RAW_REVIEWS_TOPIC = "sentinelx.raw.reviews"
CLEAN_REVIEWS_TOPIC = "sentinelx.clean.reviews"

RAW_COMPLAINTS_TOPIC = "sentinelx.raw.complaints"
CLEAN_COMPLAINTS_TOPIC = "sentinelx.clean.complaints"

RAW_NEWS_TOPIC = "sentinelx.raw.news"
CLEAN_NEWS_TOPIC = "sentinelx.clean.news"

RAW_TOPICS = [
    RAW_TRANSACTIONS_TOPIC,
    RAW_PAYMENTS_TOPIC,
    RAW_REVIEWS_TOPIC,
    RAW_COMPLAINTS_TOPIC,
    RAW_NEWS_TOPIC
]

DLQ_TOPIC = "dead-letter-queue"

# Flink Prometheus Metrics Server
class FlinkMetricsServer:
    def __init__(self, port=8002):
        self.port = port
        self.processed = 0
        self.rejected = 0
        self.duplicates = 0
        self.late_events = 0
        self.window_flush_time = 0.0
        self.total_volume = 0.0

    def start(self):
        m_self = self
        class MetricsHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in ('/metrics', '/'):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.end_headers()
                    output = [
                        f"flink_processed_events_total {m_self.processed}",
                        f"flink_rejected_events_total {m_self.rejected}",
                        f"flink_duplicate_events_total {m_self.duplicates}",
                        f"flink_late_events_total {m_self.late_events}",
                        f"flink_window_processing_seconds {m_self.window_flush_time}",
                        f"flink_window_volume_total {m_self.total_volume}"
                    ]
                    self.wfile.write("\n".join(output).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()
            def log_message(self, format, *args):
                pass
        def run():
            try:
                server = http.server.HTTPServer(('0.0.0.0', m_self.port), MetricsHandler)
                server.serve_forever()
            except Exception as e:
                logger.error(f"Failed to start Flink metrics server: {e}")
        t = threading.Thread(target=run, daemon=True)
        t.start()
        logger.info(f"Flink Prometheus metrics server active at http://localhost:{self.port}/metrics")

metrics = FlinkMetricsServer()

class FlinkWindowProcessor:
    """
    Deduplicates, validates, and aggregates raw scrapy streams before publishing clean records to Kafka
    and synchronizing them to the SQL database.
    """
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.seen_refs = {}  # Cache {ref_number: timestamp}
        self.window_data = []
        self.last_window_flush = time.time()
        self.window_duration = 5.0  # 5-second tumbling window
        self.running = False
        self.producer = None
        self.consumer = None
        
        # Watermarks tracking variables
        self.max_event_time = None
        self.allowed_lateness = 10.0  # 10 seconds lateness allowed

    def connect(self):
        try:
            self.consumer = KafkaConsumer(
                *RAW_TOPICS,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id="flink-streaming-cleaners"
            )
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
            )
            logger.info(f"Connected to Kafka brokers. Subscribed to raw topics: {RAW_TOPICS}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect Flink consumer/producer to {self.bootstrap_servers}: {e}")
            return False

    def route_to_dlq(self, payload, error_message):
        metrics.rejected += 1
        dlq_payload = {
            "failed_payload": payload,
            "error": error_message,
            "failed_at": datetime.now().isoformat(),
            "origin": "flink-cleaning-stage"
        }
        try:
            if self.producer:
                self.producer.send(DLQ_TOPIC, value=dlq_payload)
                self.producer.flush()
                logger.warning(f"[DLQ] Routed item to DLQ: {error_message}")
        except Exception as e:
            logger.error(f"Failed to route message to DLQ: {e}")

    def clean_old_dedup_keys(self):
        now = time.time()
        expired = [k for k, v in self.seen_refs.items() if now - v > 3600]
        for k in expired:
            del self.seen_refs[k]

    def run(self):
        metrics.start()
        if not self.connect():
            logger.warning("Flink processor running in STANDBY mode (Kafka offline).")
            return

        self.running = True
        db = SessionLocal()
        logger.info("Flink processor loop active.")

        try:
            while self.running:
                messages = self.consumer.poll(timeout_ms=500)
                for tp, msg_list in messages.items():
                    for msg in msg_list:
                        payload = msg.value
                        tx = payload.get("data", {}) if "data" in payload else payload

                        # Check item class/type to route appropriately
                        ref = tx.get("ref_number")
                        platform_name = tx.get("platform_name")
                        amount = tx.get("amount")
                        timestamp_str = tx.get("timestamp") or tx.get("scrape_timestamp")
                        status = tx.get("status", "SUCCESS")
                        method = tx.get("method") or tx.get("method_name", "UPI")

                        # If it is reviews, complaints, news or payment method, bypass tumbling window aggregation
                        if tp.topic in [RAW_PAYMENTS_TOPIC, RAW_REVIEWS_TOPIC, RAW_COMPLAINTS_TOPIC, RAW_NEWS_TOPIC]:
                            if not platform_name:
                                self.route_to_dlq(payload, "Schema validation failed: missing platform_name")
                                continue
                            
                            # Map raw topic to clean topic
                            clean_topic = tp.topic.replace(".raw.", ".clean.")
                            try:
                                if self.producer:
                                    self.producer.send(clean_topic, value=payload)
                                    self.producer.flush()
                                logger.info(f"[STAGE: CLEAN] Topic: {clean_topic}, Platform: {platform_name}")
                            except Exception as e:
                                logger.error(f"Failed to publish cleaned event to {clean_topic}: {e}")
                            continue

                        # 1. Schema Validation for Transactions
                        if not ref or not platform_name or not timestamp_str or amount is None:
                            self.route_to_dlq(payload, "Schema validation failed: missing ref_number, platform_name, amount, or timestamp")
                            continue

                        try:
                            amount_val = float(amount)
                            if amount_val <= 0:
                                self.route_to_dlq(payload, "Validation failed: transaction amount must be positive")
                                continue
                        except (ValueError, TypeError):
                            self.route_to_dlq(payload, "Validation failed: amount must be numeric")
                            continue

                        # 2. Event Timestamp Handling & Watermarks
                        try:
                            event_time = datetime.fromisoformat(timestamp_str)
                            event_time_ts = event_time.timestamp()
                        except Exception:
                            self.route_to_dlq(payload, "Validation failed: invalid timestamp ISO format")
                            continue

                        if self.max_event_time is None or event_time_ts > self.max_event_time:
                            self.max_event_time = event_time_ts
                            
                        watermark = self.max_event_time - self.allowed_lateness
                        
                        if event_time_ts < watermark:
                            metrics.late_events += 1
                            self.route_to_dlq(payload, f"Late event arrived after watermark. Event Time: {timestamp_str}")
                            continue

                        # 3. Deduplication
                        now_sec = time.time()
                        if ref in self.seen_refs:
                            metrics.duplicates += 1
                            logger.info(f"Duplicate transaction reference {ref} filtered out.")
                            continue
                        self.seen_refs[ref] = now_sec

                        # Append to window
                        self.window_data.append({
                            "ref_number": ref,
                            "amount": amount_val,
                            "platform_name": platform_name,
                            "method": method,
                            "type": tx.get("type", "DEPOSIT"),
                            "status": status,
                            "timestamp": timestamp_str
                        })
                        metrics.processed += 1
                        self.clean_old_dedup_keys()

                # Tumbling window aggregation trigger for transactions
                now = time.time()
                if now - self.last_window_flush >= self.window_duration:
                    start_time = time.time()
                    self.flush_window_aggregations(db)
                    metrics.window_flush_time = time.time() - start_time
                    self.last_window_flush = now

        except KeyboardInterrupt:
            logger.info("Shutting down Flink processor...")
        finally:
            db.close()
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()

    def flush_window_aggregations(self, db):
        if not self.window_data:
            return

        total_tx = len(self.window_data)
        total_volume = sum(item["amount"] for item in self.window_data)
        metrics.total_volume += total_volume

        logger.info(f"[FLINK WINDOW FLUSH] Count: {total_tx}, Volume: {total_volume:.2f} INR")

        # Process clean events: Publish to clean topic & sync to database
        for item in self.window_data:
            logger.info(f"[STAGE: CLEAN] Topic: {CLEAN_TRANSACTIONS_TOPIC}, Platform: {item['platform_name']}, Ref: {item['ref_number']}, ProcessingTime: {datetime.now().isoformat()}, ValidationResult: Cleaned")
            
            # 1. Publish to cleaned transactions topic
            try:
                if self.producer:
                    self.producer.send(CLEAN_TRANSACTIONS_TOPIC, value=item)
                    self.producer.flush()
            except Exception as e:
                logger.error(f"Failed to publish cleaned event to {CLEAN_TRANSACTIONS_TOPIC}: {e}")

            # 2. Database Enrichment & Upsert (SQLite/Postgres)
            try:
                platform = db.query(Platform).filter(Platform.name == item["platform_name"]).first()
                if not platform:
                    platform = Platform(name=item["platform_name"], url=f"https://{item['platform_name'].lower().replace(' ', '')}.com")
                    db.add(platform)
                    db.commit()
                    db.refresh(platform)

                method = db.query(PaymentMethod).filter(PaymentMethod.name == item["method"]).first()
                if not method:
                    method = PaymentMethod(name=item["method"], type="UPI")
                    db.add(method)
                    db.commit()
                    db.refresh(method)

                existing = db.query(Transaction).filter(Transaction.ref_number == item["ref_number"]).first()
                if not existing:
                    tx = Transaction(
                        ref_number=item["ref_number"],
                        user_id="FLINK_USER",
                        platform_id=platform.id,
                        method_id=method.id,
                        amount=item["amount"],
                        type=item["type"],
                        status=item["status"]
                    )
                    db.add(tx)
                    db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"DB persist fallback failed: {e}")

        self.window_data.clear()

if __name__ == "__main__":
    processor = FlinkWindowProcessor()
    processor.run()
