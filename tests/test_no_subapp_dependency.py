"""Gate: importing skseed must not eagerly pull skcapstone into sys.modules.

skseed is a standalone reasoning kernel.  It integrates with skcapstone (shared
sk-alert bus, fleet scheduler) *when that package is present*, but merely
importing skseed -- or any package that depends on it, e.g. the L0 core
``skmemory`` -- must never drag skcapstone in as an import side effect.

This matters beyond skseed itself: ``skseed.__init__`` imports ``skseed.audit``
-> ``skseed.integration``, so an eager ``from skcapstone import sdk`` in that
bridge leaked skcapstone into ``sys.modules`` for every downstream importer.
The fix resolves the skcapstone SDK lazily (``integration._get_sdk``); this test
locks that in.

The proof runs in a CLEAN interpreter subprocess (not the pytest process, which
has already imported plenty) and asserts skcapstone did not enter sys.modules.
skcapstone IS installed in a full dev/prod env, so a green result there means
the coupling is genuinely lazy, not merely that skcapstone is absent.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

# The higher-layer subapp skseed must never import as a side effect of a plain
# import.  skseed bridges to skcapstone only; the wider set is included so any
# future coupling to another subapp is caught too.
SUBAPPS = ("skcapstone", "skchat", "skcomms", "skos", "skharness")

# skseed surface exercised: the bare package import (runs __init__ -> audit ->
# integration) and the integration bridge module itself.
MODULES = (
    "skseed",
    "skseed.integration",
    "skseed.audit",
)


def _clean_import_leaks(modules: tuple[str, ...]) -> list[str]:
    """Import ``modules`` in a fresh interpreter; return any leaked subapps."""
    script = textwrap.dedent(
        f"""
        import sys
        for _m in {modules!r}:
            __import__(_m)
        _subapps = {SUBAPPS!r}
        _leaked = sorted(
            s for s in _subapps
            if any(k == s or k.startswith(s + ".") for k in sys.modules)
        )
        print(",".join(_leaked))
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout.strip()
    return out.split(",") if out else []


def test_bare_skseed_import_pulls_no_subapp():
    """A bare ``import skseed`` (via __init__ -> audit -> integration) leaks none."""
    leaked = _clean_import_leaks(("skseed",))
    assert leaked == [], (
        f"`import skseed` eagerly pulled in subapps: {leaked}. "
        "The skcapstone bridge must resolve lazily (deferred to first use)."
    )


def test_skseed_surface_import_pulls_no_subapp():
    """Importing the integration bridge and audit surface leaks no subapp."""
    leaked = _clean_import_leaks(MODULES)
    assert leaked == [], (
        f"skseed surface import pulled in subapps: {leaked}. "
        "The skcapstone import must be lazy (deferred to first use)."
    )
