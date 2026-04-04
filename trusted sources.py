"""
Trusted Sources Registry
Weighted credibility scores for each source type.
Higher = more authoritative.
"""

TRUSTED_SOURCES = {
    # ─── PEER-REVIEWED / ACADEMIC ───────────────────────────────────────────
    "pubmed": {
        "base_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
        "search_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        "fetch_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
        "abstract_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        "trust_score": 0.97,
        "category": "academic",
        "label": "PubMed / NCBI",
        "description": "NIH's biomedical research database (peer-reviewed)",
        "requires_key": False,
    },
    "semantic_scholar": {
        "base_url": "https://api.semanticscholar.org/graph/v1",
        "search_url": "https://api.semanticscholar.org/graph/v1/paper/search",
        "trust_score": 0.95,
        "category": "academic",
        "label": "Semantic Scholar",
        "description": "AI-powered research literature database",
        "requires_key": False,   # free tier available
    },
    "crossref": {
        "base_url": "https://api.crossref.org",
        "search_url": "https://api.crossref.org/works",
        "trust_score": 0.94,
        "category": "academic",
        "label": "CrossRef DOI",
        "description": "DOI-based scholarly metadata",
        "requires_key": False,
    },
    "arxiv": {
        "base_url": "http://export.arxiv.org/api/query",
        "trust_score": 0.85,
        "category": "preprint",
        "label": "arXiv",
        "description": "Preprints (CS, Physics, Math, Biology)",
        "requires_key": False,
    },

    # ─── GOVERNMENT & HEALTH AUTHORITIES ────────────────────────────────────
    "who": {
        "base_url": "https://www.who.int",
        "trust_score": 0.96,
        "category": "health_authority",
        "label": "WHO",
        "description": "World Health Organization",
        "search_via": "google_cse",
        "cse_site": "who.int",
    },
    "cdc": {
        "base_url": "https://www.cdc.gov",
        "trust_score": 0.96,
        "category": "health_authority",
        "label": "CDC",
        "description": "US Centers for Disease Control",
        "search_via": "google_cse",
        "cse_site": "cdc.gov",
    },
    "nih": {
        "base_url": "https://www.nih.gov",
        "trust_score": 0.95,
        "category": "health_authority",
        "label": "NIH",
        "description": "National Institutes of Health",
    },
    "nasa": {
        "base_url": "https://api.nasa.gov",
        "trust_score": 0.96,
        "category": "science_authority",
        "label": "NASA",
        "description": "US National Aeronautics and Space Administration",
    },
    "noaa": {
        "base_url": "https://www.ncdc.noaa.gov/cdo-web/api/v2",
        "trust_score": 0.95,
        "category": "science_authority",
        "label": "NOAA",
        "description": "National Oceanic and Atmospheric Administration",
    },

    # ─── ENCYCLOPAEDIC ──────────────────────────────────────────────────────
    "wikipedia": {
        "base_url": "https://en.wikipedia.org/api/rest_v1",
        "search_url": "https://en.wikipedia.org/w/api.php",
        "trust_score": 0.72,
        "category": "encyclopaedic",
        "label": "Wikipedia",
        "description": "Community-edited encyclopedia (used as initial context only)",
    },
    "wikidata": {
        "base_url": "https://www.wikidata.org/w/api.php",
        "sparql_url": "https://query.wikidata.org/sparql",
        "trust_score": 0.75,
        "category": "encyclopaedic",
        "label": "Wikidata",
        "description": "Structured knowledge base (facts, dates, figures)",
    },

    # ─── FACT-CHECKERS ───────────────────────────────────────────────────────
    "snopes": {
        "base_url": "https://www.snopes.com",
        "trust_score": 0.88,
        "category": "fact_checker",
        "label": "Snopes",
        "description": "Established fact-checking site",
        "search_via": "serp",
    },
    "factcheck_org": {
        "base_url": "https://www.factcheck.org",
        "trust_score": 0.90,
        "category": "fact_checker",
        "label": "FactCheck.org",
        "description": "Non-partisan fact-checking by Annenberg",
        "search_via": "serp",
    },
    "politifact": {
        "base_url": "https://www.politifact.com",
        "trust_score": 0.87,
        "category": "fact_checker",
        "label": "PolitiFact",
        "description": "Fact-checking for political claims",
        "search_via": "serp",
    },

    # ─── NEWS / WIRE SERVICES ────────────────────────────────────────────────
    "reuters": {
        "trust_score": 0.91,
        "category": "news",
        "label": "Reuters",
        "description": "International news agency",
    },
    "ap_news": {
        "trust_score": 0.91,
        "category": "news",
        "label": "AP News",
        "description": "Associated Press wire service",
    },
    "bbc": {
        "trust_score": 0.88,
        "category": "news",
        "label": "BBC",
        "description": "British Broadcasting Corporation",
    },
}

# Category weight multipliers applied on top of base trust scores
CATEGORY_WEIGHTS = {
    "academic": 1.0,
    "preprint": 0.87,
    "health_authority": 1.0,
    "science_authority": 0.98,
    "encyclopaedic": 0.75,
    "fact_checker": 0.92,
    "news": 0.85,
}

def get_source_config(source_key: str) -> dict:
    return TRUSTED_SOURCES.get(source_key, {})

def get_effective_trust(source_key: str) -> float:
    src = TRUSTED_SOURCES.get(source_key, {})
    base = src.get("trust_score", 0.5)
    cat = src.get("category", "unknown")
    multiplier = CATEGORY_WEIGHTS.get(cat, 0.7)
    return round(min(base * multiplier, 1.0), 3)

def list_sources_by_category() -> dict:
    result = {}
    for key, val in TRUSTED_SOURCES.items():
        cat = val["category"]
        result.setdefault(cat, []).append({
            "key": key,
            "label": val["label"],
            "trust_score": get_effective_trust(key),
        })
    return result