import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.database import engine
from backend.app.models.models import Base
from backend.app.api.endpoints import router

# Initialize SQLAlchemy Tables on boot
try:
    print("[INIT] Booting Database connection. Syncing tables...")
    Base.metadata.create_all(bind=engine)
    print("[INIT] Database synced successfully.")
except Exception as e:
    print(f"[WARNING] Database sync failed (this is normal if PostgreSQL is offline/starting up): {e}")

app = FastAPI(
    title="Betting Platform Data Intelligence Lakehouse API",
    description="Backend API hosting RAG query routers, real-time ML anomaly evaluation, and multi-agent coordination metrics.",
    version="2.0.0"
)

# CORS configurations for React client connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount core API endpoints
app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "Data Intelligence Lakehouse Backend",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8085, reload=True)
