"""Multimodal MCP server for PDF and image analysis."""

from __future__ import annotations

import base64
import os
from pathlib import Path

from google import genai
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("multimodal-knowledge")

ASSETS_DIR = os.environ.get("ASSETS_DIR", "./sample-assets")


def _client() -> genai.Client:
    return genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))


def _resolve_path(file_path: str) -> Path:
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(ASSETS_DIR) / path
    resolved = path.resolve()
    assets_root = Path(ASSETS_DIR).resolve()
    if not str(resolved).startswith(str(assets_root)) and not path.is_absolute():
        raise ValueError("Access denied: path outside assets directory.")
    return resolved


@mcp.tool()
async def analyze_pdf(file_path: str, question: str) -> str:
    """Extract text from a PDF and answer a question about it."""
    if not os.environ.get("GOOGLE_API_KEY"):
        return "GOOGLE_API_KEY required for PDF analysis."

    path = _resolve_path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"

    pdf_data = base64.b64encode(path.read_bytes()).decode()
    response = _client().models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        contents=[
            {"mime_type": "application/pdf", "data": pdf_data},
            f"Based on this document, answer: {question}",
        ],
    )
    return response.text or ""


@mcp.tool()
async def analyze_image(file_path: str, question: str) -> str:
    """Analyze an image (diagram, screenshot, chart) and answer a question."""
    if not os.environ.get("GOOGLE_API_KEY"):
        return "GOOGLE_API_KEY required for image analysis."

    path = _resolve_path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"

    suffix = path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "image/png")

    image_data = base64.b64encode(path.read_bytes()).decode()
    response = _client().models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        contents=[
            {"mime_type": mime, "data": image_data},
            f"Analyze this image and answer: {question}",
        ],
    )
    return response.text or ""


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
