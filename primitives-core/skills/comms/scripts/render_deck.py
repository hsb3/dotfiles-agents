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
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

# Block types this renderer implements — the full set found across the real decks in
# _meta/briefings/ (census, 2026-08-06: 22 decks). Anything outside this set fails loudly
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


def render_html(
    slides: list[dict],
    repo: str | None = None,
    title: str = "Deck",
    base_dir: str | None = None,
) -> str:
    """Return one self-contained HTML document — no external assets, no network."""
    problems = validate(slides)
    if problems:
        raise DeckError("deck failed validation:\n  - " + "\n  - ".join(problems))
    body = "".join(_slide_html(s, i, repo, base_dir) for i, s in enumerate(slides))
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
--accent-2:#1f6093;--line:#dbe3ec;--code-bg:#e9eff5;--pos:#1a7f37;--neg:#b3261e;--warn:#9a6700;
--mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#5b6b7e;
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
letter-spacing:.04em;padding:.16em .5em;border-radius:999px;color:#fff;vertical-align:.08em}
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
border-radius:50%;background:var(--accent);color:#fff;font-weight:700;font-size:16px;
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

.chart{--series-0:#1a4e8a;--series-1:#1f6093;--series-2:#4d8fc4;--series-3:#87b4d8;
--series-4:#b9d3e8;display:flex;justify-content:center}
.chart svg{max-width:100%;max-height:300px}
.ck-label{font-size:13px;fill:var(--muted);text-anchor:middle}
.ck-value{font-size:14px;font-weight:650;fill:var(--fg);text-anchor:middle}
.chart g .ck-label{text-anchor:start}

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
        # Image `src` values are authored relative to the deck file, not the caller's cwd.
        base_dir = os.path.dirname(os.path.abspath(args.slides))
        doc = render_html(slides, repo=args.repo, title=args.title, base_dir=base_dir)
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
