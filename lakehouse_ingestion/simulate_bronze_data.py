import os
import json
import sqlite3

# Define paths
INGESTION_DIR = os.path.dirname(os.path.abspath(__file__))
BRONZE_DIR = os.path.join(INGESTION_DIR, "bronze")
MELBET_DB = os.path.join(INGESTION_DIR, "..", "melbet_analytics", "data", "melbet_analytics.db")
CRIC_JSON_DIR = os.path.join(INGESTION_DIR, "..", "10cric_analytics", "json")

def simulate():
    print("[INFO] Simulating Bronze data from existing scraper outputs...")
    
    # 1. Extract from Melbet SQLite Database
    if os.path.exists(MELBET_DB):
        try:
            conn = sqlite3.connect(MELBET_DB)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Extract Bets
            cursor.execute("SELECT * FROM bets")
            rows = cursor.fetchall()
            bets_dir = os.path.join(BRONZE_DIR, "melbet-bets")
            os.makedirs(bets_dir, exist_ok=True)
            for idx, r in enumerate(rows):
                data = dict(r)
                with open(os.path.join(bets_dir, f"sim_bet_{idx}.json"), "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            print(f"  - Simulated {len(rows)} Melbet bets inside 'bronze/melbet-bets/'")

            # Extract Deposits
            cursor.execute("SELECT * FROM deposits")
            rows = cursor.fetchall()
            dep_dir = os.path.join(BRONZE_DIR, "melbet-deposits")
            os.makedirs(dep_dir, exist_ok=True)
            for idx, r in enumerate(rows):
                data = dict(r)
                with open(os.path.join(dep_dir, f"sim_dep_{idx}.json"), "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            print(f"  - Simulated {len(rows)} Melbet deposits inside 'bronze/melbet-deposits/'")

            # Extract Withdrawals
            cursor.execute("SELECT * FROM withdrawals")
            rows = cursor.fetchall()
            wd_dir = os.path.join(BRONZE_DIR, "melbet-withdrawals")
            os.makedirs(wd_dir, exist_ok=True)
            for idx, r in enumerate(rows):
                data = dict(r)
                with open(os.path.join(wd_dir, f"sim_wd_{idx}.json"), "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            print(f"  - Simulated {len(rows)} Melbet withdrawals inside 'bronze/melbet-withdrawals/'")
            
            conn.close()
        except Exception as e:
            print(f"[WARNING] Failed to extract from Melbet DB: {e}")
    else:
        print("[WARNING] Melbet SQLite DB not found at path.")

    # 2. Extract from 10Cric JSON Files
    if os.path.exists(CRIC_JSON_DIR):
        cric_dir = os.path.join(BRONZE_DIR, "10cric-raw-data")
        os.makedirs(cric_dir, exist_ok=True)
        count = 0
        for f in os.listdir(CRIC_JSON_DIR):
            if f.endswith(".json") and f != "execution_summary.json":
                src_path = os.path.join(CRIC_JSON_DIR, f)
                with open(src_path, "r", encoding="utf-8") as sfile:
                    content = json.load(sfile)
                # Wrap inside a Kafka-like stream payload
                payload = {
                    "scraper": f.split("_")[0],
                    "data": content,
                    "timestamp": content.get("timestamp", "")
                }
                dest_path = os.path.join(cric_dir, f"sim_cric_{f}")
                with open(dest_path, "w", encoding="utf-8") as dfile:
                    json.dump(payload, dfile, indent=4)
                count += 1
        print(f"  - Simulated {count} 10Cric scraper records inside 'bronze/10cric-raw-data/'")
    else:
        print("[WARNING] 10Cric JSON directory not found.")
        
    print("[INFO] Simulation finished. Run 'python lakehouse_etl.py' now to process.")

if __name__ == "__main__":
    simulate()
