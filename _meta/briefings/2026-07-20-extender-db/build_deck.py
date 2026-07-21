"""Build the Extender-DB briefing deck (16 slides) with python-pptx.

Fallback build path per the pptx-themes skill brief: pptxgenjs is not
installed in this repo/environment, so this script uses python-pptx while
applying the pptx-themes palette (carbon-white), typography (Avenir Next),
and narrative rules (lede-first explanatory register, native shape charts,
labeled diagram) by hand.

Run:
    uv run --with python-pptx python3 build_deck.py

Content is sourced verbatim (facts/wording preserved) from deck-content.md
and deck-data.json in this same directory; markdown list syntax (leading
"- ", "**", backticks) is stripped as formatting, not content.
"""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

# ---------------------------------------------------------------------------
# Theme: carbon-white (IBM Carbon) — "systems-grade" — chosen for this deck's
# subject (a database, an ingest pipeline, an assessment engine) per
# references/color-palettes.md's selection table: "Engineering readouts,
# platform briefings, technical documentation decks."
# ---------------------------------------------------------------------------
THEME = {
    "canvas": "F4F4F4",
    "surface": "FFFFFF",
    "surfaceElevated": "F4F4F4",
    "surfaceInverse": "393939",
    "textPrimary": "161616",
    "textSecondary": "525252",
    "textInverse": "FFFFFF",
    "textAccent": "0F62FE",
    "border": "C6C6C6",
    "borderStrong": "8D8D8D",
    "gridline": "E0E0E0",
    "accentPrimary": "0F62FE",
    "accentSecondary": "8A3FFC",
    "accentTertiary": "009D9A",
    "accentSoft": "D0E2FF",
    "dataPrimary": "0F62FE",
    "dataSecondary": "009D9A",
    "dataTertiary": "8A3FFC",
    "dataQuaternary": "D02670",
    "dataPositive": "24A148",
    "dataNegative": "DA1E28",
    "dataNeutral": "8D8D8D",
    "dataTrack": "E0E0E0",
    "positive": "24A148",
    "caution": "F1C21B",
    "negative": "DA1E28",
    "informational": "0043CE",
    "shadow": "000000",
}
FONT = "Avenir Next"
SLIDE_W = 13.333
SLIDE_H = 7.5
MARGIN = 0.6
CONTENT_RIGHT = SLIDE_W - MARGIN
CONTENT_W = CONTENT_RIGHT - MARGIN


def C(hexstr: str) -> RGBColor:
    return RGBColor.from_string(hexstr)


def strip_md(text: str) -> str:
    return text.replace("**", "").replace("`", "")


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def blank_slide(prs: Presentation):
    layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(layout)
    for shape in list(slide.shapes):
        shape._element.getparent().remove(shape._element)
    return slide


def set_background(slide, hexcolor: str):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = C(hexcolor)


def add_rect(slide, x, y, w, h, fill_hex=None, line_hex=None, line_w=0.75,
             shape_type=MSO_SHAPE.RECTANGLE, shadow=False):
    shp = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill_hex is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = C(fill_hex)
    if line_hex is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = C(line_hex)
        shp.line.width = Pt(line_w)
    shp.shadow.inherit = False
    return shp


def add_text(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             line_spacing=1.0, space_after=0, wrap=True):
    """runs: list of paragraphs; each paragraph is a list of (text, size, color, bold, italic)."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        for (text, size, color, bold, italic) in para:
            r = p.add_run()
            r.text = text
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.color.rgb = C(color)
            r.font.bold = bold
            r.font.italic = italic
    return box


def add_kicker_title_lede(slide, kicker, title, lede, title_size=28):
    add_text(
        slide, MARGIN, 0.42, CONTENT_W, 0.32,
        [[(kicker, 11, THEME["accentPrimary"], True, False)]],
    )
    add_text(
        slide, MARGIN, 0.74, CONTENT_W, 0.9,
        [[(title, title_size, THEME["textPrimary"], True, False)]],
        line_spacing=1.05,
    )
    add_text(
        slide, MARGIN, 1.62, CONTENT_W, 0.85,
        [[(lede, 16, THEME["textPrimary"], False, False)]],
        line_spacing=1.15,
    )


def add_footer(slide, index, total=16, note=None):
    add_text(
        slide, MARGIN, SLIDE_H - 0.42, 6.5, 0.3,
        [[(note or "", 9.5, THEME["textSecondary"], False, False)]],
    )
    add_text(
        slide, CONTENT_RIGHT - 1.6, SLIDE_H - 0.42, 1.6, 0.3,
        [[(f"{index} / {total}", 9.5, THEME["textSecondary"], False, False)]],
        align=PP_ALIGN.RIGHT,
    )


def add_bullets(slide, x, y, w, h, bullets, size=15, gap=0.14, marker="■"):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, (text, bold_first) in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.12
        p.space_after = Pt(gap * 72)
        marker_run = p.add_run()
        marker_run.text = f"{marker}  "
        marker_run.font.name = FONT
        marker_run.font.size = Pt(size - 3)
        marker_run.font.color.rgb = C(THEME["accentPrimary"])
        marker_run.font.bold = True
        text_run = p.add_run()
        text_run.text = text
        text_run.font.name = FONT
        text_run.font.size = Pt(size)
        text_run.font.color.rgb = C(THEME["textPrimary"])
        text_run.font.bold = bold_first
    return box


def content_slide(prs, index, kicker, title, lede, bullets, note=None, title_size=28,
                   bullet_size=15, bullets_y=2.62):
    slide = blank_slide(prs)
    set_background(slide, THEME["canvas"])
    add_kicker_title_lede(slide, kicker, title, strip_md(lede), title_size=title_size)
    add_bullets(
        slide, MARGIN, bullets_y, CONTENT_W, SLIDE_H - bullets_y - 0.55,
        [(strip_md(b), bold) for (b, bold) in bullets],
        size=bullet_size,
    )
    add_footer(slide, index, note=note)
    return slide


KICKER = "EXTENDER-DB BRIEFING · 2026-07-20"

prs = Presentation()
prs.slide_width = Emu(int(SLIDE_W * 914400))
prs.slide_height = Emu(int(SLIDE_H * 914400))

# ---------------------------------------------------------------------------
# Slide 1 — Title
# ---------------------------------------------------------------------------
s1 = blank_slide(prs)
set_background(s1, THEME["canvas"])
add_text(
    s1, MARGIN, 1.1, CONTENT_W, 0.35,
    [[("EXTENDER-DB BRIEFING", 13, THEME["accentPrimary"], True, False)]],
)
add_text(
    s1, MARGIN, 1.55, CONTENT_W, 1.9,
    [[("Extender-DB: the catalog and its standards, both as data", 34, THEME["textPrimary"], True, False)]],
    line_spacing=1.08,
)
card = add_rect(s1, MARGIN, 3.85, CONTENT_W, 2.35, fill_hex=THEME["surface"])
tf = card.text_frame
tf.word_wrap = True
tf.margin_left = Inches(0.4)
tf.margin_right = Inches(0.4)
tf.margin_top = Inches(0.35)
tf.margin_bottom = Inches(0.3)
tf.vertical_anchor = MSO_ANCHOR.MIDDLE
lines = [
    ("A walkthrough of what was built on feat/extender-db in dotfiles-agents", 16, THEME["textPrimary"], False),
    ("Every number in this deck was queried live from the database it describes", 16, THEME["textPrimary"], False),
    ("2026-07-20 · _meta/extender-db · briefing for Henry", 13, THEME["textSecondary"], False),
]
for i, (text, size, color, bold) in enumerate(lines):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(14)
    p.line_spacing = 1.15
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.color.rgb = C(color)
    r.font.bold = bold
add_footer(s1, 1)

# ---------------------------------------------------------------------------
# Slide 2 — The problem
# ---------------------------------------------------------------------------
content_slide(
    prs, 2, KICKER, "The problem",
    "Curating a growing catalog of skills, agents, and hooks by re-reading files doesn't scale.",
    [
        ("The repo has strong distribution machinery (roster, drift guards, marketplace generator) but had no analysis substrate", False),
        ("Questions we couldn't ask cheaply: which skills lack worked examples? what frontmatter keys does no spec define? how conformant are we to Anthropic's authoring guidance?", False),
        ("Three jobs need one substrate: organize, monitor, improve", False),
    ],
)

# ---------------------------------------------------------------------------
# Slide 3 — The key idea
# ---------------------------------------------------------------------------
content_slide(
    prs, 3, KICKER, "The key idea",
    "The standards themselves are data — with provenance, status, and supersession.",
    [
        ("If Anthropic promotes N skill archetypes, that's a cited record to evaluate against, not folklore", False),
        ("Internal taxonomies live beside published specs, marked internal + candidate", False),
        ("Competing mental models get compared against the same corpus; superseded, never overwritten", False),
    ],
)

# ---------------------------------------------------------------------------
# Slide 4 — What got built, in one picture
# ---------------------------------------------------------------------------
content_slide(
    prs, 4, KICKER, "What got built, in one picture",
    "A PocketBase database, an idempotent ingest pipeline, and an assessment loop — with the repo staying the source of truth.",
    [
        ("37 extenders · 192 files (content + sha256) · 6 frameworks · 662 assessment verdicts", True),
        ("The DB is a rebuildable projection: findings become fixes in primitives-core/, then re-ingest", False),
        ("Runs locally: serve.sh (env-configured), admin UI at 127.0.0.1:8090/_/", False),
    ],
)

# ---------------------------------------------------------------------------
# Slide 5 — Data model: two halves joined by assessments (diagram)
# ---------------------------------------------------------------------------
s5 = blank_slide(prs)
set_background(s5, THEME["canvas"])
add_kicker_title_lede(
    s5, KICKER, "Data model: two halves joined by assessments",
    "Seven collections — the inventory records what each extender IS; the doctrine records what we judge it BY.",
)

DIAG_TOP = 2.75
DIAG_BOTTOM = 6.75
LEFT_X, LEFT_W = MARGIN, 4.3
MID_X, MID_W = 5.6, 2.2
RIGHT_X, RIGHT_W = 8.5, CONTENT_RIGHT - 8.5
GAP1_X, GAP1_W = LEFT_X + LEFT_W, MID_X - (LEFT_X + LEFT_W)
GAP2_X, GAP2_W = MID_X + MID_W, RIGHT_X - (MID_X + MID_W)

# Lane headers
add_rect(s5, LEFT_X, DIAG_TOP, LEFT_W, 0.42, fill_hex=THEME["accentPrimary"])
add_text(s5, LEFT_X, DIAG_TOP, LEFT_W, 0.42,
         [[("INVENTORY — records what each extender IS", 12.5, THEME["textInverse"], True, False)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

add_rect(s5, RIGHT_X, DIAG_TOP, RIGHT_W, 0.42, fill_hex=THEME["accentTertiary"])
add_text(s5, RIGHT_X, DIAG_TOP, RIGHT_W, 0.42,
         [[("DOCTRINE — records what we judge it BY", 12.5, THEME["textInverse"], True, False)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# Left lane boxes
left_items = ["extenders", "files", "distributions", "frontmatter_dimensions"]
box_top = DIAG_TOP + 0.62
box_h = 0.72
gap = 0.14
for i, name in enumerate(left_items):
    y = box_top + i * (box_h + gap)
    add_rect(s5, LEFT_X, y, LEFT_W, box_h, fill_hex=THEME["surface"], line_hex=THEME["border"])
    add_text(s5, LEFT_X + 0.2, y, LEFT_W - 0.4, box_h,
             [[(name, 15, THEME["textPrimary"], True, False)]],
             anchor=MSO_ANCHOR.MIDDLE)

# Right lane boxes (frameworks, framework_elements)
fw_h = 0.72
fe_h = 1.02
add_rect(s5, RIGHT_X, box_top, RIGHT_W, fw_h, fill_hex=THEME["surface"], line_hex=THEME["border"])
add_text(s5, RIGHT_X + 0.2, box_top, RIGHT_W - 0.4, fw_h,
         [[("frameworks", 15, THEME["textPrimary"], True, False)]],
         anchor=MSO_ANCHOR.MIDDLE)
fe_y = box_top + fw_h + gap
add_rect(s5, RIGHT_X, fe_y, RIGHT_W, fe_h, fill_hex=THEME["surface"], line_hex=THEME["border"])
add_text(
    s5, RIGHT_X + 0.2, fe_y, RIGHT_W - 0.4, fe_h,
    [
        [("framework_elements", 15, THEME["textPrimary"], True, False)],
        [("each element carries explicit judgment criteria", 11.5, THEME["textSecondary"], False, True)],
    ],
    anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.15,
)

# Middle assessments box, vertically centered on the lane block span
lane_span_top = box_top
lane_span_bottom = box_top + 4 * box_h + 3 * gap  # bottom of left lane's 4th box
mid_h = 1.7
mid_y = (lane_span_top + lane_span_bottom) / 2 - mid_h / 2
add_rect(s5, MID_X, mid_y, MID_W, mid_h, fill_hex=THEME["surfaceInverse"])
add_text(
    s5, MID_X + 0.15, mid_y, MID_W - 0.3, mid_h,
    [
        [("assessments", 16, THEME["textInverse"], True, False)],
        [("extender × framework-element × assessor →", 10.5, THEME["textInverse"], False, False)],
        [("present / partial / absent", 10.5, THEME["textInverse"], True, False)],
    ],
    align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.15,
)

# Arrows into the join
arrow_h = 0.4
arrow_y = mid_y + mid_h / 2 - arrow_h / 2
add_rect(s5, GAP1_X + 0.06, arrow_y, GAP1_W - 0.12, arrow_h,
         fill_hex=THEME["accentPrimary"], shape_type=MSO_SHAPE.RIGHT_ARROW)
add_rect(s5, GAP2_X + 0.06, arrow_y, GAP2_W - 0.12, arrow_h,
         fill_hex=THEME["accentTertiary"], shape_type=MSO_SHAPE.RIGHT_ARROW)

add_footer(s5, 5)

# ---------------------------------------------------------------------------
# Slide 6 — Inventory side, by example
# ---------------------------------------------------------------------------
content_slide(
    prs, 6, KICKER, "Inventory side, by example",
    "One row per extender carries everything analysis needs: provenance, parsed frontmatter, the full body, and size metrics.",
    [
        ("Example record (handoff skill): kind=skill, origin=authored, frontmatter JSON, 1,000-word body, file inventory", False),
        ("files: every file with role (entrypoint/reference/script/asset), full content, sha256", False),
        ("distributions: code-desk, exec-desk, foreman-kit, diagrams, obsidian-toolkit + 5 standalone wrappers, with membership relations", False),
    ],
)

# ---------------------------------------------------------------------------
# Slide 7 — Doctrine side: the six frameworks (table)
# ---------------------------------------------------------------------------
s7 = blank_slide(prs)
set_background(s7, THEME["canvas"])
add_kicker_title_lede(
    s7, KICKER, "Doctrine side: the six frameworks",
    "Six frameworks are seeded — two cited to Anthropic docs, two derived from this repo's own enforced rules, two internal candidates.",
)

fw_rows = [
    ("anthropic-agent-skills", "Anthropic docs", "active"),
    ("claude-code-subagents", "Anthropic docs", "active"),
    ("hook-dir-layout", "repo lint", "active"),
    ("dotfiles-agents-roster-schema", "repo", "active"),
    ("hsb3-skill-archetypes", "internal", "candidate"),
    ("skill-section-taxonomy", "internal", "candidate"),
]
table_top = 2.75
table_h = 3.7
tbl_x, tbl_w = MARGIN, CONTENT_W
gframe = s7.shapes.add_table(len(fw_rows) + 1, 3, Inches(tbl_x), Inches(table_top),
                              Inches(tbl_w), Inches(table_h))
table = gframe.table
table.columns[0].width = Inches(6.4)
table.columns[1].width = Inches(3.3)
table.columns[2].width = Inches(2.43)

headers = ["Framework", "Source", "Status"]
for c, h in enumerate(headers):
    cell = table.cell(0, c)
    cell.fill.solid()
    cell.fill.fore_color.rgb = C(THEME["surfaceInverse"])
    cell.margin_left = Inches(0.15)
    cell.margin_top = Inches(0.06)
    cell.margin_bottom = Inches(0.06)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = cell.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = h
    r.font.name = FONT
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = C(THEME["textInverse"])

for r_i, (name, source, status) in enumerate(fw_rows, start=1):
    row_fill = THEME["surface"] if r_i % 2 == 1 else THEME["surfaceElevated"]
    status_color = THEME["positive"] if status == "active" else THEME["caution"]
    for c_i, text in enumerate((name, source, status)):
        cell = table.cell(r_i, c_i)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C(row_fill)
        cell.margin_left = Inches(0.15)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        r = p.add_run()
        r.text = text
        r.font.name = FONT
        r.font.size = Pt(13.5)
        r.font.color.rgb = C(THEME["textPrimary"] if c_i != 2 else status_color)
        r.font.bold = c_i == 2

# strip default table style banding by setting a plain style if available
tbl_el = gframe.table._tbl
tbl_pr = tbl_el.find(qn('a:tblPr'))
if tbl_pr is not None:
    tbl_pr.set('firstRow', '0')
    tbl_pr.set('bandRow', '0')

add_footer(s7, 7)

# ---------------------------------------------------------------------------
# Slide 8 — Assessor discipline
# ---------------------------------------------------------------------------
content_slide(
    prs, 8, KICKER, "Assessor discipline",
    "The assessor field keeps machine facts, judgment, and the adversarial trail from contaminating each other.",
    [
        ("mechanical-v1 (197 rows): regenerated by ingest every run", False),
        ("judged-v1 (345 rows): judge agents + session adjudication; ingest never touches them", False),
        ("review-v1 (120 rows): the blind reviewers' verdicts, preserved as the verification record", False),
        ("Proven: full re-ingest after loading → zero new records, all 465 judgment rows untouched", False),
    ],
)

# ---------------------------------------------------------------------------
# Slide 9 — How judgment was produced
# ---------------------------------------------------------------------------
content_slide(
    prs, 9, KICKER, "How judgment was produced",
    "Six judge agents assessed all 23 skills and returned structured JSON with evidence quotes — they never held database credentials.",
    [
        ("Batches of ~4 skills per judge; verdicts validated against the DB's element catalog before loading", False),
        ("Two reviewers blind-re-derived a stratified 8-skill sample (never saw the judges' answers)", False),
        ("One builder extended the ingest to hooks + externals, proving its work on a throwaway PocketBase instance", False),
    ],
)

# ---------------------------------------------------------------------------
# Slide 10 — Adversarial review earned its keep
# ---------------------------------------------------------------------------
content_slide(
    prs, 10, KICKER, "Adversarial review earned its keep",
    "Agreement was high where it should be, and every real disagreement was adjudicated by the session from the sources.",
    [
        ("Primaries: 6/8 exact; sections: 56/72 exact, and 15 of the 16 disagreements were adjacent partial-boundary calls (one hard flip)", False),
        ("Three adjudications: handoff → workflow-procedure; private-fork → domain-expertise; private-fork integration-partners → absent", False),
        ("The catch that mattered: the builder patched a schema gap (kind: plugin) only on its throwaway instance — the session gate caught it and fixed schema.py durably (EDB-11)", False),
    ],
    bullet_size=14.5,
)

# ---------------------------------------------------------------------------
# Slide 11 — Finding: the catalog's shape (horizontal bar chart, native shapes)
# ---------------------------------------------------------------------------
s11 = blank_slide(prs)
set_background(s11, THEME["canvas"])
add_kicker_title_lede(
    s11, KICKER, "Finding: the catalog's shape",
    "Nearly half the catalog is domain-expertise packs; no skill has guardrail-override as its primary identity.",
)

archetypes = [
    ("domain-expertise", 11),
    ("workflow-procedure", 4),
    ("deliverable-producer", 4),
    ("scaffold-auditor", 3),
    ("orchestration-delegation", 1),
    ("guardrail-override", 0),
]
CHART_TOP = 2.85
CHART_BOTTOM = 6.75
LABEL_X, LABEL_W = MARGIN, 3.0
BAR_X = LABEL_X + LABEL_W + 0.25
BAR_MAX_W = CONTENT_RIGHT - BAR_X - 0.6
row_h = (CHART_BOTTOM - CHART_TOP) / len(archetypes)
bar_h = row_h * 0.55
max_val = max(v for _, v in archetypes)

for i, (label, val) in enumerate(archetypes):
    y = CHART_TOP + i * row_h + (row_h - bar_h) / 2
    add_text(s11, LABEL_X, y, LABEL_W, bar_h,
             [[(label, 13.5, THEME["textPrimary"], True, False)]],
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    if val == 0:
        stub_w = 0.12
        add_rect(s11, BAR_X, y, stub_w, bar_h, fill_hex=THEME["dataNeutral"])
        add_text(s11, BAR_X + stub_w + 0.12, y, 0.6, bar_h,
                 [[("0", 13, THEME["textSecondary"], True, False)]],
                 anchor=MSO_ANCHOR.MIDDLE)
    else:
        bar_w = max(BAR_MAX_W * val / max_val, 0.3)
        add_rect(s11, BAR_X, y, bar_w, bar_h, fill_hex=THEME["dataPrimary"])
        add_text(s11, BAR_X + bar_w + 0.12, y, 0.6, bar_h,
                 [[(str(val), 13.5, THEME["textPrimary"], True, False)]],
                 anchor=MSO_ANCHOR.MIDDLE)

add_footer(s11, 11, note="Source: deck-data.json, queried live from the DB · count of skills by primary archetype")

# ---------------------------------------------------------------------------
# Slide 12 — Finding: section coverage (stacked horizontal bars)
# ---------------------------------------------------------------------------
s12 = blank_slide(prs)
set_background(s12, THEME["canvas"])
add_kicker_title_lede(
    s12, KICKER, "Finding: section coverage",
    "Two section types are systematically thin — a third of skills have no in-body trigger guidance, and prerequisites is the only section where absent+partial outnumber present.",
    title_size=26,
)

sections = [
    ("purpose-overview", 23, 0, 0),
    ("reference-pointers", 20, 1, 2),
    ("output-format", 19, 3, 1),
    ("integration-partners", 19, 2, 2),
    ("anti-patterns", 15, 6, 2),
    ("workflow-steps", 13, 7, 3),
    ("examples", 13, 3, 7),
    ("trigger-when-to-use", 10, 5, 8),
    ("prerequisites", 8, 7, 8),
]
TOTAL = 23
S_LABEL_X, S_LABEL_W = MARGIN, 2.5
S_BAR_X = S_LABEL_X + S_LABEL_W + 0.2
S_BAR_MAX_W = CONTENT_RIGHT - S_BAR_X

# legend
legend_y = 2.62
legend_items = [("present", THEME["positive"]), ("partial", THEME["caution"]), ("absent", THEME["negative"])]
lx = S_BAR_X
for name, color in legend_items:
    add_rect(s12, lx, legend_y, 0.22, 0.22, fill_hex=color)
    add_text(s12, lx + 0.3, legend_y - 0.03, 1.3, 0.28,
             [[(name, 11.5, THEME["textPrimary"], False, False)]], anchor=MSO_ANCHOR.MIDDLE)
    lx += 1.55

CHART12_TOP = 3.05
CHART12_BOTTOM = 6.75
row_h12 = (CHART12_BOTTOM - CHART12_TOP) / len(sections)
bar_h12 = row_h12 * 0.6

for i, (label, present, partial, absent) in enumerate(sections):
    y = CHART12_TOP + i * row_h12 + (row_h12 - bar_h12) / 2
    add_text(s12, S_LABEL_X, y, S_LABEL_W, bar_h12,
             [[(label, 12.5, THEME["textPrimary"], True, False)]],
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    cursor_x = S_BAR_X
    for value, color, is_dark in (
        (present, THEME["positive"], True),
        (partial, THEME["caution"], False),
        (absent, THEME["negative"], True),
    ):
        if value == 0:
            continue
        seg_w = S_BAR_MAX_W * value / TOTAL
        add_rect(s12, cursor_x, y, seg_w, bar_h12, fill_hex=color)
        label_color = THEME["textInverse"] if is_dark else THEME["textPrimary"]
        add_text(s12, cursor_x, y, seg_w, bar_h12,
                 [[(str(value), 11, label_color, True, False)]],
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        cursor_x += seg_w

add_footer(s12, 12, note="Source: deck-data.json, queried live from the DB · counts of 23 skills, present/partial/absent per section")

# ---------------------------------------------------------------------------
# Slide 13 — Findings: confirmed bugs and open questions
# ---------------------------------------------------------------------------
content_slide(
    prs, 13, KICKER, "Findings: confirmed bugs and open questions",
    "The database is already paying rent — one confirmed catalog bug, two conformance violations, three unspecified frontmatter keys.",
    [
        ("EDB-9 (confirmed twice, independently): obsidian-cli cites five reference files that don't exist on disk", False),
        ("EDB-3: diagrams (653 lines) and obsidian-cli (753 lines) exceed the ≤500-line SKILL.md guideline", False),
        ("EDB-4: skill metadata (×2), skill version (×2), agent memory (×1) — no spec defines them", False),
    ],
)

# ---------------------------------------------------------------------------
# Slide 14 — Full-surface census
# ---------------------------------------------------------------------------
content_slide(
    prs, 14, KICKER, "Full-surface census",
    "The whole curated surface is now inventoried, and the origin partition matches the repo's own CI output exactly.",
    [
        ("25 skills (23 authored + 2 external) · 4 agent personas · 4 hooks · 4 external plugins", False),
        ("Hooks: 16/16 layout checks pass — fully conformant with the ratified hook-dir layout", False),
        ("Origin: 31 authored · 6 external (pinned upstream + SHA)", False),
    ],
)

# ---------------------------------------------------------------------------
# Slide 15 — Promotion gate scorecard
# ---------------------------------------------------------------------------
content_slide(
    prs, 15, KICKER, "Promotion gate scorecard",
    'The charter defines "satisfied" as four checkboxes; two are ticked.',
    [
        ("✅ Judged pass for every skill, adversarially spot-verified", False),
        ("✅ One expansion kind (hooks) end-to-end with its own framework", False),
        ("⬜ ≥3 findings that changed something in the repo (EDB-9 is ready to action)", False),
        ("⬜ Update-path proof after a real catalog change (falls out of the next one)", False),
    ],
)

# ---------------------------------------------------------------------------
# Slide 16 — Decisions in your court (numbered)
# ---------------------------------------------------------------------------
s16 = blank_slide(prs)
set_background(s16, THEME["canvas"])
add_kicker_title_lede(
    s16, KICKER, "Decisions in your court",
    "Four decisions are queued for the owner, in rough order of leverage.",
)

decisions = [
    "Action EDB-9 (obsidian-cli phantom references) — doubles as the update-path proof",
    "Fold reviewer calibration notes into judging-criteria v2 before any second pass (EDB-10)",
    "Build W4: report.py + PocketBase view collections as the standing analysis surface",
    "When the gate is full: promote — stay in _meta/, graduate to scripts/ + make lane, or own repo",
]
d_top = 2.68
d_h = 0.92
d_gap = 0.14
for i, text in enumerate(decisions):
    y = d_top + i * (d_h + d_gap)
    add_rect(s16, MARGIN, y, CONTENT_W, d_h, fill_hex=THEME["surface"])
    num_w = 0.75
    add_rect(s16, MARGIN, y, num_w, d_h, fill_hex=THEME["accentPrimary"])
    add_text(s16, MARGIN, y, num_w, d_h,
             [[(str(i + 1), 22, THEME["textInverse"], True, False)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s16, MARGIN + num_w + 0.25, y, CONTENT_W - num_w - 0.5, d_h,
             [[(text, 14.5, THEME["textPrimary"], False, False)]],
             anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.1)

add_footer(s16, 16)

OUT_PATH = "/Users/henry/Developer/_hsb3/dotfiles-agents/_meta/briefings/2026-07-20-extender-db/extender-db-briefing.pptx"
prs.save(OUT_PATH)
print(f"Wrote {OUT_PATH} with {len(prs.slides)} slides")
