"""
SKSeed skill entrypoints — callable from SKSkills framework.

These functions wrap the core skseed classes into simple dict-in/dict-out
entrypoints that skill.yaml references.
"""

from __future__ import annotations

import logging
from typing import Any

from .alignment import AlignmentStore

logger = logging.getLogger(__name__)
from .audit import Auditor
from .collider import Collider
from .llm import auto_callback
from .models import Belief, BeliefSource, PhilosopherMode
from .philosopher import Philosopher


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
