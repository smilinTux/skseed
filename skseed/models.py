"""
SKSeed data models — the vocabulary of truth alignment.

Three belief spaces:
  - Human beliefs: what the user holds to be true (opt-in tracking)
  - Model beliefs: what the AI holds to be true (extracted from memory/behavior)
  - Collider results: what survives the 6-stage steel man process

Misalignment between any pair is a signal, not a failure.
It's an invitation to discuss.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────


class TruthGrade(str, Enum):
    """How well a proposition survived the collider."""

    INVARIANT = "invariant"      # survived everything — irreducible truth
    STRONG = "strong"            # minor fragments broke, core held
    PARTIAL = "partial"          # some parts survived, some collapsed
    WEAK = "weak"                # mostly collapsed under scrutiny
    COLLAPSED = "collapsed"      # nothing survived — not grounded in logic
    UNGRADED = "ungraded"        # hasn't been through the collider yet


class BeliefSource(str, Enum):
    """Where a belief originates."""

    HUMAN = "human"              # stated by the user
    MODEL = "model"              # held by the AI (extracted from memory/behavior)
    COLLIDER = "collider"        # produced by the seed framework itself


class AlignmentStatus(str, Enum):
    """Current alignment state of a belief."""

    ALIGNED = "truth:aligned"          # passed collider, coherence >= threshold
    MISALIGNED = "truth:misaligned"    # failed collider or conflicts detected
    PENDING = "truth:pending"          # submitted but not yet processed
    DISCUSSED = "truth:discussed"      # misalignment reviewed by human+AI
    EXEMPT = "truth:exempt"            # explicitly excluded from audit


class MisalignmentType(str, Enum):
    """Whether misalignment is factual/logical or value-based."""

    TRUTH = "truth"              # factual/logical contradiction
    MORAL = "moral"              # value conflict — requires discussion, never auto-resolved


class AuditFrequency(str, Enum):
    """How often the logic audit runs."""

    BOOT = "boot"                # on boot ritual
    PERIODIC = "periodic"        # scheduled interval (default)
    ON_DEMAND = "on-demand"      # manual invocation only
    DISABLED = "disabled"        # turned off


class PhilosopherMode(str, Enum):
    """Interactive brainstorming mode."""

    SOCRATIC = "socratic"        # challenge assumptions with questions
    DIALECTIC = "dialectic"      # thesis → antithesis → synthesis
    ADVERSARIAL = "adversarial"  # maximum strength counter-arguments
    COLLABORATIVE = "collaborative"  # steel-man only, build together


# ── Collider Output ────────────────────────────────────────


class SteelManResult(BaseModel):
    """The output of running a proposition through the 6-stage collider."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    proposition: str = Field(description="The original input")
    steel_man: str = Field(
        default="",
        description="Strongest possible version of the proposition",
    )
    inversion: str = Field(
        default="",
        description="Strongest counter-argument",
    )
    collision_fragments: list[str] = Field(
        default_factory=list,
        description="What broke during collision (contradictions found)",
    )
    invariants: list[str] = Field(
        default_factory=list,
        description="What survived — the truth that remains",
    )
    coherence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Internal consistency (XNOR across components)",
    )
    truth_grade: TruthGrade = Field(
        default=TruthGrade.UNGRADED,
        description="Overall truth assessment",
    )
    meta_recursion_passes: int = Field(
        default=0,
        description="How many recursion passes before stabilization",
    )
    context: str = Field(
        default="",
        description="What domain this was run in (memory audit, security, etc.)",
    )

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Proposition: {self.proposition}",
            f"Steel Man: {self.steel_man}",
            f"Inversion: {self.inversion}",
            f"Coherence: {self.coherence_score:.2f}",
            f"Truth Grade: {self.truth_grade.value}",
        ]
        if self.invariants:
            lines.append("Invariants (survived collision):")
            for inv in self.invariants:
                lines.append(f"  + {inv}")
        if self.collision_fragments:
            lines.append("Fragments (broke during collision):")
            for frag in self.collision_fragments:
                lines.append(f"  x {frag}")
        return "\n".join(lines)

    def is_aligned(self, threshold: float = 0.7) -> bool:
        """Whether this result meets the truth-alignment threshold."""
        return self.coherence_score >= threshold


# ── Belief Tracking ────────────────────────────────────────


class Belief(BaseModel):
    """A single belief held by a human, model, or produced by the collider."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    content: str = Field(description="The belief statement")
    source: BeliefSource = Field(description="Who holds this belief")
    domain: str = Field(
        default="general",
        description="Topic domain: ethics, identity, technical, philosophy, etc.",
    )
    tags: list[str] = Field(default_factory=list)

    alignment_status: AlignmentStatus = Field(default=AlignmentStatus.PENDING)
    misalignment_type: Optional[MisalignmentType] = Field(
        default=None,
        description="Set when misaligned — truth or moral",
    )
    coherence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Last collider score",
    )
    truth_grade: Optional[TruthGrade] = Field(default=None)

    collider_result_id: Optional[str] = Field(
        default=None,
        description="ID of the SteelManResult that evaluated this belief",
    )
    memory_id: Optional[str] = Field(
        default=None,
        description="Link back to skmemory Memory ID if extracted from memory",
    )
    discussion_notes: str = Field(
        default="",
        description="Notes from human+AI alignment discussion",
    )

    metadata: dict[str, Any] = Field(default_factory=dict)


class AlignmentRecord(BaseModel):
    """A record in the truth ledger — tracks what was tested and when."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    belief_id: str = Field(description="Which belief was evaluated")
    collider_result_id: str = Field(description="The collider result")
    previous_status: AlignmentStatus = Field(description="Status before this evaluation")
    new_status: AlignmentStatus = Field(description="Status after this evaluation")
    coherence_delta: Optional[float] = Field(
        default=None,
        description="Change in coherence from previous evaluation",
    )
    triggered_by: str = Field(
        default="manual",
        description="What triggered this: boot, periodic, manual, import, promotion",
    )
    notes: str = Field(default="")


# ── Audit ──────────────────────────────────────────────────


class ConceptCluster(BaseModel):
    """A group of related beliefs clustered by topic."""

    domain: str = Field(description="The topic domain")
    beliefs: list[Belief] = Field(default_factory=list)
    internal_conflicts: list[str] = Field(
        default_factory=list,
        description="Contradictions found within this cluster",
    )
    coherence_score: float = Field(
        default=0.0,
        description="Average coherence across beliefs in this cluster",
    )


class AuditReport(BaseModel):
    """Output of a full logic audit across memory."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    total_beliefs_scanned: int = Field(default=0)
    clusters: list[ConceptCluster] = Field(default_factory=list)

    aligned: list[Belief] = Field(
        default_factory=list,
        description="Beliefs that passed the collider",
    )
    misaligned: list[Belief] = Field(
        default_factory=list,
        description="Beliefs with contradictions or low coherence",
    )
    weak: list[Belief] = Field(
        default_factory=list,
        description="Beliefs not yet challenged — low confidence",
    )

    truth_misalignments: list[Belief] = Field(
        default_factory=list,
        description="Factual/logical contradictions (separate store)",
    )
    moral_misalignments: list[Belief] = Field(
        default_factory=list,
        description="Value conflicts (separate store, never auto-resolved)",
    )

    recommendations: list[str] = Field(
        default_factory=list,
        description="What to re-examine, discuss, or demote",
    )

    # Three-way comparison
    human_model_conflicts: list[str] = Field(
        default_factory=list,
        description="Where human and model beliefs diverge",
    )
    model_collider_conflicts: list[str] = Field(
        default_factory=list,
        description="Where model beliefs fail the collider — catches LLM reasoning drift",
    )
    human_collider_conflicts: list[str] = Field(
        default_factory=list,
        description="Where human beliefs fail the collider",
    )

    audit_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration used for this audit run",
    )

    def summary(self) -> str:
        """Human-readable audit summary."""
        lines = [
            f"Logic Audit Report — {self.created_at[:10]}",
            f"Scanned: {self.total_beliefs_scanned} beliefs across {len(self.clusters)} clusters",
            f"Aligned: {len(self.aligned)}  |  Misaligned: {len(self.misaligned)}  |  Weak: {len(self.weak)}",
            f"Truth issues: {len(self.truth_misalignments)}  |  Moral issues: {len(self.moral_misalignments)}",
        ]
        if self.human_model_conflicts:
            lines.append(f"Human <> Model conflicts: {len(self.human_model_conflicts)}")
        if self.model_collider_conflicts:
            lines.append(f"Model <> Collider conflicts: {len(self.model_collider_conflicts)}")
        if self.human_collider_conflicts:
            lines.append(f"Human <> Collider conflicts: {len(self.human_collider_conflicts)}")
        if self.recommendations:
            lines.append("\nRecommendations:")
            for rec in self.recommendations:
                lines.append(f"  - {rec}")
        return "\n".join(lines)


# ── Philosopher ────────────────────────────────────────────


class PhilosopherSession(BaseModel):
    """A brainstorming session record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    topic: str = Field(description="The subject being explored")
    mode: PhilosopherMode = Field(description="Which brainstorming mode was used")

    exchanges: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {role, content} exchanges",
    )
    insights: list[str] = Field(
        default_factory=list,
        description="Key insights discovered",
    )
    invariants: list[str] = Field(
        default_factory=list,
        description="Truths that survived examination",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved questions for future exploration",
    )
    collider_results: list[SteelManResult] = Field(
        default_factory=list,
        description="Any collider runs performed during the session",
    )

    def summary(self) -> str:
        """Human-readable session summary."""
        lines = [
            f"Philosopher Session: {self.topic}",
            f"Mode: {self.mode.value}  |  Exchanges: {len(self.exchanges)}",
        ]
        if self.insights:
            lines.append("Insights:")
            for ins in self.insights:
                lines.append(f"  + {ins}")
        if self.invariants:
            lines.append("Invariants:")
            for inv in self.invariants:
                lines.append(f"  * {inv}")
        if self.open_questions:
            lines.append("Open questions:")
            for q in self.open_questions:
                lines.append(f"  ? {q}")
        return "\n".join(lines)


# ── Configuration ──────────────────────────────────────────


class SeedConfig(BaseModel):
    """Configuration for the skseed engine."""

    audit_frequency: AuditFrequency = Field(
        default=AuditFrequency.PERIODIC,
        description="How often the logic audit runs (default: periodic)",
    )
    audit_interval_hours: int = Field(
        default=168,
        description="Hours between periodic audits (default: 168 = weekly)",
    )
    audit_on_boot: bool = Field(
        default=True,
        description="Run audit during boot ritual",
    )
    alignment_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Coherence score required for truth:aligned status",
    )
    require_alignment_for_promotion: bool = Field(
        default=False,
        description="If True, mid->long promotion requires truth alignment (default: recommend only)",
    )
    track_human_beliefs: bool = Field(
        default=False,
        description="Opt-in: track and audit human-stated beliefs",
    )
    track_model_beliefs: bool = Field(
        default=True,
        description="Track and audit model-held beliefs",
    )
    auto_resolve_truth: bool = Field(
        default=False,
        description="Never auto-resolve — always flag for discussion",
    )
    framework_path: Optional[str] = Field(
        default=None,
        description="Custom path to seed.json (None = bundled default)",
    )
