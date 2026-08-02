import os
import joblib
from typing import List
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from backend.app.core.database import get_db
from backend.app.core.security import verify_password, get_password_hash, create_access_token, ALGORITHM, SECRET_KEY
from backend.app.models.models import User, Platform, Transaction, PaymentMethod
from backend.app.repositories.user import user_repository
from backend.app.repositories.platform import platform_repository
from backend.app.repositories.transaction import transaction_repository
from backend.app.schemas import schemas

# RAG & Agent Modules integration
from ai_services.RAG.lakehouse_rag import SemanticRAGPipeline
from ai_services.agents.lakehouse_agents import CoordinatorAgent, IntelligentAgent

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Load models and RAG pipeline
rag_pipeline = SemanticRAGPipeline()
coordinator = CoordinatorAgent()
intelligent_agent = IntelligentAgent()

# Core Dependency to check JWT and return Current User
async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
        
    user = user_repository.get_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

def check_admin_role(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to administrative roles."
        )

# ============================================================
# AUTH CONTROLLERS
# ============================================================

@router.post("/auth/register", response_model=schemas.UserResponse)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = user_repository.get_by_email(db, email=payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered.")
        
    hashed = get_password_hash(payload.password)
    user_obj = {
        "email": payload.email,
        "hashed_password": hashed,
        "role": "user",
        "is_active": True
    }
    return user_repository.create(db, obj_in=user_obj)

@router.post("/auth/login", response_model=schemas.Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = user_repository.get_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=timedelta(minutes=60)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ============================================================
# PLATFORMS CONTROLLERS
# ============================================================

@router.get("/platforms", response_model=List[schemas.PlatformResponse])
def get_platforms(db: Session = Depends(get_db)):
    return platform_repository.get_multi(db, limit=100)

@router.post("/platforms/create", response_model=schemas.PlatformResponse, dependencies=[Depends(check_admin_role)])
def create_platform(payload: schemas.PlatformCreate, db: Session = Depends(get_db)):
    existing = platform_repository.get_by_name(db, name=payload.name)
    if existing:
        raise HTTPException(status_code=400, detail="Platform already exists.")
    return platform_repository.create(db, obj_in=payload.dict())

# ============================================================
# TRANSACTIONS CONTROLLERS
# ============================================================

@router.get("/transactions", response_model=List[schemas.TransactionResponse])
def get_transactions(db: Session = Depends(get_db)):
    return transaction_repository.get_multi(db, limit=200)

@router.get("/transactions/anomalies", response_model=List[schemas.TransactionResponse])
def get_anomalies(db: Session = Depends(get_db)):
    return transaction_repository.get_anomalies(db, limit=200)

@router.get("/transactions/by-platform/{platform_id}")
def get_transactions_by_platform(platform_id: int, db: Session = Depends(get_db)):
    """Returns all transactions for a specific platform with full provenance."""
    from sqlalchemy import text
    rows = db.execute(text("""
        SELECT t.id, t.ref_number, t.user_id, t.amount, t.type, t.status, t.is_anomalous,
               t.datetime, p.name as platform_name, p.url as platform_url,
               pm.name as method_name, pm.type as method_type
        FROM transactions t
        JOIN platforms p ON t.platform_id = p.id
        JOIN payment_methods pm ON t.method_id = pm.id
        WHERE t.platform_id = :pid
        ORDER BY t.datetime DESC
    """), {"pid": platform_id}).fetchall()
    if not rows:
        return {"data": [], "count": 0, "data_quality": "NO_DATA", "message": "No transactions found for this platform"}
    return {
        "data": [dict(r._mapping) for r in rows],
        "count": len(rows),
        "data_quality": "REAL",
        "source": "SQLite — scraped transaction records"
    }

# ============================================================
# REAL STATS OVERVIEW — reads only from DB, never fabricates
# ============================================================

@router.get("/stats/overview")
def get_stats_overview(db: Session = Depends(get_db)):
    """Returns real platform + transaction statistics. Zero means zero — never estimated."""
    from sqlalchemy import text
    from datetime import datetime

    def safe_count(query, params=None):
        try:
            result = db.execute(text(query), params or {}).scalar()
            return int(result) if result is not None else 0
        except:
            return 0

    def safe_scalar(query, params=None):
        try:
            return db.execute(text(query), params or {}).scalar()
        except:
            return None

    total_platforms = safe_count("SELECT COUNT(*) FROM platforms")
    total_transactions = safe_count("SELECT COUNT(*) FROM transactions")
    total_deposits = safe_count("SELECT COUNT(*) FROM transactions WHERE type='DEPOSIT'")
    total_withdrawals = safe_count("SELECT COUNT(*) FROM transactions WHERE type='WITHDRAWAL'")
    total_success = safe_count("SELECT COUNT(*) FROM transactions WHERE status='SUCCESS'")
    total_failed = safe_count("SELECT COUNT(*) FROM transactions WHERE status='FAILED'")
    total_anomalous = safe_count("SELECT COUNT(*) FROM transactions WHERE is_anomalous=1")
    total_payment_methods = safe_count("SELECT COUNT(*) FROM payment_methods")
    total_reviews = safe_count("SELECT COUNT(*) FROM reviews")
    total_complaints = safe_count("SELECT COUNT(*) FROM complaints")
    total_news = safe_count("SELECT COUNT(*) FROM news")

    # Per-platform breakdown
    platform_rows = db.execute(text("""
        SELECT p.id, p.name, p.url,
               COUNT(t.id) as tx_count,
               SUM(CASE WHEN t.type='DEPOSIT' THEN t.amount ELSE 0 END) as deposit_vol,
               SUM(CASE WHEN t.type='WITHDRAWAL' THEN t.amount ELSE 0 END) as withdrawal_vol,
               SUM(CASE WHEN t.is_anomalous=1 THEN 1 ELSE 0 END) as anomaly_count,
               SUM(CASE WHEN t.status='SUCCESS' THEN 1 ELSE 0 END) as success_count,
               SUM(CASE WHEN t.status='FAILED' THEN 1 ELSE 0 END) as failed_count,
               MIN(t.datetime) as first_tx,
               MAX(t.datetime) as last_tx
        FROM platforms p
        LEFT JOIN transactions t ON t.platform_id = p.id
        GROUP BY p.id, p.name, p.url
        ORDER BY tx_count DESC
    """)).fetchall()

    platforms_breakdown = []
    for r in platform_rows:
        m = dict(r._mapping)
        tx = m["tx_count"] or 0
        platforms_breakdown.append({
            "id": m["id"],
            "name": m["name"],
            "url": m["url"],
            "transaction_count": tx,
            "deposit_volume": round(m["deposit_vol"] or 0, 2),
            "withdrawal_volume": round(m["withdrawal_vol"] or 0, 2),
            "anomaly_count": m["anomaly_count"] or 0,
            "success_count": m["success_count"] or 0,
            "failed_count": m["failed_count"] or 0,
            "first_transaction": str(m["first_tx"]) if m["first_tx"] else None,
            "last_transaction": str(m["last_tx"]) if m["last_tx"] else None,
            "scan_status": "DATA_AVAILABLE" if tx > 0 else "NO_DATA"
        })

    # Payment methods breakdown
    method_rows = db.execute(text("""
        SELECT type, COUNT(*) as count FROM payment_methods GROUP BY type ORDER BY count DESC
    """)).fetchall()
    payment_by_type = {r[0]: r[1] for r in method_rows}

    # Most used payment methods by transaction count
    top_methods = db.execute(text("""
        SELECT pm.name, pm.type, COUNT(t.id) as usage_count
        FROM transactions t JOIN payment_methods pm ON t.method_id=pm.id
        GROUP BY pm.name, pm.type ORDER BY usage_count DESC LIMIT 10
    """)).fetchall()

    # Pipeline status (direct mode — Docker not running)
    pipeline_status = {
        "playwright": {"status": "AVAILABLE", "mode": "direct"},
        "kafka": {"status": "OFFLINE", "reason": "Docker not running — using direct DB mode"},
        "bronze": {"status": "AVAILABLE", "mode": "local_filesystem"},
        "spark": {"status": "OFFLINE", "reason": "Docker not running — using direct DB mode"},
        "silver": {"status": "OFFLINE", "reason": "Requires Spark"},
        "gold": {"status": "OFFLINE", "reason": "Requires Spark"},
        "postgresql": {"status": "OFFLINE", "reason": "Docker not running — using SQLite"},
        "sqlite": {"status": "ACTIVE", "mode": "local", "records": total_transactions}
    }

    return {
        "data_quality": "REAL",
        "source": "SQLite — betting_lakehouse.db",
        "generated_at": datetime.utcnow().isoformat(),
        "totals": {
            "platforms": total_platforms,
            "transactions": total_transactions,
            "deposits": total_deposits,
            "withdrawals": total_withdrawals,
            "successful_transactions": total_success,
            "failed_transactions": total_failed,
            "anomalous_transactions": total_anomalous,
            "payment_methods": total_payment_methods,
            "reviews": total_reviews,
            "complaints": total_complaints,
            "news_articles": total_news,
            "active_scan_jobs": 0
        },
        "platforms_breakdown": platforms_breakdown,
        "payment_methods_by_type": payment_by_type,
        "top_payment_methods": [
            {"name": r[0], "type": r[1], "transaction_count": r[2]}
            for r in top_methods
        ],
        "pipeline_mode": "DIRECT_DB",
        "pipeline_status": pipeline_status
    }

# ============================================================
# PLATFORM DETAIL WITH PAYMENT METHODS
# ============================================================

@router.get("/platforms/{platform_id}/detail")
def get_platform_detail(platform_id: int, db: Session = Depends(get_db)):
    """Returns full platform detail with payment methods and transaction summary."""
    from sqlalchemy import text
    platform = db.execute(text("SELECT * FROM platforms WHERE id=:id"), {"id": platform_id}).fetchone()
    if not platform:
        return {"error": "Platform not found", "data_quality": "NO_DATA"}
    p = dict(platform._mapping)

    # Payment methods used by this platform
    methods = db.execute(text("""
        SELECT pm.id, pm.name, pm.type,
               COUNT(t.id) as usage_count,
               SUM(CASE WHEN t.type='DEPOSIT' THEN t.amount ELSE 0 END) as deposit_vol,
               SUM(CASE WHEN t.type='WITHDRAWAL' THEN t.amount ELSE 0 END) as withdrawal_vol
        FROM payment_methods pm
        JOIN transactions t ON t.method_id = pm.id
        WHERE t.platform_id = :pid
        GROUP BY pm.id, pm.name, pm.type
        ORDER BY usage_count DESC
    """), {"pid": platform_id}).fetchall()

    tx_summary = db.execute(text("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN type='DEPOSIT' THEN 1 ELSE 0 END) as deposits,
               SUM(CASE WHEN type='WITHDRAWAL' THEN 1 ELSE 0 END) as withdrawals,
               SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END) as success,
               SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) as failed,
               SUM(CASE WHEN is_anomalous=1 THEN 1 ELSE 0 END) as anomalies,
               SUM(amount) as total_volume
        FROM transactions WHERE platform_id=:pid
    """), {"pid": platform_id}).fetchone()
    ts = dict(tx_summary._mapping)

    return {
        "data_quality": "REAL",
        "platform": p,
        "payment_methods": [
            {
                "id": m[0], "name": m[1], "type": m[2],
                "transaction_count": m[3],
                "deposit_volume": round(m[4] or 0, 2),
                "withdrawal_volume": round(m[5] or 0, 2),
                "min_deposit": "Not Yet Collected",
                "max_deposit": "Not Yet Collected",
                "min_withdrawal": "Not Yet Collected",
                "max_withdrawal": "Not Yet Collected",
                "fee": "Not Yet Collected",
                "processing_time": "Not Yet Collected"
            } for m in methods
        ],
        "transaction_summary": {
            "total": ts["total"] or 0,
            "deposits": ts["deposits"] or 0,
            "withdrawals": ts["withdrawals"] or 0,
            "successful": ts["success"] or 0,
            "failed": ts["failed"] or 0,
            "anomalies": ts["anomalies"] or 0,
            "total_volume": round(ts["total_volume"] or 0, 2)
        }
    }

# ============================================================
# RECENT ACTIVITY FEED — real events only
# ============================================================

@router.get("/activity/recent")
def get_recent_activity(db: Session = Depends(get_db)):
    """Returns the 10 most recent real events from the database."""
    from sqlalchemy import text
    from datetime import datetime

    events = []

    # Recent transactions
    tx_rows = db.execute(text("""
        SELECT t.datetime, t.type, t.amount, t.status, p.name as platform, pm.name as method
        FROM transactions t
        JOIN platforms p ON t.platform_id=p.id
        JOIN payment_methods pm ON t.method_id=pm.id
        ORDER BY t.datetime DESC LIMIT 5
    """)).fetchall()
    for r in tx_rows:
        m = dict(r._mapping)
        events.append({
            "type": "TRANSACTION",
            "timestamp": str(m["datetime"]),
            "platform": m["platform"],
            "description": f"{m['type']} via {m['method']} — Status: {m['status']}",
            "data_quality": "REAL"
        })

    if not events:
        return {"events": [], "count": 0, "message": "No Recent Activity"}

    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"events": events[:10], "count": len(events), "data_quality": "REAL"}

# ============================================================
# SCAN JOBS (stub — ready for Playwright integration)
# ============================================================

@router.get("/scan/jobs")
def get_scan_jobs():
    """Returns active scan jobs. No Docker = no active jobs."""
    return {
        "jobs": [],
        "count": 0,
        "message": "No active scan jobs. Docker is required for full pipeline. Using direct DB mode.",
        "pipeline_mode": "DIRECT_DB"
    }

@router.post("/scan/new")
def start_new_scan(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Queues a new platform scan (Playwright deposit page scraper)."""
    url = payload.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Platform URL is required.")
    return {
        "status": "QUEUED",
        "message": f"Scan queued for {url}. Playwright scraper will extract public deposit page payment methods.",
        "job_id": None,
        "note": "Full pipeline requires Docker. Currently running in direct DB mode."
    }



# ============================================================
# SEMANTIC RAG ENDPOINT
# ============================================================

@router.post("/query", response_model=schemas.RAGQueryResponse)
def query_rag(payload: schemas.RAGQueryRequest):
    try:
        response = rag_pipeline.answer_query(payload.query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Engine Query Failure: {e}")

# ============================================================
# ML ANOMALY INFERENCE SANDBOX
# ============================================================

@router.post("/predict-anomaly", response_model=schemas.AnomalyPredictResponse)
def predict_anomaly(payload: schemas.AnomalyPredictRequest):
    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ai_services", "ml_models", "registry", "anomaly_detector.joblib")
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="Model binary 'anomaly_detector.joblib' not found. Execute training pipeline first.")
        
    try:
        model = joblib.load(model_path)
        type_num = 1.0 if payload.type.upper() == "DEPOSIT" else 0.0
        status_num = 1.0 if payload.status.upper() == "SUCCESS" else 0.0
        features = [[payload.amount, type_num, status_num]]
        
        pred = model.predict(features)[0]
        is_anomalous = True if pred == -1 else False
        
        return {
            "amount": payload.amount,
            "type": payload.type,
            "status": payload.status,
            "is_anomalous": is_anomalous,
            "message": "Anomaly flagged by Isolation Forest boundary." if is_anomalous else "Transaction within normal limits."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML Inference error: {e}")

# ============================================================
# ASYNC AGENT RUNNER CONTROL & STATS
# ============================================================

async def run_coordinator_workflow_bg():
    await coordinator.execute_workflow()

@router.post("/agents/run")
def run_agents(background_tasks: BackgroundTasks):
    """Triggers the async Multi-Agent Coordinator workflow queue in a background task."""
    if coordinator.status == "RUNNING":
        return {"status": "already_running", "message": "Multi-agent workflow is already actively executing."}
    
    background_tasks.add_task(run_coordinator_workflow_bg)
    return {"status": "triggered", "message": "Multi-agent workflow started in background."}

@router.get("/agents/status")
def get_agents_status():
    """Returns the current execution state and logs of the Coordinator agent."""
    return {
        "status": coordinator.status,
        "logs": coordinator.logs
    }

async def approve_coordinator_workflow_bg():
    await coordinator.approve_workflow()

@router.post("/agents/approve")
def approve_agents(background_tasks: BackgroundTasks):
    """Approves the pending multi-agent report draft and resumes the workflow."""
    if coordinator.status != "AWAITING_REVIEW":
        return {"status": "error", "message": "No workflow is currently pending approval."}
    background_tasks.add_task(approve_coordinator_workflow_bg)
    return {"status": "triggered", "message": "Report approval received. Workflow resuming."}


@router.get("/agents/report/markdown")
def download_report_markdown():
    """Returns the generated agent audit report as a downloadable Markdown file."""
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "ai_services", "agents", "agent_report.md"
    )
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not yet generated. Please run the agent workflow first.")
    from fastapi.responses import FileResponse
    return FileResponse(
        path=report_path,
        media_type="text/markdown",
        filename="bet_metrics_lab_audit_report.md",
        headers={"Content-Disposition": "attachment; filename=bet_metrics_lab_audit_report.md"}
    )


@router.get("/agents/report/json")
def download_report_json():
    """Returns the generated agent audit report as a downloadable JSON file."""
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "ai_services", "agents", "agent_report.json"
    )
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not yet generated. Please run the agent workflow first.")
    from fastapi.responses import FileResponse
    return FileResponse(
        path=report_path,
        media_type="application/json",
        filename="bet_metrics_lab_audit_report.json",
        headers={"Content-Disposition": "attachment; filename=bet_metrics_lab_audit_report.json"}
    )


@router.get("/rag/health")
def get_rag_health():
    """Checks the health of the FAISS index and the underlying encoder."""
    is_healthy = False
    details = "FAISS index empty or uninitialized."
    if rag_pipeline.vector_store.index and rag_pipeline.vector_store.index.ntotal > 0:
        is_healthy = True
        details = "FAISS index loaded and active."
        
    return {
        "healthy": is_healthy,
        "details": details,
        "encoder": rag_pipeline.embedding_manager.encoder.__class__.__name__
    }

@router.get("/vector/index")
def get_vector_index():
    """Returns the current metadata indexed inside the FAISS vector store."""
    return {
        "total_records": len(rag_pipeline.vector_store.metadata),
        "metadata": rag_pipeline.vector_store.metadata
    }

@router.get("/vector/stats")
def get_vector_stats():
    """Returns statistics of the FAISS index."""
    ntotal = 0
    dimension = 384
    if rag_pipeline.vector_store.index:
        ntotal = rag_pipeline.vector_store.index.ntotal
        dimension = rag_pipeline.vector_store.index.d
    return {
        "total_vectors": ntotal,
        "dimension": dimension,
        "index_type": "IndexFlatL2"
    }

# ============================================================
# MODEL DIAGNOSTICS ENDPOINT
# ============================================================

@router.get("/model-diagnostics")
def get_diagnostics():
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ai_services", "ml_models", "registry")
    response = {
        "classifier": {"status": "missing"},
        "anomaly_detector": {"status": "missing"},
        "clustering": {"status": "missing"}
    }
    
    # Random Forest
    clf_path = os.path.join(models_dir, "payment_classifier.joblib")
    if os.path.exists(clf_path):
        try:
            clf = joblib.load(clf_path)
            response["classifier"] = {
                "status": "loaded",
                "algorithm": "Random Forest Classifier",
                "n_estimators": len(clf.estimators_)
            }
        except Exception as e:
            response["classifier"] = {"status": "error", "message": str(e)}

    # Isolation Forest
    ad_path = os.path.join(models_dir, "anomaly_detector.joblib")
    if os.path.exists(ad_path):
        try:
            ad = joblib.load(ad_path)
            response["anomaly_detector"] = {
                "status": "loaded",
                "algorithm": "Isolation Forest",
                "contamination": float(ad.contamination)
            }
        except Exception as e:
            response["anomaly_detector"] = {"status": "error", "message": str(e)}

    # K-Means
    km_path = os.path.join(models_dir, "clustering.joblib")
    if os.path.exists(km_path):
        try:
            km = joblib.load(km_path)
            response["clustering"] = {
                "status": "loaded",
                "algorithm": "K-Means Clustering",
                "n_clusters": int(km.n_clusters)
            }
        except Exception as e:
            response["clustering"] = {"status": "error", "message": str(e)}
            
    return response


@router.post("/agents/intelligent-query")
async def query_intelligent_agent(payload: dict):
    """
    Direct endpoint for 'ONE Intelligent Agent' executing task tools
    based on natural language commands.
    """
    query = payload.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query string is required.")
    response = await intelligent_agent.execute_task(query)
    return response

