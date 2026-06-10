"""Dual-mode tests for the skseed ⇄ skcapstone integration adapter.

Verifies the contract from
skcapstone/docs/ADR-optional-integration-backbone.md:
  * standalone (SK_STANDALONE=1 or skcapstone absent) → native fallback, no crash
  * integrated (skcapstone present)                   → routes to sk-alert /
                                                         skscheduler / registry
  * SK_STANDALONE=1 forces standalone even when skcapstone is present

The test sandboxes SKCAPSTONE_HOME to a tmp_path so integrated-mode writes
never pollute the real ~/.skcapstone tree.
"""

from __future__ import annotations

import json
import os

import pytest

# Record real home before any sandbox so the leak-check knows where to look.
_ORIGINAL_SK_HOME = os.environ.get("SKCAPSTONE_HOME")


@pytest.fixture(autouse=True)
def _sandbox_skcapstone_home(tmp_path, monkeypatch):
    """Point SKCAPSTONE_HOME at a throw-away directory for every test."""
    monkeypatch.setenv("SKCAPSTONE_HOME", str(tmp_path))
    try:
        import skcapstone
        monkeypatch.setattr(skcapstone, "AGENT_HOME", str(tmp_path), raising=False)
    except ImportError:
        pass
    yield
    # Leak-check: no fragments should exist in the real home
    real_home = _ORIGINAL_SK_HOME or os.path.expanduser("~/.skcapstone")
    jobs_d = os.path.join(real_home, "config", "jobs.d")
    registry = os.path.join(real_home, "registry")
    for d, prefix in [(jobs_d, "skseed_"), (registry, "skseed")]:
        if os.path.isdir(d):
            leaked = [f for f in os.listdir(d) if f.startswith(prefix)]
            assert not leaked, f"Integration test leaked files in {d}: {leaked}"


def _home(tmp_path):
    """Resolve the sandbox skcapstone home from env."""
    from pathlib import Path
    return Path(os.environ["SKCAPSTONE_HOME"])


# --------------------------------------------------------------------------
# Standalone mode (operator forced)
# --------------------------------------------------------------------------

def test_standalone_env_disables_integration(monkeypatch):
    monkeypatch.setenv("SK_STANDALONE", "1")
    from skseed import integration
    assert integration.is_present() is False
    assert integration.alert("x", {"m": 1}, level="error") is False
    assert integration.ensure_schedule() is False
    assert integration.register_self() is False


# --------------------------------------------------------------------------
# Absent mode (package not importable)
# --------------------------------------------------------------------------

def test_absent_skcapstone_falls_back(monkeypatch):
    monkeypatch.delenv("SK_STANDALONE", raising=False)
    from skseed import integration
    monkeypatch.setattr(integration, "_sdk", None)
    assert integration.is_present() is False
    # alert still "works" (logs) and reports it did not publish
    assert integration.alert("audit_failed", {"message": "boom"}, level="error") is False
    assert integration.ensure_schedule() is False
    assert integration.register_self() is False


# --------------------------------------------------------------------------
# Integrated mode (skcapstone present)
# --------------------------------------------------------------------------

def test_present_alert_publishes_topic(monkeypatch, tmp_path):
    monkeypatch.delenv("SK_STANDALONE", raising=False)
    try:
        from skseed import integration
    except Exception:
        pytest.skip("skcapstone not installed")

    if not integration.is_present():
        pytest.skip("skcapstone not available in this environment")

    assert integration.alert("audit_failed", {"message": "collider error"}, level="error") is True

    # Topic follows <service>.<severity> so `skcapstone alerts` (*.error) sees it;
    # the event name lives in the payload.
    topic_dir = _home(tmp_path) / "pubsub" / "topics" / "skseed.error"
    assert topic_dir.is_dir(), f"Expected topic dir at {topic_dir}"
    msgs = list(topic_dir.glob("msg-*.json"))
    assert msgs, "No messages written to topic dir"
    data = json.loads(msgs[-1].read_text())
    assert data["topic"] == "skseed.error"
    assert data["payload"]["event"] == "audit_failed"
    assert data["payload"]["message"] == "collider error"


def test_present_ensure_schedule_writes_dropin(monkeypatch, tmp_path):
    monkeypatch.delenv("SK_STANDALONE", raising=False)
    try:
        from skseed import integration
    except Exception:
        pytest.skip("skcapstone not installed")

    if not integration.is_present():
        pytest.skip("skcapstone not available in this environment")

    assert integration.ensure_schedule(interval_hours=24) is True

    fragment = _home(tmp_path) / "config" / "jobs.d" / "skseed_audit.yaml"
    assert fragment.exists(), f"Expected drop-in at {fragment}"

    from skcapstone.scheduler_jobs import load_jobs_with_dropins

    jobs = {j.name: j for j in load_jobs_with_dropins(_home(tmp_path) / "config" / "jobs.yaml")}
    assert "skseed_audit" in jobs
    assert jobs["skseed_audit"].command == "skseed audit --source skmemory"
    assert jobs["skseed_audit"].every_seconds == 24 * 3600

    # idempotent cleanup
    assert integration.unregister_schedule() is True
    assert not fragment.exists()


def test_present_register_self_writes_registry(monkeypatch, tmp_path):
    monkeypatch.delenv("SK_STANDALONE", raising=False)
    try:
        from skseed import integration
    except Exception:
        pytest.skip("skcapstone not installed")

    if not integration.is_present():
        pytest.skip("skcapstone not available in this environment")

    assert integration.register_self(pid_file="/tmp/skseed.pid") is True
    entry = json.loads((_home(tmp_path) / "registry" / "skseed.json").read_text())
    assert entry["name"] == "skseed"
    assert entry["pid_file"] == "/tmp/skseed.pid"


def test_alert_misalignment_warn(monkeypatch, tmp_path):
    """Warn-level misalignment alerts should be published."""
    monkeypatch.delenv("SK_STANDALONE", raising=False)
    try:
        from skseed import integration
    except Exception:
        pytest.skip("skcapstone not installed")

    if not integration.is_present():
        pytest.skip("skcapstone not available in this environment")

    result = integration.alert(
        "audit_misalignment_found",
        {"misaligned_count": 3, "truth_issues": 2, "moral_issues": 1, "triggered_by": "test"},
        level="warn",
    )
    assert result is True
    topic_dir = _home(tmp_path) / "pubsub" / "topics" / "skseed.warn"
    msgs = list(topic_dir.glob("msg-*.json"))
    assert msgs
    data = json.loads(msgs[-1].read_text())
    assert data["payload"]["event"] == "audit_misalignment_found"
    assert data["payload"]["misaligned_count"] == 3
