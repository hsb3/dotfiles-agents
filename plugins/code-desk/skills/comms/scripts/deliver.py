#!/usr/bin/env python3
"""Turn a deliverable spec into a validated, theme-styled HTML deck, and optionally a PDF.

Why this exists: a deck answers to three contracts at once — a type contract (which
sections a morning briefing owes, and how many pages each gets), a palette contract
(28 semantic tokens, no hardcoded hex), and a voice contract (title/bullet budgets,
register, id policy). Split across a renderer, a theme table and a prose style guide,
nothing checked them together, so a deck could render beautifully and still be off-spec.
This script is the one engine: a spec goes in, every contract is enforced in a single
pass, styled HTML comes out.

Key entry points: ``load_spec`` (JSON or YAML, plus the bare-array legacy shape),
``validate_spec`` and ``voice_lint`` (every problem reported at once, never fail-fast),
``render_html`` (self-contained document), ``export_pdf`` (headless-Chrome print),
``narration_script`` + ``render_audio`` (a spoken companion, provider-agnostic).
``load_local_config`` reads a project's house defaults. Stdlib only, except that a
``.yaml`` spec needs PyYAML.

Limitation: unsupported block types are a hard error, never a silent drop. A status deck
that quietly loses a slide is worse than one that fails to build.
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES_DIR = os.path.join(SKILL_ROOT, "themes")
VOICES_DIR = os.path.join(SKILL_ROOT, "voices")
TYPES_DIR = os.path.join(SKILL_ROOT, "types")

DEFAULT_THEME = "boardroom"

# Project-local preferences, discovered by walking up from the spec file. Recognized keys
# are flat strings only; `audio` names an audio provider, the rest are config names.
LOCAL_RELPATH = os.path.join(".claude", "comms.local.md")
LOCAL_KEYS = frozenset({"theme", "voice", "repo", "audio", "briefings_dir"})

# Type default when nothing overrides it: `_meta/briefings/` when a `_meta/` tree already
# exists at the resolution root (the mise-en-place standard), else `briefings/` there.
_META_DIRNAME = "_meta"
_BRIEFINGS_DIRNAME = "briefings"

# macOS `say`: no account, no network, no SDK. Any other provider value is a command
# template, which is what keeps a vendor out of this file.
DEFAULT_PROVIDER = "say"

# Block types this renderer implements — the full set found across the real decks in the
# briefing archives (census, 2026-08-06: 22 decks). Anything outside this set fails loudly
# rather than rendering a lie.
SUPPORTED_BLOCKS = frozenset(
    {
        "heading", "subtitle", "lead", "bullets", "columns", "stat", "callout", "divider",
        "table", "steps", "timeline", "matrix", "code", "image", "svg", "chart", "quote",
    }
)
CHART_KINDS = frozenset({"bar", "line", "donut"})
SLIDE_KEYS = frozenset({"id", "kicker", "notes", "layout", "footer", "fit", "balance", "blocks"})
LAYOUTS = frozenset({"center", "top", "fill"})
CALLOUT_VARIANTS = frozenset({"info", "accent", "warn", "success"})
TRENDS = {"up": "▲", "down": "▼", "flat": "→"}

TOP_KEYS = frozenset(
    {"type", "title", "repo", "theme", "voice", "waive", "sections", "slides", "briefings_dir"}
)

# Every theme file must carry all 28 semantic roles, whether or not this renderer paints
# with them: a theme is a portable palette contract, not a stylesheet fragment.
REQUIRED_TOKENS = (
    "canvas", "surface", "surfaceElevated", "surfaceInverse",
    "textPrimary", "textSecondary", "textInverse", "textAccent",
    "border", "borderStrong", "gridline",
    "accentPrimary", "accentSecondary", "accentTertiary", "accentSoft",
    "dataPrimary", "dataSecondary", "dataTertiary", "dataQuaternary",
    "dataPositive", "dataNegative", "dataNeutral", "dataTrack",
    "positive", "caution", "negative", "informational", "shadow",
)

# Theme token -> CSS custom property. Only the roles the stylesheet actually paints with
# are injected; the unmapped ones stay validated but unused rather than being given an
# invented job.
TOKEN_VARS = {
    "canvas": "--bg",
    "surface": "--bg-alt",
    "surfaceElevated": "--code-bg",
    "textPrimary": "--fg",
    "textSecondary": "--muted",
    "textInverse": "--text-inverse",
    "border": "--line",
    "borderStrong": "--page-bg",
    "accentPrimary": "--accent",
    "accentSecondary": "--accent-2",
    "positive": "--pos",
    "negative": "--neg",
    "caution": "--warn",
    "dataPrimary": "--series-0",
    "dataSecondary": "--series-1",
    "dataTertiary": "--series-2",
    "dataQuaternary": "--series-3",
    "dataNeutral": "--series-4",
}

STAGE_W, STAGE_H = 1280, 720

# The stylesheet carries CSS braces everywhere, so theme values are spliced in at a marker
# rather than through str.format.
_THEME_MARKER = "/*theme*/"

_HEX = re.compile(r"[0-9A-F]{6}")


class DeckError(Exception):
    """A deck failed validation, or the environment can't satisfy an export."""


# ---------------------------------------------------------------------------
# loading


def _plain(value: Any) -> Any:
    """Normalize YAML-only types to what the equivalent JSON spec would have produced.

    YAML parses an unquoted ``2026-06-13`` as a date object, which then reaches the
    renderer as a non-string and blows up escaping. ISO strings everywhere instead.
    """
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def load_spec(path: str) -> dict:
    """Read a spec file and normalize it to the envelope shape the rest of the module uses.

    JSON is stdlib; ``.yaml``/``.yml`` needs PyYAML and exits with a clear message without
    it. A bare top-level array is the pre-spec deck shape — a slide list with no envelope —
    and is accepted as ``{"slides": [...]}`` so decks authored before this format still
    validate and render.
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError:
            raise SystemExit("PyYAML is not installed — write the spec as JSON instead")
        data = _plain(yaml.safe_load(text))
    else:
        data = _plain(json.loads(text))

    if isinstance(data, list):
        return {"slides": data}
    if not isinstance(data, dict):
        raise DeckError("spec must be an object, or a bare array of slides")
    return data


def _names(dirpath: str) -> list[str]:
    if not os.path.isdir(dirpath):
        return []
    return sorted(
        f[:-5] for f in os.listdir(dirpath) if f.endswith(".json") and not f.startswith(".")
    )


def _load_data(dirpath: str, name: str, kind: str) -> dict:
    available = _names(dirpath)
    if name not in available:
        raise DeckError(
            f"unknown {kind} {name!r} — available: {', '.join(available) or '(none)'}"
        )
    path = os.path.join(dirpath, f"{name}.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:  # pragma: no cover - name came from a directory listing
        raise DeckError(f"cannot read {kind} {name!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DeckError(f"{kind} {name!r} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise DeckError(f"{kind} {name!r} must be a JSON object")
    return data


def load_theme(name: str) -> dict:
    """Load one theme and refuse an incomplete palette — a missing token renders as blank."""
    theme = _load_data(THEMES_DIR, name, "theme")
    problems = validate_theme(name, theme)
    if problems:
        raise DeckError("\n  - ".join(["theme is incomplete:"] + problems))
    return theme


def load_voice(name: str) -> dict:
    return _load_data(VOICES_DIR, name, "voice")


def load_type(type_id: str) -> dict:
    return _load_data(TYPES_DIR, type_id, "type")


def list_types() -> list[dict]:
    """Every deliverable type this kit defines, id-sorted."""
    return [load_type(t) for t in _names(TYPES_DIR)]


# ---------------------------------------------------------------------------
# project-local preferences


def _warn(message: str) -> None:
    """A misconfiguration yells to stderr and is then ignored — it never fails a build."""
    print(f"✗ {message}", file=sys.stderr)


def _unquote(value: str) -> str:
    """Strip surrounding quotes, then any trailing ``# comment``.

    Quotes come off first so a quoted value may itself contain a ``#``.
    """
    value = value.strip()
    if value[:1] in ("'", '"'):
        close = value.find(value[0], 1)
        return value[1:close] if close != -1 else value[1:]
    hash_at = value.find(" #")
    return value[:hash_at].rstrip() if hash_at != -1 else value


def find_local_config(start_dir: str | None) -> str | None:
    """First ``.claude/comms.local.md`` at or above *start_dir*, else None.

    No directory to start from — the ``types`` subcommand, say, which has no spec — means
    no project context and therefore no file.
    """
    if not start_dir:
        return None
    current = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(current, LOCAL_RELPATH)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def load_local_config(start_dir: str | None) -> dict:
    """A project's house defaults as a flat ``{key: string}`` map; ``{}`` when there are none.

    The file is markdown with a YAML frontmatter block, parsed here with a deliberately
    narrow line reader: flat scalars only, nested mappings and sequences skipped. Absent is
    silent; unreadable, unfenced, or carrying a key this kit does not know warns once and
    resolves to nothing more. A recognized key holding an unknown VALUE is not checked here
    — it flows into normal resolution and fails there, where the error can list the
    alternatives.
    """
    path = find_local_config(start_dir)
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        _warn(f"cannot read {path}: {exc} — ignored")
        return {}
    return _parse_local(text, path)


def _parse_local(text: str, where: str) -> dict:
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
        _warn(f"{where}: no '---' frontmatter block — ignored")
        return {}

    end = None
    for index in range(start, len(lines)):
        if lines[index].strip() in ("---", "..."):
            end = index
            break
    if end is None:
        _warn(f"{where}: frontmatter block is never closed — ignored")
        return {}

    config: dict[str, str] = {}
    unknown: list[str] = []
    for line in lines[start:end]:
        item = line.strip()
        if not item or line[:1].isspace() or item.startswith(("#", "-")):
            continue  # blank, nested, a comment, or a sequence entry
        colon = item.find(":")
        if colon == -1:
            continue
        key = item[:colon].strip().lower()
        value = _unquote(item[colon + 1:])
        if not value:
            continue  # a mapping opener; this reader takes flat scalars only
        if key in LOCAL_KEYS:
            config[key] = value
        else:
            unknown.append(key)
    if unknown:
        _warn(
            f"{where}: unknown key(s) {', '.join(sorted(set(unknown)))} — ignored "
            f"(recognized: {', '.join(sorted(LOCAL_KEYS))})"
        )
    return config


def resolve_briefings_dir(
    start_dir: str,
    override: str | None = None,
    spec: dict | None = None,
    local: dict | None = None,
) -> str:
    """The directory a comm package should be written into.

    Precedence: CLI flag (*override*) > spec field (``briefings_dir``) > project local
    (``briefings_dir`` in ``.claude/comms.local.md``) > type default — ``_meta/briefings/``
    when *start_dir* already has a ``_meta/`` tree (the mise-en-place standard), else
    ``briefings/`` there. A relative value from any of the first three sources resolves
    against *start_dir*; *local* is loaded from *start_dir* when not supplied.
    """
    root = os.path.abspath(start_dir)
    loc = local if local is not None else load_local_config(start_dir)
    value = override or (spec or {}).get("briefings_dir") or loc.get("briefings_dir")
    if isinstance(value, str) and value:
        return value if os.path.isabs(value) else os.path.join(root, value)
    if os.path.isdir(os.path.join(root, _META_DIRNAME)):
        return os.path.join(root, _META_DIRNAME, _BRIEFINGS_DIRNAME)
    return os.path.join(root, _BRIEFINGS_DIRNAME)


def validate_theme(name: str, theme: Any) -> list[str]:
    """Return a list of problems with one theme; empty means the palette is complete."""
    if not isinstance(theme, dict) or not isinstance(theme.get("tokens"), dict):
        return [f"theme {name!r}: needs a 'tokens' object"]
    tokens = theme["tokens"]
    problems = []
    for token in REQUIRED_TOKENS:
        value = tokens.get(token)
        if not isinstance(value, str) or not _HEX.fullmatch(value):
            problems.append(
                f"theme {name!r}: token {token!r} must be 6 uppercase hex digits, got {value!r}"
            )
    return problems


# ---------------------------------------------------------------------------
# inline markup


def _inline(text: str, repo: str | None = None) -> str:
    """Convert the deck inline-markup dialect to HTML, escaping everything else.

    Supported: ```code```, ``**bold**``, ``{accent|warn|ok|info:text}`` colored spans,
    ``{chip.ok|warn|info|accent:text}`` pills, and bare ``#<n>`` issue refs when *repo* is set.
    """
    out = html.escape(str(text), quote=False)

    # Chips before plain color spans — `{chip.ok:…}` also matches the color-span pattern.
    out = re.sub(
        r"\{chip\.(ok|warn|info|accent):([^}]*)\}",
        lambda m: f'<span class="chip chip-{m.group(1)}">{m.group(2)}</span>',
        out,
    )
    out = re.sub(
        r"\{(accent|warn|ok|info):([^}]*)\}",
        lambda m: f'<span class="tint tint-{m.group(1)}">{m.group(2)}</span>',
        out,
    )
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)

    if repo:
        # Only a bare hash-number — not inside an already-emitted href or a word.
        out = re.sub(
            r"(?<![\w/#>])#(\d+)\b",
            lambda m: f'<a href="https://github.com/{repo}/issues/{m.group(1)}">#{m.group(1)}</a>',
            out,
        )
    return out


# ---------------------------------------------------------------------------
# slide validation


def validate(slides: Any) -> list[str]:
    """Return a list of human-readable problems; empty means the deck is conformant."""
    problems: list[str] = []
    if not isinstance(slides, list):
        return ["top level must be a JSON array of slides"]
    if not slides:
        return ["deck has zero slides"]
    return problems + _validate_slides(slides, "slide")


def _validate_slides(slides: list, prefix: str) -> list[str]:
    """Schema-check a slide group. *prefix* carries the caller's numbering scheme so a
    sectioned spec reports ``section 'horizon' slide 1`` and a flat one ``slide 1``."""
    problems: list[str] = []
    for i, slide in enumerate(slides):
        where = f"{prefix} {i + 1}"
        if not isinstance(slide, dict):
            problems.append(f"{where}: must be an object")
            continue
        for key in set(slide) - SLIDE_KEYS:
            problems.append(f"{where}: unknown slide key {key!r}")
        layout = slide.get("layout")
        if layout is not None and layout not in LAYOUTS:
            problems.append(f"{where}: layout {layout!r} not in {sorted(LAYOUTS)}")
        blocks = slide.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            problems.append(f"{where}: needs a non-empty 'blocks' array")
            continue
        for j, block in enumerate(blocks):
            problems += _validate_block(block, f"{where} block {j + 1}")
    return problems


def _validate_block(block: Any, where: str) -> list[str]:
    if not isinstance(block, dict):
        return [f"{where}: must be an object"]
    btype = block.get("type")
    if btype not in SUPPORTED_BLOCKS:
        return [
            f"{where}: unsupported block type {btype!r} "
            f"(this renderer implements {sorted(SUPPORTED_BLOCKS)})"
        ]

    problems: list[str] = []
    if btype in ("heading", "subtitle", "lead"):
        if not str(block.get("text", "")).strip():
            problems.append(f"{where}: {btype} needs non-empty 'text'")
        if btype == "heading" and block.get("level") not in (None, 1, 2):
            problems.append(f"{where}: heading level must be 1 or 2")
    elif btype == "bullets":
        items = block.get("items")
        if not isinstance(items, list) or not items:
            problems.append(f"{where}: bullets needs a non-empty 'items' array")
    elif btype == "stat":
        if not str(block.get("value", "")).strip():
            problems.append(f"{where}: stat needs non-empty 'value'")
        trend = block.get("trend")
        if trend is not None and trend not in TRENDS:
            problems.append(f"{where}: stat trend {trend!r} not in {sorted(TRENDS)}")
    elif btype == "callout":
        if not str(block.get("text", "")).strip():
            problems.append(f"{where}: callout needs non-empty 'text'")
        variant = block.get("variant")
        if variant is not None and variant not in CALLOUT_VARIANTS:
            problems.append(f"{where}: callout variant {variant!r} not in {sorted(CALLOUT_VARIANTS)}")
    elif btype == "table":
        head, rows = block.get("head"), block.get("rows")
        if not isinstance(head, list) or not head:
            problems.append(f"{where}: table needs a non-empty 'head' array")
        if not isinstance(rows, list) or not rows:
            problems.append(f"{where}: table needs a non-empty 'rows' array")
        elif isinstance(head, list):
            for r, row in enumerate(rows):
                if not isinstance(row, list):
                    problems.append(f"{where}: table row {r + 1} must be an array")
                elif len(row) > len(head):
                    problems.append(
                        f"{where}: table row {r + 1} has {len(row)} cells but head has {len(head)}"
                    )
    elif btype == "steps":
        steps = block.get("steps")
        if not isinstance(steps, list) or not steps:
            problems.append(f"{where}: steps needs a non-empty 'steps' array")
        else:
            for s, step in enumerate(steps):
                if not isinstance(step, dict) or not str(step.get("title", "")).strip():
                    problems.append(f"{where}: step {s + 1} needs a 'title'")
    elif btype == "timeline":
        milestones = block.get("milestones")
        if not isinstance(milestones, list) or not milestones:
            problems.append(f"{where}: timeline needs a non-empty 'milestones' array")
        else:
            for m_, ms in enumerate(milestones):
                if not isinstance(ms, dict) or not str(ms.get("label", "")).strip():
                    problems.append(f"{where}: milestone {m_ + 1} needs a 'label'")
    elif btype == "matrix":
        quadrants = block.get("quadrants")
        if not isinstance(quadrants, list) or not quadrants:
            problems.append(f"{where}: matrix needs a non-empty 'quadrants' array")
        elif len(quadrants) > 4:
            problems.append(f"{where}: matrix takes at most 4 quadrants, got {len(quadrants)}")
        for axis in ("xAxis", "yAxis"):
            val = block.get(axis)
            if val is not None and (not isinstance(val, list) or len(val) != 2):
                problems.append(f"{where}: matrix {axis} must be a [start, end] pair")
    elif btype == "code":
        if not str(block.get("code", "")).strip():
            problems.append(f"{where}: code needs non-empty 'code'")
    elif btype == "quote":
        if not str(block.get("text", "")).strip():
            problems.append(f"{where}: quote needs non-empty 'text'")
    elif btype == "image":
        if not str(block.get("src", "")).strip():
            problems.append(f"{where}: image needs non-empty 'src'")
    elif btype == "svg":
        if not str(block.get("svg", "")).strip():
            problems.append(f"{where}: svg needs non-empty 'svg'")
    elif btype == "chart":
        if block.get("kind") not in CHART_KINDS:
            problems.append(f"{where}: chart kind must be one of {sorted(CHART_KINDS)}")
        data = block.get("data")
        if not isinstance(data, list) or not data:
            problems.append(f"{where}: chart needs a non-empty 'data' array")
        elif not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in data):
            problems.append(f"{where}: chart 'data' must be all numbers")
    elif btype == "columns":
        columns = block.get("columns")
        if not isinstance(columns, list) or not columns:
            problems.append(f"{where}: columns needs a non-empty 'columns' array")
        else:
            for k, col in enumerate(columns):
                if not isinstance(col, list):
                    problems.append(f"{where}: column {k + 1} must be an array of blocks")
                    continue
                for m, nested in enumerate(col):
                    problems += _validate_block(nested, f"{where} col {k + 1} block {m + 1}")
    return problems


# ---------------------------------------------------------------------------
# spec validation


def _str(spec: dict, key: str) -> str | None:
    value = spec.get(key)
    return value if isinstance(value, str) else None


def _groups(spec: dict, typedef: dict | None) -> list[tuple[str, list]]:
    """Slide groups as ``(numbering prefix, slides)``.

    A sectioned spec yields one group per section, ordered by the TYPE's section order —
    the spec's key order is an authoring accident, the type's order is the contract.
    Unknown sections trail in file order so their slides are still schema-checked.
    """
    sections = spec.get("sections")
    if isinstance(sections, dict):
        order = [s["id"] for s in ((typedef or {}).get("sections") or []) if isinstance(s, dict)]
        ids = [s for s in order if s in sections] + [s for s in sections if s not in order]
        return [
            (f"section {sid!r} slide", sections[sid])
            for sid in ids
            if isinstance(sections[sid], list)
        ]
    slides = spec.get("slides")
    return [("slide", slides)] if isinstance(slides, list) else []


def resolve_context(
    spec: dict, overrides: dict | None = None, local: dict | None = None
) -> tuple[dict, list[str]]:
    """Resolve type/theme/voice/title/repo, collecting name problems instead of raising.

    Precedence is CLI flag (*overrides*) > spec field > project local (*local*) > type
    default. The spec is the authored artifact, so it outranks ambient project preference;
    the project layer only sets house defaults once.

    Returns ``(context, problems)``; anything that failed to resolve is ``None`` in the
    context, so a caller can keep validating the rest of the spec.
    """
    over = {k: v for k, v in (overrides or {}).items() if v}
    loc = {k: v for k, v in (local or {}).items() if isinstance(v, str) and v}
    ctx: dict[str, Any] = {
        "type_name": None, "typedef": None,
        "theme_name": None, "theme": None,
        "voice_name": None, "voice": None,
        "title": "Deck", "repo": None, "waive": [],
    }
    problems: list[str] = []
    if not isinstance(spec, dict):
        return ctx, ["spec must be an object, or a bare array of slides"]

    for key in sorted(set(spec) - TOP_KEYS):
        problems.append(
            f"unknown top-level key {key!r} (allowed: {', '.join(sorted(TOP_KEYS))})"
        )
    for key in ("type", "title", "repo", "theme", "voice", "briefings_dir"):
        if key in spec and not isinstance(spec[key], str):
            problems.append(f"{key}: must be a string")

    waive = spec.get("waive", [])
    if not isinstance(waive, list) or not all(isinstance(w, str) for w in waive):
        problems.append("waive: must be a list of lint rule-id strings")
        waive = []
    ctx["waive"] = list(waive)

    type_name = _str(spec, "type")
    ctx["type_name"] = type_name
    if type_name:
        try:
            ctx["typedef"] = load_type(type_name)
        except DeckError as exc:
            problems.append(str(exc))
    typedef = ctx["typedef"] or {}

    theme_name = (
        over.get("theme") or _str(spec, "theme") or loc.get("theme")
        or typedef.get("default_theme") or DEFAULT_THEME
    )
    ctx["theme_name"] = theme_name
    try:
        ctx["theme"] = load_theme(theme_name)
    except DeckError as exc:
        problems.append(str(exc))

    # No voice resolves for an untyped or legacy spec, and no voice means no voice lint.
    voice_name = (
        over.get("voice") or _str(spec, "voice") or loc.get("voice")
        or typedef.get("default_voice")
    )
    ctx["voice_name"] = voice_name
    if voice_name:
        try:
            ctx["voice"] = load_voice(voice_name)
        except DeckError as exc:
            problems.append(str(exc))

    ctx["title"] = over.get("title") or _str(spec, "title") or "Deck"
    ctx["repo"] = over.get("repo") or _str(spec, "repo") or loc.get("repo")
    return ctx, problems


def _pages(section: dict) -> tuple[int, int]:
    pages = section.get("pages")
    if isinstance(pages, list) and len(pages) == 2 and all(isinstance(p, int) for p in pages):
        return pages[0], pages[1]
    return 1, 1


def _structure_problems(spec: dict, ctx: dict) -> list[str]:
    problems: list[str] = []
    has_sections, has_slides = "sections" in spec, "slides" in spec
    if has_sections and has_slides:
        problems.append(
            "spec has both 'sections' and 'slides' — a sectioned spec is typed, a flat one is not"
        )
    elif not has_sections and not has_slides:
        problems.append("spec needs 'sections' (typed) or 'slides' (flat)")

    if has_sections:
        sections = spec["sections"]
        if not isinstance(sections, dict):
            return problems + ["sections: must be an object mapping section id -> slide list"]
        typedef = ctx.get("typedef")
        if typedef is None:
            if not ctx.get("type_name"):
                problems.append(
                    "spec has 'sections' but no 'type' — section ids and page budgets "
                    f"come from the type (available: {', '.join(_names(TYPES_DIR)) or '(none)'})"
                )
        else:
            defined = [s["id"] for s in (typedef.get("sections") or []) if isinstance(s, dict)]
            for sid in sections:
                if sid not in defined:
                    problems.append(
                        f"unknown section {sid!r} for type {typedef.get('id')!r} — "
                        f"this type defines {', '.join(defined)}"
                    )
            for section in typedef.get("sections") or []:
                sid = section["id"]
                low, high = _pages(section)
                if sid not in sections:
                    if section.get("required", True) is not False:
                        problems.append(
                            f"missing required section {sid!r} ({section.get('name', sid)})"
                        )
                    continue
                slides = sections[sid]
                if not isinstance(slides, list):
                    problems.append(f"section {sid!r}: must be a list of slides")
                elif not low <= len(slides) <= high:
                    problems.append(
                        f"section {sid!r}: has {len(slides)} slide(s), budget is {low}-{high}"
                    )
    else:
        slides = spec.get("slides")
        if not isinstance(slides, list):
            problems.append("slides: must be an array of slides")
        elif not slides:
            problems.append("deck has zero slides")

    for prefix, group in _groups(spec, ctx.get("typedef")):
        problems += _validate_slides(group, prefix)
    return problems


def validate_spec(
    spec: dict, overrides: dict | None = None, local: dict | None = None
) -> list[str]:
    """Every STRUCTURAL problem with a spec, in one pass: unknown keys, unresolvable
    type/theme/voice names, section membership and page budgets, and slide schema.

    Voice lint is deliberately not included — its findings are waivable, so they are
    produced separately by ``voice_lint`` (``analyze_spec`` returns both together).
    """
    ctx, problems = resolve_context(spec, overrides, local)
    return problems + _structure_problems(spec, ctx)


# ---------------------------------------------------------------------------
# voice lint


# A leading id, before any plain-English label: `#<n> the loader`, `ABC-<n> the loader`.
_BARE_ID = re.compile(r"\s*(?:#\d+|[A-Z]{2,}-\d+)")

_ID_TEXT_BLOCKS = ("heading", "lead", "callout")


def _walk_blocks(blocks: Any, where: str):
    """Yield ``(block, where)`` for every block on a slide, descending into columns."""
    if not isinstance(blocks, list):
        return
    for j, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        at = f"{where} block {j + 1}"
        yield block, at
        if block.get("type") == "columns":
            for k, col in enumerate(block.get("columns") or []):
                yield from _walk_blocks(col, f"{at} col {k + 1}")


def voice_lint(slides: Any, voice: dict, prefix: str = "slide") -> list[tuple[str, str]]:
    """Return ``(rule id, message)`` findings for one slide group against a voice profile.

    Only knobs the profile actually declares are enforced — a missing budget is a rule the
    voice chose not to have, not a default. Waives are applied by the caller so a
    suppressed finding can still be counted.
    """
    findings: list[tuple[str, str]] = []
    if not isinstance(slides, list) or not isinstance(voice, dict):
        return findings
    budgets = voice.get("budgets") or {}
    title_chars = budgets.get("title_chars")
    bullet_words = budgets.get("bullet_words")
    per_slide = budgets.get("bullets_per_slide")
    register = voice.get("register")
    label_first = voice.get("id_policy") == "label-first"

    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue
        where = f"{prefix} {i + 1}"
        bullets_here = 0
        for block, at in _walk_blocks(slide.get("blocks"), where):
            btype = block.get("type")
            text = block.get("text")

            if btype == "heading" and isinstance(text, str) and block.get("level", 1) == 1:
                if title_chars and len(text) > title_chars:
                    findings.append((
                        "voice.title-budget",
                        f"{at}: title is {len(text)} chars, budget {title_chars}",
                    ))

            # ponytail: a leading-id regex, not a reader — it cannot tell a real
            # label-first line from one that merely opens with a word. Waive
            # `voice.bare-id` in the spec where it misfires.
            if label_first and btype in _ID_TEXT_BLOCKS and isinstance(text, str):
                if _BARE_ID.match(text):
                    findings.append((
                        "voice.bare-id",
                        f"{at}: {btype} opens with a bare id — plain-English label first",
                    ))

            if btype != "bullets":
                continue
            items = block.get("items")
            if not isinstance(items, list):
                continue
            bullets_here += len(items)
            for n, item in enumerate(items):
                if not isinstance(item, str):
                    continue
                at_item = f"{at} item {n + 1}"
                words = len(item.split())
                if bullet_words and words > bullet_words:
                    findings.append((
                        "voice.bullet-budget",
                        f"{at_item}: {words} words, budget {bullet_words}",
                    ))
                stripped = item.rstrip()
                if register == "fragments":
                    if stripped.endswith(".") and not stripped.endswith("..."):
                        findings.append((
                            "voice.register",
                            f"{at_item}: fragments register — drop the trailing period",
                        ))
                elif register == "sentences":
                    if not stripped.endswith((".", "!", "?")):
                        findings.append((
                            "voice.register",
                            f"{at_item}: sentences register — end with '.', '!' or '?'",
                        ))
                if label_first and _BARE_ID.match(item):
                    findings.append((
                        "voice.bare-id",
                        f"{at_item}: opens with a bare id — plain-English label first",
                    ))

        if per_slide and bullets_here > per_slide:
            findings.append((
                "voice.bullet-count",
                f"{where}: {bullets_here} bullets, budget {per_slide} per slide",
            ))
    return findings


def analyze_spec(
    spec: dict, overrides: dict | None = None, local: dict | None = None
) -> tuple[dict, list[str], list]:
    """Everything ``check`` needs: ``(context, structural problems, voice findings)``.

    Findings are returned before waives are applied — the caller decides what to suppress
    and reports how many it suppressed.
    """
    ctx, problems = resolve_context(spec, overrides, local)
    problems += _structure_problems(spec, ctx)
    findings: list[tuple[str, str]] = []
    if ctx["voice"]:
        for prefix, group in _groups(spec, ctx["typedef"]):
            findings += voice_lint(group, ctx["voice"], prefix)
    return ctx, problems, findings


def resolve_slides(spec: dict, typedef: dict | None = None) -> list[dict]:
    """Flatten a spec to one slide list, sectioned specs in the type's section order."""
    return [slide for _prefix, group in _groups(spec, typedef) for slide in group]


# ---------------------------------------------------------------------------
# rendering


def _block_html(block: dict, repo: str | None, base_dir: str | None = None) -> str:
    btype = block["type"]
    if btype == "heading":
        tag = "h2" if block.get("level") == 2 else "h1"
        return f"<{tag}>{_inline(block['text'], repo)}</{tag}>"
    if btype == "subtitle":
        return f'<p class="subtitle">{_inline(block["text"], repo)}</p>'
    if btype == "lead":
        return f'<p class="lead">{_inline(block["text"], repo)}</p>'
    if btype == "divider":
        return '<hr class="divider">'
    if btype == "bullets":
        items = "".join(f"<li>{_inline(i, repo)}</li>" for i in block["items"])
        return f"<ul>{items}</ul>"
    if btype == "stat":
        parts = [f'<div class="stat-value">{_inline(block["value"], repo)}</div>']
        if block.get("label"):
            parts.append(f'<div class="stat-label">{_inline(block["label"], repo)}</div>')
        if block.get("delta"):
            trend = block.get("trend", "flat")
            arrow = TRENDS.get(trend, "")
            parts.append(
                f'<div class="stat-delta trend-{trend}">{arrow} '
                f'{_inline(block["delta"], repo)}</div>'
            )
        if block.get("sub"):
            parts.append(f'<div class="stat-sub">{_inline(block["sub"], repo)}</div>')
        return f'<div class="stat">{"".join(parts)}</div>'
    if btype == "callout":
        variant = block.get("variant", "info")
        size = block.get("size", "md")
        inner = ""
        if block.get("title"):
            inner += f'<div class="callout-title">{_inline(block["title"], repo)}</div>'
        inner += f'<div class="callout-text">{_inline(block["text"], repo)}</div>'
        return f'<div class="callout callout-{variant} callout-{size}">{inner}</div>'
    if btype == "table":
        head = "".join(f"<th>{_inline(c, repo)}</th>" for c in block["head"])
        width = len(block["head"])
        # Ragged rows pad out to the header width — never truncate a cell off the deck.
        rows = "".join(
            "<tr>"
            + "".join(
                f"<td>{_inline(c, repo)}</td>"
                for c in list(row) + [""] * (width - len(row))
            )
            + "</tr>"
            for row in block["rows"]
        )
        return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
    if btype == "steps":
        items = "".join(
            f'<li><div class="step-title">{_inline(s["title"], repo)}</div>'
            + (f'<div class="step-detail">{_inline(s["detail"], repo)}</div>' if s.get("detail") else "")
            + "</li>"
            for s in block["steps"]
        )
        return f'<ol class="steps">{items}</ol>'
    if btype == "timeline":
        items = "".join(
            f'<li><div class="tl-label">{_inline(m["label"], repo)}</div>'
            + (f'<div class="tl-title">{_inline(m["title"], repo)}</div>' if m.get("title") else "")
            + (f'<div class="tl-detail">{_inline(m["detail"], repo)}</div>' if m.get("detail") else "")
            + "</li>"
            for m in block["milestones"]
        )
        return f'<ul class="timeline">{items}</ul>'
    if btype == "matrix":
        quads = ""
        for q in block["quadrants"]:
            inner = ""
            if q.get("title"):
                inner += f'<div class="quad-title">{_inline(q["title"], repo)}</div>'
            if q.get("items"):
                inner += "<ul>" + "".join(f"<li>{_inline(i, repo)}</li>" for i in q["items"]) + "</ul>"
            quads += f'<div class="quad">{inner}</div>'
        axes = ""
        if block.get("xAxis"):
            axes += (
                f'<div class="axis axis-x"><span>{_inline(block["xAxis"][0], repo)}</span>'
                f'<span>{_inline(block["xAxis"][1], repo)}</span></div>'
            )
        if block.get("yAxis"):
            axes += (
                f'<div class="axis axis-y"><span>{_inline(block["yAxis"][1], repo)}</span>'
                f'<span>{_inline(block["yAxis"][0], repo)}</span></div>'
            )
        return f'<div class="matrix-wrap">{axes}<div class="matrix">{quads}</div></div>'
    if btype == "code":
        lang = html.escape(str(block.get("lang", "")), quote=True)
        body = html.escape(str(block["code"]), quote=False)
        return f'<pre class="code" data-lang="{lang}"><code>{body}</code></pre>'
    if btype == "quote":
        attribution = (
            f'<footer class="quote-by">{_inline(block["attribution"], repo)}</footer>'
            if block.get("attribution")
            else ""
        )
        return f'<blockquote>{_inline(block["text"], repo)}{attribution}</blockquote>'
    if btype == "svg":
        return f'<div class="svg-block">{block["svg"]}</div>'
    if btype == "image":
        src = _image_src(block["src"], base_dir)
        alt = html.escape(str(block.get("alt", "")), quote=True)
        style = f' style="max-height:{int(block["maxHeight"])}px"' if block.get("maxHeight") else ""
        return f'<div class="image-block"><img src="{src}" alt="{alt}"{style}></div>'
    if btype == "chart":
        return _chart_svg(block, repo)
    if btype == "columns":
        cols = "".join(
            f'<div class="col">{"".join(_block_html(b, repo, base_dir) for b in col)}</div>'
            for col in block["columns"]
        )
        return f'<div class="columns">{cols}</div>'
    raise DeckError(f"unsupported block type {btype!r}")  # pragma: no cover - validated earlier


def _image_src(src: str, base_dir: str | None) -> str:
    """Inline a local image as a data URI so the document stays self-contained.

    Remote URLs and existing data URIs pass through untouched. A local path that cannot be
    read is an error: a briefing with a silently-broken image is a briefing that misleads.
    """
    import base64
    import mimetypes

    if src.startswith(("http://", "https://", "data:")):
        return html.escape(src, quote=True)
    path = src if os.path.isabs(src) else os.path.join(base_dir or ".", src)
    if not os.path.isfile(path):
        raise DeckError(f"image not found: {src} (resolved to {path})")
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as fh:
        payload = base64.b64encode(fh.read()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def _chart_svg(block: dict, repo: str | None) -> str:
    """Render a small inline SVG chart. Deliberately plain — a briefing chart, not a dashboard."""
    kind = block["kind"]
    data = [float(v) for v in block["data"]]
    labels = [str(x) for x in (block.get("labels") or [])]
    w, h, pad = 720, 260, 28
    peak = max(data + [1e-9])

    if kind == "donut":
        total = sum(data) or 1.0
        cx, cy, r, thick = 130, h / 2, 92, 34
        parts, start = [], -90.0
        for i, v in enumerate(data):
            sweep = 360.0 * (v / total)
            large = 1 if sweep > 180 else 0
            a0, a1 = math.radians(start), math.radians(start + sweep)
            x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
            x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
            parts.append(
                f'<path d="M {x0:.2f} {y0:.2f} A {r} {r} 0 {large} 1 {x1:.2f} {y1:.2f}" '
                f'fill="none" stroke="var(--series-{i % 5})" stroke-width="{thick}"/>'
            )
            start += sweep
        legend = "".join(
            f'<g transform="translate(280,{34 + i * 30})">'
            f'<rect width="14" height="14" rx="3" fill="var(--series-{i % 5})"/>'
            f'<text x="24" y="12" class="ck-label">{html.escape(labels[i] if i < len(labels) else "")}'
            f' — {data[i]:g}</text></g>'
            for i in range(len(data))
        )
        return (
            f'<div class="chart"><svg viewBox="0 0 {w} {h}" role="img">'
            f'{"".join(parts)}{legend}</svg></div>'
        )

    n = len(data)
    plot_w, plot_h = w - pad * 2, h - pad * 2
    if kind == "bar":
        slot = plot_w / n
        bw = min(slot * 0.62, 72)
        bars = ""
        for i, v in enumerate(data):
            bh = (v / peak) * plot_h
            x = pad + slot * i + (slot - bw) / 2
            y = pad + plot_h - bh
            bars += (
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bw:.2f}" height="{bh:.2f}" rx="3" '
                f'fill="var(--series-{i % 5})"/>'
                f'<text x="{x + bw / 2:.2f}" y="{y - 7:.2f}" class="ck-value">{v:g}</text>'
            )
            if i < len(labels):
                bars += (
                    f'<text x="{x + bw / 2:.2f}" y="{pad + plot_h + 18:.2f}" '
                    f'class="ck-label">{html.escape(labels[i])}</text>'
                )
        body = bars
    else:  # line
        step = plot_w / max(n - 1, 1)
        pts = [
            (pad + step * i, pad + plot_h - (v / peak) * plot_h) for i, v in enumerate(data)
        ]
        poly = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        dots = "".join(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="var(--series-0)"/>' for x, y in pts
        )
        ticks = "".join(
            f'<text x="{pts[i][0]:.2f}" y="{pad + plot_h + 18:.2f}" class="ck-label">'
            f"{html.escape(labels[i])}</text>"
            for i in range(min(len(labels), n))
        )
        body = (
            f'<polyline points="{poly}" fill="none" stroke="var(--series-0)" '
            f'stroke-width="3" stroke-linejoin="round"/>{dots}{ticks}'
        )
    baseline = (
        f'<line x1="{pad}" y1="{pad + plot_h}" x2="{w - pad}" y2="{pad + plot_h}" '
        f'stroke="var(--line)" stroke-width="1"/>'
    )
    return f'<div class="chart"><svg viewBox="0 0 {w} {h}" role="img">{baseline}{body}</svg></div>'


def _slide_html(slide: dict, index: int, repo: str | None, base_dir: str | None) -> str:
    layout = slide.get("layout", "center")
    body = "".join(_block_html(b, repo, base_dir) for b in slide["blocks"])
    head = f'<div class="kicker">{_inline(slide["kicker"], repo)}</div>' if slide.get("kicker") else ""
    foot = f'<div class="footer">{_inline(slide["footer"], repo)}</div>' if slide.get("footer") else ""
    notes = ""
    if slide.get("notes"):
        notes = f'<div class="notes">{_inline(slide["notes"], repo)}</div>'
    # The kicker lives INSIDE the body flow, not pinned above it: on a `center` slide the
    # kicker belongs to the centered group (title slides read as one block), while `top` and
    # `fill` are unaffected because the group starts at the top either way.
    return (
        f'<section class="slide layout-{layout}" data-index="{index}">'
        f'<div class="body">{head}{body}</div>{foot}{notes}</section>'
    )


def _theme_css(theme: dict) -> str:
    """Splice a theme's tokens into the stylesheet as CSS custom properties."""
    tokens = theme["tokens"]
    decls = "".join(f"{var}:#{tokens[token]};" for token, var in TOKEN_VARS.items())
    return _CSS.replace(_THEME_MARKER, decls)


def render_html(
    slides: list[dict],
    repo: str | None = None,
    title: str = "Deck",
    base_dir: str | None = None,
    theme: dict | None = None,
) -> str:
    """Return one self-contained HTML document — no external assets, no network.

    *theme* is a loaded theme object; omitted, the default palette is loaded from disk.
    """
    problems = validate(slides)
    if problems:
        raise DeckError("deck failed validation:\n  - " + "\n  - ".join(problems))
    body = "".join(_slide_html(s, i, repo, base_dir) for i, s in enumerate(slides))
    css = _theme_css(theme if theme is not None else load_theme(DEFAULT_THEME))
    return _DOCUMENT.format(title=html.escape(title), css=css, body=body)


# ---------------------------------------------------------------------------
# pdf export


def _find_chrome() -> str:
    """Locate a headless-capable Chrome/Chromium, or raise with actionable guidance."""
    for name in ("google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.isfile(mac):
        return mac
    raise DeckError(
        "no Chrome/Chromium found for PDF export. Install Google Chrome, or render HTML "
        "with --html and print it from a browser."
    )


def export_pdf(html_text: str, out_path: str, timeout: float = 120.0) -> str:
    """Print *html_text* to a PDF at *out_path* via headless Chrome. Returns the path.

    Chrome is treated as write-then-abandon rather than a well-behaved subprocess. Observed
    on macOS with a desktop Chrome session already running: ``--print-to-pdf`` writes a
    complete, correct PDF and then the headless process never exits, so waiting on it hangs
    forever. So we poll for the artifact, accept it once its size stops changing, and reap
    the process group we started.

    ``start_new_session=True`` is what makes the cleanup safe: the spawned Chrome gets its own
    process group, so killing that group cannot touch a desktop Chrome the user has open.
    """
    chrome = _find_chrome()
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)  # else a stale file reads as instant success

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "deck.html")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(html_text)
        cmd = [
            chrome,
            # `--headless=new` is required: the legacy `--headless` flag hangs before
            # producing anything on current Chrome builds.
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={os.path.join(tmp, 'profile')}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out_path}",
            f"file://{src}",
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
        try:
            size = _await_stable_file(out_path, proc, timeout)
        finally:
            _reap(proc)

    if size is None:
        raise DeckError(
            f"Chrome produced no PDF within {timeout:.0f}s. Render with --html instead and "
            f"print from a browser."
        )
    return out_path


def _await_stable_file(path: str, proc: subprocess.Popen, timeout: float) -> int | None:
    """Wait until *path* exists and its size is unchanged across two polls. Returns the size."""
    import time

    deadline = time.monotonic() + timeout
    last = -1
    while time.monotonic() < deadline:
        if os.path.isfile(path):
            size = os.path.getsize(path)
            if size > 0 and size == last:
                return size
            last = size
        elif proc.poll() is not None and last < 0:
            return None  # Chrome exited without ever creating the file
        time.sleep(0.25)
    return None


def _reap(proc: subprocess.Popen) -> None:
    """Terminate the spawned Chrome's process group, escalating to SIGKILL if it ignores us."""
    import signal

    if proc.poll() is not None:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue


# ---------------------------------------------------------------------------
# narration

_DRAFT_HEADER = (
    "# DRAFT — deck text pulled in slide order, not finished prose. Refine it, then render "
    "audio. Lines opening with '#' are notes to the writer and are dropped before any "
    "provider speaks the file."
)

# Blocks that carry sentences. Everything else on a slide is layout or a figure, which a
# listener cannot see and a skeleton should not pretend to describe. `stat` and `callout`
# earn their place because a slide can be built from nothing else — dropping them narrates
# an at-a-glance or a hero-ask slide as a bare kicker.
_SPOKEN_BLOCKS = ("heading", "subtitle", "lead", "callout", "quote")

_SPANS = re.compile(r"\{(?:chip\.)?(?:ok|warn|info|accent):([^}]*)\}")


def _spoken(text: Any) -> str:
    """Flatten the deck's inline-markup dialect to plain words — a synthesizer would read
    the asterisks and braces aloud."""
    out = _SPANS.sub(r"\1", str(text))
    out = re.sub(r"`([^`]+)`", r"\1", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"\1", out)
    return " ".join(out.split())


def _sentence(text: Any) -> str:
    """Terminate a deck fragment so the pause a slide got from a line break survives."""
    spoken = _spoken(text)
    if spoken and spoken[-1] not in ".!?:;,":
        spoken += "."
    return spoken


def _slide_narration(slide: dict, number: int) -> str:
    lines = [f"[{number}] {_spoken(slide.get('kicker') or '')}".rstrip()]
    said: list[str] = []
    for block, _at in _walk_blocks(slide.get("blocks"), ""):
        btype = block.get("type")
        if btype in _SPOKEN_BLOCKS:
            for key in ("title", "text"):
                if block.get(key):
                    said.append(_sentence(block[key]))
        elif btype == "bullets":
            said += [
                _sentence(item) for item in block.get("items") or [] if isinstance(item, str)
            ]
        elif btype == "stat":
            # Label before value: a number read cold means nothing without its noun.
            label = _spoken(block.get("label") or "")
            value = _spoken(block.get("value") or "")
            said.append(_sentence(f"{label}: {value}" if label else value))
            said += [_sentence(block[k]) for k in ("delta", "sub") if block.get(k)]
    body = " ".join(s for s in said if s)
    if body:
        lines.append(body)
    notes = _spoken(slide.get("notes") or "")
    if notes:
        lines.append(notes)  # verbatim, and last: they are the author's spoken aside
    return "\n".join(lines)


def narration_script(slides: list[dict], guidance: str | None = None) -> str:
    """A narration skeleton in deck order — one block per slide, inline markup stripped.

    Deliberately a draft: extracted deck text reads like slides, and the refining pass is
    where it becomes speech. *guidance* is the type's ``audio`` string, emitted as a comment
    so its spell-out rules travel with the file rather than living in someone's head.
    """
    out = [_DRAFT_HEADER]
    if guidance:
        out.append(f"# {_spoken(guidance)}")
    out.append("")
    for number, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        out.append(_slide_narration(slide, number))
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# audio


def _uncommented(script_path: str, workdir: str) -> str:
    """Path to *script_path* with its comment lines removed, or the original when it has none.

    The ``#`` convention is this kit's own, so honoring it on the way out is what stops a
    provider from reading the draft header aloud.
    """
    try:
        with open(script_path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        raise DeckError(f"cannot read narration script {script_path}: {exc}") from exc
    kept = [line for line in lines if not line.lstrip().startswith("#")]
    if len(kept) == len(lines):
        return script_path
    path = os.path.join(workdir, "spoken.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(kept)
    return path


def _provider_cmd(provider: str, script_path: str, out_path: str) -> list[str]:
    """The argv for one provider. Anything but ``say`` is a command template — split with
    shlex and run as a list, never through a shell."""
    if provider == DEFAULT_PROVIDER:
        exe = shutil.which(DEFAULT_PROVIDER)
        if exe is None:
            raise DeckError(
                "macOS `say` is not on PATH, so no audio can be rendered here. Ship the "
                "deck plus the written script instead, or point the `audio` key in "
                ".claude/comms.local.md at `none` (audio deliberately off) or at a "
                "command template using {script} and {out}."
            )
        return [
            exe, "-o", out_path, "--file-format=m4af", "--data-format=aac", "-f", script_path,
        ]
    cmd = [
        part.replace("{script}", script_path).replace("{out}", out_path)
        for part in shlex.split(provider)
    ]
    if not cmd:
        raise DeckError(f"audio provider {provider!r} is not a runnable command")
    return cmd


def render_audio(script_path: str, out_path: str, provider: str = DEFAULT_PROVIDER) -> str:
    """Render a narration script to audio through *provider*. Returns the output path.

    The format is whatever the provider writes — ``say`` produces m4a because macOS ships
    no mp3 encoder, and nothing here transcodes. Keeping every non-``say`` provider a
    command template is what stops a vendor SDK from ever becoming a dependency of this kit.
    """
    if not os.path.isfile(script_path):
        raise DeckError(f"narration script not found: {script_path}")
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)  # else a stale file reads as instant success

    with tempfile.TemporaryDirectory() as tmp:
        cmd = _provider_cmd(provider, _uncommented(script_path, tmp), out_path)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        except OSError as exc:
            raise DeckError(f"audio provider will not start: {shlex.join(cmd)} — {exc}") from exc

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise DeckError(
            f"audio provider exited {proc.returncode}: {shlex.join(cmd)}"
            + (f"\n  {detail[-1]}" if detail else "")
        )
    if not os.path.isfile(out_path):
        raise DeckError(f"audio provider wrote no output: {shlex.join(cmd)}")
    return out_path


# ---------------------------------------------------------------------------
# scaffolding


def scaffold(typedef: dict) -> dict:
    """Build a spec scaffold for a type: every required section, at its minimum page count.

    The result is schema-clean and voice-clean as emitted, so an author edits text rather
    than debugging a broken skeleton. Scaffolds are run-time output — write them beside the
    deliverable, never into the kit.
    """
    spec: dict[str, Any] = {
        "type": typedef["id"],
        "title": f"{typedef.get('name', typedef['id'])} - YYYY-MM-DD",
        "repo": "owner/name",
        "sections": {},
    }
    for section in typedef.get("sections") or []:
        low, high = _pages(section)
        count = min(max(low, 1), high)
        name = section.get("name", section["id"])
        slide: dict[str, Any] = {
            "kicker": name.upper(),
            "blocks": [
                {"type": "heading", "text": f"{name} headline goes here"},
                {
                    "type": "bullets",
                    "items": [
                        "Replace with the point, phrased as a fragment",
                        "One line each, no trailing period",
                    ],
                },
            ],
        }
        if section.get("guide"):
            slide["notes"] = section["guide"]
        spec["sections"][section["id"]] = [json.loads(json.dumps(slide)) for _ in range(count)]
    return spec


# ---------------------------------------------------------------------------
# cli


def _pages_label(section: dict) -> str:
    low, high = _pages(section)
    return str(low) if low == high else f"{low}-{high}"


def _cmd_types() -> int:
    typedefs = list_types()
    if not typedefs:
        print("no deliverable types defined", file=sys.stderr)
        return 1
    for typedef in typedefs:
        print(f"{typedef['id']} — {typedef.get('name', '')}")
        if typedef.get("description"):
            print(f"  {typedef['description']}")
        theme = typedef.get("default_theme", DEFAULT_THEME)
        voice_name = typedef.get("default_voice")
        print(f"  defaults: theme {theme}" + (f", voice {voice_name}" if voice_name else ""))
        if typedef.get("slug"):
            print(f"  slug: {typedef['slug']}")
        if voice_name:
            try:
                voice = load_voice(voice_name)
            except DeckError as exc:
                print(f"  voice: {exc}")
            else:
                budgets = voice.get("budgets") or {}
                bits = [f"{k} {v}" for k, v in budgets.items()]
                print(f"  voice: {voice.get('name', voice_name)} — {voice.get('register', '?')}"
                      + (f" · {', '.join(bits)}" if bits else ""))
        if typedef.get("audio"):
            print(f"  audio: {typedef['audio']}")
        print("  sections:")
        for section in typedef.get("sections") or []:
            flag = "" if section.get("required", True) is not False else " (optional)"
            print(f"    {section['id']}  [{_pages_label(section)} page(s)]{flag}"
                  f" — {section.get('name', '')}")
            if section.get("guide"):
                print(f"      {section['guide']}")
        if typedef.get("sources"):
            print("  sources:")
            for source in typedef["sources"]:
                print(f"    {source.get('label', '')}")
                print(f"      {source.get('command', '')}")
        print()
    return 0


def _cmd_new(args: argparse.Namespace) -> int:
    text = json.dumps(scaffold(load_type(args.type)), indent=2) + "\n"
    if not args.out:
        sys.stdout.write(text)
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"✓ spec  -> {args.out}")
    return 0


def _read_spec(path: str) -> dict | None:
    try:
        return load_spec(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"✗ cannot read {path}: {exc}", file=sys.stderr)
        return None


def _waived_note(findings: list, waive: list[str]) -> str:
    """A waive that suppresses nothing is worth knowing about, so report what it caught."""
    hits = [rule for rule, _ in findings if rule in waive]
    if not hits:
        return ""
    return f"  ({len(hits)} waived: {', '.join(sorted(set(hits)))})"


def _report(problems: list[str], findings: list, waive: list[str]) -> int:
    """Print every problem at once — structural first, then unwaived lint. Exit code back."""
    lines = list(problems) + [
        f"{msg} ({rule})" for rule, msg in findings if rule not in waive
    ]
    if not lines:
        return 0
    print(f"✗ {len(lines)} problem(s):", file=sys.stderr)
    for line in lines:
        print(f"  - {line}", file=sys.stderr)
    note = _waived_note(findings, waive)
    if note:
        print(note, file=sys.stderr)
    return 1


def _describe(ctx: dict, count: int) -> str:
    bits = [f"{count} slide(s)"]
    if ctx.get("type_name"):
        bits.append(f"type {ctx['type_name']}")
    bits.append(f"theme {ctx['theme_name']}")
    bits.append(f"voice {ctx['voice_name']}" if ctx.get("voice_name") else "no voice")
    return ", ".join(bits)


def _local_for(path: str) -> dict:
    """House defaults for whichever project *path* sits in."""
    return load_local_config(os.path.dirname(os.path.abspath(path)))


def _cmd_check(args: argparse.Namespace) -> int:
    spec = _read_spec(args.spec)
    if spec is None:
        return 1
    ctx, problems, findings = analyze_spec(spec, local=_local_for(args.spec))
    code = _report(problems, findings, ctx["waive"])
    if code:
        return code
    print(f"✓ spec clean — {_describe(ctx, len(resolve_slides(spec, ctx['typedef'])))}")
    note = _waived_note(findings, ctx["waive"])
    if note:
        print(note)
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    spec = _read_spec(args.spec)
    if spec is None:
        return 1
    overrides = {
        "title": args.title, "repo": args.repo, "theme": args.theme, "voice": args.voice,
    }
    ctx, problems, findings = analyze_spec(spec, overrides, _local_for(args.spec))
    code = _report(problems, findings, ctx["waive"])
    if code:
        return code
    if not args.html and not args.pdf:
        print("nothing to do: pass --html and/or --pdf (or use `check`)", file=sys.stderr)
        return 1

    slides = resolve_slides(spec, ctx["typedef"])
    # Image `src` values are authored relative to the spec file, not the caller's cwd.
    base_dir = os.path.dirname(os.path.abspath(args.spec))
    doc = render_html(
        slides, repo=ctx["repo"], title=ctx["title"], base_dir=base_dir, theme=ctx["theme"]
    )
    print(f"✓ spec clean — {_describe(ctx, len(slides))}")
    note = _waived_note(findings, ctx["waive"])
    if note:
        print(note)
    if args.html:
        os.makedirs(os.path.dirname(os.path.abspath(args.html)) or ".", exist_ok=True)
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(doc)
        print(f"✓ html  -> {args.html}")
    if args.pdf:
        print(f"✓ pdf   -> {export_pdf(doc, args.pdf)}")
    return 0


def _cmd_narrate(args: argparse.Namespace) -> int:
    if bool(args.script) == bool(args.audio):
        print(
            "narrate needs exactly one of --script OUT.txt (a draft, from a spec) or "
            "--audio OUT.m4a (audio, from a script)",
            file=sys.stderr,
        )
        return 1
    local = _local_for(args.source)

    if args.script:
        spec = _read_spec(args.source)
        if spec is None:
            return 1
        # No gate here on purpose: `check` is the gate, and a waivable finding about the
        # DECK's prose must not stand between an author and a narration draft.
        ctx, _problems = resolve_context(spec, local=local)
        slides = resolve_slides(spec, ctx["typedef"])
        text = narration_script(slides, (ctx["typedef"] or {}).get("audio"))
        os.makedirs(os.path.dirname(os.path.abspath(args.script)) or ".", exist_ok=True)
        with open(args.script, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"✓ script -> {args.script}  ({len(slides)} slide(s), draft)")
        print(f"  refine the prose, then: narrate {args.script} --audio out.m4a")
        return 0

    provider = args.provider or local.get("audio") or DEFAULT_PROVIDER
    if provider == "none":
        print("✓ audio deliberately off (provider `none`) — ship the written script")
        return 0
    print(f"✓ audio  -> {render_audio(args.source, args.audio, provider)}")
    return 0


def _cmd_briefings_dir(args: argparse.Namespace) -> int:
    spec = None
    if args.spec:
        spec = _read_spec(args.spec)
        if spec is None:
            return 1
    print(resolve_briefings_dir(args.dir, override=args.override, spec=spec))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="deliver.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="validate a spec — every problem reported at once")
    p_check.add_argument("spec", help="path to a spec (.json, .yaml, .yml)")

    p_build = sub.add_parser("build", help="validate, then render to HTML and/or PDF")
    p_build.add_argument("spec", help="path to a spec (.json, .yaml, .yml)")
    p_build.add_argument("--html", metavar="OUT", help="write self-contained HTML here")
    p_build.add_argument("--pdf", metavar="OUT", help="write a PDF here (needs Chrome)")
    p_build.add_argument("--title", help="document title (overrides the spec)")
    p_build.add_argument("--repo", help="owner/name — linkifies bare #<n> refs")
    p_build.add_argument("--theme", help=f"theme name (overrides the spec): {', '.join(_names(THEMES_DIR))}")
    p_build.add_argument("--voice", help=f"voice name (overrides the spec): {', '.join(_names(VOICES_DIR))}")

    p_narr = sub.add_parser(
        "narrate", help="draft a narration script from a spec, or render a script to audio"
    )
    p_narr.add_argument("source", help="a spec (with --script), or a script (with --audio)")
    p_narr.add_argument(
        "--script", metavar="OUT", help="write a narration draft here, reading SOURCE as a spec"
    )
    p_narr.add_argument(
        "--audio", metavar="OUT", help="render SOURCE (a narration script) to audio here"
    )
    p_narr.add_argument(
        "--provider",
        help="say (default, macOS), none, or a command template using {script} and {out}",
    )

    p_bdir = sub.add_parser(
        "briefings-dir", help="resolve <briefings-dir> for a project and print it"
    )
    p_bdir.add_argument("dir", help="project directory to resolve from")
    p_bdir.add_argument("--spec", metavar="SPEC", help="a spec file — its 'briefings_dir' field outranks project local")
    p_bdir.add_argument("--override", metavar="DIR", help="CLI override — outranks everything else")

    sub.add_parser("types", help="list the deliverable types, their sections and budgets")

    p_new = sub.add_parser("new", help="print a spec scaffold for a type")
    p_new.add_argument("type", help=f"one of: {', '.join(_names(TYPES_DIR))}")
    p_new.add_argument("-o", "--out", metavar="OUT", help="write here instead of stdout")

    args = parser.parse_args(argv)
    try:
        if args.command == "types":
            return _cmd_types()
        if args.command == "new":
            return _cmd_new(args)
        if args.command == "check":
            return _cmd_check(args)
        if args.command == "narrate":
            return _cmd_narrate(args)
        if args.command == "briefings-dir":
            return _cmd_briefings_dir(args)
        return _cmd_build(args)
    except DeckError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# assets


_CSS = """
:root{/*theme*/
--mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--page-bg);
font:16px/1.5 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--fg)}
.slide{position:relative;width:1280px;height:720px;margin:0 auto 24px;padding:64px 80px;
background:var(--bg);display:flex;flex-direction:column;overflow:hidden;page-break-after:always}
.slide:last-child{margin-bottom:0}
.layout-center .body{justify-content:center}
.layout-top .body{justify-content:flex-start}
.layout-fill .body{justify-content:space-between}
.body{flex:1;display:flex;flex-direction:column;gap:18px;min-height:0}
.kicker{font-family:var(--mono);font-size:14px;font-weight:600;letter-spacing:.12em;
text-transform:uppercase;color:var(--accent-2);flex:none;margin-bottom:-4px}
.footer{font-family:var(--mono);font-size:13px;color:var(--muted);
padding-top:12px;margin-top:18px;flex:none}
h1{font-size:44px;line-height:1.15;margin:0;font-weight:680;letter-spacing:-.015em}
h2{font-size:32px;line-height:1.2;margin:0;font-weight:680;letter-spacing:-.01em}
.subtitle{font-size:21px;line-height:1.45;margin:0;color:var(--muted)}
.lead{font-size:22px;line-height:1.45;margin:0;max-width:34em}
ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:12px}
ul li{font-size:19px;line-height:1.45;position:relative;padding-left:1.5em}
ul li::before{content:"\\25B8";position:absolute;left:.25em;top:-.03em;
color:var(--accent);font-size:.85em}
.divider{border:0;border-top:1px solid var(--line);margin:4px 0;width:100%}
.columns{display:flex;gap:36px;align-items:flex-start}
.col{flex:1;min-width:0;display:flex;flex-direction:column;gap:14px}
.stat{display:flex;flex-direction:column;gap:4px}
.stat-value{font-size:56px;line-height:1;font-weight:680;letter-spacing:-.02em;color:var(--accent)}
.stat-label{font-size:17px;font-weight:600}
.stat-sub{font-size:15px;color:var(--muted);line-height:1.35}
.stat-delta{font-size:15px;font-weight:600}
.trend-up{color:var(--pos)}.trend-down{color:var(--neg)}.trend-flat{color:var(--muted)}
.callout{border-left:4px solid var(--accent);background:var(--bg-alt);
padding:18px 22px;border-radius:0 8px 8px 0}
.callout-accent{border-color:var(--accent)}
.callout-warn{border-color:var(--warn)}
.callout-success{border-color:var(--pos)}
.callout-title{font-weight:680;margin-bottom:6px;font-size:18px}
.callout-text{font-size:18px;line-height:1.45}
.callout-lg .callout-text{font-size:22px}
.callout-hero{flex:1;display:flex;flex-direction:column;justify-content:center}
.callout-hero .callout-text{font-size:30px;line-height:1.3}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;
background:var(--code-bg);padding:.12em .38em;border-radius:4px}
strong{font-weight:680}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid var(--line)}
.tint-accent{color:var(--accent)}.tint-info{color:var(--accent-2)}
.tint-ok{color:var(--pos)}.tint-warn{color:var(--warn)}
.chip{display:inline-block;font-size:.78em;font-weight:700;text-transform:uppercase;
letter-spacing:.04em;padding:.16em .5em;border-radius:999px;color:var(--text-inverse);
vertical-align:.08em}
.chip-ok{background:var(--pos)}.chip-warn{background:var(--warn)}
.chip-info{background:var(--accent-2)}.chip-accent{background:var(--accent)}
.notes{display:none}

table{border-collapse:collapse;width:100%;font-size:16px}
th,td{text-align:left;padding:9px 14px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:680;font-size:14px;letter-spacing:.03em;text-transform:uppercase;
color:var(--accent);border-bottom:2px solid var(--accent)}
tbody tr:nth-child(even){background:var(--bg-alt)}

ol.steps{list-style:none;counter-reset:s;margin:0;padding:0;display:flex;
flex-direction:column;gap:14px}
ol.steps li{counter-increment:s;position:relative;padding-left:52px}
ol.steps li::before{content:counter(s);position:absolute;left:0;top:-2px;width:34px;height:34px;
border-radius:50%;background:var(--accent);color:var(--text-inverse);font-weight:700;font-size:16px;
display:flex;align-items:center;justify-content:center}
.step-title{font-size:19px;font-weight:650;line-height:1.3}
.step-detail{font-size:16px;color:var(--muted);line-height:1.4;margin-top:3px}

ul.timeline{list-style:none;margin:0;padding:26px 0 0;display:flex;gap:0;
position:relative;justify-content:space-between}
ul.timeline::before{content:"";position:absolute;top:32px;left:0;right:0;height:2px;
background:var(--line)}
ul.timeline li{flex:1;position:relative;padding:26px 12px 0;text-align:center}
ul.timeline li::before{content:"";position:absolute;top:-6px;left:50%;transform:translateX(-50%);
width:14px;height:14px;border-radius:50%;background:var(--accent);
box-shadow:0 0 0 4px var(--bg)}
.tl-label{font-size:13px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
color:var(--accent)}
.tl-title{font-size:17px;font-weight:650;margin-top:4px;line-height:1.3}
.tl-detail{font-size:14px;color:var(--muted);margin-top:3px;line-height:1.4}

.matrix-wrap{position:relative;padding:0 0 26px 30px;flex:1;min-height:0;display:flex}
.matrix{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:12px;flex:1}
.quad{background:var(--bg-alt);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.quad-title{font-weight:680;font-size:16px;color:var(--accent);margin-bottom:6px}
.quad ul{gap:5px}
.quad li{font-size:15px;line-height:1.35;padding-left:1.2em}
.axis{position:absolute;display:flex;justify-content:space-between;font-size:12px;
font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.axis-x{bottom:0;left:30px;right:0}
.axis-y{top:0;bottom:26px;left:0;flex-direction:column;writing-mode:vertical-rl;
transform:rotate(180deg)}

blockquote{margin:0;padding:6px 0 6px 26px;border-left:4px solid var(--accent);
font-size:24px;line-height:1.4;font-style:italic;color:var(--fg)}
.quote-by{font-size:16px;font-style:normal;color:var(--muted);margin-top:10px}
.quote-by::before{content:"— "}

pre.code{background:var(--code-bg);border-radius:8px;padding:16px 20px;margin:0;
overflow:hidden;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:15px;
line-height:1.5}
pre.code code{background:none;padding:0}

.image-block,.svg-block{display:flex;justify-content:center;align-items:center;min-height:0}
.image-block img{max-width:100%;max-height:420px;object-fit:contain}
.svg-block svg{max-width:100%;max-height:420px}

.chart{display:flex;justify-content:center}
.chart svg{max-width:100%;max-height:300px}
.ck-label{font-size:13px;fill:var(--muted);text-anchor:middle}
.ck-value{font-size:14px;font-weight:650;fill:var(--fg);text-anchor:middle}
.chart g .ck-label{text-anchor:start}

@page{size:1280px 720px;margin:0}
@media print{html,body{background:var(--bg)}.slide{margin:0;box-shadow:none}}
"""

_DOCUMENT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{css}</style></head>
<body>{body}</body></html>
"""


if __name__ == "__main__":
    sys.exit(main())
