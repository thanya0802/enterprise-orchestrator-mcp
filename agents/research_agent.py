"""Research agent: deep document and knowledge graph analysis."""

from __future__ import annotations

from agents.mcp_client import (
    MCPSessionManager,
    get_genai_client,
    plan_tool_calls,
    synthesize_answer,
)
from governance.audit_logger import AuditLogger

RESEARCH_TOOLS = {
    "semantic_search",
    "search_documents",
    "read_document",
    "list_documents",
    "explore_entity",
    "follow_relationship_path",
    "graph_stats",
}

SYSTEM_PROMPT = """You are a research analyst. Given enterprise data tools,
produce a thorough analysis. Always cite sources using [source_name] notation.
If information is missing, say so explicitly."""


async def run(
    task: str,
    audit: AuditLogger,
    context: dict | None = None,
) -> str:
    client = get_genai_client()
    manager = MCPSessionManager(audit=audit)

    try:
        await manager.connect_defaults()
        tools = manager.tools_for_names(RESEARCH_TOOLS)
        if not tools:
            return "Research tools unavailable."

        plan = await plan_tool_calls(client, task, manager.tools_description(tools), audit)
        tool_results: dict[str, str] = {}
        for step in plan:
            tool_name = step.get("tool", "")
            if tool_name in RESEARCH_TOOLS:
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
