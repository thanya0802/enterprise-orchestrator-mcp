"""Extract entities and relationships from documents using an LLM."""

from __future__ import annotations

import json
import os
import re

from google import genai

client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

EXTRACTION_PROMPT = """Extract entities and relationships from this text.

Return JSON with this structure:
{{
  "entities": [
    {{"id": "unique_id", "type": "person|project|decision|pr|meeting", "name": "...", "properties": {{}}}}
  ],
  "relationships": [
    {{"source": "entity_id", "target": "entity_id", "type": "decided_by|blocks|relates_to|assigned_to|mentioned_in|author_of", "properties": {{}}}}
  ]
}}

Text:
{text}

Return ONLY valid JSON."""


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"entities": [], "relationships": []}


def extract_entities(text: str) -> dict:
    """Extract entities and relationships from text."""
    if not os.environ.get("GOOGLE_API_KEY"):
        return {"entities": [], "relationships": []}

    response = client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.6-flash"),
        contents=EXTRACTION_PROMPT.format(text=text[:8000]),
    )
    return _parse_json_response(response.text or "")
