"""Code agent: analyzes PRs, commits, and code-related questions."""

from __future__ import annotations

from agents.mcp_client import (
    MCPSessionManager,
    get_genai_client,
    plan_tool_calls,
    synthesize_answer,
)
from governance.audit_logger import AuditLogger

CODE_TOOLS = {"get_open_issues", "get_recent_prs", "get_recent_commits"}

SYSTEM_PROMPT = """You are a senior developer reviewing code and PRs.
Analyze code changes, identify blockers, and summarize technical decisions.
Be specific about PR numbers, authors, and branch names."""


async def run(
    task: str,
    audit: AuditLogger,
    context: dict | None = None,
) -> str:
    client = get_genai_client()
    manager = MCPSessionManager(audit=audit)

    try:
        await manager.connect_defaults()
        tools = manager.tools_for_names(CODE_TOOLS)
        if not tools:
            return "GitHub tools unavailable. Set GITHUB_TOKEN and GITHUB_REPO."

        plan = await plan_tool_calls(client, task, manager.tools_description(tools), audit)
        tool_results: dict[str, str] = {}
        for step in plan:
            tool_name = step.get("tool", "")
            if tool_name in CODE_TOOLS:
                tool_results[tool_name] = await manager.call_tool(
                    tool_name, step.get("arguments", {})
                )

        if context:
            tool_results["prior_context"] = str(context)

        return await synthesize_answer(
            client, task, tool_results, audit, system_context=SYSTEM_PROMPT
        )
    finally:
        await manager.close()
