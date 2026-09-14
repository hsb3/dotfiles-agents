#!/usr/bin/env python3
"""migrate_memory.py — relocate a project's auto-memory after moving the folder.

Project data is keyed to ~/.claude/projects/<slug>/ where slug is the folder's absolute
path with every non-alphanumeric character replaced by '-'. Moving a project on disk
orphans its memory/ dir (and optionally its session transcripts) under the old slug. This
script copies them across, deriving slugs from the old and new paths.

Safe by default: dry-run unless --apply; never overwrites existing files unless --force;
never deletes the source unless --remove-old (and only after the copy is verified).

Usage:
    migrate_memory.py --list                       # show every project dir with memory/
    migrate_memory.py /old/path /new/path          # dry-run preview
    migrate_memory.py /old/path /new/path --apply  # do the copy

Slug rule: re.sub(r'[^A-Za-z0-9]', '-', os.path.abspath(path)).

Stdlib-only (no third-party dependencies); safe to run with a plain python3.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"


def slugify(path: str) -> str:
    """Replace every non-alphanumeric char with '-' — the project-dir slug rule."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def derive_slug(path: str) -> str:
    return slugify(os.path.abspath(os.path.expanduser(path)))


def fuzzy_candidates(path: str) -> list[Path]:
    """Project dirs (with a memory/) whose slug shares the final path component."""
    base = slugify(os.path.basename(os.path.normpath(os.path.expanduser(path))))
    if not base:
        return []
    out = []
    for d in sorted(PROJECTS.glob("*")):
        if (d / "memory").is_dir() and d.name.endswith(base):
            out.append(d)
    return out


def memory_file_count(mem: Path) -> int:
    return sum(1 for p in mem.rglob("*") if p.is_file())


def cmd_list() -> None:
    rows = []
    for d in sorted(PROJECTS.glob("*")):
        mem = d / "memory"
        if not mem.is_dir():
            continue
        has_index = "yes" if (mem / "MEMORY.md").exists() else "no"
        rows.append((d.name, str(memory_file_count(mem)), has_index))
    if not rows:
        print("No project memory dirs found under " + str(PROJECTS))
        return
    slug_w = max(len("Slug"), *(len(r[0]) for r in rows))
    print("Project dirs with a memory/ subdir")
    print(f"  {'Slug'.ljust(slug_w)}  Files  MEMORY.md")
    for slug, files, has_index in rows:
        print(f"  {slug.ljust(slug_w)}  {files:>5}  {has_index}")


def resolve_source(from_path: str | None, from_slug: str | None) -> tuple[str, Path]:
    """Return (slug, memory_dir) for the source, or exit with guidance."""
    if from_slug:
        mem = PROJECTS / from_slug / "memory"
        if not mem.is_dir():
            print(f"No memory/ at {mem}")
            sys.exit(1)
        return from_slug, mem

    assert from_path is not None
    # Try logical abspath, then the symlink-resolved physical path.
    tried = []
    for resolver in (
        lambda p: slugify(os.path.abspath(os.path.expanduser(p))),
        lambda p: slugify(str(Path(p).expanduser().resolve())),
    ):
        slug = resolver(from_path)
        if slug in tried:
            continue
        tried.append(slug)
        mem = PROJECTS / slug / "memory"
        if mem.is_dir():
            return slug, mem

    print(f"No memory/ found for source path {from_path}")
    print(f"Tried slugs: {', '.join(tried)}")
    cands = fuzzy_candidates(from_path)
    if cands:
        print("\nDid you mean one of these? Pass it with --from-slug:")
        for d in cands:
            print(f"  {d.name}  ({memory_file_count(d / 'memory')} files)")
    sys.exit(1)


def transcript_files(slug: str) -> list[Path]:
    """Top-level *.jsonl session transcripts under projects/<slug>/."""
    d = PROJECTS / slug
    return sorted(d.glob("*.jsonl")) if d.is_dir() else []


def human(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if f < 1024 or unit == "GB":
            return f"{int(f)} B" if unit == "B" else f"{f:.1f} {unit}"
        f /= 1024
    return f"{int(n)} B"


def plan_copies(src_files: list[Path], src_root: Path, dst_root: Path, force: bool):
    """Return a list of (action, src, dst) where action is copy | overwrite | skip."""
    plan = []
    for s in src_files:
        rel = s.relative_to(src_root)
        d = dst_root / rel
        if d.exists():
            plan.append(("overwrite" if force else "skip", s, d))
        else:
            plan.append(("copy", s, d))
    return plan


def render_plan(title: str, plan, src_root: Path) -> None:
    label = {"copy": "copy", "overwrite": "overwrite", "skip": "skip (exists)"}
    print(f"\n{title}")
    for action, s, _ in plan:
        rel = str(s.relative_to(src_root))
        print(f"  {label[action]:<14}  {rel}  ({human(s.stat().st_size)})")


def execute(plan) -> tuple[int, int]:
    """Copy per the plan; verify each. Return (copied, skipped)."""
    copied = skipped = 0
    for action, s, d in plan:
        if action == "skip":
            skipped += 1
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        if not d.exists() or d.stat().st_size != s.stat().st_size:
            print(f"Verify FAILED for {d}")
            sys.exit(1)
        copied += 1
    return copied, skipped


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="migrate_memory.py",
        description="Migrate a project's auto-memory after a folder move.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Slug rule: re.sub(r'[^A-Za-z0-9]', '-', abspath(path)).\n"
            "If a derived slug isn't found, the script retries with the symlink-resolved\n"
            "path and lists fuzzy candidates; pass --from-slug to bypass derivation.\n\n"
            "More examples:\n"
            "  migrate_memory.py /old/path /new/path --apply --include-transcripts\n"
            "  migrate_memory.py /old/path /new/path --apply --remove-old\n"
            "  migrate_memory.py --from-slug SLUG --to-slug SLUG --apply"
        ),
    )
    ap.add_argument("from_path", nargs="?", help="Old project folder path")
    ap.add_argument("to_path", nargs="?", help="New project folder path")
    ap.add_argument("--from-slug", help="Use this exact source slug (skip path derivation)")
    ap.add_argument("--to-slug", help="Use this exact dest slug (skip path derivation)")
    ap.add_argument("--apply", action="store_true", help="Actually copy (default: dry-run preview)")
    ap.add_argument("--force", action="store_true", help="Overwrite files that already exist in the destination")
    ap.add_argument("--include-transcripts", action="store_true", help="Also copy *.jsonl session transcripts")
    ap.add_argument(
        "--remove-old",
        action="store_true",
        help="After a verified copy, delete the source memory/ (and transcripts if --include-transcripts)",
    )
    ap.add_argument("--list", action="store_true", help="List every project dir that has a memory/ subdir, then exit")
    if not sys.argv[1:]:
        ap.print_help()
        return
    args = ap.parse_args()

    if args.list:
        cmd_list()
        return

    if not (args.from_slug or args.from_path) or not (args.to_slug or args.to_path):
        ap.error("provide FROM and TO paths (or --from-slug/--to-slug), or use --list")

    src_slug, src_mem = resolve_source(args.from_path, args.from_slug)
    dst_slug = args.to_slug or derive_slug(args.to_path)

    if src_slug == dst_slug:
        print(f"Source and destination slugs are identical ({src_slug}) — nothing to move.")
        sys.exit(1)

    dst_proj = PROJECTS / dst_slug
    dst_mem = dst_proj / "memory"

    print(f"\nSource: {src_mem}")
    print(f"Dest:   {dst_mem}")
    if not dst_proj.exists():
        print("  (destination project dir doesn't exist yet — no session has run there; it will be created)")

    # ---- memory/ ----
    mem_files = sorted(p for p in src_mem.rglob("*") if p.is_file())
    if not mem_files:
        print("Source memory/ is empty — nothing to copy.")
        return
    mem_plan = plan_copies(mem_files, src_mem, dst_mem, args.force)
    render_plan("memory/", mem_plan, src_mem)

    # ---- transcripts (opt-in) ----
    tx_plan = []
    if args.include_transcripts:
        tx_files = transcript_files(src_slug)
        if tx_files:
            tx_plan = plan_copies(tx_files, PROJECTS / src_slug, dst_proj, args.force)
            render_plan("transcripts (*.jsonl)", tx_plan, PROJECTS / src_slug)
        else:
            print("No *.jsonl transcripts at source.")

    skips = sum(1 for a, *_ in (*mem_plan, *tx_plan) if a == "skip")
    if skips and not args.force:
        print(f"{skips} file(s) already exist at the destination and will be SKIPPED. Pass --force to overwrite.")

    if not args.apply:
        print("\nDry run. Add --apply to copy.")
        return

    copied, skipped = execute([*mem_plan, *tx_plan])
    print(f"\nCopied {copied} file(s)" + (f", skipped {skipped} (already present)." if skipped else "."))

    # Verify the index landed before we consider removing anything.
    index_ok = (dst_mem / "MEMORY.md").exists()
    if not index_ok:
        print("Note: no MEMORY.md index at the destination — the source may not have had one.")

    if args.remove_old:
        if not index_ok and (src_mem / "MEMORY.md").exists():
            print("Refusing --remove-old: source had a MEMORY.md but the destination does not. Investigate first.")
            sys.exit(1)
        shutil.rmtree(src_mem)
        print(f"Removed source memory/ {src_mem}")
        if args.include_transcripts:
            for t in transcript_files(src_slug):
                t.unlink()
            print("Removed source *.jsonl transcripts.")

    print("\nDone. Start a session in the new location and confirm the memory index loads.")


if __name__ == "__main__":
    main()
