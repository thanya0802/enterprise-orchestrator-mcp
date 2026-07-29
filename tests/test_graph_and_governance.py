"""Basic tests for knowledge graph and governance."""

from graph_rag.graph_builder import KnowledgeGraph
from governance.pii_detector import redact_pii, scan_for_pii


def test_knowledge_graph_neighbors():
    kg = KnowledgeGraph(persist_path="knowledge_graph.json")
    result = kg.query_neighbors("auth refactor", depth=1)
    assert "Alice Chen" in result or "Auth Refactor" in result


def test_multi_hop_query():
    kg = KnowledgeGraph(persist_path="knowledge_graph.json")
    result = kg.multi_hop_query("auth refactor", ["decided_by"])
    assert "Alice Chen" in result


def test_pii_detection():
    text = "Contact alice@example.com or call 555-123-4567"
    findings = scan_for_pii(text)
    assert "email" in findings
    redacted = redact_pii(text)
    assert "alice@example.com" not in redacted


def test_graph_stats():
    kg = KnowledgeGraph(persist_path="knowledge_graph.json")
    stats = kg.get_stats()
    assert "Nodes:" in stats
