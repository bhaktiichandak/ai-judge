from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import json
from datetime import datetime

from routes.verify import router as verify_router
from routes.history import router as history_router
from routes.sources import router as sources_router
from database import connect_db, close_db

app = FastAPI(
    title="FactShield API",
    description="Multi-source AI-powered claim verification engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await connect_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

app.include_router(verify_router, prefix="/api/verify", tags=["Verification"])
app.include_router(history_router, prefix="/api/history", tags=["History"])
app.include_router(sources_router, prefix="/api/sources", tags=["Sources"])

@app.get("/health")
async def health():
    return {"status": "operational", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)