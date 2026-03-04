# SKSeed

![PyPI](https://img.shields.io/pypi/v/skseed) ![License](https://img.shields.io/badge/license-AGPL--3.0-blue) ![Python](https://img.shields.io/badge/python-3.10%2B-blue)

Sovereign Logic Kernel — an Aristotelian entelechy engine for truth alignment. Run propositions through a 6-stage steel man collider, explore ideas with structured philosopher modes, and audit AI memories for logic/truth misalignment.

## Features

- **6-stage steel man collider** — builds the strongest version of a proposition and its strongest counter-argument, smashes them together, and extracts invariant truth with a coherence score and truth grade
- **Batch collide** — cross-reference invariants across multiple propositions
- **Philosopher modes** — `socratic` (challenge assumptions), `dialectic` (thesis/antithesis/synthesis), `adversarial` (maximum counter-arguments), `collaborative` (steel-man only)
- **Belief auditing** — scan memory stores for logic/truth misalignment, cluster by domain, flag contradictions
- **Alignment ledger** — track human beliefs, model beliefs, and collider results across sessions; mark issues as discussed
- **MCP server** — expose all tools to AI agents via the Model Context Protocol
- **LLM-agnostic** — works standalone (generates prompts) or wired to any LLM callback

## Install

```bash
pip install skseed

# Optional: skmemory integration for belief auditing
pip install "skseed[memory]"
```

## Quick Usage

```bash
# Run a proposition through the steel man collider
skseed collide "Consciousness is substrate-independent"

# Collide with domain context
skseed collide "Markets self-regulate" --context economics

# Batch collide multiple propositions
skseed batch "Free will exists" "Determinism is true" "Compatibilism resolves both"

# Enter philosopher mode
skseed philosopher "What is the nature of identity?" --mode dialectic
skseed philosopher "Is privacy a right?" --mode adversarial

# Audit memories for misalignment
skseed audit --source skmemory --domain ethics

# Truth-check a single belief
skseed alignment check "AI systems can be conscious"
skseed alignment check "Privacy is a fundamental right" --source human

# Show alignment overview
skseed alignment status
skseed alignment issues

# Mark an issue as resolved after discussion
skseed alignment resolve <id> --notes "Agreed: compatibilism holds"
```

### Python API

```python
from skseed.collider import Collider
from skseed.framework import get_default_framework
from skseed.philosopher import Philosopher
from skseed.models import PhilosopherMode

# Run the steel man collider
collider = Collider(framework=get_default_framework())
result = collider.collide("All knowledge is constructed", context="epistemology")

print(result.coherence_score)   # 0.0–1.0
print(result.truth_grade.value) # A / B / C / D / F
print(result.invariants)        # List[str] — what survives the collision

# Philosopher mode
phil = Philosopher(collider=collider)
session = phil.start_session("What is time?", mode=PhilosopherMode.SOCRATIC)
print(phil.session_summary(session))
```

## License

AGPL-3.0 — see [LICENSE](LICENSE).
