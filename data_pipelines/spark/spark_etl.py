import os
import sys
import json
import sqlite3
import logging
import http.server
import threading
import time
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text

# Configure path mapping to backend app database configs
STORAGE_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(STORAGE_DIR))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.core.database import engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [SPARK] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SparkETL")

BRONZE_DIR = os.path.join(STORAGE_DIR, "bronze")
BACKEND_DB = os.path.join(project_root, "backend", "app", "betting_lakehouse.db")

# Prometheus Metrics Exporter (Task 7)
class SparkMetricsServer:
    def __init__(self, port=8003):
        self.port = port
        self.rows_read = 0
        self.rows_written = 0
        self.rejected_rows = 0
        self.duplicate_rows = 0
        self.execution_time = 0.0
        self.jdbc_sync_time = 0.0

    def start(self):
        m_self = self
        class MetricsHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in ('/metrics', '/'):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.end_headers()
                    output = [
                        f"spark_rows_read_total {m_self.rows_read}",
                        f"spark_rows_written_total {m_self.rows_written}",
                        f"spark_rejected_rows_total {m_self.rejected_rows}",
                        f"spark_duplicate_rows_total {m_self.duplicate_rows}",
                        f"spark_execution_time_seconds {m_self.execution_time}",
                        f"spark_jdbc_sync_time_seconds {m_self.jdbc_sync_time}"
                    ]
                    self.wfile.write("\n".join(output).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()
            def log_message(self, format, *args):
                pass
        def run():
            try:
                server = http.server.HTTPServer(('0.0.0.0', m_self.port), MetricsHandler)
                server.serve_forever()
            except Exception as e:
                logger.error(f"Failed to start Spark metrics server: {e}")
        t = threading.Thread(target=run, daemon=True)
        t.start()
        logger.info(f"Spark metrics exporter active at http://localhost:{self.port}/metrics")

metrics = SparkMetricsServer()

def execute_relational_upsert(df_pandas, table_name, conflict_col):
    """
    Saves Pandas dataframe to the relational database using an UPSERT pattern.
    Handles PostgreSQL conflict updates and SQLite replace statements.
    """
    try:
        if "sqlite" in str(engine.url):
            # SQLite: use INSERT OR REPLACE
            with engine.begin() as conn:
                columns = ", ".join(df_pandas.columns)
                placeholders = ", ".join([f":{col}" for col in df_pandas.columns])
                query = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
                
                for _, row in df_pandas.iterrows():
                    conn.execute(text(query), row.to_dict())
        else:
            # PostgreSQL: use INSERT ON CONFLICT DO UPDATE
            with engine.begin() as conn:
                # Stage records into a staging table first
                staging_table = f"{table_name}_staging"
                df_pandas.to_sql(staging_table, con=conn, if_exists="replace", index=False)
                
                # Formulate Postgres Merge Query
                cols = list(df_pandas.columns)
                columns_str = ", ".join(cols)
                select_str = ", ".join([f"s.{c}" for c in cols])
                update_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in cols if c != conflict_col])
                
                merge_query = f"""
                INSERT INTO {table_name} ({columns_str})
                SELECT {columns_str} FROM {staging_table}
                ON CONFLICT ({conflict_col})
                DO UPDATE SET {update_str};
                """
                conn.execute(text(merge_query))
                conn.execute(text(f"DROP TABLE {staging_table}"))
    finally:
        engine.dispose()

def run_spark_lakehouse_etl():
    """
    Initializes Spark Session with Nessie/Iceberg integrations.
    Performs Bronze->Silver->Gold ETL pipelines, and updates the production database.
    """
    metrics.start()
    start_time = time.time()
    
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import col, when, length, count, sum, avg, to_timestamp, lit
        
        logger.info("Initializing PySpark Session with Nessie & Iceberg catalog...")
        
        spark = SparkSession.builder \
            .appName("LakehouseIcebergETL") \
            .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.4_2.12:0.73.0") \
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions") \
            .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
            .config("spark.sql.catalog.nessie.uri", os.getenv("NESSIE_URI", "http://localhost:19120/api/v1")) \
            .config("spark.sql.catalog.nessie.ref", "main") \
            .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
            .config("spark.sql.catalog.nessie.warehouse", os.getenv("NESSIE_WAREHOUSE", "s3a://warehouse/")) \
            .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://localhost:9005")) \
            .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", "admin")) \
            .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "supersecretpassword")) \
            .config("spark.hadoop.fs.s3a.path.style.access", "true") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.optimizer.dynamicPartitionPruning.enabled", "true") \
            .getOrCreate()

        logger.info("Reading raw Bronze JSON events...")
        # Read partitioned JSON from Bronze (Task 2)
        df_bronze = spark.read.json(f"{BRONZE_DIR}/*/*/*/*.json")
        raw_count = df_bronze.count()
        metrics.rows_read = raw_count
        logger.info(f"Loaded {raw_count} raw rows from Bronze storage.")

        # Schema Validation & Cast logic (Task 2)
        df_valid = df_bronze.filter(
            col("ref_number").isNotNull() & 
            col("platform_name").isNotNull() & 
            col("amount").isNotNull()
        )
        valid_count = df_valid.count()
        metrics.rejected_rows = raw_count - valid_count

        # Deduplicate & Clean (Task 2)
        df_cleaned = df_valid.dropDuplicates(["ref_number"]) \
            .withColumn("amount", col("amount").cast("double")) \
            .withColumn("timestamp", to_timestamp(col("timestamp"))) \
            .withColumn("text_length", when(col("raw_text").isNotNull(), length(col("raw_text"))).otherwise(0)) \
            .withColumn("has_upi", when(col("raw_text").contains("@"), 1).otherwise(0)) \
            .withColumn("has_bank", when(col("raw_text").contains("IFSC"), 1).otherwise(0)) \
            .withColumn("has_crypto", when(col("raw_text").contains("0x"), 1).otherwise(0))

        cleaned_count = df_cleaned.count()
        metrics.duplicate_rows = valid_count - cleaned_count
        logger.info(f"Deduplicated rows: {cleaned_count} valid records out of {raw_count} raw inputs.")

        # Write to Iceberg Silver Tables
        logger.info("Writing clean transactions to Iceberg Silver layer table: nessie.silver_transactions")
        df_cleaned.write \
            .format("iceberg") \
            .mode("append") \
            .save("nessie.silver_transactions")
        metrics.rows_written += cleaned_count

        # Gold Layer Aggregations (Task 3)
        logger.info("Calculating payment channel metrics aggregates...")
        df_gold_channels = df_cleaned.groupBy("method") \
            .agg(
                sum("amount").alias("volume"),
                count("ref_number").alias("total_transactions")
            )
        
        logger.info("Writing aggregates to Gold table: nessie.gold_payment_channels")
        df_gold_channels.write \
            .format("iceberg") \
            .mode("overwrite") \
            .save("nessie.gold_payment_channels")

        logger.info("Calculating platform risk metrics aggregates...")
        df_gold_platform = df_cleaned.groupBy("platform_name") \
            .agg(
                count("ref_number").alias("transaction_count"),
                avg(when(col("status") == "SUCCESS", 1).otherwise(0)).alias("success_rate"),
                avg(col("amount")).alias("avg_amount")
            ).withColumn("risk_score", when(col("success_rate") < 0.5, lit(80.0)).otherwise(lit(20.0)))

        logger.info("Writing aggregates to Gold table: nessie.gold_platform_metrics")
        df_gold_platform.write \
            .format("iceberg") \
            .mode("overwrite") \
            .save("nessie.gold_platform_metrics")

        # PostgreSQL/SQLite Synchronization (Task 6)
        jdbc_start = time.time()
        logger.info("Synchronizing data to the relational database using UPSERT/JDBC pattern...")
        
        # Avoid collect() by performing synchronization row-by-row via pandas chunk loading
        df_silver_pandas = df_cleaned.select("ref_number", "user_id", "platform_name", "amount", "method", "type", "status", "text_length", "has_upi", "has_bank", "has_crypto").toPandas()
        execute_relational_upsert(df_silver_pandas, "silver_transactions", "ref_number")
        
        df_gold_channels_pandas = df_gold_channels.toPandas()
        execute_relational_upsert(df_gold_channels_pandas, "gold_payment_channels", "method")

        df_gold_platform_pandas = df_gold_platform.select("platform_name", "transaction_count", "success_rate", "risk_score").toPandas()
        execute_relational_upsert(df_gold_platform_pandas, "gold_platform_metrics", "platform_name")

        metrics.jdbc_sync_time = time.time() - jdbc_start
        metrics.execution_time = time.time() - start_time
        logger.info(f"Relational DB synchronization successful. Sync time: {metrics.jdbc_sync_time:.2f}s")
        
        # Sleep for 15s to allow Prometheus to scrape the metrics server before shutting down
        logger.info("ETL complete. Waiting 15s for Prometheus metrics collection...")
        time.sleep(15)
        spark.stop()

    except Exception as e:
        logger.warning(f"PySpark catalog unavailable: {e}. Executing Pandas fallback pipeline.")
        run_pandas_fallback_etl()

def run_pandas_fallback_etl():
    """
    Pandas fallback execution engine updating SQLite/PostgreSQL databases directly
    when SparkSession cannot initialize.
    """
    os.makedirs(os.path.dirname(BACKEND_DB), exist_ok=True)

    # DDL initialization
    with engine.begin() as conn:
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
                has_crypto INTEGER,
                scraped_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gold_payment_channels (
                method TEXT PRIMARY KEY,
                volume REAL,
                total_transactions INTEGER
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gold_platform_metrics (
                platform_name TEXT PRIMARY KEY,
                transaction_count INTEGER,
                success_rate REAL,
                risk_score REAL
            )
        """))

    collected_tx = []
    if os.path.exists(BRONZE_DIR):
        for root_dir, _, files in os.walk(BRONZE_DIR):
            for file in files:
                if file.endswith(".json"):
                    with open(os.path.join(root_dir, file), "r", encoding="utf-8") as f:
                        try:
                            payload = json.load(f)
                            collected_tx.append(payload)
                        except Exception:
                            continue

    if collected_tx:
        df = pd.DataFrame(collected_tx)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["text_length"] = df["raw_text"].astype(str).str.len() if "raw_text" in df.columns else 0
        df["has_upi"] = df["raw_text"].astype(str).str.contains("@").astype(int) if "raw_text" in df.columns else 0
        df["has_bank"] = df["raw_text"].astype(str).str.contains("IFSC").astype(int) if "raw_text" in df.columns else 0
        df["has_crypto"] = df["raw_text"].astype(str).str.contains("0x").astype(int) if "raw_text" in df.columns else 0
        
        columns = ["ref_number", "user_id", "platform_name", "amount", "method", "type", "status", "text_length", "has_upi", "has_bank", "has_crypto"]
        for col in columns:
            if col not in df.columns:
                df[col] = "UNKNOWN" if col != "amount" and col != "text_length" else 0
                
        df = df[columns].drop_duplicates(subset=["ref_number"])
        
        # Ingest Silver
        execute_relational_upsert(df, "silver_transactions", "ref_number")
        
        # Calculate Gold aggregates
        df_gold_channels = df.groupby("method").agg(
            volume=("amount", "sum"),
            total_transactions=("ref_number", "count")
        ).reset_index()
        execute_relational_upsert(df_gold_channels, "gold_payment_channels", "method")

        df_gold_platform = df.groupby("platform_name").agg(
            transaction_count=("ref_number", "count"),
            success_count=("status", lambda x: (x == "SUCCESS").sum())
        ).reset_index()
        df_gold_platform["success_rate"] = df_gold_platform["success_count"] / df_gold_platform["transaction_count"]
        df_gold_platform["risk_score"] = df_gold_platform["success_rate"].apply(lambda x: 80.0 if x < 0.5 else 20.0)
        df_gold_platform = df_gold_platform[["platform_name", "transaction_count", "success_rate", "risk_score"]]
        
        execute_relational_upsert(df_gold_platform, "gold_platform_metrics", "platform_name")
        logger.info(f"[ETL FALLBACK SUCCESS] Synced {len(df)} transactions into Relational DB.")
    else:
        logger.info("No Bronze data found to process.")

if __name__ == "__main__":
    run_spark_lakehouse_etl()
