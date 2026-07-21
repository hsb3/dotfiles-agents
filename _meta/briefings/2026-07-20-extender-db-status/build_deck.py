"""Build the Extender-DB STATUS briefing deck with python-pptx.

Reuses the machinery of the sibling 2026-07-20 extender-db deck: the carbon-white
THEME dict, FONT = Avenir Next, the slide scaffold / text / rect / bullet / table
helpers, and the lede-first explanatory register. Every slide carries a native-shape
visual that does explanatory work (no raster images, no external assets, palette
colors only, prose >= 14pt).

Slides 1-6 are held at a strict 1:1 with deck-content.md because the content carries
an internal cross-reference (the decisions slide's item A -> "slide 6", the
in-estate-answers table); the in-estate table therefore must stay the 6th slide.
Splits are only taken at position 7+ where they are safe -- the hand-off graph
(content slide 10) is split into two by domain, as the brief sanctions.

Content is sourced verbatim from deck-content.md; markdown syntax ("**", backticks,
"~~", leading "- ") is stripped as formatting, not content. The slide-5 grid and the
slide-10/11 graphs use the authoritative taxonomy + relationship rows from
_meta/extender-db/coverage-matrix.md (headline counts match the content doc exactly:
19 covered / 3 partial / 2 gap; 46 relationships = 24 complementary + 1 duplicative +
21 directed). The diagrams illustrate the same facts; they invent no new claims.

Run:
    uv run --with python-pptx python3 build_deck.py
"""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

# ---------------------------------------------------------------------------
# Theme: carbon-white (IBM Carbon) -- continuity with the sibling extender-db deck.
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
KICKER = "EXTENDER-DB · STATUS BRIEFING · 2026-07-20"

DECK: list = []  # (slide, note) in creation order -> footers added at the end


def C(hexstr: str) -> RGBColor:
    return RGBColor.from_string(hexstr)


def strip_md(text: str) -> str:
    return text.replace("**", "").replace("`", "").replace("~~", "")


# ---------------------------------------------------------------------------
# Low-level helpers (reused from the sibling deck)
# ---------------------------------------------------------------------------

def blank_slide(prs: Presentation, note=None):
    layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(layout)
    for shape in list(slide.shapes):
        shape._element.getparent().remove(shape._element)
    set_background(slide, THEME["canvas"])
    DECK.append((slide, note))
    return slide


def set_background(slide, hexcolor: str):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = C(hexcolor)


def add_rect(slide, x, y, w, h, fill_hex=None, line_hex=None, line_w=0.75,
             shape_type=MSO_SHAPE.RECTANGLE):
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


def connect(slide, x1, y1, x2, y2, color, width=1.6, dash=None,
            arrow_tail=True, arrow_head=False):
    cxn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                     Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    cxn.line.color.rgb = C(color)
    cxn.line.width = Pt(width)
    ln = cxn.line._get_or_add_ln()
    if dash:
        ln.append(ln.makeelement(qn('a:prstDash'), {'val': dash}))
    if arrow_head:
        ln.append(ln.makeelement(qn('a:headEnd'), {'type': 'triangle', 'w': 'med', 'len': 'med'}))
    if arrow_tail:
        ln.append(ln.makeelement(qn('a:tailEnd'), {'type': 'triangle', 'w': 'med', 'len': 'med'}))
    cxn.shadow.inherit = False
    return cxn


def node(slide, x, y, w, h, label, fill=None, line=None, text=None, size=9.5,
         bold=True, line_w=1.25):
    fill = fill or THEME["surface"]
    line = line or THEME["borderStrong"]
    text = text or THEME["textPrimary"]
    add_rect(slide, x, y, w, h, fill_hex=fill, line_hex=line, line_w=line_w,
             shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    add_text(slide, x + 0.04, y, w - 0.08, h, [[(label, size, text, bold, False)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=0.98)
    return (x, y, w, h)


def edge(slide, a, b, color, dash=None, width=1.6):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    acx, acy, bcx, bcy = ax + aw / 2, ay + ah / 2, bx + bw / 2, by + bh / 2
    dx, dy = bcx - acx, bcy - acy
    if abs(dx) >= abs(dy):
        p1 = (ax + aw, acy) if dx >= 0 else (ax, acy)
        p2 = (bx, bcy) if dx >= 0 else (bx + bw, bcy)
    else:
        p1 = (acx, ay + ah) if dy >= 0 else (acx, ay)
        p2 = (bcx, by) if dy >= 0 else (bcx, by + bh)
    connect(slide, p1[0], p1[1], p2[0], p2[1], color, width=width, dash=dash)


def add_kicker_title_lede(slide, kicker, title, lede, title_size=28, lede_size=16,
                          lede_h=0.85, lede_y=1.62):
    add_text(slide, MARGIN, 0.42, CONTENT_W, 0.32,
             [[(kicker, 11, THEME["accentPrimary"], True, False)]])
    add_text(slide, MARGIN, 0.74, CONTENT_W, 0.9,
             [[(title, title_size, THEME["textPrimary"], True, False)]], line_spacing=1.05)
    add_text(slide, MARGIN, lede_y, CONTENT_W, lede_h,
             [[(strip_md(lede), lede_size, THEME["textPrimary"], False, False)]],
             line_spacing=1.15)


def add_bullets(slide, x, y, w, h, bullets, size=15, gap=0.16, marker="■"):
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
        mk = p.add_run()
        mk.text = f"{marker}  "
        mk.font.name = FONT
        mk.font.size = Pt(size - 3)
        mk.font.color.rgb = C(THEME["accentPrimary"])
        mk.font.bold = True
        tr = p.add_run()
        tr.text = strip_md(text)
        tr.font.name = FONT
        tr.font.size = Pt(size)
        tr.font.color.rgb = C(THEME["textPrimary"])
        tr.font.bold = bold_first
    return box


def chip(slide, x, y, w, h, text, fill_hex, text_hex, size=10, bold=True,
         line_hex=None, align=PP_ALIGN.CENTER):
    add_rect(slide, x, y, w, h, fill_hex=fill_hex, line_hex=line_hex,
             shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    add_text(slide, x + 0.08, y, w - 0.16, h, [[(text, size, text_hex, bold, False)]],
             align=align, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0)


def make_table(slide, top, height, col_widths, headers, rows, cell_styler,
               header_size=14, body_size=13.5):
    ncols = len(headers)
    gframe = slide.shapes.add_table(len(rows) + 1, ncols, Inches(MARGIN), Inches(top),
                                    Inches(sum(col_widths)), Inches(height))
    table = gframe.table
    for c, w in enumerate(col_widths):
        table.columns[c].width = Inches(w)
    for c, h in enumerate(headers):
        cell = table.cell(0, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C(THEME["surfaceInverse"])
        cell.margin_left = Inches(0.15)
        cell.margin_right = Inches(0.15)
        cell.margin_top = Inches(0.05)
        cell.margin_bottom = Inches(0.05)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        r = p.add_run()
        r.text = h
        r.font.name = FONT
        r.font.size = Pt(header_size)
        r.font.bold = True
        r.font.color.rgb = C(THEME["textInverse"])
    for r_i, row in enumerate(rows, start=1):
        row_fill = THEME["surface"] if r_i % 2 == 1 else THEME["surfaceElevated"]
        for c_i, text in enumerate(row):
            cell = table.cell(r_i, c_i)
            cell.fill.solid()
            cell.fill.fore_color.rgb = C(row_fill)
            cell.margin_left = Inches(0.15)
            cell.margin_right = Inches(0.15)
            cell.margin_top = Inches(0.05)
            cell.margin_bottom = Inches(0.05)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            color, bold = cell_styler(r_i, c_i, text)
            p = cell.text_frame.paragraphs[0]
            p.line_spacing = 1.05
            r = p.add_run()
            r.text = text
            r.font.name = FONT
            r.font.size = Pt(body_size)
            r.font.color.rgb = C(color)
            r.font.bold = bold
    tbl_pr = gframe.table._tbl.find(qn('a:tblPr'))
    if tbl_pr is not None:
        tbl_pr.set('firstRow', '0')
        tbl_pr.set('bandRow', '0')
    return table


def legend(slide, x, y, items, size=10):
    """items: list of (label, color, dash|None|'solid'|'fill'). Small graph legend."""
    cx = x
    for label, color, kind in items:
        if kind == "fill":
            add_rect(slide, cx, y + 0.03, 0.22, 0.16, fill_hex=color)
        else:
            connect(slide, cx, y + 0.11, cx + 0.42, y + 0.11, color, width=2,
                    dash=("dash" if kind == "dash" else None))
        lx = cx + (0.3 if kind == "fill" else 0.5)
        add_text(slide, lx, y - 0.04, 1.9, 0.3, [[(label, size, THEME["textPrimary"], False, False)]],
                 anchor=MSO_ANCHOR.MIDDLE)
        cx = lx + 0.05 + (len(label) * 0.072 + 0.25)


prs = Presentation()
prs.slide_width = Emu(int(SLIDE_W * 914400))
prs.slide_height = Emu(int(SLIDE_H * 914400))

# ===========================================================================
# Slide 1 -- Title (with an estate-at-a-glance chip row)
# ===========================================================================
s1 = blank_slide(prs)
add_text(s1, MARGIN, 1.05, CONTENT_W, 0.35,
         [[("EXTENDER-DB · STATUS BRIEFING", 13, THEME["accentPrimary"], True, False)]])
add_text(s1, MARGIN, 1.5, CONTENT_W, 1.2,
         [[("Extender-DB — Status Briefing", 38, THEME["textPrimary"], True, False)]],
         line_spacing=1.05)
card = add_rect(s1, MARGIN, 3.25, CONTENT_W, 1.7, fill_hex=THEME["surface"])
add_rect(s1, MARGIN, 3.25, 0.12, 1.7, fill_hex=THEME["accentPrimary"])
tf = card.text_frame
tf.word_wrap = True
tf.margin_left = Inches(0.45)
tf.margin_right = Inches(0.45)
tf.margin_top = Inches(0.3)
tf.margin_bottom = Inches(0.3)
tf.vertical_anchor = MSO_ANCHOR.MIDDLE
for i, (text, size, color) in enumerate([
    ("The coverage milestone is complete: every extender is now mapped to the jobs it serves.",
     20, THEME["textPrimary"]),
    ("dotfiles-agents · branch feat/extender-db · 2026-07-20 · M1 delivered",
     14, THEME["textSecondary"])]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(12 if i == 0 else 0)
    p.line_spacing = 1.2
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.color.rgb = C(color)
# estate-at-a-glance chip row
add_text(s1, MARGIN, 5.25, CONTENT_W, 0.28,
         [[("THE ESTATE, AT A GLANCE", 11, THEME["textSecondary"], True, False)]])
glance = [("37 extenders", THEME["accentPrimary"]), ("9 frameworks", THEME["accentTertiary"]),
          ("1,550 assessments", THEME["surfaceInverse"]), ("24 jobs mapped", THEME["accentSecondary"])]
gw = (CONTENT_W - 3 * 0.2) / 4
for i, (label, color) in enumerate(glance):
    chip(s1, MARGIN + i * (gw + 0.2), 5.6, gw, 0.62, label, color, THEME["textInverse"], size=15)

# ===========================================================================
# Slide 2 -- What this project is (two-halves data-model diagram + bullets)
# ===========================================================================
s2 = blank_slide(prs)
add_kicker_title_lede(
    s2, KICKER, "What this project is",
    "Extender-db is a queryable database of the 37 agent extenders in the marketplace, "
    "joined to the mental models used to judge and compose them.", lede_h=0.8)

# left bullets
add_bullets(
    s2, MARGIN, 2.55, 6.15, 4.3,
    [
        ("Two halves joined by assessments: the inventory (what each skill, agent, hook, and "
         "external IS) and the doctrine (frameworks: archetypes, taxonomies, authoring specs, "
         "the jobs taxonomy, adopted eval methodologies).", False),
        ("The design bet is \"doctrine as data\": mental models live as rows with provenance and "
         "status, so curation questions — covered, duplicated, missing — are queries, not "
         "impressions.", False),
        ("The repo stays the source of truth. The database is a rebuildable projection.", False),
        ("It lives as a _meta/ desk tool on its own branch; promotion to more is an explicit, "
         "gated decision that has not been made.", False),
    ], size=14, gap=0.15)

# right: two-halves diagram
rx = 7.05
rw = CONTENT_RIGHT - rx
half = (rw - 0.2) / 2
inv = (rx, 2.55, half, 1.2)
doc = (rx + half + 0.2, 2.55, half, 1.2)
add_rect(s2, *inv, fill_hex=THEME["accentPrimary"], shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
add_text(s2, inv[0] + 0.08, inv[1] + 0.08, inv[2] - 0.16, inv[3] - 0.16,
         [[("INVENTORY", 12.5, THEME["textInverse"], True, False)],
          [("extenders · files · distributions · sources", 10.5, THEME["accentSoft"], False, False)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.1, space_after=4)
add_rect(s2, *doc, fill_hex=THEME["accentTertiary"], shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
add_text(s2, doc[0] + 0.08, doc[1] + 0.08, doc[2] - 0.16, doc[3] - 0.16,
         [[("DOCTRINE", 12.5, THEME["textInverse"], True, False)],
          [("frameworks · elements", 10.5, "B4F2EF", False, False)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.1, space_after=4)
assess = (rx, 4.35, rw, 0.9)
add_rect(s2, *assess, fill_hex=THEME["surfaceInverse"], shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
add_text(s2, assess[0] + 0.1, assess[1], assess[2] - 0.2, assess[3],
         [[("ASSESSMENTS — the join", 12.5, THEME["textInverse"], True, False)],
          [("extender × element × assessor → present / partial / absent", 10, THEME["textInverse"], False, False)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.1, space_after=3)
connect(s2, inv[0] + half / 2, inv[1] + inv[3], inv[0] + half / 2, assess[1], THEME["borderStrong"], width=2)
connect(s2, doc[0] + half / 2, doc[1] + doc[3], doc[0] + half / 2, assess[1], THEME["borderStrong"], width=2)
# repo -> DB one-way projection
oy = 5.55
repo = (rx, oy, 1.55, 0.62)
db = (rx + rw - 1.55, oy, 1.55, 0.62)
node(s2, *repo, "repo", fill=THEME["surface"], line=THEME["borderStrong"], size=12)
node(s2, *db, "database", fill=THEME["surface"], line=THEME["borderStrong"], size=12)
connect(s2, repo[0] + repo[2], oy + 0.31, db[0], oy + 0.31, THEME["accentPrimary"], width=2.5)
add_text(s2, rx, oy + 0.66, rw, 0.3,
         [[("one-way projection — edits flow repo → DB, never back", 10.5, THEME["textSecondary"], False, True)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# ===========================================================================
# Slide 3 -- Where it stands (milestone strip)
# ===========================================================================
s3 = blank_slide(prs)
add_kicker_title_lede(
    s3, KICKER, "Where it stands",
    "Track I — our own IP — has its foundation complete as of today; Track II — adopted "
    "evaluation — is loaded but not yet exercised.", lede_h=0.75)

add_text(s3, MARGIN, 2.42, CONTENT_W, 0.26,
         [[("DELIVERED", 12, THEME["dataPositive"], True, False),
           ("   W0 through M1 — the shared foundation", 11, THEME["textSecondary"], False, True)]])
done = ["W0 seed", "W1 judged pass", "W2 hooks", "W3 externals", "W7 eval provenance",
        "W9 taxonomy", "M1 coverage body (today)"]
cgap = 0.12
cw = (CONTENT_W - (len(done) - 1) * cgap) / len(done)
for i, label in enumerate(done):
    chip(s3, MARGIN + i * (cw + cgap), 2.72, cw, 0.74, label, THEME["dataPositive"],
         THEME["textInverse"], size=11)

add_text(s3, MARGIN, 3.86, CONTENT_W, 0.26,
         [[("NEXT", 12, THEME["accentPrimary"], True, False),
           ("   Track I — our IP (blue)      Track II — adopted eval, staged (purple)",
            11, THEME["textSecondary"], False, True)]])
nxt = [("M2 analysis surface", THEME["accentPrimary"]), ("M3 combine/coalesce", THEME["accentPrimary"]),
       ("M4 eval doctrine", THEME["accentSecondary"]), ("M5 first comparative eval", THEME["accentSecondary"]),
       ("M6 self-improvement loop (staged)", THEME["accentSecondary"])]
cw2 = (CONTENT_W - (len(nxt) - 1) * cgap) / len(nxt)
for i, (label, color) in enumerate(nxt):
    chip(s3, MARGIN + i * (cw2 + cgap), 4.18, cw2, 0.74, label, color, THEME["textInverse"], size=11)

gy = 5.35
add_rect(s3, MARGIN, gy, CONTENT_W, 1.05, fill_hex=THEME["surface"], line_hex=THEME["border"])
add_rect(s3, MARGIN, gy, 0.12, 1.05, fill_hex=THEME["caution"])
add_text(s3, MARGIN + 0.35, gy + 0.14, CONTENT_W - 0.7, 0.77,
         [[("CHARTER PROMOTION GATE", 12, THEME["textSecondary"], True, False)],
          [("2 of 4 criteria ticked", 17, THEME["textPrimary"], True, False),
           ("  —  judged pass ✓, hooks end-to-end ✓; findings→actions and update-path proof remain.",
            15, THEME["textPrimary"], False, False)]],
         anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.12, space_after=4)

# ===========================================================================
# Slide 4 -- What the database holds now (table + provenance chain glyph)
# ===========================================================================
s4 = blank_slide(prs)
add_kicker_title_lede(
    s4, KICKER, "What the database holds now",
    "One thousand five hundred fifty assessment rows now connect the 37-extender inventory to "
    "nine frameworks, and every verdict resolves to the exact prompt and response that produced it.",
    lede_h=0.9)
rows4 = [
    ("Inventory", "37 extenders (23 authored skills · 4 agents · 4 hooks · 6 externals), full "
                  "file contents, packaging, 10-publisher trust registry"),
    ("Doctrine", "9 frameworks, 72 elements — including the 24-job taxonomy and two adopted eval "
                 "methodologies (SkillOpt, ClosedLoop judges)"),
    ("Assessments", "1,550 rows across mechanical, judged, review, and coverage passes — all "
                    "provenance-linked"),
    ("Coverage (new)", "24 job_coverage rows: 19 covered · 3 partial · 2 gaps"),
    ("Relationships (new)", "46 rows: 24 complementary · 1 duplicative · 21 directed hand-off links"),
]
make_table(s4, 2.78, 2.95, [2.85, CONTENT_W - 2.85], ["Layer", "Contents"], rows4,
           lambda r, c, t: (THEME["textAccent"], True) if c == 0 else (THEME["textPrimary"], False),
           body_size=13)
# provenance chain glyph
add_text(s4, MARGIN, 5.95, CONTENT_W, 0.28,
         [[("EVERY VERDICT RESOLVES TO ITS EXACT PROVENANCE", 11, THEME["textSecondary"], True, False)]])
chain = ["verdict", "eval_run", "exact prompt", "verbatim response"]
ch_w = 2.55
ch_gap = (CONTENT_W - len(chain) * ch_w) / (len(chain) - 1)
cy = 6.28
chain_fill = [THEME["accentPrimary"], THEME["accentSecondary"], THEME["accentTertiary"], THEME["surfaceInverse"]]
for i, label in enumerate(chain):
    x = MARGIN + i * (ch_w + ch_gap)
    chip(s4, x, cy, ch_w, 0.55, label, chain_fill[i], THEME["textInverse"], size=13)
    if i < len(chain) - 1:
        connect(s4, x + ch_w + 0.04, cy + 0.275, x + ch_w + ch_gap - 0.04, cy + 0.275,
                THEME["borderStrong"], width=2)

# ===========================================================================
# Slide 5 -- The coverage matrix headline (24-job status grid)
# ===========================================================================
s5 = blank_slide(prs, note="Source: coverage-matrix.md · framework hsb3-jobs-to-be-done")
add_kicker_title_lede(
    s5, KICKER, "The coverage matrix headline",
    "Of the 24 jobs the estate needs done, 19 are covered by at least one extender whose primary "
    "purpose is that job; three are only partially served; two are open gaps.", lede_h=0.7)

STATUS_FILL = {"covered": THEME["dataPositive"], "partial": THEME["caution"], "gap": THEME["dataNegative"]}
STATUS_TEXT = {"covered": THEME["textInverse"], "partial": THEME["textPrimary"], "gap": THEME["textInverse"]}
families = [
    ("understand-research", [("orient-codebase", "covered"), ("research-question", "gap"),
                             ("consult-domain-expertise", "covered")]),
    ("build-software", [("plan-work", "covered"), ("implement-change", "covered"),
                        ("improve-code", "covered"), ("migrate-at-scale", "partial")]),
    ("assure-quality", [("review-change", "covered"), ("verify-works", "covered")]),
    ("orchestrate-sustain", [("delegate-large-job", "covered"), ("sustain-continuity", "covered"),
                             ("manage-backlog", "covered")]),
    ("produce-deliverables", [("produce-briefing", "covered"), ("produce-deck", "covered"),
                              ("produce-diagram", "covered"), ("produce-dataviz", "gap"),
                              ("produce-readme", "covered")]),
    ("govern-estate", [("enforce-standards", "covered"), ("govern-external-code", "covered"),
                       ("get-owner-signoff", "covered")]),
    ("extend-tooling", [("author-evaluate-extender", "covered"), ("configure-harness", "partial"),
                        ("integrate-knowledge-system", "covered"), ("operate-browser-ui", "partial")]),
]
lx = MARGIN
for name, color in [("covered · 19", THEME["dataPositive"]), ("partial · 3", THEME["caution"]),
                    ("gap · 2", THEME["dataNegative"])]:
    add_rect(s5, lx, 2.44, 0.24, 0.24, fill_hex=color)
    add_text(s5, lx + 0.32, 2.4, 1.7, 0.3, [[(name, 12, THEME["textPrimary"], True, False)]],
             anchor=MSO_ANCHOR.MIDDLE)
    lx += 1.9
gtop = 2.82
head_h = 0.5
jchip_h = 0.5
jgap = 0.09
colgap = 0.1
colw = (CONTENT_W - (len(families) - 1) * colgap) / len(families)
for i, (fam, jobs) in enumerate(families):
    x = MARGIN + i * (colw + colgap)
    add_rect(s5, x, gtop, colw, head_h, fill_hex=THEME["surfaceInverse"])
    add_text(s5, x + 0.04, gtop, colw - 0.08, head_h, [[(fam, 10, THEME["textInverse"], True, False)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=0.95)
    for j, (job, status) in enumerate(jobs):
        y = gtop + head_h + 0.12 + j * (jchip_h + jgap)
        chip(s5, x, y, colw, jchip_h, job, STATUS_FILL[status], STATUS_TEXT[status], size=9.5)
cap_y = 6.34
add_rect(s5, MARGIN, cap_y, CONTENT_W, 0.6, fill_hex=THEME["surface"], line_hex=THEME["border"])
add_text(s5, MARGIN + 0.2, cap_y + 0.05, CONTENT_W - 0.4, 0.5,
         [[("Deepest coverage: ", 12, THEME["textAccent"], True, False),
           ("sustain-continuity (3 present + 1 partial), produce-diagram (4 present), "
            "integrate-knowledge-system (4 present), manage-backlog and enforce-standards "
            "(3 present each).", 12, THEME["textPrimary"], False, False)]],
         anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.1)

# ===========================================================================
# Slide 6 -- Every hole has an in-estate answer (rows + promotion arrows -> ROSTER)
# ===========================================================================
s6 = blank_slide(prs)
add_kicker_title_lede(
    s6, KICKER, "Every hole has an in-estate answer",
    "The punchline of the coverage work: nothing missing needs to be authored from scratch — "
    "every gap and weak spot already has a candidate in the estate.", lede_h=0.8)

rows6 = [
    ("research-question", "gap", "Promote the user-level deep-research skill"),
    ("produce-dataviz", "gap", "Promote the user-level dataviz skill"),
    ("configure-harness", "partial", "Promote the user-level update-config skill"),
    ("migrate-at-scale", "partial", "Fold a migration playbook into foreman-kit (arch C is the mechanism)"),
    ("operate-browser-ui", "partial", "Reference Anthropic's claude-in-chrome at harness level"),
]
reg_top = 2.6
row_h = 0.52
row_gap = 0.1
job_x, job_w = MARGIN, 2.55
st_x, st_w = job_x + job_w + 0.12, 1.05
cand_x = st_x + st_w + 0.12
roster_x = 11.0
cand_w = roster_x - 0.55 - cand_x
# ROSTER box spanning all rows
n6 = len(rows6)
reg_h = n6 * row_h + (n6 - 1) * row_gap
add_rect(s6, roster_x, reg_top, CONTENT_RIGHT - roster_x, reg_h, fill_hex=THEME["surfaceInverse"],
         shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
add_text(s6, roster_x, reg_top, CONTENT_RIGHT - roster_x, reg_h,
         [[("ROSTER", 14, THEME["textInverse"], True, False)],
          [("promote / adopt", 10.5, "C6C6C6", False, False)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.1, space_after=3)
for i, (job, status, cand) in enumerate(rows6):
    y = reg_top + i * (row_h + row_gap)
    add_text(s6, job_x, y, job_w, row_h, [[(job, 12.5, THEME["textPrimary"], True, False)]],
             anchor=MSO_ANCHOR.MIDDLE)
    st_fill = THEME["dataNegative"] if status == "gap" else THEME["caution"]
    st_text = THEME["textInverse"] if status == "gap" else THEME["textPrimary"]
    chip(s6, st_x, y, st_w, row_h, status, st_fill, st_text, size=11)
    chip(s6, cand_x, y, cand_w, row_h, cand, THEME["surface"], THEME["textPrimary"], size=11,
         bold=False, line_hex=THEME["border"], align=PP_ALIGN.LEFT)
    connect(s6, cand_x + cand_w + 0.04, y + row_h / 2, roster_x, y + row_h / 2,
            THEME["accentPrimary"], width=2)
ky = reg_top + reg_h + 0.22
add_rect(s6, MARGIN, ky, CONTENT_W, 0.62, fill_hex=THEME["accentPrimary"])
add_text(s6, MARGIN + 0.3, ky, CONTENT_W - 0.6, 0.62,
         [[("These five calls are yours — issue #153, each with a default so a bare thumbs-up "
            "accepts all.", 14.5, THEME["textInverse"], True, False)]],
         anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.1)

# ===========================================================================
# Slide 7 -- How M1 was verified (the crew) -- vertical pipeline + provenance band
# ===========================================================================
s7 = blank_slide(prs)
add_kicker_title_lede(
    s7, KICKER, "How M1 was verified (the crew)",
    "The mapping was produced by a layered crew, not a single pass: cheap judges fanned out, "
    "blind reviewers re-derived a sample, and the session adjudicated every disagreement.",
    lede_h=0.8)
stages = [
    "7 sonnet judges — batched by kind, JSON only, no database access",
    "merge + validate by script",
    "888 coverage assessments loaded",
    "2 blind opus reviewers (stratified 8-extender sample) + 1 opus duplicative-pair check",
    "session adjudication — 10 rows patched, 4 boundary rules logged",
    "synthesis — relationships + job_coverage",
    "generated coverage matrix",
]
p_top = 2.58
box_h = 0.4
pitch = box_h + 0.1
badge_colors = [THEME["accentPrimary"]] * 3 + [THEME["accentSecondary"]] * 2 + [THEME["accentTertiary"]] * 2
for i, text in enumerate(stages):
    y = p_top + i * pitch
    add_rect(s7, MARGIN, y, CONTENT_W, box_h, fill_hex=THEME["surface"], line_hex=THEME["border"])
    add_rect(s7, MARGIN, y, 0.5, box_h, fill_hex=badge_colors[i])
    add_text(s7, MARGIN, y, 0.5, box_h, [[(str(i + 1), 15, THEME["textInverse"], True, False)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s7, MARGIN + 0.68, y, CONTENT_W - 0.85, box_h,
             [[(text, 12.5, THEME["textPrimary"], False, False)]], anchor=MSO_ANCHOR.MIDDLE)
    if i < len(stages) - 1:
        add_rect(s7, MARGIN + 0.16, y + box_h - 0.02, 0.18, 0.14,
                 fill_hex=THEME["borderStrong"], shape_type=MSO_SHAPE.DOWN_ARROW)
band_y = p_top + len(stages) * pitch + 0.06
add_rect(s7, MARGIN, band_y, CONTENT_W, 0.62, fill_hex=THEME["surfaceElevated"], line_hex=THEME["border"])
add_text(s7, MARGIN + 0.25, band_y + 0.06, CONTENT_W - 0.5, 0.5,
         [[("Full provenance: three eval_runs hold every exact prompt and verbatim response "
            "(W7 invariant).", 12, THEME["textPrimary"], False, False)],
          [("The 662 pre-existing assessment rows survived the live schema change "
            "checksum-identical.", 12, THEME["textPrimary"], False, False)]],
         anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.1, space_after=3)

# ===========================================================================
# Slide 8 -- What verification actually changed (stacked bar + bullets)
# ===========================================================================
s8 = blank_slide(prs)
add_kicker_title_lede(
    s8, KICKER, "What verification actually changed",
    "Blind review is recall, not just error-correction — it added coverage the fan-out missed, "
    "and produced boundary rules that become the next rubric.", lede_h=0.75)
add_text(s8, MARGIN, 2.4, CONTENT_W, 0.26,
         [[("10 DISPUTED VERDICT CELLS ON THE 8-EXTENDER SAMPLE", 11, THEME["textSecondary"], True, False)]])
bar_y = 2.72
bar_h = 0.5
bar_total_w = CONTENT_W
segs = [(7, "7 adjacent-step", THEME["caution"], THEME["textPrimary"]),
        (2, "2 reassigned (EDB-23)", THEME["accentSecondary"], THEME["textInverse"]),
        (1, "1 added by review", THEME["dataPositive"], THEME["textInverse"])]
cx = MARGIN
for val, label, color, tcolor in segs:
    w = bar_total_w * val / 10
    add_rect(s8, cx, bar_y, w, bar_h, fill_hex=color)
    add_text(s8, cx, bar_y, w, bar_h, [[(str(val), 15, tcolor, True, False)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s8, cx, bar_y + bar_h + 0.06, max(w, 1.6), 0.28,
             [[(label, 11.5, THEME["textPrimary"], True, False)]], anchor=MSO_ANCHOR.MIDDLE)
    cx += w
add_bullets(
    s8, MARGIN, 3.85, CONTENT_W, 3.0,
    [
        ("10 verdict cells disputed on the 8-extender sample; 7 were adjacent-step (the recurring "
         "partial boundary, same as W1).", False),
        ("The reviewers found a real capability the judges missed: readme-value-and-proof's "
         "headless-Chromium screenshot capture turned operate-browser-ui from a hard gap into "
         "partial coverage.", False),
        ("Two thin-description externals were reassigned outright — evidence that judging externals "
         "by a one-line description is under-determined (now tracked as EDB-23).", False),
        ("Four boundary rules were logged (for example: consuming the handoff is not sustaining "
         "continuity; nudge-only hooks cap at partial). They feed the M4 rubric directly.", False),
    ], size=14, gap=0.14)

# ===========================================================================
# Slide 9 -- The one confirmed redundancy (three composition tells as mini-diagrams)
# ===========================================================================
s9 = blank_slide(prs)
add_kicker_title_lede(
    s9, KICKER, "The one confirmed redundancy",
    "Only one duplicative pair survived adversarial checking, and the check produced a reusable "
    "test for duplication claims.", lede_h=0.7)

pan_top = 2.55
pan_h = 2.95
pgap = 0.25
pan_w = (CONTENT_W - 2 * pgap) / 3
p1x = MARGIN
p2x = MARGIN + pan_w + pgap
p3x = MARGIN + 2 * (pan_w + pgap)
for px, title in [(p1x, "base + override"), (p2x, "orchestrator + worker"), (p3x, "hub routing")]:
    add_rect(s9, px, pan_top, pan_w, pan_h, fill_hex=THEME["surface"], line_hex=THEME["border"])
    add_text(s9, px + 0.15, pan_top + 0.12, pan_w - 0.3, 0.3,
             [[(title, 13, THEME["textPrimary"], True, False)]], align=PP_ALIGN.CENTER)


def verdict_tag(px, text, color):
    chip(s9, px + 0.3, pan_top + pan_h - 0.5, pan_w - 0.6, 0.36, text, color, THEME["textInverse"], size=11)


# Panel 1: base + override -> REFUTED
b_base = (p1x + 0.55, pan_top + 1.55, pan_w - 1.1, 0.5)
b_over = (p1x + 0.55, pan_top + 0.95, pan_w - 1.1, 0.5)
node(s9, *b_base, "pptx  (base)", fill=THEME["accentSoft"], line=THEME["accentPrimary"], size=11)
node(s9, *b_over, "pptx-themes  (override)", fill=THEME["accentPrimary"], line=THEME["accentPrimary"],
     text=THEME["textInverse"], size=11)
connect(s9, p1x + pan_w - 0.45, pan_top + 1.2, p1x + pan_w - 0.45, pan_top + 1.55,
        THEME["textPrimary"], width=2)
add_text(s9, p1x + 0.2, pan_top + 2.15, pan_w - 0.4, 0.3,
         [[("override layer wins — composition", 10, THEME["textSecondary"], False, True)]],
         align=PP_ALIGN.CENTER)
verdict_tag(p1x, "REFUTED — not a dup", THEME["dataPositive"])

# Panel 2: orchestrator + worker -> REFUTED
o_lead = (p2x + 0.75, pan_top + 0.95, pan_w - 1.5, 0.5)
o_bld = (p2x + 1.4, pan_top + 1.85, pan_w - 1.5, 0.5)
node(s9, *o_lead, "lead  (orchestrator)", fill=THEME["accentSecondary"], line=THEME["accentSecondary"],
     text=THEME["textInverse"], size=11)
node(s9, *o_bld, "builder  (worker)", fill=THEME["surface"], line=THEME["accentSecondary"], size=11)
edge(s9, o_lead, o_bld, THEME["accentSecondary"], width=2)
add_text(s9, p2x + 0.2, pan_top + 2.45, pan_w - 0.4, 0.3,
         [[("spawns a worker — distinct triggers", 10, THEME["textSecondary"], False, True)]],
         align=PP_ALIGN.CENTER)
verdict_tag(p2x, "REFUTED — not a dup", THEME["dataPositive"])

# Panel 3: hub routing -> CONFIRMED duplication
hub = (p3x + (pan_w - 1.5) / 2, pan_top + 0.9, 1.5, 0.48)
authored = (p3x + 0.2, pan_top + 1.75, pan_w / 2 - 0.35, 0.62)
vendored = (p3x + pan_w / 2 + 0.15, pan_top + 1.75, pan_w / 2 - 0.35, 0.62)
node(s9, *hub, "diagrams hub", fill=THEME["surfaceInverse"], line=THEME["surfaceInverse"],
     text=THEME["textInverse"], size=10.5)
node(s9, *authored, "excalidraw (authored)", fill=THEME["surface"], line=THEME["dataPositive"],
     text=THEME["dataPositive"], size=9.5, line_w=1.75)
node(s9, *vendored, "coleam00 twin (unrouted)", fill=THEME["surface"], line=THEME["dataNegative"],
     text=THEME["dataNegative"], size=9.5, line_w=1.5)
connect(s9, hub[0] + 0.3, hub[1] + hub[3], authored[0] + authored[2] / 2, authored[1],
        THEME["dataPositive"], width=2.25)
connect(s9, hub[0] + hub[2] - 0.3, hub[1] + hub[3], vendored[0] + vendored[2] / 2, vendored[1],
        THEME["dataNegative"], width=1.75, dash="dash")
verdict_tag(p3x, "CONFIRMED — drop or fold", THEME["dataNegative"])

# doctrine caption
dc_y = pan_top + pan_h + 0.15
add_rect(s9, MARGIN, dc_y, CONTENT_W, 0.85, fill_hex=THEME["surfaceElevated"], line_hex=THEME["border"])
add_text(s9, MARGIN + 0.25, dc_y, CONTENT_W - 0.5, 0.85,
         [[("The doctrine: ", 14, THEME["textAccent"], True, False),
           ("\"produces the same deliverable\" is a weak duplication signal. The real test is "
            "\"same job the SAME WAY\" — check for base+override, orchestrator+worker, and "
            "hub-routing before believing a duplicative call.", 14, THEME["textPrimary"], False, False)]],
         anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.12)

# ===========================================================================
# Slide 10 -- Relationships: delegation & continuity (directed hand-off graph)
# ===========================================================================
s10 = blank_slide(prs)
add_kicker_title_lede(
    s10, KICKER, "Relationships: delegation & continuity",
    "Beyond coverage, M1 recorded how the extenders hand off to each other — the raw material a "
    "future composition planner will reason over.", lede_h=0.8, lede_y=1.6)
add_text(s10, MARGIN, 2.52, CONTENT_W, 0.3,
         [[("46 relationship rows: 24 complementary · 1 duplicative · 21 directed hand-off links",
            13, THEME["textPrimary"], True, False)]])
legend(s10, 8.7, 2.55, [("precedes", THEME["surfaceInverse"], "solid"),
                        ("feeds-into", THEME["accentPrimary"], "dash")])

nw, nh = 1.95, 0.62
# delegation cluster
scout = node(s10, 0.8, 3.85, nw, nh, "scout")
builder = node(s10, 4.35, 3.85, nw, nh, "builder", fill=THEME["accentSoft"], line=THEME["accentPrimary"])
reviewer = node(s10, 7.9, 3.85, nw, nh, "reviewer")
lead = node(s10, 6.1, 3.0, nw, nh, "lead", fill=THEME["accentSecondary"], line=THEME["accentSecondary"],
            text=THEME["textInverse"])
connect(s10, scout[0] + nw, scout[1] + nh / 2, builder[0], builder[1] + nh / 2,
        THEME["surfaceInverse"], width=2)                          # scout -> builder (precedes)
connect(s10, builder[0] + nw, builder[1] + nh / 2 - 0.12, reviewer[0], reviewer[1] + nh / 2 - 0.12,
        THEME["accentPrimary"], width=1.8, dash="dash")            # builder -> reviewer (feeds-into)
connect(s10, reviewer[0], reviewer[1] + nh / 2 + 0.14, builder[0] + nw, builder[1] + nh / 2 + 0.14,
        THEME["accentPrimary"], width=1.8, dash="dash")            # reviewer -> builder (return)
connect(s10, builder[0] + nw / 2 + 0.2, builder[1], lead[0], lead[1] + nh / 2,
        THEME["accentPrimary"], width=1.8, dash="dash")            # builder -> lead
connect(s10, lead[0] + nw, lead[1] + nh / 2, reviewer[0] + nw / 2, reviewer[1],
        THEME["accentPrimary"], width=1.8, dash="dash")            # lead -> reviewer
add_text(s10, 0.8, 4.65, 9.5, 0.28,
         [[("build loop — scout precedes builder; builder and reviewer feed each other; lead orchestrates",
            10.5, THEME["textSecondary"], False, True)]])
# continuity chain
cw_ = node(s10, 0.8, 5.5, 2.3, nh, "context-watermark")
hfg = node(s10, 4.6, 5.5, 2.6, nh, "handoff-freshness-guard")
shs = node(s10, 8.7, 5.5, 2.6, nh, "session-handoff-surfacer")
connect(s10, cw_[0] + cw_[2], cw_[1] + nh / 2, hfg[0], hfg[1] + nh / 2, THEME["surfaceInverse"], width=2)
connect(s10, hfg[0] + hfg[2], hfg[1] + nh / 2, shs[0], shs[1] + nh / 2, THEME["surfaceInverse"], width=2)
add_text(s10, 0.8, 6.28, 11.0, 0.28,
         [[("continuity chain — each guard precedes the next, passing the baton forward",
            10.5, THEME["textSecondary"], False, True)]])

# ===========================================================================
# Slide 11 -- Relationships: deliverables, governance & knowledge (graph, cont.)
# ===========================================================================
s11 = blank_slide(prs)
add_kicker_title_lede(
    s11, KICKER, "Relationships: deliverables, governance & knowledge",
    "The long-game consumer, deferred as EDB-22, is a grounded planner that reads coverage plus "
    "directional links plus triggers and assembles an ordered toolkit per goal at request time.",
    lede_h=0.75, lede_y=1.55)
legend(s11, 8.7, 2.28, [("precedes", THEME["surfaceInverse"], "solid"),
                        ("feeds-into", THEME["accentPrimary"], "dash")])

# deliverables band
add_text(s11, MARGIN, 2.3, 4.0, 0.26, [[("DELIVERABLES", 10.5, THEME["accentTertiary"], True, False)]])
handoff = node(s11, 0.7, 2.7, 1.7, 0.55, "handoff")
readme = node(s11, 0.7, 3.4, 1.7, 0.55, "readme-value-and-proof", size=8.5)
comms = node(s11, 3.1, 3.05, 1.7, 0.55, "comms", fill=THEME["accentSoft"], line=THEME["accentPrimary"])
pptx = node(s11, 5.5, 3.55, 1.7, 0.55, "pptx")
themes = node(s11, 7.9, 3.05, 1.7, 0.55, "pptx-themes", fill=THEME["accentSoft"], line=THEME["accentPrimary"])
for a in (handoff, readme):
    edge(s11, a, comms, THEME["accentPrimary"], dash="dash", width=1.8)
edge(s11, comms, themes, THEME["accentPrimary"], dash="dash", width=1.8)
edge(s11, pptx, themes, THEME["accentPrimary"], dash="dash", width=1.8)

# governance band
add_text(s11, MARGIN, 4.4, 5.0, 0.26, [[("GOVERNANCE", 10.5, THEME["accentSecondary"], True, False)]])
rms = node(s11, 0.7, 4.75, 2.4, 0.55, "repo-meta-structure", size=9)
rca = node(s11, 3.6, 4.75, 2.5, 0.55, "repo-compliance-audit", size=9)
meps = node(s11, 6.6, 4.75, 2.5, 0.55, "mise-en-place-scaffold", size=9)
edge(s11, rms, rca, THEME["accentPrimary"], dash="dash", width=1.8)
edge(s11, rca, meps, THEME["surfaceInverse"], width=2)

# knowledge band
add_text(s11, MARGIN, 5.55, 5.0, 0.26, [[("KNOWLEDGE SYSTEM", 10.5, THEME["accentTertiary"], True, False)]])
oab = node(s11, 0.7, 5.9, 2.3, 0.55, "obsidian-api-basics", size=9)
omcp = node(s11, 3.7, 5.9, 2.3, 0.55, "obsidian-mcp-server", size=9)
ochat = node(s11, 6.7, 5.9, 2.3, 0.55, "obsidian-chat-ui", size=9)
edge(s11, oab, omcp, THEME["surfaceInverse"], width=2)
edge(s11, omcp, ochat, THEME["accentPrimary"], dash="dash", width=1.8)
connect(s11, oab[0] + oab[2] / 2, oab[1], ochat[0] + ochat[2] / 2 - 0.1, ochat[1],
        THEME["surfaceInverse"], width=2)  # api-basics -> chat-ui precedes (arc over)

# EDB-22 planner panel (right)
pan = (9.6, 4.75, CONTENT_RIGHT - 9.6, 1.7)
add_rect(s11, *pan, fill_hex=THEME["surfaceInverse"], shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
add_text(s11, pan[0] + 0.2, pan[1] + 0.15, pan[2] - 0.4, pan[3] - 0.3,
         [[("EDB-22 — the consumer", 12, THEME["textInverse"], True, False)],
          [("a grounded planner assembles an ordered toolkit per goal from coverage + links + "
            "triggers", 10.5, "E0E0E0", False, False)]],
         anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.12, space_after=5)

# ===========================================================================
# Slide 12 -- Roadmap: two tracks, six milestones (two lanes with nodes)
# ===========================================================================
s12 = blank_slide(prs)
add_kicker_title_lede(
    s12, KICKER, "Roadmap: two tracks, six milestones",
    "The strategy is to build only what is uniquely ours — the taxonomy, coverage, and curation "
    "decisions — and adopt or reuse everything else.", lede_h=0.7)


def milestone(slide, x, y, w, h, mid, label, kind):
    fills = {"done": THEME["dataPositive"], "next": THEME["surface"], "gated": THEME["surface"]}
    lines = {"done": THEME["dataPositive"], "next": THEME["accentPrimary"], "gated": THEME["caution"]}
    texts = {"done": THEME["textInverse"], "next": THEME["accentPrimary"], "gated": "9A7B0A"}
    add_rect(slide, x, y, w, h, fill_hex=fills[kind], line_hex=lines[kind], line_w=2,
             shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    add_text(slide, x + 0.08, y + 0.06, w - 0.16, h - 0.12,
             [[(mid, 15, texts[kind], True, False)], [(label, 10, texts[kind], False, False)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.02, space_after=2)
    return (x, y, w, h)


# Track I lane
add_text(s12, MARGIN, 2.5, CONTENT_W, 0.28, [[("TRACK I — our IP", 12, THEME["accentPrimary"], True, False)]])
mw, mh = 3.3, 0.95
t1y = 2.82
m1 = milestone(s12, MARGIN, t1y, mw, mh, "M1", "coverage — done", "done")
m2 = milestone(s12, MARGIN + (mw + 0.6), t1y, mw, mh, "M2", "analysis surface (report.py)", "next")
m3 = milestone(s12, MARGIN + 2 * (mw + 0.6), t1y, mw, mh, "M3", "combine / coalesce", "next")
edge(s12, m1, m2, THEME["surfaceInverse"], width=2.2)
edge(s12, m2, m3, THEME["surfaceInverse"], width=2.2)
# Track II lane
add_text(s12, MARGIN, 4.05, CONTENT_W, 0.28,
         [[("TRACK II — adopted eval (staged)", 12, THEME["accentSecondary"], True, False)]])
t2y = 4.37
m4 = milestone(s12, MARGIN, t2y, mw, mh, "M4", "formalize judge + rubric", "next")
m5 = milestone(s12, MARGIN + (mw + 0.6), t2y, mw, mh, "M5", "first comparative benchmark", "next")
m6 = milestone(s12, MARGIN + 2 * (mw + 0.6), t2y, mw, mh, "M6", "self-improvement loop", "gated")
edge(s12, m4, m5, THEME["surfaceInverse"], width=2.2)
# gate before M6
gx = m5[0] + mw + 0.18
add_rect(s12, gx, t2y - 0.05, 0.12, mh + 0.1, fill_hex=THEME["caution"])
add_text(s12, gx - 0.55, t2y + mh + 0.02, 1.25, 0.24,
         [[("gated: M4+M5", 9.5, "9A7B0A", True, False)]], align=PP_ALIGN.CENTER)
connect(s12, gx + 0.12, t2y + mh / 2, m6[0], t2y + mh / 2, THEME["caution"], width=2.2)
# reuse annotation on M5
add_rect(s12, m5[0] + 0.35, t2y + mh + 0.28, mw - 0.7, 0.34, fill_hex=THEME["accentSoft"],
         shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
add_text(s12, m5[0] + 0.35, t2y + mh + 0.28, mw - 0.7, 0.34,
         [[("reuse, don't build — runs on the meta-harness", 9.5, THEME["accentPrimary"], True, False)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
# execution principle band
ep_y = 6.05
add_rect(s12, MARGIN, ep_y, CONTENT_W, 0.85, fill_hex=THEME["surfaceElevated"], line_hex=THEME["border"])
add_text(s12, MARGIN + 0.25, ep_y, CONTENT_W - 0.5, 0.85,
         [[("Execution principle (charter decisions 6–8): ", 14, THEME["textAccent"], True, False),
           ("methodologies are adopted (SkillOpt, ClosedLoop judges), the eval harness is reused — "
            "M5 runs through Henry's existing meta-harness on cheap models. Nothing bespoke gets built.",
            14, THEME["textPrimary"], False, False)]],
         anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.1)

# ===========================================================================
# Slide 13 -- Decisions made -- and the plan forward (decision cards + outcome chips)
# ===========================================================================
s13 = blank_slide(prs)
add_kicker_title_lede(
    s13, KICKER, "Decisions made — and the plan forward",
    "Henry decided the batch on July twentieth: items A through E accepted as recommended, and "
    "F reversed — the saved gaps view will be built.", lede_h=0.7)
decisions = [
    ("A", "The five roster promotions from slide 6.", "approved",
     THEME["dataPositive"], THEME["textInverse"], False),
    ("B", "Drop / fold the duplicative coleam00 excalidraw skill.", "approved — drop",
     THEME["dataPositive"], THEME["textInverse"], False),
    ("C", "Accept vendor-only coverage for improve-code via anthropic's code-simplifier.",
     "accepted", THEME["dataPositive"], THEME["textInverse"], False),
    ("D", "Approve the obsidian-cli reference fix next session — satisfies BOTH remaining "
          "promotion-gate criteria.", "approved", THEME["dataPositive"], THEME["textInverse"], False),
    ("E", "The repo/path pointer to the meta-harness — M5 cannot start without it, and nothing "
          "gets built in its place by design.", "STILL NEEDED — blocks M5",
     THEME["dataNegative"], THEME["textInverse"], True),
    ("F", "Optional: a saved gaps view in the database.", "REVERSED — will build",
     THEME["accentPrimary"], THEME["textInverse"], False),
]
d_top = 2.5
d_h = 0.53
d_gap = 0.05
for i, (letter, text, outcome, chip_fill, chip_text_color, blocker) in enumerate(decisions):
    y = d_top + i * (d_h + d_gap)
    add_rect(s13, MARGIN, y, CONTENT_W, d_h, fill_hex=THEME["surface"], line_hex=THEME["border"])
    badge = THEME["dataNegative"] if blocker else THEME["accentPrimary"]
    add_rect(s13, MARGIN, y, 0.6, d_h, fill_hex=badge)
    add_text(s13, MARGIN, y, 0.6, d_h, [[(letter, 20, THEME["textInverse"], True, False)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    chip_w = 2.3
    add_text(s13, MARGIN + 0.78, y, CONTENT_W - chip_w - 1.15, d_h,
             [[(text, 13, THEME["textPrimary"], blocker, False)]],
             anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.02)
    chip(s13, CONTENT_RIGHT - chip_w - 0.12, y + 0.08, chip_w, d_h - 0.16, outcome,
         chip_fill, chip_text_color, size=10.5)
band_y = d_top + 6 * d_h + 5 * d_gap + 0.14
band_h = 0.72
add_rect(s13, MARGIN, band_y, CONTENT_W, band_h, fill_hex=THEME["surfaceInverse"],
         shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
add_text(s13, MARGIN + 0.3, band_y, CONTENT_W - 0.6, band_h,
         [[("All remaining development is now tracked as epic #154 with 13 sub-issues "
            "(#155–#167) — promotions, coleam00 drop, gate path, coverage_gaps view, M2–M6.",
            14, THEME["textInverse"], True, False)]],
         anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.15)

# ===========================================================================
# Slide 14 -- Health and invariants (gate-tick chips + bullets)
# ===========================================================================
s14 = blank_slide(prs)
add_kicker_title_lede(
    s14, KICKER, "Health and invariants",
    "Everything the project asserts about itself was verified by gates this session, and the "
    "operating knowledge is now written down.", lede_h=0.7)
add_text(s14, MARGIN, 2.42, CONTENT_W, 0.26,
         [[("ALL DEFINITION-OF-DONE GATES GREEN", 11, THEME["dataPositive"], True, False)]])
gates = ["idempotent loaders", "ingest checksum-verified", "zero unlinked assessments",
         "make ci — 120 tests", "data.db WAL-checkpointed"]
ggap = 0.12
gw = (CONTENT_W - (len(gates) - 1) * ggap) / len(gates)
for i, g in enumerate(gates):
    x = MARGIN + i * (gw + ggap)
    add_rect(s14, x, 2.72, gw, 0.72, fill_hex=THEME["surface"], line_hex=THEME["dataPositive"], line_w=1.5,
             shape_type=MSO_SHAPE.ROUNDED_RECTANGLE)
    add_text(s14, x + 0.08, 2.72, gw - 0.16, 0.72,
             [[("✓ ", 12, THEME["dataPositive"], True, False), (g, 11, THEME["textPrimary"], True, False)]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0)
add_bullets(
    s14, MARGIN, 3.8, CONTENT_W, 2.9,
    [
        ("Standing invariants: session-only database credentials (judge agents are structurally "
         "read-only); every verdict provenance-linked; generated artifacts have regen scripts; "
         "schema changes merge-by-name.", False),
        ("New this session: PROCEDURES.md — the runbook with script run order, the evaluated-pass "
         "pattern, gates, and the commit discipline — so any cold session can operate the project.",
         False),
    ], size=15, gap=0.2)

# ===========================================================================
# Slide 15 -- Status in one line (closing statement + recap flow)
# ===========================================================================
s15 = blank_slide(prs)
add_text(s15, MARGIN, 0.42, CONTENT_W, 0.32, [[(KICKER, 11, THEME["accentPrimary"], True, False)]])
add_text(s15, MARGIN, 0.74, CONTENT_W, 0.6, [[("Status in one line", 28, THEME["textPrimary"], True, False)]])
card = add_rect(s15, MARGIN, 1.65, CONTENT_W, 2.15, fill_hex=THEME["surfaceInverse"])
add_rect(s15, MARGIN, 1.65, 0.12, 2.15, fill_hex=THEME["accentTertiary"])
tf = card.text_frame
tf.word_wrap = True
tf.margin_left = Inches(0.45)
tf.margin_right = Inches(0.45)
tf.margin_top = Inches(0.3)
tf.margin_bottom = Inches(0.3)
tf.vertical_anchor = MSO_ANCHOR.MIDDLE
p = tf.paragraphs[0]
p.line_spacing = 1.25
r = p.add_run()
r.text = ("Foundation complete and verified; decisions made; all remaining development tracked "
          "on epic #154 — the evaluation track starts once the meta-harness pointer lands.")
r.font.name = FONT
r.font.size = Pt(20)
r.font.color.rgb = C(THEME["textInverse"])
# recap flow: M1 delivered -> decisions -> M5 goes live
add_text(s15, MARGIN, 3.98, CONTENT_W, 0.26,
         [[("THE PATH FROM HERE", 11, THEME["textSecondary"], True, False)]])
flow = [("M1 delivered", THEME["dataPositive"], THEME["textInverse"]),
        ("5 promotions + meta-harness pointer", THEME["caution"], THEME["textPrimary"]),
        ("evaluation track goes live", THEME["accentPrimary"], THEME["textInverse"])]
fw = (CONTENT_W - 2 * 0.65) / 3
for i, (label, fill, tcol) in enumerate(flow):
    x = MARGIN + i * (fw + 0.65)
    chip(s15, x, 4.3, fw, 0.66, label, fill, tcol, size=13)
    if i < len(flow) - 1:
        connect(s15, x + fw + 0.06, 4.63, x + fw + 0.65 - 0.06, 4.63, THEME["borderStrong"], width=2.5)
info = [
    "Branch feat/extender-db pushed through fa84ecd · working tree clean · server restartable via serve.sh",
    "Epic: #154 · Runbook: PROCEDURES.md · Matrix: coverage-matrix.md",
]
for i, text in enumerate(info):
    y = 5.35 + i * 0.7
    add_rect(s15, MARGIN, y, CONTENT_W, 0.58, fill_hex=THEME["surface"], line_hex=THEME["border"])
    add_text(s15, MARGIN + 0.3, y, CONTENT_W - 0.6, 0.58, [[(text, 13.5, THEME["textPrimary"], False, False)]],
             anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.05)

# ===========================================================================
# Footers (deferred: index by creation order, total = final slide count)
# ===========================================================================
total = len(DECK)
for idx, (slide, note) in enumerate(DECK, start=1):
    add_text(slide, MARGIN, SLIDE_H - 0.42, 9.5, 0.3,
             [[(note or "", 9.5, THEME["textSecondary"], False, False)]])
    add_text(slide, CONTENT_RIGHT - 1.6, SLIDE_H - 0.42, 1.6, 0.3,
             [[(f"{idx} / {total}", 9.5, THEME["textSecondary"], False, False)]], align=PP_ALIGN.RIGHT)

OUT_PATH = ("/Users/henry/Developer/_hsb3/dotfiles-agents/_meta/briefings/"
            "2026-07-20-extender-db-status/extender-db-status-briefing.pptx")
prs.save(OUT_PATH)
print(f"Wrote {OUT_PATH} with {len(prs.slides)} slides")
