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


def test_pii_detection_no_false_positive_on_clean_text():
    text = "The auth refactor was completed on schedule with no blockers."
    assert scan_for_pii(text) == {}
    assert redact_pii(text) == text


def test_pii_detection_multiple_types_in_one_string():
    text = "SSN 123-45-6789, card 4111 1111 1111 1111, email bob@corp.com"
    findings = scan_for_pii(text)
    assert "ssn" in findings
    assert "credit_card" in findings
    assert "email" in findings
    redacted = redact_pii(text)
    assert "123-45-6789" not in redacted
    assert "bob@corp.com" not in redacted


def test_graph_stats():
    kg = KnowledgeGraph(persist_path="knowledge_graph.json")
    stats = kg.get_stats()
    assert "Nodes:" in stats
