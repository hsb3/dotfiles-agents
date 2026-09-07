"""Load the tracker snapshot the analysis scripts read (library, not a CLI).

`--snapshot FILE` wins; otherwise the named adapter under `adapters/` is run in
export mode and its stdout parsed. A snapshot that is not contract-shaped is fatal
here rather than silently reading as an empty, therefore "clean", tracker.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ADAPTERS = Path(__file__).resolve().parent / "adapters"


def add_tracker_args(parser, default_status: str = "open") -> None:
    parser.add_argument("--snapshot", help="read this exported snapshot instead of the tracker")
    parser.add_argument("--adapter", default="kata", help="adapter under adapters/ (default: kata)")
    parser.add_argument("--project", help="tracker project (default: the workspace binding)")
    parser.add_argument("--status", choices=("open", "all"), default=default_status)
    return None


def load_snapshot(args) -> dict:
    if args.snapshot:
        try:
            text = Path(args.snapshot).read_text()
        except OSError as err:
            sys.exit(f"{args.snapshot}: unreadable snapshot ({err})")
        return _validate(_parse(text, args.snapshot), args.snapshot)
    adapter = ADAPTERS / f"{args.adapter}.py"
    if not adapter.is_file():
        sys.exit(f"no adapter at {adapter} -- pass --adapter <name> or --snapshot FILE")
    argv = [sys.executable, str(adapter), "export", "--status", args.status]
    argv += ["--project", args.project] if args.project else []
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"{adapter.name} export -> exit {proc.returncode}: {proc.stderr.strip()}")
    return _validate(_parse(proc.stdout, adapter.name), adapter.name)


def _parse(text, source) -> dict:
    """Both paths fail the same way: a notice printed onto stdout, or a truncated
    file, is a sentence naming the source -- never a decoder traceback."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        sys.exit(f"{source}: not JSON ({err})")


def _validate(snapshot, source) -> dict:
    ok = isinstance(snapshot, dict) and isinstance(snapshot.get("tracker"), dict)
    if not ok or not isinstance(snapshot.get("items"), list):
        sys.exit(f"{source}: not a snapshot (need a `tracker` object and an `items` list)")
    return snapshot
