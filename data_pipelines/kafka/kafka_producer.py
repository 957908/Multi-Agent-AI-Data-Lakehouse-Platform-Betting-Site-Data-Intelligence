"""
SharedKafkaProducer — reliable Kafka producer for SentinelX pipeline.

Improvements over original:
- acks='all' for financial data durability (all replicas must confirm)
- retries=3 with exponential backoff
- compression_type='gzip' for efficiency
- Health check / reconnect detection
- Graceful fallback when Docker is not running
"""

import json
import os
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


class SharedKafkaProducer:
    """
    Singleton-style Kafka producer wrapper.
    When Kafka is offline (Docker not running), self.enabled = False
    and all publish_event calls return False gracefully — no crash.
    """

    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.enabled = False
        self._connect()

    def _connect(self):
        try:
            from kafka import KafkaProducer
            from kafka.errors import KafkaError

            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                # acks='all' — leader + all in-sync replicas must confirm
                # Critical for financial/payment data integrity
                acks="all",
                # Retry up to 3 times on transient failures
                retries=3,
                retry_backoff_ms=300,
                # Compress payloads to reduce broker load
                compression_type="gzip",
                # Serialise all values as UTF-8 JSON
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                # Connection timeouts
                request_timeout_ms=8000,
                max_block_ms=5000,
                # Batch settings — small linger for near-realtime
                linger_ms=50,
                batch_size=16384,
            )
            self.enabled = True
            logger.info(f"[KAFKA] Connected to broker at {self.bootstrap_servers} | acks=all | retries=3 | gzip")

        except Exception as e:
            self.enabled = False
            logger.warning(
                f"[KAFKA OFFLINE] Cannot connect to {self.bootstrap_servers}. "
                f"Reason: {e}. "
                f"Running in direct-DB mode (Docker not running)."
            )

    def publish_event(self, topic: str, payload: dict, max_retries: int = 3) -> bool:
        """
        Publish a single event to a Kafka topic.
        Returns True on success, False on failure.
        Does NOT raise — always fails gracefully.
        """
        if not self.enabled or not self.producer:
            return False

        # Inject pipeline metadata on every published record
        payload.setdefault("_kafka_topic", topic)
        payload.setdefault("_published_at", datetime.now(timezone.utc).isoformat())

        for attempt in range(1, max_retries + 1):
            try:
                future = self.producer.send(topic, value=payload)
                # Block until broker confirms (acks=all means all replicas confirmed)
                record_metadata = future.get(timeout=5)
                logger.info(
                    f"[KAFKA ✓] topic={topic} | partition={record_metadata.partition} | "
                    f"offset={record_metadata.offset} | platform={payload.get('platform_name')} | "
                    f"method/ref={payload.get('method_name') or payload.get('ref_number')}"
                )
                return True

            except Exception as e:
                wait = 0.3 * attempt  # exponential-ish backoff
                logger.warning(
                    f"[KAFKA] Attempt {attempt}/{max_retries} failed for topic={topic}: {e}. "
                    f"Retrying in {wait}s..."
                )
                if attempt < max_retries:
                    time.sleep(wait)

        logger.error(f"[KAFKA ✗] All {max_retries} attempts failed for topic={topic}. DB fallback active.")
        return False

    def is_healthy(self) -> bool:
        """Quick health check — returns True if producer can reach broker."""
        if not self.enabled or not self.producer:
            return False
        try:
            # Attempt a metadata refresh as a health ping
            self.producer.partitions_for("__consumer_offsets")
            return True
        except Exception:
            self.enabled = False
            return False

    def close(self):
        if self.producer:
            try:
                self.producer.flush(timeout=5)   # Flush pending messages before close
                self.producer.close(timeout=5)
                logger.info("[KAFKA] Producer closed cleanly.")
            except Exception as e:
                logger.warning(f"[KAFKA] Close error: {e}")
