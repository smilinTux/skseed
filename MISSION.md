# Mission

skseed exists to test an agent's beliefs against the operator's truth, on the operator's own box, with a framework that can be read and changed.

It is an Aristotelian entelechy engine: it takes a claim, builds its strongest possible version (steel-man), collides it with its strongest counter-argument (inversion), and extracts the invariants, what is irreducibly true across the collision. The same 6-stage collider powers belief auditing, identity verification, memory truth-scoring, and four structured philosopher modes.

## Scope

- A truth-alignment kernel: proposition collision, batch cross-referencing, an alignment ledger, and memory audits for the contradictions that corrupt long-term reasoning.
- LLM-agnostic by design: the kernel generates prompts and accepts any callback `(prompt: str) -> str`; with no model wired in it emits the prompt, with a callback it runs end-to-end.
- Built on the open Neuresthetics Seed framework.

Within the SKWorld ecosystem, skseed is the truth-alignment kernel: the layer that keeps an agent's reasoning coherent and its memory free of contradiction.

## Non-goals

- skseed does not host or bundle a model; inference is always the caller's choice.
- It is not a memory store; it audits memory (via skmemory) rather than holding it.
- It does not decide truth for you; it structures the collision so invariants can survive it.
