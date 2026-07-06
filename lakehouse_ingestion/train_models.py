import os
import sqlite3
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, silhouette_score

# Setup directories
INGESTION_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(INGESTION_DIR, "local_lakehouse.db")
MODELS_DIR = os.path.join(INGESTION_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

def load_data():
    """Loads Silver layer data for feature engineering."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Lakehouse database not found at {DB_PATH}. Please run lakehouse_etl.py first.")
        
    conn = sqlite3.connect(DB_PATH)
    df_tx = pd.read_sql_query("SELECT * FROM silver_transactions", conn)
    df_bets = pd.read_sql_query("SELECT * FROM silver_bets", conn)
    conn.close()
    return df_tx, df_bets

def train_payment_classifier(df_tx):
    """Trains a Random Forest Classifier to predict high-level payment category from text/amount features."""
    print("\n--- 1. Training Payment Category Classifier ---")
    
    # Map method names to categories in real data
    df_real = pd.DataFrame()
    if not df_tx.empty:
        df_real = df_tx.copy()
        df_real["text"] = df_real["method"] + " " + df_real["ref_number"]
        def map_category(method):
            m = str(method).lower()
            if "upi" in m or "phonepe" in m or "paytm" in m:
                return "UPI"
            elif "bank" in m or "netbanking" in m or "imps" in m or "neft" in m:
                return "Bank Transfer"
            elif "usdt" in m or "crypto" in m or "btc" in m or "wallet" in m:
                return "Crypto"
            else:
                return "E-wallet"
        df_real["category"] = df_real["method"].apply(map_category)
        
    # Generate robust simulated baseline to ensure enough training samples
    sim_data = []
    for _ in range(50):
        # UPI
        sim_data.append({"text": "PhonePe UPI payment", "amount": np.random.uniform(500, 5000), "category": "UPI"})
        sim_data.append({"text": "Paytm QR scan", "amount": np.random.uniform(100, 2000), "category": "UPI"})
        # Bank Transfer
        sim_data.append({"text": "IMPS bank transfer to SBI", "amount": np.random.uniform(5000, 50000), "category": "Bank Transfer"})
        sim_data.append({"text": "NEFT transaction HDFC", "amount": np.random.uniform(10000, 100000), "category": "Bank Transfer"})
        # Crypto
        sim_data.append({"text": "USDT deposit trc20", "amount": np.random.uniform(2000, 15000), "category": "Crypto"})
        sim_data.append({"text": "BTC transfer wallet", "amount": np.random.uniform(5000, 80000), "category": "Crypto"})
    df_sim = pd.DataFrame(sim_data)
    
    # Combine real and simulated datasets
    if not df_real.empty:
        df_real_features = pd.DataFrame({
            "text": df_real["text"],
            "amount": df_real["amount"],
            "category": df_real["category"]
        })
        df_train = pd.concat([df_sim, df_real_features], ignore_index=True)
        print(f"[INFO] Combined {len(df_real_features)} real records with {len(df_sim)} simulated records.")
    else:
        df_train = df_sim
        print(f"[INFO] Using {len(df_sim)} simulated records for baseline training.")

    # Feature engineering: extract basic NLP metadata features
    df_train["text_length"] = df_train["text"].apply(lambda x: len(str(x)))
    df_train["has_upi"] = df_train["text"].apply(lambda x: 1.0 if "upi" in str(x).lower() or "qr" in str(x).lower() or "pay" in str(x).lower() else 0.0)
    df_train["has_bank"] = df_train["text"].apply(lambda x: 1.0 if "bank" in str(x).lower() or "imps" in str(x).lower() or "neft" in str(x).lower() or "sbi" in str(x).lower() else 0.0)
    df_train["has_crypto"] = df_train["text"].apply(lambda x: 1.0 if "usdt" in str(x).lower() or "crypto" in str(x).lower() or "btc" in str(x).lower() else 0.0)
    
    # Feature matrix X and target y
    features = ["amount", "text_length", "has_upi", "has_bank", "has_crypto"]
    X = df_train[features]
    y = df_train["category"]
    
    # Train-test split (20% test size)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Train Model
    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluate
    y_pred = clf.predict(X_test)
    print("Classification Evaluation Metrics:")
    print(classification_report(y_test, y_pred))
    
    # Save Model
    model_path = os.path.join(MODELS_DIR, "payment_classifier.joblib")
    joblib.dump(clf, model_path)
    print(f"[STORE] Trained Random Forest classifier saved to: {model_path}")

def train_anomaly_detector(df_tx):
    """Trains an Isolation Forest model to detect transaction anomalies (suspiciously high amounts/states)."""
    print("\n--- 2. Training Anomaly Detector (Isolation Forest) ---")
    
    # Prep baseline simulation
    normal_tx = [{"amount": np.random.uniform(500, 10000), "type_num": 1.0, "status_num": 1.0} for _ in range(95)]
    anomalous_tx = [
        {"amount": 150000.0, "type_num": 0.0, "status_num": 0.0}, # Huge failed withdrawal
        {"amount": 95000.0, "type_num": 1.0, "status_num": 0.0},  # Huge failed deposit
        {"amount": np.random.uniform(1000, 5000), "type_num": 1.0, "status_num": 0.0} # Failed deposit
    ]
    df_sim = pd.DataFrame(normal_tx + anomalous_tx)
    
    if not df_tx.empty:
        df_real = df_tx.copy()
        df_real["type_num"] = df_real["type"].apply(lambda x: 1.0 if str(x).upper() == "DEPOSIT" else 0.0)
        df_real["status_num"] = df_real["status"].apply(lambda x: 1.0 if str(x).upper() == "SUCCESS" else 0.0)
        
        df_real_features = df_real[["amount", "type_num", "status_num"]]
        df_model = pd.concat([df_sim, df_real_features], ignore_index=True)
        print(f"[INFO] Combined {len(df_real_features)} real records with {len(df_sim)} simulated records.")
    else:
        df_model = df_sim
        print(f"[INFO] Using {len(df_sim)} simulated records for anomaly baseline.")

    # Features: amount, transaction type, transaction status
    features = ["amount", "type_num", "status_num"]
    X = df_model[features]
    
    # Fit Isolation Forest
    iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    iso.fit(X)
    
    # Predict anomalies (-1 for anomaly, 1 for normal)
    preds = iso.predict(X)
    anomalies = df_model[preds == -1]
    
    print(f"Isolation Forest Analysis:")
    print(f"  - Total transactions evaluated: {len(X)}")
    print(f"  - Number of anomalies detected: {len(anomalies)}")
    if len(anomalies) > 0:
        print("  - Sample anomalous records:")
        print(anomalies.head(3)[["amount", "type_num", "status_num"]])
        
    # Save Model
    model_path = os.path.join(MODELS_DIR, "anomaly_detector.joblib")
    joblib.dump(iso, model_path)
    print(f"[STORE] Anomaly detector model saved to: {model_path}")

def train_payment_channel_clusters():
    """Applies K-Means clustering to group payment channels by transaction volume and success rate."""
    print("\n--- 3. Training Payment Channel Clusters (K-Means) ---")
    
    # Load aggregated payment channels from Gold layer
    conn = sqlite3.connect(DB_PATH)
    try:
        df_pc = pd.read_sql_query("SELECT * FROM gold_payment_channels", conn)
    except Exception:
        df_pc = pd.DataFrame()
    conn.close()
    
    # Baseline simulation data
    sim_data = [
        {"method": "GooglePay UPI", "total_transactions": 150, "success_rate": 96.5, "volume": 350000.0},
        {"method": "PhonePe UPI", "total_transactions": 220, "success_rate": 98.0, "volume": 560000.0},
        {"method": "SBI Netbanking", "total_transactions": 45, "success_rate": 88.2, "volume": 1200000.0},
        {"method": "HDFC Bank IMPS", "total_transactions": 30, "success_rate": 92.5, "volume": 950000.0},
        {"method": "USDT-TRC20 Wallet", "total_transactions": 85, "success_rate": 100.0, "volume": 2500000.0},
        {"method": "Failed-UPI-Terminal", "total_transactions": 15, "success_rate": 10.0, "volume": 15000.0},
        {"method": "Dormant-IMPS", "total_transactions": 2, "success_rate": 0.0, "volume": 2000.0}
    ]
    df_sim = pd.DataFrame(sim_data)
    
    if not df_pc.empty:
        df_model = pd.concat([df_sim, df_pc[["method", "total_transactions", "success_rate", "volume"]]], ignore_index=True)
        print(f"[INFO] Combined {len(df_pc)} real records with {len(df_sim)} simulated records.")
    else:
        df_model = df_sim
        print(f"[INFO] Using {len(df_sim)} simulated records for clustering baseline.")

    # Features: success rate, transaction count, total volume
    features = ["total_transactions", "success_rate", "volume"]
    X = df_model[features]
    
    # Scale features log-wise or normal-wise for distance-based clustering
    X_scaled = X.copy()
    X_scaled["volume"] = np.log1p(X_scaled["volume"])
    X_scaled["total_transactions"] = np.log1p(X_scaled["total_transactions"])
    X_scaled["success_rate"] = X_scaled["success_rate"] / 100.0  # Normalize percentage to [0,1]
    
    # Train K-Means (e.g. k=3 clusters: Highly Active/Success, Large Volume/Moderate Success, Low Performance)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    
    # Predict clusters
    df_model["cluster"] = kmeans.labels_
    
    print("K-Means Cluster Groupings:")
    for cluster_id in range(3):
        group = df_model[df_model["cluster"] == cluster_id]
        print(f"  Cluster {cluster_id} (Channels count={len(group)}):")
        print(f"    - Avg Transactions: {group['total_transactions'].mean():.1f}")
        print(f"    - Avg Success Rate: {group['success_rate'].mean():.1f}%")
        print(f"    - Avg Volume: {group['volume'].mean():.1f} INR")
        print(f"    - Methods: {', '.join(group['method'].tolist())}")
        
    # Silhouette score (if channels count > clusters count)
    if len(X_scaled) > 3:
        score = silhouette_score(X_scaled, kmeans.labels_)
        print(f"  Silhouette Score (Clustering Quality): {score:.4f}")
        
    # Save Model
    model_path = os.path.join(MODELS_DIR, "clustering.joblib")
    joblib.dump(kmeans, model_path)
    print(f"[STORE] K-Means clustering model saved to: {model_path}")

def run_ml_pipeline():
    print("=" * 60)
    print("MULTI-AGENT LAKEHOUSE ML TRAINING PIPELINE")
    print("=" * 60)
    
    try:
        df_tx, df_bets = load_data()
        
        # 1. Random Forest Classifier
        train_payment_classifier(df_tx)
        
        # 2. Anomaly Detection
        train_anomaly_detector(df_tx)
        
        # 3. K-Means Clustering
        train_payment_channel_clusters()
        
        print("\n" + "=" * 60)
        print("[INFO] All models trained, evaluated, and registered successfully.")

        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Machine Learning Pipeline failed: {e}")

if __name__ == "__main__":
    run_ml_pipeline()
