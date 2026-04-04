"""
Verification Route
POST /api/verify/  — submit text for fact-checking
GET  /api/verify/{id} — get result by ID
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import time
import asyncio

from services.ai_verification import extract_claims, filter_relevant_evidence, verify_claim_full
from services.evidence_retrieval import retrieve_all_evidence
from models.claimmodel import save_claim, save_evidence_batch, get_claim_by_id, get_evidence_for_claim

router = APIRouter()

class VerifyRequest(BaseModel):
    text: str
    session_id: Optional[str] = None

class VerifyResponse(BaseModel):
    claim_id: str
    claim_text: str
    verdict: str
    confidence: float
    ensemble_agreement: float
    reasoning: str
    key_facts: list
    nuances: str
    models_used: list
    source_credibility_score: float
    evidence: list
    evidence_count: int
    academic_sources_count: int
    processing_time_ms: int
    supporting_sources: list
    contradicting_sources: list

@router.post("/", response_model=VerifyResponse)
async def verify_claim(request: VerifyRequest, background_tasks: BackgroundTasks):
    if not request.text or len(request.text.strip()) < 5:
        raise HTTPException(status_code=400, detail="Claim text too short.")
    if len(request.text) > 2000:
        raise HTTPException(status_code=400, detail="Claim text too long (max 2000 chars).")

    start_ms = int(time.time() * 1000)

    # ── Step 1: Extract claims ───────────────────────────────────────────────
    extraction = await extract_claims(request.text)
    primary_claim = extraction.get("claims", [request.text])[0]
    category = extraction.get("category", "general")

    # ── Step 2: Retrieve evidence ────────────────────────────────────────────
    raw_evidence = await retrieve_all_evidence(primary_claim, category)

    # ── Step 3: Filter relevance ─────────────────────────────────────────────
    relevant_evidence = await filter_relevant_evidence(primary_claim, raw_evidence)
    if not relevant_evidence:
        relevant_evidence = raw_evidence[:6]  # fallback: use top results anyway

    # ── Step 4: AI Verification (ensemble) ───────────────────────────────────
    verification = await verify_claim_full(primary_claim, relevant_evidence)

    # ── Step 5: Compute credibility scores ───────────────────────────────────
    academic_ev = [e for e in relevant_evidence if e.get("category") in ("academic", "health_authority", "science_authority", "preprint")]
    
    elapsed_ms = int(time.time() * 1000) - start_ms

    # ── Step 6: Prepare evidence summary (top 8, lightweight) ────────────────
    evidence_summary = []
    for ev in relevant_evidence[:8]:
        evidence_summary.append({
            "source_label": ev.get("source_label", ""),
            "source_key": ev.get("source_key", ""),
            "title": ev.get("title", ""),
            "abstract": (ev.get("abstract") or "")[:300],
            "url": ev.get("url", ""),
            "trust_score": ev.get("trust_score", 0),
            "relevance_score": ev.get("relevance_score", 0),
            "category": ev.get("category", ""),
            "year": ev.get("year", ""),
            "authors": ev.get("authors", []),
            "doi": ev.get("doi", ""),
            "pmid": ev.get("pmid", ""),
        })

    # ── Step 7: Persist to MongoDB ───────────────────────────────────────────
    claim_doc = {
        "claim_text": primary_claim,
        "original_input": request.text,
        "category": category,
        "complexity": extraction.get("complexity", "moderate"),
        "verdict": verification["verdict"],
        "confidence": verification["confidence"],
        "ensemble_agreement": verification["ensemble_agreement"],
        "reasoning": verification["reasoning"],
        "key_facts": verification.get("key_facts", []),
        "nuances": verification.get("nuances", ""),
        "models_used": verification.get("models_used", []),
        "source_credibility_score": verification.get("source_credibility_score", 0),
        "evidence_count": len(relevant_evidence),
        "academic_evidence_count": len(academic_ev),
        "evidence_summary": evidence_summary,
        "session_id": request.session_id,
        "processing_time_ms": elapsed_ms,
        "supporting_sources": verification.get("supporting_sources", []),
        "contradicting_sources": verification.get("contradicting_sources", []),
        "all_reasonings": verification.get("all_reasonings", []),
    }

    claim_id = await save_claim(claim_doc)

    # Save full evidence in background (non-blocking)
    background_tasks.add_task(save_evidence_batch, relevant_evidence, claim_id)

    return VerifyResponse(
        claim_id=claim_id,
        claim_text=primary_claim,
        verdict=verification["verdict"],
        confidence=verification["confidence"],
        ensemble_agreement=verification["ensemble_agreement"],
        reasoning=verification["reasoning"],
        key_facts=verification.get("key_facts", []),
        nuances=verification.get("nuances", ""),
        models_used=verification.get("models_used", []),
        source_credibility_score=verification.get("source_credibility_score", 0),
        evidence=evidence_summary,
        evidence_count=len(relevant_evidence),
        academic_sources_count=len(academic_ev),
        processing_time_ms=elapsed_ms,
        supporting_sources=verification.get("supporting_sources", []),
        contradicting_sources=verification.get("contradicting_sources", []),
    )

@router.get("/{claim_id}")
async def get_verification(claim_id: str):
    doc = await get_claim_by_id(claim_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Claim not found.")
    evidence = await get_evidence_for_claim(claim_id)
    doc["evidence"] = evidence
    return doc