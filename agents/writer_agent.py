"""Writer agent: synthesizes findings into a structured report."""

from __future__ import annotations

import json
import os

from google.genai import errors as genai_errors

from agents.mcp_client import generate_content_with_retry, get_genai_client
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
    model = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

    prompt = f"""{SYSTEM_PROMPT}

User question: {question}

Findings from specialized agents:
{json.dumps(findings, indent=2)}

Write the final response."""

    try:
        response = generate_content_with_retry(client, model, prompt)
    except genai_errors.ClientError as exc:
        audit.log_llm_call(prompt, f"LLM call failed: {exc}", model)
        # Surface the raw findings rather than nothing — the sub-agents
        # already did real work even if the final synthesis pass couldn't
        # run because of a rate limit.
        raw = "\n\n".join(f"**{agent}**:\n{result}" for agent, result in findings.items())
        return (
            "The final synthesis step hit a Gemini rate limit and couldn't "
            "run. Here are the raw findings from each agent instead:\n\n"
            f"{raw}" if raw else "No answer generated — rate limit exhausted and no findings to show."
        )
    audit.log_llm_call(prompt, response.text or "", model)

    answer = response.text or "No response generated."
    if scan_for_pii(answer):
        answer = redact_pii(answer)
    return answer
