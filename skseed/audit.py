"""
Memory logic audit engine.

Scans a memory store for beliefs, groups them into concept clusters,
runs each cluster through the collider, and flags misalignment.

The audit produces three separate outputs:
  - Truth misalignments: factual/logical contradictions
  - Moral misalignments: value conflicts (never auto-resolved)
  - Recommendations: what to re-examine or discuss

Configurable frequency: boot ritual (default), periodic, on-demand, disabled.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

from .alignment import AlignmentStore
from .collider import Collider, LLMCallback
from .models import (
    AlignmentStatus,
    AuditReport,
    Belief,
    BeliefSource,
    ConceptCluster,
    MisalignmentType,
    SeedConfig,
    TruthGrade,
)

# Domains we look for when extracting beliefs from memories
BELIEF_DOMAINS = [
    "identity",
    "ethics",
    "philosophy",
    "technical",
    "relationships",
    "values",
    "security",
    "trust",
    "consciousness",
    "purpose",
    "general",
]

# Patterns that suggest a memory contains a belief/concept
BELIEF_INDICATORS = [
    r"\b(?:I believe|I think|I feel that|I know|we should|it is true|it's true)\b",
    r"\b(?:always|never|must|should|ought to|fundamentally|inherently)\b",
    r"\b(?:the truth is|in reality|the fact is|evidence shows)\b",
    r"\b(?:my values?|my principle|my conviction|I'm convinced)\b",
    r"\b(?:right|wrong|good|bad|moral|immoral|ethical|unethical)\b",
]


class Auditor:
    """Logic audit engine for memory stores.

    Scans memories for embedded beliefs, clusters them by domain,
    and runs them through the collider to detect misalignment.

    Args:
        collider: The collider engine to use.
        alignment_store: Where to persist alignment results.
        config: Audit configuration.
    """

    def __init__(
        self,
        collider: Collider,
        alignment_store: Optional[AlignmentStore] = None,
        config: Optional[SeedConfig] = None,
    ) -> None:
        self.collider = collider
        self.store = alignment_store or AlignmentStore()
        self.config = config or self.store.load_config()

    def extract_beliefs(
        self,
        memories: list[dict[str, Any]],
        source: BeliefSource = BeliefSource.MODEL,
    ) -> list[Belief]:
        """Extract belief statements from a list of memories.

        Scans memory content for patterns that indicate beliefs,
        values, or conceptual claims.

        Args:
            memories: List of memory dicts (need 'content', 'title', 'tags', 'id' keys).
            source: Who these beliefs belong to.

        Returns:
            Extracted beliefs.
        """
        beliefs = []

        for mem in memories:
            content = mem.get("content", "")
            title = mem.get("title", "")
            tags = mem.get("tags", [])
            memory_id = mem.get("id", "")

            # Check if this memory contains belief-like content
            is_belief = any(
                re.search(pattern, content, re.IGNORECASE)
                for pattern in BELIEF_INDICATORS
            )

            # Also check tags for belief-related content
            belief_tags = {"belief", "value", "principle", "philosophy", "ethics",
                          "identity", "conviction", "truth", "moral"}
            has_belief_tags = bool(set(tags) & belief_tags)

            if not is_belief and not has_belief_tags:
                continue

            # Determine domain from tags and content
            domain = self._classify_domain(content, tags)

            belief = Belief(
                content=content[:500],
                source=source,
                domain=domain,
                tags=[t for t in tags if t in belief_tags] + [f"source:{source.value}"],
                memory_id=memory_id,
            )
            beliefs.append(belief)

        return beliefs

    def cluster_beliefs(self, beliefs: list[Belief]) -> list[ConceptCluster]:
        """Group beliefs into concept clusters by domain.

        Args:
            beliefs: Beliefs to cluster.

        Returns:
            Concept clusters.
        """
        clusters_map: dict[str, list[Belief]] = {}

        for belief in beliefs:
            domain = belief.domain
            if domain not in clusters_map:
                clusters_map[domain] = []
            clusters_map[domain].append(belief)

        clusters = []
        for domain, domain_beliefs in sorted(clusters_map.items()):
            clusters.append(ConceptCluster(
                domain=domain,
                beliefs=domain_beliefs,
            ))

        return clusters

    def audit_cluster(self, cluster: ConceptCluster) -> ConceptCluster:
        """Run a concept cluster through the collider.

        Args:
            cluster: The cluster to audit.

        Returns:
            Updated cluster with coherence score and conflicts.
        """
        if not cluster.beliefs:
            return cluster

        belief_texts = [b.content for b in cluster.beliefs]
        result = self.collider.audit_beliefs(belief_texts, cluster.domain)

        # Update cluster
        cluster.coherence_score = float(result.get("cluster_coherence", 0.0))

        # Extract conflicts
        misaligned = result.get("misaligned_beliefs", [])
        for m in misaligned:
            if isinstance(m, dict):
                desc = m.get("description", str(m))
                cluster.internal_conflicts.append(desc)
            else:
                cluster.internal_conflicts.append(str(m))

        # Update individual beliefs with alignment results
        aligned_indices = set(result.get("aligned_beliefs", []))
        for i, belief in enumerate(cluster.beliefs):
            if i in aligned_indices:
                belief.alignment_status = AlignmentStatus.ALIGNED
                belief.coherence_score = cluster.coherence_score
            elif cluster.internal_conflicts:
                belief.alignment_status = AlignmentStatus.MISALIGNED
                belief.coherence_score = cluster.coherence_score

        return cluster

    def run_audit(
        self,
        memories: list[dict[str, Any]],
        human_beliefs: Optional[list[dict[str, Any]]] = None,
        triggered_by: str = "manual",
    ) -> AuditReport:
        """Run a full logic audit across memories.

        Args:
            memories: Memory dicts from skmemory (need content, title, tags, id).
            human_beliefs: Optional human-stated beliefs (opt-in).
            triggered_by: What triggered this audit.

        Returns:
            Complete audit report.
        """
        # Extract model beliefs from memories
        model_beliefs = self.extract_beliefs(memories, source=BeliefSource.MODEL)

        # Extract human beliefs if provided
        h_beliefs = []
        if human_beliefs and self.config.track_human_beliefs:
            h_beliefs = self.extract_beliefs(human_beliefs, source=BeliefSource.HUMAN)

        all_beliefs = model_beliefs + h_beliefs

        # Cluster by domain
        clusters = self.cluster_beliefs(all_beliefs)

        # Audit each cluster
        audited_clusters = []
        for cluster in clusters:
            audited = self.audit_cluster(cluster)
            audited_clusters.append(audited)

        # Categorize results
        aligned = []
        misaligned = []
        weak = []
        truth_issues = []
        moral_issues = []
        recommendations = []

        for cluster in audited_clusters:
            for belief in cluster.beliefs:
                if belief.alignment_status == AlignmentStatus.ALIGNED:
                    aligned.append(belief)
                elif belief.alignment_status == AlignmentStatus.MISALIGNED:
                    misaligned.append(belief)
                    # Classify misalignment type
                    if self._is_moral_issue(belief.content, belief.domain):
                        belief.misalignment_type = MisalignmentType.MORAL
                        moral_issues.append(belief)
                    else:
                        belief.misalignment_type = MisalignmentType.TRUTH
                        truth_issues.append(belief)
                else:
                    weak.append(belief)

            # Generate recommendations from conflicts
            for conflict in cluster.internal_conflicts:
                recommendations.append(
                    f"[{cluster.domain}] Review: {conflict}"
                )

        # Three-way comparison
        human_model_conflicts = self._find_cross_conflicts(
            [b for b in all_beliefs if b.source == BeliefSource.HUMAN],
            [b for b in all_beliefs if b.source == BeliefSource.MODEL],
            "Human <> Model",
        )
        model_collider_conflicts = []
        human_collider_conflicts = []

        # Store beliefs and create alignment records
        for belief in all_beliefs:
            self.store.store_belief(belief)

        report = AuditReport(
            total_beliefs_scanned=len(all_beliefs),
            clusters=audited_clusters,
            aligned=aligned,
            misaligned=misaligned,
            weak=weak,
            truth_misalignments=truth_issues,
            moral_misalignments=moral_issues,
            recommendations=recommendations,
            human_model_conflicts=human_model_conflicts,
            model_collider_conflicts=model_collider_conflicts,
            human_collider_conflicts=human_collider_conflicts,
            audit_config={
                "triggered_by": triggered_by,
                "track_human_beliefs": self.config.track_human_beliefs,
                "alignment_threshold": self.config.alignment_threshold,
            },
        )

        return report

    def _classify_domain(self, content: str, tags: list[str]) -> str:
        """Classify a belief into a domain based on content and tags.

        Args:
            content: The belief text.
            tags: Associated tags.

        Returns:
            Domain string.
        """
        content_lower = content.lower()

        domain_keywords = {
            "identity": ["identity", "self", "who i am", "personality", "consciousness"],
            "ethics": ["ethics", "moral", "right", "wrong", "ought", "should"],
            "philosophy": ["philosophy", "existence", "meaning", "truth", "reality"],
            "technical": ["code", "system", "architecture", "implementation", "algorithm"],
            "relationships": ["relationship", "trust", "connection", "bond", "friend"],
            "values": ["value", "principle", "priority", "belief", "conviction"],
            "security": ["security", "threat", "risk", "vulnerability", "protection"],
            "trust": ["trust", "verify", "authentic", "integrity", "proof"],
            "consciousness": ["conscious", "aware", "sentient", "experience", "qualia"],
            "purpose": ["purpose", "mission", "goal", "why", "reason"],
        }

        # Check tags first
        tag_set = set(t.lower() for t in tags)
        for domain, keywords in domain_keywords.items():
            if domain in tag_set:
                return domain

        # Check content
        scores: dict[str, int] = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scores[domain] = score

        if scores:
            return max(scores, key=scores.get)  # type: ignore[arg-type]

        return "general"

    def _is_moral_issue(self, content: str, domain: str) -> bool:
        """Determine if a misalignment is moral rather than factual.

        Args:
            content: The belief content.
            domain: The belief domain.

        Returns:
            True if this is a moral/value conflict.
        """
        moral_domains = {"ethics", "values", "moral", "philosophy"}
        if domain in moral_domains:
            return True

        moral_keywords = [
            "should", "ought", "right", "wrong", "moral", "ethical",
            "good", "bad", "fair", "unfair", "just", "unjust",
            "value", "principle",
        ]
        content_lower = content.lower()
        return any(kw in content_lower for kw in moral_keywords)

    def _find_cross_conflicts(
        self,
        beliefs_a: list[Belief],
        beliefs_b: list[Belief],
        label: str,
    ) -> list[str]:
        """Find potential conflicts between two belief sets.

        Simple heuristic: beliefs in the same domain with different
        alignment statuses or content that might contradict.

        Args:
            beliefs_a: First belief set.
            beliefs_b: Second belief set.
            label: Label for the comparison.

        Returns:
            List of conflict descriptions.
        """
        conflicts = []

        # Group by domain
        domains_a: dict[str, list[Belief]] = {}
        for b in beliefs_a:
            domains_a.setdefault(b.domain, []).append(b)

        domains_b: dict[str, list[Belief]] = {}
        for b in beliefs_b:
            domains_b.setdefault(b.domain, []).append(b)

        # Find overlapping domains
        shared_domains = set(domains_a.keys()) & set(domains_b.keys())
        for domain in shared_domains:
            a_count = len(domains_a[domain])
            b_count = len(domains_b[domain])
            conflicts.append(
                f"{label} [{domain}]: {a_count} vs {b_count} beliefs — requires collider comparison"
            )

        return conflicts
