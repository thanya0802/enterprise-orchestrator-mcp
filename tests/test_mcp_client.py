"""Tests for agents/mcp_client.py — focused on failure modes that don't
require a live Gemini API key or a running MCP server: malformed LLM JSON
output, and calling a tool that doesn't exist in the session.
"""

from __future__ import annotations

import pytest

from agents.mcp_client import MCPSessionManager, parse_json_response


class TestParseJsonResponse:
    def test_clean_json_array(self):
        assert parse_json_response('[{"tool": "x", "arguments": {}}]') == [
            {"tool": "x", "arguments": {}}
        ]

    def test_json_wrapped_in_code_fence(self):
        text = '```json\n[{"tool": "x", "arguments": {}}]\n```'
        assert parse_json_response(text) == [{"tool": "x", "arguments": {}}]

    def test_code_fence_without_language_tag(self):
        text = '```\n[{"tool": "x", "arguments": {}}]\n```'
        assert parse_json_response(text) == [{"tool": "x", "arguments": {}}]

    def test_empty_string_returns_default(self):
        assert parse_json_response("") == []

    def test_malformed_json_returns_default_instead_of_raising(self):
        # This is the failure mode that used to crash `ask()` and
        # `decompose_question()` whenever the LLM returned prose instead
        # of pure JSON. It must degrade, not raise.
        text = "Sure, here's the plan: [{\"tool\": \"x\", oops not json"
        assert parse_json_response(text) == []

    def test_json_embedded_in_surrounding_prose_is_salvaged(self):
        text = 'Here is the plan:\n[{"tool": "search", "arguments": {"q": "auth"}}]\nHope that helps!'
        result = parse_json_response(text)
        assert result == [{"tool": "search", "arguments": {"q": "auth"}}]

    def test_custom_default_is_respected(self):
        assert parse_json_response("not json at all {{{", default={}) == {}


class TestIsRateLimitError:
    def test_429_client_error_is_retryable(self):
        from google.genai import errors as genai_errors

        from agents.mcp_client import _is_rate_limit_error

        exc = genai_errors.ClientError(429, {"error": {"code": 429, "message": "quota exceeded"}})
        assert _is_rate_limit_error(exc) is True

    def test_404_client_error_is_not_retryable(self):
        from google.genai import errors as genai_errors

        from agents.mcp_client import _is_rate_limit_error

        exc = genai_errors.ClientError(404, {"error": {"code": 404, "message": "not found"}})
        assert _is_rate_limit_error(exc) is False

    def test_non_api_error_is_not_retryable(self):
        from agents.mcp_client import _is_rate_limit_error

        assert _is_rate_limit_error(ValueError("some other error")) is False
    @pytest.mark.asyncio
    async def test_call_tool_not_found_returns_message_not_exception(self):
        manager = MCPSessionManager()
        result = await manager.call_tool("nonexistent_tool", {})
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_call_tool_failure_is_captured_as_result(self):
        """If a connected tool's underlying call raises (dead subprocess,
        bad arguments, etc.), call_tool should return an error string
        rather than propagate the exception and take down the whole
        orchestrator request.
        """

        class _BoomSession:
            async def call_tool(self, name, arguments):
                raise RuntimeError("simulated transport failure")

        manager = MCPSessionManager()
        manager.tools.append(
            {"name": "flaky_tool", "description": "", "parameters": {}, "_server": "flaky"}
        )
        manager.sessions["flaky"] = _BoomSession()

        result = await manager.call_tool("flaky_tool", {})
        assert "failed" in result.lower()
        assert "simulated transport failure" in result
