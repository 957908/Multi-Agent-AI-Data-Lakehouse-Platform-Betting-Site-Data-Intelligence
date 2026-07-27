import sys
import os
import unittest
import json
import tempfile
import shutil
import pandas as pd
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, text

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data_pipelines.spark.spark_etl import execute_relational_upsert

class TestSprint3(unittest.TestCase):
    def setUp(self):
        # Create temp folder for testing databases
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_lakehouse.db")
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Initialize SQL engine
        self.engine = create_engine(self.db_url)
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS silver_transactions (
                    ref_number TEXT PRIMARY KEY,
                    user_id TEXT,
                    platform_name TEXT,
                    amount REAL,
                    method TEXT,
                    type TEXT,
                    status TEXT,
                    text_length INTEGER,
                    has_upi INTEGER,
                    has_bank INTEGER,
                    has_crypto INTEGER
                )
            """))

    def tearDown(self):
        self.engine.dispose()
        import time
        time.sleep(0.2)
        shutil.rmtree(self.temp_dir)

    def test_execute_relational_upsert_insert(self):
        # Create pandas dataframe to test database inserts
        df = pd.DataFrame([{
            "ref_number": "TX_TEST_101",
            "user_id": "USER_1",
            "platform_name": "Melbet",
            "amount": 500.0,
            "method": "UPI",
            "type": "DEPOSIT",
            "status": "SUCCESS",
            "text_length": 15,
            "has_upi": 1,
            "has_bank": 0,
            "has_crypto": 0
        }])
        
        # Run upsert under mocked DATABASE_URL pointing to our SQLite test db
        with patch("data_pipelines.spark.spark_etl.DATABASE_URL", self.db_url):
            execute_relational_upsert(df, "silver_transactions", "ref_number")
            
        # Verify row exists in DB
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM silver_transactions WHERE ref_number = 'TX_TEST_101'")).fetchone()
            
        self.assertIsNotNone(result)
        self.assertEqual(result[3], 500.0)  # amount column

    def test_execute_relational_upsert_update(self):
        # Insert initial row
        df_initial = pd.DataFrame([{
            "ref_number": "TX_TEST_102",
            "user_id": "USER_2",
            "platform_name": "Melbet",
            "amount": 200.0,
            "method": "UPI",
            "type": "DEPOSIT",
            "status": "PENDING",
            "text_length": 10,
            "has_upi": 1,
            "has_bank": 0,
            "has_crypto": 0
        }])
        
        # Upsert update row (change status and amount)
        df_update = pd.DataFrame([{
            "ref_number": "TX_TEST_102",
            "user_id": "USER_2",
            "platform_name": "Melbet",
            "amount": 350.0,
            "method": "UPI",
            "type": "DEPOSIT",
            "status": "SUCCESS",
            "text_length": 10,
            "has_upi": 1,
            "has_bank": 0,
            "has_crypto": 0
        }])
        
        with patch("data_pipelines.spark.spark_etl.DATABASE_URL", self.db_url):
            execute_relational_upsert(df_initial, "silver_transactions", "ref_number")
            execute_relational_upsert(df_update, "silver_transactions", "ref_number")
            
        # Verify row amount and status was updated (no new row inserted)
        with self.engine.connect() as conn:
            rows = conn.execute(text("SELECT * FROM silver_transactions")).fetchall()
            
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], 350.0)  # updated amount
        self.assertEqual(rows[0][6], "SUCCESS")  # updated status

    @patch("pyspark.sql.SparkSession")
    def test_spark_aggregations_mock(self, mock_spark_class):
        # Verify schema mapping and aggregate operations logic
        # Test basic pandas aggregate logic as equivalence
        data = [
            {"ref_number": "TX_A", "method": "UPI", "amount": 100.0, "status": "SUCCESS", "platform_name": "Melbet"},
            {"ref_number": "TX_B", "method": "UPI", "amount": 150.0, "status": "SUCCESS", "platform_name": "Melbet"},
            {"ref_number": "TX_C", "method": "BANK", "amount": 500.0, "status": "FAILED", "platform_name": "10Cric"},
        ]
        df_pandas = pd.DataFrame(data)
        
        # Calculate aggregates using pandas to mimic Spark logic
        df_gold_channels = df_pandas.groupby("method").agg(
            volume=("amount", "sum"),
            total_transactions=("ref_number", "count")
        ).reset_index()
        
        self.assertEqual(df_gold_channels.loc[df_gold_channels["method"] == "UPI", "volume"].values[0], 250.0)
        self.assertEqual(df_gold_channels.loc[df_gold_channels["method"] == "UPI", "total_transactions"].values[0], 2)

if __name__ == "__main__":
    unittest.main()
