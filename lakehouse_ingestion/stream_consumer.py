import asyncio
import json
import os
import uuid
from datetime import datetime
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPICS = [
    "melbet-profile",
    "melbet-deposits",
    "melbet-withdrawals",
    "melbet-bets",
    "10cric-raw-data"
]
BRONZE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bronze")

# Ensure Bronze Lakehouse Directory exists
os.makedirs(BRONZE_DIR, exist_ok=True)
for topic in TOPICS:
    os.makedirs(os.path.join(BRONZE_DIR, topic), exist_ok=True)

class StreamingIngestionConsumer:
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.running = False

    def connect(self):
        try:
            print(f"Connecting to Kafka on {self.bootstrap_servers}...")
            # Initialize consumer and subscribe to topics
            self.consumer = KafkaConsumer(
                *TOPICS,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id="lakehouse-bronze-ingestors",
                consumer_timeout_ms=1000 # Short timeout for non-blocking poll
            )
            print(f"[INFO] Connected to Kafka. Subscribed to topics: {', '.join(TOPICS)}")
            return True
        except KafkaError as e:
            print(f"[ERROR] Failed to connect to Kafka broker: {e}")
            return False

    def save_to_bronze(self, topic: str, payload: dict):
        """Simulates writing to Bronze Lakehouse table partitioned by topic name."""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp_str}_{unique_id}.json"
        
        filepath = os.path.join(BRONZE_DIR, topic, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        
        print(f"[STORE] Saved raw record to Bronze Lakehouse: [Topic={topic}] -> {os.path.basename(filepath)}")

    def run(self):
        if not self.connect():
            return

        self.running = True
        print("\n" + "=" * 60)
        print("REAL-TIME STREAMING INGESTION CONSUMER (BRONZE LAYER)")
        print("Listening for messages... Press Ctrl+C to terminate.")
        print("=" * 60 + "\n")

        try:
            while self.running:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=500)
                for tp, messages in message_batch.items():
                    for message in messages:
                        topic = tp.topic
                        payload = message.value
                        print(f"[EVENT] Received event from partition {message.partition} on topic '{topic}':")
                        
                        # Pretty print summary info
                        if "profile" in topic:
                            print(f"  └ Profile Event: User ID={payload.get('user_id')}, Username={payload.get('profile', {}).get('username')}")
                        elif "deposits" in topic or "withdrawals" in topic or "bets" in topic:
                            print(f"  └ Financial Event: User ID={payload.get('user_id')}, Amt/PnL={payload.get('amount') or payload.get('profit_loss') or payload.get('stake')} {payload.get('currency', '')}")
                        elif "10cric" in topic:
                            print(f"  └ 10Cric Scraper Event: Scraper={payload.get('scraper')}, Headings={payload.get('data', {}).get('page_title')}")
                        
                        # Save to Bronze Lakehouse object storage replica
                        self.save_to_bronze(topic, payload)
                        
        except KeyboardInterrupt:
            print("\nShutting down streaming consumer gracefully...")
        finally:
            if self.consumer:
                self.consumer.close()
            print("Streaming consumer connection closed.")

if __name__ == "__main__":
    consumer = StreamingIngestionConsumer()
    consumer.run()
