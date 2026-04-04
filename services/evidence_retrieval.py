"""
Evidence Retrieval Service
Fetches real evidence from:
  - PubMed (biomedical research papers)
  - Semantic Scholar (cross-domain academic papers)
  - CrossRef (DOI metadata)
  - arXiv (preprints)
  - Wikidata (structured facts)
  - Wikipedia (context)
  - SERP (fact-checker sites via SerpAPI/Brave Search)
"""

import httpx
import asyncio
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional
from services.trusted_sources import TRUSTED_SOURCES, get_effective_trust

SERP_API_KEY = os.getenv("SERP_API_KEY", "")      # SerpAPI or Brave Search
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")       # Free from NCBI (higher rate limit)
SS_API_KEY   = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")  # Optional, free

TIMEOUT = httpx.Timeout(15.0)
HEADERS  = {"User-Agent": "FactShield/2.0 (factshield@example.com)"}

# ─── PUBMED ──────────────────────────────────────────────────────────────────

async def search_pubmed(query: str, max_results: int = 5) -> List[Dict]:
    """Search PubMed via NCBI Entrez API and fetch abstracts."""
    cfg = TRUSTED_SOURCES["pubmed"]
    params = {
        "db": "pubmed", "term": query, "retmax": max_results,
        "retmode": "json", "sort": "relevance",
    }
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        # Step 1: search IDs
        r = await client.get(cfg["search_url"], params=params)
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        # Step 2: fetch abstracts
        fetch_params = {
            "db": "pubmed", "id": ",".join(ids),
            "retmode": "xml", "rettype": "abstract",
        }
        if NCBI_API_KEY:
            fetch_params["api_key"] = NCBI_API_KEY

        rf = await client.get(cfg["abstract_url"], params=fetch_params)
        rf.raise_for_status()

    return _parse_pubmed_xml(rf.text)

def _parse_pubmed_xml(xml_text: str) -> List[Dict]:
    root = ET.fromstring(xml_text)
    results = []
    for article in root.findall(".//PubmedArticle"):
        try:
            pmid = article.findtext(".//PMID", "")
            title = article.findtext(".//ArticleTitle", "No title")
            # Journal
            journal = article.findtext(".//Journal/Title", "")
            year = article.findtext(".//PubDate/Year", "")
            # Abstract
            abstract_parts = article.findall(".//AbstractText")
            abstract = " ".join(a.text or "" for a in abstract_parts)
            # Authors
            authors = [
                f"{a.findtext('LastName','')} {a.findtext('Initials','')}"
                for a in article.findall(".//Author")[:3]
            ]
            results.append({
                "source_key": "pubmed",
                "source_label": "PubMed",
                "trust_score": get_effective_trust("pubmed"),
                "title": title,
                "abstract": abstract[:800] if abstract else "",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "pmid": pmid,
                "journal": journal,
                "year": year,
                "authors": authors,
                "category": "academic",
                "retrieved_at": datetime.utcnow().isoformat(),
            })
        except Exception:
            continue
    return results

# ─── SEMANTIC SCHOLAR ─────────────────────────────────────────────────────────

async def search_semantic_scholar(query: str, max_results: int = 5) -> List[Dict]:
    cfg = TRUSTED_SOURCES["semantic_scholar"]
    params = {
        "query": query, "limit": max_results,
        "fields": "title,abstract,authors,year,venue,externalIds,openAccessPdf,citationCount",
    }
    headers = {**HEADERS}
    if SS_API_KEY:
        headers["x-api-key"] = SS_API_KEY

    async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
        r = await client.get(cfg["search_url"], params=params)
        r.raise_for_status()
        papers = r.json().get("data", [])

    results = []
    for p in papers:
        doi = (p.get("externalIds") or {}).get("DOI", "")
        pdf_url = (p.get("openAccessPdf") or {}).get("url", "")
        results.append({
            "source_key": "semantic_scholar",
            "source_label": "Semantic Scholar",
            "trust_score": get_effective_trust("semantic_scholar"),
            "title": p.get("title", ""),
            "abstract": (p.get("abstract") or "")[:800],
            "url": pdf_url or (f"https://doi.org/{doi}" if doi else ""),
            "doi": doi,
            "year": p.get("year"),
            "venue": p.get("venue", ""),
            "authors": [a["name"] for a in (p.get("authors") or [])[:3]],
            "citation_count": p.get("citationCount", 0),
            "category": "academic",
            "retrieved_at": datetime.utcnow().isoformat(),
        })
    return results

# ─── CROSSREF ────────────────────────────────────────────────────────────────

async def search_crossref(query: str, max_results: int = 3) -> List[Dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        r = await client.get(
            TRUSTED_SOURCES["crossref"]["search_url"],
            params={"query": query, "rows": max_results, "select": "DOI,title,abstract,author,published,container-title,score"}
        )
        r.raise_for_status()
        items = r.json().get("message", {}).get("items", [])

    results = []
    for item in items:
        doi = item.get("DOI", "")
        year = ""
        pub = item.get("published", {}).get("date-parts", [[]])
        if pub and pub[0]:
            year = str(pub[0][0])
        results.append({
            "source_key": "crossref",
            "source_label": "CrossRef",
            "trust_score": get_effective_trust("crossref"),
            "title": (item.get("title") or [""])[0],
            "abstract": (item.get("abstract") or "")[:500],
            "url": f"https://doi.org/{doi}",
            "doi": doi,
            "year": year,
            "journal": (item.get("container-title") or [""])[0],
            "authors": [
                f"{a.get('given','')} {a.get('family','')}".strip()
                for a in (item.get("author") or [])[:3]
            ],
            "category": "academic",
            "retrieved_at": datetime.utcnow().isoformat(),
        })
    return results

# ─── ARXIV ───────────────────────────────────────────────────────────────────

async def search_arxiv(query: str, max_results: int = 3) -> List[Dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        r = await client.get(
            TRUSTED_SOURCES["arxiv"]["base_url"],
            params={"search_query": f"all:{query}", "max_results": max_results, "sortBy": "relevance"}
        )
        r.raise_for_status()

    root = ET.fromstring(r.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", "", ns) or "").strip()
        abstract = (entry.findtext("atom:summary", "", ns) or "").strip()[:800]
        url = entry.findtext("atom:id", "", ns)
        published = entry.findtext("atom:published", "", ns)[:4] if entry.findtext("atom:published") else ""
        authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)[:3]]
        results.append({
            "source_key": "arxiv",
            "source_label": "arXiv",
            "trust_score": get_effective_trust("arxiv"),
            "title": title,
            "abstract": abstract,
            "url": url,
            "year": published,
            "authors": authors,
            "category": "preprint",
            "retrieved_at": datetime.utcnow().isoformat(),
        })
    return results

# ─── WIKIDATA ─────────────────────────────────────────────────────────────────

async def query_wikidata(claim_text: str) -> List[Dict]:
    """Get structured facts from Wikidata using keyword extraction."""
    params = {
        "action": "wbsearchentities",
        "search": claim_text[:100],
        "language": "en",
        "format": "json",
        "limit": 3,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        r = await client.get(TRUSTED_SOURCES["wikidata"]["base_url"], params=params)
        r.raise_for_status()
        entities = r.json().get("search", [])

    results = []
    for ent in entities[:2]:
        results.append({
            "source_key": "wikidata",
            "source_label": "Wikidata",
            "trust_score": get_effective_trust("wikidata"),
            "title": ent.get("label", ""),
            "abstract": ent.get("description", ""),
            "url": ent.get("concepturi", ""),
            "category": "encyclopaedic",
            "retrieved_at": datetime.utcnow().isoformat(),
        })
    return results

# ─── WIKIPEDIA ───────────────────────────────────────────────────────────────

async def search_wikipedia(query: str) -> List[Dict]:
    params = {
        "action": "query", "list": "search",
        "srsearch": query, "srlimit": 3,
        "srprop": "snippet|titlesnippet",
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        r = await client.get(TRUSTED_SOURCES["wikipedia"]["search_url"], params=params)
        r.raise_for_status()
        items = r.json().get("query", {}).get("search", [])

    results = []
    for item in items:
        title = item.get("title", "")
        snippet = item.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")
        results.append({
            "source_key": "wikipedia",
            "source_label": "Wikipedia",
            "trust_score": get_effective_trust("wikipedia"),
            "title": title,
            "abstract": snippet,
            "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
            "category": "encyclopaedic",
            "retrieved_at": datetime.utcnow().isoformat(),
        })
    return results

# ─── FACT-CHECKERS via SerpAPI ────────────────────────────────────────────────

FACT_CHECK_SITES = ["snopes.com", "factcheck.org", "politifact.com", "reuters.com/fact-check"]

async def search_fact_checkers(query: str) -> List[Dict]:
    """Search established fact-checker sites via SerpAPI (or Brave Search)."""
    if not SERP_API_KEY:
        return []

    results = []
    for site in FACT_CHECK_SITES[:2]:
        params = {
            "api_key": SERP_API_KEY,
            "q": f"site:{site} {query}",
            "num": 2,
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.get("https://serpapi.com/search", params=params)
                r.raise_for_status()
                organic = r.json().get("organic_results", [])
                for item in organic[:2]:
                    src_key = site.replace(".com", "").replace(".org", "").replace("/fact-check", "").replace(".", "_")
                    results.append({
                        "source_key": src_key,
                        "source_label": site.split(".")[0].capitalize(),
                        "trust_score": 0.88,
                        "title": item.get("title", ""),
                        "abstract": item.get("snippet", ""),
                        "url": item.get("link", ""),
                        "category": "fact_checker",
                        "retrieved_at": datetime.utcnow().isoformat(),
                    })
        except Exception:
            continue
    return results

# ─── MASTER RETRIEVAL ─────────────────────────────────────────────────────────

async def retrieve_all_evidence(claim: str, claim_category: str = "general") -> List[Dict]:
    """
    Retrieve evidence from all sources in parallel.
    Returns a deduplicated, sorted list of evidence items.
    """
    tasks = []

    # Always search Wikipedia & Wikidata for context
    tasks.append(search_wikipedia(claim))
    tasks.append(query_wikidata(claim))

    # Academic sources (always)
    tasks.append(search_pubmed(claim, max_results=4))
    tasks.append(search_semantic_scholar(claim, max_results=4))
    tasks.append(search_crossref(claim, max_results=3))

    # arXiv for tech/science claims
    if claim_category in ("science", "technology", "health", "general"):
        tasks.append(search_arxiv(claim, max_results=2))

    # Fact-checkers
    tasks.append(search_fact_checkers(claim))

    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten and filter errors
    all_evidence = []
    for batch in raw_results:
        if isinstance(batch, Exception):
            continue
        all_evidence.extend(batch)

    # Deduplicate by URL
    seen_urls = set()
    unique_evidence = []
    for ev in all_evidence:
        url = ev.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_evidence.append(ev)

    # Sort by trust score descending
    unique_evidence.sort(key=lambda x: x.get("trust_score", 0), reverse=True)
    return unique_evidence