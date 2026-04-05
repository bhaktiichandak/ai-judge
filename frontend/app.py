import os
import re
import html
from pathlib import Path
from uuid import uuid4

import requests
import streamlit as st
from dotenv import load_dotenv

try:
    from frontend.sidebar import render_sidebar
except ImportError:
    from sidebar import render_sidebar


env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


st.set_page_config(
    page_title="FactForge",
    page_icon="F",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

:root {
    --ff-canvas: #1e1e1e;
    --ff-surface: #252526;
    --ff-surface-strong: #2d2d30;
    --ff-surface-soft: #31343a;
    --ff-ink: #d4d4d4;
    --ff-muted: #9da5b4;
    --ff-line: rgba(255, 255, 255, 0.08);
    --ff-accent: #3794ff;
    --ff-accent-deep: #0e639c;
    --ff-accent-soft: rgba(55, 148, 255, 0.14);
    --ff-shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
}

*, *::before, *::after {
    font-family: 'Manrope', sans-serif !important;
    box-sizing: border-box;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.03em;
}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display: none !important;
}

.stApp {
    background:
        radial-gradient(circle at top right, rgba(55, 148, 255, 0.12), transparent 24%),
        radial-gradient(circle at top left, rgba(14, 99, 156, 0.10), transparent 22%),
        linear-gradient(180deg, #1b1b1c 0%, #1f1f22 100%);
    color: var(--ff-ink);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #181818 0%, #1e1e1e 100%) !important;
    border-right: 1px solid var(--ff-line) !important;
}

[data-testid="stSidebar"] > div {
    padding: 0 !important;
}

.block-container {
    padding: 1.8rem 2.4rem 7rem 2.4rem !important;
    max-width: 1040px !important;
    margin: 0 auto !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--ff-surface-strong) !important;
    border: 1px solid var(--ff-line) !important;
    border-radius: 18px !important;
    padding: 1.1rem 1.2rem !important;
    margin-bottom: 1rem !important;
    box-shadow: var(--ff-shadow) !important;
    color: var(--ff-ink) !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: linear-gradient(180deg, rgba(37, 37, 38, 0.98), rgba(31, 31, 34, 0.98)) !important;
    border: 1px solid rgba(55, 148, 255, 0.16) !important;
    border-radius: 18px !important;
    padding: 1.1rem 1.2rem !important;
    margin-bottom: 1rem !important;
    box-shadow: var(--ff-shadow) !important;
    color: var(--ff-ink) !important;
}

[data-testid="stChatInput"] textarea {
    background: var(--ff-surface-strong) !important;
    border: 1px solid var(--ff-line) !important;
    border-radius: 16px !important;
    color: var(--ff-ink) !important;
    font-size: 0.96rem !important;
    padding: 1rem 1rem !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(55, 148, 255, 0.38) !important;
    box-shadow: 0 0 0 3px rgba(55, 148, 255, 0.10) !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #7f8895 !important;
}

[data-testid="stSelectbox"] > div > div {
    background: var(--ff-surface) !important;
    border: 1px solid var(--ff-line) !important;
    border-radius: 12px !important;
    color: var(--ff-ink) !important;
    font-size: 0.875rem !important;
}

button[kind="secondary"] {
    background: var(--ff-surface) !important;
    border: 1px solid var(--ff-line) !important;
    border-radius: 12px !important;
    color: var(--ff-ink) !important;
    font-size: 0.84rem !important;
    transition: all 0.2s ease !important;
}

button[kind="secondary"]:hover {
    border-color: rgba(55, 148, 255, 0.28) !important;
    background: var(--ff-surface-soft) !important;
}

[data-testid="stMetric"] {
    background: var(--ff-surface) !important;
    border: 1px solid var(--ff-line) !important;
    border-radius: 14px !important;
    padding: 0.75rem 0.55rem !important;
    text-align: center !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.15rem !important;
    color: var(--ff-ink) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.7rem !important;
    color: var(--ff-muted) !important;
}

hr {
    border-color: var(--ff-line) !important;
    margin: 1rem 0 !important;
}

::-webkit-scrollbar {
    width: 5px;
}

::-webkit-scrollbar-track {
    background: #0f1217;
}

::-webkit-scrollbar-thumb {
    background: rgba(55, 148, 255, 0.22);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(55, 148, 255, 0.34);
}

[data-testid="stChatMessage"] p {
    color: inherit !important;
    font-size: 0.925rem !important;
    line-height: 1.7 !important;
}

[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3,
[data-testid="stChatMessage"] h4 {
    color: inherit !important;
}

[data-testid="stChatMessage"] code {
    background: rgba(55, 148, 255, 0.10) !important;
    color: #9cdcfe !important;
    border-radius: 8px !important;
    padding: 0.15rem 0.4rem !important;
    font-size: 0.85rem !important;
}

[data-testid="column"] button {
    height: 78px !important;
    background: var(--ff-surface) !important;
    border: 1px solid var(--ff-line) !important;
    border-radius: 14px !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
}

[data-testid="column"] button:hover {
    border-color: rgba(55, 148, 255, 0.32) !important;
    background: var(--ff-surface-soft) !important;
    transform: none;
}

[data-testid="column"] button p {
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: var(--ff-ink) !important;
    font-family: 'Manrope', sans-serif !important;
}

[data-testid="stMarkdownContainer"] a {
    color: #4fc1ff !important;
}

.ff-shell {
    animation: ff-rise 0.55s ease both;
}

.ff-hero {
    padding: 1.45rem 1.55rem;
    border-radius: 20px;
    border: 1px solid rgba(55, 148, 255, 0.16);
    background:
        linear-gradient(180deg, rgba(55, 148, 255, 0.06), rgba(55, 148, 255, 0.01)),
        var(--ff-surface);
    box-shadow: var(--ff-shadow);
}

.ff-hero::after {
    display: none;
}

.ff-brand-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: flex-start;
}

.ff-brand {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
}

.ff-mark {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    background: linear-gradient(180deg, var(--ff-accent), var(--ff-accent-deep));
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #f5fbff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.1rem;
    font-weight: 700;
    box-shadow: 0 12px 24px rgba(14, 99, 156, 0.28);
}

.ff-eyebrow {
    color: #75beff;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.68rem;
    font-weight: 700;
    margin-bottom: 0.45rem;
}

.ff-title {
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--ff-ink);
    font-size: clamp(2rem, 3vw, 3rem);
    line-height: 1;
    margin: 0 0 0.65rem 0;
}

.ff-subtitle {
    color: var(--ff-muted);
    font-size: 0.93rem;
    max-width: 640px;
    line-height: 1.6;
    margin: 0;
}

.ff-badge-row {
    display: flex;
    gap: 0.65rem;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.ff-badge {
    padding: 0.42rem 0.72rem;
    border-radius: 999px;
    border: 1px solid var(--ff-line);
    background: rgba(255, 255, 255, 0.03);
    color: var(--ff-ink);
    font-size: 0.74rem;
    font-weight: 700;
}

.ff-badge--forge {
    background: var(--ff-accent-soft);
    color: #dcebff;
    border-color: rgba(55, 148, 255, 0.26);
}

.ff-chip-row {
    display: flex;
    gap: 0.65rem;
    flex-wrap: wrap;
    margin: 1rem 0 0.2rem 0;
}

.ff-chip {
    padding: 0.38rem 0.68rem;
    border-radius: 999px;
    background: rgba(55, 148, 255, 0.08);
    border: 1px solid rgba(55, 148, 255, 0.14);
    color: #b8d9ff;
    font-size: 0.72rem;
    font-weight: 600;
}

.ff-empty {
    text-align: left;
    padding: 1.65rem 1.55rem 0.7rem 1.55rem;
    border-radius: 20px;
    border: 1px solid rgba(55, 148, 255, 0.12);
    background:
        linear-gradient(180deg, rgba(55, 148, 255, 0.04), transparent),
        var(--ff-surface);
    box-shadow: var(--ff-shadow);
    margin: 1.15rem 0 1rem 0;
}

.ff-empty-title {
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--ff-ink);
    font-size: 1.85rem;
    margin: 0 0 0.75rem 0;
}

.ff-empty-copy {
    color: var(--ff-muted);
    font-size: 0.98rem;
    line-height: 1.7;
    margin: 0 0 1rem 0;
    max-width: 700px;
}

.ff-prompt-card {
    display: none;
}

.ff-prompt-kicker {
    color: var(--ff-ember);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.67rem;
    font-weight: 800;
    margin-bottom: 0.45rem;
}

.ff-prompt-title {
    color: var(--ff-ink);
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
}

.ff-prompt-copy {
    color: var(--ff-muted);
    font-size: 0.84rem;
    line-height: 1.55;
}

.ff-section {
    background: var(--ff-surface);
    border: 1px solid var(--ff-line);
    border-radius: 18px;
    padding: 1rem 1rem 0.35rem 1rem;
    margin-top: 1rem;
    box-shadow: none;
}

.ff-section-title {
    color: #75beff;
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-weight: 700;
    margin-bottom: 0.7rem;
}

.ff-summary {
    border-radius: 18px;
    padding: 1rem 1rem 0.95rem 1rem;
    border: 1px solid var(--ff-line);
    min-height: 136px;
    box-shadow: none;
}

.ff-summary--verdict {
    background:
        linear-gradient(180deg, rgba(55, 148, 255, 0.10), rgba(55, 148, 255, 0.02)),
        var(--ff-surface-soft);
    color: var(--ff-ink);
    border-color: rgba(55, 148, 255, 0.24);
}

.ff-summary--light {
    background: var(--ff-surface);
    color: var(--ff-ink);
}

.ff-summary-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-weight: 800;
    opacity: 0.72;
    margin-bottom: 0.7rem;
}

.ff-summary-body {
    font-size: 0.95rem;
    line-height: 1.62;
    font-weight: 600;
}

@keyframes ff-rise {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@media (max-width: 900px) {
    .block-container {
        padding: 1.4rem 1rem 7rem 1rem !important;
    }
    .ff-brand-row {
        flex-direction: column;
    }
    .ff-badge-row {
        justify-content: flex-start;
    }
}

@media (max-width: 640px) {
    .ff-hero,
    .ff-empty {
        padding: 1.1rem 1rem;
        border-radius: 18px;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


SECTION_ALIASES = {
    "correct_option": ["## Correct Option"],
    "best_answer": ["## Best Answer", "## 🏆 Best Answer"],
    "contradictions": ["## Contradictions", "## 🔍 Contradictions"],
    "confidence": ["## Confidence Score", "## 💯 Confidence Score", "## 💯 Confidence"],
    "final_verdict": ["## Final Consensus Verdict", "## ⚖️ Final Consensus Verdict"],
    "strengths": ["## Strengths"],
    "areas_for_improvement": ["## Areas for Improvement"],
    "actionable_steps": ["## Actionable Steps"],
    "core_concept": ["## Core Concept"],
    "logical_structure": ["## Logical Structure"],
    "deep_insights": ["## Deep Insights"],
    "a_vs_b_breakdown": ["## A vs B Breakdown"],
    "pros_and_cons": ["## Pros and Cons"],
    "final_recommendation": ["## Final Recommendation"],
    "risks": ["## Risks"],
    "next_steps": ["## Next Steps"],
    "claim_check": ["## Claim Check"],
    "evidence_strength": ["## Evidence Strength"],
    "source_quality": ["## Source Quality"],
    "counter_gaps": ["## Counter-Evidence & Gaps", "## Counter-Evidence and Gaps"],
    "sources": ["## Sources & References", "## 📚 Sources & References"],
}


MODE_LABELS = {
    "judge": "Judge",
    "credibility": "Credibility",
    "feedback": "Feedback",
    "analyze": "Analyze",
    "compare": "Compare",
}


def normalize_query_param(value) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def ensure_chat_session_id() -> str:
    existing = normalize_query_param(st.session_state.get("chat_session_id")) or normalize_query_param(st.query_params.get("chat"))
    session_id = existing or uuid4().hex
    st.session_state.chat_session_id = session_id
    st.query_params["chat"] = session_id
    return session_id


def load_session_from_backend(session_id: str) -> None:
    try:
        response = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}", timeout=3)
        if response.ok:
            data = response.json()
            st.session_state.messages = data.get("messages", [])
            st.session_state.storage_backend = data.get("storage_backend", "local")
    except Exception:
        st.session_state.storage_backend = st.session_state.get("storage_backend", "local")


if "messages" not in st.session_state:
    st.session_state.messages = []

if "storage_backend" not in st.session_state:
    st.session_state.storage_backend = "local"

if "session_loaded" not in st.session_state:
    st.session_state.session_loaded = False


chat_session_id = ensure_chat_session_id()
if not st.session_state.session_loaded:
    load_session_from_backend(chat_session_id)
    st.session_state.session_loaded = True


config = render_sidebar()


storage_label = "Mongo Sync" if st.session_state.get("storage_backend") == "mongo" else "Local Draft"
mode_label = MODE_LABELS[config["mode"]]
st.markdown(
    f"""
    <div class="ff-shell">
        <div class="ff-hero">
            <div class="ff-brand-row">
                <div class="ff-brand">
                    <div class="ff-mark">FF</div>
                    <div>
                        <div class="ff-eyebrow">FactForge</div>
                        <div class="ff-title">Evidence, shaped into decisions.</div>
                        <p class="ff-subtitle">
                            FactForge reviews code, writing, product thinking, and factual claims with a polished
                            consensus workflow that feels more like a strategy desk than a disposable chat window.
                        </p>
                    </div>
                </div>
                <div class="ff-badge-row">
                    <div class="ff-badge ff-badge--forge">{mode_label}</div>
                    <div class="ff-badge">{storage_label}</div>
                    <div class="ff-badge">Source-aware</div>
                </div>
            </div>
            <div class="ff-chip-row">
                <div class="ff-chip">Deterministic review engine</div>
                <div class="ff-chip">Opinionated verdict layout</div>
                <div class="ff-chip">{len(st.session_state.messages)} messages in this workspace</div>
            </div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)


if not st.session_state.messages:
    st.markdown(
        """
        <div class="ff-empty">
            <div class="ff-eyebrow">Fresh Workspace</div>
            <h2 class="ff-empty-title">What do you want FactForge to pressure-test?</h2>
            <p class="ff-empty-copy">
                Choose a starting mode or paste directly into the input below.
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    st.caption("Starter modes")
    columns = st.columns(5)
    examples = [
        ("Essay", "Evaluate the quality of my writing", "an expert editor and professor"),
        ("Code", "Review my code for quality and bugs", "a senior software engineer"),
        ("Argument", "Judge the logic of my reasoning", "a master debater and logician"),
        ("Idea", "Rate the strength of my concept", "a startup founder and strategist"),
        ("Research", "Evaluate my research question or claim with credible evidence", "a meticulous fact-checker and research analyst"),
    ]

    for column, (title, description, persona) in zip(columns, examples):
        with column:
            if st.button(title, key=f"btn_{title}", use_container_width=True, help=description):
                setup_msg = (
                    f"System Instruction: The user selected the '{title}' category. "
                    f"You must now act as {persona}. Your primary goal is to {description.lower()}."
                )
                ack_msg = (
                    f"**{title} Forge Activated**\n\n"
                    f"FactForge is now responding as {persona}. Share your material and it will {description.lower()}."
                )
                st.session_state.messages.append({"role": "user", "content": setup_msg, "hidden": True})
                st.session_state.messages.append({"role": "assistant", "content": ack_msg})
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)


def parse_structured_sections(content: str) -> dict[str, str]:
    found_headers = []

    for key, aliases in SECTION_ALIASES.items():
        best_match = None
        for alias in aliases:
            index = content.find(alias)
            if index != -1 and (best_match is None or index < best_match[0]):
                best_match = (index, alias)
        if best_match:
            found_headers.append((best_match[0], key, best_match[1]))

    found_headers.sort(key=lambda item: item[0])
    sections: dict[str, str] = {}

    for idx, (_, key, alias) in enumerate(found_headers):
        start = content.find(alias) + len(alias)
        end = found_headers[idx + 1][0] if idx + 1 < len(found_headers) else len(content)
        value = content[start:end].strip()
        if value:
            sections[key] = value

    return sections


def format_inline_text(value: str) -> str:
    return html.escape(value).replace("\n", "<br>")


def render_summary_card(title: str, body: str, tone: str = "light") -> None:
    st.markdown(
        f"""
        <div class="ff-summary ff-summary--{tone}">
            <div class="ff-summary-label">{html.escape(title)}</div>
            <div class="ff-summary-body">{format_inline_text(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_detail_block(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="ff-section">
            <div class="ff-section-title">{html.escape(title)}</div>
        </div>
    """,
        unsafe_allow_html=True,
    )
    st.markdown(body)


def format_source_metadata(sources: list[dict]) -> str:
    if not sources:
        return (
            "- No credible external sources were returned by the backend.\n"
            "- This response should be treated as unverified."
        )

    lines = []
    for source in sources:
        snippet = (source.get("snippet") or "No snippet available.").replace("\n", " ").strip()
        if len(snippet) > 220:
            snippet = snippet[:217].rstrip() + "..."
        title = (source.get("title") or "Untitled source").replace("[", "\\[").replace("]", "\\]")
        lines.append(
            f"- [{title}]({source.get('url', '')}) | {source.get('source_type', 'Unknown')} | "
            f"{source.get('published', 'Date unavailable')} | {source.get('credibility_tier', 'Low')} | {snippet}"
        )

    return "\n".join(lines)


def render_message(content: str, sources: list[dict] | None = None) -> None:
    sections = parse_structured_sections(content)
    if "best_answer" not in sections or "final_verdict" not in sections:
        st.markdown(content)
        if sources:
            render_detail_block("Sources and References", format_source_metadata(sources))
        return

    render_summary_card("Final Consensus Verdict", sections["final_verdict"], "verdict")

    if "correct_option" in sections:
        render_detail_block("Correct Option", sections["correct_option"])

    c1, c2, c3 = st.columns(3)
    with c1:
        render_summary_card("Best Answer", sections.get("best_answer", "Not available."))
    with c2:
        contradictions = sections.get("contradictions", "No contradictions listed.")
        render_summary_card("Contradictions", contradictions)
    with c3:
        confidence = sections.get("confidence", "Not available.")
        render_summary_card("Confidence", confidence)

    if "claim_check" in sections:
        render_detail_block("Claim Check", sections["claim_check"])

    if "strengths" in sections:
        render_detail_block("Strengths", sections["strengths"])

    if "areas_for_improvement" in sections:
        render_detail_block("Areas for Improvement", sections["areas_for_improvement"])

    if "actionable_steps" in sections:
        render_detail_block("Actionable Steps", sections["actionable_steps"])

    if "core_concept" in sections:
        render_detail_block("Core Concept", sections["core_concept"])

    if "logical_structure" in sections:
        render_detail_block("Logical Structure", sections["logical_structure"])

    if "deep_insights" in sections:
        render_detail_block("Deep Insights", sections["deep_insights"])

    if "a_vs_b_breakdown" in sections:
        render_detail_block("A vs B Breakdown", sections["a_vs_b_breakdown"])

    if "pros_and_cons" in sections:
        render_detail_block("Pros and Cons", sections["pros_and_cons"])

    if "final_recommendation" in sections:
        render_detail_block("Final Recommendation", sections["final_recommendation"])

    if "evidence_strength" in sections:
        render_detail_block("Evidence Strength", sections["evidence_strength"])

    if "source_quality" in sections:
        render_detail_block("Source Quality", sections["source_quality"])

    if "counter_gaps" in sections:
        render_detail_block("Counter-Evidence and Gaps", sections["counter_gaps"])

    if "risks" in sections:
        render_detail_block("Risks", sections["risks"])

    if "next_steps" in sections:
        render_detail_block("Next Steps", sections["next_steps"])

    if "sources" in sections:
        render_detail_block("Sources and References", sections["sources"])
    elif sources:
        render_detail_block("Sources and References", format_source_metadata(sources))


for msg in st.session_state.messages:
    if msg.get("hidden"):
        continue

    avatar = "🧑‍💻" if msg["role"] == "user" else "⚖️"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "assistant":
            render_message(msg["content"], msg.get("sources"))
        else:
            st.markdown(msg["content"])


user_input = st.chat_input("Drop in a claim, draft, code block, or product idea for FactForge to work on...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="⚖️"):
        with st.spinner("Forging your review..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/chat",
                    json={
                        "message": user_input,
                        "history": st.session_state.messages[:-1],
                        "model": config["model"],
                        "mode": config["mode"],
                        "session_id": st.session_state.get("chat_session_id"),
                    },
                    timeout=45,
                )
                data = response.json()
                reply = data.get("reply") or f"Error: {data.get('error', 'Unknown error')}"
                sources = data.get("sources", [])
                st.session_state.storage_backend = data.get("storage_backend", st.session_state.get("storage_backend", "local"))
            except requests.exceptions.ConnectionError:
                reply = "Backend offline. Run: `uvicorn backend.main:app --reload --port 8000`"
                sources = []
            except requests.exceptions.Timeout:
                reply = "Timed out. The model or live evidence step took too long. Please try again."
                sources = []
            except Exception as e:
                reply = f"Error: {str(e)}"
                sources = []

        render_message(reply, sources)
        st.session_state.messages.append({"role": "assistant", "content": reply, "sources": sources})
