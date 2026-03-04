"""Tests for the SKSeed audit engine."""

import json

import pytest

from skseed import Auditor, Collider, AuditReport, Belief, BeliefSource
from skseed.models import AlignmentStatus, ConceptCluster, SeedConfig
from skseed.alignment import AlignmentStore


@pytest.fixture
def mock_collider():
    """Collider with a mock LLM that returns structured audit results."""
    def _llm(prompt: str) -> str:
        if "audit" in prompt.lower() or "belief" in prompt.lower():
            return json.dumps({
                "aligned_beliefs": [0],
                "misaligned_beliefs": [{"index": 1, "description": "Contradiction found"}],
                "invariants": ["consistency"],
                "cluster_coherence": 0.75,
                "recommendations": ["Review belief 1"],
            })
        return json.dumps({
            "steel_man": "Strong",
            "inversion": "Counter",
            "coherence_score": 0.8,
            "truth_grade": "strong",
            "invariants": [],
            "collision_fragments": [],
        })
    return Collider(llm=_llm)


@pytest.fixture
def auditor(mock_collider, tmp_path):
    store = AlignmentStore(base_dir=str(tmp_path / "alignment"))
    return Auditor(collider=mock_collider, alignment_store=store)


class TestBeliefExtraction:
    """Tests for extracting beliefs from memories."""

    def test_extracts_belief_content(self, auditor):
        memories = [
            {"id": "m1", "content": "I believe that truth is fundamental", "title": "", "tags": []},
            {"id": "m2", "content": "The weather is nice today", "title": "", "tags": []},
        ]
        beliefs = auditor.extract_beliefs(memories)
        assert len(beliefs) == 1
        assert "truth" in beliefs[0].content.lower()

    def test_extracts_by_tags(self, auditor):
        memories = [
            {"id": "m1", "content": "Some text", "title": "", "tags": ["belief", "ethics"]},
        ]
        beliefs = auditor.extract_beliefs(memories)
        assert len(beliefs) == 1

    def test_empty_memories(self, auditor):
        beliefs = auditor.extract_beliefs([])
        assert len(beliefs) == 0

    def test_source_assignment(self, auditor):
        memories = [
            {"id": "m1", "content": "I believe in sovereignty", "title": "", "tags": []},
        ]
        model_beliefs = auditor.extract_beliefs(memories, source=BeliefSource.MODEL)
        assert model_beliefs[0].source == BeliefSource.MODEL
        human_beliefs = auditor.extract_beliefs(memories, source=BeliefSource.HUMAN)
        assert human_beliefs[0].source == BeliefSource.HUMAN


class TestClustering:
    """Tests for belief clustering."""

    def test_clusters_by_domain(self, auditor):
        beliefs = [
            Belief(content="A", source=BeliefSource.MODEL, domain="ethics"),
            Belief(content="B", source=BeliefSource.MODEL, domain="ethics"),
            Belief(content="C", source=BeliefSource.MODEL, domain="tech"),
        ]
        clusters = auditor.cluster_beliefs(beliefs)
        assert len(clusters) == 2
        domains = {c.domain for c in clusters}
        assert domains == {"ethics", "tech"}

    def test_single_domain(self, auditor):
        beliefs = [
            Belief(content="A", source=BeliefSource.MODEL, domain="identity"),
            Belief(content="B", source=BeliefSource.MODEL, domain="identity"),
        ]
        clusters = auditor.cluster_beliefs(beliefs)
        assert len(clusters) == 1
        assert len(clusters[0].beliefs) == 2


class TestDomainClassification:
    """Tests for the domain classifier."""

    def test_ethics_domain(self, auditor):
        domain = auditor._classify_domain("This is morally wrong", [])
        assert domain == "ethics"

    def test_identity_domain(self, auditor):
        domain = auditor._classify_domain("My identity and consciousness define who I am", [])
        assert domain in ("identity", "consciousness")

    def test_tag_priority(self, auditor):
        domain = auditor._classify_domain("Some generic text", ["security"])
        assert domain == "security"

    def test_general_fallback(self, auditor):
        domain = auditor._classify_domain("xyzzy foobar baz", [])
        assert domain == "general"


class TestFullAudit:
    """Tests for end-to-end audit flow."""

    def test_audit_produces_report(self, auditor):
        memories = [
            {"id": "m1", "content": "I believe truth must be verified", "title": "", "tags": []},
            {"id": "m2", "content": "I think ethics should guide decisions", "title": "", "tags": ["ethics"]},
        ]
        report = auditor.run_audit(memories, triggered_by="test")
        assert isinstance(report, AuditReport)
        assert report.total_beliefs_scanned >= 1
        assert report.audit_config["triggered_by"] == "test"

    def test_audit_empty_memories(self, auditor):
        report = auditor.run_audit([], triggered_by="test")
        assert report.total_beliefs_scanned == 0
        assert len(report.clusters) == 0

    def test_moral_classification(self, auditor):
        assert auditor._is_moral_issue("This should be fair", "ethics") is True
        assert auditor._is_moral_issue("The code runs fast", "technical") is False
