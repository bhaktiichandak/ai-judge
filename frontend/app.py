import streamlit as st
import requests
import os
import re
from dotenv import load_dotenv
from pathlib import Path
from sidebar import render_sidebar

# ── Load environment variables ────────────────────────
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Page Configuration ────────────────────────────────
st.set_page_config(
    page_title="AI Judge",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Professional CSS ──────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after {
    font-family: 'Inter', sans-serif !important;
    box-sizing: border-box;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display: none !important;
}

/* ── App background ── */
.stApp {
    background-color: #0a0a0a;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #111111 !important;
    border-right: 1px solid #1f1f1f !important;
}
[data-testid="stSidebar"] > div {
    padding: 0 !important;
}

/* ── Main content area ── */
.block-container {
    padding: 2rem 3rem 8rem 3rem !important;
    max-width: 860px !important;
    margin: 0 auto !important;
}

/* ── User message bubble ── */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: #111827 !important;
    border: 1px solid #1e293b !important;
    border-radius: 14px !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.75rem !important;
}

/* ── Assistant message bubble ── */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: #0d1117 !important;
    border: 1px solid #161b22 !important;
    border-radius: 14px !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.75rem !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    background: #111111 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 12px !important;
    color: #e0e0e0 !important;
    font-size: 0.95rem !important;
    padding: 0.875rem 1rem !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #444 !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: #161616 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    color: #e0e0e0 !important;
    font-size: 0.875rem !important;
}

/* ── Buttons ── */
button[kind="secondary"] {
    background: #161616 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 10px !important;
    color: #888 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s !important;
}
button[kind="secondary"]:hover {
    border-color: #3b82f6 !important;
    color: #fff !important;
    background: #1e3a5f !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #161616 !important;
    border: 1px solid #1f1f1f !important;
    border-radius: 10px !important;
    padding: 0.6rem 0.4rem !important;
    text-align: center !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.2rem !important;
    color: #e0e0e0 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.7rem !important;
    color: #555 !important;
}

/* ── Divider ── */
hr { border-color: #1f1f1f !important; margin: 1rem 0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #222; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #333; }

/* ── Markdown text in chat ── */
[data-testid="stChatMessage"] p {
    color: #d0d0d0 !important;
    font-size: 0.925rem !important;
    line-height: 1.7 !important;
}
[data-testid="stChatMessage"] h2 {
    color: #ffffff !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    margin: 1rem 0 0.4rem 0 !important;
    padding-bottom: 0.3rem !important;
    border-bottom: 1px solid #1f1f1f !important;
}
[data-testid="stChatMessage"] li {
    color: #b0b0b0 !important;
    font-size: 0.9rem !important;
    line-height: 1.8 !important;
}
[data-testid="stChatMessage"] code {
    background: #1a1a1a !important;
    color: #7dd3fc !important;
    border-radius: 4px !important;
    padding: 0.15rem 0.4rem !important;
    font-size: 0.85rem !important;
}

/* ── Example Cards (Buttons) ── */
[data-testid="column"] button {
    height: 120px !important;
    background: #111111 !important;
    border: 1px solid #1f1f1f !important;
    border-radius: 14px !important;
    transition: all 0.2s !important;
}
[data-testid="column"] button:hover {
    border-color: #3b82f6 !important;
    background: #15202b !important;
    transform: translateY(-2px);
}
[data-testid="column"] button p {
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    color: #e0e0e0 !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session State ─────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Sidebar ───────────────────────────────────────────
config = render_sidebar()


# ── Top Header Bar ────────────────────────────────────
st.markdown("""
    <div style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.25rem 0 1.25rem 0;
        border-bottom: 1px solid #1a1a1a;
        margin-bottom: 1.5rem;
    ">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 1.6rem;">⚖️</span>
            <div>
                <div style="
                    font-size: 1.25rem;
                    font-weight: 700;
                    color: #ffffff;
                    letter-spacing: -0.3px;
                ">AI Judge</div>
                <div style="font-size: 0.75rem; color: #555; margin-top: 1px;">
                    Intelligent evaluation engine
                </div>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="
                font-size: 0.75rem;
                color: #4ade80;
                background: #0d2010;
                border: 1px solid #14532d;
                padding: 0.3rem 0.75rem;
                border-radius: 20px;
                display: flex;
                align-items: center;
                gap: 0.4rem;
            ">
                <span style="
                    width: 6px; height: 6px;
                    background: #4ade80;
                    border-radius: 50%;
                    display: inline-block;
                "></span>
                Live
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)


# ── Active Config Pills ───────────────────────────────
model_label = "🧠 Multi-Model Consensus"
mode_label  = {
    "judge":    "⚖️ Judge",
    "feedback": "📝 Feedback",
    "analyze":  "🔍 Analyze",
    "compare":  "⚡ Compare"
}[config["mode"]]

st.markdown(f"""
    <div style="display: flex; gap: 0.5rem; margin-bottom: 1.75rem; flex-wrap: wrap;">
        <span style="
            background: #0f1f3d;
            color: #93c5fd;
            border: 1px solid #1e3a5f;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 500;
        ">{model_label}</span>
        <span style="
            background: #1a0f2e;
            color: #c4b5fd;
            border: 1px solid #3b1f6e;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 500;
        ">{mode_label}</span>
        <span style="
            background: #0f1f0f;
            color: #86efac;
            border: 1px solid #14532d;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 500;
        ">💬 {len(st.session_state.messages)} messages</span>
    </div>
""", unsafe_allow_html=True)


# ── Welcome Screen ────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
        <div style="
            text-align: center;
            padding: 3.5rem 2rem 2.5rem 2rem;
        ">
            <div style="
                font-size: 2.75rem;
                margin-bottom: 1rem;
                filter: drop-shadow(0 0 20px rgba(59,130,246,0.3));
            ">⚖️</div>
            <h2 style="
                color: #ffffff;
                font-size: 1.6rem;
                font-weight: 700;
                margin: 0 0 0.5rem 0;
                letter-spacing: -0.5px;
            ">What would you like judged?</h2>
            <p style="
                color: #4a4a4a;
                font-size: 0.9rem;
                margin: 0 0 2.5rem 0;
            ">Submit any text, code, argument, or idea for an instant AI verdict</p>
        </div>
    """, unsafe_allow_html=True)

    # Example prompt cards (Clickable Buttons)
    c1, c2, c3, c4 = st.columns(4)
    examples = [
        ("📄", "Essay", "Evaluate the quality of my writing", "an Expert Editor and Professor"),
        ("💻", "Code", "Review my code for quality & bugs", "a Senior Software Engineer"),
        ("🗣️", "Argument", "Judge the logic of my reasoning", "a Master Debater and Logician"),
        ("💡", "Idea", "Rate the strength of my concept", "a Startup Founder and Strategist"),
    ]
    for col, (icon, title, desc, persona) in zip([c1, c2, c3, c4], examples):
        with col:
            if st.button(f"{icon} {title}", key=f"btn_{title}", use_container_width=True, help=desc):
                setup_msg = f"System Instruction: The user has selected the '{title}' category. You must now act as {persona}. Your primary goal is to {desc.lower()}. Adopt this persona for all following evaluations."
                ack_msg = f"**{icon} {title} Mode Activated!**  \n\nI am now acting as {persona}. Please provide your input, and I will {desc.lower()}."
                
                # Inject the setup context (hidden from UI) and the visible acknowledgment
                st.session_state.messages.append({"role": "user", "content": setup_msg, "hidden": True})
                st.session_state.messages.append({"role": "assistant", "content": ack_msg})
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)


# ── Custom UI Renderer ────────────────────────────────
def render_message(content: str):
    """Parses the consensus markdown and renders a beautiful UI card."""
    if "## 🏆 Best Answer" in content and "## ⚖️ Final Consensus Verdict" in content:
        try:
            best_ans = content.split("## 🏆 Best Answer")[1].split("## 🔍 Contradictions")[0].strip()
            contra   = content.split("## 🔍 Contradictions")[1].split("## 💯 Confidence Score")[0].strip()
            conf     = content.split("## 💯 Confidence Score")[1].split("## ⚖️ Final Consensus Verdict")[0].strip()
            
            if "## 📚 Sources & References" in content:
                verdict  = content.split("## ⚖️ Final Consensus Verdict")[1].split("## 📚 Sources & References")[0].strip()
                sources  = content.split("## 📚 Sources & References")[1].strip()
            else:
                verdict  = content.split("## ⚖️ Final Consensus Verdict")[1].strip()
                sources  = None

            # Verdict as a prominent success banner
            st.success(f"**⚖️ Final Consensus Verdict**  \n{verdict}")

            # 3-column dashboard layout
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.info(f"**🏆 Best Answer**  \n{best_ans}")
            
            with c2:
                if any(word in contra.lower() for word in ["agree", "none", "no contradiction"]):
                    st.info(f"**✅ Contradictions**  \n{contra}")
                else:
                    st.warning(f"**⚠️ Contradictions**  \n{contra}")
            
            with c3:
                match = re.search(r'\d+%', conf)
                if match:
                    score = int(match.group(0).replace('%', ''))
                    if score >= 80:
                        st.info(f"**💯 Confidence: {match.group(0)}**  \n{conf}")
                    elif score >= 50:
                        st.warning(f"**💯 Confidence: {match.group(0)}**  \n{conf}")
                    else:
                        st.error(f"**💯 Confidence: {match.group(0)}**  \n{conf}")
                else:
                    st.info(f"**💯 Confidence**  \n{conf}")
                    
            if sources:
                st.markdown(f"""
                    <div style="background: #111111; border: 1px solid #1f1f1f; border-radius: 10px; padding: 1rem; margin-top: 1rem;">
                        <h4 style="margin-top: 0; color: #a3a3a3; font-size: 0.9rem;">📚 Sources & References</h4>
                        <div style="color: #d0d0d0; font-size: 0.85rem;">{sources}</div>
                    </div>
                """, unsafe_allow_html=True)
            return
        except Exception:
            pass # Fallback to standard rendering if parsing fails
            
    st.markdown(content)


# ── Chat History ──────────────────────────────────────
for msg in st.session_state.messages:
    if msg.get("hidden"):
        continue
        
    avatar = "🧑‍💻" if msg["role"] == "user" else "⚖️"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "assistant":
            render_message(msg["content"])
        else:
            st.markdown(msg["content"])


# ── Chat Input ────────────────────────────────────────
user_input = st.chat_input("Ask AI Judge to evaluate something...")

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_input)

    # Get AI response
    with st.chat_message("assistant", avatar="⚖️"):
        with st.spinner("Analyzing..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/chat",
                    json={
                        "message": user_input,
                        "history": st.session_state.messages[:-1],
                        "model":   config["model"],
                        "mode":    config["mode"]
                    },
                    timeout=30
                )
                data  = response.json()
                reply = data.get("reply") or f"❌ {data.get('error', 'Unknown error')}"

            except requests.exceptions.ConnectionError:
                reply = "❌ **Backend offline.** Run: `uvicorn backend.main:app --reload --port 8000`"
            except requests.exceptions.Timeout:
                reply = "⏱️ **Timed out.** The model is taking too long. Please try again."
            except Exception as e:
                reply = f"❌ **Error:** {str(e)}"

        render_message(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})