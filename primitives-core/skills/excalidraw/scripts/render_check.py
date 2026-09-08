#!/usr/bin/env python3
"""Render an .excalidraw scene headless, screenshot it, and lint it for defects.

An authored scene is written blind: the model that emits the JSON never sees the canvas,
so a label that escaped its box or an arrow bound to an id that no longer exists ships
looking fine in the diff and broken on the whiteboard. This closes the loop offline —
render, screenshot, lint, fix, render again — with no network, no install, and no
upstream renderer.

Three stages, each usable alone:

  * ``render_svg`` walks the scene's ``elements`` and draws the supported subset
    (rectangle, ellipse, diamond, line, arrow, text, container labels, frame) to a
    self-contained SVG. First-party and deliberately plain: geometry and layout are
    exact, the hand-drawn wobble is not reproduced. It answers "is this laid out right",
    not "is this pretty".
  * ``lint_scene`` reads the scene as data and reports the defects a renderer cannot
    show you a cause for: overlapping shapes, a binding naming a missing element, a
    label with no back-reference, an element escaping its frame, text too wide for its
    container.
  * ``screenshot`` rasterizes the SVG through headless Chromium via Playwright, which
    must be resolvable by node (globally installed is fine — see ``--node-path``).

Outputs go to a scratch directory, never next to the scene: a render is a derived
artifact and tracking it invites a stale one. Exit 0 = rendered and clean; exit 1 = it
rendered but the lint found defects (both files are still written, which is the point —
you look at the picture and read the finding side by side).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(SKILL_ROOT, "examples", "request-path.excalidraw")

SHAPES = ("rectangle", "ellipse", "diamond", "image")
PAD = 24
# Virgil is wider than a system sans; 0.55em per character tracks it closely enough to
# catch overflow without pulling in a font metrics library.
CHAR_EM = 0.55
LABEL_PAD = 8


# --- geometry ----------------------------------------------------------------------


def _live(scene):
    return [e for e in scene.get("elements", []) if not e.get("isDeleted")]


def _box(el):
    """(x0, y0, x1, y1) in scene coordinates, points included for linear elements."""
    x, y = float(el.get("x", 0)), float(el.get("y", 0))
    pts = el.get("points")
    if pts:
        xs = [x + float(p[0]) for p in pts]
        ys = [y + float(p[1]) for p in pts]
        return min(xs), min(ys), max(xs), max(ys)
    return x, y, x + float(el.get("width", 0)), y + float(el.get("height", 0))


def _overlap(a, b):
    ax0, ay0, ax1, ay1 = _box(a)
    bx0, by0, bx1, by1 = _box(b)
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def _text_width(el):
    longest = max((len(line) for line in str(el.get("text", "")).splitlines()), default=0)
    return longest * float(el.get("fontSize", 20)) * CHAR_EM


def scene_bounds(elements):
    boxes = [_box(e) for e in elements] or [(0, 0, 100, 100)]
    return (
        min(b[0] for b in boxes) - PAD,
        min(b[1] for b in boxes) - PAD,
        max(b[2] for b in boxes) + PAD,
        max(b[3] for b in boxes) + PAD,
    )


# --- lint --------------------------------------------------------------------------


def lint_scene(scene):
    """Findings as ``(code, message)``, sorted and deduplicated.

    Five rules, each one a mistake an authored scene makes silently. None of them needs
    to look at pixels — a scene is data, and every one of these is a broken reference or
    a geometry contradiction visible in the JSON.
    """
    els = _live(scene)
    by_id = {e.get("id"): e for e in els}
    out = []

    shapes = [e for e in els if e.get("type") in SHAPES]
    for i, a in enumerate(shapes):
        for b in shapes[i + 1:]:
            if _overlap(a, b):
                out.append((
                    "overlap",
                    f"{a['id']} and {b['id']} overlap — one is drawn on top of the other",
                ))

    for el in els:
        if el.get("type") not in ("arrow", "line"):
            continue
        for side in ("startBinding", "endBinding"):
            binding = el.get(side) or {}
            target = binding.get("elementId")
            if target and target not in by_id:
                out.append((
                    "dangling-arrow",
                    f"{el['id']}.{side} names `{target}`, which is not in the scene",
                ))

    for el in els:
        if el.get("type") != "text":
            continue
        container_id = el.get("containerId")
        if not container_id:
            continue
        container = by_id.get(container_id)
        if container is None:
            out.append((
                "orphan-label",
                f"{el['id']}.containerId names `{container_id}`, which is not in the scene",
            ))
            continue
        refs = [b.get("id") for b in container.get("boundElements") or []]
        if el.get("id") not in refs:
            out.append((
                "orphan-label",
                f"{el['id']} is bound to {container_id}, but {container_id}."
                "boundElements has no back-reference — the label will float free",
            ))
        room = float(container.get("width", 0)) - 2 * LABEL_PAD
        if _text_width(el) > room:
            out.append((
                "text-overflow",
                f"{el['id']} needs ~{_text_width(el):.0f}px but {container_id} offers "
                f"{room:.0f}px — the text will spill or force the container taller",
            ))

    for el in els:
        frame_id = el.get("frameId")
        if not frame_id:
            continue
        frame = by_id.get(frame_id)
        if frame is None:
            out.append((
                "frame-escape",
                f"{el['id']}.frameId names `{frame_id}`, which is not in the scene",
            ))
            continue
        ex0, ey0, ex1, ey1 = _box(el)
        fx0, fy0, fx1, fy1 = _box(frame)
        if ex0 < fx0 or ey0 < fy0 or ex1 > fx1 or ey1 > fy1:
            out.append((
                "frame-escape",
                f"{el['id']} sits outside frame {frame_id} — it renders clipped or "
                "detached from the group",
            ))

    return sorted(set(out))


# --- defects -----------------------------------------------------------------------


def _find(elements, eid):
    for el in elements:
        if el.get("id") == eid:
            return el
    return None


def introduce_defect(scene, kind):
    """Return a copy of the scene with one named defect injected."""
    scene = json.loads(json.dumps(scene))
    els = scene["elements"]
    if kind == "overlap":
        _find(els, "db")["x"] = 470
        _find(els, "db-label")["x"] = 482
    elif kind == "orphan-label":
        box = _find(els, "api")
        box["boundElements"] = [
            b for b in box["boundElements"] if b.get("id") != "api-label"
        ]
    elif kind == "dangling-arrow":
        _find(els, "arrow-2")["endBinding"] = {"elementId": "warehouse", "focus": 0, "gap": 4}
    elif kind == "frame-escape":
        _find(els, "cache")["y"] = 400
        _find(els, "cache-label")["y"] = 420
    elif kind == "text-overflow":
        long_text = "Postgres 17 primary with read replica"
        lab = _find(els, "db-label")
        lab["text"] = lab["originalText"] = long_text
    else:
        raise SystemExit(f"unknown defect: {kind}")
    return scene


DEFECTS = ("overlap", "orphan-label", "dangling-arrow", "frame-escape", "text-overflow")


# --- render ------------------------------------------------------------------------


FONT_STACK = "Chalkboard SE, Bradley Hand, Segoe Print, Comic Sans MS, cursive"
DASHES = {"dashed": "12 8", "dotted": "2 6"}


def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _stroke(el):
    out = [
        f'stroke="{el.get("strokeColor") or "#1e1e1e"}"',
        f'stroke-width="{el.get("strokeWidth", 2)}"',
        'stroke-linecap="round"',
        'stroke-linejoin="round"',
        f'opacity="{float(el.get("opacity", 100)) / 100:.2f}"',
    ]
    dash = DASHES.get(el.get("strokeStyle"))
    if dash:
        out.append(f'stroke-dasharray="{dash}"')
    return " ".join(out)


def _fill(el):
    bg = el.get("backgroundColor")
    if not bg or bg == "transparent":
        return 'fill="none"'
    # `hachure` and `cross-hatch` are scribbled fills upstream; flat fill is the honest
    # stand-in — it shows the same coverage without pretending to be the real texture.
    return f'fill="{bg}"'


def _arrowhead(x1, y1, x2, y2, color, size=12):
    angle = math.atan2(y2 - y1, x2 - x1)
    pts = [
        (x2, y2),
        (x2 - size * math.cos(angle - 0.42), y2 - size * math.sin(angle - 0.42)),
        (x2 - size * math.cos(angle + 0.42), y2 - size * math.sin(angle + 0.42)),
    ]
    joined = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    return f'<polygon points="{joined}" fill="{color}" />'


def _draw_text(el, by_id):
    size = float(el.get("fontSize", 20))
    lines = str(el.get("text", "")).splitlines() or [""]
    color = el.get("strokeColor") or "#1e1e1e"
    container = by_id.get(el.get("containerId"))
    if container is not None:
        cx0, cy0, cx1, cy1 = _box(container)
        anchor, tx = "middle", (cx0 + cx1) / 2
        ty = (cy0 + cy1) / 2 - (len(lines) - 1) * size * 0.625 + size * 0.35
    else:
        anchor, tx = "start", float(el.get("x", 0))
        ty = float(el.get("y", 0)) + size * 0.9
    out = []
    for n, line in enumerate(lines):
        out.append(
            f'<text x="{tx:.1f}" y="{ty + n * size * 1.25:.1f}" fill="{color}" '
            f'font-size="{size}" font-family="{FONT_STACK}" '
            f'text-anchor="{anchor}">{_esc(line)}</text>'
        )
    return out


def _draw(el, by_id):
    kind = el.get("type")
    x0, y0, x1, y1 = _box(el)
    w, h = x1 - x0, y1 - y0
    if kind == "frame":
        name = _esc(el.get("name") or "")
        return [
            f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="none" '
            'stroke="#bbbbbb" stroke-width="1" stroke-dasharray="6 6" rx="4" />',
            f'<text x="{x0}" y="{y0 - 8}" fill="#999999" font-size="14" '
            f'font-family="{FONT_STACK}">{name}</text>',
        ]
    if kind == "rectangle":
        rx = 12 if el.get("roundness") else 0
        return [f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="{rx}" '
                f'{_fill(el)} {_stroke(el)} />']
    if kind == "ellipse":
        return [f'<ellipse cx="{x0 + w / 2}" cy="{y0 + h / 2}" rx="{w / 2}" '
                f'ry="{h / 2}" {_fill(el)} {_stroke(el)} />']
    if kind == "diamond":
        pts = f"{x0 + w / 2},{y0} {x1},{y0 + h / 2} {x0 + w / 2},{y1} {x0},{y0 + h / 2}"
        return [f'<polygon points="{pts}" {_fill(el)} {_stroke(el)} />']
    if kind in ("arrow", "line"):
        ex, ey = float(el.get("x", 0)), float(el.get("y", 0))
        pts = [(ex + float(p[0]), ey + float(p[1])) for p in el.get("points") or []]
        if len(pts) < 2:
            return []
        joined = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        color = el.get("strokeColor") or "#1e1e1e"
        out = [f'<polyline points="{joined}" fill="none" {_stroke(el)} />']
        if el.get("endArrowhead"):
            out.append(_arrowhead(*pts[-2], *pts[-1], color))
        if el.get("startArrowhead"):
            out.append(_arrowhead(*pts[1], *pts[0], color))
        return out
    if kind == "text":
        return _draw_text(el, by_id)
    if kind == "image":
        return [f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#f1f3f5" '
                'stroke="#adb5bd" stroke-dasharray="4 4" />',
                f'<text x="{x0 + w / 2}" y="{y0 + h / 2}" text-anchor="middle" '
                f'fill="#868e96" font-size="14" font-family="{FONT_STACK}">'
                f'[image {_esc(el.get("id"))}]</text>']
    # Anything unsupported is outlined rather than dropped: a silently missing element
    # is the one failure mode a render loop must never have.
    return [f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="none" '
            f'stroke="#fa5252" stroke-dasharray="3 3" />',
            f'<text x="{x0 + 4}" y="{y0 + 14}" fill="#fa5252" font-size="12" '
            f'font-family="{FONT_STACK}">unsupported: {_esc(kind)}</text>']


def render_svg(scene):
    """A self-contained SVG of the scene — geometry exact, sketch texture not attempted."""
    els = _live(scene)
    by_id = {e.get("id"): e for e in els}
    x0, y0, x1, y1 = scene_bounds(els)
    width, height = x1 - x0, y1 - y0
    bg = (scene.get("appState") or {}).get("viewBackgroundColor") or "#ffffff"
    body = []
    for el in els:
        body.extend(_draw(el, by_id))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">'
        f'<rect width="100%" height="100%" fill="{bg}" />'
        f'<g transform="translate({-x0:.1f},{-y0:.1f})">'
        + "".join(body)
        + "</g></svg>\n"
    )


# --- screenshot --------------------------------------------------------------------


DRIVER = """
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: Number(process.env.EXC_W), height: Number(process.env.EXC_H) },
    deviceScaleFactor: Number(process.env.EXC_SCALE),
  });
  await page.goto('file://' + process.env.EXC_SVG);
  await page.screenshot({ path: process.env.EXC_PNG });
  await browser.close();
})();
"""


def node_path(explicit=None):
    """Where node should look for playwright: flag, env, then the global root."""
    if explicit:
        return explicit
    env = os.environ.get("EXCALIDRAW_NODE_PATH")
    if env:
        return env
    npm = shutil.which("npm")
    if not npm:
        return ""
    try:
        out = subprocess.run(
            [npm, "root", "-g"], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip()


def screenshot(svg_path, png_path, width, height, scale=2, explicit_node_path=None):
    """Rasterize the SVG with headless Chromium. Returns the png path."""
    node = shutil.which("node")
    if not node:
        raise SystemExit("node not found on PATH — needed to drive Playwright")
    with tempfile.TemporaryDirectory() as work:
        driver = os.path.join(work, "shot.js")
        with open(driver, "w", encoding="utf-8") as fh:
            fh.write(DRIVER)
        env = dict(os.environ)
        env.update(
            NODE_PATH=node_path(explicit_node_path),
            EXC_SVG=svg_path,
            EXC_PNG=png_path,
            EXC_W=str(int(width)),
            EXC_H=str(int(height)),
            EXC_SCALE=str(scale),
        )
        run = subprocess.run(
            [node, driver], env=env, capture_output=True, text=True, timeout=180
        )
    if run.returncode != 0:
        raise SystemExit(
            "headless render failed — is playwright resolvable by node?\n"
            f"NODE_PATH={env['NODE_PATH']}\n{(run.stderr or run.stdout).strip()}"
        )
    return png_path


# --- self-check --------------------------------------------------------------------


def self_test():
    """Every injectable defect is caught, and the shipped sample is clean."""
    with open(SAMPLE, encoding="utf-8") as fh:
        scene = json.load(fh)
    assert lint_scene(scene) == [], f"sample is not clean: {lint_scene(scene)}"
    for kind in DEFECTS:
        codes = [c for c, _ in lint_scene(introduce_defect(scene, kind))]
        assert kind in codes, f"{kind}: not detected (got {codes})"
    svg = render_svg(scene)
    assert svg.startswith("<svg"), "render did not produce an svg"
    for needle in ("<rect", "<ellipse", "<polyline", "<text", "Browser"):
        assert needle in svg, f"render is missing {needle}"
    print(f"✓ self-check passed — {len(DEFECTS)} defects detected, sample renders clean")
    return 0


# --- cli ---------------------------------------------------------------------------


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Render an .excalidraw scene headless, screenshot it, and lint it.",
        epilog="Exit 0 = rendered clean; 1 = rendered with lint findings.",
    )
    ap.add_argument("scene", nargs="?", default=SAMPLE,
                    help="path to a .excalidraw scene (default: the bundled sample)")
    ap.add_argument("--out", help="output directory (default: a fresh temp dir)")
    ap.add_argument("--defect", choices=DEFECTS,
                    help="inject this defect into a copy of the scene before rendering")
    ap.add_argument("--lint-only", action="store_true", help="skip render and screenshot")
    ap.add_argument("--no-screenshot", action="store_true",
                    help="write the SVG but skip Playwright")
    ap.add_argument("--scale", type=int, default=2, help="screenshot pixel ratio (default 2)")
    ap.add_argument("--node-path", help="NODE_PATH for resolving playwright "
                                        "(default: $EXCALIDRAW_NODE_PATH, else `npm root -g`)")
    ap.add_argument("--self-test", action="store_true",
                    help="run the built-in lint/render checks and exit")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    with open(args.scene, encoding="utf-8") as fh:
        scene = json.load(fh)
    stem = os.path.splitext(os.path.basename(args.scene))[0]
    if args.defect:
        scene = introduce_defect(scene, args.defect)
        stem = f"{stem}.{args.defect}"

    findings = lint_scene(scene)

    if not args.lint_only:
        out = args.out or tempfile.mkdtemp(prefix="excalidraw-render.")
        os.makedirs(out, exist_ok=True)
        svg = render_svg(scene)
        svg_path = os.path.join(out, stem + ".svg")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"svg   {svg_path}")
        if args.defect:
            scene_path = os.path.join(out, stem + ".excalidraw")
            with open(scene_path, "w", encoding="utf-8") as fh:
                json.dump(scene, fh, indent=2)
            print(f"scene {scene_path}")
        if not args.no_screenshot:
            x0, y0, x1, y1 = scene_bounds(_live(scene))
            png = screenshot(svg_path, os.path.join(out, stem + ".png"),
                             x1 - x0, y1 - y0, args.scale, args.node_path)
            print(f"png   {png}")

    if findings:
        print(f"\n✗ {len(findings)} defect(s):")
        for code, message in findings:
            print(f"  [{code}] {message}")
        return 1
    print("\n✓ lint clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
