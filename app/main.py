"""Streamlit UI for Enterprise Knowledge Orchestrator."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

import streamlit as st

from agents.orchestrator import ask, orchestrate
from governance.audit_logger import AuditLogger

st.set_page_config(page_title="Knowledge Orchestrator", layout="wide")
st.title("Enterprise Knowledge Orchestrator")
st.caption("Ask questions across your docs, GitHub, knowledge graph, and more.")

if "question_input" not in st.session_state:
    st.session_state["question_input"] = ""

SAMPLE_QUESTIONS: dict[str, list[str]] = {
    "Direct lookup (single orchestrator)": [
        "Why was PostgreSQL chosen over other databases?",
        "Who is responsible for the OAuth provider decision?",
        "What went wrong in the March sprint?",
        "Summarize the JWT security review findings.",
    ],
    "Cross-referencing (multi-agent)": [
        "Who made the decision about the auth refactor, and what PRs are they currently working on?",
        "What's the status of PR #51, and who's blocking it?",
        "Summarize the architecture decisions and flag any that conflict with open PRs or issues.",
        "What's blocking the API v2 rollout, and who owns the blocker?",
    ],
    "Knowledge graph traversal": [
        "Show me everyone connected to the auth refactor decision.",
    ],
    "Live GitHub data": [
        "What are the open issues right now?",
        "Summarize recent commits to the repo.",
        "Which PRs are blocked, and by what?",
    ],
    "Accuracy stress test": [
        "Is ADR-002 approved yet, and what's the fallback plan?",
    ],
}

with st.expander("💡 Sample questions to try", expanded=True):
    st.caption(
        "This demo runs against seeded sample docs (an auth-refactor project) "
        "plus whichever GitHub repo is configured. Click any question to load it below."
    )
    for category, questions in SAMPLE_QUESTIONS.items():
        st.markdown(f"**{category}**")
        cols = st.columns(2)
        for i, q in enumerate(questions):
            if cols[i % 2].button(q, key=f"sample_{q}", use_container_width=True):
                st.session_state["question_input"] = q

mode = st.radio(
    "Mode",
    ["Single orchestrator", "Multi-agent"],
    horizontal=True,
    help="Multi-agent decomposes complex questions across research, code, and writer agents.",
)

question = st.text_input(
    "Ask a question:",
    key="question_input",
    placeholder="What decisions were made about the auth refactor, and are any blocked by open PRs?",
)

if not os.environ.get("GOOGLE_API_KEY"):
    st.warning("Set `GOOGLE_API_KEY` to enable LLM-powered answers.")

if question:
    with st.spinner("Searching across data sources..."):
        if mode == "Multi-agent":
            answer, audit = asyncio.run(orchestrate(question))
        else:
            audit = AuditLogger()
            answer = asyncio.run(ask(question, audit=audit))

    st.markdown("### Answer")
    st.markdown(answer)

    with st.expander("Compliance & audit trail"):
        st.markdown(audit.generate_compliance_report())
