import os
import joblib
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lakehouse_rag import run_rag_pipeline, reindex_vector_store

app = FastAPI(
    title="Lakehouse Semantic RAG & Analytics API",
    description="REST API service providing semantic RAG searches and real-time ML anomaly prediction boundaries.",
    version="1.1"
)

# Enable CORS for frontend dashboard calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class AnomalyPredictRequest(BaseModel):
    amount: float
    type: str
    status: str

@app.get("/")
def root():
    return {
        "status": "active",
        "service": "Lakehouse RAG & ML Prediction Engine",
        "index_exists": os.path.exists(os.path.join(os.path.dirname(__file__), "vector_store", "faiss_index.index")),
        "model_exists": os.path.exists(os.path.join(os.path.dirname(__file__), "models", "anomaly_detector.joblib"))
    }

@app.post("/query")
def query_lakehouse(payload: QueryRequest):
    """Answers user query by retrieving relevant context and generating response."""
    try:
        response = run_rag_pipeline(payload.query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG execution failure: {str(e)}")

@app.post("/reindex")
def sync_vector_index():
    """Syncs the FAISS vector store with any updates in the SQLite database."""
    try:
        success = reindex_vector_store()
        if success:
            return {"status": "completed", "message": "FAISS vector store successfully synced with database."}
        else:
            raise HTTPException(status_code=500, detail="Reindexing failed. Check terminal logs.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindexing failure: {str(e)}")

@app.post("/predict-anomaly")
def predict_anomaly(payload: AnomalyPredictRequest):
    """Evaluates transaction metrics against the trained Isolation Forest model."""
    model_path = os.path.join(os.path.dirname(__file__), "models", "anomaly_detector.joblib")
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="Model binary anomaly_detector.joblib not found. Run train_models.py first.")
        
    try:
        # Load isolation model
        model = joblib.load(model_path)
        
        # Preprocess features
        type_num = 1.0 if payload.type.upper() == "DEPOSIT" else 0.0
        status_num = 1.0 if payload.status.upper() == "SUCCESS" else 0.0
        features = [[payload.amount, type_num, status_num]]
        
        # Predict: -1 for anomaly, 1 for normal
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
        raise HTTPException(status_code=500, detail=f"ML Prediction failure: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)
