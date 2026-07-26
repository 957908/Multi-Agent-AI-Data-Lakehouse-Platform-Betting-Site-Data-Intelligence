import json
import os
import time
from datetime import datetime
from kafka import KafkaConsumer
from backend.app.core.database import SessionLocal
from backend.app.models.models import Transaction, Platform, PaymentMethod

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = "10cric-raw-data"

class FlinkWindowProcessor:
    """
    Simulates Apache Flink stream processing logic:
    1. Deduplication on Transaction reference numbers.
    2. Data Enrichment (matching Platform names and Payment methods to DB identifiers).
    3. Window Aggregation (5-second Tumbling Window to sum transaction volume).
    """
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.seen_refs = set()
        self.window_data = []
        self.last_window_flush = time.time()
        self.window_duration = 5.0 # 5-second tumbling window

    def run(self):
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                consumer_timeout_ms=1000
            )
            print(f"[FLINK] Listening to Kafka for stream processing on topic: {TOPIC}...")
        except Exception as e:
            print(f"[WARNING] [FLINK] Flink stream broker connection skipped: {e}")
            return

        db = SessionLocal()
        
        try:
            while True:
                messages = consumer.poll(timeout_ms=500)
                for tp, msg_list in messages.items():
                    for msg in msg_list:
                        payload = msg.value
                        tx = payload.get("data", {}) if "data" in payload else payload
                        
                        # --- 1. Deduplication ---
                        ref = tx.get("ref_number")
                        if not ref or ref in self.seen_refs:
                            continue
                        self.seen_refs.add(ref)

                        # --- 2. Data Enrichment & Accumulation ---
                        amount = float(tx.get("amount", 0.0))
                        platform_name = tx.get("platform_name", "Unknown")
                        method_name = tx.get("method", "UPI")

                        self.window_data.append({
                            "ref_number": ref,
                            "amount": amount,
                            "platform_name": platform_name,
                            "method": method_name,
                            "type": tx.get("type", "DEPOSIT"),
                            "status": tx.get("status", "SUCCESS")
                        })
                
                # --- 3. Tumbling Window Aggregation Trigger ---
                now = time.time()
                if now - self.last_window_flush >= self.window_duration:
                    self.flush_window_aggregations(db)
                    self.last_window_flush = now
                    
        except KeyboardInterrupt:
            print("[FLINK] Processing shut down.")
        finally:
            db.close()

    def flush_window_aggregations(self, db):
        if not self.window_data:
            return
            
        total_tx = len(self.window_data)
        total_volume = sum(item["amount"] for item in self.window_data)
        
        print("\n" + "-"*50)
        print(f"[FLINK WINDOW] Window flushed at {datetime.now().strftime('%H:%M:%S')}")
        print(f"  └ Total Transactions: {total_tx}")
        print(f"  └ Total Volume: {total_volume:.2f} INR")
        
        # Save enriched transactions to database
        for item in self.window_data:
            try:
                # Resolve Platform ID
                platform = db.query(Platform).filter(Platform.name == item["platform_name"]).first()
                if not platform:
                    platform = Platform(name=item["platform_name"], url=f"https://{item['platform_name'].lower()}.com")
                    db.add(platform)
                    db.commit()
                    db.refresh(platform)
                
                # Resolve Payment Method ID
                method = db.query(PaymentMethod).filter(PaymentMethod.name == item["method"]).first()
                if not method:
                    method = PaymentMethod(name=item["method"], type="UPI")
                    db.add(method)
                    db.commit()
                    db.refresh(method)

                # Persist Transaction
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
                print(f"[FLINK ERROR] Failed to enrich and save event: {e}")
                
        self.window_data.clear()
        print("-"*50 + "\n")

if __name__ == "__main__":
    processor = FlinkWindowProcessor()
    processor.run()
