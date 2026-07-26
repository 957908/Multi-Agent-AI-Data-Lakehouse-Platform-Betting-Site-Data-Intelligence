import json
import os
import uuid
from datetime import datetime
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPICS = ["melbet-raw-data", "10cric-raw-data", "22bet-raw-data", "stake-raw-data", "mostbet-raw-data", "parimatch-raw-data"]
DLQ_TOPIC = "dead-letter-queue"
RETRY_TOPIC = "stream-retry"

BRONZE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "bronze")
os.makedirs(BRONZE_DIR, exist_ok=True)

class KafkaStreamConsumer:
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.producer = None
        self.running = False

    def connect(self):
        try:
            # Subscribe to main scraping topics
            self.consumer = KafkaConsumer(
                *TOPICS,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id="lakehouse-consumers",
                consumer_timeout_ms=1000
            )
            # Producer to publish to DLQ or Retry topics
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
            )
            print(f"[INFO] Consumer connected. Listening on topics: {', '.join(TOPICS)}")
            return True
        except KafkaError as e:
            print(f"[ERROR] Failed to initialize Kafka consumer infrastructure: {e}")
            return False

    def save_to_bronze_layer(self, topic: str, payload: dict):
        topic_dir = os.path.join(BRONZE_DIR, topic)
        os.makedirs(topic_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{uid}.json"
        
        filepath = os.path.join(topic_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        print(f"[BRONZE] Saved raw message to: {filepath}")

    def route_to_dlq(self, payload: dict, error_message: str):
        """Routes failed messages to the Dead Letter Queue topic for debugging."""
        dlq_payload = {
            "failed_payload": payload,
            "error": error_message,
            "failed_at": datetime.now().isoformat()
        }
        try:
            self.producer.send(DLQ_TOPIC, value=dlq_payload)
            print(f"[DLQ] Routing corrupted payload to Dead Letter Queue: {error_message}")
        except Exception as pe:
            print(f"[ERROR] Failed to publish event to DLQ: {pe}")

    def process_message(self, topic: str, payload: dict):
        # Basic validation: ensure platform and ref_number are in payload
        if not payload.get("platform_name") or not payload.get("ref_number"):
            raise ValueError("Corrupted transaction log: missing platform_name or ref_number.")
        
        self.save_to_bronze_layer(topic, payload)

    def start_polling(self):
        if not self.connect():
            return
            
        self.running = True
        print("\n" + "="*70)
        print(" KAFKA STREAM CONSUMER LISTENING (PRESS CTRL+C TO STOP)")
        print("="*70 + "\n")
        
        try:
            while self.running:
                msg_pack = self.consumer.poll(timeout_ms=500)
                for tp, messages in msg_pack.items():
                    for message in messages:
                        topic = tp.topic
                        payload = message.value
                        print(f"[EVENT] Received event from topic '{topic}'")
                        
                        try:
                            self.process_message(topic, payload)
                        except Exception as pe:
                            # Route to DLQ if validation fails
                            self.route_to_dlq(payload, str(pe))
                            
        except KeyboardInterrupt:
            print("\nShutting down streaming consumer...")
        finally:
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()

if __name__ == "__main__":
    consumer = KafkaStreamConsumer()
    consumer.start_polling()
