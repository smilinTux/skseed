/**
 * SKSeed — OpenClaw Plugin
 *
 * Registers agent tools that wrap the skseed CLI so OpenClaw agents
 * can run steel man collisions, truth audits, and philosopher sessions
 * as first-class tools.
 *
 * Requires: skseed CLI on PATH (typically via ~/.skenv/bin/skseed)
 */

import { execSync } from "node:child_process";
import type { OpenClawPluginApi, AnyAgentTool } from "openclaw/plugin-sdk";
import { emptyPluginConfigSchema } from "openclaw/plugin-sdk";

const SKSEED_BIN = process.env.SKSEED_BIN || "skseed";
const EXEC_TIMEOUT = 120_000;
const IS_WIN = process.platform === "win32";

function skenvPath(): string {
  if (IS_WIN) {
    const local = process.env.LOCALAPPDATA || "";
    return `${local}\\skenv\\Scripts`;
  }
  const home = process.env.HOME || "";
  return `${home}/.local/bin:${home}/.skenv/bin`;
}

function runCli(args: string): { ok: boolean; output: string } {
  const sep = IS_WIN ? ";" : ":";
  try {
    const raw = execSync(`${SKSEED_BIN} ${args}`, {
      encoding: "utf-8",
      timeout: EXEC_TIMEOUT,
      env: {
        ...process.env,
        PATH: `${skenvPath()}${sep}${process.env.PATH}`,
      },
    }).trim();
    return { ok: true, output: raw };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return { ok: false, output: msg };
  }
}

function textResult(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

function escapeShellArg(s: string): string {
  return `'${s.replace(/'/g, "'\\''")}'`;
}

// -- Tool definitions --------------------------------------------------------

function createCollideTool() {
  return {
    name: "skseed_collide",
    label: "SKSeed Steel Man Collide",
    description:
      "Run a proposition through the 6-stage steel man collider. Builds the strongest version of the claim, collides it with its strongest inversion, and extracts invariant truth.",
    parameters: {
      type: "object",
      required: ["proposition"],
      properties: {
        proposition: { type: "string", description: "The proposition to collide." },
        depth: { type: "number", description: "Recursion depth (default: 3, max: 7)." },
      },
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const prop = String(params.proposition ?? "");
      const depth = params.depth ? ` --depth ${params.depth}` : "";
      const result = runCli(`collide ${escapeShellArg(prop)}${depth}`);
      return textResult(result.output);
    },
  };
}

function createAuditTool() {
  return {
    name: "skseed_audit",
    label: "SKSeed Memory Audit",
    description:
      "Scan agent memories for logic and truth misalignment. Checks stored beliefs against the collider's invariant truths.",
    parameters: {
      type: "object",
      properties: {
        limit: { type: "number", description: "Max memories to audit (default: 50)." },
      },
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const limit = params.limit ? ` --limit ${params.limit}` : "";
      const result = runCli(`audit${limit}`);
      return textResult(result.output);
    },
  };
}

function createBatchTool() {
  return {
    name: "skseed_batch",
    label: "SKSeed Batch Collide",
    description:
      "Run multiple propositions through the collider and cross-reference invariants to find convergent truths.",
    parameters: {
      type: "object",
      required: ["propositions"],
      properties: {
        propositions: {
          type: "string",
          description: "Semicolon-separated list of propositions to collide.",
        },
      },
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const props = String(params.propositions ?? "");
      const result = runCli(`batch ${escapeShellArg(props)}`);
      return textResult(result.output);
    },
  };
}

function createAlignmentTool() {
  return {
    name: "skseed_alignment",
    label: "SKSeed Truth Alignment",
    description:
      "Check or update truth alignment between human beliefs, model beliefs, and collider invariants.",
    parameters: {
      type: "object",
      properties: {
        action: {
          type: "string",
          enum: ["status", "list", "check"],
          description: "Action to perform (default: status).",
        },
      },
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const action = String(params.action ?? "status");
      const result = runCli(`alignment ${action}`);
      return textResult(result.output);
    },
  };
}

function createPhilosopherTool() {
  return {
    name: "skseed_philosopher",
    label: "SKSeed Philosopher Mode",
    description:
      "Enter philosopher mode to brainstorm and stress-test an idea through dialectical reasoning. Returns a structured analysis.",
    parameters: {
      type: "object",
      required: ["idea"],
      properties: {
        idea: { type: "string", description: "The idea or question to explore." },
        mode: {
          type: "string",
          enum: ["socratic", "dialectic", "phenomenological", "analytic"],
          description: "Philosophy mode (default: dialectic).",
        },
      },
    },
    async execute(_id: string, params: Record<string, unknown>) {
      const idea = String(params.idea ?? "");
      const mode = params.mode ? ` --mode ${params.mode}` : "";
      const result = runCli(`philosopher ${escapeShellArg(idea)}${mode}`);
      return textResult(result.output);
    },
  };
}

// -- Plugin registration -----------------------------------------------------

const skseedPlugin = {
  id: "skseed",
  name: "SKSeed",
  description:
    "Sovereign Logic Kernel — steel man collider, truth alignment, memory audit, and philosopher mode.",
  configSchema: emptyPluginConfigSchema(),

  register(api: OpenClawPluginApi) {
    const tools = [
      createCollideTool(),
      createAuditTool(),
      createBatchTool(),
      createAlignmentTool(),
      createPhilosopherTool(),
    ];

    for (const tool of tools) {
      api.registerTool(tool as unknown as AnyAgentTool, {
        names: [tool.name],
        optional: true,
      });
    }

    api.registerCommand({
      name: "skseed",
      description: "Run skseed CLI commands. Usage: /skseed <subcommand> [args]",
      acceptsArgs: true,
      handler: async (ctx) => {
        const args = ctx.args?.trim() ?? "collide --help";
        const result = runCli(args);
        return { text: result.output };
      },
    });

    api.logger.info?.(`SKSeed plugin registered (5 tools + /skseed command)`);
  },
};

export default skseedPlugin;
