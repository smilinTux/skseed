"""
Philosopher mode — interactive brainstorming through the collider.

Four modes of engagement:

  SOCRATIC: Challenge assumptions with questions. Never state conclusions.
  DIALECTIC: Thesis → antithesis → synthesis via Hegelian dialectics.
  ADVERSARIAL: Maximum strength counter-arguments. Try to break the idea.
  COLLABORATIVE: Steel-man only. Build the strongest version together.

Sessions can be saved as memories and their invariants tracked
for truth alignment over time.
"""

from __future__ import annotations

from typing import Optional

from .collider import Collider, LLMCallback
from .models import PhilosopherMode, PhilosopherSession, SteelManResult


class Philosopher:
    """Interactive brainstorming engine.

    Wraps the collider with conversational modes for exploring ideas.

    Args:
        collider: The collider engine.
    """

    def __init__(self, collider: Collider) -> None:
        self.collider = collider

    def start_session(
        self,
        topic: str,
        mode: PhilosopherMode = PhilosopherMode.DIALECTIC,
    ) -> PhilosopherSession:
        """Start a new philosopher session.

        Generates the initial prompt and records the opening exchange.

        Args:
            topic: The subject to explore.
            mode: Which brainstorming mode to use.

        Returns:
            A new PhilosopherSession with the initial exchange.
        """
        session = PhilosopherSession(topic=topic, mode=mode)

        # Generate and optionally execute the opening prompt
        response = self.collider.philosopher(topic, mode.value)

        session.exchanges.append({
            "role": "user",
            "content": f"Let's explore: {topic}",
        })
        session.exchanges.append({
            "role": "philosopher",
            "content": response,
        })

        return session

    def continue_session(
        self,
        session: PhilosopherSession,
        user_input: str,
    ) -> PhilosopherSession:
        """Continue an existing philosopher session with new input.

        Args:
            session: The ongoing session.
            user_input: What the user wants to explore next.

        Returns:
            Updated session with new exchange.
        """
        # Build context from previous exchanges
        context = self._build_context(session)
        continuation_topic = f"{session.topic} — continuing: {user_input}"

        response = self.collider.philosopher(continuation_topic, session.mode.value)

        session.exchanges.append({
            "role": "user",
            "content": user_input,
        })
        session.exchanges.append({
            "role": "philosopher",
            "content": response,
        })

        return session

    def collide_insight(
        self,
        session: PhilosopherSession,
        insight: str,
    ) -> SteelManResult:
        """Run a discovered insight through the full collider.

        Takes something interesting from the session and tests it
        rigorously. If it survives, it's an invariant worth keeping.

        Args:
            session: The current session.
            insight: The insight to test.

        Returns:
            Collider result for the insight.
        """
        result = self.collider.collide(
            insight,
            context=f"philosopher-{session.mode.value}",
        )
        session.collider_results.append(result)

        if result.is_aligned():
            session.invariants.append(insight)
        else:
            session.open_questions.append(
                f"Needs more examination: {insight} (coherence: {result.coherence_score:.2f})"
            )

        return result

    def extract_insights(
        self,
        session: PhilosopherSession,
    ) -> PhilosopherSession:
        """Ask the LLM to extract insights from a session.

        Reviews all exchanges and identifies key discoveries,
        invariants, and open questions.

        Args:
            session: The session to analyze.

        Returns:
            Session with populated insights/invariants/open_questions.
        """
        if not self.collider.can_execute:
            return session

        exchanges_text = "\n".join(
            f"[{e['role']}]: {e['content'][:300]}"
            for e in session.exchanges
        )

        prompt = f"""Review this philosopher session and extract:

TOPIC: {session.topic}
MODE: {session.mode.value}

EXCHANGES:
{exchanges_text}

Return as JSON:
- insights: (key discoveries, list of strings)
- invariants: (truths that survived examination, list of strings)
- open_questions: (unresolved questions worth exploring, list of strings)"""

        if self.collider._llm:
            raw = self.collider._llm(prompt)
            parsed = self.collider._extract_json(raw)
            if parsed:
                session.insights.extend(parsed.get("insights", []))
                session.invariants.extend(parsed.get("invariants", []))
                session.open_questions.extend(parsed.get("open_questions", []))

        return session

    def session_summary(self, session: PhilosopherSession) -> str:
        """Generate a human-readable summary of a session.

        Args:
            session: The session to summarize.

        Returns:
            Formatted summary string.
        """
        lines = [
            f"{'=' * 60}",
            f"Philosopher Session: {session.topic}",
            f"Mode: {session.mode.value}",
            f"Exchanges: {len(session.exchanges)}",
            f"{'=' * 60}",
        ]

        if session.insights:
            lines.append("\nInsights:")
            for ins in session.insights:
                lines.append(f"  + {ins}")

        if session.invariants:
            lines.append("\nInvariants (survived examination):")
            for inv in session.invariants:
                lines.append(f"  * {inv}")

        if session.open_questions:
            lines.append("\nOpen Questions:")
            for q in session.open_questions:
                lines.append(f"  ? {q}")

        if session.collider_results:
            lines.append(f"\nCollider Runs: {len(session.collider_results)}")
            for r in session.collider_results:
                status = "ALIGNED" if r.is_aligned() else "NEEDS WORK"
                lines.append(
                    f"  [{status}] {r.proposition[:60]}... "
                    f"(coherence: {r.coherence_score:.2f})"
                )

        return "\n".join(lines)

    def _build_context(self, session: PhilosopherSession) -> str:
        """Build conversation context from session exchanges.

        Args:
            session: The session to build context from.

        Returns:
            Context string.
        """
        # Take the last 6 exchanges for context
        recent = session.exchanges[-6:]
        return "\n".join(
            f"[{e['role']}]: {e['content'][:200]}"
            for e in recent
        )
