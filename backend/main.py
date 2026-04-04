from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import router

# ── Create the FastAPI app ────────────────────────────
app = FastAPI(
    title="AI Judge API",
    description="Backend for AI Judge — LLM powered evaluation engine",
    version="1.0.0"
)

# ── CORS Middleware ───────────────────────────────────
# This allows our Streamlit frontend to talk to this backend
# Without this, browser will block the requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allow all origins (fine for hackathon)
    allow_methods=["*"],      # Allow all HTTP methods
    allow_headers=["*"],      # Allow all headers
)

# ── Connect the routes ────────────────────────────────
# All routes from routes.py will be available under /api
# Example: /api/chat, /api/health
app.include_router(router, prefix="/api")


# ── Root endpoint ─────────────────────────────────────
# Visit http://localhost:8000 to confirm server is running
@app.get("/")
def root():
    return {
        "message": "Welcome to AI Judge API ⚖️",
        "docs": "Visit /docs to see all endpoints",
        "health": "Visit /api/health to check status"
    }