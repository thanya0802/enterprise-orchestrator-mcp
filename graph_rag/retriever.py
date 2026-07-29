"""Semantic retrieval helpers for GraphRAG pipeline."""

from __future__ import annotations

from pathlib import Path

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter


def build_chroma_collection(docs_dir: str, chroma_path: str = "./chroma_db"):
    """Index markdown files into ChromaDB."""
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection("documents")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs_path = Path(docs_dir)

    for md_file in docs_path.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        chunks = splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            collection.upsert(
                ids=[f"{md_file.stem}_{i}"],
                documents=[chunk],
                metadatas=[{"source": str(md_file.relative_to(docs_path))}],
            )
    return collection
