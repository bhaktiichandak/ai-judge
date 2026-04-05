from uuid import uuid4

import streamlit as st


def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 1.6rem 1.35rem 1.15rem 1.35rem;">
                <div style="
                    border-radius: 18px;
                    background: linear-gradient(180deg, rgba(55,148,255,0.08), rgba(255,255,255,0.02));
                    border: 1px solid rgba(55,148,255,0.16);
                    padding: 0.95rem 0.95rem 0.9rem 0.95rem;
                ">
                    <div style="display:flex; align-items:center; gap:0.8rem;">
                        <div style="
                            width: 42px;
                            height: 42px;
                            border-radius: 12px;
                            background: linear-gradient(180deg, #3794ff, #0e639c);
                            border: 1px solid rgba(255,255,255,0.08);
                            color: #f5fbff;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                            font-weight:800;
                            font-size:0.88rem;
                            font-family:'Space Grotesk', sans-serif;
                        ">FF</div>
                        <div>
                            <div style="
                                font-size: 1.1rem;
                                font-weight: 700;
                                color: #d4d4d4;
                                letter-spacing: -0.3px;
                                font-family:'Space Grotesk', sans-serif;
                            ">FactForge</div>
                            <div style="
                                font-size: 0.68rem;
                                color: #75beff;
                                text-transform: uppercase;
                                letter-spacing: 0.14em;
                                margin-top: 0.2rem;
                            ">Evidence Workspace</div>
                        </div>
                    </div>
                    <div style="
                        font-size: 0.76rem;
                        color: rgba(212,212,212,0.72);
                        margin-top: 0.7rem;
                        line-height: 1.55;
                    ">A minimal workspace for reviewing claims, code, writing, and decisions.</div>
                </div>
            </div>
            <div style="height:1px; background:rgba(255,255,255,0.08); margin: 0 1rem;"></div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='padding: 1rem 0.25rem 0 0.25rem;'>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="
                font-size: 0.7rem;
                font-weight: 600;
                color: rgba(117,190,255,0.72);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 0.4rem;
                padding-left: 0.25rem;
            ">System Engine</div>
            <div style="
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(55,148,255,0.12);
                border-radius: 14px;
                color: #d4d4d4;
                font-size: 0.85rem;
                padding: 0.85rem;
            ">
                <b>Forge Engine</b><br>
                <span style="font-size: 0.75rem; color: rgba(212,212,212,0.62);">Deterministic scoring with source support when the task needs verification</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        model = "deterministic-consensus"

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="
                font-size: 0.7rem;
                font-weight: 600;
                color: rgba(117,190,255,0.72);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 0.4rem;
                padding-left: 0.25rem;
            ">Mode</div>
            """,
            unsafe_allow_html=True,
        )

        mode = st.selectbox(
            label="mode",
            options=["judge", "credibility", "feedback", "analyze", "compare"],
            format_func=lambda x: {
                "judge": "Judge - General evaluation",
                "credibility": "Credibility - Verify with sources",
                "feedback": "Feedback - Improve the draft",
                "analyze": "Analyze - Surface structure",
                "compare": "Compare - Evaluate tradeoffs",
            }[x],
            label_visibility="collapsed",
        )

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1px; background:rgba(255,255,255,0.08);'></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="
                font-size: 0.7rem;
                font-weight: 600;
                color: rgba(117,190,255,0.72);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 0.6rem;
                padding-left: 0.25rem;
            ">Session</div>
            """,
            unsafe_allow_html=True,
        )

        msgs = st.session_state.get("messages", [])
        total = len(msgs)
        user = len([m for m in msgs if m["role"] == "user"])
        storage_backend = st.session_state.get("storage_backend", "local")
        session_id = st.session_state.get("chat_session_id", "")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Messages", total, help="Total messages in this chat, including AI responses.")
        with c2:
            st.metric("Your Prompts", user, help="Number of prompts you have sent to the AI.")

        storage_label = "MongoDB" if storage_backend == "mongo" else "Local session"
        st.caption(f"Storage: {storage_label}")
        if session_id:
            st.caption(f"Session ID: `{session_id[:8]}...`")

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

        if st.button("Clear conversation", use_container_width=True, type="secondary"):
            st.session_state.messages = []
            st.session_state.chat_session_id = uuid4().hex
            st.session_state.session_loaded = False
            st.query_params["chat"] = st.session_state.chat_session_id
            st.rerun()

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1px; background:rgba(255,255,255,0.08);'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="padding: 1.25rem 0.25rem;">
                <div style="
                    font-size: 0.7rem;
                    font-weight: 600;
                    color: rgba(117,190,255,0.72);
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 0.75rem;
                ">Focus</div>
                <div style="display:flex; flex-direction:column; gap:0.5rem;">
                    <div style="font-size:0.81rem; color:rgba(212,212,212,0.68);">Code review</div>
                    <div style="font-size:0.81rem; color:rgba(212,212,212,0.68);">Writing review</div>
                    <div style="font-size:0.81rem; color:rgba(212,212,212,0.68);">Claim verification</div>
                    <div style="font-size:0.81rem; color:rgba(212,212,212,0.68);">Idea analysis</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="
                position: absolute;
                bottom: 1.5rem;
                left: 0; right: 0;
                text-align: center;
                font-size: 0.7rem;
                color: rgba(117,190,255,0.32);
            ">
                FactForge studio
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

    return {"model": model, "mode": mode}
