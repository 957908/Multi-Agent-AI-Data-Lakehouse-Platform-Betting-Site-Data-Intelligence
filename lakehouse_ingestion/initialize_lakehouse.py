import os
import sys

def initialize_spark_lakehouse():
    """Attempts to initialize Apache Iceberg tables in MinIO using PySpark."""
    try:
        from pyspark.sql import SparkSession
        print("[INFO] PySpark detected. Initializing Spark Session with Iceberg & Project Nessie...")
        
        # Configure Spark with Apache Iceberg, AWS S3A, and Nessie jars
        spark = SparkSession.builder \
            .appName("LakehouseInitialization") \
            .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.4_2.12:0.73.0,software.amazon.awssdk:bundle:2.20.18") \
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions") \
            .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
            .config("spark.sql.catalog.nessie.uri", "http://localhost:19120/api/v1") \
            .config("spark.sql.catalog.nessie.ref", "main") \
            .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
            .config("spark.sql.catalog.nessie.warehouse", "s3a://lakehouse-warehouse") \
            .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9005") \
            .config("spark.hadoop.fs.s3a.access.key", "admin") \
            .config("spark.hadoop.fs.s3a.secret.key", "supersecretpassword") \
            .config("spark.hadoop.fs.s3a.path.style.access", "true") \
            .getOrCreate()
            
        print("[INFO] Creating Silver and Gold Iceberg tables...")
        
        # Create Silver Tables (Cleaned transactions and bets)
        spark.sql("""
            CREATE TABLE IF NOT EXISTS nessie.silver_bets (
                bet_id STRING,
                user_id STRING,
                event_name STRING,
                stake DOUBLE,
                odds DOUBLE,
                status STRING,
                profit_loss DOUBLE,
                settlement_time TIMESTAMP
            ) USING iceberg
        """)
        
        spark.sql("""
            CREATE TABLE IF NOT EXISTS nessie.silver_transactions (
                ref_number STRING,
                user_id STRING,
                type STRING,
                amount DOUBLE,
                method STRING,
                status STRING,
                datetime TIMESTAMP
            ) USING iceberg
        """)
        
        # Create Gold Tables (Aggregates)
        spark.sql("""
            CREATE TABLE IF NOT EXISTS nessie.gold_user_metrics (
                user_id STRING,
                total_bets LONG,
                win_rate DOUBLE,
                net_pnl DOUBLE,
                roi DOUBLE,
                last_updated TIMESTAMP
            ) USING iceberg
        """)
        
        print("[INFO] Lakehouse Iceberg schemas initialized successfully on MinIO.")
        spark.stop()
        return True
    except Exception as e:
        print(f"[WARNING] Spark Lakehouse initialization failed/unavailable: {e}")
        print("Falling back to local SQLite Lakehouse model...")
        return initialize_sqlite_lakehouse()

def initialize_sqlite_lakehouse():
    """Initializes local tables inside SQLite db acting as a lightweight Bronze/Silver/Gold store."""
    import sqlite3
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_lakehouse.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"[INFO] Creating tables in SQLite Lakehouse replica: {db_path}...")
        
        # Silver Bets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_bets (
                bet_id TEXT PRIMARY KEY,
                user_id TEXT,
                event_name TEXT,
                stake REAL,
                odds REAL,
                status TEXT,
                profit_loss REAL,
                settlement_time TEXT
            )
        """)
        
        # Silver Transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS silver_transactions (
                ref_number TEXT PRIMARY KEY,
                user_id TEXT,
                type TEXT,
                amount REAL,
                method TEXT,
                status TEXT,
                datetime TEXT
            )
        """)
        
        # Gold User Metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_user_metrics (
                user_id TEXT PRIMARY KEY,
                total_bets INTEGER,
                win_rate REAL,
                net_pnl REAL,
                roi REAL,
                last_updated TEXT
            )
        """)
        
        # Gold Payment Channel Metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gold_payment_channels (
                method TEXT PRIMARY KEY,
                total_transactions INTEGER,
                success_rate REAL,
                volume REAL
            )
        """)
        
        conn.commit()
        conn.close()
        print("[INFO] Local SQLite Lakehouse schema initialized successfully.")
        return True
    except Exception as sqle:
        print(f"[ERROR] Failed to initialize SQLite Lakehouse: {sqle}")
        return False

if __name__ == "__main__":
    initialize_spark_lakehouse()
