"""Build and query a knowledge graph from extracted entities."""

from __future__ import annotations

import json
import os
from pathlib import Path

import networkx as nx


class KnowledgeGraph:
    def __init__(self, persist_path: str | None = None):
        self.persist_path = persist_path or os.environ.get(
            "KNOWLEDGE_GRAPH_PATH", "./knowledge_graph.json"
        )
        self.graph = nx.DiGraph()
        self._load()

    def add_entities(self, extraction: dict) -> None:
        for entity in extraction.get("entities", []):
            self.graph.add_node(
                entity["id"],
                type=entity.get("type", "unknown"),
                name=entity.get("name", entity["id"]),
                **entity.get("properties", {}),
            )
        for rel in extraction.get("relationships", []):
            if rel["source"] in self.graph and rel["target"] in self.graph:
                self.graph.add_edge(
                    rel["source"],
                    rel["target"],
                    type=rel.get("type", "relates_to"),
                    **rel.get("properties", {}),
                )
        self._save()

    def query_neighbors(self, entity_name: str, depth: int = 2) -> str:
        """Find all entities within N hops of a given entity."""
        target = None
        for node, data in self.graph.nodes(data=True):
            if entity_name.lower() in data.get("name", "").lower():
                target = node
                break
        if not target:
            return f"Entity '{entity_name}' not found in knowledge graph."

        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(target, 0)]
        results: list[str] = []
        while queue:
            current, d = queue.pop(0)
            if current in visited or d > depth:
                continue
            visited.add(current)
            node_data = self.graph.nodes[current]
            results.append(
                f"{'  ' * d}{node_data.get('name', current)} ({node_data.get('type', '?')})"
            )

            for neighbor in self.graph.neighbors(current):
                edge_data = self.graph.edges[current, neighbor]
                neighbor_name = self.graph.nodes[neighbor].get("name", neighbor)
                results.append(
                    f"{'  ' * (d + 1)}--[{edge_data.get('type', '?')}]--> {neighbor_name}"
                )
                queue.append((neighbor, d + 1))

        return "\n".join(results)

    def multi_hop_query(self, start_entity: str, relationship_path: list[str]) -> str:
        """Follow a specific path of relationships."""
        current_nodes: list[str] = []
        for node, data in self.graph.nodes(data=True):
            if start_entity.lower() in data.get("name", "").lower():
                current_nodes.append(node)

        if not current_nodes:
            return f"No entity matching '{start_entity}'"

        results = [f"Starting from: {start_entity}"]
        for rel_type in relationship_path:
            next_nodes: list[str] = []
            for node in current_nodes:
                for neighbor in self.graph.neighbors(node):
                    edge = self.graph.edges[node, neighbor]
                    if edge.get("type") == rel_type:
                        next_nodes.append(neighbor)
                        name = self.graph.nodes[neighbor].get("name", neighbor)
                        results.append(f"  --[{rel_type}]--> {name}")
            current_nodes = next_nodes
            if not current_nodes:
                break

        return "\n".join(results) if len(results) > 1 else "No path found."

    def get_stats(self) -> str:
        types = {d.get("type") for _, d in self.graph.nodes(data=True)}
        return (
            f"Nodes: {self.graph.number_of_nodes()}, "
            f"Edges: {self.graph.number_of_edges()}, "
            f"Types: {types}"
        )

    def _save(self) -> None:
        data = nx.node_link_data(self.graph)
        Path(self.persist_path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        path = Path(self.persist_path)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if "links" in data and "edges" not in data:
                data["edges"] = data.pop("links")
            self.graph = nx.node_link_graph(data, directed=True)
