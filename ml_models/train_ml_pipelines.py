import os
import sqlite3
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

# ML imports
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, silhouette_score

# Setup directories
ML_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_DIR = os.path.join(ML_DIR, "registry")
os.makedirs(REGISTRY_DIR, exist_ok=True)

BACKEND_DB = os.path.join(os.path.dirname(ML_DIR), "backend", "app", "betting_lakehouse.db")

def load_ml_dataset():
    """Loads transaction records from the Lakehouse database to compile feature arrays."""
    if os.path.exists(BACKEND_DB):
        conn = sqlite3.connect(BACKEND_DB)
        try:
            df = pd.read_sql_query("SELECT * FROM silver_transactions", conn)
            conn.close()
            if not df.empty:
                print(f"[ML] Loaded {len(df)} records from backend DB.")
                return df
        except Exception:
            conn.close()
            
    # Mock data fallback for bootstrapping model training
    print("[ML] DB table not populated yet. Bootstrapping mock dataset...")
    np.random.seed(42)
    n_samples = 150
    
    amounts = np.random.exponential(scale=3000, size=n_samples)
    # Inject anomalies
    amounts[5] = 250000.0
    amounts[18] = 450000.0
    
    text_lengths = np.random.randint(10, 150, size=n_samples)
    has_upi = np.random.choice([0, 1], size=n_samples, p=[0.3, 0.7])
    has_bank = np.random.choice([0, 1], size=n_samples, p=[0.7, 0.3])
    has_crypto = np.random.choice([0, 1], size=n_samples, p=[0.9, 0.1])
    
    # Types: 1 for DEPOSIT, 0 for WITHDRAWAL
    types = np.random.choice([0, 1], size=n_samples, p=[0.4, 0.6])
    # Status: 1 for SUCCESS, 0 for FAILED
    status = np.random.choice([0, 1], size=n_samples, p=[0.1, 0.9])
    
    # Categories: 0 = UPI, 1 = Bank, 2 = Crypto
    categories = []
    for i in range(n_samples):
        if has_crypto[i] == 1:
            categories.append(2)
        elif has_bank[i] == 1:
            categories.append(1)
        else:
            categories.append(0)
            
    return pd.DataFrame({
        "amount": amounts,
        "text_length": text_lengths,
        "has_upi": has_upi,
        "has_bank": has_bank,
        "has_crypto": has_crypto,
        "type_num": types,
        "status_num": status,
        "category": categories
    })

def train_and_register_models():
    df = load_ml_dataset()
    
    # Derive category column if missing in loaded database dataset
    if "category" not in df.columns:
        categories = []
        for i in range(len(df)):
            if df["has_crypto"].iloc[i] == 1:
                categories.append(2)
            elif df["has_bank"].iloc[i] == 1:
                categories.append(1)
            else:
                categories.append(0)
        df["category"] = categories
        
    # 1. Feature Matrices
    X_clf = df[["amount", "text_length", "has_upi", "has_bank", "has_crypto"]]
    y_clf = df["category"]
    
    # ----------------------------------------------------
    # Model A: Random Forest Classifier (Category Router)
    # ----------------------------------------------------
    print("\n[ML] Training Random Forest Classifier...")
    X_train, X_test, y_train, y_test = train_test_split(X_clf, y_clf, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    
    # Evaluate Classifier
    print("Classifier Report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    
    # Save Classifier
    clf_path = os.path.join(REGISTRY_DIR, "payment_classifier.joblib")
    joblib.dump(clf, clf_path)
    print(f"[ML] Registered Random Forest: {clf_path}")

    # ----------------------------------------------------
    # Model B: Isolation Forest (Anomaly Boundary)
    # ----------------------------------------------------
    print("\n[ML] Training Isolation Forest Anomaly Detector...")
    # Features for anomaly: amount, transaction type, status
    if "type_num" not in df.columns:
        df["type_num"] = df["type"].apply(lambda x: 1.0 if str(x).upper() == "DEPOSIT" else 0.0) if "type" in df.columns else 1.0
    if "status_num" not in df.columns:
        df["status_num"] = df["status"].apply(lambda x: 1.0 if str(x).upper() == "SUCCESS" else 0.0) if "status" in df.columns else 1.0
        
    X_anom = df[["amount", "type_num", "status_num"]]
    
    # Define Isolation model with 3% expected contamination
    detector = IsolationForest(contamination=0.03, random_state=42)
    detector.fit(X_anom)
    
    # Evaluate Anomaly
    preds = detector.predict(X_anom)
    anomalies_count = list(preds).count(-1)
    print(f"Flagged Anomalies: {anomalies_count} out of {len(df)} records ({anomalies_count/len(df)*100:.2f}%)")
    
    # Save Anomaly Detector
    det_path = os.path.join(REGISTRY_DIR, "anomaly_detector.joblib")
    joblib.dump(detector, det_path)
    print(f"[ML] Registered Isolation Forest: {det_path}")

    # ----------------------------------------------------
    # Model C: K-Means Clustering (Performance Groups)
    # ----------------------------------------------------
    print("\n[ML] Training K-Means Clusterer...")
    X_cluster = df[["amount", "text_length"]]
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit(X_cluster)
    
    # Save Clustering Model
    cluster_path = os.path.join(REGISTRY_DIR, "clustering.joblib")
    joblib.dump(kmeans, cluster_path)
    print(f"[ML] Registered K-Means Clustering: {cluster_path}")

    # --- MLflow Logging Simulation ---
    log_mlflow_metadata(clf, detector, kmeans)

def log_mlflow_metadata(clf, detector, kmeans):
    """Simulates registering ML models in MLflow client registry."""
    mlflow_log_path = os.path.join(REGISTRY_DIR, "mlflow_run.json")
    metadata = {
        "experiment_name": "Betting_Data_Intelligence_MLOps",
        "run_id": str(np.random.randint(100000, 999999)),
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "random_forest_estimators": len(clf.estimators_),
            "isolation_forest_contamination": detector.contamination,
            "kmeans_inertia": float(kmeans.inertia_)
        },
        "registered_models": [
            {"name": "payment_classifier", "version": "1.0", "stage": "Production"},
            {"name": "anomaly_detector", "version": "1.0", "stage": "Production"},
            {"name": "clustering", "version": "1.0", "stage": "Production"}
        ]
    }
    with open(mlflow_log_path, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"[MLOps] Exported MLflow run parameters & metrics registry details to {mlflow_log_path}")

if __name__ == "__main__":
    train_and_register_models()
