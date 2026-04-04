"""
Multi-AI Verification Layer
Runs claim verification across Gemini, OpenAI (GPT-4o), and Groq (LLaMA).
Uses ensemble scoring to reduce single-model bias.
"""

import os
import asyncio
import json
from typing import List, Dict, Optional

import google.generativeai as genai
from openai import AsyncOpenAI
from groq import AsyncGroq

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

CLAIM_EXTRACTION_PROMPT = """You are a precise claim extraction engine.

Given the following user input, extract all distinct factual claims.
Return ONLY a JSON object in this exact format:
{{
  "claims": ["claim 1", "claim 2", ...],
  "category": "health|science|politics|history|technology|general",
  "complexity": "simple|moderate|complex"
}}

User input: {text}
"""

VERIFICATION_PROMPT = """You are a rigorous fact-checking analyst with expertise in evaluating evidence.

CLAIM TO VERIFY:
"{claim}"

EVIDENCE RETRIEVED FROM TRUSTED SOURCES:
{evidence_block}

Analyze this claim against the evidence. You MUST return ONLY a JSON object:
{{
  "verdict": "TRUE|FALSE|PARTIALLY_TRUE|UNVERIFIABLE|MISLEADING",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentence factual explanation citing specific sources",
  "supporting_sources": ["url1", "url2"],
  "contradicting_sources": ["url1"],
  "key_facts": ["fact1", "fact2"],
  "nuances": "any important context or caveats"
}}

Be factual, precise, and cite evidence directly. Do not speculate.
"""

RELEVANCE_FILTER_PROMPT = """You are evaluating evidence relevance.

CLAIM: "{claim}"

EVIDENCE ITEM:
Title: {title}
Abstract: {abstract}
Source: {source} (Trust Score: {trust_score})

Rate this evidence's relevance to the claim.
Return ONLY JSON:
{{
  "relevance_score": 0.0-1.0,
  "is_relevant": true/false,
  "relevance_reason": "one sentence"
}}
"""

# ─── CLAIM EXTRACTION ─────────────────────────────────────────────────────────

async def extract_claims(text: str) -> Dict:
    """Use fastest model (Groq/LLaMA) to extract claims quickly."""
    prompt = CLAIM_EXTRACTION_PROMPT.format(text=text)

    if GROQ_API_KEY:
        try:
            client = AsyncGroq(api_key=GROQ_API_KEY)
            resp = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            print(f"[Groq claim extraction failed] {e}")

    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = await asyncio.to_thread(model.generate_content, prompt)
            raw = resp.text.strip().lstrip("```json").rstrip("```").strip()
            return json.loads(raw)
        except Exception as e:
            print(f"[Gemini claim extraction failed] {e}")

    # Fallback
    return {"claims": [text], "category": "general", "complexity": "moderate"}

# ─── RELEVANCE FILTERING ──────────────────────────────────────────────────────

async def filter_relevant_evidence(claim: str, evidence_list: List[Dict]) -> List[Dict]:
    """Filter evidence list to only relevant items. Uses Groq for speed."""
    if not evidence_list:
        return []

    async def check_one(ev: Dict) -> Optional[Dict]:
        prompt = RELEVANCE_FILTER_PROMPT.format(
            claim=claim,
            title=ev.get("title", ""),
            abstract=ev.get("abstract", "")[:400],
            source=ev.get("source_label", ""),
            trust_score=ev.get("trust_score", 0),
        )
        try:
            if GROQ_API_KEY:
                client = AsyncGroq(api_key=GROQ_API_KEY)
                resp = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                )
                result = json.loads(resp.choices[0].message.content)
                ev["relevance_score"] = result.get("relevance_score", 0.5)
                ev["relevance_reason"] = result.get("relevance_reason", "")
                if result.get("is_relevant", False):
                    return ev
            else:
                # No LLM — keep all academic/fact-checker sources
                if ev.get("category") in ("academic", "fact_checker", "health_authority"):
                    ev["relevance_score"] = 0.7
                    return ev
        except Exception:
            if ev.get("trust_score", 0) > 0.85:
                return ev
        return None

    tasks = [check_one(ev) for ev in evidence_list]
    results = await asyncio.gather(*tasks)
    relevant = [r for r in results if r is not None]
    return sorted(relevant, key=lambda x: (x.get("relevance_score", 0) * x.get("trust_score", 0)), reverse=True)

# ─── SINGLE-MODEL VERIFICATION ────────────────────────────────────────────────

def _build_evidence_block(evidence_list: List[Dict]) -> str:
    lines = []
    for i, ev in enumerate(evidence_list[:6], 1):
        lines.append(f"[{i}] SOURCE: {ev.get('source_label','')} (trust={ev.get('trust_score',0):.2f})")
        lines.append(f"    TITLE: {ev.get('title','')}")
        if ev.get("abstract"):
            lines.append(f"    CONTENT: {ev['abstract'][:500]}")
        if ev.get("url"):
            lines.append(f"    URL: {ev['url']}")
        lines.append("")
    return "\n".join(lines)

async def verify_with_gemini(claim: str, evidence_list: List[Dict]) -> Dict:
    if not GEMINI_API_KEY:
        return {}
    prompt = VERIFICATION_PROMPT.format(
        claim=claim,
        evidence_block=_build_evidence_block(evidence_list)
    )
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        resp = await asyncio.to_thread(model.generate_content, prompt)
        raw = resp.text.strip().lstrip("```json").rstrip("```").strip()
        result = json.loads(raw)
        result["model"] = "gemini-1.5-pro"
        return result
    except Exception as e:
        print(f"[Gemini verify failed] {e}")
        return {}

async def verify_with_openai(claim: str, evidence_list: List[Dict]) -> Dict:
    if not OPENAI_API_KEY:
        return {}
    prompt = VERIFICATION_PROMPT.format(
        claim=claim,
        evidence_block=_build_evidence_block(evidence_list)
    )
    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)
        result["model"] = "gpt-4o-mini"
        return result
    except Exception as e:
        print(f"[OpenAI verify failed] {e}")
        return {}

async def verify_with_groq(claim: str, evidence_list: List[Dict]) -> Dict:
    if not GROQ_API_KEY:
        return {}
    prompt = VERIFICATION_PROMPT.format(
        claim=claim,
        evidence_block=_build_evidence_block(evidence_list)
    )
    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        resp = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)
        result["model"] = "llama-3.3-70b"
        return result
    except Exception as e:
        print(f"[Groq verify failed] {e}")
        return {}

# ─── ENSEMBLE DECISION ENGINE ─────────────────────────────────────────────────

VERDICT_SCORES = {
    "TRUE": 1.0, "PARTIALLY_TRUE": 0.5, "MISLEADING": 0.25,
    "UNVERIFIABLE": 0.0, "FALSE": -1.0,
}

MODEL_WEIGHTS = {
    "gemini-1.5-pro": 0.40,
    "gpt-4o-mini": 0.35,
    "llama-3.3-70b": 0.25,
}

def ensemble_decision(model_results: List[Dict], evidence_list: List[Dict]) -> Dict:
    """
    Combine model verdicts using weighted ensemble.
    Also computes a source-based credibility score.
    """
    valid = [r for r in model_results if r and r.get("verdict")]
    if not valid:
        return {
            "verdict": "UNVERIFIABLE",
            "confidence": 0.0,
            "reasoning": "No AI models were able to verify this claim.",
            "ensemble_agreement": 0.0,
        }

    # Weighted verdict score
    total_weight = 0.0
    weighted_score = 0.0
    verdicts = []
    confidences = []

    for r in valid:
        model = r.get("model", "")
        w = MODEL_WEIGHTS.get(model, 0.25)
        v_score = VERDICT_SCORES.get(r.get("verdict", "UNVERIFIABLE"), 0.0)
        weighted_score += v_score * w * r.get("confidence", 0.5)
        total_weight += w
        verdicts.append(r.get("verdict"))
        confidences.append(r.get("confidence", 0.5))

    norm_score = weighted_score / max(total_weight, 1e-9)

    # Source credibility bonus
    academic_sources = [e for e in evidence_list if e.get("category") in ("academic", "health_authority", "science_authority")]
    source_credibility = sum(e.get("trust_score", 0) for e in academic_sources[:5]) / max(len(academic_sources[:5]), 1)
    source_bonus = min(source_credibility * 0.1, 0.1)

    # Ensemble agreement (fraction of models agreeing on verdict)
    most_common_verdict = max(set(verdicts), key=verdicts.count)
    agreement = verdicts.count(most_common_verdict) / len(verdicts)

    # Final confidence
    avg_conf = sum(confidences) / len(confidences)
    final_confidence = round(min(avg_conf + source_bonus, 1.0), 3)

    # Map score to verdict
    if norm_score > 0.55:
        final_verdict = "TRUE"
    elif norm_score > 0.2:
        final_verdict = "PARTIALLY_TRUE"
    elif norm_score > -0.1:
        final_verdict = "MISLEADING" if "MISLEADING" in verdicts else "UNVERIFIABLE"
    else:
        final_verdict = "FALSE"

    # Merge reasoning from all models
    reasonings = [r.get("reasoning", "") for r in valid if r.get("reasoning")]
    key_facts = []
    for r in valid:
        key_facts.extend(r.get("key_facts", []))
    key_facts = list(dict.fromkeys(key_facts))[:5]  # deduplicate

    return {
        "verdict": final_verdict,
        "confidence": final_confidence,
        "ensemble_agreement": round(agreement, 2),
        "reasoning": reasonings[0] if reasonings else "",
        "all_reasonings": reasonings,
        "key_facts": key_facts,
        "nuances": valid[0].get("nuances", "") if valid else "",
        "models_used": [r.get("model") for r in valid],
        "source_credibility_score": round(source_credibility, 3),
        "supporting_sources": valid[0].get("supporting_sources", []) if valid else [],
        "contradicting_sources": valid[0].get("contradicting_sources", []) if valid else [],
    }

# ─── MASTER VERIFY PIPELINE ───────────────────────────────────────────────────

async def verify_claim_full(claim: str, evidence_list: List[Dict]) -> Dict:
    """Run all three models in parallel and ensemble the results."""
    tasks = [
        verify_with_gemini(claim, evidence_list),
        verify_with_openai(claim, evidence_list),
        verify_with_groq(claim, evidence_list),
    ]
    model_results = await asyncio.gather(*tasks)
    return ensemble_decision(list(model_results), evidence_list)