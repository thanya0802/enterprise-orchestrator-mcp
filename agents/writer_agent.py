"""Writer agent: synthesizes findings into a structured report."""

from __future__ import annotations

import json
import os

from agents.mcp_client import get_genai_client
from governance.audit_logger import AuditLogger
from governance.pii_detector import redact_pii, scan_for_pii

SYSTEM_PROMPT = """You are a technical writer. Synthesize the raw findings into
a clear, well-structured response. Include:
- A direct answer to the question
- Supporting evidence with citations
- Any caveats or gaps in the information
Keep it concise but thorough."""


async def run(
    question: str,
    audit: AuditLogger,
    context: dict | None = None,
) -> str:
    client = get_genai_client()
    findings = context or {}

    prompt = f"""{SYSTEM_PROMPT}

User question: {question}

Findings from specialized agents:
{json.dumps(findings, indent=2)}

Write the final response."""

    response = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        contents=prompt,
    )
    audit.log_llm_call(prompt, response.text or "", os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))

    answer = response.text or "No response generated."
    if scan_for_pii(answer):
        answer = redact_pii(answer)
    return answer
