import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Scrapy path setup
scrapy_root = os.path.join(project_root, "scrapers", "scrapy")
if scrapy_root not in sys.path:
    sys.path.insert(0, scrapy_root)

from data_collection.items import TransactionItem, ReviewItem, ComplaintItem
from data_collection.pipelines import DataValidationPipeline, KafkaPublisherPipeline, PostgresExportPipeline
from data_collection.spiders.cric10 import Cric10Spider
from data_collection.spiders.melbet import MelbetSpider
from data_collection.spiders.mostbet import MostbetSpider
from data_collection.spiders.parimatch import ParimatchSpider
from data_collection.spiders.stake import StakeSpider
from scrapy.exceptions import DropItem

class TestSprint1(unittest.TestCase):
    def test_spider_compilation(self):
        # Verify all spiders instantiate without error and contain required properties
        spiders = [Cric10Spider(), MelbetSpider(), MostbetSpider(), ParimatchSpider(), StakeSpider()]
        for spider in spiders:
            self.assertIsNotNone(spider.name)
            self.assertIsNotNone(spider.start_urls)

    def test_validation_pipeline_success(self):
        pipeline = DataValidationPipeline()
        spider = MagicMock()
        item = TransactionItem(
            platform_name="10Cric",
            ref_number="TX_VALID_123",
            amount=1000.0,
            type="DEPOSIT",
            status="SUCCESS"
        )
        result = pipeline.process_item(item, spider)
        self.assertEqual(result, item)

    def test_validation_pipeline_missing_fields(self):
        pipeline = DataValidationPipeline()
        spider = MagicMock()
        
        # Missing ref_number
        item_missing_ref = TransactionItem(
            platform_name="10Cric",
            amount=1000.0,
            type="DEPOSIT",
            status="SUCCESS"
        )
        with self.assertRaises(DropItem):
            pipeline.process_item(item_missing_ref, spider)

        # Negative amount
        item_neg_amount = TransactionItem(
            platform_name="10Cric",
            ref_number="TX_NEG_123",
            amount=-5.0,
            type="DEPOSIT",
            status="SUCCESS"
        )
        with self.assertRaises(DropItem):
            pipeline.process_item(item_neg_amount, spider)

    @patch("data_pipelines.kafka.kafka_producer.SharedKafkaProducer")
    def test_kafka_publisher_pipeline_success(self, mock_producer_class):
        # Setup mock producer
        mock_producer = MagicMock()
        mock_producer.enabled = True
        mock_producer.publish_event.return_value = True
        mock_producer_class.return_value = mock_producer

        pipeline = KafkaPublisherPipeline()
        spider = MagicMock(name="cric10")
        spider.name = "cric10"

        pipeline.open_spider(spider)
        
        item = TransactionItem(
            platform_name="10Cric",
            ref_number="TX_KAFKA_123",
            amount=1000.0,
            type="DEPOSIT",
            status="SUCCESS"
        )
        
        result = pipeline.process_item(item, spider)
        self.assertTrue(result.get("_pushed_to_kafka"))
        mock_producer.publish_event.assert_called_once()
        pipeline.close_spider(spider)

    @patch("data_pipelines.kafka.kafka_producer.SharedKafkaProducer")
    def test_kafka_publisher_pipeline_fallback(self, mock_producer_class):
        # Mock producer disabled/offline
        mock_producer = MagicMock()
        mock_producer.enabled = False
        mock_producer_class.return_value = mock_producer

        pipeline = KafkaPublisherPipeline()
        spider = MagicMock(name="cric10")
        spider.name = "cric10"

        pipeline.open_spider(spider)
        
        item = TransactionItem(
            platform_name="10Cric",
            ref_number="TX_KAFKA_123",
            amount=1000.0,
            type="DEPOSIT",
            status="SUCCESS"
        )
        
        result = pipeline.process_item(item, spider)
        # Since Kafka was disabled, flag _pushed_to_kafka should NOT be True
        self.assertNotEqual(result.get("_pushed_to_kafka"), True)
        pipeline.close_spider(spider)

    def test_postgres_pipeline_skips_when_pushed_to_kafka(self):
        pipeline = PostgresExportPipeline()
        spider = MagicMock()
        pipeline.db = MagicMock() # mock DB session
        
        item = TransactionItem(
            platform_name="10Cric",
            ref_number="TX_SKIP_DB",
            amount=1000.0,
            type="DEPOSIT",
            status="SUCCESS",
            _pushed_to_kafka=True
        )
        
        result = pipeline.process_item(item, spider)
        # The pipeline should return item directly without calling DB queries
        pipeline.db.query.assert_not_called()
        self.assertEqual(result, item)

if __name__ == "__main__":
    unittest.main()
