// opencode (2.0.25) as an agent under test: argv, per-run isolation, skill and
// agent injection under OPENCODE_CONFIG_DIR, and the JSON-event fold.
import { cpSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { AgentDef, Candidate } from "./candidate.ts";
import { emptyRecord, jsonLines, num, type Adapter, type InjectContext, type Injection, type TrialRecord } from "./harnesses.ts";

const SCHEMA = "https://opencode.ai/config.json";
const SKILL_NAME = /^[a-z0-9]+(-[a-z0-9]+)*$/;

const TOOL_KEYS: Record<string, string> = {
  bash: "bash",
  edit: "edit",
  write: "edit",
  read: "read",
  grep: "grep",
  glob: "glob",
  webfetch: "webfetch",
  websearch: "websearch",
};

/** A model id as opencode takes it: ids with `/` pass through, others get `anthropic/`. */
export function providerModel(model: string): string {
  return model.includes("/") ? model : `anthropic/${model}`;
}

/** Translates one agent file into an opencode subagent definition. */
export function translateAgent(agent: AgentDef): string {
  const lines = ["---", `description: ${JSON.stringify(agent.description)}`, "mode: subagent"];
  const model = agent.model;
  // Aliases such as haiku, sonnet, opus and inherit have neither / nor -; opencode cannot resolve them.
  if (model && (model.includes("/") || model.includes("-"))) lines.push(`model: ${providerModel(model)}`);
  if (agent.tools !== null) {
    const allowed = new Set<string>();
    for (const tool of agent.tools.split(/[\s,]+/)) {
      const key = TOOL_KEYS[tool.toLowerCase()];
      if (key) allowed.add(key);
    }
    lines.push("permission:");
    if (!allowed.has("edit")) lines.push("  edit: deny");
    if (!allowed.has("bash")) lines.push("  bash: deny");
    for (const key of [...allowed].sort()) lines.push(`  ${key}: allow`);
  }
  lines.push("---", agent.body);
  return lines.join("\n") + "\n";
}

async function inject(candidate: Candidate, ctx: InjectContext): Promise<Injection> {
  const config = join(ctx.runDir, "oc-config");
  if (candidate.kind === "skill") {
    const name = candidate.skillName;
    cpSync(candidate.dir, join(config, "skills", name), { recursive: true });
    writeFileSync(join(config, "opencode.json"), JSON.stringify({ $schema: SCHEMA, permission: { skill: { [name]: "allow" } } }));
  } else {
    mkdirSync(join(config, "agents"), { recursive: true });
    for (const agent of candidate.agents) writeFileSync(join(config, "agents", `${agent.name}.md`), translateAgent(agent));
    writeFileSync(join(config, "opencode.json"), JSON.stringify({ $schema: SCHEMA }));
  }
  return { args: [] };
}

function eventError(ev: Record<string, any>): string {
  const err = ev.error;
  const candidates = [err?.data?.message, err?.message, ev.part?.message, ev.message, err?.name, err];
  const found = candidates.find((c) => typeof c === "string" && c !== "");
  return found ?? "opencode reported an error event";
}

function add(total: number | null, value: unknown): number | null {
  const n = num(value);
  return n === null ? total : (total ?? 0) + n;
}

function fold(stdout: string): TrialRecord {
  const rec = emptyRecord();
  const texts: string[] = [];
  let steps = 0;
  for (const ev of jsonLines(stdout)) {
    const part = ev.part ?? {};
    if (ev.type === "step_start") steps++;
    else if (ev.type === "tool_use" && typeof part.tool === "string") rec.tool_names.push(part.tool);
    else if (ev.type === "text" && typeof part.text === "string" && part.text !== "") texts.push(part.text);
    else if (ev.type === "step_finish") {
      rec.cost_usd = add(rec.cost_usd, part.cost);
      const tokens = part.tokens ?? {};
      rec.input_tokens = add(rec.input_tokens, tokens.input);
      rec.output_tokens = add(rec.output_tokens, tokens.output);
      rec.cache_read_tokens = add(rec.cache_read_tokens, tokens.cache?.read);
      rec.cache_creation_tokens = add(rec.cache_creation_tokens, tokens.cache?.write);
    } else if (ev.type === "error") rec.event_error = eventError(ev);
  }
  rec.result = texts.join("\n");
  rec.num_turns = steps === 0 ? null : steps;
  rec.skill_used = rec.tool_names.includes("skill");
  return rec;
}

export const opencode: Adapter = {
  harness: "opencode",
  exe: "opencode",
  defaultModel: "claude-sonnet-4-5",
  scrubPrefix: "OPENCODE",
  withheldEnv: [],
  reportsPlugins: false,
  wallClockDuration: true,
  // opencode silently ignores a skill whose name breaks its pattern, and hosts no Claude plugins.
  canHost: (c) =>
    c.kind === "agent" || (c.kind === "skill" && c.skillName.length <= 64 && SKILL_NAME.test(c.skillName)),
  runEnv: (runDir) => {
    const home = join(runDir, "home");
    const config = join(runDir, "oc-config");
    mkdirSync(home, { recursive: true });
    mkdirSync(config, { recursive: true });
    return { HOME: home, OPENCODE_CONFIG_DIR: config };
  },
  inject,
  // --standalone is mandatory: without it opencode starts a background service that outlives the trial.
  argv: (prompt, model, _ws, injected) => ["opencode", "run", prompt, "--format", "json", "--auto", "--standalone", "-m", providerModel(model), ...injected],
  fold,
  succeeded: (exitCode) => exitCode === 0,
};
