"""ClaudeAdapter — drive Claude Code (`claude -p`) headlessly.

Ported near-verbatim from the workbench run_eval.py chassis:
per-kind injection (plugin → --plugin-dir; skill → synthetic-plugin wrapper;
agent → --agents JSON from frontmatter), stream-json parsing, and the env scrub
that keeps the host's Claude Code config out of a trial.

Isolation is a hard invariant here (task-22): every trial runs against a
throwaway HOME + config dir with user/project settings files and foreign MCP
config switched off, so a candidate is graded on itself and not on whatever the
operator happens to have installed. There is no "run without isolation" path —
if the isolation tree cannot be built the adapter raises rather than inheriting.
"""

from __future__ import annotations

import atexit
import json
import os
import re
import shutil
import subprocess
import tempfile

from .base import Adapter, Injection, NormalizedRecord
from ..candidate import agent_identities


class ClaudeAdapter(Adapter):
    name = "claude"

    def __init__(self, allow_bash: bool = False, **_ignored):
        # allow_bash is claude-specific (opencode uses --dangerously-skip-permissions);
        # it flows in via the adapter registry (get_adapter(name, allow_bash=...)).
        self.allow_bash = allow_bash

    # ── preflight ────────────────────────────────────────────────────────────

    def preflight(self) -> str:
        """"missing" if the CLI is not on PATH, else "ok".

        Claude Code auth can be a login (no env token), so a cheap "noauth" probe
        without a billed call is not reliable — an auth failure surfaces as a
        non-zero-exit trial with an error field. ("noauth" stays in the contract
        enum for adapters that *can* probe it, e.g. opencode.)
        """
        if shutil.which("claude") is None:
            return "missing"
        return "ok"

    def cli_version(self) -> str:
        try:
            proc = subprocess.run(
                ["claude", "--version"], capture_output=True, text=True, timeout=30
            )
            return proc.stdout.strip() or "unknown"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return "unavailable"

    # ── injection ────────────────────────────────────────────────────────────

    def inject(self, kind: str, candidate_dir: str, tmpdir: str) -> Injection:
        """Per-kind `claude -p --bare` flags that load exactly this candidate."""
        if kind == "plugin":
            return Injection(["--plugin-dir", candidate_dir], [], True)
        if kind == "skill":
            name = os.path.basename(os.path.normpath(candidate_dir))
            plug = self._synth_plugin(candidate_dir, name, tmpdir)
            return Injection(["--plugin-dir", plug], [plug], True)
        if kind == "agent":
            agent_identities(candidate_dir)
            payload = json.dumps(self._agent_definitions(candidate_dir))
            return Injection(["--agents", payload], [], True)
        # Kinds claude cannot host -> explicit skip (never a silent no-op).
        return Injection([], [], False)

    @staticmethod
    def _synth_plugin(candidate_dir, name, tmpdir):
        """Wrap a bare skill candidate in a synthetic plugin dir for --plugin-dir."""
        plug = os.path.join(tmpdir, "plugin")
        os.makedirs(os.path.join(plug, ".claude-plugin"))
        manifest = {
            "name": f"eval-{name}",
            "version": "0.0.0",
            "description": f"eval-harness wrapper for skill candidate {name}",
        }
        with open(os.path.join(plug, ".claude-plugin", "plugin.json"), "w") as fh:
            json.dump(manifest, fh)
        shutil.copytree(candidate_dir, os.path.join(plug, "skills", name))
        return plug

    @classmethod
    def _agent_definitions(cls, path):
        """Build the --agents JSON payload from a candidate's agent .md files."""
        defs = {}
        for f in sorted(os.listdir(path)):
            if not f.endswith(".md") or f.lower() == "readme.md":
                continue
            with open(os.path.join(path, f), encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            fm, body = cls._split_frontmatter(text)
            name = cls._fm_field(fm, "name") or os.path.splitext(f)[0]
            desc = cls._fm_field(fm, "description") or body.strip().split("\n")[0][:200]
            defs[name] = {"description": desc, "prompt": body.strip()}
        return defs

    @staticmethod
    def _split_frontmatter(text):
        """Return (frontmatter, body). Frontmatter is None when absent."""
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
        if m:
            return m.group(1), m.group(2)
        return None, text

    @staticmethod
    def _fm_field(fm, key):
        if fm is None:
            return None
        m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
        return m.group(1).strip().strip("\"'") if m else None

    # ── invocation ───────────────────────────────────────────────────────────

    # The eval allowlist. `Skill` + `Task` are load-bearing: without them the
    # injected skill/agent can never be *invoked* even though it loads (#170).
    # Bash/Edit/Write/Read/Grep/Glob are the tools a candidate needs to do real
    # work in its isolated workspace.
    ALLOWED_TOOLS = "Skill,Task,Bash,Edit,Read,Write,Grep,Glob"

    #: Inherited env vars that would carry the host's Claude Code identity/config
    #: into the trial. Scrubbed before the per-run values are set, so a bug in the
    #: isolation path can never silently degrade into "uses the operator's setup".
    #: ``PATH`` and ``ANTHROPIC_API_KEY`` are deliberately NOT scrubbed — the CLI
    #: has to be findable and the apiKeyHelper has to have a key to echo.
    CONFIG_BLEED_ENV = (
        "CLAUDECODE",  # fleet-dashboard: block nested-claude detection
        "CLAUDE_CODE_ENTRYPOINT",  # marks the child as part of a parent session
        "CLAUDE_PLUGIN_ROOT",  # points at the caller's plugin tree
        "CLAUDE_CONFIG_DIR",  # re-set per run below; popped so it can't survive
        "XDG_CONFIG_HOME",  # re-set per run below; popped so it can't survive
    )

    def invocation(self, prompt, workspace, model, injection: Injection):
        """Build the headless ``claude -p`` argv + env, fully isolated from the host.

        Wave 1 used ``--bare``, but ``--bare`` sets ``CLAUDE_CODE_SIMPLE=1`` which
        strips the advertised toolset to ``['Bash','Edit','Read']`` — the ``Skill``
        and ``Task`` tools never surface, so an injected skill/agent loads yet can
        never be invoked (#170; battle-test §2.1; probe-confirmed 2026-07-21). We
        drop ``--bare`` (only way the init event advertises ``Skill``) and restore
        its env-key auth by other means: a per-run ``apiKeyHelper`` (via
        ``--settings``) echoes ``$ANTHROPIC_API_KEY``, so headless env-key auth
        keeps working (``apiKeySource: apiKeyHelper``) with no interactive login.

        **Isolation contract** (task-22; symmetric in kind with the opencode
        adapter's throwaway HOME). Every layer the CLI can load user state from is
        closed, and each was probe-confirmed against claude 2.1.220:

        - throwaway ``HOME`` (``<run_tmp>/claude-home``) + ``XDG_CONFIG_HOME``
          inside it, so HOME-adjacent config roots cannot reach the user's;
        - fresh per-run ``CLAUDE_CONFIG_DIR`` → no user plugins/skills/hooks
          (init reports ``plugins: []``, 4 built-in agents, 15 built-in skills;
          with the real config dir it reported 7 plugins / 8 agents / 27 skills);
        - ``--setting-sources ""`` → no user/project/local ``settings.json``
          layers (and the ``--settings`` apiKeyHelper still applies: verified
          ``apiKeySource: apiKeyHelper`` under an empty source list);
        - ``--strict-mcp-config`` → no user/project MCP servers (``mcp_servers:
          []``);
        - :attr:`CONFIG_BLEED_ENV` scrubbed from the inherited environment.

        The isolation tree is materialised beside the workspace (``workspace ==
        <run_tmp>/ws``) so the core's tmpdir cleanup sweeps it. If that dir is not
        writable we retry in a private ``tempfile.mkdtemp()`` root rather than
        degrade — and if *that* fails we raise. Running a trial against the
        operator's real HOME/config is never an outcome.
        """
        argv = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            self.ALLOWED_TOOLS,
            # Isolation flags — see the contract above. Empty --setting-sources
            # disables user/project/local settings files; --strict-mcp-config
            # ignores every MCP config we did not pass explicitly.
            "--setting-sources",
            "",
            "--strict-mcp-config",
        ]
        argv += list(injection.flags)
        if model:
            argv += ["--model", model]

        env = dict(os.environ)
        for key in self.CONFIG_BLEED_ENV:
            env.pop(key, None)

        # Per-run isolation lives beside the workspace, so the core cleans it up
        # with the run tmpdir. workspace == <run_tmp>/ws → its parent is the tmp.
        run_dir = os.path.dirname(os.path.normpath(workspace))
        try:
            home, xdg, config_dir, helper = self._materialise_isolation(run_dir)
        except OSError:
            # Run dir not writable (e.g. a bare stub workspace path). Isolation is
            # not optional, so retry in a private temp root instead of inheriting
            # the user's HOME/config. Not swept by the core's run-tmp cleanup, so
            # this adapter sweeps it itself at interpreter exit.
            try:
                root = tempfile.mkdtemp(prefix="claude-iso-")
                atexit.register(shutil.rmtree, root, ignore_errors=True)
                home, xdg, config_dir, helper = self._materialise_isolation(root)
            except OSError as exc:
                raise RuntimeError(
                    "claude adapter cannot build an isolated HOME/config tree "
                    f"(neither the run dir {run_dir!r} nor the system temp dir is "
                    "writable); refusing to run a trial against the host config"
                ) from exc

        env["HOME"] = home
        env["XDG_CONFIG_HOME"] = xdg
        env["CLAUDE_CONFIG_DIR"] = config_dir
        argv += ["--settings", json.dumps({"apiKeyHelper": helper})]
        return argv, env

    @staticmethod
    def _materialise_isolation(root):
        """Create one run's isolation tree under ``root``.

        Returns ``(home, xdg_config_home, claude_config_dir, apikey_helper)``.
        Raises ``OSError`` if ``root`` is not writable — the caller decides what
        to do about that (never "carry on uninsulated").
        """
        home = os.path.join(root, "claude-home")
        xdg = os.path.join(home, ".config")
        config_dir = os.path.join(root, "claude-config")
        os.makedirs(xdg, exist_ok=True)
        os.makedirs(config_dir, exist_ok=True)
        helper = os.path.join(root, "apikey-helper.sh")
        with open(helper, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\nprintf "%s" "${ANTHROPIC_API_KEY:-}"\n')
        os.chmod(helper, 0o755)
        return home, xdg, config_dir, helper

    # ── log parsing ──────────────────────────────────────────────────────────

    def parse_log(self, raw: str) -> NormalizedRecord:
        """Fold `--output-format stream-json` lines into one NormalizedRecord."""
        rec = NormalizedRecord()
        for line in (raw or "").splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if not isinstance(ev, dict):
                continue
            if ev.get("type") == "system" and ev.get("subtype") == "init":
                rec.plugins = ev.get("plugins") or []
                rec.plugin_errors = ev.get("plugin_errors") or []
            elif ev.get("type") == "assistant":
                content = (ev.get("message") or {}).get("content") or []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        rec.tool_names.append(block.get("name") or "")
            elif ev.get("type") == "result":
                rec.result = ev.get("result") or ""
                rec.cost_usd = ev.get("total_cost_usd")
                rec.duration_ms = ev.get("duration_ms")
                rec.num_turns = ev.get("num_turns")
                usage = ev.get("usage") or {}
                rec.input_tokens = usage.get("input_tokens")
                rec.output_tokens = usage.get("output_tokens")
                rec.cache_read_tokens = usage.get("cache_read_input_tokens")
                rec.cache_creation_tokens = usage.get("cache_creation_input_tokens")
        rec.skill_used = any(n == "Skill" for n in rec.tool_names)
        return rec

    # ── success ──────────────────────────────────────────────────────────────

    def success(self, returncode: int, record: NormalizedRecord) -> bool:
        # Claude Code exit codes are honest: 0 == success.
        return returncode == 0
