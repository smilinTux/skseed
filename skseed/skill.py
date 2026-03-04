"""
SKSeed skill entrypoints — callable from SKSkills framework.

These functions wrap the core skseed classes into simple dict-in/dict-out
entrypoints that skill.yaml references.
"""

from __future__ import annotations

import logging
from typing import Any

from .alignment import AlignmentStore
from .audit import Auditor
from .collider import Collider
from .llm import auto_callback
from .models import Belief, BeliefSource, PhilosopherMode
from .philosopher import Philosopher

logger = logging.getLogger(__name__)


def _get_collider() -> Collider:
    """Get a collider with the best available LLM callback."""
    llm = auto_callback()
    return Collider(llm=llm)


def collide(proposition: str, context: str = "") -> dict[str, Any]:
    """Run a proposition through the 6-stage steel man collider.

    Args:
        proposition: The claim/argument/idea to analyze.
        context: Domain context (e.g., security, ethics, identity).

    Returns:
        Collider result as a dict.
    """
    collider = _get_collider()
    result = collider.collide(proposition, context=context)
    return result.model_dump()


def audit(domain: str = "", triggered_by: str = "skill") -> dict[str, Any]:
    """Scan memories for logic/truth misalignment.

    Extracts beliefs from memory, clusters by domain, runs through
    the collider, and flags contradictions.

    Args:
        domain: Filter by topic domain (optional).
        triggered_by: What triggered this audit.

    Returns:
        Audit report as a dict.
    """
    collider = _get_collider()
    store = AlignmentStore()
    auditor = Auditor(collider=collider, alignment_store=store)

    # Gather memories from skmemory if available
    memories = _load_memories(domain)

    report = auditor.run_audit(
        memories=memories,
        triggered_by=triggered_by,
    )
    return report.model_dump()


def philosopher(topic: str, mode: str = "dialectic") -> dict[str, Any]:
    """Enter philosopher mode for brainstorming.

    Args:
        topic: The subject to explore.
        mode: Brainstorming mode (socratic, dialectic, adversarial, collaborative).

    Returns:
        Philosopher session as a dict.
    """
    collider = _get_collider()
    phil = Philosopher(collider=collider)

    try:
        phil_mode = PhilosopherMode(mode)
    except ValueError:
        phil_mode = PhilosopherMode.DIALECTIC

    session = phil.start_session(topic, mode=phil_mode)
    return session.model_dump()


def truth_check(
    belief: str,
    source: str = "model",
    domain: str = "general",
) -> dict[str, Any]:
    """Check if a belief is truth-aligned.

    Runs through the collider and records the result in the alignment store.

    Args:
        belief: The belief statement to check.
        source: Who holds this belief (human or model).
        domain: Topic domain.

    Returns:
        Dict with belief, collider result, and alignment record.
    """
    collider = _get_collider()
    store = AlignmentStore()

    try:
        belief_source = BeliefSource(source)
    except ValueError:
        belief_source = BeliefSource.MODEL

    # Create belief object
    belief_obj = Belief(
        content=belief,
        source=belief_source,
        domain=domain,
    )

    # Run through collider
    result = collider.collide(belief, context=domain)

    # Record alignment
    record = store.record_alignment(
        belief=belief_obj,
        result=result,
        triggered_by="truth-check",
    )

    return {
        "belief": belief_obj.model_dump(),
        "collider_result": result.model_dump(),
        "alignment_record": record.model_dump(),
        "is_aligned": result.is_aligned(),
    }


def alignment_report(
    domain: str = "",
    action: str = "status",
) -> dict[str, Any]:
    """Show truth alignment status across all three belief stores.

    Args:
        domain: Filter by domain (optional).
        action: Action — status, issues, or ledger.

    Returns:
        Alignment status dict.
    """
    store = AlignmentStore()

    if action == "issues":
        issues = store.list_issues()
        return {
            "action": "issues",
            "open_issues": issues,
            "count": len(issues),
        }

    if action == "ledger":
        ledger = store.get_ledger(limit=50)
        return {
            "action": "ledger",
            "entries": [r.model_dump() for r in ledger],
            "count": len(ledger),
        }

    # Default: status
    comparison = store.compare_beliefs(domain=domain or None)
    issues = store.list_issues()

    human_beliefs = store.list_beliefs(source=BeliefSource.HUMAN, domain=domain or None)
    model_beliefs = store.list_beliefs(source=BeliefSource.MODEL, domain=domain or None)
    collider_beliefs = store.list_beliefs(source=BeliefSource.COLLIDER, domain=domain or None)

    return {
        "action": "status",
        "human_beliefs": len(human_beliefs),
        "model_beliefs": len(model_beliefs),
        "collider_truths": len(collider_beliefs),
        "open_issues": len(issues),
        "comparison": comparison,
        "domain_filter": domain or "all",
    }


# ── New entrypoints (collider extras) ────────────────────────────────────────


def batch_collide(propositions: list[str], context: str = "") -> dict[str, Any]:
    """Run multiple propositions through the collider in sequence.

    Args:
        propositions: List of claims/arguments to analyze.
        context: Shared domain context for all propositions.

    Returns:
        Dict with results list and aggregate summary.
    """
    collider = _get_collider()
    results = collider.batch_collide(propositions, context=context)
    return {
        "results": [r.model_dump() for r in results],
        "count": len(results),
        "avg_coherence": (
            sum(r.coherence_score for r in results) / len(results) if results else 0.0
        ),
    }


def cross_reference(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Find invariant truths shared across multiple prior collider results.

    Args:
        results: List of SteelManResult dicts from previous collide calls.

    Returns:
        Dict summarizing cross-cutting invariants.
    """
    from .models import SteelManResult

    collider = _get_collider()
    result_objs = [SteelManResult(**r) for r in results]
    return collider.cross_reference(result_objs)


def verify_soul(identity_claims: list[str]) -> dict[str, Any]:
    """Verify identity claims through the steel man collider.

    Args:
        identity_claims: List of identity statements to verify.

    Returns:
        SteelManResult dict representing identity coherence.
    """
    collider = _get_collider()
    result = collider.verify_soul(identity_claims)
    return result.model_dump()


def truth_score_memory(memory_content: str) -> dict[str, Any]:
    """Score a memory's content for truth alignment before promotion.

    Args:
        memory_content: The full text content of a memory entry.

    Returns:
        SteelManResult dict with coherence score and truth grade.
    """
    collider = _get_collider()
    result = collider.truth_score_memory(memory_content)
    return result.model_dump()


def audit_beliefs(beliefs: list[str], domain: str = "") -> dict[str, Any]:
    """Audit a cluster of related beliefs for internal consistency.

    Args:
        beliefs: List of belief statements in the same domain.
        domain: Domain label for context.

    Returns:
        Audit result dict with cross-conflicts and coherence analysis.
    """
    collider = _get_collider()
    return collider.audit_beliefs(beliefs, domain=domain)


# ── Philosopher extras ────────────────────────────────────────────────────────


def continue_session(session: dict[str, Any], user_input: str) -> dict[str, Any]:
    """Continue an existing philosopher session with new input.

    Args:
        session: PhilosopherSession dict from a previous philosopher call.
        user_input: The next message or question to continue the dialogue.

    Returns:
        Updated PhilosopherSession dict with the new exchange appended.
    """
    from .models import PhilosopherSession

    collider = _get_collider()
    phil = Philosopher(collider=collider)
    session_obj = PhilosopherSession(**session)
    updated = phil.continue_session(session_obj, user_input)
    return updated.model_dump()


def collide_insight(session: dict[str, Any], insight: str) -> dict[str, Any]:
    """Run a specific insight from a philosopher session through the full collider.

    Args:
        session: PhilosopherSession dict (used for context).
        insight: The specific insight or claim to collide.

    Returns:
        SteelManResult dict.
    """
    from .models import PhilosopherSession

    collider = _get_collider()
    phil = Philosopher(collider=collider)
    session_obj = PhilosopherSession(**session)
    result = phil.collide_insight(session_obj, insight)
    return result.model_dump()


def session_summary(session: dict[str, Any]) -> dict[str, Any]:
    """Generate a human-readable summary of a philosopher session.

    Args:
        session: PhilosopherSession dict to summarize.

    Returns:
        Dict with summary text and key metadata.
    """
    from .models import PhilosopherSession

    collider = _get_collider()
    phil = Philosopher(collider=collider)
    session_obj = PhilosopherSession(**session)
    summary_text = phil.session_summary(session_obj)
    return {
        "summary": summary_text,
        "topic": session_obj.topic,
        "mode": session_obj.mode.value,
        "exchange_count": len(session_obj.exchanges),
        "insight_count": len(session_obj.insights),
        "invariant_count": len(session_obj.invariants),
    }


# ── Alignment extras ──────────────────────────────────────────────────────────


def coherence_trend(domain: str = "", lookback_days: int = 7) -> dict[str, Any]:
    """Analyze truth alignment coherence trends over time.

    Args:
        domain: Filter by domain (optional).
        lookback_days: How many days back to analyze (default 7, max 30).

    Returns:
        Dict with coherence trend, direction, and recommended anchor value.
    """
    store = AlignmentStore()
    days = max(1, min(30, lookback_days))
    return store.coherence_trend(domain=domain or None, lookback_days=days)


# ── Memory loader ─────────────────────────────────────────────────────────────


def _load_memories(domain: str = "") -> list[dict[str, Any]]:
    """Load memories from skmemory for audit.

    Falls back to empty list if skmemory is not available.

    Args:
        domain: Optional domain filter.

    Returns:
        List of memory dicts.
    """
    try:
        from skmemory import MemoryStore

        ms = MemoryStore()
        memories = ms.search(domain) if domain else ms.list_all()
        return [
            {
                "id": getattr(m, "id", ""),
                "content": getattr(m, "content", ""),
                "title": getattr(m, "title", ""),
                "tags": getattr(m, "tags", []),
            }
            for m in memories
        ]
    except ImportError:
        logger.warning("skmemory not installed — audit will run without memories. Install with: pip install skmemory")
        return []
    except Exception as exc:
        logger.warning("Failed to load memories from skmemory: %s", exc)
        return []
