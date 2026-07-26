import json
import os
from kafka import KafkaProducer
from kafka.errors import KafkaError

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

class SharedKafkaProducer:
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.enabled = False
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                request_timeout_ms=5000,
                max_block_ms=3000
            )
            self.enabled = True
            print(f"[INFO] Connected to Kafka producer on {self.bootstrap_servers}")
        except KafkaError as e:
            print(f"[WARNING] Could not connect to Kafka broker: {e}. Running in local-only fallback mode.")

    def publish_event(self, topic: str, payload: dict) -> bool:
        if not self.enabled or not self.producer:
            return False
            
        try:
            future = self.producer.send(topic, value=payload)
            record_metadata = future.get(timeout=3)
            print(f"[KAFKA] Published to '{topic}' [partition={record_metadata.partition}, offset={record_metadata.offset}]")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to publish message to topic '{topic}': {e}")
            return False

    def close(self):
        if self.producer:
            self.producer.close()
