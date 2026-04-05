from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.llm import get_ai_response
from backend.mongo_store import is_mongo_configured, load_chat_session, save_chat_session


router = APIRouter()


class Message(BaseModel):
    role: str
    content: str
    hidden: bool = False
    sources: List[dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = Field(default_factory=list)
    model: Optional[str] = "consensus"
    mode: Optional[str] = "judge"
    session_id: Optional[str] = None


class SourceItem(BaseModel):
    claim: str
    title: str
    url: str
    snippet: str
    published: str
    source_type: str
    credibility_tier: str
    score: int
    relevance: int


class ChatResponse(BaseModel):
    reply: str
    model_used: str
    task_kind: Optional[str] = None
    sources: List[SourceItem] = Field(default_factory=list)
    session_id: Optional[str] = None
    storage_backend: str = "local"
    error: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    storage_backend: str = "local"


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "AI Judge backend is running",
        "storage_backend": "mongo" if is_mongo_configured() else "local",
    }


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str):
    messages = load_chat_session(session_id)
    return SessionResponse(
        session_id=session_id,
        messages=[Message(**message) for message in messages],
        storage_backend="mongo" if is_mongo_configured() else "local",
    )


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        history_list = [
            {
                "role": msg.role,
                "content": msg.content,
                "hidden": msg.hidden,
                "sources": msg.sources,
            }
            for msg in request.history
        ]

        result = get_ai_response(
            user_message=request.message,
            history=history_list,
            model=request.model,
            mode=request.mode,
        )

        full_messages = history_list + [
            {"role": "user", "content": request.message, "hidden": False, "sources": []},
            {
                "role": "assistant",
                "content": result.reply,
                "hidden": False,
                "sources": result.sources,
            },
        ]

        used_mongo = bool(request.session_id) and save_chat_session(request.session_id, full_messages)

        return ChatResponse(
            reply=result.reply,
            model_used=result.model_used,
            task_kind=result.task_kind,
            sources=result.sources,
            session_id=request.session_id,
            storage_backend="mongo" if used_mongo else "local",
        )

    except RuntimeError as e:
        return ChatResponse(
            reply="",
            model_used=request.model,
            session_id=request.session_id,
            storage_backend="mongo" if is_mongo_configured() else "local",
            error=str(e),
        )
