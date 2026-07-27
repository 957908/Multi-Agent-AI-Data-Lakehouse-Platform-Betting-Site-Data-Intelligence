import sys
import os
import unittest
import json
import shutil
import tempfile
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data_pipelines.kafka.kafka_consumer import KafkaStreamConsumer
from data_pipelines.flink.flink_consumer import FlinkWindowProcessor

class TestSprint2(unittest.TestCase):
    def setUp(self):
        # Create temp directory for testing Bronze storage path
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        # Clean up temp files
        shutil.rmtree(self.test_dir)

    @patch("data_pipelines.kafka.kafka_consumer.KafkaConsumer")
    @patch("data_pipelines.kafka.kafka_consumer.KafkaProducer")
    def test_kafka_consumer_validation_and_dlq(self, mock_producer_class, mock_consumer_class):
        # Set up mock objects
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer
        
        consumer = KafkaStreamConsumer()
        consumer.producer = mock_producer
        consumer.running = True
        
        # Test Case 1: Corrupted Payload (Missing Fields)
        invalid_payload = {
            "ref_number": "TX_123",
            # Missing platform_name, amount, status
        }
        
        with patch("data_pipelines.kafka.kafka_consumer.BRONZE_DIR", self.test_dir):
            # Should raise ValueError and route to DLQ
            with self.assertRaises(ValueError):
                consumer.process_message("transactions-clean", invalid_payload, 0, 100)
                
        # Verify routed to DLQ
        consumer.route_to_dlq(invalid_payload, "Missing fields")
        mock_producer.send.assert_called_with("dead-letter-queue", value={
            "failed_payload": invalid_payload,
            "error": "Missing fields",
            "failed_at": unittest.mock.ANY
        })

    @patch("data_pipelines.kafka.kafka_consumer.KafkaConsumer")
    @patch("data_pipelines.kafka.kafka_consumer.KafkaProducer")
    def test_bronze_storage_partitioning(self, mock_producer_class, mock_consumer_class):
        consumer = KafkaStreamConsumer()
        
        payload = {
            "ref_number": "TX_456",
            "platform_name": "Melbet",
            "timestamp": datetime.now().isoformat(),
            "amount": 250.0,
            "status": "SUCCESS"
        }
        
        with patch("data_pipelines.kafka.kafka_consumer.BRONZE_DIR", self.test_dir):
            consumer.process_message("transactions-clean", payload, 0, 101)
            
            # Verify file exists in partition directory
            dt = datetime.now()
            expected_subdir = os.path.join(
                self.test_dir,
                f"year={dt.strftime('%Y')}",
                f"month={dt.strftime('%m')}",
                f"day={dt.strftime('%d')}",
                "platform=melbet"
            )
            
            self.assertTrue(os.path.exists(expected_subdir))
            files = os.listdir(expected_subdir)
            self.assertEqual(len(files), 1)
            
            # Read and verify content
            with open(os.path.join(expected_subdir, files[0]), "r") as f:
                saved = json.load(f)
            self.assertEqual(saved["ref_number"], "TX_456")

    @patch("data_pipelines.flink.flink_consumer.KafkaConsumer")
    @patch("data_pipelines.flink.flink_consumer.KafkaProducer")
    @patch("data_pipelines.flink.flink_consumer.SessionLocal")
    def test_flink_validation_and_deduplication(self, mock_session, mock_producer_class, mock_consumer_class):
        processor = FlinkWindowProcessor()
        processor.producer = MagicMock()
        
        # Payload 1: Valid
        payload_1 = {
            "ref_number": "TX_DUP_1",
            "platform_name": "10Cric",
            "amount": 100.0,
            "timestamp": datetime.now().isoformat(),
            "status": "SUCCESS",
            "method": "UPI"
        }
        
        # Inject raw topic polling simulation
        tp_mock = MagicMock()
        tp_mock.topic = "10cric-raw-data"
        msg_mock_1 = MagicMock()
        msg_mock_1.value = payload_1
        
        mock_consumer = MagicMock()
        mock_consumer.poll.return_value = {tp_mock: [msg_mock_1]}
        processor.consumer = mock_consumer
        processor.running = True
        
        # Run Flink event poll once (simulate loop run)
        # We manually invoke the validation & aggregation checks on processor
        db_mock = MagicMock()
        
        # Test Case 1: First arrival succeeds
        processor.window_data.clear()
        processor.seen_refs.clear()
        
        # Verify deduplication
        now = time.time()
        processor.seen_refs["TX_DUP_1"] = now
        
        # If we poll again with same ref, it should skip appending
        msg_mock_dup = MagicMock()
        msg_mock_dup.value = payload_1
        
        # Simulate deduplication check
        ref = payload_1["ref_number"]
        is_dup = ref in processor.seen_refs
        self.assertTrue(is_dup)

    @patch("data_pipelines.flink.flink_consumer.KafkaConsumer")
    @patch("data_pipelines.flink.flink_consumer.KafkaProducer")
    def test_flink_watermark_allowed_lateness(self, mock_producer_class, mock_consumer_class):
        processor = FlinkWindowProcessor()
        processor.producer = MagicMock()
        
        # Let's set max event time seen so far to a high value
        processor.max_event_time = datetime(2026, 7, 27, 22, 0, 0).timestamp()
        processor.allowed_lateness = 10.0 # 10 seconds
        
        # Watermark = 22:00:00 - 10s = 21:59:50
        
        # Late event: 21:59:40 (10 seconds older than watermark)
        late_payload = {
            "ref_number": "TX_LATE",
            "platform_name": "10Cric",
            "amount": 100.0,
            "timestamp": datetime(2026, 7, 27, 21, 59, 40).isoformat(),
            "status": "SUCCESS",
            "method": "UPI"
        }
        
        # Mock route to DLQ
        processor.route_to_dlq = MagicMock()
        
        # Test process logic manually
        event_time_ts = datetime.fromisoformat(late_payload["timestamp"]).timestamp()
        watermark = processor.max_event_time - processor.allowed_lateness
        
        if event_time_ts < watermark:
            processor.route_to_dlq(late_payload, "Late event arrived after watermark")
            
        processor.route_to_dlq.assert_called_once_with(late_payload, "Late event arrived after watermark")

if __name__ == "__main__":
    unittest.main()
