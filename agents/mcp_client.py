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
from google.genai import errors as genai_errors
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from governance.audit_logger import AuditLogger
from governance.pii_detector import redact_pii, scan_for_pii

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def get_genai_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required.")
    return genai.Client(api_key=api_key)


def _is_rate_limit_error(exc: BaseException) -> bool:
    """True for 429 RESOURCE_EXHAUSTED — the one error worth retrying with
    backoff. Other 4xx errors (bad request, auth) won't succeed on retry,
    so we let those raise immediately instead of wasting time.
    """
    return isinstance(exc, genai_errors.ClientError) and getattr(exc, "code", None) == 429


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def generate_content_with_retry(client: genai.Client, model: str, contents: str):
    """Wraps client.models.generate_content with backoff on free-tier rate
    limits (429 RESOURCE_EXHAUSTED). Free-tier Gemini quotas are low enough
    (as few as 5 requests/minute) that a single multi-agent question can
    exceed them on its own — this smooths over that rather than crashing
    the whole Streamlit page on a transient limit.
    """
    return client.models.generate_content(model=model, contents=contents)


def parse_json_response(text: str, default: Any = None) -> Any:
    """Parse JSON out of an LLM response, tolerating code fences and minor
    formatting noise. LLMs occasionally return malformed or non-JSON output
    (extra prose, truncated arrays, etc.) — rather than let that raise and
    crash the whole request, fall back to `default` (an empty list by
    convention for planning steps) so the caller can degrade gracefully.
    """
    if default is None:
        default = []
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    if not cleaned:
        return default
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to salvage a JSON array/object embedded in extra prose.
        match = re.search(r"[\[{].*[\]}]", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return default


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
        """Connect to all default servers. A server that fails to start
        (missing token, bad env, etc.) is skipped rather than taking down
        the whole session — the orchestrator just has fewer tools available.
        """
        docs_dir = str(PROJECT_ROOT / "mcp-servers/markdown-server/sample-docs")
        await self._try_connect(
            "markdown",
            PROJECT_ROOT / "mcp-servers/markdown-server",
            env={
                "DOCS_DIR": docs_dir,
                "CHROMA_PATH": str(PROJECT_ROOT / "mcp-servers/markdown-server/chroma_db"),
            },
        )
        await self._try_connect(
            "github",
            PROJECT_ROOT / "mcp-servers/github-server",
            env={
                "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
                "GITHUB_REPO": os.environ.get("GITHUB_REPO", "owner/repo"),
            },
        )
        graph_path = PROJECT_ROOT / "knowledge_graph.json"
        if graph_path.exists():
            await self._try_connect(
                "graph",
                PROJECT_ROOT / "mcp-servers/graph-server",
                env={"KNOWLEDGE_GRAPH_PATH": str(graph_path)},
            )

    async def _try_connect(self, name: str, cwd: Path, env: dict[str, str] | None = None) -> None:
        try:
            await self.connect_server(name, cwd, env=env)
        except Exception as exc:  # noqa: BLE001 - one bad server shouldn't kill the whole session
            self.audit.log_tool_call(
                tool_name="__connect__",
                arguments={"server": name},
                result=f"Failed to connect to '{name}' server: {exc}",
                server=name,
                latency_ms=0.0,
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
        try:
            result = await self.sessions[server_name].call_tool(tool_name, arguments)
        except Exception as exc:  # noqa: BLE001 - surface any transport/tool failure as a result, not a crash
            latency_ms = (time.perf_counter() - start) * 1000
            error_text = f"Tool '{tool_name}' on server '{server_name}' failed: {exc}"
            self.audit.log_tool_call(tool_name, arguments, error_text, server_name, latency_ms)
            return error_text
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

    try:
        response = generate_content_with_retry(client, MODEL, planning_prompt)
    except genai_errors.ClientError as exc:
        # Rate limit persisted past retries, or a non-retryable error (bad
        # request, auth). Log it and return an empty plan rather than
        # crashing the whole request — synthesize_answer can still explain
        # to the user that no tools ran.
        audit.log_llm_call(planning_prompt, f"LLM call failed: {exc}", MODEL)
        return []
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

    try:
        response = generate_content_with_retry(client, MODEL, synthesis_prompt)
    except genai_errors.ClientError as exc:
        audit.log_llm_call(synthesis_prompt, f"LLM call failed: {exc}", MODEL)
        return (
            "I couldn't generate an answer right now — the Gemini API rate limit "
            "was exceeded and retries were exhausted. This is a free-tier quota "
            "limit (see the raw error in the audit trail below), not an application "
            "error. Please wait a minute and try again."
        )
    audit.log_llm_call(synthesis_prompt, response.text or "", MODEL)
    answer = response.text or "No answer generated."

    pii = scan_for_pii(answer)
    if pii:
        answer = redact_pii(answer)
    return answer
