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
from ai_services.agents.lakehouse_agents import CoordinatorAgent

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Load models and RAG pipeline
rag_pipeline = SemanticRAGPipeline()
coordinator = CoordinatorAgent()

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
    return transaction_repository.get_multi(db, limit=100)

@router.get("/transactions/anomalies", response_model=List[schemas.TransactionResponse])
def get_anomalies(db: Session = Depends(get_db)):
    return transaction_repository.get_anomalies(db, limit=100)

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
