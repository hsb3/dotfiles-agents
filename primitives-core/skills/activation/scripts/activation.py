#!/usr/bin/env python3
"""Write and audit the harness-selected per-project activation file.

Two subcommands:

  create   copy the shipped example to the selected project policy and make sure
           the selected local policy is gitignored.
  check    report, key by key, what the enforcement hooks actually resolve —
           separating "not configured" (fine) from "written but inert" (the silent
           failure this tool exists to surface).

`check` owns **no frontmatter parser**. Every value it prints comes from calling the
hooks' own loader functions, loaded by path, so the report cannot drift from the
behaviour it describes. The one thing the hooks cannot answer is which keys the
operator actually typed — a misspelled key and an absent key look identical to a
loader — so this script locates top-level key *names* and nothing else.

Stdlib only. Exit codes: 0 all clear, 1 something is inert/unknown/ignored,
2 hard error (the hooks could not be found). All output goes to stdout: the
failure report is the report.
"""

import argparse
import difflib
import importlib.util
import os
import json
from pathlib import Path
import subprocess
import shutil
import sys

KEYS = ("enforce", "protected", "protected-branches", "isolate", "handoff",
        "watermark", "effort")
EFFORT_VALUES = ("standard", "deep")

HOOK_NAMES = (
    "worker-context",
    "config-custody",
    "worktree-isolation",
    "session-handoff-surfacer",
    "handoff-freshness-guard",
    "worker-git-scope-guard",
    "context-watermark",
)

EXAMPLE_RELPATH = os.path.join("..", "examples", "atelier.local.md")

EXIT_OK = 0
EXIT_PROBLEM = 1
EXIT_ERROR = 2


# ---------------------------------------------------------------------------
# Finding the hooks
# ---------------------------------------------------------------------------

def _hook_roots():
    """The two candidate `hooks/` directories, in priority order.

    Both supported layouts put the hooks three levels above this script's directory,
    with the same relative shape:

        dev tree   primitives-core/skills/activation/scripts -> primitives-core/hooks
        installed  plugins/<id>/skills/activation/scripts    -> plugins/<id>/hooks

    In the installed bundle both `skills/activation` and `hooks/<name>` are symlinks
    into `primitives-core/`, so the answer differs depending on whether __file__ is
    resolved. Try the UNRESOLVED directory first — that is the bundle's own `hooks/`,
    which is the right answer while its symlinks are intact — then the realpath'd one,
    which lands back in `primitives-core/` and is right when a copy dereferenced the
    symlinks or when the script runs straight out of this tree. A wrong guess here
    would silently audit a different set of hooks than the ones the project runs, so
    a miss on both is a hard error naming both paths, never a fallback parser.
    """
    seen = []
    for base in (os.path.dirname(os.path.abspath(__file__)),
                 os.path.dirname(os.path.realpath(__file__))):
        root = os.path.normpath(os.path.join(base, "..", "..", "..", "hooks"))
        if root not in seen:
            seen.append(root)
    return seen


def load_hooks():
    """Import every hook module that reads the activation file. Returns
    (modules, tried_paths).

    Each gets a unique module name: every hook file is called `hook.py`, and
    colliding names in sys.modules would hand back the wrong module.
    """
    tried = _hook_roots()
    for root in tried:
        paths = {n: os.path.join(root, n, "hook.py") for n in HOOK_NAMES}
        if not all(os.path.isfile(p) for p in paths.values()):
            continue
        modules = {}
        # Bytecode caching off: importing a hook would otherwise write a __pycache__
        # directory into the installed plugin tree. `check` is read-only on the
        # installation it audits.
        saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True
        try:
            for name, path in paths.items():
                mod_name = "atelier_activation_hook_" + name.replace("-", "_")
                spec = importlib.util.spec_from_file_location(mod_name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                modules[name] = module
        finally:
            sys.dont_write_bytecode = saved
        return modules, tried
    return None, tried


# ---------------------------------------------------------------------------
# Key-presence locator — names only, never values
# ---------------------------------------------------------------------------

def frontmatter_region(text):
    """The frontmatter block's lines, or None when the file has no frontmatter.

    The fence rule is the one all five hooks implement, identically: the first
    non-blank line of the file must be exactly `---` (after stripping a BOM), and
    the block ends at the next line whose strip is `---` or `...`. No opening fence
    in that position, or no closing fence, means every hook sees no frontmatter at
    all and ignores the whole file.
    """
    lines = text.splitlines()

    start = None
    for index, line in enumerate(lines):
        stripped = line.lstrip("﻿").strip()
        if not stripped:
            continue
        if stripped == "---":
            start = index + 1
        break  # the first non-blank line must be the opening fence
    if start is None:
        return None

    for index in range(start, len(lines)):
        if lines[index].strip() in ("---", "..."):
            return lines[start:index]
    return None


def top_level_keys(region):
    """The top-level key NAMES in the frontmatter, in order, deduped.

    This is a key-presence locator and nothing else: it reports names and resolves
    no values. Every value in the report comes from the hooks' own loaders. If this
    function ever starts interpreting a value, it has become a sixth parser and the
    report can disagree with the hooks — which is the exact bug the tool reports.

    Skips the same things the hooks skip: blank lines, `#` comments, indented lines
    (a nested mapping under some other key), and `- ` sequence items.
    """
    keys = []
    for line in region:
        item = line.strip()
        if not item or item.startswith("#") or item.startswith("-"):
            continue
        if line[:1].isspace():
            continue
        colon = item.find(":")
        if colon == -1:
            continue
        key = item[:colon].strip().lower()
        if key and key not in keys:
            keys.append(key)
    return keys


def effort_value(region, unquote):
    """`effort:`'s raw value, or "".

    The single value this script reads for itself, and the exception that proves the
    rule above: no hook parses `effort`, so here the checker IS the only reader. Even
    so, `unquote` is the hooks' own `_unquote` rather than a copy of it, and the loop
    runs to the end so a key written twice takes the last value — both so a file that
    reads one way to the hooks reads the same way here.
    """
    value = ""
    for line in region:
        item = line.strip()
        if not item or item.startswith("#") or line[:1].isspace():
            continue
        colon = item.find(":")
        if colon == -1 or item[:colon].strip().lower() != "effort":
            continue
        value = unquote(item[colon + 1:])
    return value


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _row(key, state, detail, sources):
    return {"key": key, "state": state, "detail": detail, "sources": sources}


def _agree(results):
    """results: {hook_name: value}. Returns (value, None) or (None, message).

    Two hooks read `enforce` and two read `handoff`, each with its own parser. They
    should never differ; if they do, that is a defect in the hooks and the operator
    needs to hear it rather than see one arbitrary winner.
    """
    values = list(results.values())
    if all(value == values[0] for value in values):
        return values[0], None
    detail = "; ".join("{0}={1!r}".format(k, v) for k, v in sorted(results.items()))
    return None, detail


def evaluate(project_dir, modules):
    """Resolve every key. Returns a dict the renderer turns into a report."""
    worker, custody, isolation = (
        modules["worker-context"], modules["config-custody"], modules["worktree-isolation"])
    surfacer, freshness = (
        modules["session-handoff-surfacer"], modules["handoff-freshness-guard"])
    scope_guard = modules["worker-git-scope-guard"]
    watermark = modules["context-watermark"]

    # The hooks all resolve the activation path the same way (ATELIER_ACTIVATION_FILE
    # first, then harness-local / legacy / inherited policy), so ask one of them rather
    # than recomputing it: this line is ground truth about which file is in play.
    path = worker._resolve_activation_path(project_dir)

    result = {"path": path, "rows": [], "warnings": [], "problems": []}

    try:
        size = os.path.getsize(path)
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        result["exists"] = False
        if os.environ.get("ATELIER_ACTIVATION_FILE") or os.path.lexists(path):
            result["problems"].append("selected activation file is unreadable or missing: " + str(exc))
        return result
    result["exists"] = True

    # Every hook bails to its inert default above this size, before it parses a byte.
    # Read the cap off a hook rather than restating it, so a change there moves this.
    cap = worker.ACTIVATION_MAX_BYTES
    if size > cap:
        result["region"] = False
        result["problems"].append(
            "too large: {0} bytes, over the {1}-byte cap every hook applies before it "
            "parses anything. Nothing in the file is live until it shrinks - the keys "
            "themselves are not the problem.".format(size, cap))
        return result

    region = frontmatter_region(text)
    if region is None:
        result["region"] = False
        result["problems"].append(
            "no frontmatter: the first non-blank line is not `---`, or the block is "
            "never closed. Every hook ignores this entire file. Fix: make the first "
            "non-blank line exactly `---`, and close the block with `---`.")
        return result
    result["region"] = True

    present = top_level_keys(region)

    # -- enforce (two hooks) ------------------------------------------------
    enforce_by_hook = {
        "worker-context": worker._load_mode(project_dir),
        "config-custody": custody._load_activation(project_dir)[0],
    }
    enforce, enforce_clash = _agree(enforce_by_hook)
    enforce_sources = sorted(enforce_by_hook)

    if enforce_clash:
        result["rows"].append(_row("enforce", "DISAGREEMENT", enforce_clash, enforce_sources))
    elif "enforce" not in present:
        result["rows"].append(_row("enforce", "not configured", "", enforce_sources))
    elif enforce == "off":
        result["rows"].append(_row(
            "enforce", "inert",
            "written, but both hooks read it as off - the value is not one of "
            "advisory/strict", enforce_sources))
    else:
        result["rows"].append(_row("enforce", "armed", enforce, enforce_sources))

    # -- protected (config-custody; independent of enforce) -----------------
    patterns = custody._load_activation(project_dir)[1]
    if "protected" not in present:
        result["rows"].append(_row("protected", "not configured", "", ["config-custody"]))
    elif not patterns:
        result["rows"].append(_row(
            "protected", "inert",
            "written, but no patterns were parsed - an empty list, or a scalar "
            "where a sequence belongs", ["config-custody"]))
    elif enforce in (None, "off"):
        result["rows"].append(_row(
            "protected", "inert",
            "{0} pattern(s) parsed ({1}) but never consulted: enforce is off".format(
                len(patterns), ", ".join(patterns)), ["config-custody"]))
    else:
        result["rows"].append(_row(
            "protected", "armed", ", ".join(patterns), ["config-custody"]))

    # -- protected-branches (worker-git-scope-guard; independent of enforce) -
    # A DIFFERENT key from `protected` above: branch names, not file paths. Its hook
    # never reads `enforce`, so unlike `protected` there is no armed-but-never-consulted
    # state to report - written and parsed means live.
    branches = sorted(scope_guard._load_protected_branches(project_dir))
    if "protected-branches" not in present:
        result["rows"].append(_row(
            "protected-branches", "not configured",
            "the stash half of this hook is live regardless; only the "
            "protected-branch half needs this key", ["worker-git-scope-guard"]))
    elif not branches:
        result["rows"].append(_row(
            "protected-branches", "inert",
            "written, but no branch names were parsed - an empty list, or a scalar "
            "where a sequence belongs", ["worker-git-scope-guard"]))
    else:
        result["rows"].append(_row(
            "protected-branches", "armed", ", ".join(branches),
            ["worker-git-scope-guard"]))

    # -- isolate (worktree-isolation) ---------------------------------------
    isolate_mode, isolate_types = isolation._load_activation(project_dir)
    if "isolate" not in present:
        result["rows"].append(_row("isolate", "not configured", "", ["worktree-isolation"]))
    elif isolate_mode == "off":
        result["rows"].append(_row(
            "isolate", "inert",
            "written, but read as off - not `writers` and not a non-empty list of "
            "agent types", ["worktree-isolation"]))
    else:
        result["rows"].append(_row(
            "isolate", "armed",
            "{0} -> {1}".format(isolate_mode, ", ".join(isolate_types)),
            ["worktree-isolation"]))

    # -- handoff (two hooks; config, then the hooks' own path validation) ----
    handoff_sources = ["handoff-freshness-guard", "session-handoff-surfacer"]
    raw_by_hook = {
        "session-handoff-surfacer": surfacer._load_handoff_config(project_dir),
        "handoff-freshness-guard": freshness._load_handoff_config(project_dir),
    }
    raw, raw_clash = _agree(raw_by_hook)
    mode = (raw or {}).get("mode")
    # Which value has to survive path validation depends on the mode: the handoff
    # file in file mode, the freshness stamp in external mode. Ask each hook for
    # its own answer - the loader alone does not say whether the value survived,
    # since a path escaping the project root is silently rejected by both.
    key = "stamp" if mode == "external" else "path"
    resolved_by_hook = {
        name: module._resolve_override_path((raw_by_hook[name] or {}).get(key), project_dir)
        for name, module in (("session-handoff-surfacer", surfacer),
                             ("handoff-freshness-guard", freshness))
    }
    resolved, resolved_clash = _agree(resolved_by_hook)

    if raw_clash or resolved_clash:
        result["rows"].append(_row(
            "handoff", "DISAGREEMENT", raw_clash or resolved_clash, handoff_sources))
    elif "handoff" not in present:
        result["rows"].append(_row("handoff", "not configured", "", handoff_sources))
    elif not raw:
        result["rows"].append(_row(
            "handoff", "inert", "written, but blank - both hooks read no value",
            handoff_sources))
    elif mode not in ("file", "external"):
        result["rows"].append(_row(
            "handoff", "inert",
            "unrecognised mode {0!r} - expected `file` or `external`, so both hooks "
            "ignore the key and fall back to the standard search".format(mode),
            handoff_sources))
    elif not (raw or {}).get(key):
        # No value written at all is a different mistake from a value that was
        # written and then rejected, and the operator fixes them differently:
        # one line to add versus one line to move inside the root.
        result["rows"].append(_row(
            "handoff", "inert",
            "{0} mode, but no `{1}:` - the key names nowhere to look, so both hooks "
            "fall back to the standard search".format(mode, key), handoff_sources))
    elif resolved is None and mode == "external":
        result["rows"].append(_row(
            "handoff", "inert",
            "external mode `stamp` resolves outside the project root, so both hooks "
            "reject it and fall back to the standard search", handoff_sources))
    elif resolved is None:
        result["rows"].append(_row(
            "handoff", "inert",
            "resolves outside the project root, so both hooks reject it and fall "
            "back to the standard search", handoff_sources))
    elif mode == "external":
        where = raw["location"] or "no location set"
        result["rows"].append(_row(
            "handoff", "armed",
            "external - stamp {0}, handoff lives at: {1}".format(resolved, where),
            handoff_sources))
        if not os.path.isfile(resolved):
            result["warnings"].append(
                "handoff: that stamp file does not exist yet, so the freshness guard "
                "reads it as no handoff at all and blocks a manual /compact. The "
                "surfacer still points a cold session at the location. Touch the stamp "
                "whenever the handoff is updated.")
    else:
        result["rows"].append(_row("handoff", "armed", resolved, handoff_sources))
        if not os.path.isfile(resolved):
            result["warnings"].append(
                "handoff: that file does not exist yet. This is still live: the hooks "
                "do NOT fall back to the standard search when an override is set, they "
                "report no handoff at all. Create the file or drop the key.")

    # -- watermark (context-watermark; every sub-key optional) --------------
    # Absent sub-keys are not a defect: each one that is missing or unusable
    # leaves that tier computed from the model's window, which is the shipped
    # behaviour. Only a key written with nothing readable under it is inert.
    thresholds = watermark._load_watermark_config(project_dir)
    if "watermark" not in present:
        result["rows"].append(_row("watermark", "not configured", "", ["context-watermark"]))
    elif not thresholds:
        result["rows"].append(_row(
            "watermark", "inert",
            "written, but no usable soft/hard/complexity value - the sub-keys are "
            "missing, blank, or not positive numbers, so every tier stays computed",
            ["context-watermark"]))
    else:
        result["rows"].append(_row(
            "watermark", "armed",
            ", ".join("{0}={1}".format(k, thresholds[k])
                      for k in ("soft", "hard", "complexity") if k in thresholds),
            ["context-watermark"]))

    # -- effort (no hook) ---------------------------------------------------
    effort = effort_value(region, worker._unquote)
    if "effort" not in present:
        result["rows"].append(_row("effort", "not configured", "", ["no hook"]))
    elif effort.lower() in EFFORT_VALUES:
        result["rows"].append(_row("effort", "prose-only", effort.lower(), ["no hook"]))
    else:
        result["rows"].append(_row(
            "effort", "inert",
            "unrecognised value {0!r} - expected one of {1}".format(
                effort, "/".join(EFFORT_VALUES)), ["no hook"]))

    # -- anything else in the block -----------------------------------------
    for key in present:
        if key in KEYS:
            continue
        near = difflib.get_close_matches(key, KEYS, n=1)
        detail = "unknown key - no hook reads it, so it does nothing"
        if near:
            detail += "; did you mean `{0}`?".format(near[0])
        result["rows"].append(_row(key, "inert", detail, ["no hook"]))

    return result


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

BAD_STATES = ("inert", "DISAGREEMENT")


def render(result, out):
    print("activation file  {0}".format(result["path"]), file=out)
    print("", file=out)

    if not result.get("exists"):
        if result["problems"]:
            print("ERROR  " + "; ".join(result["problems"]), file=out)
            return EXIT_PROBLEM
        print("not configured - no activation file here, so every key is off and no "
              "hook acts.", file=out)
        return EXIT_OK

    if not result.get("region"):
        for problem in result["problems"]:
            print("IGNORED  {0}".format(problem), file=out)
        print("", file=out)
        print("FAIL  the file is present but every hook skips it, so nothing written "
              "in it is live.", file=out)
        return EXIT_PROBLEM

    rows = result["rows"]
    key_width = max(len(r["key"]) for r in rows)
    state_width = max(len(r["state"]) for r in rows)
    for r in rows:
        line = "  {0}  {1}  {2}".format(
            r["key"].ljust(key_width), r["state"].ljust(state_width), r["detail"]).rstrip()
        print("{0}  [{1}]".format(line, ", ".join(r["sources"])), file=out)

    for warning in result["warnings"]:
        print("", file=out)
        print("WARN  {0}".format(warning), file=out)

    counts = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    summary = ", ".join("{0} {1}".format(counts[s], s) for s in sorted(counts))

    print("", file=out)
    if any(r["state"] in BAD_STATES for r in rows):
        print("FAIL  {0}. An inert key is written but does nothing - fix it or delete "
              "it.".format(summary), file=out)
        return EXIT_PROBLEM
    print("OK  {0}. `prose-only` means no hook enforces it; the delegation skill "
          "honours it when an agent reads the file.".format(summary), file=out)
    return EXIT_OK


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_check(project_dir, out):
    modules, tried = load_hooks()
    if modules is None:
        print("ERROR  cannot find the atelier hooks - refusing to guess at the values.",
              file=out)
        for root in tried:
            print("       tried  {0}".format(root), file=out)
        return EXIT_ERROR
    local = modules["worker-context"].atelier_local
    moves = reconcile_policy(project_dir, local, check=True)
    if moves:
        print("NEEDS  policy migration: " + ", ".join(moves), file=out)
        return EXIT_PROBLEM
    return render(evaluate(project_dir, modules), out)


def reconcile_policy(project_dir, local, check=False):
    """Coalesce identical old locations into the configured canonical location.

    This is deliberately byte-oriented: a setup tool may relocate a policy but never
    reinterpret it.  Every extant location is read before the first write, so a
    divergent duplicate leaves the project untouched, including with --force.
    """
    paths = [Path(path) for path in local.policy_paths(project_dir) if os.path.lexists(path)]
    if not paths:
        return []
    contents = []
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError("refusing non-regular policy: " + str(path))
        contents.append(path.read_bytes())
    if any(data != contents[0] for data in contents[1:]):
        raise ValueError("divergent activation policies; resolve them before setup")
    target = Path(local.activation_destination(project_dir))
    stale = [path for path in paths if path != target]
    if not stale:
        return []
    moves = [str(path) for path in stale]
    if check:
        return moves
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(contents[0])
    for path in stale:
        path.unlink()
    return moves


def _ensure_gitignore(project_dir, out, dest):
    """Ignore the selected per-machine, per-project policy."""
    relpath = os.path.relpath(dest, project_dir).replace(os.sep, "/")
    if relpath.startswith("../"):
        print("note   activation is outside this project; no ignore rule added", file=out)
        return
    pattern = relpath.rsplit("/", 1)[0] + "/*.local.md" if relpath in (
        ".claude/atelier.local.md", ".codex/atelier.local.md") else relpath
    equivalents = (pattern, "*.local.md", pattern + "/")
    path = os.path.join(project_dir, ".gitignore")
    if not os.path.isfile(path):
        print("note   no .gitignore here, so nothing was changed - ignore "
              "{0} however this project does it.".format(pattern), file=out)
        return
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if any(line.strip() in equivalents for line in text.splitlines()):
        print("ok     .gitignore already ignores it", file=out)
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(("" if text.endswith("\n") or not text else "\n")
                 + "\n# atelier per-project activation - local, never committed\n"
                 + pattern + "\n")
    print("wrote  {0} appended to {1}".format(pattern, path), file=out)


def cmd_create(project_dir, force, out):
    example = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), EXAMPLE_RELPATH))
    if not os.path.isfile(example):
        print("ERROR  the shipped example is missing: {0}".format(example), file=out)
        return EXIT_ERROR

    modules, tried = load_hooks()
    if modules is None:
        print("ERROR  cannot find the atelier hooks: " + ", ".join(tried), file=out)
        return EXIT_ERROR
    local = modules["worker-context"].atelier_local
    moved = reconcile_policy(project_dir, local)
    dest = local.activation_destination(project_dir)
    if moved:
        print("moved  activation policy to {0}".format(dest), file=out)
        return EXIT_OK
    if os.path.lexists(dest) and not force:
        print("refused  {0} already exists - not overwriting it.".format(dest), file=out)
        print("         Re-run with --force to replace it, or edit it in place.", file=out)
        return EXIT_PROBLEM

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(example, dest)
    print("wrote  {0}".format(dest), file=out)
    _ensure_gitignore(project_dir, out, dest)
    harness = os.environ.get("ATELIER_HARNESS", "claude-code")
    if harness == "codex":
        text = Path(dest).read_text()
        text = text.replace('"${CLAUDE_PLUGIN_ROOT}/skills/activation/scripts/activation.py" check',
                            '"' + os.path.abspath(__file__) + '" check --harness codex')
        Path(dest).write_text(text)
    print("next   python3 {0} check --harness {1}".format(os.path.abspath(__file__), harness), file=out)
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def codex_setup(project_dir, out, check=False):
    """Generate local roles and the narrow writable-root addition; never approve hooks."""
    roots = _hook_roots()
    sys.path.insert(0, os.path.join(roots[0], "_lib"))
    try:
        import codex_roles
        import codex_workers
        import tomllib
        # Read every existing policy before setup creates .codex and changes the
        # configured-agent set. A conflict must leave roles and config untouched.
        reconcile_policy(project_dir, __import__("atelier_local"), check=True)
        common = subprocess.check_output(
            ["git", "-C", project_dir, "rev-parse", "--git-common-dir"],
            text=True, env=codex_workers.clean_git_env()).strip()
        common = (Path(project_dir) / common).resolve()
        writable = [str(common / path) for path in
                    ("atelier-codex/checkouts", "worktrees", "objects", "refs/heads/atelier", "logs/refs/heads/atelier")]
        config = Path(project_dir) / ".codex/config.toml"
        exclude = common / "info/exclude"
        for path in (config.parent, common / "info"):
            if path.is_symlink() or path.exists() and not path.is_dir():
                raise ValueError("Refusing non-directory or symlink setup directory: " + str(path))
        for path in (config, exclude):
            if path.is_symlink() or path.exists() and not path.is_file():
                raise ValueError("Refusing non-regular or symlink setup file: " + str(path))
        text = config.read_text() if config.exists() else ""
        parsed = tomllib.loads(text)
        existing = parsed.get("sandbox_workspace_write", {})
        configured = existing.get("writable_roots", [])
        missing = [path for path in writable if path not in configured]
        agents = parsed.get("agents")
        agent_settings = []
        if agents is not None:
            if not isinstance(agents, dict):
                raise ValueError("agents must be a TOML table")
            depth = agents.get("max_depth", 1)
            if not isinstance(depth, int) or isinstance(depth, bool) or depth < 2:
                agent_settings.append("max_depth = 2")
            if agents.get("enabled") is False:
                agent_settings.append("enabled = true")
            concurrency = agents.get("max_concurrent_threads_per_session")
            if isinstance(concurrency, int) and concurrency < 2:
                agent_settings.append("max_concurrent_threads_per_session = 2")
        if agent_settings:
            print("ERROR  existing agents table is user-owned; set these entries under [agents]: "
                  + "; ".join(agent_settings), file=out)
            return EXIT_PROBLEM
        marker = "# atelier managed writable roots\n"
        if missing and "sandbox_workspace_write" in parsed:
            print("ERROR  existing sandbox_workspace_write table is user-owned; add these writable_roots: "
                  + json.dumps(missing), file=out)
            return EXIT_PROBLEM
        codex_roles.setup(project_dir, check=True)
        additions = []
        if missing:
            additions.append(marker + "[sandbox_workspace_write]\nwritable_roots = " + json.dumps(writable))
        if agents is None:
            additions.append("[agents]\nmax_depth = 2")
        if additions and not check:
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(text.rstrip() + "\n\n" + "\n\n".join(additions) + "\n")
        changed = codex_roles.setup(project_dir, check=check)
        moved = reconcile_policy(project_dir, __import__("atelier_local"), check=check)
        print(("needs " if check and changed else "ok    ") + " Codex roles: "
              + (", ".join(str(path) for path in changed) if changed else "current"), file=out)
        print(("needs " if check and missing else "ok    ") + " Codex writable roots: "
              + json.dumps(writable), file=out)
        print(("needs " if check and agents is None else "ok    ")
              + " Codex manager depth: agents.max_depth = "
              + str(2 if agents is None else agents["max_depth"]), file=out)
        if moved:
            print(("needs " if check else "moved ") + " activation policy: "
                  + ", ".join(moved), file=out)
        if moved and not check:
            reconcile_policy(project_dir, __import__("atelier_local"))
        if not check:
            exclude.parent.mkdir(parents=True, exist_ok=True)
            old = exclude.read_text() if exclude.exists() else ""
            additions = [line for line in ("/.codex/agents/atelier-*.toml", "/.codex/config.toml")
                         if line not in old.splitlines()]
            if additions:
                exclude.write_text(old.rstrip() + "\n" + "\n".join(additions) + "\n")
        print("unverified  hook trust: open /hooks in Codex for this project and approve the reviewed atelier hooks. "
              "Parsed activation settings alone do not prove loaded, enabled, trusted hooks. Restart after setup.", file=out)
        return EXIT_PROBLEM if check and (changed or missing or agents is None or moved) else EXIT_OK
    except (OSError, ValueError, subprocess.SubprocessError, ImportError) as exc:
        print("ERROR  Codex setup: " + str(exc), file=out)
        return EXIT_ERROR


def _project_dir(value):
    return os.path.abspath(value or (os.environ.get("CLAUDE_PROJECT_DIR") if os.environ.get("ATELIER_HARNESS") != "codex" else None) or os.getcwd())


def main(argv=None, out=None):
    out = out or sys.stdout
    parser = argparse.ArgumentParser(
        prog="activation.py",
        description="Write and audit the harness-selected per-project "
                    "activation file for the atelier plugin.")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser(
        "create", help="copy the shipped example to the selected project policy and "
                       "gitignore it")
    create.add_argument("--force", action="store_true",
                        help="overwrite an existing activation file")

    check = sub.add_parser(
        "check", help="report what each key actually resolves to: armed, inert, or "
                      "not configured")

    setup = sub.add_parser("codex-setup", help="generate project-local Codex roles and writable roots")
    for p in (create, check, setup):
        p.add_argument("--harness", choices=("claude-code", "codex"),
                       default=os.environ.get("ATELIER_HARNESS") or ("codex" if os.environ.get("CODEX_THREAD_ID") else "claude-code"))
        p.add_argument("--project-dir", default=None,
                       help="project root (default: $CLAUDE_PROJECT_DIR, else cwd)")

    args = parser.parse_args(argv)
    os.environ["ATELIER_HARNESS"] = "codex" if args.command == "codex-setup" else args.harness
    project_dir = _project_dir(args.project_dir)
    if args.command == "codex-setup":
        return codex_setup(project_dir, out)
    if args.command == "create":
        return cmd_create(project_dir, args.force, out)
    if args.harness == "codex":
        print("Codex parsed policy only; runtime hook trust is checked separately below.", file=out)
    code = cmd_check(project_dir, out)
    if args.harness == "codex":
        code = max(code, codex_setup(project_dir, out, check=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
