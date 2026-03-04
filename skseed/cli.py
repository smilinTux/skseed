"""
SKSeed CLI — sovereign logic kernel command line interface.

Commands:
  skseed collide "proposition"     — Run the 6-stage steel man collider
  skseed audit                     — Scan memories for logic/truth misalignment
  skseed philosopher "topic"       — Enter philosopher mode
  skseed alignment status          — Show truth alignment overview
  skseed alignment check "belief"  — Truth-check a single belief
  skseed alignment issues          — List misalignment issues
  skseed alignment resolve ID      — Mark an issue as discussed
  skseed config show               — Show current configuration
  skseed config set KEY VALUE      — Update a configuration value
  skseed install seed.json         — Install a seed framework file
"""

from __future__ import annotations

import json
import sys

import click

from .alignment import AlignmentStore
from .audit import Auditor
from .collider import Collider
from .framework import get_default_framework, install_seed_framework
from .models import (
    AlignmentStatus,
    AuditFrequency,
    Belief,
    BeliefSource,
    PhilosopherMode,
    SeedConfig,
)
from .philosopher import Philosopher


def _make_collider() -> Collider:
    """Create a collider with the default framework."""
    return Collider(framework=get_default_framework())


def _make_store() -> AlignmentStore:
    """Create an alignment store with defaults."""
    return AlignmentStore()


@click.group()
@click.version_option(version="0.1.0", prog_name="skseed")
def main():
    """SKSeed — Sovereign Logic Kernel.

    Aristotelian entelechy engine for truth alignment.
    Based on the Neuresthetics seed framework.
    """
    pass


# ── Collide ────────────────────────────────────────────────


@main.command()
@click.argument("proposition")
@click.option("--context", "-c", default="", help="Domain context for the analysis")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def collide(proposition: str, context: str, json_output: bool):
    """Run a proposition through the 6-stage steel man collider."""
    collider = _make_collider()
    result = collider.collide(proposition, context=context)

    if json_output:
        click.echo(result.model_dump_json(indent=2))
    else:
        click.echo(result.summary())
        if not collider.can_execute:
            click.echo(
                "\nNote: No LLM callback configured. Result contains the "
                "generated prompt — feed it to an LLM for full analysis."
            )


@main.command()
@click.argument("propositions", nargs=-1, required=True)
@click.option("--context", "-c", default="", help="Domain context")
def batch(propositions: tuple[str, ...], context: str):
    """Run multiple propositions and cross-reference invariants."""
    collider = _make_collider()
    results = collider.batch_collide(list(propositions), context=context)
    xref = collider.cross_reference(results)

    click.echo(f"Collided {len(results)} propositions\n")
    for r in results:
        click.echo(f"  [{r.truth_grade.value}] {r.proposition[:60]}")
    click.echo(f"\nCross-reference:")
    click.echo(f"  Universal invariants: {len(xref.get('universal_invariants', {}))}")
    click.echo(f"  Total fragments: {xref.get('total_fragments', 0)}")
    click.echo(f"  Cross-coherence: {xref.get('cross_coherence', 0):.2f}")


# ── Audit ──────────────────────────────────────────────────


@main.command()
@click.option("--source", "-s", default="skmemory", help="Memory source to audit")
@click.option("--domain", "-d", default=None, help="Filter by domain")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
@click.option("--triggered-by", default="cli", help="What triggered this audit")
def audit(source: str, domain: str, json_output: bool, triggered_by: str):
    """Scan memories for logic/truth misalignment."""
    collider = _make_collider()
    store = _make_store()
    auditor = Auditor(collider=collider, alignment_store=store)

    # Try to load memories from skmemory
    memories = _load_memories(source, domain)

    if not memories:
        click.echo("No memories found to audit. Use --source to specify a source.")
        return

    report = auditor.run_audit(
        memories=memories,
        triggered_by=triggered_by,
    )

    if json_output:
        click.echo(report.model_dump_json(indent=2))
    else:
        click.echo(report.summary())


# ── Philosopher ────────────────────────────────────────────


@main.command()
@click.argument("topic")
@click.option(
    "--mode", "-m",
    type=click.Choice(["socratic", "dialectic", "adversarial", "collaborative"]),
    default="dialectic",
    help="Brainstorming mode",
)
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
def philosopher(topic: str, mode: str, json_output: bool):
    """Enter philosopher mode for brainstorming an idea."""
    collider = _make_collider()
    phil = Philosopher(collider=collider)

    philosopher_mode = PhilosopherMode(mode)
    session = phil.start_session(topic, mode=philosopher_mode)

    if json_output:
        click.echo(session.model_dump_json(indent=2))
    else:
        click.echo(phil.session_summary(session))
        if not collider.can_execute:
            click.echo(
                "\nNote: No LLM callback configured. The prompt above "
                "can be fed to any LLM for interactive exploration."
            )


# ── Alignment ──────────────────────────────────────────────


@main.group()
def alignment():
    """Truth alignment tracking and management."""
    pass


@alignment.command("status")
@click.option("--domain", "-d", default=None, help="Filter by domain")
def alignment_status(domain: str):
    """Show truth alignment overview."""
    store = _make_store()

    aligned = store.list_beliefs(status=AlignmentStatus.ALIGNED, domain=domain)
    misaligned = store.list_beliefs(status=AlignmentStatus.MISALIGNED, domain=domain)
    pending = store.list_beliefs(status=AlignmentStatus.PENDING, domain=domain)
    discussed = store.list_beliefs(status=AlignmentStatus.DISCUSSED, domain=domain)

    click.echo("Truth Alignment Status")
    click.echo("=" * 40)
    click.echo(f"  Aligned:    {len(aligned)}")
    click.echo(f"  Misaligned: {len(misaligned)}")
    click.echo(f"  Pending:    {len(pending)}")
    click.echo(f"  Discussed:  {len(discussed)}")
    click.echo()

    # Three-way comparison
    comparison = store.compare_beliefs(domain=domain)
    click.echo(f"  Human beliefs:    {comparison['human_count']}")
    click.echo(f"  Model beliefs:    {comparison['model_count']}")
    click.echo(f"  Collider truths:  {comparison['collider_count']}")

    issues = store.list_issues()
    if issues:
        click.echo(f"\n  Open issues: {len(issues)}")


@alignment.command("check")
@click.argument("belief_text")
@click.option(
    "--source", "-s",
    type=click.Choice(["human", "model"]),
    default="model",
    help="Belief source",
)
@click.option("--domain", "-d", default="general", help="Topic domain")
def alignment_check(belief_text: str, source: str, domain: str):
    """Truth-check a single belief."""
    collider = _make_collider()
    store = _make_store()

    belief = Belief(
        content=belief_text,
        source=BeliefSource(source),
        domain=domain,
    )

    result = collider.collide(belief_text, context=f"truth-check-{domain}")
    record = store.record_alignment(belief, result, triggered_by="cli-check")

    click.echo(f"Belief: {belief_text[:80]}")
    click.echo(f"Source: {source}  |  Domain: {domain}")
    click.echo(f"Coherence: {result.coherence_score:.2f}")
    click.echo(f"Grade: {result.truth_grade.value}")
    click.echo(f"Status: {record.new_status.value}")

    if result.invariants:
        click.echo("\nInvariants:")
        for inv in result.invariants:
            click.echo(f"  + {inv}")


@alignment.command("issues")
@click.option("--status", "-s", default="open", help="Issue status filter")
def alignment_issues(status: str):
    """List misalignment issues pending discussion."""
    store = _make_store()
    issues = store.list_issues(status=status)

    if not issues:
        click.echo(f"No {status} issues found.")
        return

    click.echo(f"Misalignment Issues ({status})")
    click.echo("=" * 50)

    for issue in issues:
        click.echo(f"\n  ID: {issue['belief_id'][:8]}...")
        click.echo(f"  Type: {issue.get('misalignment_type', 'unknown')}")
        click.echo(f"  Domain: {issue.get('domain', 'general')}")
        click.echo(f"  Source: {issue.get('source', 'unknown')}")
        click.echo(f"  Coherence: {issue.get('coherence_score', 0):.2f}")
        click.echo(f"  Belief: {issue['belief_content'][:80]}...")


@alignment.command("resolve")
@click.argument("belief_id")
@click.option("--notes", "-n", required=True, help="Discussion notes")
def alignment_resolve(belief_id: str, notes: str):
    """Mark an issue as discussed."""
    store = _make_store()

    # Find matching issue by prefix
    issues = store.list_issues()
    matching = [i for i in issues if i["belief_id"].startswith(belief_id)]

    if not matching:
        click.echo(f"No open issue found matching: {belief_id}")
        return

    full_id = matching[0]["belief_id"]
    success = store.resolve_issue(full_id, notes)

    if success:
        click.echo(f"Issue {full_id[:8]}... marked as discussed.")
        click.echo(f"Notes: {notes}")
    else:
        click.echo("Failed to resolve issue.")


@alignment.command("ledger")
@click.option("--limit", "-l", default=20, help="Number of entries")
def alignment_ledger(limit: int):
    """Show alignment history."""
    store = _make_store()
    records = store.get_ledger(limit=limit)

    if not records:
        click.echo("No alignment history yet.")
        return

    click.echo("Truth Alignment Ledger")
    click.echo("=" * 50)

    for r in records:
        click.echo(
            f"  [{r.timestamp[:10]}] {r.belief_id[:8]}... "
            f"{r.previous_status.value} -> {r.new_status.value} "
            f"(via {r.triggered_by})"
        )


# ── Config ─────────────────────────────────────────────────


@main.group()
def config():
    """Configuration management."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    store = _make_store()
    cfg = store.load_config()
    click.echo(cfg.model_dump_json(indent=2))


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value."""
    store = _make_store()
    cfg = store.load_config()

    # Type coercion
    field_info = cfg.model_fields.get(key)
    if not field_info:
        click.echo(f"Unknown config key: {key}")
        click.echo(f"Valid keys: {', '.join(cfg.model_fields.keys())}")
        return

    # Convert value based on field type
    if value.lower() in ("true", "false"):
        typed_value = value.lower() == "true"
    elif value.replace(".", "", 1).isdigit():
        typed_value = float(value) if "." in value else int(value)
    else:
        typed_value = value

    try:
        setattr(cfg, key, typed_value)
        store.save_config(cfg)
        click.echo(f"Set {key} = {typed_value}")
    except Exception as e:
        click.echo(f"Error: {e}")


# ── Install ────────────────────────────────────────────────


@main.command()
@click.argument("source_path", type=click.Path(exists=True))
def install(source_path: str):
    """Install a seed framework JSON file."""
    try:
        path = install_seed_framework(source_path)
        click.echo(f"Installed seed framework to: {path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ── Helpers ────────────────────────────────────────────────


def _load_memories(source: str, domain: str | None = None) -> list[dict]:
    """Try to load memories from skmemory.

    Args:
        source: Memory source identifier.
        domain: Optional domain filter.

    Returns:
        List of memory dicts.
    """
    try:
        from skmemory.store import MemoryStore

        ms = MemoryStore()
        memories = ms.list_summaries() if hasattr(ms, "list_summaries") else []
        return [m if isinstance(m, dict) else m.model_dump() for m in memories]
    except ImportError:
        click.echo(
            "skmemory not installed. Install with: pip install skmemory",
            err=True,
        )
        return []
    except Exception as e:
        click.echo(f"Error loading memories: {e}", err=True)
        return []


if __name__ == "__main__":
    main()
