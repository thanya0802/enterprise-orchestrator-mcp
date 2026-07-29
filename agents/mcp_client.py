"""Shared MCP client utilities for agents."""

from __future__ import annotations

import json
import os
import re
import time
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from governance.audit_logger import AuditLogger
from governance.pii_detector import redact_pii, scan_for_pii

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def get_genai_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required.")
    return genai.Client(api_key=api_key)


def parse_json_response(text: str) -> Any:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return json.loads(cleaned)


class MCPSessionManager:
    """Manages MCP server connections with proper async context cleanup."""

    def __init__(self, audit: AuditLogger | None = None):
        self.sessions: dict[str, ClientSession] = {}
        self.tools: list[dict] = []
        self._stack = AsyncExitStack()
        self.audit = audit or AuditLogger()

    async def connect_server(
        self,
        name: str,
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> None:
        merged_env = {**os.environ, **(env or {})}
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "server.py"],
            env=merged_env,
            cwd=str(cwd),
        )
        read, write = await self._stack.enter_async_context(stdio_client(server_params))
        session = await self._stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self.sessions[name] = session

        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            self.tools.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                    "_server": name,
                }
            )

    async def connect_defaults(self) -> None:
        docs_dir = str(PROJECT_ROOT / "mcp-servers/markdown-server/sample-docs")
        await self.connect_server(
            "markdown",
            PROJECT_ROOT / "mcp-servers/markdown-server",
            env={
                "DOCS_DIR": docs_dir,
                "CHROMA_PATH": str(PROJECT_ROOT / "mcp-servers/markdown-server/chroma_db"),
            },
        )
        await self.connect_server(
            "github",
            PROJECT_ROOT / "mcp-servers/github-server",
            env={
                "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
                "GITHUB_REPO": os.environ.get("GITHUB_REPO", "owner/repo"),
            },
        )
        graph_path = PROJECT_ROOT / "knowledge_graph.json"
        if graph_path.exists():
            await self.connect_server(
                "graph",
                PROJECT_ROOT / "mcp-servers/graph-server",
                env={"KNOWLEDGE_GRAPH_PATH": str(graph_path)},
            )

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        server_name = None
        for tool in self.tools:
            if tool["name"] == tool_name:
                server_name = tool["_server"]
                break
        if not server_name:
            return f"Tool '{tool_name}' not found."

        start = time.perf_counter()
        result = await self.sessions[server_name].call_tool(tool_name, arguments)
        latency_ms = (time.perf_counter() - start) * 1000

        text = ""
        if result.content:
            text = result.content[0].text if hasattr(result.content[0], "text") else str(result.content[0])

        self.audit.log_tool_call(tool_name, arguments, text, server_name, latency_ms)
        return text

    def tools_for_names(self, names: set[str]) -> list[dict]:
        return [t for t in self.tools if t["name"] in names]

    def tools_description(self, tools: list[dict] | None = None) -> str:
        source = tools if tools is not None else self.tools
        return "\n".join(f"- {t['name']}: {t['description']}" for t in source)

    async def close(self) -> None:
        await self._stack.aclose()


async def plan_tool_calls(
    client: genai.Client,
    question: str,
    tools_description: str,
    audit: AuditLogger,
) -> list[dict]:
    planning_prompt = f"""You are an enterprise knowledge assistant.
You have access to these tools:

{tools_description}

User question: {question}

Respond with a JSON array of tool calls needed to answer this question.
Format: [{{"tool": "tool_name", "arguments": {{"arg": "value"}}}}]
Only output the JSON array, nothing else."""

    response = client.models.generate_content(model=MODEL, contents=planning_prompt)
    audit.log_llm_call(planning_prompt, response.text or "", MODEL)
    return parse_json_response(response.text or "[]")


async def synthesize_answer(
    client: genai.Client,
    question: str,
    tool_results: dict,
    audit: AuditLogger,
    system_context: str = "",
) -> str:
    synthesis_prompt = f"""Based on these data sources, answer the user's question.
Cite which source each piece of information came from.

{system_context}

User question: {question}

Data retrieved:
{json.dumps(tool_results, indent=2)}

Provide a clear, structured answer with citations."""

    response = client.models.generate_content(model=MODEL, contents=synthesis_prompt)
    audit.log_llm_call(synthesis_prompt, response.text or "", MODEL)
    answer = response.text or "No answer generated."

    pii = scan_for_pii(answer)
    if pii:
        answer = redact_pii(answer)
    return answer
