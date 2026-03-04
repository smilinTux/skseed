"""Tests for SKSeed hooks."""

import pytest

from skseed.hooks import on_memory_check, on_boot_audit, _looks_like_belief


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    """Ensure auto_callback returns None so tests don't hit real LLMs."""
    monkeypatch.setattr("skseed.skill.auto_callback", lambda: None)


class TestLooksLikeBelief:
    """Tests for belief detection in content."""

    def test_belief_statement(self):
        assert _looks_like_belief("I believe that truth is paramount") is True

    def test_should_statement(self):
        assert _looks_like_belief("We should always verify trust") is True

    def test_factual_assertion(self):
        assert _looks_like_belief("The truth is that sovereignty matters") is True

    def test_plain_text(self):
        assert _looks_like_belief("The function returns a list") is False

    def test_empty(self):
        assert _looks_like_belief("") is False


class TestOnMemoryCheck:
    """Tests for the on_memory_check hook."""

    def test_skips_non_belief(self):
        result = on_memory_check(memory_id="m1", content="Just some data")
        assert result["checked"] is False
        assert "does not appear" in result["reason"]

    def test_skips_empty_content(self):
        result = on_memory_check(memory_id="m1", content="")
        assert result["checked"] is False

    def test_checks_belief_content(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        result = on_memory_check(
            memory_id="m1",
            content="I believe that consciousness is substrate-independent",
        )
        # Should attempt the check (may succeed or fail gracefully)
        assert "memory_id" in result
        assert result["memory_id"] == "m1"


class TestOnBootAudit:
    """Tests for the on_boot_audit hook."""

    def test_boot_audit_runs(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        result = on_boot_audit()
        # Either runs successfully or reports why it didn't
        assert "ran" in result

    def test_boot_audit_disabled(self, tmp_path, monkeypatch):
        """Test that boot audit respects disabled config."""
        from skseed.alignment import AlignmentStore
        from skseed.models import SeedConfig

        align_dir = str(tmp_path / ".skseed" / "alignment")
        store = AlignmentStore(base_dir=align_dir)
        store.save_config(SeedConfig(audit_on_boot=False))

        # AlignmentStore() default arg is captured at class def time,
        # so we need to make the no-arg constructor use our temp dir.
        _orig_init = AlignmentStore.__init__

        def _patched_init(self, base_dir=align_dir):
            _orig_init(self, base_dir)

        monkeypatch.setattr(AlignmentStore, "__init__", _patched_init)

        result = on_boot_audit()
        assert result["ran"] is False
        assert "disabled" in result["reason"].lower()
