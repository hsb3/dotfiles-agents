#!/usr/bin/env python3
"""Build an owner-signoff form (index.html) from a YAML or JSON spec.

Validates the spec against the schema documented in SKILL.md, renders the form
from assets/template.html, and writes index.html next to the spec file. The
serve step is a separate script (serve_signoff.py) so a validation failure
surfaces in the foreground, not inside a background task.

Stdlib-only for JSON specs; YAML specs need PyYAML (falls back with a clear
error if it is missing).

Usage: python3 build_signoff.py <spec.yaml|spec.json>
       python3 build_signoff.py --batch-root [project-root]

The second form prints where this project's dated batch dirs live and builds
nothing — `_meta/signoff` unless a `signoff:` key overrides it.
"""

import datetime
import html
import json
import pathlib
import string
import sys

TEMPLATE = pathlib.Path(__file__).resolve().parent.parent / "assets" / "template.html"

LOCAL_RELPATH = pathlib.Path(".claude") / "owner-signoff.local.md"
DEFAULT_BATCH_ROOT = "_meta/signoff"

DEFAULT_CHOICES = ["Approve", "Modify (note below)"]
DEFAULT_CATEGORY = "Decision"
ITEM_KEYS = {"id", "category", "question", "context", "recommendation", "choices", "text_field"}
# Z is the general-notes section the template always appends.
AUTO_IDS = string.ascii_uppercase[:25]


def _frontmatter_value(text: str, key: str) -> str | None:
    """The scalar *key* holds in a leading `---` frontmatter block, else None.

    Deliberately narrow: flat scalars only, first match wins, quotes and a trailing
    ` #` comment stripped. Anything richer belongs in the spec file, not here.
    """
    lines = text.splitlines()
    if not lines or lines[0].lstrip("﻿").strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() in ("---", "..."):
            break
        name, sep, value = line.partition(":")
        if not sep or name.strip() != key:
            continue
        value = value.strip()
        if value[:1] in ("'", '"'):
            close = value.find(value[0], 1)
            return (value[1:close] if close != -1 else value[1:]) or None
        hash_at = value.find(" #")
        return (value[:hash_at].rstrip() if hash_at != -1 else value) or None
    return None


def resolve_batch_root(project_root) -> pathlib.Path:
    """Where this project's dated sign-off batch dirs live.

    `<project-root>/_meta/signoff` unless a `signoff:` key in
    `.claude/owner-signoff.local.md` names another project-relative dir. The key
    absent, blank, or resolving outside the project root leaves the default in
    force. Fail-open on purpose: an override is never a way to switch the skill off.
    """
    root = pathlib.Path(project_root).resolve()
    try:
        override = _frontmatter_value((root / LOCAL_RELPATH).read_text(encoding="utf-8"), "signoff")
    except OSError:
        override = None
    if override:
        candidate = (root / override).resolve()
        if candidate.is_relative_to(root):
            return candidate
    return root / DEFAULT_BATCH_ROOT


def load_spec(path: pathlib.Path):
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            raise SystemExit("PyYAML is not installed — write the spec as JSON instead")
        spec = yaml.safe_load(text)
        # YAML parses an unquoted `date: 2026-08-26` as datetime.date — normalize it.
        if isinstance(spec, dict) and isinstance(spec.get("date"), datetime.date):
            spec["date"] = spec["date"].isoformat()
        return spec
    return json.loads(text)


def validate(spec) -> list[str]:
    errs: list[str] = []
    if not isinstance(spec, dict):
        return ["spec must be a mapping"]

    title = spec.get("title")
    if not isinstance(title, str) or not title.strip():
        errs.append("title: required, non-empty string")
    for key in ("project", "date"):
        if key in spec and not isinstance(spec[key], str):
            errs.append(f"{key}: must be a string")

    summary = spec.get("summary", {})
    if not isinstance(summary, dict):
        errs.append("summary: must be a mapping with 'done' and/or 'waiting' lists")
    else:
        for key, val in summary.items():
            if key not in ("done", "waiting"):
                errs.append(f"summary.{key}: unknown key (use 'done'/'waiting')")
            elif not (isinstance(val, list) and all(isinstance(x, str) for x in val)):
                errs.append(f"summary.{key}: must be a list of strings")

    unknown_top = set(spec) - {"title", "project", "date", "summary", "items"}
    for key in sorted(unknown_top):
        errs.append(f"{key}: unknown top-level key")

    items = spec.get("items")
    if not isinstance(items, list) or not items:
        errs.append("items: required, non-empty list")
        return errs

    seen_ids: set[str] = set()
    for i, item in enumerate(items):
        where = f"items[{i}]"
        if not isinstance(item, dict):
            errs.append(f"{where}: must be a mapping")
            continue
        for key in sorted(set(item) - ITEM_KEYS):
            errs.append(f"{where}.{key}: unknown key")
        for key in ("question", "context", "recommendation"):
            val = item.get(key)
            if not isinstance(val, str) or not val.strip():
                errs.append(f"{where}.{key}: required, non-empty string")
        item_id = item.get("id")
        if item_id is not None:
            if not isinstance(item_id, str) or not item_id.strip():
                errs.append(f"{where}.id: must be a non-empty string (or omit for auto A/B/C…)")
            elif item_id == "Z":
                errs.append(f"{where}.id: 'Z' is reserved for the general-notes section")
            elif item_id in seen_ids:
                errs.append(f"{where}.id: duplicate id {item_id!r}")
            else:
                seen_ids.add(item_id)
        for key in ("category", "text_field"):
            if key in item and (not isinstance(item[key], str) or not item[key].strip()):
                errs.append(f"{where}.{key}: must be a non-empty string")
        choices = item.get("choices")
        if choices is not None:
            if (
                not isinstance(choices, list)
                or len(choices) < 2
                or not all(isinstance(c, str) and c.strip() for c in choices)
            ):
                errs.append(f"{where}.choices: must be a list of 2+ non-empty strings")
    return errs


def resolve_ids(items: list[dict]) -> list[str]:
    """Explicit ids as given; missing ids get the next unused letter A–Y."""
    used = {item["id"] for item in items if "id" in item}
    auto = (c for c in AUTO_IDS if c not in used)
    ids = []
    for item in items:
        if "id" in item:
            ids.append(item["id"])
        else:
            try:
                ids.append(next(auto))
            except StopIteration:
                raise SystemExit("more than 25 items without explicit ids — add explicit ids")
    return ids


def render_section(item: dict, item_id: str) -> str:
    e = html.escape
    choices = item.get("choices", DEFAULT_CHOICES)
    radios = "\n      ".join(
        f'<label><input type="radio" name="{e(item_id)}" value="{e(c)}"'
        f'{" checked" if j == 0 else ""}> {e(c)}</label>'
        for j, c in enumerate(choices)
    )
    text_input = (
        f'\n    <input type="text" name="{e(item_id)}_text" placeholder="{e(item["text_field"])}">'
        if item.get("text_field")
        else ""
    )
    return f"""  <section data-id="{e(item_id)}">
    <span class="pill">{e(item.get("category", DEFAULT_CATEGORY))}</span>
    <h2>{e(item["question"])}</h2>
    <p class="ctx">{e(item["context"])}</p>
    <div class="rec"><b>Recommendation:</b> {e(item["recommendation"])}</div>
    <div class="choices">
      {radios}
    </div>{text_input}
    <textarea name="{e(item_id)}_notes" placeholder="Inline notes…"></textarea>
  </section>"""


def render(spec: dict) -> str:
    e = html.escape
    summary = spec.get("summary") or {}
    summary_html = ""
    if summary.get("done") or summary.get("waiting"):
        lis = [f'    <li class="done">{e(t)}</li>' for t in summary.get("done", [])]
        lis += [f'    <li class="wait">{e(t)}</li>' for t in summary.get("waiting", [])]
        summary_html = (
            '  <section class="summary">\n    <h2>Where things stand</h2>\n    <ul>\n'
            + "\n".join("  " + li for li in lis)
            + "\n    </ul>\n  </section>"
        )

    items = spec["items"]
    ids = resolve_ids(items)
    sections = "\n\n".join(render_section(item, item_id) for item, item_id in zip(items, ids))
    meta = " · ".join(x for x in (spec.get("date"), spec.get("project")) if x)

    out = TEMPLATE.read_text()
    for placeholder, value in (
        ("{{TITLE}}", e(spec["title"])),
        ("{{META}}", e(meta) + " · " if meta else ""),
        ("{{SUMMARY}}", summary_html),
        ("{{SECTIONS}}", sections),
    ):
        out = out.replace(placeholder, value)
    return out


USAGE = (
    "usage: python3 build_signoff.py <spec.yaml|spec.json>\n"
    "       python3 build_signoff.py --batch-root [project-root]"
)


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(USAGE)  # asking for help is not a usage error
        return
    if len(sys.argv) in (2, 3) and sys.argv[1] == "--batch-root":
        print(resolve_batch_root(sys.argv[2] if len(sys.argv) == 3 else "."))
        return
    if len(sys.argv) != 2:
        raise SystemExit(USAGE)
    spec_path = pathlib.Path(sys.argv[1]).resolve()
    spec = load_spec(spec_path)
    errs = validate(spec)
    if errs:
        print("spec is invalid:", file=sys.stderr)
        for err in errs:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    out = spec_path.parent / "index.html"
    out.write_text(render(spec))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
