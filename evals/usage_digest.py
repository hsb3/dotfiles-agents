#!/usr/bin/env python3
"""Read-only, replay-safe digest for local Codex usage JSONL streams."""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


TOKEN_KEYS = ("input", "cached_input", "output", "reasoning", "total")
SAFE_FIELDS = {"schema", "schema_version", "kind", "counter_state", "observation_id",
               "segment", "lifecycle_id", "native_id", "parent_id", "role", "model",
               "effort", "requested_model", "requested_tier", "host", "source_repo",
               "effective_cwd", "started_at", "timing", "tokens", "cumulative_tokens"}


def _clean(value):
    return value if isinstance(value, str) and value else "unknown"


def _tokens(value):
    if not isinstance(value, dict) or set(value) != set(TOKEN_KEYS):
        return None
    if any(not isinstance(value[key], int) or isinstance(value[key], bool) or value[key] < 0
           for key in TOKEN_KEYS):
        return None
    if value["cached_input"] > value["input"] or value["reasoning"] > value["output"]:
        return None
    if value["total"] != value["input"] + value["output"]:
        return None
    return value


def _canonical(row):
    """Append timestamps do not make an observation different."""
    return json.dumps({key: value for key, value in row.items() if key not in {"ts", "timestamp", "appended_at"}},
                      sort_keys=True, separators=(",", ":"))


def _read(paths):
    rows, errors = [], Counter()
    for path in paths:
        try:
            with open(path, encoding="utf-8") as stream:
                for line in stream:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        errors["malformed-json"] += 1
                        continue
                    if not isinstance(row, dict):
                        errors["malformed-row"] += 1
                    else:
                        rows.append(row)
        except OSError:
            errors["unreadable-input"] += 1
    return rows, errors


def digest(paths):
    rows, errors = _read(paths)
    seen, states, missing = {}, Counter(), Counter()
    groups = {name: defaultdict(lambda: {key: 0 for key in TOKEN_KEYS})
              for name in ("model", "role", "root_child", "host", "source_repo")}
    totals = {key: 0 for key in TOKEN_KEYS}
    lifetimes, observed, legacy = {}, 0, 0
    for row in rows:
        if row.get("schema") != "codex-usage":
            legacy += 1
            continue
        version = row.get("schema_version")
        if not isinstance(version, int) or isinstance(version, bool) or version > 2:
            errors["unsupported-future-schema"] += 1
            continue
        if version != 2 or row.get("kind") != "delta" or not isinstance(row.get("observation_id"), str):
            errors["unsupported-schema"] += 1
            continue
        identity, content = row["observation_id"], _canonical(row)
        prior = seen.get(identity)
        if prior is not None:
            if prior != content:
                errors["conflicting-observation-id"] += 1
            continue
        seen[identity] = content
        state = row.get("counter_state")
        if not isinstance(state, str):
            errors["missing-counter-state"] += 1
            continue
        states[state] += 1
        if state != "observed":
            continue
        tokens = _tokens(row.get("tokens"))
        if tokens is None:
            errors["invalid-tokens"] += 1
            continue
        observed += 1
        dimensions = {name: _clean(row.get(name)) for name in ("model", "role", "host", "source_repo")}
        for name, value in dimensions.items():
            if value == "unknown":
                missing[name] += 1
        root, native = _clean(row.get("parent_id") or row.get("native_id")), _clean(row.get("native_id"))
        dimensions["root_child"] = root + "/" + native
        for key, value in tokens.items():
            totals[key] += value
            for name, group in dimensions.items():
                groups[name][group][key] += value
        lifecycle = _clean(row.get("lifecycle_id") or row.get("native_id"))
        timing = row.get("timing") if isinstance(row.get("timing"), dict) else {}
        lifetime = timing.get("lifetime_ms")
        if isinstance(lifetime, int) and not isinstance(lifetime, bool) and lifetime >= 0:
            lifetimes[lifecycle] = max(lifetimes.get(lifecycle, 0), lifetime)
        else:
            missing["lifetime_ms"] += 1
    return {"observed": observed, "legacy_unknown": legacy, "tokens": totals,
            "groups": {name: dict(sorted(values.items())) for name, values in groups.items()},
            "lifetime_ms_by_lifecycle": dict(sorted(lifetimes.items())),
            "coverage": {"states": dict(sorted(states.items())), "missing": dict(sorted(missing.items())),
                         "errors": dict(sorted(errors.items()))}}


def export(paths, host, output):
    rows, _ = _read(paths)
    safe = []
    for row in rows:
        if row.get("schema") == "codex-usage" and row.get("schema_version") == 2 and row.get("host") == host:
            safe.append({key: row[key] for key in sorted(SAFE_FIELDS & row.keys())})
    Path(output).write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in safe),
                            encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("report", "export"):
        command = commands.add_parser(name)
        command.add_argument("--input", action="append", required=True, type=Path)
        command.add_argument("--output", type=Path, required=name == "export")
        if name == "export":
            command.add_argument("--host", required=True)
    args = parser.parse_args(argv)
    if args.command == "export":
        export(args.input, args.host, args.output)
        return 0
    result = json.dumps(digest(args.input), sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
