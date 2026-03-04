"""Tests for the SKSeed alignment store."""

import json
import tempfile
from pathlib import Path

import pytest

from skseed import (
    AlignmentRecord,
    AlignmentStatus,
    Belief,
    BeliefSource,
    SteelManResult,
    TruthGrade,
)
from skseed.alignment import AlignmentStore
from skseed.models import SeedConfig


@pytest.fixture
def tmp_store(tmp_path):
    """Create an alignment store in a temp directory."""
    return AlignmentStore(base_dir=str(tmp_path / "alignment"))


class TestBeliefCRUD:
    """Tests for belief storage operations."""

    def test_store_and_retrieve(self, tmp_store):
        b = Belief(content="Truth is knowable", source=BeliefSource.MODEL, domain="philosophy")
        bid = tmp_store.store_belief(b)
        retrieved = tmp_store.get_belief(bid)
        assert retrieved is not None
        assert retrieved.content == "Truth is knowable"
        assert retrieved.source == BeliefSource.MODEL

    def test_store_human_belief(self, tmp_store):
        b = Belief(content="Kindness matters", source=BeliefSource.HUMAN, domain="ethics")
        bid = tmp_store.store_belief(b)
        retrieved = tmp_store.get_belief(bid)
        assert retrieved.source == BeliefSource.HUMAN

    def test_list_by_source(self, tmp_store):
        tmp_store.store_belief(Belief(content="A", source=BeliefSource.MODEL))
        tmp_store.store_belief(Belief(content="B", source=BeliefSource.MODEL))
        tmp_store.store_belief(Belief(content="C", source=BeliefSource.HUMAN))
        model = tmp_store.list_beliefs(source=BeliefSource.MODEL)
        assert len(model) == 2
        human = tmp_store.list_beliefs(source=BeliefSource.HUMAN)
        assert len(human) == 1

    def test_list_by_domain(self, tmp_store):
        tmp_store.store_belief(Belief(content="A", source=BeliefSource.MODEL, domain="ethics"))
        tmp_store.store_belief(Belief(content="B", source=BeliefSource.MODEL, domain="tech"))
        result = tmp_store.list_beliefs(domain="ethics")
        assert len(result) == 1

    def test_delete_belief(self, tmp_store):
        b = Belief(content="Delete me", source=BeliefSource.MODEL)
        bid = tmp_store.store_belief(b)
        assert tmp_store.delete_belief(bid) is True
        assert tmp_store.get_belief(bid) is None

    def test_delete_nonexistent(self, tmp_store):
        assert tmp_store.delete_belief("nonexistent-id") is False

    def test_update_belief(self, tmp_store):
        b = Belief(content="Original", source=BeliefSource.MODEL)
        tmp_store.store_belief(b)
        b.content = "Updated"
        tmp_store.update_belief(b)
        retrieved = tmp_store.get_belief(b.id)
        assert retrieved.content == "Updated"


class TestAlignment:
    """Tests for alignment recording."""

    def test_record_aligned(self, tmp_store):
        b = Belief(content="Test belief", source=BeliefSource.MODEL)
        result = SteelManResult(
            proposition="Test belief",
            coherence_score=0.85,
            truth_grade=TruthGrade.STRONG,
        )
        record = tmp_store.record_alignment(b, result)
        assert record.new_status == AlignmentStatus.ALIGNED
        assert b.alignment_status == AlignmentStatus.ALIGNED

    def test_record_misaligned_creates_issue(self, tmp_store):
        b = Belief(content="Weak claim", source=BeliefSource.MODEL)
        result = SteelManResult(
            proposition="Weak claim",
            coherence_score=0.3,
            truth_grade=TruthGrade.WEAK,
        )
        record = tmp_store.record_alignment(b, result)
        assert record.new_status == AlignmentStatus.MISALIGNED
        issues = tmp_store.list_issues()
        assert len(issues) == 1
        assert issues[0]["belief_content"] == "Weak claim"

    def test_resolve_issue(self, tmp_store):
        b = Belief(content="Discuss me", source=BeliefSource.MODEL)
        result = SteelManResult(proposition="Discuss me", coherence_score=0.2)
        tmp_store.record_alignment(b, result)
        resolved = tmp_store.resolve_issue(b.id, "We discussed and agreed")
        assert resolved is True
        issues = tmp_store.list_issues(status="open")
        assert len(issues) == 0

    def test_coherence_delta_tracking(self, tmp_store):
        b = Belief(content="Evolving", source=BeliefSource.MODEL, coherence_score=0.5)
        r1 = SteelManResult(proposition="Evolving", coherence_score=0.8)
        record = tmp_store.record_alignment(b, r1)
        assert record.coherence_delta == pytest.approx(0.3)


class TestLedger:
    """Tests for alignment ledger."""

    def test_ledger_records(self, tmp_store):
        b = Belief(content="Test", source=BeliefSource.MODEL)
        r = SteelManResult(proposition="Test", coherence_score=0.9)
        tmp_store.record_alignment(b, r, triggered_by="test")
        ledger = tmp_store.get_ledger()
        assert len(ledger) == 1
        assert ledger[0].triggered_by == "test"

    def test_coherence_trend(self, tmp_store):
        b = Belief(content="Track me", source=BeliefSource.MODEL)
        for score in [0.5, 0.6, 0.7]:
            b.coherence_score = score - 0.1
            r = SteelManResult(proposition="Track me", coherence_score=score)
            tmp_store.record_alignment(b, r)
        trend = tmp_store.coherence_trend(b.id)
        assert len(trend) == 3


class TestThreeWayComparison:
    """Tests for cross-store belief comparison."""

    def test_compare_beliefs(self, tmp_store):
        tmp_store.store_belief(Belief(content="H1", source=BeliefSource.HUMAN, domain="ethics"))
        tmp_store.store_belief(Belief(content="M1", source=BeliefSource.MODEL, domain="ethics"))
        tmp_store.store_belief(Belief(content="C1", source=BeliefSource.COLLIDER, domain="ethics"))
        comp = tmp_store.compare_beliefs(domain="ethics")
        assert comp["human_count"] == 1
        assert comp["model_count"] == 1
        assert comp["collider_count"] == 1


class TestConfig:
    """Tests for seed configuration."""

    def test_default_config(self, tmp_store):
        config = tmp_store.load_config()
        assert config.alignment_threshold == 0.7
        assert config.audit_on_boot is True

    def test_save_and_load_config(self, tmp_store):
        config = SeedConfig(alignment_threshold=0.8, audit_on_boot=False)
        tmp_store.save_config(config)
        loaded = tmp_store.load_config()
        assert loaded.alignment_threshold == 0.8
        assert loaded.audit_on_boot is False
