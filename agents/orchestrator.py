"""
Orchestrator: connects to MCP servers and routes user questions
to the right tools via an LLM.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.mcp_client import (
    MCPSessionManager,
    get_genai_client,
    plan_tool_calls,
    synthesize_answer,
)
from governance.audit_logger import AuditLogger


async def ask(question: str, audit: AuditLogger | None = None) -> str:
    """Connect to servers, plan tool calls, execute, and synthesize an answer."""
    audit = audit or AuditLogger()
    client = get_genai_client()
    manager = MCPSessionManager(audit=audit)

    try:
        await manager.connect_defaults()
        if not manager.tools:
            return "No MCP tools available. Check server configuration."

        plan = await plan_tool_calls(
            client, question, manager.tools_description(), audit
        )

        tool_results: dict[str, str] = {}
        for step in plan:
            tool_name = step.get("tool", "")
            arguments = step.get("arguments", {})
            if tool_name:
                tool_results[tool_name] = await manager.call_tool(tool_name, arguments)

        return await synthesize_answer(client, question, tool_results, audit)
    finally:
        await manager.close()


async def decompose_question(question: str, audit: AuditLogger) -> list[dict]:
    """Break a complex question into sub-tasks for specialized agents."""
    client = get_genai_client()
    prompt = f"""Decompose this question into sub-tasks for specialized agents.

Available agents:
- research_agent: document search, semantic analysis, knowledge graph traversal
- code_agent: GitHub PRs, issues, commits, code analysis
- writer_agent: synthesizes findings into reports (use only as final step)

Question: {question}

Return JSON array:
[{{"agent": "agent_name", "task": "specific sub-question", "depends_on": []}}]

Use depends_on with agent names that must complete first.
writer_agent should depend on all other agents."""

    response = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        contents=prompt,
    )
    audit.log_llm_call(prompt, response.text or "", os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))

    from agents.mcp_client import parse_json_response

    return parse_json_response(response.text or "[]")


async def orchestrate(question: str) -> tuple[str, AuditLogger]:
    """Multi-agent orchestration with task decomposition."""
    from agents.code_agent import run as run_code_agent
    from agents.research_agent import run as run_research_agent
    from agents.writer_agent import run as run_writer_agent

    audit = AuditLogger()
    sub_tasks = await decompose_question(question, audit)

    agent_runners = {
        "research_agent": run_research_agent,
        "code_agent": run_code_agent,
        "writer_agent": run_writer_agent,
    }

    results: dict[str, str] = {}

    for task in sub_tasks:
        if task.get("depends_on"):
            continue
        agent = task.get("agent", "")
        if agent in agent_runners:
            audit.log_agent_delegation("orchestrator", agent, task.get("task", ""), "independent task")
            results[agent] = await agent_runners[agent](task.get("task", question), audit)

    for task in sub_tasks:
        if not task.get("depends_on"):
            continue
        agent = task.get("agent", "")
        if agent in agent_runners:
            context = {dep: results[dep] for dep in task["depends_on"] if dep in results}
            audit.log_agent_delegation("orchestrator", agent, task.get("task", ""), f"depends on {list(context)}")
            if agent == "writer_agent":
                results[agent] = await agent_runners[agent](question, audit, context=results)
            else:
                results[agent] = await agent_runners[agent](task.get("task", question), audit, context=context)

    if "writer_agent" not in results:
        results["writer_agent"] = await run_writer_agent(question, audit, context=results)

    return results.get("writer_agent", "No response generated."), audit


if __name__ == "__main__":
    q = os.environ.get(
        "DEMO_QUESTION",
        "What decisions were made about the auth refactor, and are there any related open PRs?",
    )
    use_multi_agent = os.environ.get("USE_MULTI_AGENT", "false").lower() == "true"

    if use_multi_agent:
        answer, logger = asyncio.run(orchestrate(q))
        print(answer)
        print("\n--- Compliance Report ---")
        print(logger.generate_compliance_report())
    else:
        print(asyncio.run(ask(q)))
