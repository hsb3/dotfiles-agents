#!/usr/bin/env python3
"""project_memory.py — give a git repo its own tracked, transferable auto-memory.

Replaces the hidden machine-local default (~/.claude/projects/<slug>/memory/) with an
in-repo .claude/memory/ that travels via git, so a project's learnings move with the
repo across machines and clones.

Two-layer model: global/user memory stays at ~/.claude/memory/ (curated, machine-wide);
project memory lives in each repo's tracked .claude/memory/ and is opted in per repo by
writing autoMemoryDirectory into that repo's .claude/settings.local.json (default) or the
tracked .claude/settings.json (with --portable).

Usage:
    project_memory.py init                       # wire in-repo memory for the current repo
    project_memory.py init --portable --migrate  # portable path + migrate hidden native dir
    project_memory.py status                     # show how the current repo is configured
    project_memory.py list                       # hidden native dirs (migration candidates)

After init, accept the workspace-trust dialog for the folder and commit .claude/memory/.

Stdlib-only (no third-party dependencies); safe to run with a plain python3.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

GITIGNORE_BEGIN = "# >>> project-memory (managed) >>>"
GITIGNORE_END = "# <<< project-memory (managed) <<<"
GITIGNORE_BLOCK = f"""{GITIGNORE_BEGIN}
# narrow-ignore: ignore only machine-local/transient; track everything else under .claude/
# (memory/, rules/, settings.json stay tracked & transferable)
.claude/settings.local.json
.claude/worktrees/
.claude/*.lock
.claude/**/.DS_Store
{GITIGNORE_END}
"""

MEMORY_STUB = """<!-- Project auto-memory index for {repo}. Tracked in this repo so learnings travel
across machines and can be mined for global patterns. Memory is written here automatically;
edit or prune freely. Global/user memory lives separately in ~/.claude/memory/ (curated).
Keep this file an index: one line per memory file. First 200 lines load every session. -->

# Project memory — {repo}

_One line per memory file:_ `- [Title](file.md) — short hook`
"""


def fail(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def repo_root() -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        fail("not inside a git repository (cd into one, then run `init`).")
    return Path(out.stdout.strip()).resolve()


def project_slug(path: Path) -> str:
    """The mangling of an absolute path -> ~/.claude/projects/<slug>/ name.

    Rule (shared with migrate_memory.py): non-alphanumerics -> '-'.
    """
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def native_memory_dir(root: Path) -> Path:
    return Path.home() / ".claude" / "projects" / project_slug(root) / "memory"


def settings_path(root: Path, *, local: bool) -> Path:
    name = "settings.local.json" if local else "settings.json"
    return root / ".claude" / name


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text() or "{}")
    except json.JSONDecodeError as e:
        fail(f"{path} is not valid JSON: {e}")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def configured_dir(root: Path) -> tuple[str, str] | None:
    """Return (scope, raw_value) of an autoMemoryDirectory set in this repo, if any.

    Local settings win over project settings (settings precedence).
    """
    for scope, local in (("local", True), ("project", False)):
        data = read_json(settings_path(root, local=local))
        val = data.get("autoMemoryDirectory")
        if val:
            return scope, val
    return None


def expand(raw: str) -> Path:
    return Path(os.path.expanduser(raw)).resolve()


def ensure_gitignore(root: Path) -> bool:
    gi = root / ".gitignore"
    text = gi.read_text() if gi.exists() else ""
    # Match on the marker suffix so blocks written by earlier tool names (whose
    # begin marker ends with the same suffix) are recognized and never duplicated.
    if "project-memory (managed) >>>" in text:
        return False
    sep = "" if text.endswith("\n") or text == "" else "\n"
    gi.write_text(text + sep + ("\n" if text else "") + GITIGNORE_BLOCK)
    return True


def cmd_init(args: argparse.Namespace) -> int:
    root = repo_root()
    mem = root / ".claude" / "memory"
    mem.mkdir(parents=True, exist_ok=True)

    created_stub = False
    memory_md = mem / "MEMORY.md"
    if not memory_md.exists():
        memory_md.write_text(MEMORY_STUB.format(repo=root.name))
        created_stub = True

    # Choose where/how to record autoMemoryDirectory.
    home = Path.home().resolve()
    if args.portable:
        try:
            rel = mem.relative_to(home)
        except ValueError:
            fail(
                f"--portable needs the repo under your home dir; {root} is not. "
                "Re-run without --portable to use a machine-local absolute path."
            )
        value = f"~/{rel}"
        target = settings_path(root, local=False)
        scope_note = "tracked .claude/settings.json (portable ~/-relative path)"
    else:
        value = str(mem)
        target = settings_path(root, local=True)
        scope_note = "machine-local .claude/settings.local.json (absolute path)"

    data = read_json(target)
    prev = data.get("autoMemoryDirectory")
    data["autoMemoryDirectory"] = value
    write_json(target, data)

    gi_changed = ensure_gitignore(root)

    migrated = 0
    native = native_memory_dir(root)
    if args.migrate and native.exists():
        for f in sorted(native.glob("*.md")):
            dest = mem / f.name
            if dest.exists():
                print(f"  skip {f.name} (already in repo)")
                continue
            shutil.copy2(f, dest)
            migrated += 1

    # Report.
    print(f"[ok] project memory wired for {root.name}")
    print(f"  memory dir : {mem}" + ("  (new MEMORY.md stub)" if created_stub else ""))
    print(f"  setting    : autoMemoryDirectory = {value}")
    print(f"  written to : {scope_note}")
    if prev and prev != value:
        print(f"  replaced previous value: {prev}")
    if gi_changed:
        print("  .gitignore : added managed block (memory tracked, settings.local ignored)")
    if args.migrate:
        if native.exists():
            print(f"  migrated   : {migrated} file(s) from hidden native dir {native}")
        else:
            print(f"  migrate    : no hidden native dir at {native}")
    elif native.exists() and list(native.glob("*.md")):
        print(f"  note: a hidden native memory dir exists at {native}")
        print("        re-run with --migrate to copy its files into the repo.")

    print()
    print("next:")
    print("  * accept the workspace-trust dialog for this folder so the setting is honored")
    if not args.portable:
        print("  * on another machine, re-run `init` to recreate the local path")
    commit_targets = ".claude/memory .gitignore"
    if args.portable:
        commit_targets += " .claude/settings.json"
    print(f"  * commit the memory dir:  git add {commit_targets}")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    root = repo_root()
    mem = root / ".claude" / "memory"
    print(f"{root.name}  {root}")

    cfg = configured_dir(root)
    if cfg:
        scope, raw = cfg
        resolved = expand(raw)
        ok = resolved == mem.resolve()
        mark = "-> in-repo" if ok else "-> elsewhere"
        print(f"  autoMemoryDirectory : {raw}  ({scope} settings)  {mark}")
    else:
        print("  autoMemoryDirectory : not set — using hidden native default")
        print(f"                        {native_memory_dir(root)}")

    if mem.exists():
        files = sorted(p.name for p in mem.glob("*.md"))
        idx = "MEMORY.md" if (mem / "MEMORY.md").exists() else "no MEMORY.md"
        topics = [f for f in files if f != "MEMORY.md"]
        print(f"  in-repo memory dir  : exists — index {idx}, {len(topics)} topic file(s)")
    else:
        print("  in-repo memory dir  : none (run `init`)")

    native = native_memory_dir(root)
    if native.exists() and list(native.glob("*.md")):
        n = len(list(native.glob("*.md")))
        print(f"  hidden native dir   : {n} file(s) at {native} (migration candidate)")
    return 0


def cmd_path(_: argparse.Namespace) -> int:
    root = repo_root()
    cfg = configured_dir(root)
    if cfg:
        print(str(expand(cfg[1])))
    else:
        print(str(native_memory_dir(root)))
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        print("no ~/.claude/projects directory")
        return 0
    found = []
    for proj in sorted(base.iterdir()):
        mem = proj / "memory"
        if mem.is_dir() and list(mem.glob("*.md")):
            n = len(list(mem.glob("*.md")))
            guess = "/" + proj.name.strip("-").replace("-", "/")  # best-effort de-mangle
            found.append((proj.name, n, mem, guess))
    if not found:
        print("no hidden native memory dirs with files")
        return 0
    print("Hidden native memory dirs (migrate into a repo with `init --migrate`):\n")
    for slug, n, mem, guess in found:
        print(f"  {n:>2} file(s)  {mem}")
        print(f"           ~ {guess}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="project_memory.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd")

    pi = sub.add_parser("init", help="set up tracked project memory in the current repo")
    pi.add_argument(
        "--portable",
        action="store_true",
        help="write a ~/-relative path to tracked settings.json instead of an absolute path to "
        "settings.local.json (imposes the path on anyone who clones — prefer for personal repos only)",
    )
    pi.add_argument(
        "--migrate",
        action="store_true",
        help="copy files from a hidden native memory dir into the repo",
    )
    pi.set_defaults(func=cmd_init)

    sub.add_parser("status", help="show how the current repo's memory is configured").set_defaults(func=cmd_status)
    sub.add_parser("path", help="print the resolved memory dir for this repo").set_defaults(func=cmd_path)
    sub.add_parser("list", help="hidden native memory dirs that exist (migration candidates)").set_defaults(func=cmd_list)

    args = p.parse_args()
    if not getattr(args, "func", None):
        p.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
