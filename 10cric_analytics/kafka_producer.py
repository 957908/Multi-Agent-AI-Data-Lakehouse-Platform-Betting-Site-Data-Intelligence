import json
import os
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Get bootstrap servers from env or default
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

class KafkaDataProducer:
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.enabled = False
        
        try:
            print(f"Connecting to Kafka bootstrap servers: {self.bootstrap_servers}...")
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                request_timeout_ms=5000,
                max_block_ms=3000
            )
            self.enabled = True
            print("[INFO] Successfully connected to Kafka.")
        except KafkaError as e:
            print(f"[WARNING] Could not connect to Kafka broker: {e}")
            print("Kafka streaming will be disabled for this run (scrapers will continue locally).")

    def publish(self, topic: str, data: dict) -> bool:
        """Publishes a JSON payload to a specified Kafka topic."""
        if not self.enabled or not self.producer:
            return False
            
        try:
            future = self.producer.send(topic, value=data)
            # Block briefly to ensure delivery/failure response in CLI execution
            record_metadata = future.get(timeout=3)
            print(f"[INFO] Sent message to topic '{topic}' [partition={record_metadata.partition}, offset={record_metadata.offset}]")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to publish message to Kafka topic '{topic}': {e}")
            return False

    def close(self):
        if self.producer:
            self.producer.close()
            print("Kafka producer connection closed.")
