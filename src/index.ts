/**
 * @smilintux/skseed — Sovereign Logic Kernel
 *
 * Neuresthetics Seed Framework: Recursive Axiomatic Steel Man Collider.
 * Exports the seed.json schema and TypeScript types matching the Python skseed package.
 *
 * Python package: pip install skseed
 * MCP tools: skseed_collide, skseed_audit, skseed_philosopher, skseed_truth_check, skseed_alignment
 */

import * as _seedJson from "../skseed/data/seed.json";

// ── Raw seed framework data ──────────────────────────────────────────────────

export const seedFramework = _seedJson as SeedFramework;

// ── TypeScript types ─────────────────────────────────────────────────────────

export type TruthGrade =
  | "INVARIANT"
  | "STRONG"
  | "PARTIAL"
  | "WEAK"
  | "COLLAPSED"
  | "UNGRADED";

export type PhilosopherMode =
  | "socratic"
  | "dialectic"
  | "adversarial"
  | "collaborative";

export type BeliefSource = "human" | "model" | "collider";

export interface SteelManResult {
  /** The input proposition */
  proposition: string;
  /** Strongest version of the proposition */
  steel_manned: string;
  /** Strongest counter-argument */
  counter: string;
  /** What survives collision as invariant truth */
  invariant: string;
  /** Coherence score 0.0–1.0 */
  coherence_score: number;
  /** Truth grade */
  truth_grade: TruthGrade;
  /** Reasoning trace from each stage */
  stages: string[];
}

export interface Belief {
  id: string;
  content: string;
  domain: string;
  source: BeliefSource;
  created_at: string;
  tags: string[];
  collider_result?: SteelManResult;
}

export interface AlignmentIssue {
  id: string;
  domain: string;
  description: string;
  human_belief?: string;
  model_belief?: string;
  collider_verdict?: string;
  is_moral: boolean;
  opened_at: string;
  resolved_at?: string;
}

export interface AlignmentStatus {
  total_beliefs: number;
  human_beliefs: number;
  model_beliefs: number;
  collider_truths: number;
  open_issues: number;
  coherence_trend: number;
  last_audit: string | null;
}

// ── Seed Framework schema types ───────────────────────────────────────────────

export interface SeedDefinition {
  term: string;
  details: string;
}

export interface SeedStage {
  stage: string;
  description: string;
  key_gates: string[];
  recursive_mechanism: string;
}

export interface SeedPrinciple {
  principle: string;
  details: string;
}

export interface SeedFrameworkMeta {
  id: string;
  function: string;
  source: string;
  version: string;
  automatic_self_feed: string;
  initial_run: string;
  definitions: SeedDefinition[];
  axioms: string[];
  principles: SeedPrinciple[];
  stages: SeedStage[];
}

export interface SeedFramework {
  framework: SeedFrameworkMeta;
}

// ── Utilities ────────────────────────────────────────────────────────────────

/**
 * Returns the Neuresthetics Seed Framework JSON document.
 * This is the declarative AST used by the Python skseed collider.
 */
export function getSeedFramework(): SeedFramework {
  return seedFramework;
}

/**
 * Returns all stage definitions from the seed framework.
 */
export function getSeedStages(): SeedStage[] {
  return seedFramework.framework.stages;
}

/**
 * Returns the axioms from the seed framework.
 */
export function getSeedAxioms(): string[] {
  return seedFramework.framework.axioms;
}

/**
 * Returns all term definitions from the seed framework.
 */
export function getSeedDefinitions(): SeedDefinition[] {
  return seedFramework.framework.definitions;
}
