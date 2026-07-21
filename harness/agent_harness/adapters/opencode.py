"""OpencodeAdapter — drive opencode (`opencode run`) headlessly.

Mirrors the ClaudeAdapter across the vendor seam (base.Adapter) but with
opencode's very different mechanics, all confirmed empirically against
**opencode 1.18.0** on 2026-07-21 (see handoff-w2.md §"empirical findings"):

- **Injection rides a per-run config dir, not CLI flags.** opencode has no
  ``--plugin-dir`` equivalent; instead it layers extra ``skills/ agents/ …``
  search roots and an ``opencode.json`` from ``OPENCODE_CONFIG_DIR``. So
  ``inject`` materialises ``<tmpdir>/oc-config`` and returns it in
  ``Injection.files``; ``invocation`` reads ``files[0]`` and exports it as
  ``OPENCODE_CONFIG_DIR``. ``flags`` stays empty for every kind.
- **Throwaway HOME per run** (isolation the claude adapter lacked): a fresh
  ``$HOME`` inside the run tmpdir means the user's ``~/.config/opencode`` and
  ``~/.claude/skills`` never bleed into a trial. auth then comes purely from the
  passed-through provider env var (``ANTHROPIC_API_KEY`` — opencode's anthropic
  provider falls back to it with zero config).
- **``--auto``** is the headless permission bypass in 1.18.0 (there is no
  ``--dangerously-skip-permissions``); combined with an injected
  ``permission.skill.<name>: allow`` grant so a skill call never blocks on ``ask``.
- **``--format json``** emits JSONL events discriminated by a top-level ``type``
  (``step_start`` / ``text`` / ``tool_use`` / ``step_finish`` / ``error``), each
  wrapping a ``part`` payload; ``parse_log`` folds the whole stream (never assumes
  the last line is terminal — opencode#26855 can drop the final ``step_finish``).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

from .base import Adapter, Injection, NormalizedRecord

# opencode skill names are stricter than Claude Code's: a name failing this regex
# is silently invisible to opencode, so we skip (supported=False) rather than
# inject a dead skill. Source: opencode-expertise skill + distribution.md gotcha 3.
_SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class OpencodeAdapter(Adapter):
    name = "opencode"

    # A throwaway HOME has no configured default model, so we must always pass
    # ``-m`` — this pinned default is used when the run model is None/"default".
    DEFAULT_MODEL = "anthropic/claude-sonnet-4-5"

    def __init__(self, **_ignored):
        # opencode has no allow_bash notion (permissions are handled by --auto +
        # the injected config); the kwarg is accepted and ignored for registry
        # symmetry with the claude adapter (get_adapter passes allow_bash=...).
        pass

    # ── preflight ────────────────────────────────────────────────────────────

    #: env vars any of which authenticate a provider opencode can reach with
    #: zero config (throwaway HOME bypasses persisted auth.json).
    _AUTH_ENV = (
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_GENERATIVE_AI_API_KEY",
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
    )

    def preflight(self) -> str:
        """"missing" if the CLI is absent, "noauth" if no provider key is in the
        env, else "ok".

        Because every trial runs under a throwaway HOME, persisted opencode auth
        is intentionally bypassed and the only usable credential is a provider
        env var — so "no provider env key" is a genuine, cheap noauth signal.
        """
        if shutil.which("opencode") is None:
            return "missing"
        if not any(os.environ.get(k) for k in self._AUTH_ENV):
            return "noauth"
        return "ok"

    def cli_version(self) -> str:
        try:
            proc = subprocess.run(
                ["opencode", "--version"], capture_output=True, text=True, timeout=30
            )
            return proc.stdout.strip() or "unknown"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return "unavailable"

    # ── injection ────────────────────────────────────────────────────────────

    def inject(self, kind: str, candidate_dir: str, tmpdir: str) -> Injection:
        """Materialise a per-run ``OPENCODE_CONFIG_DIR`` loading this candidate.

        Returns ``files=[config_dir]`` (invocation exports it) and no CLI flags.
        ``supported=False`` for kinds opencode genuinely can't host, so the core
        emits an explicit skip row (never a silent dead injection).
        """
        if kind == "skill":
            return self._inject_skill(candidate_dir, tmpdir)
        if kind == "agent":
            return self._inject_agent(candidate_dir, tmpdir)
        if kind == "plugin":
            # A Claude Code plugin bundle (.claude-plugin/plugin.json + hooks/
            # skills) has no mechanical opencode translation — hooks require a
            # bespoke TS plugin ("Hooks → NOT mechanical", cc-to-opencode-mapping).
            return Injection([], [], False)
        # Unknown kind -> explicit skip (mirrors the claude adapter).
        return Injection([], [], False)

    def _inject_skill(self, candidate_dir, tmpdir) -> Injection:
        name = os.path.basename(os.path.normpath(candidate_dir))
        if not (1 <= len(name) <= 64 and _SKILL_NAME_RE.match(name)):
            # Invalid name would be silently invisible to opencode -> skip loudly.
            return Injection([], [], False)
        config_dir = self._new_config_dir(tmpdir)
        shutil.copytree(candidate_dir, os.path.join(config_dir, "skills", name))
        # Grant the skill (default `ask` would block a headless call even with
        # --auto's leniency) via the config dir's own opencode.json (merged in).
        self._write_config(config_dir, {"permission": {"skill": {name: "allow"}}})
        return Injection([], [config_dir], True)

    def _inject_agent(self, candidate_dir, tmpdir) -> Injection:
        defs = self._agent_files(candidate_dir)
        if not defs:
            return Injection([], [], False)
        config_dir = self._new_config_dir(tmpdir)
        agents_dir = os.path.join(config_dir, "agents")
        os.makedirs(agents_dir)
        for fname, text in defs.items():
            with open(os.path.join(agents_dir, fname), "w", encoding="utf-8") as fh:
                fh.write(text)
        self._write_config(config_dir, {})
        return Injection([], [config_dir], True)

    @staticmethod
    def _new_config_dir(tmpdir) -> str:
        config_dir = os.path.join(tmpdir, "oc-config")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    @staticmethod
    def _write_config(config_dir, extra: dict):
        cfg = {"$schema": "https://opencode.ai/config.json"}
        cfg.update(extra)
        with open(os.path.join(config_dir, "opencode.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)

    @classmethod
    def _agent_files(cls, path) -> dict:
        """Translate each candidate agent .md → an opencode agent file body.

        CC `name` becomes the filename; `description` is required; `mode:
        subagent` is added; a bare `model:` gains the required provider prefix
        (or is dropped to inherit the run model); the CC `tools:` allowlist
        becomes an explicit opencode `permission:` map (unlisted CC tools were
        implicitly denied, so we emit denies).
        """
        out = {}
        for f in sorted(os.listdir(path)):
            if not f.endswith(".md") or f.lower() == "readme.md":
                continue
            with open(os.path.join(path, f), encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            fm, body = cls._split_frontmatter(text)
            name = cls._fm_field(fm, "name") or os.path.splitext(f)[0]
            desc = cls._fm_field(fm, "description") or body.strip().split("\n")[0][:200]
            out[f"{name}.md"] = cls._render_agent(fm, name, desc, body)
        return out

    @classmethod
    def _render_agent(cls, fm, name, desc, body) -> str:
        lines = ["---", f"description: {desc}", "mode: subagent"]
        model = cls._fm_field(fm, "model")
        if model:
            lines.append(f"model: {cls._provider_prefixed(model)}")
        tools = cls._fm_field(fm, "tools")
        perm = cls._tools_to_permission(tools)
        if perm:
            lines.append("permission:")
            lines.extend(f"  {tool}: {action}" for tool, action in perm)
        lines.append("---")
        return "\n".join(lines) + "\n" + body.strip() + "\n"

    #: CC tool name -> opencode permission key (best-effort v1 mapping).
    _TOOL_PERMISSION_MAP = {
        "bash": "bash",
        "edit": "edit",
        "write": "edit",
        "read": "read",
        "grep": "grep",
        "glob": "glob",
        "webfetch": "webfetch",
        "websearch": "websearch",
    }

    @classmethod
    def _tools_to_permission(cls, tools_field):
        """CC `tools:` allowlist -> ordered opencode permission (allow/deny) pairs.

        Inversion: an allowlist means everything else is denied. We emit `edit`
        and `bash` denies when they aren't allowed (the two consequential write
        surfaces); allowed tools that map to a permission key get an explicit
        allow. Returns [] when no `tools:` field is present (inherit defaults).
        """
        if not tools_field:
            return []
        allowed = {t.strip().lower() for t in re.split(r"[,\s]+", tools_field) if t.strip()}
        allowed_keys = {cls._TOOL_PERMISSION_MAP[t] for t in allowed if t in cls._TOOL_PERMISSION_MAP}
        pairs = []
        # Deny the consequential surfaces first if not explicitly allowed…
        for key in ("edit", "bash"):
            if key not in allowed_keys:
                pairs.append((key, "deny"))
        # …then allow what the candidate did list (narrow rules last: opencode
        # evaluates the LAST matching rule).
        for key in sorted(allowed_keys):
            pairs.append((key, "allow"))
        return pairs

    @staticmethod
    def _split_frontmatter(text):
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

    @staticmethod
    def _provider_prefixed(model) -> str:
        """opencode model ids need a `provider/` prefix; bare ids default to
        anthropic (the pinned default provider for this harness)."""
        return model if "/" in model else f"anthropic/{model}"

    # ── invocation ───────────────────────────────────────────────────────────

    def invocation(self, prompt, workspace, model, injection: Injection):
        argv = [
            "opencode",
            "run",
            prompt,
            "--dir",
            workspace,
            "--format",
            "json",
            "--auto",  # headless permission bypass (1.18.0; no skip-permissions flag)
            "-m",
            self._provider_prefixed(model) if (model and model != "default") else self.DEFAULT_MODEL,
        ]

        env = dict(os.environ)
        # Drop any inherited opencode config pointers so the trial is hermetic;
        # our own OPENCODE_CONFIG_DIR (if injecting) is the only config layer.
        for key in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_CONTENT", "OPENCODE_CONFIG_DIR"):
            env.pop(key, None)

        # Throwaway HOME inside the run tmpdir (workspace == <tmp>/ws), so the
        # core's cleanup removes it and no user config bleeds in (handoff §7).
        home = os.path.join(os.path.dirname(os.path.normpath(workspace)), "oc-home")
        os.makedirs(home, exist_ok=True)
        env["HOME"] = home

        if injection.files:
            env["OPENCODE_CONFIG_DIR"] = injection.files[0]
        return argv, env

    # ── log parsing ──────────────────────────────────────────────────────────

    def parse_log(self, raw: str) -> NormalizedRecord:
        """Fold `--format json` JSONL into one NormalizedRecord.

        Scans the whole stream (never trusts the last line to be terminal —
        opencode#26855 can drop the final `step_finish`): cost is summed across
        every `step_finish`, turns counted from `step_start`, duration derived
        from the min/max event timestamps.
        """
        rec = NormalizedRecord()
        texts = []
        cost = 0.0
        have_cost = False
        steps = 0
        timestamps = []
        for line in (raw or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if not isinstance(ev, dict):
                continue
            etype = ev.get("type")
            part = ev.get("part") or {}
            ts = ev.get("timestamp")
            if isinstance(ts, (int, float)) and not isinstance(ts, bool):
                timestamps.append(ts)
            if etype == "step_start":
                steps += 1
            elif etype == "tool_use":
                tool = part.get("tool")
                if tool:
                    rec.tool_names.append(tool)
                    if tool == "skill":
                        rec.skill_used = True
            elif etype == "text":
                t = part.get("text")
                if isinstance(t, str) and t:
                    texts.append(t)
            elif etype == "step_finish":
                c = part.get("cost")
                if isinstance(c, (int, float)) and not isinstance(c, bool):
                    cost += c
                    have_cost = True
            elif etype == "error":
                msg = self._error_message(ev, part)
                if msg:
                    rec.error = msg
                    rec.plugin_errors.append(msg)
        rec.result = "\n".join(texts)
        rec.num_turns = steps or None
        rec.cost_usd = cost if have_cost else None
        if len(timestamps) >= 2:
            rec.duration_ms = int(max(timestamps) - min(timestamps))
        return rec

    @staticmethod
    def _error_message(ev, part):
        """Best-effort extraction of an error string (event schema unobserved)."""
        for src in (part, ev):
            if not isinstance(src, dict):
                continue
            for key in ("message", "error", "text", "name"):
                val = src.get(key)
                if isinstance(val, str) and val:
                    return val
        return "opencode reported an error event"

    # ── success ──────────────────────────────────────────────────────────────

    def success(self, returncode: int, record: NormalizedRecord) -> bool:
        # opencode exit codes are honest: 0 == success (proven, mcp-agent-bus).
        return returncode == 0
