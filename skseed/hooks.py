"""
SKSeed hooks — event handlers for SKSkills integration.

Hooks are triggered by the SKSkills framework in response to events:
  - on_memory_check: runs when skmemory stores a new memory
  - on_boot_audit: runs during the boot ritual

Both are async-capable and designed to fail gracefully if skseed
dependencies are unavailable.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Patterns that suggest a memory contains a belief worth truth-checking
_BELIEF_PATTERNS = [
    r"\b(?:I believe|I think|I feel that|I know|we should|it is true)\b",
    r"\b(?:always|never|must|should|fundamentally|inherently)\b",
    r"\b(?:the truth is|in reality|the fact is|evidence shows)\b",
    r"\b(?:my values?|my principle|my conviction|I'm convinced)\b",
]


def _looks_like_belief(content: str) -> bool:
    """Check if content looks like it contains a belief statement."""
    return any(
        re.search(pattern, content, re.IGNORECASE)
        for pattern in _BELIEF_PATTERNS
    )


def on_memory_check(memory_id: str = "", content: str = "", **kwargs: Any) -> dict[str, Any]:
    """Hook: optionally truth-check new memories on storage.

    Only runs if the memory contains belief-like content.

    Args:
        memory_id: The stored memory's ID.
        content: The memory content text.
        **kwargs: Additional context from the event.

    Returns:
        Dict with check status and optional result.
    """
    if not content or not _looks_like_belief(content):
        return {
            "checked": False,
            "reason": "Content does not appear to contain beliefs",
            "memory_id": memory_id,
        }

    try:
        from .skill import truth_check

        result = truth_check(
            belief=content[:500],
            source="model",
            domain=kwargs.get("domain", "general"),
        )
        logger.info(
            "Memory %s truth-checked: aligned=%s, coherence=%.2f",
            memory_id,
            result.get("is_aligned"),
            result.get("collider_result", {}).get("coherence_score", 0.0),
        )
        return {
            "checked": True,
            "memory_id": memory_id,
            "is_aligned": result.get("is_aligned"),
            "truth_grade": result.get("collider_result", {}).get("truth_grade"),
            "coherence_score": result.get("collider_result", {}).get("coherence_score"),
        }
    except Exception as exc:
        logger.warning("Memory truth-check failed for %s: %s", memory_id, exc)
        return {
            "checked": False,
            "reason": f"Truth-check failed: {exc}",
            "memory_id": memory_id,
        }


def on_boot_audit(**kwargs: Any) -> dict[str, Any]:
    """Hook: run a logic audit during boot ritual.

    Checks configuration to see if boot audit is enabled.

    Args:
        **kwargs: Boot context.

    Returns:
        Dict with audit status and optional report summary.
    """
    try:
        from .alignment import AlignmentStore

        store = AlignmentStore()
        config = store.load_config()

        if not config.audit_on_boot:
            return {
                "ran": False,
                "reason": "Boot audit disabled in configuration",
            }

        from .skill import audit

        report = audit(triggered_by="boot")
        return {
            "ran": True,
            "total_beliefs": report.get("total_beliefs_scanned", 0),
            "aligned": len(report.get("aligned", [])),
            "misaligned": len(report.get("misaligned", [])),
            "truth_issues": len(report.get("truth_misalignments", [])),
            "moral_issues": len(report.get("moral_misalignments", [])),
            "recommendations": report.get("recommendations", []),
        }
    except Exception as exc:
        logger.warning("Boot audit failed: %s", exc)
        return {
            "ran": False,
            "reason": f"Boot audit failed: {exc}",
        }
