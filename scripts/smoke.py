#!/usr/bin/env python3
"""Loadability smoke (issue #24, deferred D of #22).

The unit/validation layer checks artifact SHAPES statically; this drives the REAL tools
against the generated bundles under targets/ and confirms they actually load. A fragment can
be schema-correct yet rejected at load — the first run of this smoke caught exactly that
(opencode 1.17 rejecting the CC-style `tools:` frontmatter the agent transform used to pass
through).

Opt-in by design: `make smoke`, NOT part of `make ci` (needs the tools installed). Each
tool section SKIPs (never fails) when its binary is absent, and every skip is logged — no
silent caps. The CMA section is pure stdlib and always runs.

What it checks:
  - opencode (sandboxed HOME): the full generated bundle — agents in
    ~/.config/opencode/agent/, skills in ~/.claude/skills/, every mcp fragment merged into
    opencode.json — then `opencode debug config` (no config errors), `opencode agent list`
    / `opencode debug skill` / `opencode mcp list` (every generated id present). opencode
    prints config errors but still exits 0, so checks assert on OUTPUT, not exit codes.
    An mcp server whose command isn't installed lists as failed — that's environmental, so
    the check requires the server to be LISTED, not connected.
  - claude (sandboxed HOME): all mcp fragments merged into a project .mcp.json ->
    `claude mcp list` (unapproved project servers list as pending without network); each
    plugin dir -> `claude --plugin-dir <dir> plugin details <name>`.
  - CMA: `targets/claude-agents/agents/*.json` against the pinned contract for
    `BetaManagedAgentsCreateAgentParams` (name + model required, non-empty strings; typed
    optionals) — CANON.md CMA contract; schema-level, no network.

Expected ids derive from the bundle on disk (roster<->disk agreement is `make check`'s job).

Usage: python3 scripts/smoke.py   (or `make smoke`; exit 0 = pass/skip only, 1 = failures)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = os.path.join(REPO, "targets")
TIMEOUT = 90  # per tool invocation
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def tool_errored(out):
    """True when a tool printed a real error line. opencode emits `Error: ...` at line
    start (ANSI-wrapped, exit code still 0) — a bare substring match would false-positive
    on config dumps that echo agent prompts containing the word."""
    return any(line.startswith("Error:") for line in ANSI.sub("", out).splitlines())


# Pinned CMA contract (CANON.md CMA contract; BetaManagedAgentsCreateAgentParams):
# name + model are the two required creation params; the rest are typed optionals.
CMA_REQUIRED = ("name", "model")
CMA_OPTIONAL_TYPES = {"system": str, "skills": list, "tools": list, "metadata": dict}

passes, failures, skips = [], [], []


def ok(msg):
    passes.append(msg)
    print(f"  ✓ {msg}")


def fail(msg):
    failures.append(msg)
    print(f"  ✗ {msg}")


def skip(msg):
    skips.append(msg)
    print(f"  ~ SKIP: {msg}")


def run(cmd, env, cwd=None):
    """Run a tool command; return (exit_code, combined_output). Timeout counts as failure."""
    try:
        p = subprocess.run(
            cmd,
            env=env,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT after {TIMEOUT}s"


def sandbox_env(home):
    """Minimal env for a tool run against a throwaway HOME (keeps PATH; drops session vars)."""
    env = {
        "HOME": home,
        "PATH": os.environ.get("PATH", ""),
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
        "XDG_CACHE_HOME": os.path.join(home, ".cache"),
        "XDG_STATE_HOME": os.path.join(home, ".local", "state"),
        "TERM": "dumb",
        "NO_COLOR": "1",
    }
    return env


def merged_mcp(frag_dir, top_key):
    """Merge every fragment's {top_key: {...}} objects; return (config, [server names]).
    Raises ValueError naming the offending fragment on invalid JSON or a duplicate server
    name (a duplicate would be silently clobbered — that's a build regression)."""
    merged, names = {}, []
    for f in sorted(os.listdir(frag_dir)):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(frag_dir, f), encoding="utf-8") as fh:
            try:
                frag = json.load(fh)
            except json.JSONDecodeError as e:
                raise ValueError(f"mcp fragment {f} is invalid JSON: {e}") from e
        for name, spec in frag.get(top_key, {}).items():
            if name in merged:
                raise ValueError(f"mcp fragment {f} redefines server `{name}`")
            merged[name] = spec
            names.append(name)
    return {top_key: merged}, names


def present(name, out):
    """True when `name` appears in tool output as its own token — a bare substring test
    would count a slug that is merely a prefix of a longer listed name."""
    return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", out) is not None


# ── CMA (stdlib, always runs) ───────────────────────────────────────────────────────────
def validate_cma_agent(payload):
    """Return a list of problems for one CMA agent payload (empty = valid)."""
    problems = []
    for key in CMA_REQUIRED:
        v = payload.get(key)
        if not isinstance(v, str) or not v.strip():
            problems.append(f"required `{key}` missing or not a non-empty string")
    for key, typ in CMA_OPTIONAL_TYPES.items():
        if key in payload and not isinstance(payload[key], typ):
            problems.append(f"`{key}` is not a {typ.__name__}")
    return problems


def smoke_cma():
    print("CMA payload schema (stdlib, no network):")
    agents_dir = os.path.join(TARGETS, "claude-agents", "agents")
    if not os.path.isdir(agents_dir):
        skip("targets/claude-agents/agents/ absent — run `make build` first")
        return
    bad = 0
    files = [f for f in sorted(os.listdir(agents_dir)) if f.endswith(".json")]
    for f in files:
        with open(os.path.join(agents_dir, f), encoding="utf-8") as fh:
            try:
                payload = json.load(fh)
            except json.JSONDecodeError as e:
                fail(f"CMA {f}: invalid JSON ({e})")
                bad += 1
                continue
        problems = validate_cma_agent(payload)
        for p in problems:
            fail(f"CMA {f}: {p}")
        bad += bool(problems)
    if not bad:
        ok(
            f"CMA: {len(files)} agent payloads satisfy the pinned create-params contract"
        )


# ── opencode ─────────────────────────────────────────────────────────────────────────────
def smoke_opencode():
    print("opencode (sandboxed HOME):")
    if not shutil.which("opencode"):
        skip("opencode not on PATH — all opencode checks")
        return
    src = os.path.join(TARGETS, "opencode")
    with tempfile.TemporaryDirectory() as home:
        agent_dir = os.path.join(home, ".config", "opencode", "agent")
        skills_dir = os.path.join(home, ".claude", "skills")
        os.makedirs(agent_dir)
        os.makedirs(skills_dir)
        agents = sorted(
            f[:-3] for f in os.listdir(os.path.join(src, "agents")) if f.endswith(".md")
        )
        for a in agents:
            shutil.copy2(
                os.path.join(src, "agents", a + ".md"),
                os.path.join(agent_dir, a + ".md"),
            )
        skills = sorted(os.listdir(os.path.join(src, "skills")))
        for s in skills:
            shutil.copytree(os.path.join(src, "skills", s), os.path.join(skills_dir, s))
        try:
            config, servers = merged_mcp(os.path.join(src, "mcp"), "mcp")
        except ValueError as e:
            fail(f"opencode: {e}")
            return
        with open(
            os.path.join(home, ".config", "opencode", "opencode.json"), "w"
        ) as fh:
            json.dump(config, fh)
        env = sandbox_env(home)

        # 1 — config resolves without errors (opencode exits 0 even on config errors,
        #     so assert on output)
        code, out = run(["opencode", "debug", "config"], env)
        if code != 0 or tool_errored(out):
            fail(f"opencode debug config reported errors:\n{out[:500]}")
            return  # a broken config poisons every later check; stop here, loudly
        ok("opencode debug config: bundle config resolves cleanly")

        # 2 — every generated agent loads
        _, out = run(["opencode", "agent", "list"], env)
        missing = [a for a in agents if not present(a, out)]
        if tool_errored(out) or missing:
            fail(f"opencode agent list: missing/errored {missing or ''}\n{out[:300]}")
        else:
            ok(f"opencode agent list: all {len(agents)} generated agents load")

        # 3 — the skill scan runs clean and discovers generated skills. opencode's
        #     external-skill scan is ASYNC: `debug skill` dumps whatever is indexed at
        #     that instant, so the discovered subset varies run to run (observed 6–59 of
        #     58 across identical sandboxes, opencode 1.17.10). Full-set presence can't be
        #     asserted deterministically — we require a clean run + ≥1 generated skill,
        #     and LOG the observed coverage so the cap is never silent.
        _, out = run(["opencode", "debug", "skill"], env)
        found = [s for s in skills if present(s, out)]
        if tool_errored(out):
            fail(f"opencode debug skill reported errors:\n{out[:300]}")
        elif not found:
            fail("opencode debug skill: no generated skill discovered at all")
        else:
            ok(
                f"opencode debug skill: scan clean; {len(found)}/{len(skills)} generated "
                f"skills indexed at dump time (async scan — subset varies by run)"
            )

        # 4 — every mcp server is LISTED (a server whose command isn't installed shows
        #     as failed — environmental, not a bundle defect)
        _, out = run(["opencode", "mcp", "list"], env)
        missing = [s for s in servers if not present(s, out)]
        if missing:
            fail(f"opencode mcp list: not listed: {missing}\n{out[:300]}")
        else:
            ok(f"opencode mcp list: all {len(servers)} servers listed")


# ── claude code ──────────────────────────────────────────────────────────────────────────
def smoke_claude():
    print("Claude Code (sandboxed HOME):")
    if not shutil.which("claude"):
        skip("claude not on PATH — all Claude Code checks")
        return
    src = os.path.join(TARGETS, "claude-code")
    with tempfile.TemporaryDirectory() as home:
        # sandbox_env builds a fresh dict, so a live session's CLAUDECODE (and every
        # other session var) is already not inherited — no explicit unset needed.
        env = sandbox_env(home)

        # 1 — all mcp fragments merge into a project .mcp.json and list (unapproved
        #     project servers show as pending without network / health checks)
        proj = os.path.join(home, "proj")
        os.makedirs(proj)
        try:
            config, servers = merged_mcp(os.path.join(src, "mcp"), "mcpServers")
        except ValueError as e:
            fail(f"claude: {e}")
            return
        with open(os.path.join(proj, ".mcp.json"), "w") as fh:
            json.dump(config, fh)
        code, out = run(["claude", "mcp", "list"], env, cwd=proj)
        missing = [s for s in servers if not present(s, out)]
        if code != 0 or missing:
            fail(f"claude mcp list: exit {code}, missing {missing}\n{out[:300]}")
        else:
            ok(f"claude mcp list: all {len(servers)} servers listed from .mcp.json")

        # 2 — every generated plugin loads via --plugin-dir
        plugins_dir = os.path.join(src, "plugins")
        if not os.path.isdir(plugins_dir):
            skip("targets/claude-code/plugins/ absent — no plugin checks")
            return
        for p in sorted(os.listdir(plugins_dir)):
            pdir = os.path.join(plugins_dir, p)
            if not os.path.isfile(os.path.join(pdir, ".claude-plugin", "plugin.json")):
                continue
            code, out = run(
                ["claude", "--plugin-dir", pdir, "plugin", "details", p], env
            )
            if code != 0 or not present(p, out):
                fail(f"claude plugin details {p}: exit {code}\n{out[:300]}")
            else:
                ok(f"claude plugin details {p}: loads with component inventory")


def main():
    smoke_cma()
    smoke_opencode()
    smoke_claude()
    print(
        f"\nsmoke: {len(passes)} passed · {len(failures)} failed · {len(skips)} skipped"
    )
    for s in skips:
        print(f"  skipped: {s}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
