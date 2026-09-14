"""Render every generated analysis doc for the extender DB from one data pass.

Supersedes `render_matrix.py`: same coverage-matrix.md, same rendering algorithm and
literal header text (byte-compatible with its output where the underlying data hasn't
changed), plus a NEW `analysis.md` covering the DB's other cross-cutting answers —
per-extender profiles, duplicative/conflicting/directed relationships, an assessor
comparison, and an eval-runs provenance index.

Generated-artifact discipline (both files): never hand-edit; re-run after any change to
assessments, job_coverage, relationships, extenders, or eval_runs. Deterministic (stable
sort keys throughout, no clocks/randomness) so reruns on unchanged data are no-ops.

    python3 report.py                              # writes both files next to this script
    python3 report.py --out DIR                     # writes both files into DIR instead
    python3 report.py --fixtures DIR                 # reads <DIR>/<collection>.json dumps
                                                      # instead of the live DB (dev/test —
                                                      # no PB credentials needed)

Session-run only in production mode (needs PB_URL/PB_ADMIN_EMAIL/PB_ADMIN_PASSWORD), like
the loaders and render_matrix.py. `--fixtures` mode needs neither the server nor credentials.

Data-access design: every collection is fetched whole (`list_all(coll)`, no server-side
filter) and every section filters/joins in plain Python. render_matrix.py issued one
filtered query for `assessments`; report.py issues none, trading that filter for a single
shared, uniform fetch that both output files reuse — simpler than threading N differently
-filtered queries through two documents. `PB` and a `FixtureSource` (same `list_all(coll)`
shape, backed by `<dir>/<collection>.json`) are interchangeable behind that one method, so
every rendering function is a pure function of the fetched data — trivially testable
against fixtures.

Key Functions:
    render_coverage_matrix(): the render_matrix.py algorithm, unchanged, over `data`.
    render_analysis(): the four new sections (see module docstring above), each a plain
        function of `data` returning row dicts, rendered to a markdown table.

Limitations:
    - The coverage-matrix.md header's provenance line is literal carried-over text
      from render_matrix.py (not data-derived, so it goes stale the same way the original
      did — e.g. it still only names the M1 eval_runs after the W2 delta). Left as-is for
      byte-compatibility; making it data-derived is a follow-up, not part of this brief.
    - "resolved-or-open" status on a relationship pair is a heuristic: the literal
      substring `RESOLVED` in its `evidence` text (the only convention the data uses today;
      there's no dedicated schema field). A relationship whose evidence happens to contain
      that word for other reasons would misclassify — none do today.
    - The relationship listing in analysis.md covers `duplicative`, `conflicting`,
      `precedes`, and `feeds-into` — the kinds that need a resolution or an ordering
      decision. `complementary` is informational abundance, not actionable, and stays out
      of the listing (it's already counted in coverage-matrix.md's kind-count table).
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pb import PB  # noqa: E402

FRAMEWORK_SLUG = "hsb3-jobs-to-be-done"
ASSESSOR = "coverage-v1"
MECHANICAL_ASSESSOR = "mechanical-v1"
JUDGED_ASSESSOR = "judged-v1"
COMPARISON_ASSESSORS = (MECHANICAL_ASSESSOR, JUDGED_ASSESSOR, ASSESSOR)
RESOLUTION_KINDS = ("duplicative", "conflicting", "precedes", "feeds-into")
DIRECTED_KINDS = ("precedes", "feeds-into")


class FixtureSource:
    """Dev/test data source: one `<collection>.json` file per collection, each a plain
    list of records — the same shape `PB.list_all(coll)` returns with no filter."""

    def __init__(self, path):
        self.path = path
        self._cache = {}

    def list_all(self, coll):
        if coll not in self._cache:
            fp = os.path.join(self.path, f"{coll}.json")
            with open(fp, encoding="utf-8") as fh:
                self._cache[coll] = json.load(fh)
        return self._cache[coll]


# --- data load -----------------------------------------------------------------------

def load(src):
    """Fetch every collection report.py needs, once, whole. Everything downstream is a
    plain function over this dict — no further data-source calls."""
    frameworks = src.list_all("frameworks")
    all_extenders = src.list_all("extenders")
    extenders = [e for e in all_extenders if not e.get("retired")]
    sources = src.list_all("sources")
    # Retiring keeps a dropped unit's assessments and edges, but every join below indexes
    # ext_by_id unguarded, so rows pointing at a filtered-out unit must go too.
    live = {e["id"] for e in extenders}
    all_relationships = src.list_all("relationships")
    relationships = [r for r in all_relationships
                     if r["extender_a"] in live and r["extender_b"] in live]
    all_assessments = src.list_all("assessments")
    assessments = [a for a in all_assessments if a["extender"] in live]
    return {
        "retired_units": len(all_extenders) - len(extenders),
        "suppressed_assessments": len(all_assessments) - len(assessments),
        "suppressed_relationships": len(all_relationships) - len(relationships),
        "frameworks": frameworks,
        "fw_by_id": {f["id"]: f for f in frameworks},
        "fw_by_slug": {f["slug"]: f for f in frameworks},
        "elements": src.list_all("framework_elements"),
        "extenders": extenders,
        "ext_by_id": {e["id"]: e for e in extenders},
        "sources": sources,
        "src_by_id": {s["id"]: s for s in sources},
        "job_coverage": src.list_all("job_coverage"),
        "relationships": relationships,
        "assessments": assessments,
        "eval_runs": src.list_all("eval_runs"),
    }


def projection_scope(data):
    return (
        f"Retired units excluded: **{data['retired_units']}**. "
        f"Suppressed rows: **{data['suppressed_assessments']} assessments**, "
        f"**{data['suppressed_relationships']} relationships**. "
        "Counts cover all fetched rows, before section-specific filtering. "
        "Assessments and relationships referencing retired or missing extenders are "
        "excluded; each relationship counts once even if both endpoints are excluded. "
        "Stored history is retained; eval-run linked-row counts reflect this active projection."
    )


# --- coverage-matrix.md (render_matrix.py's algorithm, unchanged) --------------------

def render_coverage_matrix(data):
    fw = data["fw_by_slug"].get(FRAMEWORK_SLUG)
    if fw is None:
        raise SystemExit(f"framework not found: {FRAMEWORK_SLUG}")
    jobs = sorted(
        (e for e in data["elements"] if e["framework"] == fw["id"]),
        key=lambda e: e["sort_order"])
    ext_by_id = data["ext_by_id"]
    src_by_id = data["src_by_id"]
    cov_by_job = {c["job"]: c for c in data["job_coverage"]}
    rels = data["relationships"]

    verdicts = defaultdict(lambda: {"present": [], "partial": []})
    for a in data["assessments"]:
        if a["framework"] == fw["id"] and a["assessor"] == ASSESSOR \
                and a["verdict"] in ("present", "partial"):
            verdicts[a["element"]][a["verdict"]].append(ext_by_id[a["extender"]]["slug"])

    lines = [
        "# Extender coverage matrix — jobs-to-be-done",
        "",
        "_Generated by `report.py` — do not hand-edit. Truth lives in the database",
        f"(assessor `{ASSESSOR}` assessments + `job_coverage` + `relationships`);",
        "this file is a rendered snapshot for reading and diff review._",
        "",
        f"Framework: `{FRAMEWORK_SLUG}` ({len(jobs)} jobs, "
        f"{len({j['category'] for j in jobs})} families) x {len(ext_by_id)} extenders.",
        "Provenance: eval_runs `m1-coverage-judged-2026-07-20`,",
        "`m1-coverage-review-2026-07-20`, `m1-coverage-adjudication-2026-07-20`.",
        "",
        projection_scope(data),
        "",
        "## Matrix",
        "",
        "| Job | Family | Status | Present | Partial | Disposition | Source |",
        "|---|---|---|---|---|---|---|",
    ]
    for j in jobs:
        v = verdicts[j["id"]]
        c = cov_by_job.get(j["id"], {})
        src = src_by_id.get(c.get("source") or "", {}).get("slug", "")
        lines.append("| `{}` | {} | **{}** | {} | {} | {} | {} |".format(
            j["slug"], j["category"], c.get("status", "?"),
            ", ".join(sorted(v["present"])) or "—",
            ", ".join(sorted(v["partial"])) or "—",
            c.get("disposition", "?"), src or "—"))

    lines += ["", "## Gaps and partial coverage", ""]
    for j in jobs:
        c = cov_by_job.get(j["id"], {})
        if c.get("status") in ("gap", "partial"):
            lines.append(f"- **`{j['slug']}`** ({c['status']}, disposition {c['disposition']}):"
                         f" {c.get('rationale', '')}")

    by_kind = defaultdict(list)
    for r in rels:
        by_kind[r["kind"]].append(r)
    lines += ["", "## Relationships", "",
              "| Kind | Count |", "|---|---|"]
    for kind in sorted(by_kind):
        lines.append(f"| {kind} | {len(by_kind[kind])} |")
    if by_kind.get("duplicative"):
        lines += ["", "### Duplicative pairs (M3 coalesce candidates)", ""]
        for r in sorted(by_kind["duplicative"],
                        key=lambda r: (ext_by_id[r["extender_a"]]["slug"], ext_by_id[r["extender_b"]]["slug"])):
            lines.append(f"- {ext_by_id[r['extender_a']]['slug']} = "
                         f"{ext_by_id[r['extender_b']]['slug']}: {r.get('evidence', '')}")
    if by_kind.get("conflicting"):
        lines += ["", "### Conflicting pairs", ""]
        for r in by_kind["conflicting"]:
            lines.append(f"- {ext_by_id[r['extender_a']]['slug']} x "
                         f"{ext_by_id[r['extender_b']]['slug']}: {r.get('evidence', '')}")

    dirs = [r for r in rels if r["kind"] in DIRECTED_KINDS]
    lines += ["", "### Directed hand-off links (composition-planner substrate, EDB-22)", ""]
    for r in sorted(dirs, key=lambda r: (ext_by_id[r["extender_a"]]["slug"], r["kind"],
                                          ext_by_id[r["extender_b"]]["slug"])):
        arrow = "->" if r["kind"] == "precedes" else "=>"
        lines.append(f"- {ext_by_id[r['extender_a']]['slug']} {arrow} "
                     f"{ext_by_id[r['extender_b']]['slug']} ({r['kind']})")
    lines.append("")

    n_gap = sum(1 for c in cov_by_job.values() if c.get("status") == "gap")
    n_part = sum(1 for c in cov_by_job.values() if c.get("status") == "partial")
    return lines, {"n_jobs": len(jobs), "n_gap": n_gap, "n_part": n_part, "n_rels": len(rels)}


# --- analysis.md sections --------------------------------------------------------------

def build_extender_profiles(data):
    """slug, kind, jobs served (present/partial counts), relationship degree."""
    fw = data["fw_by_slug"].get(FRAMEWORK_SLUG)
    fw_id = fw["id"] if fw else None
    served_present = defaultdict(set)
    served_partial = defaultdict(set)
    for a in data["assessments"]:
        if a["framework"] == fw_id and a["assessor"] == ASSESSOR:
            if a["verdict"] == "present":
                served_present[a["extender"]].add(a["element"])
            elif a["verdict"] == "partial":
                served_partial[a["extender"]].add(a["element"])
    degree = Counter()
    for r in data["relationships"]:
        degree[r["extender_a"]] += 1
        degree[r["extender_b"]] += 1
    rows = []
    for e in sorted(data["extenders"], key=lambda e: e["slug"]):
        rows.append({
            "slug": e["slug"],
            "kind": e["kind"],
            "present": len(served_present[e["id"]]),
            "partial": len(served_partial[e["id"]]),
            "degree": degree.get(e["id"], 0),
        })
    return rows


def build_relationship_listing(data):
    """duplicative/conflicting/directed pairs — kind, pair, evidence, resolved-or-open."""
    ext_by_id = data["ext_by_id"]
    rows = []
    for r in sorted(
        (r for r in data["relationships"] if r["kind"] in RESOLUTION_KINDS),
        key=lambda r: (r["kind"], ext_by_id[r["extender_a"]]["slug"], ext_by_id[r["extender_b"]]["slug"]),
    ):
        evidence = r.get("evidence", "")
        rows.append({
            "kind": r["kind"],
            "a": ext_by_id[r["extender_a"]]["slug"],
            "b": ext_by_id[r["extender_b"]]["slug"],
            "evidence": evidence,
            "status": "resolved" if "RESOLVED" in evidence else "open",
        })
    return rows


def build_assessor_comparison(data):
    """Per extender: mechanical-v1 dimension verdicts vs judged-v1/coverage-v1 verdicts,
    each as a present/partial/absent triple; "—" where the assessor never assessed that
    extender at all (distinct from an all-absent triple)."""
    counts = {a: defaultdict(Counter) for a in COMPARISON_ASSESSORS}
    for a in data["assessments"]:
        if a["assessor"] in counts:
            counts[a["assessor"]][a["extender"]][a["verdict"]] += 1
    rows = []
    for e in sorted(data["extenders"], key=lambda e: e["slug"]):
        row = {"slug": e["slug"], "kind": e["kind"]}
        for assessor in COMPARISON_ASSESSORS:
            c = counts[assessor].get(e["id"])
            row[assessor] = (
                "—" if not c
                else f"{c.get('present', 0)}/{c.get('partial', 0)}/{c.get('absent', 0)}"
            )
        rows.append(row)
    return rows


def build_eval_run_index(data):
    """slug, kind, status, and rows linked to it across assessments/job_coverage/
    relationships (the three collections carrying an `eval_run` relation)."""
    linked_colls = ("assessments", "job_coverage", "relationships")
    counts = {coll: Counter(r["eval_run"] for r in data[coll] if r.get("eval_run"))
              for coll in linked_colls}
    rows = []
    for r in sorted(data["eval_runs"], key=lambda r: r["slug"]):
        per_coll = {coll: counts[coll].get(r["id"], 0) for coll in linked_colls}
        rows.append({
            "slug": r["slug"], "kind": r["kind"], "status": r["status"],
            **per_coll, "total": sum(per_coll.values()),
        })
    return rows


def render_analysis(data):
    lines = [
        "# Extender-DB analysis",
        "",
        "_Generated by `report.py` — do not hand-edit. Companion to `coverage-matrix.md`;",
        "covers the DB's other cross-cutting answers: per-extender profiles, "
        "duplicative/conflicting/directed relationships, an assessor comparison, and the",
        "eval-runs provenance index._",
        "",
        projection_scope(data),
        "",
        "## Extender profiles",
        "",
        "| Extender | Kind | Jobs present | Jobs partial | Relationship degree |",
        "|---|---|---|---|---|",
    ]
    for row in build_extender_profiles(data):
        lines.append("| `{slug}` | {kind} | {present} | {partial} | {degree} |".format(**row))

    lines += [
        "",
        "## Duplicative, conflicting, and directed relationships",
        "",
        "_Pairs that need a resolution (`duplicative`/`conflicting`) or carry an ordering",
        "decision (`precedes`/`feeds-into`, the composition-planner substrate, EDB-22)._",
        "`complementary` pairs are informational and excluded — see the kind-count table",
        "in `coverage-matrix.md`.",
        "",
        "| Kind | A | B | Status | Evidence |",
        "|---|---|---|---|---|",
    ]
    for row in build_relationship_listing(data):
        lines.append("| {kind} | `{a}` | `{b}` | {status} | {evidence} |".format(**row))

    lines += [
        "",
        "## Assessor comparison",
        "",
        "_Present/partial/absent verdict counts per extender, per assessor. `—` = the",
        "assessor never assessed that extender (not the same as an all-absent triple)._",
        "",
        "| Extender | Kind | mechanical-v1 (P/Pa/Ab) | judged-v1 (P/Pa/Ab) | "
        "coverage-v1 (P/Pa/Ab) |",
        "|---|---|---|---|---|",
    ]
    for row in build_assessor_comparison(data):
        lines.append("| `{}` | {} | {} | {} | {} |".format(
            row["slug"], row["kind"], row[MECHANICAL_ASSESSOR],
            row[JUDGED_ASSESSOR], row[ASSESSOR]))

    lines += [
        "",
        "## Eval-run provenance index",
        "",
        "| Slug | Kind | Status | assessments | job_coverage | relationships | Total |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in build_eval_run_index(data):
        lines.append("| `{slug}` | {kind} | {status} | {assessments} | {job_coverage} | "
                      "{relationships} | {total} |".format(**row))
    lines.append("")
    return lines


# --- CLI ---------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Render every extender-DB analysis doc (coverage-matrix.md, "
                     "analysis.md) from one data pass. Supersedes render_matrix.py."
    )
    ap.add_argument("--fixtures",
                     help="read <dir>/<collection>.json dumps instead of the live DB "
                          "(dev/test mode; no PB credentials needed)")
    ap.add_argument("--out",
                     help="directory to write coverage-matrix.md/analysis.md into "
                          "(default: next to this script, i.e. evals/)")
    args = ap.parse_args()

    src = FixtureSource(args.fixtures) if args.fixtures else PB()
    data = load(src)

    out_dir = args.out or HERE
    os.makedirs(out_dir, exist_ok=True)

    matrix_lines, stats = render_coverage_matrix(data)
    matrix_path = os.path.join(out_dir, "coverage-matrix.md")
    with open(matrix_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(matrix_lines))
    print(f"wrote {matrix_path}: {stats['n_jobs']} jobs ({stats['n_gap']} gap, "
          f"{stats['n_part']} partial), {stats['n_rels']} relationships")

    analysis_lines = render_analysis(data)
    analysis_path = os.path.join(out_dir, "analysis.md")
    with open(analysis_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(analysis_lines))
    print(f"wrote {analysis_path}: {len(data['extenders'])} extenders, "
          f"{len(data['eval_runs'])} eval_runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
