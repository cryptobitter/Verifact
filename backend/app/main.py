import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import time
import json
import logging
from collections import defaultdict
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.routes import auth_routes, analysis_routes
from app.database import Base, engine
import app.models

app = FastAPI(
    title="VERIFACT API",
    description="AI-powered clinical fracture radiology AI co-pilot & PACS diagnostic workstation",
    version="2.0.0",
)

# Robust CORS configuration
cors_origins = list(set(settings.cors_origins + [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000"
]))


# In-memory sliding window rate limiter
_request_history = defaultdict(list)
RATE_LIMIT_WINDOW_SEC = 60
MAX_REQUESTS_PER_WINDOW = 120

@app.middleware("http")
async def telemetry_and_rate_limit_middleware(request: Request, call_next):
    # Rate Limiting
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Prune old timestamps
    _request_history[client_ip] = [t for t in _request_history[client_ip] if now - t < RATE_LIMIT_WINDOW_SEC]
    if len(_request_history[client_ip]) >= MAX_REQUESTS_PER_WINDOW:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Maximum 120 requests per minute."}
        )
    _request_history[client_ip].append(now)

    # Telemetry
    t_start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

    # Structured JSON log
    log_record = {
        "event": "http_request",
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "client_ip": client_ip
    }
    # Print clean structured log line
    print(json.dumps(log_record))
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-migrate table columns on startup
# Ensure database schema is initialized
try:
    Base.metadata.create_all(bind=engine)
except Exception as _db_err:
    print(f"[WARN] Failed to verify DB schema at startup: {_db_err}")

# Mount static samples directory
samples_dir = Path(__file__).resolve().parent / "static" / "samples"
if samples_dir.is_dir():
    app.mount("/static/samples", StaticFiles(directory=str(samples_dir)), name="samples")


@app.get("/")
def root():
    return {
        "system": "VERIFACT",
        "description": "Verifact AI Clinical Orthopedic Expert PACS System",
        "status": "operational",
        "version": "2.0.0"
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {e}"

    from ml.inference import get_inference_engine
    engine = get_inference_engine()

    return {
        "status": "ok" if "unhealthy" not in db_status else "degraded",
        "system": "VERIFACT",
        "database": db_status,
        "model_loaded": engine.is_loaded,
        "model_version": engine.model_version,
        "storage": "operational"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[UNHANDLED EXCEPTION] {request.method} {request.url}: {exc}")
    origin = request.headers.get("origin")
    headers = {}
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "error": str(exc)},
        headers=headers,
    )

app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(analysis_routes.router, tags=["analysis"])
