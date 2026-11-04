from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.routes import auth_routes, analysis_routes
from app.database import Base, engine

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-migrate table columns on startup
try:
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        needed_cols = [
            ("heatmap_url", "TEXT"),
            ("displacement", "VARCHAR(100)"),
            ("confidence", "FLOAT"),
            ("clinical_notes", "TEXT"),
            ("signed_off", "BOOLEAN DEFAULT 0"),
            ("signed_by", "VARCHAR(255)"),
            ("signed_at", "DATETIME"),
            ("fracture_detected", "BOOLEAN DEFAULT 1"),
            ("lateral_image_url", "TEXT"),
            ("lateral_heatmap_url", "TEXT"),
            ("patient_id", "VARCHAR(50)"),
            ("patient_age", "INTEGER"),
            ("patient_gender", "VARCHAR(20)"),
            ("mechanism_of_injury", "VARCHAR(255)"),
            ("annotations", "TEXT"),
            ("email_sent_to", "VARCHAR(255)"),
            ("email_sent_at", "DATETIME"),
        ]
        for col_name, col_type in needed_cols:
            try:
                conn.execute(text(f"ALTER TABLE analyses ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            except Exception:
                pass  # column already exists
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
def health_check():
    return {"status": "ok", "system": "VERIFACT"}


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
