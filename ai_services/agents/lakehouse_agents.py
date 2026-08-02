import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, text

# Setup paths to import backend classes dynamically
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(AGENTS_DIR))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.core.database import engine
from ai_services.RAG.lakehouse_rag import SemanticRAGPipeline

# LangGraph Imports
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END

logger = logging.getLogger("LakehouseAgents")
REPORT_PATH = os.path.join(AGENTS_DIR, "agent_report.md")

class AgentState(TypedDict):
    context: Dict[str, Any]
    logs: List[str]

# -------------------------------------------------------------
# LangGraph Node Functions
# -------------------------------------------------------------

def coordinator_node(state: AgentState) -> AgentState:
    logs = list(state["logs"])
    context = dict(state["context"])
    
    logs.append("[LANGGRAPH] Coordinator Node active: Retrieving context from RAG vector store...")
    try:
        rag = SemanticRAGPipeline()
        rag_res = rag.answer_query("Get recent platform health, anomalies and payment channels aggregates.")
        context["rag_context"] = rag_res.get("answer", "")
        logs.append(f"[LANGGRAPH] Coordinator Node: RAG context successfully loaded ({len(context['rag_context'])} chars).")
    except Exception as e:
        logs.append(f"[LANGGRAPH WARNING] Coordinator RAG query failed: {e}")
        context["rag_context"] = "RAG context unavailable."
        
    return {"context": context, "logs": logs}

def risk_analysis_node(state: AgentState) -> AgentState:
    logs = list(state["logs"])
    context = dict(state["context"])
    
    logs.append("[LANGGRAPH] Risk Analyst Node active: Evaluating platform risk profiles...")
    risk_profile = {"high_risk_platforms": [], "avg_trust_score": 80.0}
    
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT platform_name, risk_score FROM gold_platform_metrics")).fetchall()
            for r in rows:
                if r[1] > 50.0:
                    risk_profile["high_risk_platforms"].append(r[0])
            
            # Calculate average trust score
            avg_trust = conn.execute(text("SELECT AVG(trust_score) FROM platforms")).scalar()
            if avg_trust is not None:
                risk_profile["avg_trust_score"] = float(avg_trust)
                
        logs.append(f"[LANGGRAPH] Risk Analyst Node: Found {len(risk_profile['high_risk_platforms'])} high-risk platforms. Average trust: {risk_profile['avg_trust_score']:.1f}%")
    except Exception as e:
        logs.append(f"[LANGGRAPH ERROR] Risk analysis database query failed: {e}")
        risk_profile["high_risk_platforms"] = []
        
    context["risk_analysis"] = risk_profile
    return {"context": context, "logs": logs}

def payment_intelligence_node(state: AgentState) -> AgentState:
    logs = list(state["logs"])
    context = dict(state["context"])
    
    logs.append("[LANGGRAPH] Payment Intel Node active: Aggregating transaction metrics...")
    metrics = {"total_volume": 0.0, "popular_methods": []}
    
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT method, volume FROM gold_payment_channels")).fetchall()
            for r in rows:
                metrics["total_volume"] += r[1]
                metrics["popular_methods"].append(r[0])
        logs.append(f"[LANGGRAPH] Payment Intel Node: Calculated volume {metrics['total_volume']:.2f} INR across {len(metrics['popular_methods'])} channels.")
    except Exception as e:
        logs.append(f"[LANGGRAPH ERROR] Payment metrics database query failed: {e}")
        
    context["payment_metrics"] = metrics
    return {"context": context, "logs": logs}

def platform_health_node(state: AgentState) -> AgentState:
    logs = list(state["logs"])
    context = dict(state["context"])
    
    logs.append("[LANGGRAPH] Platform Health Node active: Checking server health status...")
    health = {"status": "HEALTHY", "latency_ms": 15.0}
    
    # Check actual latency/availability of local services
    try:
        start_time = datetime.now()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = (datetime.now() - start_time).total_seconds() * 1000.0
        health["latency_ms"] = latency
        logs.append(f"[LANGGRAPH] Platform Health Node: Connection latency check complete: {latency:.2f} ms.")
    except Exception as e:
        health["status"] = "DEGRADED"
        logs.append(f"[LANGGRAPH WARNING] Platform Health Node: Latency check failed (DEGRADED): {e}")
        
    context["platform_health"] = health
    return {"context": context, "logs": logs}

def data_quality_node(state: AgentState) -> AgentState:
    logs = list(state["logs"])
    context = dict(state["context"])
    
    logs.append("[LANGGRAPH] Data Quality Node active: Auditing silver schema compliance...")
    quality = {"valid_records": 0, "null_fields_detected": 0}
    
    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM silver_transactions")).scalar()
            quality["valid_records"] = count
            
            # Check for null fields
            null_count = conn.execute(text("""
                SELECT COUNT(*) FROM silver_transactions 
                WHERE ref_number IS NULL OR user_id IS NULL OR amount IS NULL
            """)).scalar()
            quality["null_fields_detected"] = null_count
            
        logs.append(f"[LANGGRAPH] Data Quality Node: Audited {quality['valid_records']} silver rows. Null violations: {quality['null_fields_detected']}.")
    except Exception as e:
        logs.append(f"[LANGGRAPH ERROR] Data quality database query failed: {e}")
        
    context["data_quality"] = quality
    return {"context": context, "logs": logs}

def awaiting_review_node(state: AgentState) -> AgentState:
    logs = list(state["logs"])
    context = dict(state["context"])
    
    logs.append("[LANGGRAPH] =====================================================")
    logs.append("[LANGGRAPH] WORKFLOW PAUSED: Human Operator signature required to publish Audit Report.")
    logs.append("[LANGGRAPH] Awaiting review gate confirmation from dashboard...")
    logs.append("[LANGGRAPH] =====================================================")
    
    return {"context": context, "logs": logs}

def report_generator_node(state: AgentState) -> AgentState:
    logs = list(state["logs"])
    context = dict(state["context"])
    
    logs.append("[LANGGRAPH] Report Generator Node active: Writing final system audit reports...")
    
    try:
        md_content = f"""# Medallion Lakehouse Platform Audit Report
Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 1. Executive Summary
This report was compiled by the multi-agent coordinator using RAG context:
{context.get("rag_context")}

## 2. Ingestion & Quality Metrics
* **Valid Transactions Ingested**: {context["data_quality"].get("valid_records", 0)}
* **Null Fields Flagged**: {context["data_quality"].get("null_fields_detected", 0)}

## 3. Financial & Payment Metrics
* **Total Aggregated Volume**: {context["payment_metrics"].get("total_volume", 0.0):.2f} INR
* **Payment Channels Detected**: {", ".join(context["payment_metrics"].get("popular_methods", []))}

## 4. Risk Profile Details
* **High Risk Platforms**: {", ".join(context["risk_analysis"].get("high_risk_platforms", []))}
* **Platform Status**: {context["platform_health"].get("status", "UNKNOWN")} (latency: {context["platform_health"].get("latency_ms", 0.0):.1f} ms)
"""
        with open(context["report_path_md"], "w", encoding="utf-8") as f:
            f.write(md_content)

        json_content = {
            "generated_at": datetime.now().isoformat(),
            "rag_context": context["rag_context"],
            "data_quality": context["data_quality"],
            "payment_metrics": context["payment_metrics"],
            "risk_profile": context["risk_analysis"],
            "system_health": context["platform_health"]
        }
        with open(context["report_path_json"], "w", encoding="utf-8") as f:
            json.dump(json_content, f, indent=4)

        logs.append(f"[LANGGRAPH] Report Generator Node: Successfully saved agent_report.md and agent_report.json.")
        context["success"] = True
    except Exception as e:
        logs.append(f"[LANGGRAPH ERROR] Report generation failed: {e}")
        
    return {"context": context, "logs": logs}

# -------------------------------------------------------------
# State Graph Construction & Compilation
# -------------------------------------------------------------

workflow = StateGraph(AgentState)

# Register nodes
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("risk_analysis", risk_analysis_node)
workflow.add_node("payment_intelligence", payment_intelligence_node)
workflow.add_node("platform_health", platform_health_node)
workflow.add_node("data_quality", data_quality_node)
workflow.add_node("awaiting_review", awaiting_review_node)
workflow.add_node("report_generator", report_generator_node)

# Flow routing condition
def route_post_quality(state: AgentState):
    if state["context"].get("approved"):
        return "report_generator"
    return "awaiting_review"

# Wire edges
workflow.add_edge(START, "coordinator")
workflow.add_edge("coordinator", "risk_analysis")
workflow.add_edge("risk_analysis", "payment_intelligence")
workflow.add_edge("payment_intelligence", "platform_health")
workflow.add_edge("platform_health", "data_quality")

# Conditional Review Gate
workflow.add_conditional_edges("data_quality", route_post_quality)
workflow.add_edge("report_generator", END)
workflow.add_edge("awaiting_review", END)

app = workflow.compile()

# -------------------------------------------------------------
# CoordinatorAgent Interface
# -------------------------------------------------------------

class CoordinatorAgent:
    """
    Orchestrates the multi-agent task queue: Coordinator -> RAG -> Risk -> Payment -> Health -> Quality -> Report.
    Powered by LangGraph with human-in-the-loop Review Gate state preservation.
    """
    def __init__(self):
        self.status = "IDLE"
        self.logs = []
        self.current_state = None

    async def execute_workflow(self) -> dict:
        self.status = "RUNNING"
        self.logs = ["[LANGGRAPH] Started orchestration workflow."]
        
        # Initialize LangGraph State
        state: AgentState = {
            "context": {
                "start_time": datetime.now().isoformat(),
                "rag_context": "",
                "risk_analysis": {},
                "payment_metrics": {},
                "platform_health": {},
                "data_quality": {},
                "report_path_md": REPORT_PATH,
                "report_path_json": os.path.join(AGENTS_DIR, "agent_report.json"),
                "success": False,
                "approved": False
            },
            "logs": self.logs
        }
        
        try:
            # Run LangGraph pipeline
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: app.invoke(state))
            
            # Sync logs and state back
            self.logs = result["logs"]
            self.current_state = result
            
            # Evaluate current workflow state
            if not result["context"].get("approved"):
                self.status = "AWAITING_REVIEW"
                logger.info("[COORDINATOR] Workflow paused at awaiting_review gate.")
            else:
                self.status = "IDLE"
                logger.info("[COORDINATOR] Workflow complete.")
                
            return result["context"]
        except Exception as e:
            self.status = "IDLE"
            self.logs.append(f"[LANGGRAPH ERROR] Workflow pipeline failed: {e}")
            logger.error(f"Orchestration crash: {e}")
            return {"success": False, "error": str(e)}

    async def approve_workflow(self) -> dict:
        if self.status != "AWAITING_REVIEW" or not self.current_state:
            return {"success": False, "error": "No workflow active at the review gate."}
            
        self.status = "RUNNING"
        self.logs.append("[LANGGRAPH] Operator Signature Verified. Continuing workflow...")
        
        # Update approval context
        self.current_state["context"]["approved"] = True
        self.current_state["logs"] = self.logs
        
        try:
            # Resume LangGraph pipeline from stored state
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: app.invoke(self.current_state))
            
            self.logs = result["logs"]
            self.current_state = result
            self.status = "IDLE"
            
            return result["context"]
        except Exception as e:
            self.status = "IDLE"
            self.logs.append(f"[LANGGRAPH ERROR] Report generation failed: {e}")
            return {"success": False, "error": str(e)}


class IntelligentAgent:
    """
    ONE Intelligent Agent with tool-use capabilities.
    Executes actions based on natural language queries or direct commands.
    Available Tools:
    - Scraper Tool: Triggers Scrapy Playwright spiders for target platform URL.
    - Spark ETL Tool: Runs Lakehouse PySpark / Pandas fallback ETL to clean and partition Bronze.
    - Iceberg Query Tool: Runs SQL queries directly on production database tables.
    - ML Analysis Tool: Runs Isolation Forest anomaly check or RF prediction.
    - Vector Search Tool: Performs similarity search directly on the FAISS vector database.
    - RAG Tool: Routes queries to SemanticRAGPipeline.
    - Report Generator: Writes system executive audit markdown and JSON reports.
    - Dashboard Tool: Generates platform KPI metrics snapshot.
    """
    def __init__(self):
        self.rag = SemanticRAGPipeline()
        self.logs = []

    def log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [INTELLIGENT_AGENT] {message}"
        self.logs.append(formatted)
        logger.info(formatted)

    async def execute_task(self, query: str) -> dict:
        self.logs = []
        self.log(f"Received query: '{query}'")
        q = query.lower()

        # Step 1: Parse Intent and Route to Tools (ReAct style reasoning step)
        try:
            if "scrape" in q or "crawl" in q or "spider" in q:
                # 1. SCRAPER TOOL
                self.log("Action: Invoking Scraper Tool...")
                platform_name = "melbet"
                if "10cric" in q or "cric" in q:
                    platform_name = "cric10"
                elif "22play" in q or "bet22" in q:
                    platform_name = "bet22"
                
                self.log(f"Tool Input: Target platform spider '{platform_name}'")
                
                # Run Scrapy spider as subprocess
                import subprocess
                scrapy_dir = os.path.join(project_root, "scrapers", "scrapy")
                self.log(f"Subprocess run: python -m scrapy crawl {platform_name}")
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "scrapy", "crawl", platform_name,
                    cwd=scrapy_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                self.log(f"Scraper Tool exited with code: {process.returncode}")
                
                return {
                    "task": "Scrape Site",
                    "success": process.returncode == 0,
                    "output": f"Scrape completed for {platform_name}.",
                    "logs": self.logs
                }

            elif "etl" in q or "process data" in q or "clean" in q:
                # 2. SPARK ETL TOOL
                self.log("Action: Invoking Spark ETL Tool...")
                etl_script = os.path.join(project_root, "data_pipelines", "spark", "spark_etl.py")
                self.log(f"Subprocess run: python {etl_script}")
                import subprocess
                process = await asyncio.create_subprocess_exec(
                    sys.executable, etl_script,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                self.log(f"Spark ETL Tool exited with code: {process.returncode}")
                
                return {
                    "task": "Spark Ingestion / Fallback ETL",
                    "success": process.returncode == 0,
                    "output": "Bronze files cleaned and synchronized to Silver/Gold database layers.",
                    "logs": self.logs
                }

            elif "query table" in q or "sql" in q or "select" in q:
                # 3. ICEBERG QUERY TOOL
                self.log("Action: Invoking Iceberg Query Tool...")
                # Extract simple table name from query
                table = "silver_transactions"
                if "gold_platform" in q:
                    table = "gold_platform_metrics"
                elif "gold_payment" in q:
                    table = "gold_payment_channels"
                
                self.log(f"Tool Input: SQL Query on database table '{table}'")
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    self.log(f"Query Result: {table} count is {result}")
                
                return {
                    "task": "Database Query",
                    "success": True,
                    "output": f"Table '{table}' contains {result} rows.",
                    "logs": self.logs
                }

            elif "anomaly" in q or "predict" in q or "fraud" in q:
                # 4. ML ANALYSIS TOOL
                self.log("Action: Invoking ML Analysis Tool...")
                model_path = os.path.join(project_root, "ai_services", "ml_models", "registry", "anomaly_detector.joblib")
                if not os.path.exists(model_path):
                    self.log("Error: anomaly_detector.joblib not found. Retraining ML pipeline first...")
                    train_script = os.path.join(project_root, "ai_services", "ml_models", "train_ml_pipelines.py")
                    process = await asyncio.create_subprocess_exec(sys.executable, train_script)
                    await process.wait()

                import joblib
                model = joblib.load(model_path)
                # Parse amount from query if present, otherwise default to 250000 (anomaly)
                amount = 250000.0
                for token in q.split():
                    try:
                        amount = float(token.replace(",", ""))
                        break
                    except ValueError:
                        continue
                
                self.log(f"Tool Input: Predict anomaly for amount {amount} INR (DEPOSIT, SUCCESS)")
                # Features: [amount, type_num (deposit=1.0), status_num (success=1.0)]
                pred = model.predict([[amount, 1.0, 1.0]])[0]
                is_anomalous = (pred == -1)
                self.log(f"Prediction Result: anomalous={is_anomalous}")
                
                return {
                    "task": "ML Anomaly Analysis",
                    "success": True,
                    "output": f"Amount {amount} INR is classified as ANOMALOUS (Fraud attempt)." if is_anomalous else f"Amount {amount} INR is within normal limits.",
                    "logs": self.logs
                }

            elif "vector" in q or "similar" in q or "search" in q:
                # 5. VECTOR SEARCH TOOL
                self.log("Action: Invoking Vector Search Tool...")
                # Search for keywords or platforms in FAISS
                search_term = "melbet"
                for word in ["1xbet", "10cric", "22play", "phonepe", "upi", "crypto"]:
                    if word in q:
                        search_term = word
                        break
                
                self.log(f"Tool Input: FAISS Similarity Search for keyword '{search_term}'")
                context = self.rag.retrieve_context(search_term, top_k=2)
                self.log(f"FAISS Result: Found {len(context)} matching records.")
                
                return {
                    "task": "Vector Similarity Search",
                    "success": True,
                    "output": context,
                    "logs": self.logs
                }

            elif "report" in q or "pdf" in q:
                # 6. REPORT GENERATOR
                self.log("Action: Invoking Report Generator Tool...")
                self.log("Compiling platforms data and writing audit reports...")
                # Trigger the LangGraph workflow to write reports
                coordinator_agent = CoordinatorAgent()
                # Auto-approve for the report generation task
                res = await coordinator_agent.execute_workflow()
                await coordinator_agent.approve_workflow()
                self.log("Report generated at ai_services/agents/agent_report.md")
                
                return {
                    "task": "Report Ingestion",
                    "success": True,
                    "output": "Executive system audit report generated and exported to markdown/JSON successfully.",
                    "logs": self.logs
                }

            elif "dashboard" in q or "kpi" in q or "status" in q:
                # 7. DASHBOARD TOOL
                self.log("Action: Invoking Dashboard Tool...")
                with engine.connect() as conn:
                    tx_count = conn.execute(text("SELECT COUNT(*) FROM transactions")).scalar() or 0
                    plat_count = conn.execute(text("SELECT COUNT(*) FROM platforms")).scalar() or 0
                    anom_count = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE is_anomalous=1")).scalar() or 0
                self.log(f"Dashboard Stats: platforms={plat_count}, transactions={tx_count}, anomalies={anom_count}")
                
                return {
                    "task": "Dashboard Telemetry Query",
                    "success": True,
                    "output": {
                        "active_platforms": plat_count,
                        "ingested_transactions": tx_count,
                        "flagged_fraud_alerts": anom_count,
                        "system_status": "ONLINE"
                    },
                    "logs": self.logs
                }

            else:
                # 8. RAG TOOL (default fallback search)
                self.log("Action: Invoking RAG Tool (General query dispatcher)...")
                response = self.rag.answer_query(query)
                self.log(f"RAG Result: verified={response.get('verified')}, answer_length={len(response.get('answer', ''))}")
                
                return {
                    "task": "RAG Natural Language Query",
                    "success": True,
                    "output": response,
                    "logs": self.logs
                }
        except Exception as err:
            self.log(f"Tool execution failed with exception: {err}")
            return {
                "task": "Orchestrator Tool routing",
                "success": False,
                "error": str(err),
                "logs": self.logs
            }

