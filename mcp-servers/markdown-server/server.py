"""Markdown/file MCP server with keyword and vector search."""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("markdown-knowledge")

DOCS_DIR = os.environ.get("DOCS_DIR", "./sample-docs")
CHROMA_PATH = os.environ.get("CHROMA_PATH", "./chroma_db")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection("documents")


def _docs_path() -> Path:
    return Path(DOCS_DIR).resolve()


def index_documents() -> None:
    """Chunk and index all markdown files."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs_path = _docs_path()
    if not docs_path.exists():
        return

    for md_file in docs_path.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        chunks = splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            doc_id = f"{md_file.stem}_{i}"
            collection.upsert(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[{"source": str(md_file.relative_to(docs_path))}],
            )


@mcp.tool()
async def search_documents(query: str) -> str:
    """Search through markdown documents for relevant content.
    Returns matching sections with filenames."""
    results: list[str] = []
    docs_path = _docs_path()

    if not docs_path.exists():
        return f"Documents directory not found: {docs_path}"

    for md_file in docs_path.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if query.lower() in content.lower():
            paragraphs = content.split("\n\n")
            for para in paragraphs:
                if query.lower() in para.lower():
                    results.append(f"[{md_file.name}]: {para[:500]}")

    if not results:
        return f"No documents found matching '{query}'"
    return "\n\n---\n\n".join(results[:5])


@mcp.tool()
async def semantic_search(query: str, n_results: int = 5) -> str:
    """Search documents using semantic similarity (vector search)."""
    if collection.count() == 0:
        index_documents()

    if collection.count() == 0:
        return "No documents indexed for semantic search."

    results = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))
    output: list[str] = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        output.append(f"[{meta['source']}]: {doc}")
    return "\n\n---\n\n".join(output) if output else f"No semantic matches for '{query}'"


@mcp.tool()
async def list_documents() -> str:
    """List all available documents in the knowledge base."""
    docs_path = _docs_path()
    if not docs_path.exists():
        return "No documents directory found."
    files = [str(f.relative_to(docs_path)) for f in docs_path.rglob("*.md")]
    return "\n".join(files) if files else "No documents found."


@mcp.tool()
async def read_document(filename: str) -> str:
    """Read the full content of a specific document."""
    docs_path = _docs_path()
    file_path = (docs_path / filename).resolve()
    if not file_path.exists():
        return f"File '{filename}' not found."
    if not str(file_path).startswith(str(docs_path)):
        return "Access denied: path traversal detected."
    return file_path.read_text(encoding="utf-8")[:5000]


def main() -> None:
    index_documents()
    mcp.run()


if __name__ == "__main__":
    main()
