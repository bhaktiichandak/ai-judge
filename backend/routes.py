from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from backend.llm import get_ai_response

# ── Router setup ──────────────────────────────────────
# Think of router as a mini app that handles /api routes
router = APIRouter()


# ── Request shape ─────────────────────────────────────
# This defines exactly what frontend must send us
class Message(BaseModel):
    role: str        # "user" or "assistant"
    content: str     # the actual message text

class ChatRequest(BaseModel):
    message: str                        # current user message
    history: Optional[List[Message]] = []  # previous messages
    model: Optional[str] = "groq"      # "groq" or "gemini"
    mode: Optional[str] = "judge"      # "judge", "feedback", "analyze", "compare"


# ── Response shape ────────────────────────────────────
# This defines exactly what we send back to frontend
class ChatResponse(BaseModel):
    reply: str             # AI response text
    model_used: str        # which model was used
    error: Optional[str] = None  # error message if any


# ── Health check endpoint ─────────────────────────────
# Used to verify backend is running
# Visit: http://localhost:8000/api/health
@router.get("/health")
def health_check():
    return {"status": "ok", "message": "AI Judge backend is running ⚖️"}


# ── Main chat endpoint ────────────────────────────────
# Frontend sends message here, gets AI response back
# URL: http://localhost:8000/api/chat
@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        # Convert history objects to plain dicts
        history_list = [
            {"role": msg.role, "content": msg.content}
            for msg in request.history
        ]

        # Call the AI (groq or gemini)
        reply = get_ai_response(
            user_message=request.message,
            history=history_list,
            model=request.model,
            mode=request.mode
        )

        return ChatResponse(
            reply=reply,
            model_used=request.model
        )

    except RuntimeError as e:
        # Return error cleanly instead of crashing
        return ChatResponse(
            reply="",
            model_used=request.model,
            error=str(e)
        )