"""Ingest documents into vector DB and knowledge graph."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from graph_rag.entity_extractor import extract_entities
from graph_rag.graph_builder import KnowledgeGraph


def ingest_all(docs_dir: str = "./mcp-servers/markdown-server/sample-docs") -> None:
    kg = KnowledgeGraph()
    docs_path = Path(docs_dir)

    for md_file in docs_path.rglob("*.md"):
        print(f"Processing {md_file.name}...")
        content = md_file.read_text(encoding="utf-8")
        extraction = extract_entities(content)
        kg.add_entities(extraction)
        print(
            f"  → {len(extraction.get('entities', []))} entities, "
            f"{len(extraction.get('relationships', []))} relationships"
        )

    print(f"\nGraph stats: {kg.get_stats()}")


if __name__ == "__main__":
    ingest_all()
