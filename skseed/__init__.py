"""
SKSeed — Sovereign Logic Kernel.

Aristotelian entelechy engine for truth alignment.
Based on the Neuresthetics seed framework.

https://github.com/neuresthetics/seed

The seed framework is a recursive axiomatic steel man collider: it
takes any proposition, builds its strongest possible version, collides
it with its strongest inversion, and extracts what survives as
invariant truth.

Core modules:
  - collider: The 6-stage steel man engine
  - alignment: Three-way truth alignment (human/model/collider)
  - audit: Memory logic audit for misalignment detection
  - philosopher: Interactive brainstorming modes
  - framework: Seed JSON loader and prompt generator

Usage:
    from skseed import Collider, Auditor, Philosopher, AlignmentStore

    collider = Collider()
    result = collider.collide("Consciousness is substrate-independent")
    print(result.summary())
"""

__version__ = "0.1.0"

from .alignment import AlignmentStore
from .audit import Auditor
from .collider import Collider
from .framework import SeedFramework, get_default_framework, load_seed_framework
from .models import (
    AlignmentRecord,
    AlignmentStatus,
    AuditReport,
    Belief,
    BeliefSource,
    ConceptCluster,
    MisalignmentType,
    PhilosopherMode,
    PhilosopherSession,
    SeedConfig,
    SteelManResult,
    TruthGrade,
)
from .llm import anthropic_callback, auto_callback, ollama_callback, openai_callback, passthrough_callback
from .philosopher import Philosopher

__all__ = [
    "AlignmentRecord",
    "AlignmentStatus",
    "AlignmentStore",
    "AuditReport",
    "Auditor",
    "Belief",
    "BeliefSource",
    "Collider",
    "ConceptCluster",
    "MisalignmentType",
    "Philosopher",
    "PhilosopherMode",
    "PhilosopherSession",
    "SeedConfig",
    "SeedFramework",
    "SteelManResult",
    "TruthGrade",
    "anthropic_callback",
    "auto_callback",
    "get_default_framework",
    "load_seed_framework",
    "ollama_callback",
    "openai_callback",
    "passthrough_callback",
]
