"""Tests for SKSeed skill entrypoints."""

from unittest.mock import patch

import pytest

from skseed.skill import collide, audit, philosopher, truth_check, alignment_report


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    """Ensure auto_callback returns None so tests don't hit real LLMs."""
    monkeypatch.setattr("skseed.skill.auto_callback", lambda: None)


class TestCollideEntrypoint:
    """Tests for the collide skill entrypoint."""

    def test_returns_dict(self):
        result = collide("Truth is knowable")
        assert isinstance(result, dict)
        assert "proposition" in result
        assert "truth_grade" in result
        assert result["truth_grade"] == "ungraded"

    def test_with_context(self):
        result = collide("Security requires trust", context="security")
        assert result["context"] == "security"


class TestAuditEntrypoint:
    """Tests for the audit skill entrypoint."""

    def test_returns_dict(self):
        result = audit()
        assert isinstance(result, dict)
        assert "total_beliefs_scanned" in result

    def test_with_triggered_by(self):
        result = audit(triggered_by="test")
        assert result["audit_config"]["triggered_by"] == "test"


class TestPhilosopherEntrypoint:
    """Tests for the philosopher skill entrypoint."""

    def test_returns_dict(self):
        result = philosopher("What is consciousness?")
        assert isinstance(result, dict)
        assert "topic" in result
        assert result["topic"] == "What is consciousness?"

    def test_mode_selection(self):
        result = philosopher("Ethics of AI", mode="socratic")
        assert result["mode"] == "socratic"

    def test_invalid_mode_falls_back(self):
        result = philosopher("Test", mode="invalid")
        assert result["mode"] == "dialectic"


class TestTruthCheckEntrypoint:
    """Tests for the truth_check skill entrypoint."""

    def test_returns_structure(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "skseed.alignment.DEFAULT_ALIGNMENT_DIR",
            str(tmp_path / ".skseed" / "alignment"),
        )
        result = truth_check("Sovereignty is non-negotiable")
        assert isinstance(result, dict)
        assert "belief" in result
        assert "collider_result" in result
        assert "alignment_record" in result
        assert "is_aligned" in result

    def test_source_model(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "skseed.alignment.DEFAULT_ALIGNMENT_DIR",
            str(tmp_path / ".skseed" / "alignment"),
        )
        result = truth_check("Test", source="model")
        assert result["belief"]["source"] == "model"

    def test_source_human(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "skseed.alignment.DEFAULT_ALIGNMENT_DIR",
            str(tmp_path / ".skseed" / "alignment"),
        )
        result = truth_check("Test", source="human")
        assert result["belief"]["source"] == "human"


class TestAlignmentReportEntrypoint:
    """Tests for the alignment_report skill entrypoint."""

    def test_status_action(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "skseed.alignment.DEFAULT_ALIGNMENT_DIR",
            str(tmp_path / ".skseed" / "alignment"),
        )
        result = alignment_report(action="status")
        assert result["action"] == "status"
        assert "human_beliefs" in result
        assert "model_beliefs" in result

    def test_issues_action(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "skseed.alignment.DEFAULT_ALIGNMENT_DIR",
            str(tmp_path / ".skseed" / "alignment"),
        )
        result = alignment_report(action="issues")
        assert result["action"] == "issues"
        assert "open_issues" in result

    def test_ledger_action(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "skseed.alignment.DEFAULT_ALIGNMENT_DIR",
            str(tmp_path / ".skseed" / "alignment"),
        )
        result = alignment_report(action="ledger")
        assert result["action"] == "ledger"
        assert "entries" in result
