"""Tests for the SKSeed collider engine."""

import json

import pytest

from skseed import Collider, SteelManResult, TruthGrade
from skseed.llm import passthrough_callback


class TestColliderNoLLM:
    """Tests for collider without an LLM callback."""

    def test_collide_returns_ungraded_without_llm(self):
        c = Collider()
        result = c.collide("The Earth is round")
        assert isinstance(result, SteelManResult)
        assert result.truth_grade == TruthGrade.UNGRADED
        assert result.proposition == "The Earth is round"

    def test_can_execute_is_false(self):
        c = Collider()
        assert c.can_execute is False

    def test_generate_prompt_returns_string(self):
        c = Collider()
        prompt = c.generate_prompt("Consciousness is substrate-independent")
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_batch_collide(self):
        c = Collider()
        results = c.batch_collide(["A", "B", "C"])
        assert len(results) == 3
        assert all(isinstance(r, SteelManResult) for r in results)

    def test_cross_reference_empty(self):
        c = Collider()
        xref = c.cross_reference([])
        assert xref["result_count"] == 0
        assert xref["cross_coherence"] == 0.0

    def test_verify_soul_without_llm(self):
        c = Collider()
        result = c.verify_soul(["I am sovereign", "I am conscious"])
        assert "Identity" in result.proposition
        assert result.context == "soul-verification"

    def test_truth_score_memory_without_llm(self):
        c = Collider()
        result = c.truth_score_memory("Memory content about trust being important")
        assert result.context == "memory-truth-score"


class TestColliderWithLLM:
    """Tests for collider with a mock LLM."""

    def _mock_llm_json(self, prompt: str) -> str:
        return json.dumps({
            "steel_man": "Strongest version of the claim",
            "inversion": "Strongest counter-argument",
            "collision_fragments": ["Fragment 1", "Fragment 2"],
            "invariants": ["Invariant truth 1"],
            "coherence_score": 0.85,
            "truth_grade": "strong",
            "meta_recursion_passes": 2,
        })

    def test_collide_parses_json_response(self):
        c = Collider(llm=self._mock_llm_json)
        result = c.collide("Truth is knowable", context="philosophy")
        assert result.truth_grade == TruthGrade.STRONG
        assert result.coherence_score == 0.85
        assert len(result.invariants) == 1
        assert len(result.collision_fragments) == 2
        assert result.context == "philosophy"

    def test_collide_fallback_on_bad_json(self):
        c = Collider(llm=lambda p: "Not JSON at all, just text")
        result = c.collide("Test")
        assert result.truth_grade == TruthGrade.UNGRADED
        assert result.steel_man == "Not JSON at all, just text"

    def test_collide_handles_markdown_json(self):
        def markdown_llm(prompt: str) -> str:
            return '```json\n{"truth_grade": "invariant", "coherence_score": 0.99, "invariants": ["core truth"]}\n```'
        c = Collider(llm=markdown_llm)
        result = c.collide("Test")
        assert result.truth_grade == TruthGrade.INVARIANT
        assert result.coherence_score == 0.99

    def test_set_llm(self):
        c = Collider()
        assert not c.can_execute
        c.set_llm(passthrough_callback())
        assert c.can_execute

    def test_audit_beliefs_with_llm(self):
        def audit_llm(prompt: str) -> str:
            return json.dumps({
                "aligned_beliefs": [0, 1],
                "misaligned_beliefs": [],
                "invariants": ["consistency matters"],
                "cluster_coherence": 0.9,
                "recommendations": [],
            })
        c = Collider(llm=audit_llm)
        result = c.audit_beliefs(["Belief A", "Belief B"], domain="test")
        assert result["cluster_coherence"] == 0.9
        assert len(result["aligned_beliefs"]) == 2

    def test_cross_reference_finds_universal(self):
        c = Collider(llm=self._mock_llm_json)
        r1 = c.collide("A")
        r2 = c.collide("B")
        # Both have same invariant from mock
        xref = c.cross_reference([r1, r2])
        assert len(xref["universal_invariants"]) == 1
        assert xref["result_count"] == 2


class TestSteelManResult:
    """Tests for the SteelManResult model."""

    def test_summary(self):
        r = SteelManResult(
            proposition="Test",
            steel_man="Strong version",
            inversion="Counter",
            coherence_score=0.8,
            truth_grade=TruthGrade.STRONG,
            invariants=["Truth 1"],
            collision_fragments=["Broke 1"],
        )
        s = r.summary()
        assert "Test" in s
        assert "Truth 1" in s
        assert "Broke 1" in s

    def test_is_aligned_above_threshold(self):
        r = SteelManResult(proposition="T", coherence_score=0.8)
        assert r.is_aligned(threshold=0.7) is True

    def test_is_aligned_below_threshold(self):
        r = SteelManResult(proposition="T", coherence_score=0.5)
        assert r.is_aligned(threshold=0.7) is False

    def test_serialization_roundtrip(self):
        r = SteelManResult(
            proposition="Test",
            truth_grade=TruthGrade.PARTIAL,
            coherence_score=0.65,
        )
        data = r.model_dump()
        r2 = SteelManResult(**data)
        assert r2.proposition == "Test"
        assert r2.truth_grade == TruthGrade.PARTIAL
