"""MCP server exposing knowledge graph tools."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP

from graph_rag.graph_builder import KnowledgeGraph

mcp = FastMCP("graph-knowledge")

kg = KnowledgeGraph(
    persist_path=os.environ.get("KNOWLEDGE_GRAPH_PATH", str(PROJECT_ROOT / "knowledge_graph.json"))
)


@mcp.tool()
async def explore_entity(entity_name: str, depth: int = 2) -> str:
    """Explore an entity and its connections in the knowledge graph."""
    return kg.query_neighbors(entity_name, depth)


@mcp.tool()
async def follow_relationship_path(start_entity: str, relationships: str) -> str:
    """Follow a chain of relationships from an entity.
    Example: start='auth refactor', relationships='decided_by,assigned_to'"""
    rels = [r.strip() for r in relationships.split(",") if r.strip()]
    return kg.multi_hop_query(start_entity, rels)


@mcp.tool()
async def graph_stats() -> str:
    """Get statistics about the knowledge graph."""
    return kg.get_stats()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
