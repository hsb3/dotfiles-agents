#!/usr/bin/env python3
"""Consumer-facing catalog drift guard — the README's plugin lineup, machine-checked.

README.md is hand-authored (nothing generated is tracked, ADR 0017), so this guard
verifies it against the manifests and against the plugin assemblies on disk instead of
generating it. README.md and `.claude-plugin/marketplace.json` are lifted verbatim onto
the published `main` branch (`.github/workflows/publish.yml`), so a relative link that
only resolves on `dev` (e.g. into `primitives-core/` or `scripts/`) 404s for every
visitor, and a stale catalog cell is a lie on the front page.

README.md is read as it RENDERS: fenced code blocks and HTML comments are blanked out
before anything below is parsed, so a table wrapped in ``` or `<!-- -->` counts as no
table rather than as a passing one. Six checks:

  1. Catalog coverage — exactly one `## Catalog` heading, whose section carries at least
     one row; every plugin in `.claude-plugin/marketplace.json` has exactly one row; no
     row names a plugin absent from the marketplace; no duplicate rows. The plugin cell's
     fixed contract is `| [\\`<id>\\`](plugins/<id>/README.md) | ... |` — a row whose
     backticked id and link-path id disagree is a violation.
  2. Catalog cell content — per row, `Kind` is exactly `bundle` or `standalone` AND
     agrees with the assembly on disk (a plugin whose `plugins/<id>/` holds more than one
     skill, or any agent, hook, or command, is a bundle; a one-skill assembly is
     standalone — an MCP server does not enter this, since kind counts the units a user
     invokes); the blurb is a non-empty single sentence of at most 140 characters; the
     `Contents` cell is a `<n> skills · <n> agents · <n> hooks · <n> commands ·
     <n> MCP servers` list whose counts equal what `plugins/<id>/` actually holds — the
     four member directories, plus the servers `plugins/<id>/.mcp.json` declares (a
     unit with a zero count is omitted from the cell, not written as `0`).
  3. Published-surface links — every inline Markdown link, reference-style link
     definition (`[label]: dest`), and HTML `href=`/`src=` attribute in README.md is an
     absolute `http(s)://` URL, a pure `#anchor`, or a relative path that (a) exists on
     disk and (b) is on the publish lift map: anything under `plugins/`, or one of
     `README.md`, `.gitignore`, `.claude-plugin/marketplace.json`. Nothing else exists on
     `main` — including the rest of `.claude-plugin/`.
  4. Manifest parity — every `plugins/<id>/.claude-plugin/plugin.json` agrees with that
     plugin's marketplace.json entry on BOTH `description` and `version`.
  5. metadata.description claims — the marketplace blurb's stated counts are checked
     against reality (`N plugins` vs `len(plugins)`, `N bundles` / `N standalone` vs the
     real split, digits or number words), and the plugin names it enumerates in a list
     must be real plugin ids.
  6. Description quality — every `description` in any `plugin.json` and in
     marketplace.json (including `metadata.description`) is present, non-empty, at least
     40 characters, does not end in an ellipsis (`…` / `...`), and ends its final
     sentence with `.`, `!`, or `?` (an unterminated tail is a mid-sentence cutoff).

Deliberately NOT covered: prose counts in README.md body text (only marketplace.json's
`metadata.description` is count-checked); whether a metadata enumeration is exhaustive or
lists a name under the right kind; the wording of a blurb beyond shape; and anchors are
not resolved to real headings. Check 5's enumeration scan is a heuristic — it validates a
run of three or more comma/colon/dash-separated single-token items only when at least two
of them are real plugin ids, so a wholly fabricated list is not caught. Sentence counting
is punctuation-based (`.`/`!`/`?` before whitespace or end), so an abbreviation followed
by a space reads as a sentence break; a mid-blurb `draw.io` or `.claude` does not.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violations (prints every one).
Usage: python3 scripts/check_catalog.py   (run from anywhere)
"""

import json
import os
import re
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(REPO, "README.md")
MARKETPLACE = os.path.join(REPO, ".claude-plugin", "marketplace.json")
PLUGINS_DIR = os.path.join(REPO, "plugins")

CATALOG_HEADING = re.compile(r"^##\s+Catalog\s*$")
HEADING = re.compile(r"^##\s+")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
# The fixed catalog-row contract: the plugin cell is a link whose text and href we pull
# apart separately so a mismatch between them (backticked id vs linked path id) is its
# own violation rather than a silent non-match.
ROW_LINK = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]+)\)")
BACKTICKED_ID = re.compile(r"^`([A-Za-z0-9_.-]+)`$")
ROW_PATH_ID = re.compile(r"^plugins/([A-Za-z0-9_.-]+)/README\.md$")
MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REF_LINK_DEF = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*(\S+)")
HTML_LINK_ATTR = re.compile(r"\b(href|src)\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)

# The publish lift map (.github/workflows/publish.yml): plugins/ is copied whole
# (dereferenced), then three individual files. Everything else is dev-only.
PUBLISHED_DIRS = {"plugins"}
PUBLISHED_FILES = {"README.md", ".gitignore", os.path.join(".claude-plugin", "marketplace.json")}
PUBLISHED_BLURB = (
    "only plugins/, .claude-plugin/marketplace.json, README.md, and .gitignore ship on main"
)

KINDS = ("bundle", "standalone")
CONTENTS_UNITS = ("skill", "agent", "hook", "command", "MCP server")
CONTENTS_TOKEN = re.compile(r"^(\d+)\s+(skill|agent|hook|command|MCP server)s?$")
CONTENTS_SEP = "·"
CONTENTS_SHAPE = f" {CONTENTS_SEP} ".join(f"<n> {u}s" for u in CONTENTS_UNITS)
MCP_SPEC = ".mcp.json"
MAX_BLURB_CHARS = 140
MIN_DESCRIPTION_CHARS = 40
SENTENCE_END = re.compile(r"[.!?](?=\s|$)")
ELLIPSIS_TAIL = re.compile(r"(?:…|\.\.\.)[.…\s]*$")

TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")
UNIT_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
TENS_WORDS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}
COUNT_NOUNS = (
    ({"standalone", "standalones"}, "standalone", "standalone plugin(s)"),
    ({"bundle", "bundles"}, "bundle", "bundle(s)"),
    ({"plugin", "plugins"}, "total", "plugin(s)"),
)
COUNT_WINDOW = 4
ENUM_SPLIT = re.compile(r"[,:;—–]")
PLUGIN_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
PARENTHETICAL = re.compile(r"\([^()]*\)")


def _load_marketplace():
    """Return the parsed marketplace.json, or None if it's missing."""
    if not os.path.isfile(MARKETPLACE):
        return None
    with open(MARKETPLACE, encoding="utf-8") as fh:
        return json.load(fh)


def _read_readme_lines():
    """Return README.md's lines, or None if it's missing."""
    if not os.path.isfile(README_PATH):
        return None
    with open(README_PATH, encoding="utf-8") as fh:
        return fh.readlines()


def _strip_render_noise(lines):
    """Blank out fenced code blocks and HTML comments, preserving the line count.

    A catalog table inside ``` or `<!-- -->` renders as no catalog at all; parsing the
    raw source would let either one hide the whole front door behind a green check.
    """
    out = []
    fence = None
    in_comment = False
    for raw in lines:
        if fence is not None:
            out.append("\n")
            m = FENCE.match(raw)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            continue
        line = raw
        if in_comment:
            end = line.find("-->")
            if end == -1:
                out.append("\n")
                continue
            line = line[end + 3:]
            in_comment = False
        while True:
            start = line.find("<!--")
            if start == -1:
                break
            end = line.find("-->", start + 4)
            if end == -1:
                line = line[:start]
                in_comment = True
                break
            line = line[:start] + line[end + 3:]
        m = FENCE.match(line)
        if m:
            fence = m.group(1)
            out.append("\n")
            continue
        out.append(line if line.endswith("\n") else line + "\n")
    return out


def _readme_render_lines():
    """README.md's lines as they render — fenced blocks and HTML comments blanked out."""
    lines = _read_readme_lines()
    if lines is None:
        return None
    return _strip_render_noise(lines)


def _catalog_sections(lines):
    """Return one (heading_index, section_lines) pair per `## Catalog` heading."""
    sections = []
    for i, line in enumerate(lines):
        if not CATALOG_HEADING.match(line.rstrip("\n")):
            continue
        end = len(lines)
        for j in range(i + 1, len(lines)):
            if HEADING.match(lines[j]):
                end = j
                break
        sections.append((i, lines[i + 1:end]))
    return sections


def _row_cells(line):
    """Split a `| a | b | c |` table row into its stripped cells."""
    s = line.strip()
    if not s.startswith("|"):
        return []
    body = s[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in body.split("|")]


def _count_children(path, want_dirs, suffix=None):
    """Count the public immediate children of `path` (symlinks followed).

    A leading dot or underscore marks a child that is not a member of the
    assembly: `hooks/_lib/` is the hooks' shared append helper, imported by
    them rather than registered as one of them, and counting it would put the
    catalog one hook ahead of the plugin's real contents.
    """
    if not os.path.isdir(path):
        return 0
    n = 0
    for entry in os.listdir(path):
        if entry.startswith((".", "_")):
            continue
        full = os.path.join(path, entry)
        if want_dirs:
            if os.path.isdir(full):
                n += 1
        elif os.path.isfile(full) and (suffix is None or entry.endswith(suffix)):
            n += 1
    return n


def _count_mcp_servers(base):
    """Count the servers plugins/<pid>/.mcp.json declares — the file is not a member dir.

    A spec that will not parse counts zero: JSON validity is `check_manifests.py`'s job,
    and reading a broken file as "one server" would make this guard's message blame the
    catalog for a defect that is not there.
    """
    path = os.path.join(base, MCP_SPEC)
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, encoding="utf-8") as fh:
            servers = json.load(fh).get("mcpServers")
    except (ValueError, OSError, AttributeError):
        return 0
    return len(servers) if isinstance(servers, dict) else 0


def _assembly_counts(pid):
    """Return (skills, agents, hooks, commands, mcp servers) for plugins/<pid>/, or None.

    Order matches CONTENTS_UNITS; commands are flat `.md` files like agents.
    """
    base = os.path.join(PLUGINS_DIR, pid)
    if not os.path.isdir(base):
        return None
    return (
        _count_children(os.path.join(base, "skills"), want_dirs=True),
        _count_children(os.path.join(base, "agents"), want_dirs=False, suffix=".md"),
        _count_children(os.path.join(base, "hooks"), want_dirs=True),
        _count_children(os.path.join(base, "commands"), want_dirs=False, suffix=".md"),
        _count_mcp_servers(base),
    )


def _kind_counts(counts):
    """(skills, agents, hooks, commands) read by unit name, not by position in the tuple —
    a bare `counts[:4]` silently mislabels the columns if CONTENTS_UNITS is ever reordered."""
    by_unit = dict(zip(CONTENTS_UNITS, counts))
    return tuple(by_unit[u] for u in ("skill", "agent", "hook", "command"))


def _expected_kind(counts):
    """A multi-skill assembly, or one carrying agents, hooks, or commands, is a bundle.

    An MCP server is deliberately not part of this: kind counts the units a user invokes,
    and a server spec rides along with the skill that drives it.
    """
    skills, agents, hooks, commands = _kind_counts(counts)
    return "bundle" if (skills > 1 or agents or hooks or commands) else "standalone"


def _contents_label(counts_by_unit):
    """Render `{skill: 2, hook: 1}` as `2 skills · 1 hook`."""
    parts = []
    for unit in CONTENTS_UNITS:
        n = counts_by_unit.get(unit, 0)
        if n:
            parts.append(f"{n} {unit}{'' if n == 1 else 's'}")
    return f" {CONTENTS_SEP} ".join(parts) if parts else "no skills, agents, hooks, or commands"


def _parse_contents(cell):
    """Return {unit: count} for a `2 skills · 1 agent` cell, or None if unparseable."""
    if not cell:
        return None
    parsed = {}
    for part in cell.split(CONTENTS_SEP):
        m = CONTENTS_TOKEN.match(part.strip())
        if not m or m.group(2) in parsed:
            return None
        parsed[m.group(2)] = int(m.group(1))
    return parsed


def _row_cell_problems(pid, cells):
    """Check 2: the Kind, blurb, and Contents cells of one catalog row."""
    problems = []
    if len(cells) != 4:
        return [
            f"README.md catalog row for `{pid}`: has {len(cells)} cell(s), not the 4 the "
            "catalog-row contract fixes (plugin | Kind | what it does | Contents)"
        ]
    kind, blurb, contents = cells[1], cells[2], cells[3]
    counts = _assembly_counts(pid)

    if kind not in KINDS:
        problems.append(
            f"README.md catalog row for `{pid}`: Kind cell {kind!r} is neither `bundle` "
            "nor `standalone`"
        )
    elif counts is not None:
        expected = _expected_kind(counts)
        if kind != expected:
            skills, agents, hooks, commands = _kind_counts(counts)
            problems.append(
                f"README.md catalog row for `{pid}`: Kind cell {kind!r} disagrees with the "
                f"assembly — plugins/{pid}/ holds {skills} skill(s), {agents} agent(s), "
                f"{hooks} hook(s), {commands} command(s), which is a {expected}"
            )

    if not blurb:
        problems.append(
            f"README.md catalog row for `{pid}`: the 'what it does' cell is empty — the rule "
            "is one non-empty sentence"
        )
    else:
        if len(blurb) > MAX_BLURB_CHARS:
            problems.append(
                f"README.md catalog row for `{pid}`: blurb {blurb!r} is {len(blurb)} chars — "
                f"the rule is at most {MAX_BLURB_CHARS}"
            )
        ends = SENTENCE_END.findall(blurb)
        if not ends:
            problems.append(
                f"README.md catalog row for `{pid}`: blurb {blurb!r} does not end in `.`, `!`, "
                "or `?` — the rule is one complete sentence"
            )
        elif len(ends) > 1:
            problems.append(
                f"README.md catalog row for `{pid}`: blurb {blurb!r} runs {len(ends)} "
                "sentences — the rule is exactly one"
            )

    if counts is not None:
        stated = _parse_contents(contents)
        if stated is None:
            problems.append(
                f"README.md catalog row for `{pid}`: Contents cell {contents!r} is not a "
                f"`{CONTENTS_SHAPE}` list"
            )
        else:
            actual = {u: n for u, n in zip(CONTENTS_UNITS, counts) if n}
            stated = {u: n for u, n in stated.items() if n}
            if stated != actual:
                problems.append(
                    f"README.md catalog row for `{pid}`: Contents cell {contents!r} disagrees "
                    f"with the assembly — plugins/{pid}/ holds {_contents_label(actual)}"
                )
    return problems


def catalog_problems():
    """Checks 1 and 2: the `## Catalog` table matches marketplace.json and the assemblies."""
    market = _load_marketplace()
    if market is None:
        return [".claude-plugin/marketplace.json: missing at the repo root"]
    market_ids = {p.get("name") for p in market.get("plugins", []) if p.get("name")}

    lines = _readme_render_lines()
    if lines is None:
        return ["README.md: missing at the repo root"]
    sections = _catalog_sections(lines)
    if not sections:
        return ["README.md: no '## Catalog' heading found"]

    problems = []
    if len(sections) > 1:
        where = ", ".join(f"line {i + 1}" for i, _ in sections)
        problems.append(
            f"README.md: {len(sections)} '## Catalog' headings ({where}) — the rule is exactly "
            "one; only the first is checked and readers only see the first"
        )

    row_ids = []
    for raw_line in sections[0][1]:
        line = raw_line.strip()
        m = ROW_LINK.match(line)
        if not m:
            continue  # not a data row (header, separator, or prose in the section)
        text, href = m.group(1), m.group(2)
        bt = BACKTICKED_ID.match(text)
        if not bt:
            problems.append(
                f"README.md catalog row {line!r}: plugin cell {text!r} is not backticked "
                "as `<id>` per the fixed catalog-row contract"
            )
            continue
        ph = ROW_PATH_ID.match(href)
        if not ph:
            problems.append(
                f"README.md catalog row {line!r}: link {href!r} does not follow the fixed "
                "plugins/<id>/README.md contract"
            )
            continue
        bt_id, ph_id = bt.group(1), ph.group(1)
        if bt_id != ph_id:
            problems.append(
                f"README.md catalog row: id mismatch — backticked `{bt_id}` vs link path "
                f"plugins/{ph_id}/README.md"
            )
            continue
        row_ids.append(bt_id)
        problems.extend(_row_cell_problems(bt_id, _row_cells(line)))

    if not row_ids:
        problems.append(
            "README.md: the '## Catalog' section holds no catalog rows — the rule is one row "
            "per plugin (a table inside a ``` fence or an HTML comment renders as no catalog)"
        )
        return problems

    for id_, n in sorted(Counter(row_ids).items()):
        if n > 1:
            problems.append(f"README.md catalog: duplicate row for `{id_}` ({n} rows)")

    row_id_set = set(row_ids)
    for id_ in sorted(market_ids - row_id_set):
        problems.append(
            f"README.md catalog: missing a row for plugin `{id_}` (listed in "
            "marketplace.json but absent from the Catalog table)"
        )
    for id_ in sorted(row_id_set - market_ids):
        problems.append(f"README.md catalog: row names `{id_}`, which is not a plugin in marketplace.json")
    return problems


def _readme_link_refs(text):
    """Yield (form, href) for every inline link, reference definition, and HTML attribute."""
    for m in MD_LINK.finditer(text):
        yield "link", m.group(1)
    for line in text.splitlines():
        m = REF_LINK_DEF.match(line)
        if m:
            yield "reference-style link definition", m.group(2)
    for m in HTML_LINK_ATTR.finditer(text):
        yield f"HTML {m.group(1).lower()} attribute", m.group(2)


def link_problems():
    """Check 3: every relative README.md link resolves inside the published surface."""
    lines = _readme_render_lines()
    if lines is None:
        return ["README.md: missing at the repo root"]
    text = "".join(lines)

    problems = []
    seen = set()
    for form, raw in _readme_link_refs(text):
        raw = raw.strip()
        if not raw:
            continue
        href = raw.split()[0]  # drop an optional `"title"` suffix
        href = href.strip("<>")
        if (form, href) in seen:
            continue
        seen.add((form, href))

        if href.startswith("http://") or href.startswith("https://"):
            continue
        if href.startswith("#"):
            continue  # pure anchor
        if href.startswith("mailto:"):
            continue

        path_part = href.split("#", 1)[0]
        if not path_part:
            continue  # `somefile.md#anchor` with empty path shouldn't occur, but be safe

        abs_path = os.path.normpath(os.path.join(REPO, path_part))
        if not os.path.exists(abs_path):
            problems.append(
                f"README.md {form} {href!r}: relative path {path_part!r} does not exist on disk"
            )
            continue

        rel = os.path.relpath(abs_path, REPO)
        if rel == os.pardir or rel.startswith(os.pardir + os.sep):
            problems.append(f"README.md {form} {href!r}: resolves outside the repo")
            continue

        if rel in PUBLISHED_FILES or rel.split(os.sep)[0] in PUBLISHED_DIRS:
            continue
        problems.append(
            f"README.md {form} {href!r}: resolves to {rel!r}, which is outside the published "
            f"surface ({PUBLISHED_BLURB})"
        )
    return problems


def _plugin_manifests():
    """Yield (pid, marketplace_entry, plugin_json_or_None) for every marketplace entry."""
    market = _load_marketplace()
    for entry in (market or {}).get("plugins", []):
        pid = entry.get("name", "?")
        pj_path = os.path.join(PLUGINS_DIR, pid, ".claude-plugin", "plugin.json")
        if not os.path.isfile(pj_path):
            yield pid, entry, None
            continue
        with open(pj_path, encoding="utf-8") as fh:
            yield pid, entry, json.load(fh)


def description_problems():
    """Check 4a: plugin.json's description matches marketplace.json's, per plugin."""
    if _load_marketplace() is None:
        return [".claude-plugin/marketplace.json: missing at the repo root"]
    problems = []
    for pid, entry, pj in _plugin_manifests():
        if pj is None:
            problems.append(
                f"plugins/{pid}/.claude-plugin/plugin.json: missing — cannot verify "
                "description parity with marketplace.json"
            )
            continue
        if pj.get("description", "") != entry.get("description", ""):
            problems.append(
                f"plugins/{pid}: description drift — plugin.json and marketplace.json disagree for `{pid}`"
            )
    return problems


def version_problems():
    """Check 4b: plugin.json's version matches marketplace.json's, per plugin."""
    if _load_marketplace() is None:
        return [".claude-plugin/marketplace.json: missing at the repo root"]
    problems = []
    for pid, entry, pj in _plugin_manifests():
        if pj is None:
            continue  # already reported by description_problems()
        mk_ver, pj_ver = entry.get("version"), pj.get("version")
        if mk_ver is None:
            problems.append(f"marketplace.json[{pid}]: no `version` field — the entry must state one")
        if pj_ver is None:
            problems.append(
                f"plugins/{pid}/.claude-plugin/plugin.json: no `version` field — the manifest must state one"
            )
        if mk_ver is not None and pj_ver is not None and mk_ver != pj_ver:
            problems.append(
                f"plugins/{pid}: version drift — plugin.json says {pj_ver!r}, marketplace.json "
                f"says {mk_ver!r} for `{pid}`"
            )
    return problems


def _token_number(token):
    """Return the integer a token states (`20`, `sixteen`, `twenty-four`), or None."""
    t = token.lower()
    if t.isdigit():
        return int(t)
    if t in UNIT_WORDS:
        return UNIT_WORDS[t]
    if t in TENS_WORDS:
        return TENS_WORDS[t]
    if "-" in t:
        head, tail = t.split("-", 1)
        if head in TENS_WORDS and tail in UNIT_WORDS and 1 <= UNIT_WORDS[tail] <= 9:
            return TENS_WORDS[head] + UNIT_WORDS[tail]
    return None


def _stated_counts(text):
    """Yield (key, label, claimed) for every `<number> plugins|bundles|standalone` claim."""
    tokens = [m.group(0) for m in TOKEN.finditer(text)]
    for i, token in enumerate(tokens):
        n = _token_number(token)
        if n is None:
            continue
        for follower in tokens[i + 1:i + 1 + COUNT_WINDOW]:
            word = follower.lower()
            match = next((c for c in COUNT_NOUNS if word in c[0]), None)
            if match:
                yield match[1], match[2], n
                break


def _enumerated_names(text, known_ids):
    """Return the plugin names a comma/colon/dash-separated enumeration lists.

    Heuristic (documented in the module docstring): parentheticals are dropped, the rest
    is split on list punctuation, and a run of three or more single-token chunks counts as
    an enumeration only when at least two of its members are real plugin ids.
    """
    flat = PARENTHETICAL.sub(" ", text)
    names, run = [], []
    for chunk in ENUM_SPLIT.split(flat) + [""]:
        candidate = chunk.strip().strip(".").strip().strip("`'\"")
        for lead in ("and ", "or ", "plus "):
            if candidate.lower().startswith(lead):
                candidate = candidate[len(lead):].strip().strip("`")
        if candidate and PLUGIN_ID.match(candidate):
            run.append(candidate)
            continue
        if len(run) >= 3 and sum(1 for r in run if r in known_ids) >= 2:
            names.extend(run)
        run = []
    return names


def metadata_problems():
    """Check 5: marketplace metadata.description's stated counts and names are real."""
    market = _load_marketplace()
    if market is None:
        return [".claude-plugin/marketplace.json: missing at the repo root"]
    desc = market.get("metadata", {}).get("description", "") or ""
    if not desc:
        return []  # emptiness is check 6's violation, not this one's

    entries = market.get("plugins", [])
    ids = [e.get("name", "?") for e in entries]
    kinds = Counter()
    for pid in ids:
        counts = _assembly_counts(pid)
        if counts is not None:
            kinds[_expected_kind(counts)] += 1
    actual = {"total": len(entries), "bundle": kinds["bundle"], "standalone": kinds["standalone"]}

    problems = []
    for key, label, claimed in _stated_counts(desc):
        if claimed != actual[key]:
            problems.append(
                f"marketplace.json metadata.description: claims {claimed} {label}, but the "
                f"marketplace has {actual[key]} — the rule is that stated counts match the manifest"
            )
    known = set(ids)
    for name in _enumerated_names(desc, known):
        if name not in known:
            problems.append(
                f"marketplace.json metadata.description: enumerates `{name}`, which is not a "
                "plugin in marketplace.json"
            )
    return problems


def _description_quality(where, obj):
    """Check 6, for one manifest: present, non-empty, long enough, not cut off."""
    if "description" not in obj:
        return [f"{where}: no `description` key — every shipped manifest must carry one"]
    desc = obj.get("description")
    if not isinstance(desc, str) or not desc.strip():
        return [f"{where}: description is empty — every shipped manifest must carry a real one"]
    d = desc.strip()
    if ELLIPSIS_TAIL.search(d):
        return [f"{where}: ends with an ellipsis — looks truncated ({d[-40:]!r})"]
    problems = []
    if len(d) < MIN_DESCRIPTION_CHARS:
        problems.append(
            f"{where}: description is {len(d)} chars ({d!r}) — under the "
            f"{MIN_DESCRIPTION_CHARS}-character floor"
        )
    if d[-1] not in ".!?":
        problems.append(
            f"{where}: description ends {d[-40:]!r} with no closing `.`, `!`, or `?` — its "
            "final sentence is unterminated, which is how a mid-word cutoff looks"
        )
    return problems


def truncation_problems():
    """Check 6: every shipped description is present, substantial, and not cut off."""
    market = _load_marketplace()
    if market is None:
        return [".claude-plugin/marketplace.json: missing at the repo root"]
    problems = []

    problems.extend(_description_quality("marketplace.json metadata.description", market.get("metadata", {})))

    for entry in market.get("plugins", []):
        pid = entry.get("name", "?")
        problems.extend(_description_quality(f"marketplace.json[{pid}].description", entry))

    if os.path.isdir(PLUGINS_DIR):
        for d in sorted(os.listdir(PLUGINS_DIR)):
            pj_path = os.path.join(PLUGINS_DIR, d, ".claude-plugin", "plugin.json")
            if not os.path.isfile(pj_path):
                continue
            with open(pj_path, encoding="utf-8") as fh:
                pj = json.load(fh)
            problems.extend(
                _description_quality(f"plugins/{d}/.claude-plugin/plugin.json description", pj)
            )
    return problems


def main():
    problems = (
        catalog_problems()
        + link_problems()
        + description_problems()
        + version_problems()
        + metadata_problems()
        + truncation_problems()
    )
    if problems:
        print(f"✗ catalog guard: {len(problems)} violation(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(
        "✓ catalog guard clean — README catalog matches marketplace.json 1:1, every row's "
        "kind/blurb/contents matches the assembly on disk, all links resolve inside the "
        "published surface, plugin.json/marketplace.json descriptions and versions match, "
        "metadata.description's counts and names are real, no truncated descriptions"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
