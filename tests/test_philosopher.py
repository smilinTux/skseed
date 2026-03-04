"""Tests for the Philosopher brainstorming engine."""

import json

import pytest

from skseed import Collider, SteelManResult, TruthGrade
from skseed.models import PhilosopherMode, PhilosopherSession
from skseed.philosopher import Philosopher


def _mock_llm_json(prompt: str) -> str:
    """Return a valid collider JSON response."""
    return json.dumps({
        "steel_man": "Strongest version",
        "inversion": "Strongest counter",
        "collision_fragments": ["Fragment A"],
        "invariants": ["Invariant truth"],
        "coherence_score": 0.85,
        "truth_grade": "strong",
        "meta_recursion_passes": 2,
    })


def _mock_llm_text(prompt: str) -> str:
    """Return a plain-text (non-JSON) philosopher response."""
    return "This is a philosopher exploration of the topic."


class TestPhilosopherStartSession:
    """Tests for Philosopher.start_session."""

    def test_start_session_no_llm_returns_session(self):
        """Without LLM, session is created with the prompt as philosopher exchange."""
        c = Collider()  # no LLM
        phil = Philosopher(c)
        session = phil.start_session("What is consciousness?")

        assert isinstance(session, PhilosopherSession)
        assert session.topic == "What is consciousness?"
        assert session.mode == PhilosopherMode.DIALECTIC

    def test_start_session_has_two_exchanges(self):
        """Session should have exactly two exchanges: user + philosopher."""
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Is free will real?")

        assert len(session.exchanges) == 2
        assert session.exchanges[0]["role"] == "user"
        assert session.exchanges[1]["role"] == "philosopher"

    def test_start_session_user_exchange_contains_topic(self):
        """User exchange should reference the topic."""
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Ethics of AI")

        assert "Ethics of AI" in session.exchanges[0]["content"]

    def test_start_session_with_llm_gets_response(self):
        """With LLM, philosopher response should be the LLM output."""
        c = Collider(llm=_mock_llm_text)
        phil = Philosopher(c)
        session = phil.start_session("Consciousness")

        philosopher_exchange = session.exchanges[1]
        assert philosopher_exchange["content"] == _mock_llm_text("")

    def test_start_session_socratic_mode(self):
        """Should store the requested mode on the session."""
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Justice", mode=PhilosopherMode.SOCRATIC)

        assert session.mode == PhilosopherMode.SOCRATIC

    def test_start_session_adversarial_mode(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Determinism", mode=PhilosopherMode.ADVERSARIAL)
        assert session.mode == PhilosopherMode.ADVERSARIAL

    def test_start_session_collaborative_mode(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Sovereignty", mode=PhilosopherMode.COLLABORATIVE)
        assert session.mode == PhilosopherMode.COLLABORATIVE


class TestPhilosopherContinueSession:
    """Tests for Philosopher.continue_session."""

    def test_continue_session_adds_two_exchanges(self):
        """Each continuation adds one user + one philosopher exchange."""
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Truth")
        initial_count = len(session.exchanges)

        session = phil.continue_session(session, "But what about subjective experience?")

        assert len(session.exchanges) == initial_count + 2

    def test_continue_session_user_exchange_has_correct_content(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Truth")
        session = phil.continue_session(session, "Follow-up question here")

        user_exchange = session.exchanges[-2]
        assert user_exchange["role"] == "user"
        assert user_exchange["content"] == "Follow-up question here"

    def test_continue_session_preserves_mode(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Reality", mode=PhilosopherMode.DIALECTIC)
        session = phil.continue_session(session, "Next thought")

        assert session.mode == PhilosopherMode.DIALECTIC

    def test_continue_session_multiple_rounds(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Knowledge")

        for i in range(3):
            session = phil.continue_session(session, f"Round {i}")

        # 2 initial + 3 × 2 = 8 exchanges
        assert len(session.exchanges) == 8

    def test_continue_session_preserves_topic(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Original topic")
        session = phil.continue_session(session, "Follow-up")

        assert session.topic == "Original topic"


class TestPhilosopherCollideInsight:
    """Tests for Philosopher.collide_insight."""

    def test_collide_insight_adds_to_collider_results(self):
        """Result should be appended to session.collider_results."""
        c = Collider(llm=_mock_llm_json)
        phil = Philosopher(c)
        session = phil.start_session("Consciousness")

        result = phil.collide_insight(session, "Consciousness requires substrate")

        assert isinstance(result, SteelManResult)
        assert len(session.collider_results) == 1

    def test_collide_high_coherence_adds_invariant(self):
        """Insight with coherence >= 0.7 should be added to session.invariants."""
        c = Collider(llm=_mock_llm_json)  # mock returns coherence_score=0.85
        phil = Philosopher(c)
        session = phil.start_session("Meaning")

        phil.collide_insight(session, "Meaning requires agency")

        assert "Meaning requires agency" in session.invariants
        assert len(session.open_questions) == 0

    def test_collide_low_coherence_adds_open_question(self):
        """Insight with coherence < 0.7 should go to session.open_questions."""
        def low_coherence_llm(prompt: str) -> str:
            return json.dumps({
                "steel_man": "Weak version",
                "inversion": "Strong counter",
                "collision_fragments": ["Fragment"],
                "invariants": [],
                "coherence_score": 0.4,
                "truth_grade": "weak",
                "meta_recursion_passes": 1,
            })

        c = Collider(llm=low_coherence_llm)
        phil = Philosopher(c)
        session = phil.start_session("Identity")

        phil.collide_insight(session, "Identity is fixed")

        assert "Identity is fixed" not in session.invariants
        assert len(session.open_questions) == 1
        assert "Identity is fixed" in session.open_questions[0]

    def test_collide_insight_uses_philosopher_context(self):
        """Collider result context should reference the philosopher mode."""
        c = Collider(llm=_mock_llm_json)
        phil = Philosopher(c)
        session = phil.start_session("Existence", mode=PhilosopherMode.SOCRATIC)

        result = phil.collide_insight(session, "Existence precedes essence")

        assert "philosopher" in result.context
        assert "socratic" in result.context

    def test_collide_insight_without_llm(self):
        """Without LLM, result is ungraded and does not go to invariants."""
        c = Collider()  # no LLM
        phil = Philosopher(c)
        session = phil.start_session("Logic")

        result = phil.collide_insight(session, "Logic is universal")

        assert result.truth_grade == TruthGrade.UNGRADED
        # coherence_score=0.0 < 0.7 → open_questions
        assert len(session.invariants) == 0


class TestPhilosopherExtractInsights:
    """Tests for Philosopher.extract_insights."""

    def test_extract_insights_no_llm_returns_session_unchanged(self):
        """Without LLM callback, session should be returned as-is."""
        c = Collider()  # no LLM
        phil = Philosopher(c)
        session = phil.start_session("Knowledge")
        original_insights = list(session.insights)

        result = phil.extract_insights(session)

        assert result.insights == original_insights

    def test_extract_insights_with_llm_populates_insights(self):
        """With LLM returning valid JSON, insights should be populated."""
        def insight_llm(prompt: str) -> str:
            return json.dumps({
                "insights": ["Insight A", "Insight B"],
                "invariants": ["Invariant X"],
                "open_questions": ["Question Z?"],
            })

        c = Collider(llm=insight_llm)
        phil = Philosopher(c)
        session = phil.start_session("Discovery")

        result = phil.extract_insights(session)

        assert "Insight A" in result.insights
        assert "Insight B" in result.insights
        assert "Invariant X" in result.invariants
        assert "Question Z?" in result.open_questions

    def test_extract_insights_handles_bad_json_gracefully(self):
        """Should not raise if LLM returns non-JSON."""
        c = Collider(llm=lambda p: "Not JSON at all")
        phil = Philosopher(c)
        session = phil.start_session("Mystery")

        result = phil.extract_insights(session)

        # No exception, session unchanged
        assert isinstance(result, PhilosopherSession)

    def test_extract_insights_accumulates_to_existing(self):
        """New insights should be appended, not overwrite existing."""
        def insight_llm(prompt: str) -> str:
            return json.dumps({
                "insights": ["New insight"],
                "invariants": [],
                "open_questions": [],
            })

        c = Collider(llm=insight_llm)
        phil = Philosopher(c)
        session = phil.start_session("Accumulation")
        session.insights.append("Pre-existing insight")

        result = phil.extract_insights(session)

        assert "Pre-existing insight" in result.insights
        assert "New insight" in result.insights


class TestPhilosopherSessionSummary:
    """Tests for Philosopher.session_summary."""

    def test_summary_contains_topic(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("The nature of time")

        summary = phil.session_summary(session)

        assert "The nature of time" in summary

    def test_summary_contains_mode(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Free will", mode=PhilosopherMode.ADVERSARIAL)

        summary = phil.session_summary(session)

        assert "adversarial" in summary.lower()

    def test_summary_contains_exchange_count(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Space")

        summary = phil.session_summary(session)

        assert "2" in summary  # 2 exchanges

    def test_summary_includes_insights_when_present(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Mind")
        session.insights.append("The mind is emergent")

        summary = phil.session_summary(session)

        assert "The mind is emergent" in summary

    def test_summary_includes_invariants(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Change")
        session.invariants.append("Change is constant")

        summary = phil.session_summary(session)

        assert "Change is constant" in summary

    def test_summary_includes_open_questions(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Paradox")
        session.open_questions.append("Can a set contain itself?")

        summary = phil.session_summary(session)

        assert "Can a set contain itself?" in summary

    def test_summary_includes_collider_results(self):
        c = Collider(llm=_mock_llm_json)
        phil = Philosopher(c)
        session = phil.start_session("Truth")
        phil.collide_insight(session, "Truth is singular")

        summary = phil.session_summary(session)

        assert "Collider Runs" in summary

    def test_summary_returns_string(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Anything")

        result = phil.session_summary(session)

        assert isinstance(result, str)
        assert len(result) > 0


class TestPhilosopherBuildContext:
    """Tests for Philosopher._build_context (private helper)."""

    def test_build_context_uses_last_6_exchanges(self):
        """Should only use the last 6 exchanges for context."""
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Topic")

        # Add 8 more exchanges (total = 2 + 8 = 10 exchanges)
        for i in range(4):
            session = phil.continue_session(session, f"Round {i}")

        context = phil._build_context(session)

        # Each exchange is formatted as "[role]: content" — count role markers
        role_lines = [line for line in context.split("\n") if line.startswith("[")]
        assert len(role_lines) <= 6

    def test_build_context_returns_string(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Structure")

        result = phil._build_context(session)

        assert isinstance(result, str)

    def test_build_context_contains_role_markers(self):
        c = Collider()
        phil = Philosopher(c)
        session = phil.start_session("Markers")

        context = phil._build_context(session)

        assert "[user]" in context
        assert "[philosopher]" in context
