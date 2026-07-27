import os
import uuid
import time
import logging
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.app.core.database import engine, get_db
from backend.app.models.models import Base
from backend.app.api.endpoints import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

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

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Latency logging middleware
@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    start_time = time.time()
    response: Response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    
    # Add standard security headers
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - ID: {request_id} - Time: {process_time:.4f}s")
    return response

# Mount core API endpoints
app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "service": "Data Intelligence Lakehouse Backend",
        "version": "2.0.0"
    }

# -------------------------------------------------------------
# Health & Diagnostic Endpoints (Task 4)
# -------------------------------------------------------------

@app.get("/health")
def healthcheck():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/health/live")
def liveness():
    return {"status": "alive", "timestamp": time.time()}

@app.get("/health/ready")
def readiness(response: Response):
    # Verify DB connectivity
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        response.status_code = 503
        return {"status": "unready", "database": "disconnected", "error": str(e)}

@app.on_event("shutdown")
def graceful_shutdown():
    logger.info("[SHUTDOWN] Executing graceful shutdown procedures...")
    try:
        engine.dispose()
        logger.info("[SHUTDOWN] Database engines successfully closed.")
    except Exception as e:
        logger.error(f"Error disposing database connections: {e}")

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8085, reload=True)
