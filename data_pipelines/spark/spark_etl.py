import os
import sys
import json
import sqlite3
import pandas as pd
from datetime import datetime

# Setup directory references
STORAGE_DIR = os.path.dirname(os.path.abspath(__file__))
BRONZE_DIR = os.path.join(STORAGE_DIR, "bronze")
BACKEND_DB = os.path.join(os.path.dirname(os.path.dirname(STORAGE_DIR)), "backend", "app", "betting_lakehouse.db")

def run_spark_lakehouse_etl():
    """Initializes Spark Session with Iceberg / Nessie jars and writes partitioned Iceberg tables."""
    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import col, when, length, lit
        
        print("[SPARK] Initializing PySpark Session with Nessie & Iceberg integrations...")
        spark = SparkSession.builder \
            .appName("LakehouseIcebergETL") \
            .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.4_2.12:0.73.0") \
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

        print("[SPARK] Loading Bronze layer JSON records into Spark DataFrame...")
        # Read from partitioned Bronze directory
        df_bronze = spark.read.json(f"{BRONZE_DIR}/*/*.json")
        
        # --- Feature Engineering & Cleaning ---
        df_cleaned = df_bronze.filter(col("ref_number").isNotNull()) \
            .dropDuplicates(["ref_number"]) \
            .withColumn("amount", col("amount").cast("double")) \
            .withColumn("text_length", length(col("raw_text"))) \
            .withColumn("has_upi", when(col("raw_text").contains("@"), 1).otherwise(0)) \
            .withColumn("has_bank", when(col("raw_text").contains("IFSC"), 1).otherwise(0)) \
            .withColumn("has_crypto", when(col("raw_text").contains("0x"), 1).otherwise(0))
            
        print("[SPARK] Writing processed dataframe to silver_transactions Iceberg table...")
        df_cleaned.write \
            .format("iceberg") \
            .mode("append") \
            .save("nessie.silver_transactions")

        # Spark SQL Aggregations (Gold Layer)
        df_gold_channels = df_cleaned.groupBy("method") \
            .agg({"amount": "sum", "ref_number": "count"}) \
            .withColumnRenamed("sum(amount)", "volume") \
            .withColumnRenamed("count(ref_number)", "total_transactions")
            
        df_gold_channels.write \
            .format("iceberg") \
            .mode("overwrite") \
            .save("nessie.gold_payment_channels")
            
        print("[SPARK] Spark Iceberg ETL execution finished successfully.")
        spark.stop()
        
    except Exception as e:
        print(f"[INFO] PySpark catalog unavailable: {e}")
        print("[INFO] Executing local Pandas fallback ingestion pipeline...")
        run_pandas_fallback_etl()

def run_pandas_fallback_etl():
    """Fallback engine using Pandas and SQLite/PostgreSQL connectors to sync Bronze data."""
    # Ensure backend directory exists
    os.makedirs(os.path.dirname(BACKEND_DB), exist_ok=True)
    
    # Read from local SQLite for offline/mock development
    conn = sqlite3.connect(BACKEND_DB)
    cursor = conn.cursor()
    
    # Create tables if not exists
    cursor.execute("""
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
    """)
    
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
        
        # Keep required columns
        columns = ["ref_number", "user_id", "platform_name", "amount", "method", "type", "status", "text_length", "has_upi", "has_bank", "has_crypto"]
        for col in columns:
            if col not in df.columns:
                df[col] = "UNKNOWN" if col != "amount" and col != "text_length" else 0
                
        df = df[columns].drop_duplicates(subset=["ref_number"])
        
        # Upsert
        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO silver_transactions 
                    (ref_number, user_id, platform_name, amount, method, type, status, text_length, has_upi, has_bank, has_crypto, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["ref_number"], row["user_id"], row["platform_name"], row["amount"], 
                    row["method"], row["type"], row["status"], row["text_length"], 
                    row["has_upi"], row["has_bank"], row["has_crypto"], datetime.now().isoformat()
                ))
            except Exception as se:
                print(f"[ETL ERROR] Failed to save transaction row: {se}")
                
        conn.commit()
        print(f"[ETL SUCCESS] Ingested and updated {len(df)} transactions into Lakehouse.")
    else:
        print("[INFO] No Bronze data found to process.")
        
    conn.close()

if __name__ == "__main__":
    run_spark_lakehouse_etl()
