#!/usr/bin/env python3
"""Render a comms ``slides.json`` deck to self-contained HTML, and optionally to PDF.

Why this exists: the comms skill previously depended on the deck-builder MCP server for the
three self-comms (morning briefing, end-of-day wrap-up, weekly planning). That made the skill
uninstallable without a local MCP server. This module re-authors the render/validate/export
path as a first-party script so the skill stands alone — the path ADR 0015 prescribes for
promoting an external capability to first-party ("re-author, don't copy").

The ``slides.json`` shape is kept compatible with the decks already sitting in
``_meta/briefings/`` so prior deliverables still render.

Key entry points: ``validate`` (schema conformance), ``render_html`` (self-contained
document), ``export_pdf`` (headless-Chrome print). Stdlib only — no install step, matching
the repo-wide zero-install invariant.

Limitation: unsupported block types are a hard error, never a silent drop. A status deck that
quietly loses a slide is worse than one that fails to build.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

# Block types this renderer implements. The upstream schema is wider; comms only ever
# authored these six. Anything else fails loudly rather than rendering a lie.
SUPPORTED_BLOCKS = frozenset(
    {"heading", "subtitle", "lead", "bullets", "columns", "stat", "callout", "divider"}
)
SLIDE_KEYS = frozenset({"id", "kicker", "notes", "layout", "footer", "fit", "balance", "blocks"})
LAYOUTS = frozenset({"center", "top", "fill"})
CALLOUT_VARIANTS = frozenset({"info", "accent", "warn", "success"})
TRENDS = {"up": "▲", "down": "▼", "flat": "→"}

STAGE_W, STAGE_H = 1280, 720


class DeckError(Exception):
    """A deck failed validation, or the environment can't satisfy an export."""


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
# validation


def validate(slides: Any) -> list[str]:
    """Return a list of human-readable problems; empty means the deck is conformant."""
    problems: list[str] = []
    if not isinstance(slides, list):
        return ["top level must be a JSON array of slides"]
    if not slides:
        return ["deck has zero slides"]

    for i, slide in enumerate(slides):
        where = f"slide {i + 1}"
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
# rendering


def _block_html(block: dict, repo: str | None) -> str:
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
    if btype == "columns":
        cols = "".join(
            f'<div class="col">{"".join(_block_html(b, repo) for b in col)}</div>'
            for col in block["columns"]
        )
        return f'<div class="columns">{cols}</div>'
    raise DeckError(f"unsupported block type {btype!r}")  # pragma: no cover - validated earlier


def _slide_html(slide: dict, index: int, repo: str | None) -> str:
    layout = slide.get("layout", "center")
    body = "".join(_block_html(b, repo) for b in slide["blocks"])
    head = f'<div class="kicker">{_inline(slide["kicker"], repo)}</div>' if slide.get("kicker") else ""
    foot = f'<div class="footer">{_inline(slide["footer"], repo)}</div>' if slide.get("footer") else ""
    notes = ""
    if slide.get("notes"):
        notes = f'<div class="notes">{_inline(slide["notes"], repo)}</div>'
    return (
        f'<section class="slide layout-{layout}" data-index="{index}">'
        f'{head}<div class="body">{body}</div>{foot}{notes}</section>'
    )


def render_html(slides: list[dict], repo: str | None = None, title: str = "Deck") -> str:
    """Return one self-contained HTML document — no external assets, no network."""
    problems = validate(slides)
    if problems:
        raise DeckError("deck failed validation:\n  - " + "\n  - ".join(problems))
    body = "".join(_slide_html(s, i, repo) for i, s in enumerate(slides))
    return _DOCUMENT.format(title=html.escape(title), css=_CSS, body=body)


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
# assets


_CSS = """
:root{--bg:#fff;--bg-alt:#f3f6fa;--fg:#11243a;--muted:#5b6b7e;--accent:#1a4e8a;
--accent-2:#1f6093;--line:#dbe3ec;--code-bg:#e9eff5;--pos:#1a7f37;--neg:#b3261e;--warn:#9a6700}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#5b6b7e;
font:16px/1.5 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--fg)}
.slide{position:relative;width:1280px;height:720px;margin:0 auto 24px;padding:64px 80px;
background:var(--bg);display:flex;flex-direction:column;overflow:hidden;page-break-after:always}
.slide:last-child{margin-bottom:0}
.layout-center .body{justify-content:center}
.layout-top .body{justify-content:flex-start}
.layout-fill .body{justify-content:space-between}
.body{flex:1;display:flex;flex-direction:column;gap:20px;min-height:0}
.kicker{font-size:14px;font-weight:700;letter-spacing:.10em;text-transform:uppercase;
color:var(--accent);margin-bottom:20px;flex:none}
.footer{font-size:13px;color:var(--muted);border-top:1px solid var(--line);
padding-top:12px;margin-top:20px;flex:none}
h1{font-size:44px;line-height:1.15;margin:0;font-weight:650;letter-spacing:-.01em}
h2{font-size:24px;line-height:1.25;margin:0;font-weight:650;color:var(--accent)}
.subtitle{font-size:21px;line-height:1.45;margin:0;color:var(--muted)}
.lead{font-size:22px;line-height:1.45;margin:0;max-width:34em}
ul{margin:0;padding-left:1.3em;display:flex;flex-direction:column;gap:12px}
li{font-size:19px;line-height:1.45}
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
letter-spacing:.04em;padding:.16em .5em;border-radius:999px;color:#fff;vertical-align:.08em}
.chip-ok{background:var(--pos)}.chip-warn{background:var(--warn)}
.chip-info{background:var(--accent-2)}.chip-accent{background:var(--accent)}
.notes{display:none}
@page{size:1280px 720px;margin:0}
@media print{html,body{background:#fff}.slide{margin:0;box-shadow:none}}
"""

_DOCUMENT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{css}</style></head>
<body>{body}</body></html>
"""


# ---------------------------------------------------------------------------
# cli


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("slides", help="path to slides.json")
    parser.add_argument("--validate", action="store_true", help="check the schema and exit")
    parser.add_argument("--html", metavar="OUT", help="write self-contained HTML here")
    parser.add_argument("--pdf", metavar="OUT", help="write a PDF here (needs Chrome)")
    parser.add_argument("--repo", help="owner/name — linkifies bare #<n> refs")
    parser.add_argument("--title", default="Deck", help="document title")
    args = parser.parse_args(argv)

    try:
        with open(args.slides, encoding="utf-8") as fh:
            slides = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"✗ cannot read {args.slides}: {exc}", file=sys.stderr)
        return 1

    problems = validate(slides)
    if problems:
        print(f"✗ {len(problems)} validation problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"✓ schema clean — {len(slides)} slide(s)")
    if args.validate:
        return 0
    if not args.html and not args.pdf:
        print("nothing to do: pass --html and/or --pdf (or --validate)", file=sys.stderr)
        return 1

    try:
        doc = render_html(slides, repo=args.repo, title=args.title)
        if args.html:
            os.makedirs(os.path.dirname(os.path.abspath(args.html)) or ".", exist_ok=True)
            with open(args.html, "w", encoding="utf-8") as fh:
                fh.write(doc)
            print(f"✓ html  -> {args.html}")
        if args.pdf:
            print(f"✓ pdf   -> {export_pdf(doc, args.pdf)}")
    except DeckError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
