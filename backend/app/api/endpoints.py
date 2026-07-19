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
from rag_service.lakehouse_rag import SemanticRAGPipeline
from agents.lakehouse_agents import run_agent_orchestration

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Load models and RAG pipeline
rag_pipeline = SemanticRAGPipeline()

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
    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ml_models", "registry", "anomaly_detector.joblib")
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
# ASYNC AGENT RUNNER CONTROL
# ============================================================

def trigger_agent_run_sync():
    import asyncio
    asyncio.run(run_agent_orchestration())

@router.post("/agents/run")
def run_agents(background_tasks: BackgroundTasks):
    """Triggers the async Multi-Agent Actor Crew in a separate background thread."""
    background_tasks.add_task(trigger_agent_run_sync)
    return {"status": "triggered", "message": "Multi-agent simulation started in background."}

# ============================================================
# MODEL DIAGNOSTICS ENDPOINT
# ============================================================

@router.get("/model-diagnostics")
def get_diagnostics():
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ml_models", "registry")
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
