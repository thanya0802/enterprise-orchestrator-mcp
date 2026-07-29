"""Logs tool calls, LLM interactions, and agent decisions."""

from __future__ import annotations

import datetime
import json
from pathlib import Path


class AuditLogger:
    def __init__(self, log_dir: str = "./audit_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.entries: list[dict] = []

    def log_tool_call(
        self,
        tool_name: str,
        arguments: dict,
        result: str,
        server: str,
        latency_ms: float,
    ) -> None:
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": "tool_call",
            "session_id": self.session_id,
            "tool": tool_name,
            "server": server,
            "arguments": arguments,
            "result_preview": result[:200],
            "result_length": len(result),
            "latency_ms": latency_ms,
        }
        self.entries.append(entry)
        self._write(entry)

    def log_llm_call(
        self,
        prompt_preview: str,
        response_preview: str,
        model: str,
        tokens_used: int = 0,
    ) -> None:
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": "llm_call",
            "session_id": self.session_id,
            "model": model,
            "prompt_preview": prompt_preview[:300],
            "response_preview": response_preview[:300],
            "tokens_used": tokens_used,
        }
        self.entries.append(entry)
        self._write(entry)

    def log_agent_delegation(
        self, from_agent: str, to_agent: str, task: str, reason: str
    ) -> None:
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": "agent_delegation",
            "session_id": self.session_id,
            "from": from_agent,
            "to": to_agent,
            "task": task,
            "reason": reason,
        }
        self.entries.append(entry)
        self._write(entry)

    def generate_compliance_report(self) -> str:
        tool_calls = [e for e in self.entries if e["type"] == "tool_call"]
        llm_calls = [e for e in self.entries if e["type"] == "llm_call"]
        delegations = [e for e in self.entries if e["type"] == "agent_delegation"]

        report = f"""# Compliance Report — Session {self.session_id}

## Summary
- Tool calls: {len(tool_calls)}
- LLM calls: {len(llm_calls)}
- Agent delegations: {len(delegations)}
- Total entries: {len(self.entries)}

## Data Sources Accessed
{chr(10).join(set(e['server'] for e in tool_calls)) or 'None'}

## Models Used
{chr(10).join(set(e['model'] for e in llm_calls)) or 'None'}

## Full Audit Trail
"""
        for entry in self.entries:
            report += f"\n[{entry['timestamp']}] {entry['type']}: "
            if entry["type"] == "tool_call":
                report += f"{entry['tool']} on {entry['server']} ({entry['latency_ms']:.0f}ms)"
            elif entry["type"] == "llm_call":
                report += f"{entry['model']}"
            elif entry["type"] == "agent_delegation":
                report += f"{entry['from']} → {entry['to']}: {entry['task'][:80]}"
        return report

    def _write(self, entry: dict) -> None:
        log_file = self.log_dir / f"audit_{self.session_id}.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
