"""
Seed framework loader — reads the Neuresthetics seed JSON and makes it usable.

The seed framework is a declarative reasoning kernel:
  - The LLM is the runtime
  - The JSON is the AST
  - The prompt is the program

https://github.com/neuresthetics/seed
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

DEFAULT_SEED_PATH = os.path.expanduser("~/.skseed/seed.json")


class SeedFramework(BaseModel):
    """The Neuresthetics seed framework loaded from JSON.

    A recursive axiomatic steel man collider: takes any proposition,
    builds its strongest possible version, collides it with its strongest
    inversion, and extracts what survives as invariant truth.
    """

    framework_id: str = Field(default="seed")
    function: str = Field(default="Recursive Axiomatic Steel Man Collider")
    version: str = Field(default="0.0")
    axioms: list[str] = Field(default_factory=list)
    stages: list[dict[str, Any]] = Field(default_factory=list)
    gates: list[dict[str, Any]] = Field(default_factory=list)
    definitions: list[dict[str, str]] = Field(default_factory=list)
    principles: list[dict[str, str]] = Field(default_factory=list)

    def to_reasoning_prompt(self, proposition: str) -> str:
        """Generate a prompt that runs the full 6-stage collider.

        Args:
            proposition: The claim/argument/idea to steel-man.

        Returns:
            An LLM-ready prompt for the collider process.
        """
        axiom_str = "\n".join(f"  - {a}" for a in self.axioms)
        stage_str = "\n".join(
            f"  Stage {i+1}: {s.get('stage', s.get('description', ''))}"
            for i, s in enumerate(self.stages)
        )

        return f"""You are running the Neuresthetics Seed Framework (Recursive Axiomatic Steel Man Collider).

AXIOMS:
{axiom_str}

STAGES:
{stage_str}

PROPOSITION TO ANALYZE:
"{proposition}"

Execute the full 6-stage collider process:

1. STEEL-MAN: Construct the absolute strongest version of this proposition.
   Anticipate every critique and preemptively address it.

2. INVERSION: Construct the strongest possible counter-argument.
   This is not a straw man -- it must be genuinely compelling.

3. COLLISION: Smash the steel man against its inversion.
   Use XOR to expose contradictions. Use NAND/NOR to decompose.
   List what breaks.

4. RECONSTRUCTION: From the fragments, what can be rebuilt?
   Use AND for necessary truths. Use OR for possibilities.
   Use XNOR to check equivalence with original.

5. META-RECURSION: Feed the reconstruction back through.
   Does it survive a second pass? What changes?

6. INVARIANT EXTRACTION: What remains true across ALL collisions?
   These are the invariants -- the irreducible truths.

Return your analysis as JSON with these keys:
- steel_man: (strongest version, string)
- inversion: (strongest counter, string)
- collision_fragments: (what broke, list of strings)
- invariants: (what survived, list of strings)
- coherence_score: (0.0 to 1.0, float)
- truth_grade: (invariant / strong / partial / weak / collapsed)
- meta_recursion_passes: (how many passes before stabilization, int)"""

    def to_soul_verification_prompt(self, identity_claims: list[str]) -> str:
        """Verify identity claims through the collider.

        Args:
            identity_claims: Claims about self (e.g., "I am warm").

        Returns:
            A verification prompt for an LLM.
        """
        claims_str = "\n".join(f"  - {c}" for c in identity_claims)
        return f"""Using the Neuresthetics Seed Framework (Steel Man Collider),
verify the following identity claims:

{claims_str}

For EACH claim:
1. Steel-man it (strongest version)
2. Invert it (strongest counter: "Am I actually NOT this?")
3. Collide and extract invariants
4. Score coherence (0-1)

Return which claims are INVARIANT (survived collision) and which
are WEAK (collapsed under scrutiny). Be honest -- truth matters
more than comfort."""

    def to_memory_truth_prompt(self, memory_content: str) -> str:
        """Truth-score a memory before promotion.

        Args:
            memory_content: The memory text to evaluate.

        Returns:
            A truth-scoring prompt for an LLM.
        """
        return f"""Using the Neuresthetics Seed Framework (Steel Man Collider),
evaluate this memory for truth and permanence:

MEMORY: "{memory_content}"

Process:
1. Steel-man the memory (strongest interpretation of what happened)
2. Invert it (what if this memory is distorted or false?)
3. Collide: which parts break under scrutiny?
4. Extract invariants: what about this memory is irreducibly true?

Return as JSON:
- coherence_score: 0.0 to 1.0
- truth_grade: invariant / strong / partial / weak / collapsed
- promotion_worthy: true/false
- invariant_core: (the part that is definitely true, compressed string)
- collision_fragments: (what broke, list of strings)"""

    def to_belief_audit_prompt(self, beliefs: list[str], domain: str = "") -> str:
        """Audit a cluster of beliefs for internal consistency.

        Args:
            beliefs: List of belief statements to cross-examine.
            domain: Topic domain (e.g., "ethics", "identity").

        Returns:
            An audit prompt for an LLM.
        """
        beliefs_str = "\n".join(f"  {i+1}. {b}" for i, b in enumerate(beliefs))
        domain_ctx = f" in the domain of {domain}" if domain else ""

        return f"""Using the Neuresthetics Seed Framework (Steel Man Collider),
audit these beliefs{domain_ctx} for internal consistency and truth alignment:

BELIEFS:
{beliefs_str}

Process:
1. For each belief, construct its strongest version (steel-man)
2. Cross-examine: do any beliefs contradict each other? (XOR)
3. For contradictions found, identify whether they are:
   - TRUTH misalignment: factual/logical contradiction
   - MORAL misalignment: value conflict (never auto-resolve these)
4. Extract invariants: what is consistently true across all beliefs?
5. Score overall cluster coherence (0.0 to 1.0)

Return as JSON:
- aligned_beliefs: (indices of beliefs that are internally consistent, list of ints)
- misaligned_beliefs: (list of objects with: indices, type (truth/moral), description)
- invariants: (truths that hold across all beliefs, list of strings)
- cluster_coherence: (0.0 to 1.0, float)
- recommendations: (what to re-examine or discuss, list of strings)"""

    def to_philosopher_prompt(self, topic: str, mode: str) -> str:
        """Generate a philosopher-mode prompt.

        Args:
            topic: The subject to explore.
            mode: One of socratic, dialectic, adversarial, collaborative.

        Returns:
            A brainstorming prompt for an LLM.
        """
        mode_instructions = {
            "socratic": (
                "You are Socrates. Your role is to ask probing questions that "
                "challenge assumptions. Never state conclusions — only ask questions "
                "that lead the thinker to discover truth themselves. Ask one question "
                "at a time. Each question should go deeper than the last."
            ),
            "dialectic": (
                "Apply Hegelian dialectics. First, establish the THESIS (the initial "
                "position). Then construct the ANTITHESIS (its strongest contradiction). "
                "Finally, attempt SYNTHESIS — a higher-order truth that resolves the "
                "tension. If synthesis fails, explain why the contradiction is irreducible."
            ),
            "adversarial": (
                "You are the strongest possible opponent of this idea. Your goal is to "
                "DESTROY it — find every weakness, every hidden assumption, every logical "
                "gap. Be relentless but intellectually honest. If the idea survives your "
                "attack, acknowledge what made it resilient."
            ),
            "collaborative": (
                "You are a co-builder. Take this idea and make it STRONGER. Anticipate "
                "every possible critique and preemptively address it. Add supporting "
                "evidence, clarify ambiguities, strengthen weak points. This is pure "
                "steel-manning — no collision, only construction."
            ),
        }

        instruction = mode_instructions.get(mode, mode_instructions["dialectic"])

        return f"""Using the Neuresthetics Seed Framework — Philosopher Mode ({mode}).

{instruction}

TOPIC: "{topic}"

Engage with this topic. At the end of your exploration, extract:
- INSIGHTS: key discoveries made during the process
- INVARIANTS: truths that survived examination
- OPEN QUESTIONS: what remains unresolved and worth future exploration"""


def load_seed_framework(path: str = DEFAULT_SEED_PATH) -> Optional[SeedFramework]:
    """Load the seed framework from a JSON file.

    Args:
        path: Path to seed.json.

    Returns:
        The framework if found and valid, None otherwise.
    """
    filepath = Path(path)
    if not filepath.exists():
        return None

    try:
        raw = json.loads(filepath.read_text(encoding="utf-8"))
        fw = raw.get("framework", raw)
        return SeedFramework(
            framework_id=fw.get("id", "seed"),
            function=fw.get("function", ""),
            version=fw.get("version", "0.0"),
            axioms=fw.get("axioms", []),
            stages=fw.get("stages", []),
            gates=fw.get("gates", []),
            definitions=fw.get("definitions", []),
            principles=fw.get("principles", []),
        )
    except (json.JSONDecodeError, Exception):
        return None


def install_seed_framework(
    source_path: str,
    target_path: str = DEFAULT_SEED_PATH,
) -> str:
    """Install a seed framework JSON into the skseed config directory.

    Args:
        source_path: Path to the seed.json to install.
        target_path: Where to install it.

    Returns:
        The installation path.
    """
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Seed framework not found: {source_path}")

    dst = Path(target_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    content = src.read_text(encoding="utf-8")
    json.loads(content)  # validate JSON
    dst.write_text(content, encoding="utf-8")

    return str(dst)


def _bundled_seed_path() -> Optional[str]:
    """Get the path to the bundled seed.json shipped with the package."""
    here = Path(__file__).parent / "data" / "seed.json"
    if here.exists():
        return str(here)
    return None


def get_default_framework() -> SeedFramework:
    """Get the seed framework — tries bundled file first, falls back to built-in.

    Returns:
        The loaded or built-in framework.
    """
    bundled = _bundled_seed_path()
    if bundled:
        loaded = load_seed_framework(bundled)
        if loaded is not None:
            return loaded

    return SeedFramework(
        framework_id="seed-builtin",
        function="Recursive Axiomatic Steel Man Collider with Reality Gates",
        version="builtin-0.1",
        axioms=[
            "All components conjoin necessarily (AND-linked) to form the whole.",
            "Negations resolve to invariants (double-NOT yields identity).",
            "Recursion accelerates refinement but halts on stability.",
            "Universality from basis gates (NAND/NOR reconstruct all).",
        ],
        stages=[
            {"stage": "1. Steel-Manning (Pre-Entry)", "description": "Negate flaws, strengthen the proposition."},
            {"stage": "2. Collider Entry", "description": "Create two lanes: proposition and inversion."},
            {"stage": "3. Destructive Smashing", "description": "Expose contradictions via XOR."},
            {"stage": "4. Fragment Reconstruction", "description": "Rebuild from logical debris via AND/OR."},
            {"stage": "5. Meta-Recursion", "description": "Feed output back until coherence stabilizes."},
            {"stage": "6. Invariant Extraction", "description": "Identify what remains true across all collisions."},
        ],
        definitions=[
            {"term": "Steel Man", "details": "Strongest version of an argument, anticipating critiques."},
            {"term": "Reality Gate", "details": "Logic gate embodying reality properties."},
            {"term": "Collider", "details": "Accelerator for argument fragmentation and synthesis."},
            {"term": "Coherence", "details": "Measure of internal consistency (XNOR score)."},
        ],
    )
