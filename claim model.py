"""
MongoDB Atlas Data Models
Collections:
  - claims       : every verification request + result
  - evidence     : individual evidence items linked to claims
  - sources      : trusted source registry (pre-seeded)
  - sessions     : user sessions
"""

from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from bson import ObjectId

# ─── PYDANTIC MODELS ──────────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    source_key: str
    source_label: str
    trust_score: float
    title: str
    abstract: Optional[str] = ""
    url: Optional[str] = ""
    doi: Optional[str] = ""
    pmid: Optional[str] = ""
    year: Optional[str] = ""
    journal: Optional[str] = ""
    authors: Optional[List[str]] = []
    category: str
    relevance_score: Optional[float] = 0.0
    relevance_reason: Optional[str] = ""
    citation_count: Optional[int] = 0
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class VerificationResult(BaseModel):
    verdict: str                  # TRUE | FALSE | PARTIALLY_TRUE | MISLEADING | UNVERIFIABLE
    confidence: float             # 0.0 - 1.0
    ensemble_agreement: float     # fraction of models that agreed
    reasoning: str
    all_reasonings: List[str] = []
    key_facts: List[str] = []
    nuances: str = ""
    models_used: List[str] = []
    source_credibility_score: float = 0.0
    supporting_sources: List[str] = []
    contradicting_sources: List[str] = []

class ClaimDocument(BaseModel):
    """Main MongoDB document stored in `claims` collection."""
    claim_text: str
    original_input: str
    category: str = "general"
    complexity: str = "moderate"
    verdict: str = "UNVERIFIABLE"
    confidence: float = 0.0
    ensemble_agreement: float = 0.0
    reasoning: str = ""
    key_facts: List[str] = []
    nuances: str = ""
    models_used: List[str] = []
    source_credibility_score: float = 0.0
    evidence_count: int = 0
    academic_evidence_count: int = 0
    evidence_summary: List[Dict] = []   # top 5 evidence items (lightweight)
    session_id: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict = {}

class SessionDocument(BaseModel):
    session_id: str
    claims_verified: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

# ─── DATABASE OPERATIONS ─────────────────────────────────────────────────────

from database import get_db

async def save_claim(claim_doc: dict) -> str:
    """Insert a claim document, return inserted ID."""
    db = get_db()
    claim_doc["created_at"] = datetime.utcnow()
    result = await db.claims.insert_one(claim_doc)
    return str(result.inserted_id)

async def save_evidence_batch(evidence_list: List[dict], claim_id: str) -> None:
    """Save full evidence list linked to a claim."""
    db = get_db()
    for ev in evidence_list:
        ev["claim_id"] = claim_id
        ev["retrieved_at"] = datetime.utcnow()
    if evidence_list:
        await db.evidence.insert_many(evidence_list)

async def get_claim_history(limit: int = 20, skip: int = 0) -> List[dict]:
    db = get_db()
    cursor = db.claims.find(
        {},
        {"claim_text": 1, "verdict": 1, "confidence": 1, "created_at": 1,
         "category": 1, "source_credibility_score": 1, "evidence_count": 1}
    ).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs

async def get_claim_by_id(claim_id: str) -> Optional[dict]:
    db = get_db()
    try:
        doc = await db.claims.find_one({"_id": ObjectId(claim_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc
    except Exception:
        return None

async def get_evidence_for_claim(claim_id: str) -> List[dict]:
    db = get_db()
    cursor = db.evidence.find({"claim_id": claim_id}).sort("trust_score", -1)
    docs = await cursor.to_list(length=50)
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs

async def get_verdict_stats() -> dict:
    """Aggregate verdict distribution across all claims."""
    db = get_db()
    pipeline = [
        {"$group": {"_id": "$verdict", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cursor = db.claims.aggregate(pipeline)
    results = await cursor.to_list(length=10)
    return {r["_id"]: r["count"] for r in results}

async def seed_trusted_sources():
    """Seed the sources collection with trusted source registry (run once)."""
    from services.trusted_sources import TRUSTED_SOURCES, get_effective_trust
    db = get_db()
    for key, src in TRUSTED_SOURCES.items():
        await db.sources.update_one(
            {"domain": key},
            {"$set": {
                "domain": key,
                "label": src.get("label", key),
                "trust_score": get_effective_trust(key),
                "category": src.get("category", "unknown"),
                "description": src.get("description", ""),
                "updated_at": datetime.utcnow(),
            }},
            upsert=True
        )
    print("[DB] Trusted sources seeded")