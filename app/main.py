"""Streamlit UI for Enterprise Knowledge Orchestrator."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from agents.orchestrator import ask, orchestrate
from governance.audit_logger import AuditLogger

st.set_page_config(page_title="Knowledge Orchestrator", layout="wide")
st.title("Enterprise Knowledge Orchestrator")
st.caption("Ask questions across your docs, GitHub, knowledge graph, and more.")

mode = st.radio(
    "Mode",
    ["Single orchestrator", "Multi-agent"],
    horizontal=True,
    help="Multi-agent decomposes complex questions across research, code, and writer agents.",
)

question = st.text_input(
    "Ask a question:",
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
