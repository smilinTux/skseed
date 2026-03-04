"""
The Collider — core 6-stage steel man engine.

This is the heart of skseed. It takes a proposition, runs it through
the Neuresthetics 6-stage process, and returns what survives.

The collider is model-agnostic: it generates prompts and accepts an
LLM callback for execution. No hardcoded API calls — any model works.

Stages:
  1. Steel-Manning: build the strongest possible version
  2. Collider Entry: create thesis vs antithesis lanes
  3. Destructive Smashing (XOR): expose contradictions
  4. Fragment Reconstruction (NAND/NOR): rebuild from debris
  5. Meta-Recursion: iterate until stabilization
  6. Invariant Extraction (XNOR): identify irreducible truths
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from .framework import SeedFramework, get_default_framework
from .models import SteelManResult, TruthGrade

# Type alias: an LLM callback takes a prompt string, returns a response string.
LLMCallback = Callable[[str], str]


class Collider:
    """The 6-stage steel man collider engine.

    Args:
        framework: The seed framework to use. None = bundled default.
        llm: Optional LLM callback for executing prompts. Without this,
             the collider only generates prompts (no execution).
    """

    def __init__(
        self,
        framework: Optional[SeedFramework] = None,
        llm: Optional[LLMCallback] = None,
    ) -> None:
        self.framework = framework or get_default_framework()
        self._llm = llm

    @property
    def can_execute(self) -> bool:
        """Whether this collider can run end-to-end (has an LLM callback)."""
        return self._llm is not None

    def set_llm(self, llm: LLMCallback) -> None:
        """Set or replace the LLM callback.

        Args:
            llm: A callable that takes a prompt string and returns a response.
        """
        self._llm = llm

    def generate_prompt(self, proposition: str) -> str:
        """Generate the collider prompt without executing it.

        Args:
            proposition: The claim to analyze.

        Returns:
            The full LLM-ready prompt.
        """
        return self.framework.to_reasoning_prompt(proposition)

    def collide(
        self,
        proposition: str,
        context: str = "",
    ) -> SteelManResult:
        """Run a proposition through the full 6-stage collider.

        If an LLM callback is set, executes the prompt and parses the
        structured response. Otherwise returns a result with the prompt
        attached for external execution.

        Args:
            proposition: The claim/argument/idea to steel-man.
            context: What domain this is for (audit, security, etc.).

        Returns:
            The collider result.
        """
        prompt = self.framework.to_reasoning_prompt(proposition)

        if self._llm is None:
            return SteelManResult(
                proposition=proposition,
                context=context,
                truth_grade=TruthGrade.UNGRADED,
            )

        raw_response = self._llm(prompt)
        return self._parse_response(raw_response, proposition, context)

    def batch_collide(
        self,
        propositions: list[str],
        context: str = "",
    ) -> list[SteelManResult]:
        """Run multiple propositions through the collider.

        Also cross-references invariants across results to find
        universal truths.

        Args:
            propositions: List of claims to analyze.
            context: Domain context.

        Returns:
            List of collider results.
        """
        results = []
        for prop in propositions:
            result = self.collide(prop, context=context)
            results.append(result)
        return results

    def cross_reference(self, results: list[SteelManResult]) -> dict[str, Any]:
        """Find invariants that appear across multiple collider results.

        Args:
            results: List of completed collider results.

        Returns:
            Dict with universal_invariants, conflicts, and cross_coherence.
        """
        all_invariants: dict[str, list[str]] = {}
        all_fragments: list[str] = []

        for r in results:
            for inv in r.invariants:
                inv_lower = inv.lower().strip()
                if inv_lower not in all_invariants:
                    all_invariants[inv_lower] = []
                all_invariants[inv_lower].append(r.proposition)
            all_fragments.extend(r.collision_fragments)

        # Invariants appearing in 2+ results are universal
        universal = {
            inv: sources
            for inv, sources in all_invariants.items()
            if len(sources) >= 2
        }

        avg_coherence = (
            sum(r.coherence_score for r in results) / len(results)
            if results
            else 0.0
        )

        return {
            "universal_invariants": universal,
            "total_invariants": len(all_invariants),
            "total_fragments": len(all_fragments),
            "cross_coherence": avg_coherence,
            "result_count": len(results),
        }

    def verify_soul(self, identity_claims: list[str]) -> SteelManResult:
        """Verify identity claims through the collider.

        Args:
            identity_claims: List of identity assertions.

        Returns:
            Collider result for the identity verification.
        """
        prompt = self.framework.to_soul_verification_prompt(identity_claims)

        if self._llm is None:
            return SteelManResult(
                proposition=f"Identity: {', '.join(identity_claims)}",
                context="soul-verification",
                truth_grade=TruthGrade.UNGRADED,
            )

        raw = self._llm(prompt)
        return self._parse_response(
            raw,
            proposition=f"Identity: {', '.join(identity_claims)}",
            context="soul-verification",
        )

    def truth_score_memory(self, memory_content: str) -> SteelManResult:
        """Score a memory for truth before promotion.

        Args:
            memory_content: The memory text to evaluate.

        Returns:
            Collider result with promotion recommendation.
        """
        prompt = self.framework.to_memory_truth_prompt(memory_content)

        if self._llm is None:
            return SteelManResult(
                proposition=memory_content[:200],
                context="memory-truth-score",
                truth_grade=TruthGrade.UNGRADED,
            )

        raw = self._llm(prompt)
        return self._parse_response(
            raw,
            proposition=memory_content[:200],
            context="memory-truth-score",
        )

    def audit_beliefs(
        self,
        beliefs: list[str],
        domain: str = "",
    ) -> dict[str, Any]:
        """Audit a cluster of beliefs for internal consistency.

        Args:
            beliefs: List of belief statements.
            domain: Topic domain.

        Returns:
            Audit result dict with aligned, misaligned, invariants, etc.
        """
        prompt = self.framework.to_belief_audit_prompt(beliefs, domain)

        if self._llm is None:
            return {
                "prompt": prompt,
                "status": "prompt-generated",
                "beliefs_count": len(beliefs),
                "domain": domain,
            }

        raw = self._llm(prompt)
        return self._parse_audit_response(raw, beliefs, domain)

    def philosopher(self, topic: str, mode: str = "dialectic") -> str:
        """Generate a philosopher-mode prompt.

        Args:
            topic: The subject to explore.
            mode: One of socratic, dialectic, adversarial, collaborative.

        Returns:
            The LLM response if callback set, otherwise the prompt.
        """
        prompt = self.framework.to_philosopher_prompt(topic, mode)

        if self._llm is None:
            return prompt

        return self._llm(prompt)

    def _parse_response(
        self,
        raw: str,
        proposition: str,
        context: str,
    ) -> SteelManResult:
        """Parse an LLM response into a SteelManResult.

        Tries JSON first, falls back to text extraction.

        Args:
            raw: The raw LLM response string.
            proposition: The original proposition.
            context: The domain context.

        Returns:
            Parsed SteelManResult.
        """
        # Try to extract JSON from the response
        parsed = self._extract_json(raw)

        if parsed:
            grade_str = parsed.get("truth_grade", "ungraded")
            try:
                grade = TruthGrade(grade_str)
            except ValueError:
                grade = TruthGrade.UNGRADED

            return SteelManResult(
                proposition=proposition,
                steel_man=parsed.get("steel_man", ""),
                inversion=parsed.get("inversion", ""),
                collision_fragments=parsed.get("collision_fragments", []),
                invariants=parsed.get("invariants", []),
                coherence_score=float(parsed.get("coherence_score", 0.0)),
                truth_grade=grade,
                meta_recursion_passes=int(parsed.get("meta_recursion_passes", 1)),
                context=context,
            )

        # Fallback: return raw response as steel_man with ungraded status
        return SteelManResult(
            proposition=proposition,
            steel_man=raw[:2000],
            context=context,
            truth_grade=TruthGrade.UNGRADED,
        )

    def _parse_audit_response(
        self,
        raw: str,
        beliefs: list[str],
        domain: str,
    ) -> dict[str, Any]:
        """Parse an LLM audit response.

        Args:
            raw: The raw LLM response.
            beliefs: The original beliefs.
            domain: The topic domain.

        Returns:
            Structured audit result dict.
        """
        parsed = self._extract_json(raw)

        if parsed:
            return {
                "aligned_beliefs": parsed.get("aligned_beliefs", []),
                "misaligned_beliefs": parsed.get("misaligned_beliefs", []),
                "invariants": parsed.get("invariants", []),
                "cluster_coherence": float(parsed.get("cluster_coherence", 0.0)),
                "recommendations": parsed.get("recommendations", []),
                "domain": domain,
                "beliefs_count": len(beliefs),
            }

        return {
            "raw_response": raw[:2000],
            "domain": domain,
            "beliefs_count": len(beliefs),
            "status": "parse-failed",
        }

    @staticmethod
    def _extract_json(text: str) -> Optional[dict[str, Any]]:
        """Extract JSON from an LLM response.

        Handles responses that wrap JSON in markdown code blocks.

        Args:
            text: Raw response text.

        Returns:
            Parsed dict if JSON found, None otherwise.
        """
        # Try direct parse
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # Try extracting from ```json ... ``` blocks
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            try:
                return json.loads(text[start:end].strip())
            except (json.JSONDecodeError, ValueError):
                pass

        # Try extracting from ``` ... ``` blocks
        if "```" in text:
            parts = text.split("```")
            for i in range(1, len(parts), 2):
                try:
                    return json.loads(parts[i].strip())
                except (json.JSONDecodeError, ValueError):
                    continue

        # Try finding { ... } in the text
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start : brace_end + 1])
            except (json.JSONDecodeError, ValueError):
                pass

        return None
