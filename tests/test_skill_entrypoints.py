"""Tests for SKSeed skill entrypoints with LLM-layer mocking.

Covers:
  - collide() — proposition analysis, context propagation, result structure
  - philosopher() — structured PhilosopherSession output, mode handling
  - truth_check() — belief recording, is_aligned field, domain propagation
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from skseed.alignment import AlignmentStore as _RealAlignmentStore
from skseed.skill import collide, philosopher, truth_check, alignment_report


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _no_real_llm(monkeypatch):
    """Prevent auto_callback from hitting real APIs in every test."""
    monkeypatch.setattr("skseed.skill.auto_callback", lambda: None)


@pytest.fixture()
def tmp_alignment(tmp_path, monkeypatch):
    """Redirect AlignmentStore in skseed.skill to a temp directory.

    AlignmentStore uses a default arg evaluated at class-definition time,
    so patching the module variable is insufficient.  Instead we patch
    the class itself inside skseed.skill to always bind the tmp base_dir.
    """
    alignment_dir = str(tmp_path / ".skseed" / "alignment")

    def _store_factory(*args, **kwargs):
        kwargs.setdefault("base_dir", alignment_dir)
        return _RealAlignmentStore(*args, **kwargs)

    monkeypatch.setattr("skseed.skill.AlignmentStore", _store_factory)
    return alignment_dir


# ── collide() ──────────────────────────────────────────────────────────────────


class TestCollideSkillEntrypoint:
    """Tests for the collide() skill entrypoint."""

    def test_returns_dict(self):
        result = collide("Truth is knowable")
        assert isinstance(result, dict)

    def test_proposition_in_result(self):
        result = collide("Sovereignty matters")
        assert result["proposition"] == "Sovereignty matters"

    def test_context_propagates(self):
        result = collide("Encryption is necessary", context="security")
        assert result["context"] == "security"

    def test_default_context_is_empty(self):
        result = collide("Logic is universal")
        assert result.get("context", "") == ""

    def test_truth_grade_field_present(self):
        result = collide("Free software is ethical")
        assert "truth_grade" in result

    def test_coherence_score_is_float(self):
        result = collide("Privacy is a right")
        assert isinstance(result["coherence_score"], float)

    def test_coherence_score_in_range(self):
        result = collide("Data integrity is important")
        score = result["coherence_score"]
        assert 0.0 <= score <= 1.0

    def test_steel_man_field_present(self):
        result = collide("Open source wins")
        assert "steel_man" in result

    def test_inversion_field_present(self):
        result = collide("Monoliths are better than microservices")
        assert "inversion" in result

    def test_invariants_is_list(self):
        result = collide("Correctness before performance")
        assert isinstance(result["invariants"], list)

    def test_collision_fragments_is_list(self):
        result = collide("All assumptions are valid")
        assert isinstance(result["collision_fragments"], list)

    def test_with_real_llm_mock(self, monkeypatch):
        """When an LLM callback is injected, collide() uses it."""
        llm_calls = []

        def fake_llm(prompt):
            llm_calls.append(prompt)
            return "Steel man: this is clearly true. Inversion: no it isn't."

        monkeypatch.setattr("skseed.skill.auto_callback", lambda: fake_llm)
        result = collide("LLMs change everything")
        # The collider should have used the LLM
        assert len(llm_calls) > 0
        assert isinstance(result, dict)
        assert result["proposition"] == "LLMs change everything"

    def test_empty_proposition_returns_dict(self):
        # Edge case: empty string should not raise
        result = collide("")
        assert isinstance(result, dict)


# ── philosopher() ──────────────────────────────────────────────────────────────


class TestPhilosopherSkillEntrypoint:
    """Tests for the philosopher() skill entrypoint."""

    def test_returns_dict(self):
        result = philosopher("What is consciousness?")
        assert isinstance(result, dict)

    def test_topic_in_result(self):
        result = philosopher("Is free will real?")
        assert result["topic"] == "Is free will real?"

    def test_mode_in_result(self):
        result = philosopher("Ethics of AI", mode="socratic")
        assert result["mode"] == "socratic"

    def test_all_valid_modes(self):
        for mode in ("socratic", "dialectic", "adversarial", "collaborative"):
            result = philosopher("Test topic", mode=mode)
            assert result["mode"] == mode

    def test_invalid_mode_defaults_to_dialectic(self):
        result = philosopher("Topic", mode="nonsense_mode")
        assert result["mode"] == "dialectic"

    def test_exchanges_field_is_list(self):
        result = philosopher("Truth and knowledge")
        assert isinstance(result["exchanges"], list)

    def test_insights_field_is_list(self):
        result = philosopher("Nature of mind")
        assert isinstance(result["insights"], list)

    def test_open_questions_field_is_list(self):
        result = philosopher("Hard problem of consciousness")
        assert isinstance(result["open_questions"], list)

    def test_invariants_field_is_list(self):
        result = philosopher("Logic and mathematics")
        assert isinstance(result["invariants"], list)

    def test_collider_results_field_is_list(self):
        result = philosopher("Language shapes thought")
        assert isinstance(result["collider_results"], list)

    def test_default_mode_is_dialectic(self):
        result = philosopher("Any topic")
        assert result["mode"] == "dialectic"

    def test_with_real_llm_mock(self, monkeypatch):
        """When an LLM is available, philosopher builds exchanges."""
        def fake_llm(prompt):
            return "This is a thoughtful philosophical response."

        monkeypatch.setattr("skseed.skill.auto_callback", lambda: fake_llm)
        result = philosopher("Meaning of existence", mode="dialectic")
        assert result["topic"] == "Meaning of existence"
        assert isinstance(result, dict)


# ── truth_check() ──────────────────────────────────────────────────────────────


class TestTruthCheckSkillEntrypoint:
    """Tests for the truth_check() skill entrypoint."""

    def test_returns_dict(self, tmp_alignment):
        result = truth_check("The sky is blue")
        assert isinstance(result, dict)

    def test_belief_content_matches_input(self, tmp_alignment):
        result = truth_check("Sovereignty is non-negotiable")
        assert result["belief"]["content"] == "Sovereignty is non-negotiable"

    def test_is_aligned_field_present(self, tmp_alignment):
        result = truth_check("Data at rest must be encrypted")
        assert "is_aligned" in result
        assert isinstance(result["is_aligned"], bool)

    def test_collider_result_field_present(self, tmp_alignment):
        result = truth_check("Open source is more secure")
        assert "collider_result" in result
        assert isinstance(result["collider_result"], dict)

    def test_alignment_record_field_present(self, tmp_alignment):
        result = truth_check("Privacy is fundamental")
        assert "alignment_record" in result
        assert isinstance(result["alignment_record"], dict)

    def test_model_source_default(self, tmp_alignment):
        result = truth_check("LLMs can reason")
        assert result["belief"]["source"] == "model"

    def test_human_source(self, tmp_alignment):
        result = truth_check("I believe in open data", source="human")
        assert result["belief"]["source"] == "human"

    def test_invalid_source_defaults_to_model(self, tmp_alignment):
        result = truth_check("Test belief", source="alien")
        assert result["belief"]["source"] == "model"

    def test_domain_propagates(self, tmp_alignment):
        result = truth_check("Encryption is fast enough", domain="security")
        assert result["belief"]["domain"] == "security"

    def test_default_domain_is_general(self, tmp_alignment):
        result = truth_check("Math is certain")
        assert result["belief"]["domain"] == "general"

    def test_belief_recorded_in_alignment_store(self, tmp_alignment):
        """truth_check() must write to the AlignmentStore (not just return data)."""
        from skseed.models import BeliefSource

        truth_check("Persistence matters")
        store = _RealAlignmentStore(base_dir=tmp_alignment)
        model_beliefs = store.list_beliefs(source=BeliefSource.MODEL)
        assert len(model_beliefs) >= 1
        contents = [b.content for b in model_beliefs]
        assert "Persistence matters" in contents

    def test_second_belief_recorded_separately(self, tmp_alignment):
        """Each truth_check() call appends a distinct record."""
        from skseed.models import BeliefSource

        truth_check("First belief", source="model")
        truth_check("Second belief", source="model")

        store = _RealAlignmentStore(base_dir=tmp_alignment)
        beliefs = store.list_beliefs(source=BeliefSource.MODEL)
        contents = [b.content for b in beliefs]
        assert "First belief" in contents
        assert "Second belief" in contents

    def test_human_belief_stored_separately_from_model(self, tmp_alignment):
        from skseed.models import BeliefSource

        truth_check("Human claim", source="human")
        truth_check("Model claim", source="model")

        store = _RealAlignmentStore(base_dir=tmp_alignment)
        human_beliefs = store.list_beliefs(source=BeliefSource.HUMAN)
        model_beliefs = store.list_beliefs(source=BeliefSource.MODEL)
        assert any(b.content == "Human claim" for b in human_beliefs)
        assert any(b.content == "Model claim" for b in model_beliefs)

    def test_alignment_record_has_triggered_by(self, tmp_alignment):
        result = truth_check("Triggered belief")
        record = result["alignment_record"]
        assert record.get("triggered_by") == "truth-check"

    def test_collider_result_has_proposition(self, tmp_alignment):
        result = truth_check("AI is transformative")
        cr = result["collider_result"]
        assert cr["proposition"] == "AI is transformative"


# ── alignment_report() cross-check ────────────────────────────────────────────


class TestAlignmentReportAfterTruthCheck:
    """Verify that beliefs stored via truth_check() appear in alignment_report()."""

    def test_belief_count_increments(self, tmp_alignment):
        from skseed.skill import alignment_report

        before = alignment_report(action="status")
        truth_check("New belief for count test")
        after = alignment_report(action="status")

        assert after["model_beliefs"] == before["model_beliefs"] + 1

    def test_ledger_grows_after_truth_check(self, tmp_alignment):
        from skseed.skill import alignment_report

        truth_check("Ledger test belief")
        report = alignment_report(action="ledger")
        assert report["count"] >= 1
