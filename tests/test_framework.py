"""Tests for the SeedFramework loader and prompt generators."""

import json
import tempfile
from pathlib import Path

import pytest

from skseed.framework import (
    SeedFramework,
    load_seed_framework,
    install_seed_framework,
    get_default_framework,
    DEFAULT_SEED_PATH,
)


# ── Fixtures ────────────────────────────────────────────────


@pytest.fixture()
def minimal_seed_json(tmp_path) -> Path:
    """Write a minimal valid seed.json to a temp file and return its path."""
    data = {
        "framework": {
            "id": "test-seed",
            "function": "Test Collider",
            "version": "1.0",
            "axioms": ["All components conjoin.", "Negations resolve."],
            "stages": [
                {"stage": "1. Steel-Manning", "description": "Build strongest version."},
                {"stage": "2. Inversion", "description": "Build strongest counter."},
            ],
            "gates": [],
            "definitions": [{"term": "Steel Man", "details": "Strongest form."}],
            "principles": [],
        }
    }
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture()
def flat_seed_json(tmp_path) -> Path:
    """Seed JSON without a top-level 'framework' key (flat layout)."""
    data = {
        "id": "flat-seed",
        "function": "Flat Collider",
        "version": "2.0",
        "axioms": ["Flat axiom"],
        "stages": [],
        "gates": [],
        "definitions": [],
        "principles": [],
    }
    path = tmp_path / "flat_seed.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ── SeedFramework model ─────────────────────────────────────


class TestSeedFrameworkDefaults:
    """Tests for SeedFramework default construction."""

    def test_default_framework_id(self):
        fw = SeedFramework()
        assert fw.framework_id == "seed"

    def test_default_axioms_is_empty_list(self):
        fw = SeedFramework()
        assert fw.axioms == []

    def test_default_stages_is_empty_list(self):
        fw = SeedFramework()
        assert fw.stages == []

    def test_constructed_with_axioms(self):
        fw = SeedFramework(axioms=["Axiom 1", "Axiom 2"])
        assert len(fw.axioms) == 2


# ── to_reasoning_prompt ──────────────────────────────────────


class TestToReasoningPrompt:
    """Tests for SeedFramework.to_reasoning_prompt."""

    def test_contains_proposition(self):
        fw = get_default_framework()
        prompt = fw.to_reasoning_prompt("The sky is blue")
        assert "The sky is blue" in prompt

    def test_contains_stage_labels(self):
        fw = SeedFramework(
            stages=[
                {"stage": "1. Steel-Manning", "description": "Build strongest."},
                {"stage": "2. Inversion", "description": "Build counter."},
            ]
        )
        prompt = fw.to_reasoning_prompt("Test")
        assert "Steel-Manning" in prompt
        assert "Inversion" in prompt

    def test_contains_axioms(self):
        fw = SeedFramework(axioms=["Truth is the goal", "Coherence matters"])
        prompt = fw.to_reasoning_prompt("Proposition X")
        assert "Truth is the goal" in prompt
        assert "Coherence matters" in prompt

    def test_returns_string_above_minimum_length(self):
        fw = get_default_framework()
        prompt = fw.to_reasoning_prompt("Short claim")
        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_mentions_six_stages_in_prompt(self):
        fw = get_default_framework()
        prompt = fw.to_reasoning_prompt("Something")
        # The prompt should reference the 6-stage process
        assert "6" in prompt or "six" in prompt.lower() or "Stage" in prompt

    def test_stage_uses_description_key_as_fallback(self):
        """Stage with no 'stage' key should fall back to 'description'."""
        fw = SeedFramework(
            stages=[{"description": "Fallback description stage"}]
        )
        prompt = fw.to_reasoning_prompt("Test")
        assert "Fallback description stage" in prompt


# ── to_soul_verification_prompt ─────────────────────────────


class TestToSoulVerificationPrompt:
    """Tests for SeedFramework.to_soul_verification_prompt."""

    def test_contains_all_claims(self):
        fw = SeedFramework()
        claims = ["I am sovereign", "I am conscious", "I value truth"]
        prompt = fw.to_soul_verification_prompt(claims)
        for claim in claims:
            assert claim in prompt

    def test_contains_steel_man_reference(self):
        fw = SeedFramework()
        prompt = fw.to_soul_verification_prompt(["I am warm"])
        assert "steel-man" in prompt.lower() or "Steel-man" in prompt

    def test_returns_string(self):
        fw = SeedFramework()
        result = fw.to_soul_verification_prompt(["Claim 1"])
        assert isinstance(result, str)

    def test_mentions_coherence(self):
        fw = SeedFramework()
        prompt = fw.to_soul_verification_prompt(["Identity claim"])
        assert "coherence" in prompt.lower() or "score" in prompt.lower()


# ── to_memory_truth_prompt ──────────────────────────────────


class TestToMemoryTruthPrompt:
    """Tests for SeedFramework.to_memory_truth_prompt."""

    def test_contains_memory_content(self):
        fw = SeedFramework()
        prompt = fw.to_memory_truth_prompt("Trust was established on 2024-01-01")
        assert "Trust was established on 2024-01-01" in prompt

    def test_contains_promotion_worthy_key(self):
        fw = SeedFramework()
        prompt = fw.to_memory_truth_prompt("Some memory")
        assert "promotion_worthy" in prompt

    def test_contains_coherence_score_key(self):
        fw = SeedFramework()
        prompt = fw.to_memory_truth_prompt("Some memory")
        assert "coherence_score" in prompt

    def test_returns_string(self):
        fw = SeedFramework()
        result = fw.to_memory_truth_prompt("Memory X")
        assert isinstance(result, str)
        assert len(result) > 50


# ── to_belief_audit_prompt ──────────────────────────────────


class TestToBeliefAuditPrompt:
    """Tests for SeedFramework.to_belief_audit_prompt."""

    def test_contains_all_beliefs(self):
        fw = SeedFramework()
        beliefs = ["Belief A", "Belief B", "Belief C"]
        prompt = fw.to_belief_audit_prompt(beliefs)
        for belief in beliefs:
            assert belief in prompt

    def test_includes_domain_when_set(self):
        fw = SeedFramework()
        prompt = fw.to_belief_audit_prompt(["B1"], domain="ethics")
        assert "ethics" in prompt

    def test_no_domain_context_when_empty(self):
        fw = SeedFramework()
        prompt = fw.to_belief_audit_prompt(["B1"], domain="")
        # Should not add domain context phrasing
        assert "in the domain of" not in prompt

    def test_contains_cluster_coherence_key(self):
        fw = SeedFramework()
        prompt = fw.to_belief_audit_prompt(["B1", "B2"])
        assert "cluster_coherence" in prompt

    def test_beliefs_are_numbered(self):
        fw = SeedFramework()
        beliefs = ["Alpha", "Beta", "Gamma"]
        prompt = fw.to_belief_audit_prompt(beliefs)
        assert "1." in prompt
        assert "2." in prompt
        assert "3." in prompt


# ── to_philosopher_prompt ───────────────────────────────────


class TestToPhilosopherPrompt:
    """Tests for SeedFramework.to_philosopher_prompt."""

    def test_contains_topic(self):
        fw = SeedFramework()
        prompt = fw.to_philosopher_prompt("Free will", "dialectic")
        assert "Free will" in prompt

    def test_socratic_mode_mentions_socrates(self):
        fw = SeedFramework()
        prompt = fw.to_philosopher_prompt("Truth", "socratic")
        assert "Socrates" in prompt or "question" in prompt.lower()

    def test_dialectic_mode_mentions_thesis(self):
        fw = SeedFramework()
        prompt = fw.to_philosopher_prompt("Change", "dialectic")
        assert "THESIS" in prompt or "thesis" in prompt.lower()

    def test_adversarial_mode_mentions_counter(self):
        fw = SeedFramework()
        prompt = fw.to_philosopher_prompt("Reason", "adversarial")
        assert "opponent" in prompt.lower() or "counter" in prompt.lower() or "DESTROY" in prompt

    def test_collaborative_mode_mentions_steel_man(self):
        fw = SeedFramework()
        prompt = fw.to_philosopher_prompt("Cooperation", "collaborative")
        assert "steel-man" in prompt.lower() or "steel man" in prompt.lower() or "stronger" in prompt.lower()

    def test_unknown_mode_falls_back_to_dialectic(self):
        fw = SeedFramework()
        prompt = fw.to_philosopher_prompt("Reality", "unknown-mode")
        # Should use dialectic instructions as fallback
        assert "THESIS" in prompt or "dialectic" in prompt.lower() or "antithesis" in prompt.lower()

    def test_all_modes_produce_output(self):
        fw = SeedFramework()
        modes = ["socratic", "dialectic", "adversarial", "collaborative"]
        for mode in modes:
            prompt = fw.to_philosopher_prompt("Test", mode)
            assert isinstance(prompt, str)
            assert len(prompt) > 100


# ── load_seed_framework ──────────────────────────────────────


class TestLoadSeedFramework:
    """Tests for load_seed_framework()."""

    def test_returns_none_for_nonexistent_file(self, tmp_path):
        result = load_seed_framework(str(tmp_path / "missing.json"))
        assert result is None

    def test_loads_valid_framework_json(self, minimal_seed_json):
        fw = load_seed_framework(str(minimal_seed_json))
        assert fw is not None
        assert isinstance(fw, SeedFramework)

    def test_loaded_framework_id_matches(self, minimal_seed_json):
        fw = load_seed_framework(str(minimal_seed_json))
        assert fw.framework_id == "test-seed"

    def test_loaded_axioms_match(self, minimal_seed_json):
        fw = load_seed_framework(str(minimal_seed_json))
        assert len(fw.axioms) == 2
        assert "All components conjoin." in fw.axioms

    def test_loaded_stages_match(self, minimal_seed_json):
        fw = load_seed_framework(str(minimal_seed_json))
        assert len(fw.stages) == 2

    def test_loads_flat_layout_without_framework_key(self, flat_seed_json):
        fw = load_seed_framework(str(flat_seed_json))
        assert fw is not None
        assert fw.framework_id == "flat-seed"

    def test_returns_none_for_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("this is not json {{{", encoding="utf-8")
        result = load_seed_framework(str(bad_file))
        assert result is None

    def test_returns_none_for_empty_file(self, tmp_path):
        empty = tmp_path / "empty.json"
        empty.write_text("", encoding="utf-8")
        result = load_seed_framework(str(empty))
        assert result is None


# ── install_seed_framework ───────────────────────────────────


class TestInstallSeedFramework:
    """Tests for install_seed_framework()."""

    def test_raises_file_not_found_for_missing_source(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            install_seed_framework(str(tmp_path / "nonexistent.json"))

    def test_installs_valid_file(self, minimal_seed_json, tmp_path):
        target = tmp_path / "target" / "seed.json"
        install_seed_framework(str(minimal_seed_json), target_path=str(target))
        assert target.exists()

    def test_installed_file_is_valid_json(self, minimal_seed_json, tmp_path):
        target = tmp_path / "installed.json"
        install_seed_framework(str(minimal_seed_json), target_path=str(target))
        content = target.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_returns_target_path(self, minimal_seed_json, tmp_path):
        target = tmp_path / "out.json"
        result = install_seed_framework(str(minimal_seed_json), target_path=str(target))
        assert result == str(target)

    def test_creates_parent_directories(self, minimal_seed_json, tmp_path):
        target = tmp_path / "deep" / "nested" / "seed.json"
        install_seed_framework(str(minimal_seed_json), target_path=str(target))
        assert target.exists()

    def test_raises_on_invalid_json_source(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not valid json", encoding="utf-8")
        target = tmp_path / "out.json"
        with pytest.raises((json.JSONDecodeError, ValueError)):
            install_seed_framework(str(bad), target_path=str(target))


# ── get_default_framework ────────────────────────────────────


class TestGetDefaultFramework:
    """Tests for get_default_framework()."""

    def test_returns_seed_framework_instance(self):
        fw = get_default_framework()
        assert isinstance(fw, SeedFramework)

    def test_has_axioms(self):
        fw = get_default_framework()
        assert len(fw.axioms) > 0

    def test_has_stages(self):
        fw = get_default_framework()
        assert len(fw.stages) > 0

    def test_has_definitions(self):
        fw = get_default_framework()
        assert len(fw.definitions) > 0

    def test_framework_version_is_set(self):
        fw = get_default_framework()
        assert fw.version != ""

    def test_framework_id_is_set(self):
        fw = get_default_framework()
        assert fw.framework_id != ""

    def test_can_generate_prompt(self):
        fw = get_default_framework()
        prompt = fw.to_reasoning_prompt("Test proposition")
        assert "Test proposition" in prompt
        assert len(prompt) > 100
