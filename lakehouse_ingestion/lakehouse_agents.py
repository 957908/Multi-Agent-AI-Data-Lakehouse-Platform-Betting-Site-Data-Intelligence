import os
import json
import asyncio
import joblib
from datetime import datetime

# Setup directories
INGESTION_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(INGESTION_DIR, "models", "anomaly_detector.joblib")
REPORT_PATH = os.path.join(INGESTION_DIR, "agent_report.md")

class AgentMessage:
    """Standard message envelope for async agent communication."""
    def __init__(self, sender: str, recipient: str, task_type: str, payload: dict):
        self.sender = sender
        self.recipient = recipient
        self.task_type = task_type
        self.payload = payload
        self.timestamp = datetime.now().isoformat()

# Registry to resolve target agent inboxes
AGENT_REGISTRY = {}

class BaseAgent:
    """Base agent implementing local inbox message queue handles."""
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
    """Simulates/Triggers data scraping and pushes raw events to target."""
    async def run(self):
        print(f"[INFO] [{self.name}] Agent started. Initializing scraping simulation...")
        await asyncio.sleep(0.5)
        
        # Simulate some standard raw transactions
        tx_data = [
            {"ref_number": "TXN_A101", "user_id": "4829103", "amount": 1200.0, "method": "PhonePe", "status": "SUCCESS", "type": "DEPOSIT"},
            {"ref_number": "TXN_B202", "user_id": "4829103", "amount": 800.0, "method": "UPI", "status": "SUCCESS", "type": "WITHDRAWAL"},
            {"ref_number": "TXN_C303", "user_id": "10CRIC_PUBLIC", "amount": 3500.0, "method": "UPI / NetBanking", "status": "SUCCESS", "type": "DEPOSIT"},
            # Injected Anomaly (Suspiciously huge amount)
            {"ref_number": "TXN_ANOMALY_999", "user_id": "4829103", "amount": 250000.0, "method": "UPI", "status": "FAILED", "type": "WITHDRAWAL"}
        ]
        
        for tx in tx_data:
            print(f"[INFO] [{self.name}] Scraped transaction event: {tx['ref_number']} (Amount: {tx['amount']} INR)")
            await self.send_message("ValidatorAgent", "raw_transaction", tx)
            await asyncio.sleep(0.1)
            
        print(f"[INFO] [{self.name}] Finished emission of raw scraper streams.")

class ValidatorAgent(BaseAgent):
    """Sanitizes raw scraper data fields and schema formats."""
    async def run(self):
        print(f"[INFO] [{self.name}] Agent started. Listening for raw events...")
        while True:
            msg = await self.inbox.get()
            if msg.task_type == "raw_transaction":
                payload = msg.payload
                print(f"[INFO] [{self.name}] Processing raw record {payload['ref_number']} from {msg.sender}")
                
                # Perform validation
                amount = float(payload.get("amount", 0.0))
                ref_num = str(payload.get("ref_number", "UNKNOWN"))
                
                # Sanitization complete
                clean_data = {
                    "ref_number": ref_num,
                    "user_id": str(payload.get("user_id", "GUEST")),
                    "amount": amount,
                    "method": str(payload.get("method", "Unknown")),
                    "status": str(payload.get("status", "PENDING")).upper(),
                    "type": str(payload.get("type", "DEPOSIT")).upper()
                }
                print(f"[INFO] [{self.name}] Validated successfully: {ref_num}")
                await self.send_message("AnomalyAgent", "validated_transaction", clean_data)
                await self.send_message("ReporterAgent", "record_processed", clean_data)
                    
            self.inbox.task_done()

class AnomalyAgent(BaseAgent):
    """Loads Isolation Forest model and evaluates transactions in real-time."""
    def __init__(self, name: str):
        super().__init__(name)
        self.model = None
        self.load_ml_model()

    def load_ml_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print(f"[INFO] [{self.name}] Successfully loaded trained Isolation Forest model.")
            except Exception as e:
                print(f"[WARNING] [{self.name}] Could not load ML model: {e}. Fallback to rule-based detection.")
        else:
            print(f"[WARNING] [{self.name}] Model file not found at {MODEL_PATH}. Using rule-based detection.")

    async def run(self):
        print(f"[INFO] [{self.name}] Agent started. Listening for validated transactions...")
        while True:
            msg = await self.inbox.get()
            if msg.task_type == "validated_transaction":
                tx = msg.payload
                print(f"[INFO] [{self.name}] Evaluating transaction {tx['ref_number']} for anomalies...")
                
                is_anomalous = False
                
                # 1. Try ML model inference
                if self.model is not None:
                    try:
                        type_num = 1.0 if tx["type"] == "DEPOSIT" else 0.0
                        status_num = 1.0 if tx["status"] == "SUCCESS" else 0.0
                        features = [[tx["amount"], type_num, status_num]]
                        
                        pred = self.model.predict(features)[0]
                        if pred == -1:
                            is_anomalous = True
                    except Exception as e:
                        print(f"[WARNING] [{self.name}] Model scoring error: {e}. Falling back to rule-based.")
                        
                # 2. Rule-based checks (if model fails or flags)
                if not is_anomalous and tx["amount"] > 50000.0:
                    is_anomalous = True
                    
                if is_anomalous:
                    alert_payload = {
                        "ref_number": tx["ref_number"],
                        "amount": tx["amount"],
                        "user_id": tx["user_id"],
                        "reason": "Suspicious transaction value detected by isolation boundary." if self.model else "Amount exceeds static safety limit (50,000 INR)"
                    }
                    print(f"[CRITICAL] [{self.name}] ANOMALY DETECTED: {tx['ref_number']} (Amount: {tx['amount']} INR)")
                    await self.send_message("ReporterAgent", "anomaly_alert", alert_payload)
                else:
                    print(f"[INFO] [{self.name}] Transaction {tx['ref_number']} passed anomaly check.")
                    
            self.inbox.task_done()

class ReporterAgent(BaseAgent):
    """Listens for statistics and anomaly alerts to compile execution summaries."""
    def __init__(self, name: str):
        super().__init__(name)
        self.records_processed = 0
        self.total_volume = 0.0
        self.anomalies_flagged = []

    async def run(self):
        print(f"[INFO] [{self.name}] Agent started. Listening for metrics...")
        while True:
            msg = await self.inbox.get()
            if msg.task_type == "record_processed":
                self.records_processed += 1
                self.total_volume += msg.payload["amount"]
            elif msg.task_type == "anomaly_alert":
                self.anomalies_flagged.append(msg.payload)
                print(f"[INFO] [{self.name}] Recorded anomaly alert for {msg.payload['ref_number']}.")
                    
            self.inbox.task_done()

    def generate_report(self):
        print(f"[INFO] [{self.name}] Compiling final Multi-Agent execution summary...")
        report = []
        report.append("# Multi-Agent Pipeline Execution Summary")
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append("## Core Statistics")
        report.append(f"- **Total Transactions Processed**: {self.records_processed}")
        report.append(f"- **Total Ingested Volume**: {self.total_volume:.2f} INR")
        report.append(f"- **Total Anomalies Flagged**: {len(self.anomalies_flagged)}\n")
        
        if self.anomalies_flagged:
            report.append("## Flagged Anomaly Details")
            for idx, a in enumerate(self.anomalies_flagged):
                report.append(f"### {idx+1}. Transaction Ref: `{a['ref_number']}`")
                report.append(f"- **User**: `{a['user_id']}`")
                report.append(f"- **Amount**: `{a['amount']:.2f} INR`")
                report.append(f"- **Risk Trigger**: {a['reason']}\n")
                
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
        print(f"[STORE] Final markdown summary report saved to: {REPORT_PATH}")

class IngestionOrchestrator:
    """Manages agent tasks and gracefully unblocks when all inboxes drain."""
    def __init__(self):
        self.scraper = ScraperAgent("ScraperAgent")
        self.validator = ValidatorAgent("ValidatorAgent")
        self.anomaly = AnomalyAgent("AnomalyAgent")
        self.reporter = ReporterAgent("ReporterAgent")

    async def execute(self):
        print("=" * 60)
        print("ASYNC MULTI-AGENT INGESTION ORCHESTRATION")
        print("=" * 60)
        
        # 1. Spin up consumer agents as background loops
        v_task = asyncio.create_task(self.validator.run())
        a_task = asyncio.create_task(self.anomaly.run())
        r_task = asyncio.create_task(self.reporter.run())
        
        # 2. Run scraper agent to emit messages
        await self.scraper.run()
        
        # 3. Wait for all inboxes to drain sequentially
        print("[INFO] [Orchestrator] Waiting for ValidatorAgent queue...")
        await self.validator.inbox.join()
        
        print("[INFO] [Orchestrator] Waiting for AnomalyAgent queue...")
        await self.anomaly.inbox.join()
        
        print("[INFO] [Orchestrator] Waiting for ReporterAgent queue...")
        await self.reporter.inbox.join()
        
        print("[INFO] [Orchestrator] All queues drained successfully.")
        
        # 4. Cancel background loops
        v_task.cancel()
        a_task.cancel()
        r_task.cancel()
        
        # 5. Compile reports
        self.reporter.generate_report()
        print("=" * 60)
        print("Multi-Agent orchestration finished cleanly.")
        print("=" * 60)

if __name__ == "__main__":
    orchestrator = IngestionOrchestrator()
    asyncio.run(orchestrator.execute())
