"""
FactShield — FastAPI Backend Entry Point
Run with: uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import connect_db, close_db, get_db
from models.claimmodel import seed_trusted_sources
from routes.verify import router as verify_router


# ─── LIFESPAN ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect DB + seed sources. Shutdown: close connection."""
    await connect_db()
    await seed_trusted_sources()
    print("[App] FactShield backend ready.")
    yield
    await close_db()
    print("[App] Shutdown complete.")


# ─── APP ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FactShield API",
    description="Multi-AI fact verification backed by peer-reviewed sources & MongoDB Atlas.",
    version="2.0.0",
    lifespan=lifespan,
)

# Allow the Streamlit frontend (and local dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",   # Streamlit default
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── ROUTES ───────────────────────────────────────────────────────────────────

app.include_router(verify_router, prefix="/api/verify", tags=["Verification"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "FactShield",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health", tags=["Health"])
async def health():
    """Ping MongoDB and confirm the service is alive."""
    try:
        db = get_db()
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    return {"status": "ok", "database": db_status}


@app.get("/api/stats", tags=["Stats"])
async def stats():
    """Return verdict distribution across all stored claims."""
    from claimmodel import get_verdict_stats
    verdicts = await get_verdict_stats()
    total = sum(verdicts.values())
    return {
        "total_claims_verified": total,
        "verdict_distribution": verdicts,
    }


# ─── DEV RUNNER ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)