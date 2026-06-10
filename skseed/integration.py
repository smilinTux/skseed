"""skseed ⇄ skcapstone — optional integration adapter.

skseed runs fully standalone.  When the ``skcapstone`` package is installed
(and the operator has not forced standalone mode with ``SK_STANDALONE=1``),
this adapter routes alerts through skcapstone's shared **sk-alert** bus and
registers skseed's belief-audit sweep with the fleet **skscheduler**, so the
whole sk* mesh sees one alert stream and one scheduler.  When skcapstone is
absent, every call degrades to skseed's native behaviour (structured logging;
skseed is a pure kernel / library with no daemon, so the native scheduling
fallback is a no-op / caller responsibility).

This is the *default-on-by-presence* pattern from
``skcapstone/docs/ADR-optional-integration-backbone.md`` — nothing here is a
hard dependency; ``skcapstone`` lives in the optional ``[skcapstone]`` extra.

Public API:
    is_present()                      -> bool
    alert(event, payload, level)      -> bool   (True iff sent via sk-alert)
    ensure_schedule(interval_hours)   -> bool   (True iff registered with skscheduler)
    unregister_schedule()             -> bool
    register_self(pid_file)           -> bool

Topic convention: ``skseed.<severity>`` (severity ∈ info|warn|error|critical).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("skseed.integration")

#: This service's name — used as the alert topic prefix and registry key.
SERVICE = "skseed"

#: Fleet-scheduler job name for the periodic belief-audit sweep.
SWEEP_JOB = "skseed_audit"

# Optional import — never a hard dependency.
try:
    from skcapstone import sdk as _sdk
except Exception:  # ImportError, or a broken partial install
    _sdk = None  # type: ignore[assignment]

#: severity → logging method name (native fallback)
_LOG_METHOD = {
    "info": "info",
    "warn": "warning",
    "error": "error",
    "critical": "critical",
}
_NOTIFY_LEVELS = frozenset({"warn", "error", "critical"})


def is_present() -> bool:
    """Return whether skcapstone integration should be used from this process.

    ``True`` only when the package imported, the operator has not set
    ``SK_STANDALONE``, and the SDK reports itself available.  Any failure is
    treated as "not present" so callers transparently use their native path.
    """
    if os.environ.get("SK_STANDALONE"):
        return False
    if _sdk is None:
        return False
    try:
        return bool(_sdk.is_available())
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("skcapstone present-check failed: %s", exc)
        return False


def alert(event: str, payload: dict[str, Any], level: str = "info") -> bool:
    """Emit an alert: via skcapstone sk-alert when present, else local log.

    The published topic follows the ecosystem convention ``skseed.<severity>``
    (so ``skcapstone alerts`` — which subscribes to ``*.error`` / ``*.critical``
    / ``*.warn`` — surfaces it). The semantic *event* name is carried in the
    payload's ``event`` field rather than the topic, so routing stays
    severity-based while detail is preserved.

    Args:
        event: Semantic event name (e.g. ``"audit_failed"``). Stored in the
            payload as ``event``.
        payload: JSON-serialisable event body.
        level: ``info | warn | error | critical``.

    Returns:
        ``True`` if published to the shared bus, ``False`` if it fell back to
        local logging (which always also happens at the matching level).
    """
    body = {"event": event, **dict(payload)}
    if is_present():
        try:
            return bool(
                _sdk.alert(
                    f"{SERVICE}.{level}",
                    body,
                    level=level,
                    notify=level in _NOTIFY_LEVELS,
                )
            )
        except Exception as exc:
            logger.warning("sk-alert publish failed, logging locally: %s", exc)

    # native fallback — structured log at the matching level
    method = getattr(logger, _LOG_METHOD.get(level, "info"))
    method("[%s.%s] %s", SERVICE, level, body)
    return False


def ensure_schedule(interval_hours: float = 24.0) -> bool:
    """Register the belief-audit sweep with the fleet scheduler, if present.

    Writes a ``jobs.d/skseed_audit.yaml`` drop-in that runs ``skseed audit``
    every *interval_hours*, so the skcapstone daemon owns the cadence (with
    central retry/notify).  Idempotent — safe to call on every startup.

    skseed is a pure kernel library (no daemon) so when skcapstone is absent
    there is no native scheduler to fall back to — the caller is responsible
    for scheduling via cron / systemd / the calling application's own loop.

    Args:
        interval_hours: Audit cadence in hours (default 24h — once a day).

    Returns:
        ``True`` if registered with skscheduler; ``False`` when skcapstone is
        absent (caller must handle scheduling natively).
    """
    if not is_present():
        return False
    try:
        _sdk.register_job(
            {
                "name": SWEEP_JOB,
                "type": "shell",
                "command": "skseed audit --source skmemory",
                "every": f"{int(interval_hours * 3600)}s",
                "timeout": 1800,
                "notify": "on_failure",
                "notify_level": "error",
            }
        )
        logger.info(
            "Registered '%s' with skcapstone scheduler (every %.1fh).",
            SWEEP_JOB,
            interval_hours,
        )
        return True
    except Exception as exc:
        logger.warning("ensure_schedule failed (using native): %s", exc)
        return False


def unregister_schedule() -> bool:
    """Remove the belief-audit drop-in from the fleet scheduler."""
    if _sdk is None:
        return False
    try:
        return bool(_sdk.unregister_job(SWEEP_JOB))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("unregister_schedule failed: %s", exc)
        return False


def register_self(pid_file: Optional[str] = None) -> bool:
    """Advertise skseed to skcapstone's discovery registry, if present.

    skseed is a pure kernel library (no daemon / pid file) — the pid_file
    argument is accepted for API symmetry but defaults to ``None`` (no
    liveness signal beyond the registry entry itself).

    Args:
        pid_file: Optional pid-file path used as a liveness signal.

    Returns:
        ``True`` if registered, ``False`` otherwise.
    """
    if not is_present():
        return False
    try:
        _sdk.register_service(
            SERVICE,
            pid_file=pid_file or str(Path("~/.skseed/daemon.pid").expanduser()),
        )
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("register_self failed: %s", exc)
        return False
