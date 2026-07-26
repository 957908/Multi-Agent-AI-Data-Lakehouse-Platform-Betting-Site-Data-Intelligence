import os
import json
import asyncio
import joblib
from datetime import datetime

# Setup directories
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(os.path.dirname(AGENTS_DIR), "ml_models", "registry", "anomaly_detector.joblib")
REPORT_PATH = os.path.join(AGENTS_DIR, "agent_report.md")

class AgentMessage:
    def __init__(self, sender: str, recipient: str, task_type: str, payload: dict):
        self.sender = sender
        self.recipient = recipient
        self.task_type = task_type
        self.payload = payload
        self.timestamp = datetime.now().isoformat()

# Registry to resolve target agent inboxes
AGENT_REGISTRY = {}

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.inbox = asyncio.Queue()
        AGENT_REGISTRY[name] = self

    async def send_message(self, recipient: str, task_type: str, payload: dict):
        msg = AgentMessage(self.name, recipient, task_type, payload)
        if recipient in AGENT_REGISTRY:
            await AGENT_REGISTRY[recipient].inbox.put(msg)
        else:
            print(f"[WARNING] [{self.name}] Recipient '{recipient}' not found in registry.")

class ScraperAgent(BaseAgent):
    async def run(self):
        print(f"[INFO] [{self.name}] Started emission of raw scraper simulation...")
        await asyncio.sleep(0.5)
        
        # Simulate some standard raw transactions from dynamic crawls
        tx_data = [
            {"ref_number": "TXN_C101", "user_id": "4829103", "amount": 1500.0, "method": "PhonePe", "status": "SUCCESS", "type": "DEPOSIT", "platform_name": "Melbet"},
            {"ref_number": "TXN_C202", "user_id": "4829103", "amount": 900.0, "method": "UPI", "status": "SUCCESS", "type": "WITHDRAWAL", "platform_name": "Melbet"},
            {"ref_number": "TXN_C303", "user_id": "10CRIC_PUBLIC", "amount": 4200.0, "method": "UPI / NetBanking", "status": "SUCCESS", "type": "DEPOSIT", "platform_name": "10Cric"},
            # Extreme anomaly
            {"ref_number": "TXN_ANOMALY_999", "user_id": "4829103", "amount": 550000.0, "method": "UPI", "status": "FAILED", "type": "WITHDRAWAL", "platform_name": "10Cric"}
        ]
        
        for tx in tx_data:
            print(f"[INFO] [{self.name}] Emitting scraper event: {tx['ref_number']}")
            await self.send_message("ValidatorAgent", "raw_transaction", tx)
            await asyncio.sleep(0.2)

class ValidatorAgent(BaseAgent):
    async def run(self):
        print(f"[INFO] [{self.name}] Listening for raw events...")
        while True:
            msg = await self.inbox.get()
            if msg.task_type == "raw_transaction":
                payload = msg.payload
                print(f"[INFO] [{self.name}] Validating payload schema for {payload['ref_number']}")
                
                # Perform basic schema sanitization
                clean_data = {
                    "ref_number": str(payload.get("ref_number", "UNKNOWN")),
                    "user_id": str(payload.get("user_id", "GUEST")),
                    "amount": float(payload.get("amount", 0.0)),
                    "method": str(payload.get("method", "Unknown")),
                    "status": str(payload.get("status", "PENDING")).upper(),
                    "type": str(payload.get("type", "DEPOSIT")).upper(),
                    "platform_name": str(payload.get("platform_name", "Unknown"))
                }
                
                await self.send_message("AnomalyDetectorAgent", "validated_transaction", clean_data)
                await self.send_message("ReporterAgent", "record_processed", clean_data)
            self.inbox.task_done()

class AnomalyDetectorAgent(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name)
        self.model = None
        self.load_ml_model()

    def load_ml_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print(f"[INFO] [{self.name}] Successfully loaded Isolation Forest model.")
            except Exception as e:
                print(f"[WARNING] [{self.name}] Isolation Forest load failure: {e}. Fallback to static boundaries.")

    async def run(self):
        print(f"[INFO] [{self.name}] Listening for validated transactions...")
        while True:
            msg = await self.inbox.get()
            if msg.task_type == "validated_transaction":
                tx = msg.payload
                is_anomalous = False
                
                # 1. ML Scoring
                if self.model:
                    try:
                        type_num = 1.0 if tx["type"] == "DEPOSIT" else 0.0
                        status_num = 1.0 if tx["status"] == "SUCCESS" else 0.0
                        features = [[tx["amount"], type_num, status_num]]
                        pred = self.model.predict(features)[0]
                        if pred == -1:
                            is_anomalous = True
                    except Exception:
                        pass
                
                # 2. Rule based fallback check
                if not is_anomalous and tx["amount"] > 50000.0:
                    is_anomalous = True
                    
                if is_anomalous:
                    print(f"[CRITICAL] [{self.name}] ANOMALY DETECTED: {tx['ref_number']} for {tx['amount']} INR.")
                    alert = {
                        "ref_number": tx["ref_number"],
                        "amount": tx["amount"],
                        "platform": tx["platform_name"],
                        "reason": "Amount exceeds ML boundary / static limit."
                    }
                    await self.send_message("ReporterAgent", "anomaly_alert", alert)
                else:
                    print(f"[INFO] [{self.name}] Transaction {tx['ref_number']} passed validation limits.")
            self.inbox.task_done()

class ReporterAgent(BaseAgent):
    def __init__(self, name: str):
        super().__init__(name)
        self.processed = []
        self.anomalies = []

    async def run(self):
        print(f"[INFO] [{self.name}] Listening for platform events...")
        while True:
            msg = await self.inbox.get()
            if msg.task_type == "record_processed":
                self.processed.append(msg.payload)
            elif msg.task_type == "anomaly_alert":
                self.anomalies.append(msg.payload)
                self.generate_report_file()
            self.inbox.task_done()

    def generate_report_file(self):
        """Writes current compiled execution states as a clean markdown report."""
        report = f"""# Dynamic Multi-Agent Execution Summary

Report generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Ingestion Metrics
* **Total Transactions Crawled**: {len(self.processed)}
* **Anomalous Flags Raised**: {len(self.anomalies)}

## Flagged Anomalies Details
"""
        for a in self.anomalies:
            report += f"""
### [CRITICAL ALERT] {a['ref_number']}
* **Platform**: {a['platform']}
* **Amount**: {a['amount']} INR
* **Reason**: {a['reason']}
* **Risk Score Impact**: +35 points
"""
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[REPORTER] Compiled updated summary markdown report: {REPORT_PATH}")

async def run_agent_orchestration():
    # Instantiate agents
    scraper = ScraperAgent("ScraperAgent")
    validator = ValidatorAgent("ValidatorAgent")
    detector = AnomalyDetectorAgent("AnomalyDetectorAgent")
    reporter = ReporterAgent("ReporterAgent")
    
    # Spawn background task loops
    t_val = asyncio.create_task(validator.run())
    t_det = asyncio.create_task(detector.run())
    t_rep = asyncio.create_task(reporter.run())
    
    # Trigger scraper run
    await scraper.run()
    
    # Wait for processing queues to complete
    await asyncio.sleep(2)
    
    # Terminate background loops
    t_val.cancel()
    t_det.cancel()
    t_rep.cancel()

if __name__ == "__main__":
    asyncio.run(run_agent_orchestration())
