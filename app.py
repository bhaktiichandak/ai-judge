"""
FactShield — Streamlit Frontend
"""

import streamlit as st
import requests
import uuid
import time
from datetime import datetime

API_BASE = "http://localhost:8000/api"

st.set_page_config(
    page_title="FactShield",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
  .verdict-TRUE    { background:#d1fae5; color:#065f46; border-radius:8px; padding:6px 14px; font-weight:700; }
  .verdict-FALSE   { background:#fee2e2; color:#991b1b; border-radius:8px; padding:6px 14px; font-weight:700; }
  .verdict-PARTIALLY_TRUE { background:#fef3c7; color:#92400e; border-radius:8px; padding:6px 14px; font-weight:700; }
  .verdict-MISLEADING     { background:#ede9fe; color:#4c1d95; border-radius:8px; padding:6px 14px; font-weight:700; }
  .verdict-UNVERIFIABLE   { background:#f3f4f6; color:#374151; border-radius:8px; padding:6px 14px; font-weight:700; }
  .source-badge { display:inline-block; background:#e0f2fe; color:#0369a1; border-radius:999px; padding:3px 10px; font-size:12px; margin:2px; }
  .academic-badge { background:#f0fdf4; color:#166534; }
  .evidence-card { border:1px solid #e5e7eb; border-radius:12px; padding:14px; margin:8px 0; }
  .trust-high { color:#059669; font-weight:600; }
  .trust-med  { color:#d97706; font-weight:600; }
  .trust-low  { color:#dc2626; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ── Session ───────────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "history" not in st.session_state:
    st.session_state.history = []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ FactShield")
    st.caption("Multi-AI • Peer-reviewed sources • MongoDB Atlas")
    st.divider()

    st.markdown("**Source Tiers**")
    tier_info = {
        "🔬 Peer-reviewed": "PubMed, Semantic Scholar, CrossRef, arXiv",
        "🏛️ Gov / Health": "WHO, CDC, NIH, NASA, NOAA",
        "📖 Encyclopaedic": "Wikipedia, Wikidata",
        "✅ Fact-checkers": "Snopes, FactCheck.org, PolitiFact",
        "📰 News wires": "Reuters, AP News, BBC",
    }
    for tier, sources in tier_info.items():
        with st.expander(tier):
            st.caption(sources)

    st.divider()
    st.markdown("**AI Models**")
    st.markdown("• Gemini 1.5 Pro (40%)\n• GPT-4o-mini (35%)\n• LLaMA-3.3-70B (25%)")

    st.divider()
    if st.button("📜 View History", use_container_width=True):
        st.session_state.show_history = True

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🛡️ FactShield")
st.markdown("*AI-powered fact verification backed by peer-reviewed research & trusted sources*")
st.divider()

# ── Input ─────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col1:
    claim_input = st.text_area(
        "Enter a claim to verify",
        placeholder="e.g. 'Vitamin C cures the common cold' or 'The Great Wall of China is visible from space'",
        height=120,
        max_chars=2000,
    )
with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    verify_btn = st.button("🔍 Verify", type="primary", use_container_width=True)

# ── Verification ──────────────────────────────────────────────────────────────
if verify_btn and claim_input.strip():
    with st.spinner(""):
        progress = st.progress(0, text="🔬 Extracting claims...")
        time.sleep(0.3)
        progress.progress(15, text="📚 Searching PubMed, Semantic Scholar, arXiv...")
        time.sleep(0.3)
        progress.progress(35, text="🌐 Checking WHO, CDC, fact-checkers...")
        time.sleep(0.3)
        progress.progress(55, text="🤖 Running Gemini + GPT-4o + LLaMA ensemble...")
        time.sleep(0.3)
        progress.progress(80, text="💾 Scoring & saving to MongoDB Atlas...")

        try:
            resp = requests.post(
                f"{API_BASE}/verify/",
                json={"text": claim_input, "session_id": st.session_state.session_id},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            progress.progress(100, text="✅ Done!")
            time.sleep(0.4)
            progress.empty()
            st.session_state.history.insert(0, data)
        except requests.exceptions.ConnectionError:
            progress.empty()
            st.error("⚠️ Backend not running. Start with: `cd backend && python main.py`")
            st.stop()
        except Exception as e:
            progress.empty()
            st.error(f"Error: {e}")
            st.stop()

    # ── Results ───────────────────────────────────────────────────────────────
    st.divider()
    verdict = data["verdict"]
    confidence = data["confidence"]
    verdict_colors = {
        "TRUE": "🟢", "FALSE": "🔴", "PARTIALLY_TRUE": "🟡",
        "MISLEADING": "🟣", "UNVERIFIABLE": "⚪",
    }
    emoji = verdict_colors.get(verdict, "⚪")

    col_v, col_c, col_e, col_t = st.columns(4)
    with col_v:
        st.metric("Verdict", f"{emoji} {verdict.replace('_', ' ')}")
    with col_c:
        st.metric("Confidence", f"{confidence:.0%}")
    with col_e:
        st.metric("Evidence Found", data.get("evidence_count", 0))
    with col_t:
        st.metric("Processing", f"{data.get('processing_time_ms', 0)}ms")

    st.markdown(f"**Claim verified:** _{data['claim_text']}_")

    # Ensemble agreement
    agreement = data.get("ensemble_agreement", 0)
    if agreement > 0.65:
        st.success(f"✅ {agreement:.0%} model agreement across {', '.join(data.get('models_used', []))}")
    else:
        st.warning(f"⚠️ {agreement:.0%} model agreement — results have uncertainty")

    # Reasoning
    st.markdown("### 📝 Analysis")
    st.info(data.get("reasoning", "No reasoning provided."))

    if data.get("nuances"):
        st.markdown("**Important context/nuances:**")
        st.caption(data["nuances"])

    # Key facts
    if data.get("key_facts"):
        st.markdown("### 🔑 Key Facts")
        for fact in data["key_facts"]:
            st.markdown(f"• {fact}")

    # Evidence cards
    st.markdown(f"### 📚 Evidence ({data.get('academic_sources_count', 0)} peer-reviewed)")
    evidence_list = data.get("evidence", [])
    
    if evidence_list:
        tabs = st.tabs(["All Sources", "Academic", "Fact-checkers", "Encyclopaedic"])
        
        def render_evidence_cards(items):
            if not items:
                st.caption("No sources in this category.")
                return
            for ev in items:
                trust = ev.get("trust_score", 0)
                trust_class = "trust-high" if trust > 0.9 else ("trust-med" if trust > 0.75 else "trust-low")
                cat = ev.get("category", "")
                badge_cls = "source-badge academic-badge" if cat in ("academic", "preprint") else "source-badge"
                
                with st.expander(f"**{ev.get('source_label', 'Source')}** — {ev.get('title', 'Untitled')[:80]}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Trust Score", f"{trust:.2f}")
                    c2.metric("Relevance", f"{ev.get('relevance_score', 0):.2f}")
                    c3.metric("Category", cat.replace("_", " ").title())
                    
                    if ev.get("abstract"):
                        st.markdown(f"_{ev['abstract'][:400]}..._")
                    
                    meta = []
                    if ev.get("authors"):
                        meta.append(f"👤 {', '.join(ev['authors'][:2])}")
                    if ev.get("year"):
                        meta.append(f"📅 {ev['year']}")
                    if ev.get("journal"):
                        meta.append(f"📖 {ev['journal']}")
                    if ev.get("doi"):
                        meta.append(f"DOI: {ev['doi']}")
                    if meta:
                        st.caption(" | ".join(meta))
                    
                    if ev.get("url"):
                        st.markdown(f"[🔗 View Source]({ev['url']})")

        with tabs[0]:
            render_evidence_cards(evidence_list)
        with tabs[1]:
            render_evidence_cards([e for e in evidence_list if e.get("category") in ("academic", "preprint", "health_authority", "science_authority")])
        with tabs[2]:
            render_evidence_cards([e for e in evidence_list if e.get("category") == "fact_checker"])
        with tabs[3]:
            render_evidence_cards([e for e in evidence_list if e.get("category") == "encyclopaedic"])

    # Source credibility
    src_score = data.get("source_credibility_score", 0)
    st.markdown("### 🏆 Source Credibility")
    st.progress(src_score, text=f"Source credibility: {src_score:.0%} (based on peer-reviewed citations)")

    # Claim ID for sharing
    st.caption(f"Claim ID: `{data['claim_id']}` | Session: `{st.session_state.session_id[:8]}...`")

# ── History sidebar panel ─────────────────────────────────────────────────────
if st.session_state.get("show_history") and st.session_state.history:
    st.divider()
    st.markdown("### 📜 Session History")
    for item in st.session_state.history[:10]:
        verdict = item.get("verdict", "UNVERIFIABLE")
        emojis = {"TRUE": "🟢", "FALSE": "🔴", "PARTIALLY_TRUE": "🟡", "MISLEADING": "🟣", "UNVERIFIABLE": "⚪"}
        st.markdown(f"{emojis.get(verdict,'⚪')} **{verdict}** — _{item.get('claim_text','')[:80]}_")

elif not claim_input and not st.session_state.history:
    # Landing info
    st.markdown("### How FactShield works")
    cols = st.columns(4)
    steps = [
        ("🔬", "Extract", "AI identifies the core factual claim"),
        ("📡", "Retrieve", "Searches PubMed, Semantic Scholar, WHO, CDC, fact-checkers"),
        ("🤖", "Verify", "3 AI models analyze evidence independently"),
        ("📊", "Decide", "Ensemble scoring produces final verdict + confidence"),
    ]
    for col, (icon, title, desc) in zip(cols, steps):
        with col:
            st.markdown(f"**{icon} {title}**")
            st.caption(desc)