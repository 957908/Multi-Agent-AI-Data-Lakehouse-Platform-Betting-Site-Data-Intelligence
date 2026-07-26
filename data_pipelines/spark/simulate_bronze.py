import os
import json
import uuid
from datetime import datetime

STORAGE_DIR = os.path.dirname(os.path.abspath(__file__))
BRONZE_DIR = os.path.join(STORAGE_DIR, "bronze")
os.makedirs(BRONZE_DIR, exist_ok=True)

def simulate_bronze_records():
    print("[SIMULATOR] Generating raw transaction JSON logs inside Bronze layer...")
    
    # 1. 10Cric mock data
    cric_dir = os.path.join(BRONZE_DIR, "10cric-raw-data")
    os.makedirs(cric_dir, exist_ok=True)
    cric_data = [
        {"ref_number": "CRIC_TXN_0021", "user_id": "USER_CRIC_110", "platform_name": "10Cric", "amount": 15000.0, "method": "UPI / NetBanking", "type": "DEPOSIT", "status": "SUCCESS", "raw_text": "Deposit via standard UPI netbanking gateway"},
        {"ref_number": "CRIC_TXN_0022", "user_id": "USER_CRIC_110", "platform_name": "10Cric", "amount": 4500.0, "method": "UPI", "type": "WITHDRAWAL", "status": "SUCCESS", "raw_text": "Withdrawal processed back to client's VPA payee address: user@upi"}
    ]
    for idx, item in enumerate(cric_data):
        file_path = os.path.join(cric_dir, f"sim_cric_{idx}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(item, f, indent=4)

    # 2. Melbet mock data
    melbet_dir = os.path.join(BRONZE_DIR, "melbet-raw-data")
    os.makedirs(melbet_dir, exist_ok=True)
    melbet_data = [
        {"ref_number": "MEL_TXN_9988", "user_id": "USER_MEL_889", "platform_name": "Melbet", "amount": 7500.0, "method": "PhonePe", "type": "DEPOSIT", "status": "SUCCESS", "raw_text": "IMPS transfer matching reference MEL_TXN_9988"},
        {"ref_number": "MEL_TXN_ANOMALY", "user_id": "USER_MEL_889", "platform_name": "Melbet", "amount": 150000.0, "method": "UPI", "type": "DEPOSIT", "status": "SUCCESS", "raw_text": "Large amount flag trigger - check client info status"}
    ]
    for idx, item in enumerate(melbet_data):
        file_path = os.path.join(melbet_dir, f"sim_mel_{idx}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(item, f, indent=4)
            
    print(f"[SIMULATOR] Successfully populated mock files in {BRONZE_DIR}")

if __name__ == "__main__":
    simulate_bronze_records()
