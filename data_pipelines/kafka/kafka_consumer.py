import json
import os
import sys
import uuid
import time
import signal
import logging
import http.server
import threading
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("KafkaStreamConsumer")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
BRONZE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "bronze")
os.makedirs(BRONZE_DIR, exist_ok=True)

# Cleaned transactions and other raw topics
TOPICS = [
    "sentinelx.clean.transactions",
    "sentinelx.clean.payments",
    "sentinelx.clean.reviews",
    "sentinelx.clean.complaints",
    "sentinelx.clean.news"
]
DLQ_TOPIC = "dead-letter-queue"
RETRY_TOPIC = "stream-retry"

# Prometheus metrics collector helper class (no external dependencies required)
class PrometheusMetricsServer:
    def __init__(self, port=8001):
        self.port = port
        self.processed = {}
        self.rejected = {}
        self.dlq_count = 0
        self.lag = {}
        self.publish_rate = {}

    def start(self):
        metrics_self = self
        class MetricsHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in ('/metrics', '/'):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.end_headers()
                    output = []

                    # Processed Metrics
                    output.append("# HELP processed_events_total Total processed events")
                    output.append("# TYPE processed_events_total counter")
                    for topic, val in metrics_self.processed.items():
                        output.append(f'processed_events_total{{topic="{topic}"}} {val}')

                    # Rejected Metrics
                    output.append("# HELP rejected_events_total Total rejected events")
                    output.append("# TYPE rejected_events_total counter")
                    for key, val in metrics_self.rejected.items():
                        topic, reason = key
                        output.append(f'rejected_events_total{{topic="{topic}",reason="{reason}"}} {val}')

                    # DLQ Metrics
                    output.append("# HELP dlq_events_total Total events routed to Dead Letter Queue")
                    output.append("# TYPE dlq_events_total counter")
                    output.append(f"dlq_events_total {metrics_self.dlq_count}")

                    # lag Metrics
                    output.append("# HELP kafka_consumer_lag Kafka consumer lag per partition")
                    output.append("# TYPE kafka_consumer_lag gauge")
                    for key, val in metrics_self.lag.items():
                        topic, partition = key
                        output.append(f'kafka_consumer_lag{{topic="{topic}",partition="{partition}"}} {val}')

                    # Publish Rate Metrics
                    output.append("# HELP kafka_publish_total Total events published to Kafka")
                    output.append("# TYPE kafka_publish_total counter")
                    for topic, val in metrics_self.publish_rate.items():
                        output.append(f'kafka_publish_total{{topic="{topic}"}} {val}')

                    self.wfile.write("\n".join(output).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # suppress HTTP request prints

        def run_server():
            try:
                server = http.server.HTTPServer(('0.0.0.0', metrics_self.port), MetricsHandler)
                server.serve_forever()
            except Exception as e:
                logger.error(f"Failed to start prometheus http server: {e}")

        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        logger.info(f"Exposing Prometheus metrics at http://localhost:{self.port}/metrics")

metrics = PrometheusMetricsServer()

class LoggingRebalanceListener:
    def on_partitions_revoked(self, revoked):
        logger.info(f"Partitions revoked: {[str(tp) for tp in revoked]}")

    def on_partitions_assigned(self, assigned):
        logger.info(f"Partitions assigned: {[str(tp) for tp in assigned]}")

class KafkaStreamConsumer:
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.producer = None
        self.running = False
        self.metrics_started = False

    def connect_with_retry(self):
        backoff = 1.0
        while self.running:
            try:
                logger.info(f"Attempting to connect to Kafka brokers at {self.bootstrap_servers}...")
                self.consumer = KafkaConsumer(
                    *TOPICS,
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=False,  # Manual offset commit strategy
                    group_id="lakehouse-bronze-consumers"
                )
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
                )
                # Register partition listener
                self.consumer.subscribe(topics=TOPICS, listener=LoggingRebalanceListener())
                logger.info(f"Successfully connected to Kafka. Subscribed to topics: {TOPICS}")
                return True
            except KafkaError as e:
                logger.error(f"Connection failed: {e}. Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
        return False

    def save_to_bronze_layer(self, topic: str, payload: dict):
        # Partition by year, month, day, and platform
        import re
        raw_platform = payload.get("platform_name", "UNKNOWN")
        # Sanitize platform name to prevent path traversal (alphanumeric and underscores only)
        platform = re.sub(r'[^a-zA-Z0-9_]', '_', raw_platform.lower().replace(" ", "_"))
        dt = datetime.now()
        
        partition_dir = os.path.join(
            BRONZE_DIR,
            f"year={dt.strftime('%Y')}",
            f"month={dt.strftime('%m')}",
            f"day={dt.strftime('%d')}",
            f"platform={platform}"
        )
        os.makedirs(partition_dir, exist_ok=True)

        timestamp_str = dt.strftime("%H%M%S")
        uid = str(uuid.uuid4())[:8]
        filename = f"{timestamp_str}_{uid}.json"
        filepath = os.path.join(partition_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        logger.info(f"[BRONZE] Saved partitioned message. File: {filepath}")

    def route_to_dlq(self, payload: dict, error_message: str):
        # Update metrics
        metrics.dlq_count += 1
        
        dlq_payload = {
            "failed_payload": payload,
            "error": error_message,
            "failed_at": datetime.now().isoformat()
        }
        try:
            if self.producer:
                self.producer.send(DLQ_TOPIC, value=dlq_payload)
                self.producer.flush()
                # Update metrics
                metrics.publish_rate[DLQ_TOPIC] = metrics.publish_rate.get(DLQ_TOPIC, 0) + 1
                logger.warning(f"[DLQ] Routed corrupted/invalid payload to Dead Letter Queue: {error_message}")
        except Exception as e:
            logger.error(f"Failed to publish event to DLQ: {e}")

    def process_message(self, topic: str, payload: dict, partition: int, offset: int):
        # Structured Logging
        logger.info(f"[STAGE: INGEST] Topic: {topic}, Partition: {partition}, Offset: {offset}, Platform: {payload.get('platform_name')}, Ref: {payload.get('ref_number')}")
        
        # Schema Validation
        ref_number = payload.get("ref_number")
        platform_name = payload.get("platform_name")
        timestamp = payload.get("timestamp") or payload.get("scrape_timestamp")
        amount = payload.get("amount")
        status = payload.get("status")
        
        # Validate reviews, complaints, or transactions appropriately
        if topic in ["sentinelx.clean.reviews", "sentinelx.clean.complaints", "sentinelx.clean.news", "sentinelx.clean.payments"]:
            # Reviews/Complaints validation
            if not platform_name:
                metrics.rejected[(topic, "missing_platform")] = metrics.rejected.get((topic, "missing_platform"), 0) + 1
                raise ValueError("Validation failed: missing platform_name")
        else:
            # Transaction validation
            if not ref_number or not platform_name or not timestamp or amount is None or not status:
                missing = [k for k, v in [("ref_number", ref_number), ("platform_name", platform_name), ("timestamp", timestamp), ("amount", amount), ("status", status)] if not v]
                metrics.rejected[(topic, "missing_fields")] = metrics.rejected.get((topic, "missing_fields"), 0) + 1
                raise ValueError(f"Validation failed: missing required transactional fields: {missing}")

            try:
                if float(amount) <= 0:
                    metrics.rejected[(topic, "invalid_amount")] = metrics.rejected.get((topic, "invalid_amount"), 0) + 1
                    raise ValueError(f"Validation failed: transaction amount must be positive. Amount: {amount}")
            except (ValueError, TypeError):
                metrics.rejected[(topic, "non_numeric_amount")] = metrics.rejected.get((topic, "non_numeric_amount"), 0) + 1
                raise ValueError(f"Validation failed: amount must be a number. Amount: {amount}")

        # Store to Bronze layer partition
        self.save_to_bronze_layer(topic, payload)
        
        # Update metrics
        metrics.processed[topic] = metrics.processed.get(topic, 0) + 1

    def start_polling(self):
        if not self.metrics_started:
            metrics.start()
            self.metrics_started = True

        self.running = True
        logger.info("Kafka consumer loop active.")

        while self.running:
            try:
                if not self.consumer or not self.producer:
                    if not self.connect_with_retry():
                        break

                msg_pack = self.consumer.poll(timeout_ms=1000)
                for tp, messages in msg_pack.items():
                    # Calculate partition lag
                    try:
                        end_offsets = self.consumer.end_offsets([tp])
                        last_offset = end_offsets[tp]
                        current_lag = last_offset - messages[-1].offset if messages else 0
                        metrics.lag[(tp.topic, tp.partition)] = current_lag
                    except Exception as le:
                        logger.debug(f"Failed to calculate consumer partition lag: {le}")

                    for message in messages:
                        topic = tp.topic
                        payload = message.value
                        partition = tp.partition
                        offset = message.offset

                        try:
                            self.process_message(topic, payload, partition, offset)
                            # Commit only after successful processing
                            self.consumer.commit()
                        except ValueError as pe:
                            # Poison pill / Validation failure: Route to DLQ and commit offset to skip
                            logger.error(f"[INGEST ERROR] Validation exception: {pe}")
                            self.route_to_dlq(payload, str(pe))
                            self.consumer.commit()
                        except Exception as e:
                            # Transient storage write failure: Do NOT commit offset, raise to restart connection
                            logger.error(f"[TRANSIENT ERROR] Processing failed: {e}. Offset NOT committed.")
                            raise e
                        
            except Exception as e:
                logger.error(f"Polling loop encountered an exception: {e}. Reconnecting...")
                self.consumer = None
                self.producer = None
                time.sleep(2)

    def stop(self):
        logger.info("Shutting down consumer thread...")
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()

if __name__ == "__main__":
    consumer = KafkaStreamConsumer()
    
    # Graceful shutdown handlers
    def shutdown_handler(sig, frame):
        consumer.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    consumer.start_polling()
