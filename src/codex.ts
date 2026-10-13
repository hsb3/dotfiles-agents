// Codex (codex-cli 0.162.1) as an agent under test: argv, per-run isolation,
// skill/agent/plugin injection under CODEX_HOME, and the item-event fold.
import { cpSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Candidate } from "./candidate.ts";
import { emptyRecord, jsonLines, num, type Adapter, type InjectContext, type Injection, type TrialRecord } from "./harnesses.ts";
import { runProcess } from "./subprocess.ts";

const MARKETPLACE = "agent-harness";
const INSTALL_TIMEOUT_SEC = 60;

/** Runs one install step; returns its error text and exit code when it fails. */
async function installStep(argv: string[], ctx: InjectContext): Promise<{ error: string; exitCode: number } | null> {
  const r = await runProcess(argv, { cwd: ctx.ws, env: ctx.env, timeoutSec: INSTALL_TIMEOUT_SEC });
  if (r.notFound) return { error: `executable not found: ${argv[0]}`, exitCode: -1 };
  if (r.timedOut) return { error: `timeout after ${INSTALL_TIMEOUT_SEC}s`, exitCode: -1 };
  if (r.exitCode !== 0) return { error: r.stderr.trim() || r.stdout.trim() || `exit ${r.exitCode}`, exitCode: r.exitCode };
  return null;
}

async function installPlugin(candidate: Candidate, ctx: InjectContext): Promise<Injection> {
  const { name, version } = candidate.plugin!;
  const market = join(ctx.runDir, "codex-market");
  cpSync(candidate.dir, join(market, "plugins", name), { recursive: true });
  mkdirSync(join(market, ".claude-plugin"), { recursive: true });
  writeFileSync(
    join(market, ".claude-plugin", "marketplace.json"),
    JSON.stringify({
      name: MARKETPLACE,
      owner: { name: MARKETPLACE },
      plugins: [{ name, source: `./plugins/${name}`, version }],
    }),
  );
  for (const argv of [
    ["codex", "plugin", "marketplace", "add", market, "--json"],
    ["codex", "plugin", "add", `${name}@${MARKETPLACE}`, "--json"],
  ]) {
    const failed = await installStep(argv, ctx);
    if (failed) return { failure: `codex plugin install failed: ${failed.error}`, exitCode: failed.exitCode };
  }
  return { args: [] };
}

async function inject(candidate: Candidate, ctx: InjectContext): Promise<Injection> {
  const home = join(ctx.runDir, "codex-home");
  if (candidate.kind === "plugin") return installPlugin(candidate, ctx);
  if (candidate.kind === "skill") {
    cpSync(candidate.dir, join(home, "skills", candidate.skillName), { recursive: true });
    return { args: [] };
  }
  mkdirSync(join(home, "agents"), { recursive: true });
  for (const a of candidate.agents) {
    // A JSON string literal is a valid TOML basic string.
    const toml = [
      `name = ${JSON.stringify(a.name)}`,
      `description = ${JSON.stringify(a.description)}`,
      `developer_instructions = ${JSON.stringify(a.body)}`,
    ];
    writeFileSync(join(home, "agents", `${a.name}.toml`), toml.join("\n") + "\n");
  }
  return { args: [] };
}

const NOTICE_ITEMS = new Set(["reasoning", "todo_list", "error"]);

function fold(stdout: string): TrialRecord {
  const rec = emptyRecord();
  rec.result = "";
  let turnEnded = false;
  let turnError: string | null = null;
  let streamError: string | null = null;
  const add = (total: number | null, value: unknown) => (total ?? 0) + (num(value) ?? 0);
  for (const ev of jsonLines(stdout)) {
    if (ev.type === "item.completed") {
      const item = ev.item ?? {};
      if (item.type === "agent_message") rec.result = typeof item.text === "string" ? item.text : "";
      else if (typeof item.type === "string" && !NOTICE_ITEMS.has(item.type)) {
        rec.tool_names.push(item.type);
        if (item.type === "command_execution" && typeof item.command === "string" && item.command.includes("SKILL.md")) {
          rec.skill_used = true;
        }
      }
    } else if (ev.type === "turn.completed") {
      turnEnded = true;
      const usage = ev.usage ?? {};
      rec.input_tokens = add(rec.input_tokens, usage.input_tokens);
      rec.output_tokens = add(rec.output_tokens, usage.output_tokens);
      rec.cache_read_tokens = add(rec.cache_read_tokens, usage.cached_input_tokens);
      rec.cache_creation_tokens = add(rec.cache_creation_tokens, usage.cache_write_input_tokens);
    } else if (ev.type === "turn.failed") {
      turnEnded = true;
      turnError = typeof ev.error?.message === "string" ? ev.error.message : "";
    } else if (ev.type === "error" && typeof ev.message === "string") {
      streamError = ev.message;
    }
  }
  // Top-level error events also report retries, so they count only when no turn ended.
  rec.event_error = turnError ?? (turnEnded ? null : streamError);
  return rec;
}

export const codex: Adapter = {
  harness: "codex",
  exe: "codex",
  defaultModel: "gpt-6.1-sol",
  scrubPrefix: "CODEX_",
  reportsPlugins: false,
  wallClockDuration: true,
  canHost: () => true,
  runEnv: (runDir, base) => {
    const home = join(runDir, "home");
    const codexHome = join(runDir, "codex-home");
    mkdirSync(home, { recursive: true });
    mkdirSync(codexHome, { recursive: true });
    const env: Record<string, string> = { HOME: home, CODEX_HOME: codexHome };
    if (base.OPENAI_API_KEY !== undefined) env.CODEX_API_KEY = base.OPENAI_API_KEY;
    return env;
  },
  inject,
  // Never --ignore-user-config: the per-run config.toml carries an installed plugin.
  argv: (prompt, model, ws, injected) => [
    "codex",
    "exec",
    "--json",
    "--skip-git-repo-check",
    "--ephemeral",
    "--sandbox",
    "workspace-write",
    "-c",
    "sandbox_workspace_write.network_access=true",
    "--dangerously-bypass-hook-trust",
    ...injected,
    "-C",
    ws,
    "-m",
    model,
    prompt,
  ],
  fold,
  succeeded: (exitCode, record) => exitCode === 0 && !!record.result,
};
