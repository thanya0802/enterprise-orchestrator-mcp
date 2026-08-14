"""
Minimal A2A implementation: agents expose capabilities
and accept delegated tasks via a simple HTTP API.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from fastapi import FastAPI
from pydantic import BaseModel, Field

from governance.audit_logger import AuditLogger


class AgentCard(BaseModel):
    name: str
    description: str
    capabilities: list[str]
    endpoint: str


class Task(BaseModel):
    task_id: str
    question: str
    context: dict = Field(default_factory=dict)
    delegated_by: str = ""


class TaskResult(BaseModel):
    task_id: str
    agent: str
    result: str
    confidence: float = 0.8
    sources: list[str] = Field(default_factory=list)


AGENT_REGISTRY: dict[str, AgentCard] = {}


def register_agent(card: AgentCard) -> None:
    AGENT_REGISTRY[card.name] = card


def create_agent_app(
    card: AgentCard,
    handler: Callable[[Task], Awaitable[TaskResult]],
) -> FastAPI:
    app = FastAPI(title=card.name)
    register_agent(card)

    @app.get("/.well-known/agent.json")
    async def agent_info() -> dict:
        return card.model_dump()

    @app.post("/tasks")
    async def handle_task(task: Task) -> TaskResult:
        return await handler(task)

    @app.get("/registry")
    async def list_agents() -> dict[str, AgentCard]:
        return AGENT_REGISTRY

    return app


def build_research_app() -> FastAPI:
    from agents.research_agent import run as research_run

    card = AgentCard(
        name="research_agent",
        description="Document search and knowledge graph analysis",
        capabilities=["semantic_search", "explore_entity"],
        endpoint="/tasks",
    )

    async def handler(task: Task) -> TaskResult:
        audit = AuditLogger()
        result = await research_run(task.question, audit, context=task.context)
        return TaskResult(task_id=task.task_id, agent=card.name, result=result)

    return create_agent_app(card, handler)


def build_code_app() -> FastAPI:
    from agents.code_agent import run as code_run

    card = AgentCard(
        name="code_agent",
        description="GitHub PR, issue, and commit analysis",
        capabilities=["get_recent_prs", "get_open_issues"],
        endpoint="/tasks",
    )

    async def handler(task: Task) -> TaskResult:
        audit = AuditLogger()
        result = await code_run(task.question, audit, context=task.context)
        return TaskResult(task_id=task.task_id, agent=card.name, result=result)

    return create_agent_app(card, handler)
