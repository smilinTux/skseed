"""
Three-way truth alignment tracker.

Three belief stores, kept separate:
  1. Human beliefs — what the user states as true (opt-in)
  2. Model beliefs — what the AI holds as true (extracted from memory)
  3. Collider results — what survives the 6-stage process

Misalignment between any pair is a signal for discussion.
Truth misalignments (factual/logical) can potentially be resolved.
Moral misalignments (value conflicts) are NEVER auto-resolved.

Tagged for potential future collapse if desired, but the separation
exists so humans can clearly see that both types exist.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import (
    AlignmentRecord,
    AlignmentStatus,
    Belief,
    BeliefSource,
    MisalignmentType,
    SeedConfig,
    SteelManResult,
)

DEFAULT_ALIGNMENT_DIR = os.path.expanduser("~/.skseed/alignment")


class AlignmentStore:
    """Persistent store for the three belief spaces.

    Beliefs are stored as JSON files in separate directories:
      alignment/human/    — human beliefs (opt-in)
      alignment/model/    — model beliefs
      alignment/collider/ — collider-produced truths
      alignment/ledger/   — alignment history records
      alignment/issues/   — misalignment issues pending discussion
    """

    def __init__(self, base_dir: str = DEFAULT_ALIGNMENT_DIR) -> None:
        self._base = Path(base_dir)
        self._dirs = {
            BeliefSource.HUMAN: self._base / "human",
            BeliefSource.MODEL: self._base / "model",
            BeliefSource.COLLIDER: self._base / "collider",
        }
        self._ledger_dir = self._base / "ledger"
        self._issues_dir = self._base / "issues"
        self._config_path = self._base / "config.json"

        for d in list(self._dirs.values()) + [self._ledger_dir, self._issues_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> SeedConfig:
        """Load configuration or return defaults."""
        if self._config_path.exists():
            try:
                raw = json.loads(self._config_path.read_text(encoding="utf-8"))
                return SeedConfig(**raw)
            except Exception:
                pass
        return SeedConfig()

    def save_config(self, config: SeedConfig) -> None:
        """Persist configuration."""
        self._config_path.write_text(
            config.model_dump_json(indent=2), encoding="utf-8"
        )

    # ── Belief CRUD ────────────────────────────────────────

    def store_belief(self, belief: Belief) -> str:
        """Store a belief in the appropriate space.

        Args:
            belief: The belief to store.

        Returns:
            The belief ID.
        """
        target_dir = self._dirs.get(belief.source, self._dirs[BeliefSource.MODEL])
        path = target_dir / f"{belief.id}.json"
        path.write_text(belief.model_dump_json(indent=2), encoding="utf-8")
        return belief.id

    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """Retrieve a belief by ID, searching all stores."""
        for source_dir in self._dirs.values():
            path = source_dir / f"{belief_id}.json"
            if path.exists():
                return Belief.model_validate_json(path.read_text(encoding="utf-8"))
        return None

    def list_beliefs(
        self,
        source: Optional[BeliefSource] = None,
        status: Optional[AlignmentStatus] = None,
        domain: Optional[str] = None,
        misalignment_type: Optional[MisalignmentType] = None,
    ) -> list[Belief]:
        """List beliefs with optional filters.

        Args:
            source: Filter by belief source (human/model/collider).
            status: Filter by alignment status.
            domain: Filter by topic domain.
            misalignment_type: Filter by misalignment type.

        Returns:
            Matching beliefs.
        """
        dirs = (
            [self._dirs[source]] if source else list(self._dirs.values())
        )
        beliefs = []

        for d in dirs:
            for path in sorted(d.glob("*.json")):
                try:
                    b = Belief.model_validate_json(path.read_text(encoding="utf-8"))
                    if status and b.alignment_status != status:
                        continue
                    if domain and b.domain != domain:
                        continue
                    if misalignment_type and b.misalignment_type != misalignment_type:
                        continue
                    beliefs.append(b)
                except Exception:
                    continue

        return beliefs

    def update_belief(self, belief: Belief) -> None:
        """Update an existing belief in-place."""
        belief.updated_at = datetime.now(timezone.utc).isoformat()
        self.store_belief(belief)

    def delete_belief(self, belief_id: str) -> bool:
        """Remove a belief from all stores."""
        for source_dir in self._dirs.values():
            path = source_dir / f"{belief_id}.json"
            if path.exists():
                path.unlink()
                return True
        return False

    # ── Alignment Operations ───────────────────────────────

    def record_alignment(
        self,
        belief: Belief,
        result: SteelManResult,
        config: Optional[SeedConfig] = None,
        triggered_by: str = "manual",
    ) -> AlignmentRecord:
        """Record the result of running a belief through the collider.

        Updates the belief's status and scores, stores a ledger entry,
        and creates an issue if misaligned.

        Args:
            belief: The belief that was evaluated.
            result: The collider output.
            config: Configuration (for threshold). None = defaults.
            triggered_by: What triggered this evaluation.

        Returns:
            The alignment record.
        """
        cfg = config or self.load_config()
        previous_status = belief.alignment_status

        # Determine new status
        if result.is_aligned(cfg.alignment_threshold):
            new_status = AlignmentStatus.ALIGNED
        else:
            new_status = AlignmentStatus.MISALIGNED

        # Calculate coherence delta
        coherence_delta = None
        if belief.coherence_score is not None:
            coherence_delta = result.coherence_score - belief.coherence_score

        # Update belief
        belief.alignment_status = new_status
        belief.coherence_score = result.coherence_score
        belief.truth_grade = result.truth_grade
        belief.collider_result_id = result.id
        self.update_belief(belief)

        # Create ledger record
        record = AlignmentRecord(
            belief_id=belief.id,
            collider_result_id=result.id,
            previous_status=previous_status,
            new_status=new_status,
            coherence_delta=coherence_delta,
            triggered_by=triggered_by,
        )
        ledger_path = self._ledger_dir / f"{record.id}.json"
        ledger_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

        # If misaligned, create an issue for discussion
        if new_status == AlignmentStatus.MISALIGNED:
            self._create_issue(belief, result)

        return record

    def _create_issue(self, belief: Belief, result: SteelManResult) -> None:
        """Create a misalignment issue for human+AI discussion."""
        issue = {
            "belief_id": belief.id,
            "belief_content": belief.content,
            "source": belief.source.value,
            "domain": belief.domain,
            "misalignment_type": (
                belief.misalignment_type.value if belief.misalignment_type else "unknown"
            ),
            "coherence_score": result.coherence_score,
            "truth_grade": result.truth_grade.value if result.truth_grade else "ungraded",
            "invariants": result.invariants,
            "collision_fragments": result.collision_fragments,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "open",
        }
        issue_path = self._issues_dir / f"{belief.id}.json"
        issue_path.write_text(json.dumps(issue, indent=2), encoding="utf-8")

    def list_issues(self, status: str = "open") -> list[dict[str, Any]]:
        """List misalignment issues pending discussion.

        Args:
            status: Filter by issue status (open/discussed/resolved).

        Returns:
            List of issue dicts.
        """
        issues = []
        for path in sorted(self._issues_dir.glob("*.json")):
            try:
                issue = json.loads(path.read_text(encoding="utf-8"))
                if issue.get("status") == status:
                    issues.append(issue)
            except Exception:
                continue
        return issues

    def resolve_issue(
        self,
        belief_id: str,
        notes: str,
        new_status: AlignmentStatus = AlignmentStatus.DISCUSSED,
    ) -> bool:
        """Mark an issue as discussed/resolved.

        Args:
            belief_id: The belief whose issue to resolve.
            notes: Discussion notes.
            new_status: New status for the belief.

        Returns:
            True if issue was found and resolved.
        """
        issue_path = self._issues_dir / f"{belief_id}.json"
        if not issue_path.exists():
            return False

        issue = json.loads(issue_path.read_text(encoding="utf-8"))
        issue["status"] = "discussed"
        issue["discussion_notes"] = notes
        issue["resolved_at"] = datetime.now(timezone.utc).isoformat()
        issue_path.write_text(json.dumps(issue, indent=2), encoding="utf-8")

        # Update the belief
        belief = self.get_belief(belief_id)
        if belief:
            belief.alignment_status = new_status
            belief.discussion_notes = notes
            self.update_belief(belief)

        return True

    # ── Three-Way Comparison ───────────────────────────────

    def compare_beliefs(
        self, domain: Optional[str] = None
    ) -> dict[str, list[str]]:
        """Compare beliefs across all three stores for a domain.

        Returns conflicts between human<>model, model<>collider,
        and human<>collider.

        Args:
            domain: Topic domain to compare (None = all).

        Returns:
            Dict with conflict lists for each pair.
        """
        human = self.list_beliefs(source=BeliefSource.HUMAN, domain=domain)
        model = self.list_beliefs(source=BeliefSource.MODEL, domain=domain)
        collider = self.list_beliefs(source=BeliefSource.COLLIDER, domain=domain)

        return {
            "human_beliefs": [b.content for b in human],
            "model_beliefs": [b.content for b in model],
            "collider_truths": [b.content for b in collider],
            "human_count": len(human),
            "model_count": len(model),
            "collider_count": len(collider),
            "domains": list(
                {b.domain for b in human + model + collider}
            ),
        }

    # ── Ledger ─────────────────────────────────────────────

    def get_ledger(self, limit: int = 50) -> list[AlignmentRecord]:
        """Get recent alignment history.

        Args:
            limit: Max records to return.

        Returns:
            Recent alignment records, newest first.
        """
        records = []
        paths = sorted(self._ledger_dir.glob("*.json"), reverse=True)

        for path in paths[:limit]:
            try:
                r = AlignmentRecord.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
                records.append(r)
            except Exception:
                continue

        return records

    def coherence_trend(
        self,
        belief_id: str,
    ) -> list[dict[str, Any]]:
        """Get the coherence score history for a belief.

        Args:
            belief_id: The belief to track.

        Returns:
            List of {timestamp, coherence, grade} dicts, oldest first.
        """
        records = []
        for path in sorted(self._ledger_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if raw.get("belief_id") == belief_id:
                    records.append({
                        "timestamp": raw.get("timestamp"),
                        "coherence_delta": raw.get("coherence_delta"),
                        "status": raw.get("new_status"),
                        "triggered_by": raw.get("triggered_by"),
                    })
            except Exception:
                continue
        return records
