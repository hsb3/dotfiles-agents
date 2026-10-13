// Claude Code (2.1.296) as an agent under test: argv, per-run isolation,
// candidate injection, and the stream-json fold.
import { cpSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Candidate } from "./candidate.ts";
import { emptyRecord, jsonLines, num, type Adapter, type InjectContext, type Injection, type TrialRecord } from "./harnesses.ts";
import type { Env } from "./subprocess.ts";

/** Per-run variables for any claude process (agent or grader); creates both dirs. */
export function claudeRunEnv(home: string, configDir: string): Env {
  mkdirSync(home, { recursive: true });
  mkdirSync(configDir, { recursive: true });
  return { HOME: home, CLAUDE_CONFIG_DIR: configDir, CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS: "1" };
}

async function inject(candidate: Candidate, ctx: InjectContext): Promise<Injection> {
  if (candidate.kind === "plugin") return { args: ["--plugin-dir", candidate.dir] };
  if (candidate.kind === "skill") {
    const skill = candidate.skillName;
    const plugin = join(ctx.runDir, "plugin");
    mkdirSync(join(plugin, ".claude-plugin"), { recursive: true });
    writeFileSync(
      join(plugin, ".claude-plugin", "plugin.json"),
      JSON.stringify({ name: `eval-${skill}`, version: "0.0.0", description: `eval-harness wrapper for skill candidate ${skill}` }),
    );
    cpSync(candidate.dir, join(plugin, "skills", skill), { recursive: true });
    return { args: ["--plugin-dir", plugin] };
  }
  const agents: Record<string, { description: string; prompt: string }> = {};
  for (const a of candidate.agents) agents[a.name] = { description: a.description, prompt: a.body };
  return { args: ["--agents", JSON.stringify(agents)] };
}

function fold(stdout: string): TrialRecord {
  const rec = emptyRecord();
  for (const ev of jsonLines(stdout)) {
    if (ev.type === "system" && ev.subtype === "init") {
      rec.plugins = Array.isArray(ev.plugins) ? ev.plugins : [];
      rec.plugin_errors = Array.isArray(ev.plugin_errors) ? ev.plugin_errors : [];
    } else if (ev.type === "assistant") {
      const content = ev.message?.content;
      if (!Array.isArray(content)) continue;
      for (const block of content) {
        if (block?.type === "tool_use" && typeof block.name === "string") rec.tool_names.push(block.name);
      }
    } else if (ev.type === "result") {
      rec.result = typeof ev.result === "string" ? ev.result : null;
      rec.cost_usd = num(ev.total_cost_usd);
      rec.duration_ms = num(ev.duration_ms);
      rec.num_turns = num(ev.num_turns);
      const usage = ev.usage ?? {};
      rec.input_tokens = num(usage.input_tokens);
      rec.output_tokens = num(usage.output_tokens);
      rec.cache_read_tokens = num(usage.cache_read_input_tokens);
      rec.cache_creation_tokens = num(usage.cache_creation_input_tokens);
      rec.event_error = ev.is_error === true ? (rec.result ?? "") : null;
    }
  }
  rec.skill_used = rec.tool_names.includes("Skill");
  return rec;
}

export const claude: Adapter = {
  harness: "claude",
  exe: "claude",
  defaultModel: "claude-sonnet-4-5",
  scrubPrefix: "CLAUDE",
  reportsPlugins: true,
  wallClockDuration: false,
  canHost: () => true,
  runEnv: (runDir) => claudeRunEnv(join(runDir, "home"), join(runDir, "claude-config")),
  inject,
  // Never --bare: it hides the Skill and Task tools from an injected candidate.
  argv: (prompt, model, _ws, injected) => [
    "claude",
    "-p",
    prompt,
    "--output-format",
    "stream-json",
    "--verbose",
    "--permission-mode",
    "acceptEdits",
    "--allowedTools",
    "Skill,Task,Bash,Edit,Read,Write,Grep,Glob",
    "--setting-sources",
    "",
    "--strict-mcp-config",
    ...injected,
    "--model",
    model,
  ],
  fold,
  succeeded: (exitCode) => exitCode === 0,
};
