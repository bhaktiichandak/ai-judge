from __future__ import annotations

import os
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError


env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


DEFAULT_DB_NAME = "ai_judge"
DEFAULT_COLLECTION_NAME = "chat_sessions"
DEFAULT_TIMEOUT_MS = 3000


def is_mongo_configured() -> bool:
    return bool(os.getenv("MONGODB_URI"))


@lru_cache(maxsize=1)
def get_chat_collection() -> Collection | None:
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        return None

    db_name = os.getenv("MONGODB_DB_NAME", DEFAULT_DB_NAME)
    collection_name = os.getenv("MONGODB_COLLECTION_NAME", DEFAULT_COLLECTION_NAME)
    timeout_ms = int(os.getenv("MONGODB_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS)))

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=timeout_ms, connectTimeoutMS=timeout_ms, socketTimeoutMS=timeout_ms)
        collection = client[db_name][collection_name]
        collection.create_index("session_id", unique=True)
        collection.create_index("updated_at")
        return collection
    except PyMongoError:
        return None


def normalize_message(message: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "role": message.get("role", "assistant"),
        "content": message.get("content", ""),
        "hidden": bool(message.get("hidden", False)),
        "sources": list(message.get("sources") or []),
    }
    return normalized


def save_chat_session(session_id: str, messages: list[dict[str, Any]]) -> bool:
    collection = get_chat_collection()
    if collection is None or not session_id:
        return False

    now = datetime.now(UTC)
    payload = [normalize_message(message) for message in messages]

    try:
        collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "messages": payload,
                    "message_count": len(payload),
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "session_id": session_id,
                    "created_at": now,
                },
            },
            upsert=True,
        )
        return True
    except PyMongoError:
        return False


def load_chat_session(session_id: str) -> list[dict[str, Any]]:
    collection = get_chat_collection()
    if collection is None or not session_id:
        return []

    try:
        document = collection.find_one({"session_id": session_id}, {"_id": 0, "messages": 1})
    except PyMongoError:
        return []

    if not document:
        return []

    messages = document.get("messages") or []
    return [normalize_message(message) for message in messages]
