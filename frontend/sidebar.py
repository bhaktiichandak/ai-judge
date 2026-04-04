import streamlit as st

def render_sidebar() -> dict:
    with st.sidebar:

        # ── Brand ─────────────────────────────────────
        st.markdown("""
            <div style="padding: 1.75rem 1.5rem 1.25rem 1.5rem;">
                <div style="display:flex; align-items:center; gap:0.6rem;">
                    <span style="font-size:1.4rem;">⚖️</span>
                    <span style="
                        font-size: 1.1rem;
                        font-weight: 700;
                        color: #ffffff;
                        letter-spacing: -0.3px;
                    ">AI Judge</span>
                </div>
                <div style="
                    font-size: 0.72rem;
                    color: #3a3a3a;
                    margin-top: 0.3rem;
                    margin-left: 2rem;
                ">Groq · Gemini · Llama 3.1</div>
            </div>
            <div style="height:1px; background:#1a1a1a; margin: 0 1rem;"></div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='padding: 1rem 0.25rem 0 0.25rem;'>", unsafe_allow_html=True)

        # ── Model ─────────────────────────────────────
        st.markdown("""
            <div style="
                font-size: 0.7rem;
                font-weight: 600;
                color: #3a3a3a;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 0.4rem;
                padding-left: 0.25rem;
            ">System Engine</div>
            <div style="
                background: #161616;
                border: 1px solid #2a2a2a;
                border-radius: 10px;
                color: #a3a3a3;
                font-size: 0.85rem;
                padding: 0.75rem;
            ">
                🧠 <b>Consensus Mode</b><br>
                <span style="font-size: 0.75rem; color: #666;">Parallel evaluation via Groq + Gemini</span>
            </div>
        """, unsafe_allow_html=True)

        model = "consensus"

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # ── Mode ──────────────────────────────────────
        st.markdown("""
            <div style="
                font-size: 0.7rem;
                font-weight: 600;
                color: #3a3a3a;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 0.4rem;
                padding-left: 0.25rem;
            ">Mode</div>
        """, unsafe_allow_html=True)

        mode = st.selectbox(
            label="mode",
            options=["judge", "feedback", "analyze", "compare"],
            format_func=lambda x: {
                "judge":    "⚖️  Judge — Deliver a verdict",
                "feedback": "📝  Feedback — Improve it",
                "analyze":  "🔍  Analyze — Break it down",
                "compare":  "⚡  Compare — A vs B",
            }[x],
            label_visibility="collapsed"
        )

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1px; background:#1a1a1a;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

        # ── Stats ─────────────────────────────────────
        st.markdown("""
            <div style="
                font-size: 0.7rem;
                font-weight: 600;
                color: #3a3a3a;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 0.6rem;
                padding-left: 0.25rem;
            ">Session</div>
        """, unsafe_allow_html=True)

        msgs  = st.session_state.get("messages", [])
        total = len(msgs)
        user  = len([m for m in msgs if m["role"] == "user"])

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Messages", total, help="Total messages in this chat, including AI responses.")
        with c2:
            st.metric("Your Prompts", user, help="Number of times you have sent a prompt to the AI.")

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        # ── Clear ─────────────────────────────────────
        if st.button("Clear conversation", use_container_width=True, type="secondary"):
            st.session_state.messages = []
            st.rerun()

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1px; background:#1a1a1a;'></div>", unsafe_allow_html=True)

        # ── Capabilities ──────────────────────────────
        st.markdown("""
            <div style="padding: 1.25rem 0.25rem;">
                <div style="
                    font-size: 0.7rem;
                    font-weight: 600;
                    color: #3a3a3a;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 0.75rem;
                ">Capabilities</div>
                <div style="display:flex; flex-direction:column; gap:0.5rem;">
                    <div style="font-size:0.8rem; color:#444;">📄 &nbsp;Essays & writing</div>
                    <div style="font-size:0.8rem; color:#444;">💻 &nbsp;Code review</div>
                    <div style="font-size:0.8rem; color:#444;">🗣️ &nbsp;Arguments & logic</div>
                    <div style="font-size:0.8rem; color:#444;">💡 &nbsp;Ideas & plans</div>
                    <div style="font-size:0.8rem; color:#444;">📊 &nbsp;Data & analysis</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ── Footer ────────────────────────────────────
        st.markdown("""
            <div style="
                position: absolute;
                bottom: 1.5rem;
                left: 0; right: 0;
                text-align: center;
                font-size: 0.7rem;
                color: #222;
            ">
                Built with FastAPI & Streamlit
            </div>
        """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    return {"model": model, "mode": mode}