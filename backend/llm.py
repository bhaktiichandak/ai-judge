from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None


env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if Groq and os.getenv("GROQ_API_KEY") else None

MAX_CLAIMS = 3
MAX_CREDIBLE_SOURCES = 5
MAX_SEARCH_QUERIES = 4
SEARCH_TIMEOUT_SECONDS = float(os.getenv("SEARCH_TIMEOUT_SECONDS", "3.0"))
ENABLE_LIVE_SOURCES = os.getenv("ENABLE_LIVE_SOURCES", "true").lower() == "true"
QUESTION_ANSWER_MODEL = os.getenv("QUESTION_ANSWER_MODEL", "llama-3.1-8b-instant")
MCQ_OPTION_PATTERN = re.compile(r"^\s*([A-Ha-h]|\d{1,2})[\)\.\:\-]\s*(.+)$")
QUESTION_START_PATTERN = re.compile(
    r"^\s*(who|what|when|where|which|why|how|is|are|was|were|do|does|did|can|could|"
    r"should|will|would|has|have|had|capital of|population of|define|explain)\b"
)

SEARCH_STOPWORDS = {
    "a", "an", "and", "are", "be", "can", "could", "did", "do", "does", "for",
    "from", "how", "i", "if", "in", "is", "it", "its", "of", "on", "or", "say",
    "says", "should", "that", "the", "their", "them", "these", "this", "to",
    "was", "were", "what", "when", "where", "which", "who", "why", "will", "with",
    "would", "your",
}
SOURCE_REQUEST_TERMS = {
    "source", "sources", "citation", "citations", "evidence", "reference",
    "references", "credible", "credibility", "fact", "fact-check", "verify",
    "verified", "proof",
}
SOURCE_META_TERMS = {
    "add", "cite", "give", "include", "list", "please", "provide", "show", "with",
}
RESEARCH_TERMS = {
    "research", "study", "studies", "paper", "papers", "journal", "literature",
    "survey", "dataset", "report", "reports", "analysis", "findings",
}
FACTUAL_TERMS = {
    "who", "what", "when", "where", "which", "does", "did", "is", "are",
    "capital", "population", "invented", "published", "founded", "define",
    "definition", "cause", "effect",
}
TRUSTED_SOURCE_RULES = [
    ("pubmed.ncbi.nlm.nih.gov", "Peer-reviewed index", "Very High", 5),
    ("nih.gov", "Government health source", "Very High", 5),
    ("who.int", "Global public-health authority", "Very High", 5),
    ("nist.gov", "Government standards source", "Very High", 5),
    ("sec.gov", "Regulatory filing source", "Very High", 5),
    ("ietf.org", "Standards body", "Very High", 5),
    ("w3.org", "Standards body", "Very High", 5),
    ("rfc-editor.org", "Standards publication source", "Very High", 5),
    ("iana.org", "Internet standards source", "Very High", 5),
    ("oecd.org", "Policy standards source", "High", 4),
    ("docs.python.org", "Official technical documentation", "High", 4),
    ("developer.mozilla.org", "Official technical documentation", "High", 4),
    ("nature.com", "Research publisher", "High", 4),
    ("science.org", "Research publisher", "High", 4),
    ("britannica.com", "Reference publisher", "Moderate", 3),
    ("nasa.gov", "Government science source", "Very High", 5),
    ("noaa.gov", "Government science source", "Very High", 5),
    ("cdc.gov", "Government health source", "Very High", 5),
    ("cia.gov", "Government reference source", "High", 4),
    ("usgs.gov", "Government science source", "Very High", 5),
    ("worldbank.org", "International data source", "High", 4),
    ("arxiv.org", "Research preprint source", "Moderate", 3),
    ("github.com", "Official project or docs host", "Moderate", 3),
]


@dataclass
class SourceRecord:
    claim: str
    title: str
    url: str
    snippet: str
    published: str
    source_type: str
    credibility_tier: str
    score: int
    relevance: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvaluationResult:
    reply: str
    model_used: str
    sources: list[dict]
    task_kind: str


def normalize_domain(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain


def classify_source(url: str) -> tuple[str, str, int]:
    domain = normalize_domain(url)
    for trusted_domain, label, tier, score in TRUSTED_SOURCE_RULES:
        if domain == trusted_domain or domain.endswith(f".{trusted_domain}"):
            return label, tier, score
    if domain.endswith(".gov") or ".gov." in domain:
        return "Government source", "Very High", 5
    if domain.endswith(".edu") or ".edu." in domain:
        return "Academic institution", "High", 4
    if any(token in domain for token in ("docs.", "developer.", "reference.")):
        return "Official documentation", "High", 4
    if domain.endswith(".org"):
        return "Organization / NGO", "Moderate", 3
    return ("General web", "Low", 1) if domain else ("Unknown", "Low", 1)


def get_no_proxy_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def cleanup_search_query(text: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9\.-]+", text)
    filtered = [token for token in tokens if token.lower() not in SEARCH_STOPWORDS]
    return " ".join(filtered[:8]) if filtered else text.strip()


def text_token_set(text: str) -> set[str]:
    tokens = set()
    for raw_token in re.findall(r"[A-Za-z0-9\.-]+", text):
        token = raw_token.lower().strip(".-")
        if token and token not in SEARCH_STOPWORDS and len(token) > 1:
            tokens.add(token)
    return tokens


def score_result_relevance(claim: str, title: str, snippet: str, url: str, option_texts: list[str] | None = None) -> int:
    result_tokens = text_token_set(" ".join([title, snippet, url]))
    overlap = len(text_token_set(claim) & result_tokens)
    option_bonus = 0
    for option_text in option_texts or []:
        if text_token_set(option_text) & result_tokens:
            option_bonus += 2
    return overlap + option_bonus


def parse_mcq_prompt(user_message: str) -> dict | None:
    lines = [line.rstrip() for line in user_message.splitlines() if line.strip()]
    if not lines:
        return None
    options = []
    stem_lines = []
    options_started = False
    for line in lines:
        match = MCQ_OPTION_PATTERN.match(line)
        if match:
            options_started = True
            options.append({"label": match.group(1).upper(), "text": match.group(2).strip()})
            continue
        if options_started and options:
            options[-1]["text"] = f"{options[-1]['text']} {line.strip()}".strip()
        else:
            stem_lines.append(line.strip())
    if len(options) < 2:
        return None
    question = " ".join(stem_lines).strip() or cleanup_search_query(user_message)
    return {"question": question, "options": options[:6]}


def looks_like_code(text: str) -> bool:
    if "```" in text:
        return True
    code_patterns = [
        r"^\s*(def|class|import|from)\s+",
        r"\bdef\s+\w+\s*\(",
        r"\bclass\s+\w+\s*[:\(]",
        r"^\s*(function|const|let|var)\s+",
        r"^\s*(public|private|protected|static)\s+",
        r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER)\b",
        r"^\s*#include\s+",
        r"^\s*<[^>]+>\s*$",
    ]
    hits = sum(1 for pattern in code_patterns if re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE))
    symbol_hits = sum(marker in text for marker in ("{", "}", "();", "=>", "::", "</", "/>", "return "))
    return hits >= 1 or (hits == 0 and symbol_hits >= 3 and "\n" in text)


def looks_like_factual_prompt(text: str) -> bool:
    lower = text.lower().strip()
    raw_tokens = {
        token.lower().strip(".-")
        for token in re.findall(r"[A-Za-z0-9\.-]+", text)
        if token.strip(".-")
    }
    return (
        "?" in text
        or bool(QUESTION_START_PATTERN.match(lower))
        or bool(raw_tokens & FACTUAL_TERMS)
        or bool(re.search(r"\b(true or false|fact[\s-]?check|correct or not)\b", lower))
    )


def looks_like_yes_no_question(text: str) -> bool:
    lower = text.lower().strip()
    return bool(
        re.match(
            r"^(is|are|was|were|do|does|did|can|could|should|will|would|has|have|had)\b",
            lower,
        )
    )


def infer_task_profile(user_message: str, selected_mode: str) -> dict:
    stripped = user_message.strip()
    mcq_data = parse_mcq_prompt(stripped)
    tokens = text_token_set(stripped)
    lower = stripped.lower()
    sentence_count = len(re.findall(r"[.!?]+", stripped))
    explicit_source_request = bool(tokens & SOURCE_REQUEST_TERMS)
    research_like = bool(tokens & RESEARCH_TERMS)
    factual_like = looks_like_factual_prompt(stripped)

    if mcq_data:
        kind = "mcq"
    elif looks_like_code(stripped):
        kind = "code"
    elif research_like:
        kind = "research"
    elif selected_mode == "compare" or re.search(r"\b(compare|vs|versus)\b", lower):
        kind = "comparison"
    elif bool(tokens & {"essay", "thesis", "paragraph", "article", "statement"}) or (sentence_count >= 3 and len(stripped.split()) > 80):
        kind = "essay"
    elif bool(tokens & {"argument", "argue", "debate", "because", "therefore", "should", "must"}):
        kind = "argument"
    elif bool(tokens & {"idea", "plan", "feature", "product", "startup", "roadmap", "concept"}):
        kind = "idea"
    elif factual_like:
        kind = "question"
    else:
        kind = "general"

    needs_evidence = (
        selected_mode == "credibility"
        or mcq_data is not None
        or explicit_source_request
        or research_like
        or (kind == "question" and factual_like)
    )
    if kind == "code" and selected_mode != "credibility" and not explicit_source_request:
        needs_evidence = False
    return {"kind": kind, "needs_evidence": needs_evidence}


def build_effective_user_message(user_message: str, history: list[dict]) -> str:
    if len(user_message.split()) >= 12 or not history:
        return user_message
    recent_user_messages = [
        message["content"].strip()
        for message in history[-4:]
        if message.get("role") == "user" and message.get("content", "").strip()
    ]
    if not recent_user_messages:
        return user_message
    deduped = []
    for item in recent_user_messages + [user_message]:
        if item not in deduped:
            deduped.append(item)
    return "\n".join(deduped[-3:])


def extract_claims_for_review(user_message: str, task_profile: dict | None = None) -> list[str]:
    raw_text = user_message.strip()
    if not raw_text:
        return []
    mcq_data = parse_mcq_prompt(raw_text)
    if mcq_data:
        return [cleanup_search_query(mcq_data["question"])]
    if task_profile and task_profile.get("kind") == "question":
        return [raw_text]
    if not task_profile or not task_profile.get("needs_evidence"):
        return [cleanup_search_query(raw_text)]
    segments = re.split(r"[\n\r]+|(?<=[\.\?\!])\s+", raw_text)
    claims = []
    for segment in segments:
        cleaned = cleanup_search_query(segment.strip(" -\t"))
        lowered_tokens = text_token_set(cleaned)
        non_source_tokens = lowered_tokens - SOURCE_REQUEST_TERMS
        if lowered_tokens and not non_source_tokens:
            continue
        if lowered_tokens and non_source_tokens and len(non_source_tokens) <= 1 and lowered_tokens & SOURCE_REQUEST_TERMS:
            continue
        if lowered_tokens & SOURCE_REQUEST_TERMS and non_source_tokens and non_source_tokens <= SOURCE_META_TERMS:
            continue
        if cleaned and cleaned not in claims:
            claims.append(cleaned)
        if len(claims) >= MAX_CLAIMS:
            break
    return claims or [cleanup_search_query(raw_text)]


def domain_hint_queries(text: str) -> list[str]:
    tokens = text_token_set(text)
    hints: list[str] = []
    if tokens & {"python", "javascript", "html", "css", "http", "api", "programming", "algorithm"}:
        hints.extend(["site:docs.python.org", "site:developer.mozilla.org", "site:ietf.org", "site:rfc-editor.org"])
    if tokens & {"health", "disease", "medicine", "drug", "symptom", "vaccine", "virus", "treatment"}:
        hints.extend(["site:nih.gov", "site:pubmed.ncbi.nlm.nih.gov", "site:who.int", "site:cdc.gov"])
    if tokens & {"planet", "space", "nasa", "climate", "weather", "ocean", "earthquake", "geology"}:
        hints.extend(["site:nasa.gov", "site:noaa.gov", "site:usgs.gov"])
    if tokens & {"economy", "gdp", "inflation", "finance", "stock", "revenue", "filing", "earnings"}:
        hints.extend(["site:sec.gov", "site:worldbank.org", "site:oecd.org"])
    if tokens & {"capital", "country", "population", "geography", "flag"}:
        hints.extend(["site:cia.gov", "site:britannica.com"])
    return hints


def build_search_queries(claim: str, mcq_data: dict | None = None, needs_evidence: bool = False) -> list[str]:
    raw_claim = claim.strip()
    base = cleanup_search_query(raw_claim)
    queries = [raw_claim, base, f"{raw_claim} official source", f"{base} official source"]
    if mcq_data and cleanup_search_query(mcq_data["question"]) == claim:
        queries.extend(f"{base} {cleanup_search_query(option['text'])}" for option in mcq_data["options"][:2])
    queries.extend(f"{base} {hint}" for hint in domain_hint_queries(claim))
    if needs_evidence:
        queries.extend([f"{raw_claim} site:gov", f"{base} site:gov", f"{raw_claim} site:edu", f"{base} site:edu"])
    deduped = []
    seen = set()
    for query in queries:
        normalized = query.strip()
        if not normalized or normalized in seen:
            continue
        deduped.append(normalized)
        seen.add(normalized)
        if len(deduped) >= MAX_SEARCH_QUERIES:
            break
    return deduped


def option_texts_for_claim(claim: str, mcq_data: dict | None) -> list[str]:
    if not mcq_data or cleanup_search_query(mcq_data["question"]) != claim:
        return []
    return [option["text"] for option in mcq_data["options"][:6]]


def bing_rss_results(search_query: str) -> list[dict]:
    session = get_no_proxy_session()
    try:
        response = session.get(
            "https://www.bing.com/search",
            params={"q": search_query, "format": "rss", "setlang": "en-US", "cc": "US"},
            timeout=SEARCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
    except Exception:
        return []
    items = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        snippet = (item.findtext("description") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if pub_date:
            pub_date = re.sub(r"\s+\d{2}:\d{2}:\d{2}.*", "", pub_date)
        if not url:
            continue
        items.append(
            {
                "title": title or normalize_domain(url) or "Untitled source",
                "href": url,
                "body": snippet or "No snippet available.",
                "date": pub_date or "Date unavailable",
            }
        )
    return items


def collect_sources(user_message: str, task_profile: dict | None = None) -> tuple[list[str], list[SourceRecord]]:
    if not ENABLE_LIVE_SOURCES or (task_profile and not task_profile.get("needs_evidence")):
        return [], []
    mcq_data = parse_mcq_prompt(user_message)
    claims = extract_claims_for_review(user_message, task_profile)
    collected: list[SourceRecord] = []
    seen_urls: set[str] = set()
    for claim in claims:
        option_texts = option_texts_for_claim(claim, mcq_data)
        for search_query in build_search_queries(claim, mcq_data, bool(task_profile and task_profile.get("needs_evidence"))):
            for result in bing_rss_results(search_query):
                url = result.get("href")
                if not url or url in seen_urls:
                    continue
                title = (result.get("title") or normalize_domain(url) or "Untitled source").strip()
                snippet = (result.get("body") or "No snippet available.").strip()
                source_type, tier, score = classify_source(url)
                relevance = score_result_relevance(claim, title, snippet, url, option_texts)
                claim_token_count = len(text_token_set(claim))
                min_relevance = 2 if claim_token_count >= 2 else 1
                if relevance < min_relevance:
                    continue
                if score <= 1 and relevance <= 1:
                    continue
                collected.append(
                    SourceRecord(
                        claim=claim,
                        title=title,
                        url=url,
                        snippet=snippet,
                        published=result.get("date") or "Date unavailable",
                        source_type=source_type,
                        credibility_tier=tier,
                        score=score,
                        relevance=relevance,
                    )
                )
                seen_urls.add(url)
                if len(collected) >= MAX_CREDIBLE_SOURCES * 2:
                    break
            if len(collected) >= MAX_CREDIBLE_SOURCES * 2:
                break
        if len(collected) >= MAX_CREDIBLE_SOURCES * 2:
            break
    collected.sort(key=lambda item: ((item.score * 10) + item.relevance, item.score, item.relevance), reverse=True)
    filtered = [item for item in collected if item.score >= 3 or item.relevance >= 2]
    trusted = [item for item in filtered if item.score >= 3]
    if trusted:
        collected = trusted
    elif len(filtered) >= 2:
        collected = filtered
    elif task_profile and task_profile.get("needs_evidence"):
        collected = []
    return claims, collected[:MAX_CREDIBLE_SOURCES]


def summarize_source_quality(sources: list[SourceRecord]) -> str:
    if not sources:
        return (
            "No credible external sources were retrieved in this run, so any factual judgment "
            "should be treated as low confidence."
        )
    tier_counts = {"Very High": 0, "High": 0, "Moderate": 0, "Low": 0}
    source_types: list[str] = []
    for source in sources:
        tier_counts[source.credibility_tier] = tier_counts.get(source.credibility_tier, 0) + 1
        if source.source_type not in source_types:
            source_types.append(source.source_type)
    strongest_tier = next((tier for tier in ("Very High", "High", "Moderate", "Low") if tier_counts.get(tier, 0) > 0), "Low")
    return (
        f"Retrieved {len(sources)} source(s). Strongest credibility tier: {strongest_tier}. "
        f"Source mix: {', '.join(source_types[:4])}."
    )


def render_sources_markdown(sources: list[SourceRecord]) -> str:
    if not sources:
        return (
            "- No credible external sources were retrieved for this response.\n"
            "- The answer is deterministic, but it is not externally verified."
        )
    lines = []
    for source in sources:
        snippet = source.snippet.replace("\n", " ").strip()
        if len(snippet) > 220:
            snippet = snippet[:217].rstrip() + "..."
        safe_title = source.title.replace("[", "\\[").replace("]", "\\]")
        lines.append(
            f"- [{safe_title}]({source.url}) | {source.source_type} | {source.published} | "
            f"{source.credibility_tier} | {snippet}"
        )
    return "\n".join(lines)


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def join_bullets(items: list[str], fallback: str) -> str:
    return "\n".join(f"- {item}" for item in (items or [fallback]))


def format_sections(sections: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"{header}\n{body.strip()}" for header, body in sections if body.strip())


def analyze_code_quality(text: str) -> dict:
    strengths = []
    risks = []
    next_steps = []
    score = 6
    if re.search(r"^\s*(def|class)\s+\w+", text, re.MULTILINE):
        strengths.append("The code is organized into named functions or classes instead of a single flat script.")
        score += 1
    if re.search(r"def\s+\w+\([^)]*:\s*[^)]*\)\s*->", text):
        strengths.append("Type hints are present, which makes the interfaces easier to follow.")
        score += 1
    if re.search(r"\b(assert|pytest|unittest|TestCase)\b", text):
        strengths.append("There is at least some testing signal in the snippet.")
        score += 1
    if re.search(r"except\s*:", text):
        risks.append("A bare `except:` can hide real failures.")
        next_steps.append("Replace bare exception handlers with specific exception types.")
        score -= 2
    if re.search(r"except\s+Exception\b", text):
        risks.append("Broad `except Exception` blocks can swallow bugs that should fail loudly.")
        next_steps.append("Narrow exception handling around the exact failure modes you expect.")
        score -= 1
    if re.search(r"def\s+\w+\([^)]*=\s*(\[\]|\{\})", text):
        risks.append("There is a mutable default argument, which can leak state across calls.")
        next_steps.append("Use `None` as the default and create a fresh list or dict inside the function.")
        score -= 2
    todo_count = len(re.findall(r"\b(TODO|FIXME|XXX)\b", text, re.IGNORECASE))
    if todo_count:
        risks.append(f"The snippet still contains {todo_count} unfinished TODO or FIXME marker(s).")
        next_steps.append("Close or ticket the unfinished areas before relying on this path.")
        score -= 1
    if len(re.findall(r"\bprint\(", text)) >= 3:
        risks.append("Several `print()` calls suggest debugging code is still mixed into runtime logic.")
        next_steps.append("Replace ad-hoc prints with structured logging.")
        score -= 1
    if not strengths:
        strengths.append("The snippet is structured enough to inspect and iterate on.")
    if not risks:
        risks.append("No obvious syntax-level flaw jumps out from the pasted code, but runtime behavior still needs tests.")
        next_steps.append("Add a focused regression test around the highest-risk path before changing behavior.")
    verdict = (
        f"This code looks {'solid enough to iterate on' if score >= 7 else 'workable but still fragile'}. "
        "The bigger risks are in runtime behavior, failure handling, and coverage."
    )
    return {"score": clamp(score, 2, 9), "verdict": verdict, "strengths": strengths[:3], "risks": risks[:3], "next_steps": next_steps[:3]}


def analyze_text_quality(text: str, kind: str) -> dict:
    words = text.split()
    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    strengths = []
    risks = []
    next_steps = []
    score = 5
    if len(words) >= 60:
        strengths.append("There is enough material here to judge intent and structure instead of reacting to a one-line prompt.")
        score += 1
    else:
        risks.append("The prompt is brief, so the evaluation can only be as precise as the detail provided.")
        next_steps.append("Add one or two concrete examples or constraints so the next pass can go deeper.")
    if len(paragraphs) >= 2 or re.search(r"[-*]\s", text):
        strengths.append("The input has visible structure, which makes the main points easier to follow.")
        score += 1
    else:
        risks.append("The ideas are packed together, which makes critique and prioritization harder.")
        next_steps.append("Split the input into short sections or bullets so each claim can be judged separately.")
    if re.search(r"\b(for example|because|therefore|however|but)\b", text, re.IGNORECASE):
        strengths.append("The reasoning shows connective tissue rather than isolated claims.")
        score += 1
    if kind in {"research", "argument", "question"} and not re.search(r"\b(data|study|source|evidence|because)\b", text, re.IGNORECASE):
        risks.append("The claim asks for trust without pointing to evidence.")
        next_steps.append("Anchor the strongest point with a source, number, or concrete example.")
        score -= 1
    if kind == "idea" and not re.search(r"\b(user|customer|market|cost|risk|timeline)\b", text, re.IGNORECASE):
        risks.append("The idea is still high-level and does not expose user, cost, or execution constraints.")
        next_steps.append("State who the idea is for, the main risk, and the first real-world test you would run.")
        score -= 1
    if not strengths:
        strengths.append("The prompt is understandable enough to produce a deterministic review.")
    if not risks:
        risks.append("The main remaining risk is hidden context rather than a visible structural flaw.")
        next_steps.append("Clarify the intended audience and success criteria to make the next review more precise.")
    verdict = (
        f"This {kind} input is {'reasonably well-formed' if score >= 7 else 'usable but under-specified'}. "
        "The next gain will come from adding specificity, not changing the tone."
    )
    return {"score": clamp(score, 3, 9), "verdict": verdict, "strengths": strengths[:3], "risks": risks[:3], "next_steps": next_steps[:3]}


def analyze_comparison_request(text: str) -> dict:
    match = re.search(r"(.+?)\s+(?:vs\.?|versus)\s+(.+)", text, re.IGNORECASE)
    left = match.group(1).strip(" .:?") if match else "Option A"
    right = match.group(2).strip(" .:?") if match else "Option B"
    verdict = (
        f"The comparison between {left} and {right} is answerable, but the winner still depends on the criteria you care about most."
    )
    breakdown = (
        f"Judge {left} and {right} on the same criteria: fit, cost, complexity, learning curve, and long-term maintenance risk."
    )
    pros_and_cons = [
        f"{left} may be stronger when its native ecosystem or strengths match your use case.",
        f"{right} may be stronger when speed of execution, familiarity, or lower migration cost matters more.",
        "The biggest mistake is choosing before naming the evaluation criteria.",
    ]
    recommendation = (
        "Define three criteria first, score both sides against them, and only then choose a winner. "
        "That keeps the answer stable instead of opinion-driven."
    )
    return {"score": 7, "verdict": verdict, "breakdown": breakdown, "pros_and_cons": pros_and_cons, "recommendation": recommendation}


def determine_evidence_strength(sources: list[SourceRecord]) -> tuple[str, str]:
    very_high = sum(source.credibility_tier == "Very High" for source in sources)
    high = sum(source.credibility_tier == "High" for source in sources)
    average_score = (sum(source.score for source in sources) / len(sources)) if sources else 0
    if very_high >= 2 or (very_high >= 1 and high >= 1):
        return "Strong", "The evidence set includes multiple high-trust sources with overlapping relevance."
    if very_high >= 1 or high >= 2 or (len(sources) >= 3 and average_score >= 3):
        return "Moderate", "There is some credible support, but the source pool is still limited."
    if sources:
        return "Weak", "Some sources were found, but they are sparse or not strong enough to fully verify the claim."
    return "Weak", "No credible external sources were retrieved in this run."


def build_claim_checks(claims: list[str], sources: list[SourceRecord]) -> list[str]:
    claim_checks = []
    for claim in claims or ["The main claim"]:
        supporting = [source for source in sources if source.claim == claim]
        strong_sources = [source for source in supporting if source.score >= 4]
        if len(strong_sources) >= 2:
            status = "Supported"
            reason = "multiple strong sources matched this claim"
        elif strong_sources or len(supporting) >= 2:
            status = "Partially Supported"
            reason = "there is some support, but not enough to remove uncertainty"
        elif supporting:
            status = "Unsupported"
            reason = "the retrieved sources were too weak or too indirect to verify it"
        else:
            status = "Unsupported"
            reason = "no credible supporting source was retrieved"
        claim_checks.append(f"{claim}: {status} - {reason}.")
    return claim_checks


def choose_mcq_option(mcq_data: dict, sources: list[SourceRecord]) -> tuple[str, str]:
    best_option = None
    best_score = -1
    for option in mcq_data["options"]:
        option_tokens = text_token_set(option["text"])
        score = 0
        for source in sources:
            source_tokens = text_token_set(f"{source.title} {source.snippet} {source.url}")
            score += len(option_tokens & source_tokens) * max(source.score, 1)
        if score > best_score:
            best_option = option
            best_score = score
    if not best_option or best_score <= 0:
        return ("Insufficient evidence to choose confidently.", "No option had clear support from the retrieved sources.")
    return (f"{best_option['label']} - {best_option['text']}", f"The retrieved evidence aligned best with option {best_option['label']}.")


def normalize_answer_snippet(snippet: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", snippet or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,-")
    if not cleaned or cleaned.lower() == "no snippet available":
        return ""
    candidate = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0].strip()
    if len(candidate) < 24 and len(cleaned) > len(candidate):
        candidate = cleaned
    if len(candidate) > 220:
        candidate = candidate[:217].rstrip() + "..."
    if candidate and candidate[-1] not in ".!?":
        candidate += "."
    return candidate


def build_corrected_answer(task_profile: dict, claims: list[str], sources: list[SourceRecord], mcq_data: dict | None) -> str:
    if mcq_data:
        correct_option, _ = choose_mcq_option(mcq_data, sources)
        if not correct_option.startswith("Insufficient evidence"):
            return f"The correct option is {correct_option}."
        return ""
    if task_profile.get("kind") != "question" or not sources:
        return ""
    top_source = sources[0]
    answer_snippet = normalize_answer_snippet(top_source.snippet)
    if answer_snippet:
        return f"Based on the strongest retrieved source, {answer_snippet}"
    if top_source.title:
        return f"The strongest retrieved source points to {top_source.title}."
    return ""


def build_source_context(sources: list[SourceRecord]) -> str:
    if not sources:
        return "No external sources were retrieved for this question."
    lines = []
    for source in sources[:4]:
        lines.append(
            f"- {source.title} | {source.url}\n"
            f"  Snippet: {normalize_answer_snippet(source.snippet) or source.snippet.strip() or 'No snippet available.'}"
        )
    return "\n".join(lines)


def answer_question_with_llm(question: str, sources: list[SourceRecord], binary_question: bool) -> str:
    if not groq_client:
        return ""
    system_prompt = (
        "You answer user questions directly and clearly.\n"
        "Rules:\n"
        "- Give the actual answer first, not a review of the question.\n"
        "- If the question is yes/no, start with Yes., No., or Partly., then explain.\n"
        "- If the user's assumption is wrong, correct it explicitly.\n"
        "- If source snippets are provided, use them when helpful.\n"
        "- If no sources are available, still answer from general knowledge when the answer is well known.\n"
        "- Do not mention prompts, tools, models, verification pipelines, or internal process.\n"
        "- Do not use headings or bullet points.\n"
        "- Keep the answer concise but actually useful."
    )
    user_prompt = (
        f"Question: {question}\n"
        f"Question type: {'yes/no' if binary_question else 'open-ended'}\n"
        f"Retrieved source context:\n{build_source_context(sources)}"
    )
    try:
        response = groq_client.chat.completions.create(
            model=QUESTION_ANSWER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=280,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        return ""


def build_question_reply(effective_message: str, task_profile: dict, claims: list[str], sources: list[SourceRecord]) -> str:
    mcq_data = parse_mcq_prompt(effective_message)
    claim_checks = build_claim_checks(claims, sources)
    evidence_label, evidence_reason = determine_evidence_strength(sources)
    corrected_answer = build_corrected_answer(task_profile, claims, sources, mcq_data)
    supported = sum("Supported" in item and "Partially" not in item for item in claim_checks)
    partial = sum("Partially Supported" in item for item in claim_checks)
    binary_question = looks_like_yes_no_question(effective_message)
    llm_answer = answer_question_with_llm(effective_message, sources, binary_question)

    if llm_answer:
        answer = llm_answer
    elif corrected_answer:
        if binary_question:
            prefix = "Yes." if supported else "Probably not." if partial else "No."
            answer = f"{prefix} {corrected_answer}"
        else:
            answer = corrected_answer
    elif supported:
        answer = "The retrieved sources support this."
    elif partial:
        answer = "The retrieved sources only partially support this, so the answer is still uncertain."
    else:
        answer = "I could not verify this from strong sources in this run."

    sections = [("## Answer", answer)]
    if sources:
        verification_bits = [f"{evidence_label} evidence strength. {evidence_reason}"]
        if not any(source.credibility_tier == "Very High" for source in sources):
            verification_bits.append("The source mix is useful, but not anchored by the strongest institutions.")
        if len({source.claim for source in sources}) < len(claims):
            verification_bits.append("Not every part of the prompt found its own supporting source.")
        sections.append(("## Verification", " ".join(verification_bits)))
        sections.append(("## What I Checked", join_bullets(claim_checks, "No claim-level verification was possible.")))
        sections.append(("## Sources & References", render_sources_markdown(sources)))
    else:
        sections.append(
            (
                "## Verification",
                "No strong live sources were retrieved for this answer, so this response is coming from the model's general knowledge rather than a successful external fact-check.",
            )
        )
    return format_sections(sections)


def build_confidence(task_profile: dict, sources: list[SourceRecord], base_score: int) -> str:
    confidence = 55 + (base_score * 4)
    if task_profile.get("needs_evidence"):
        evidence_label, evidence_reason = determine_evidence_strength(sources)
        confidence += 10 if evidence_label == "Strong" else 2 if evidence_label == "Moderate" else -10
        confidence = clamp(confidence, 25, 95)
        return f"{confidence}% - {evidence_reason}"
    confidence = clamp(confidence, 45, 92)
    return f"{confidence}% - based on deterministic rubric scoring of the provided text."


def build_consensus_header(task_profile: dict) -> tuple[str, str]:
    best_answer = (
        "Deterministic consensus engine. This run used local rubric scoring"
        + (" plus retrieved source metadata." if task_profile.get("needs_evidence") else ".")
    )
    contradictions = (
        "No model-to-model contradiction analysis was used. Only gaps or conflicts in the available evidence were considered."
        if task_profile.get("needs_evidence")
        else "No model-to-model contradictions were generated because deterministic mode was used."
    )
    return best_answer, contradictions


def build_judge_reply(effective_message: str, task_profile: dict, sources: list[SourceRecord]) -> str:
    kind = task_profile.get("kind", "general")
    assessment = analyze_code_quality(effective_message) if kind == "code" else analyze_text_quality(effective_message, kind)
    best_answer, contradictions = build_consensus_header(task_profile)
    sections = [
        ("## Best Answer", best_answer),
        ("## Contradictions", contradictions),
        ("## Confidence Score", build_confidence(task_profile, sources, assessment["score"])),
        ("## Final Consensus Verdict", assessment["verdict"]),
        ("## Strengths", join_bullets(assessment["strengths"], "The input is clear enough to assess.")),
        ("## Risks", join_bullets(assessment["risks"], "No major structural risk was detected.")),
        ("## Next Steps", join_bullets(assessment["next_steps"], "Add more specificity so the next judgment can go deeper.")),
    ]
    if task_profile.get("needs_evidence"):
        claim_checks = build_claim_checks(extract_claims_for_review(effective_message, task_profile), sources)
        sections.extend(
            [
                ("## Source Quality", summarize_source_quality(sources)),
                ("## Claim Check", join_bullets(claim_checks, "No claim-level verification was possible.")),
                ("## Sources & References", render_sources_markdown(sources)),
            ]
        )
    return format_sections(sections)


def build_feedback_reply(effective_message: str, task_profile: dict, sources: list[SourceRecord]) -> str:
    kind = task_profile.get("kind", "general")
    assessment = analyze_code_quality(effective_message) if kind == "code" else analyze_text_quality(effective_message, kind)
    best_answer, contradictions = build_consensus_header(task_profile)
    sections = [
        ("## Best Answer", best_answer),
        ("## Contradictions", contradictions),
        ("## Confidence Score", build_confidence(task_profile, sources, assessment["score"])),
        ("## Final Consensus Verdict", assessment["verdict"]),
        ("## Strengths", join_bullets(assessment["strengths"], "The input is understandable.")),
        ("## Areas for Improvement", join_bullets(assessment["risks"], "The next improvement is adding more concrete detail.")),
        ("## Actionable Steps", join_bullets(assessment["next_steps"], "Revise the weakest part first, then rerun the review.")),
    ]
    if task_profile.get("needs_evidence"):
        sections.extend([("## Source Quality", summarize_source_quality(sources)), ("## Sources & References", render_sources_markdown(sources))])
    return format_sections(sections)


def build_analyze_reply(effective_message: str, task_profile: dict, sources: list[SourceRecord]) -> str:
    kind = task_profile.get("kind", "general")
    assessment = analyze_code_quality(effective_message) if kind == "code" else analyze_text_quality(effective_message, kind)
    best_answer, contradictions = build_consensus_header(task_profile)
    core_concept = (
        "The input is executable logic, so the main lens is correctness plus failure handling."
        if kind == "code"
        else "The input communicates a main idea that can be judged for clarity, structure, and support."
    )
    logical_structure = (
        "Imports, definitions, and control flow should stay separated so side effects remain predictable."
        if kind == "code"
        else "The strongest parts are the explicit claims and the connective reasoning between them."
    )
    sections = [
        ("## Best Answer", best_answer),
        ("## Contradictions", contradictions),
        ("## Confidence Score", build_confidence(task_profile, sources, assessment["score"])),
        ("## Final Consensus Verdict", assessment["verdict"]),
        ("## Core Concept", core_concept),
        ("## Logical Structure", logical_structure),
        ("## Deep Insights", join_bullets(assessment["risks"], "The biggest hidden issue is missing context.")),
    ]
    if task_profile.get("needs_evidence"):
        sections.extend([("## Source Quality", summarize_source_quality(sources)), ("## Sources & References", render_sources_markdown(sources))])
    return format_sections(sections)


def build_compare_reply(effective_message: str, task_profile: dict, sources: list[SourceRecord]) -> str:
    assessment = analyze_comparison_request(effective_message)
    best_answer, contradictions = build_consensus_header(task_profile)
    sections = [
        ("## Best Answer", best_answer),
        ("## Contradictions", contradictions),
        ("## Confidence Score", build_confidence(task_profile, sources, assessment["score"])),
        ("## Final Consensus Verdict", assessment["verdict"]),
        ("## A vs B Breakdown", assessment["breakdown"]),
        ("## Pros and Cons", join_bullets(assessment["pros_and_cons"], "The tradeoff space still needs clearer criteria.")),
        ("## Final Recommendation", assessment["recommendation"]),
    ]
    if task_profile.get("needs_evidence"):
        sections.extend([("## Source Quality", summarize_source_quality(sources)), ("## Sources & References", render_sources_markdown(sources))])
    return format_sections(sections)


def build_credibility_reply(effective_message: str, task_profile: dict, claims: list[str], sources: list[SourceRecord]) -> str:
    mcq_data = parse_mcq_prompt(effective_message)
    claim_checks = build_claim_checks(claims, sources)
    evidence_label, evidence_reason = determine_evidence_strength(sources)
    best_answer, contradictions = build_consensus_header(task_profile)
    corrected_answer = build_corrected_answer(task_profile, claims, sources, mcq_data)
    supported = sum("Supported" in item and "Partially" not in item for item in claim_checks)
    partial = sum("Partially Supported" in item for item in claim_checks)
    if supported:
        verdict = "The claim is credible enough to treat as provisionally supported by the retrieved sources."
    elif partial:
        verdict = "The claim has some support, but the evidence is incomplete and should not be treated as settled."
    else:
        verdict = "The claim is not verified by this run because the evidence is weak, missing, or too indirect."
    if corrected_answer:
        verdict = f"{corrected_answer} {verdict}"
    gaps = []
    if not sources:
        gaps.append("No credible external source was retrieved, so the answer is deterministic but not verified.")
    else:
        if not any(source.credibility_tier == "Very High" for source in sources):
            gaps.append("The source mix is usable but not anchored by the strongest available institutions.")
        if len({source.claim for source in sources}) < len(claims):
            gaps.append("Not every claim found its own supporting source, so some parts remain unverified.")
        gaps.append("Search results can miss paywalled, recent, or more authoritative sources that did not appear in the RSS feed.")
    sections = [
        ("## Best Answer", best_answer),
        ("## Contradictions", contradictions),
        ("## Confidence Score", build_confidence(task_profile, sources, 7 if sources else 4)),
        ("## Final Consensus Verdict", verdict),
    ]
    if mcq_data:
        correct_option, option_reason = choose_mcq_option(mcq_data, sources)
        sections.append(("## Correct Option", f"{correct_option}\n\n{option_reason}"))
    sections.extend(
        [
            ("## Claim Check", join_bullets(claim_checks, "No claim-level verification was possible.")),
            ("## Evidence Strength", f"{evidence_label} - {evidence_reason}"),
            ("## Counter-Evidence & Gaps", join_bullets(gaps, "No specific counter-evidence was retrieved, but the evidence pool is still limited.")),
            ("## Source Quality", summarize_source_quality(sources)),
            ("## Sources & References", render_sources_markdown(sources)),
        ]
    )
    return format_sections(sections)


def get_ai_response(user_message: str, history: list, model: str = "consensus", mode: str = "judge") -> EvaluationResult:
    effective_message = build_effective_user_message(user_message, history)
    task_profile = infer_task_profile(effective_message, mode)
    claims, sources = collect_sources(effective_message, task_profile)
    if task_profile.get("kind") == "question" and mode != "credibility":
        reply = build_question_reply(effective_message, task_profile, claims, sources)
    elif mode == "credibility" or task_profile.get("kind") == "mcq":
        reply = build_credibility_reply(effective_message, task_profile, claims, sources)
    elif mode == "feedback":
        reply = build_feedback_reply(effective_message, task_profile, sources)
    elif mode == "analyze":
        reply = build_analyze_reply(effective_message, task_profile, sources)
    elif mode == "compare":
        reply = build_compare_reply(effective_message, task_profile, sources)
    else:
        reply = build_judge_reply(effective_message, task_profile, sources)
    return EvaluationResult(
        reply=reply,
        model_used="deterministic-consensus",
        sources=[source.to_dict() for source in sources],
        task_kind=task_profile.get("kind", "general"),
    )
