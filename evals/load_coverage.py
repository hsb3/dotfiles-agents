"""Load a judged extender->job coverage mapping JSON into `assessments`, keyed on the
full cross product of every extender in the DB x every element of the
`hsb3-jobs-to-be-done` framework (W9 M1, PLAN.md "Execution architecture" step 1).

Session-run only, like load_assessments.py / load_eval_run.py — judge agents produce
JSON and never touch the DB; credentials stay with the session.

    python3 load_coverage.py mapping.json [--dry-run]

Input JSON shape (produced by W9 M1 judge agents from their extender-by-extender read):
{
  "eval_run": "<eval_runs record id>",           # from load_eval_run.py's `run["id"]`
  "mappings": [
    {
      "extender": "<extender slug or name, as stored in extenders>",
      "jobless": false,                          # true => every job below is dropped;
                                                   # all 24 rows are written absent
      "jobs": [
        {"element": "<job element slug or name, as stored in framework_elements>",
         "verdict": "present|partial",            # absent is NEVER listed explicitly —
                                                    # it is the default for every job not
                                                    # named here
         "evidence": "<quote from the extender's body>"}
      ]
    }
  ]
}

Every extender in the DB must appear in `mappings` exactly once (missing/extra is a
validation error); every job element not listed for an extender is written as an
`absent` assessment row with empty evidence. All rows are stamped
`assessor=coverage-v1` and linked to the given `eval_run`.

Scoped delta mode (`--extenders slug1,slug2`, EDB-26): restricts a pass to exactly the
named extenders — `mappings` must equal that set, not the full DB roster, and only
their rows are built/written; other extenders' rows (including their `eval_run` stamp)
are never touched. Fixes the delta-loader provenance bug: an unscoped delta input still
carries every unchanged extender verbatim, and loading it relinks ALL those carried
rows' `eval_run` to the new run (see PROCEDURES.md's ordering gotchas). Default
(`--extenders` omitted) is unchanged byte-for-byte.

Key Functions:
    validate_shape(): pure input-shape checks (malformed types, bad verdict, duplicate
        extender/element strings, jobless/jobs conflict) — run BEFORE any DB call, so a
        structurally bad file fails without needing the server up.
    validate_against_db(): DB-dependent checks (extender/element/eval_run existence;
        full roster coverage, or exactly `scope` if given) — run after validate_shape().
    build_rows(): expands the mapping into the cross product (all extenders, or just
        `scope`) x 24 job elements.
    plan_and_apply(): diffs the cross product against existing coverage-v1 rows
        (create/update/unchanged) and, unless --dry-run, writes it.

Limitations:
    - "extender"/"element" values in the input may be either the DB `slug` or `name`
      field; the first record seen wins on a collision (none expected at this scale;
      `--extenders` values resolve the same way).
    - Idempotency is judged on (verdict, evidence, eval_run, assessor); `score` is left
      untouched (not part of this brief).
"""

import argparse
import json
import sys

from pb import PB, esc

FRAMEWORK_SLUG = "hsb3-jobs-to-be-done"
ASSESSOR = "coverage-v1"
INPUT_VERDICTS = {"present", "partial"}
ABSENT = "absent"


# --- tier 1: pure input-shape validation, no DB --------------------------------------

def validate_shape(data: object) -> list[str]:
    """Structural checks only — safe to run with no network access."""
    if not isinstance(data, dict):
        return ["top level must be a JSON object"]
    errs: list[str] = []
    eval_run = data.get("eval_run")
    if not isinstance(eval_run, str) or not eval_run:
        errs.append("missing or invalid 'eval_run' (expected a non-empty string record id)")
    mappings = data.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        errs.append("missing or invalid 'mappings' (expected a non-empty list)")
        return errs
    seen_extenders: dict[str, int] = {}
    for i, m in enumerate(mappings):
        where = f"mappings[{i}]"
        if not isinstance(m, dict):
            errs.append(f"{where}: must be an object")
            continue
        ext = m.get("extender")
        if not isinstance(ext, str) or not ext:
            errs.append(f"{where}: missing or invalid 'extender'")
        elif ext in seen_extenders:
            errs.append(
                f"duplicate extender in input: {ext!r} "
                f"(mappings[{seen_extenders[ext]}] and {where})"
            )
        else:
            seen_extenders[ext] = i
        jobless = m.get("jobless", False)
        if not isinstance(jobless, bool):
            errs.append(f"{where}: 'jobless' must be a boolean")
        jobs = m.get("jobs", [])
        if not isinstance(jobs, list):
            errs.append(f"{where}: 'jobs' must be a list")
            jobs = []
        if jobless and jobs:
            errs.append(
                f"{where} ({ext!r}): 'jobless' is true but 'jobs' is non-empty — ambiguous"
            )
        errs.extend(_validate_jobs_shape(jobs, where, ext))
    return errs


def _validate_jobs_shape(jobs: list, where: str, ext: object) -> list[str]:
    errs: list[str] = []
    seen_elements: dict[str, int] = {}
    for j, job in enumerate(jobs):
        jwhere = f"{where}.jobs[{j}]"
        if not isinstance(job, dict):
            errs.append(f"{jwhere}: must be an object")
            continue
        el = job.get("element")
        if not isinstance(el, str) or not el:
            errs.append(f"{jwhere}: missing or invalid 'element'")
        elif el in seen_elements:
            errs.append(f"{where} ({ext!r}): duplicate element in jobs list: {el!r}")
        else:
            seen_elements[el] = j
        verdict = job.get("verdict")
        if verdict not in INPUT_VERDICTS:
            errs.append(
                f"{jwhere}: bad verdict {verdict!r} (must be one of {sorted(INPUT_VERDICTS)})"
            )
        if "evidence" in job and not isinstance(job["evidence"], str):
            errs.append(f"{jwhere}: 'evidence' must be a string")
    return errs


# --- tier 2: DB-dependent validation ---------------------------------------------------

def fetch_reference(pb: PB) -> tuple[str, list[dict], list[dict]]:
    fws = {f["slug"]: f["id"] for f in pb.list_all("frameworks")}
    if FRAMEWORK_SLUG not in fws:
        raise SystemExit(f"framework not found in DB: {FRAMEWORK_SLUG!r}")
    fw_id = fws[FRAMEWORK_SLUG]
    elements = [e for e in pb.list_all("framework_elements") if e["framework"] == fw_id]
    extenders = pb.list_all("extenders")
    return fw_id, elements, extenders


def build_lookup(records: list[dict]) -> dict[str, str]:
    """Map both `slug` and `name` to id; first record seen wins on a collision."""
    lookup: dict[str, str] = {}
    for r in records:
        for alias in (r.get("slug"), r.get("name")):
            if alias and alias not in lookup:
                lookup[alias] = r["id"]
    return lookup


def validate_against_db(
    pb: PB, data: dict, elements: list[dict], extenders: list[dict],
    scope: list[str] | None = None,
) -> list[str]:
    """`scope`, if given (raw `--extenders` slugs/names), requires `mappings` contain
    EXACTLY that set instead of the full DB roster — missing AND extra are both errors."""
    errs: list[str] = []
    el_lookup = build_lookup(elements)
    ext_lookup = build_lookup(extenders)
    ext_slug_by_id = {e["id"]: e["slug"] for e in extenders}
    resolved: dict[str, int] = {}
    for i, m in enumerate(data["mappings"]):
        ext_name = m.get("extender")
        ext_id = ext_lookup.get(ext_name)
        if ext_id is None:
            errs.append(f"mappings[{i}]: unknown extender {ext_name!r} (not in DB)")
            continue
        if ext_id in resolved:
            errs.append(
                f"mappings[{i}]: extender {ext_name!r} resolves to the same DB extender "
                f"as mappings[{resolved[ext_id]}] ({ext_slug_by_id[ext_id]!r})"
            )
            continue
        resolved[ext_id] = i
        for j, job in enumerate(m.get("jobs", [])):
            el_name = job.get("element")
            if el_lookup.get(el_name) is None:
                errs.append(
                    f"mappings[{i}].jobs[{j}] ({ext_name!r}): unknown job element "
                    f"{el_name!r} (not in {FRAMEWORK_SLUG})"
                )
    if scope is None:
        target_ids = {e["id"] for e in extenders}
        label = "DB extenders"
    else:
        target_ids = set()
        for s in scope:
            eid = ext_lookup.get(s)
            if eid is None:
                errs.append(f"--extenders: unknown extender {s!r} (not in DB)")
            else:
                target_ids.add(eid)
        label = "--extenders scope"
    missing = target_ids - set(resolved)
    if missing:
        missing_slugs = sorted(ext_slug_by_id[i] for i in missing)
        errs.append(f"{len(missing)} {label} missing from input: {missing_slugs}")
    if scope is not None:
        extra = set(resolved) - target_ids
        if extra:
            extra_slugs = sorted(ext_slug_by_id[i] for i in extra)
            errs.append(
                f"{len(extra)} extenders in input outside --extenders scope: {extra_slugs}"
            )
    eval_run_id = data.get("eval_run")
    if eval_run_id and pb.find_first("eval_runs", f"id='{esc(eval_run_id)}'") is None:
        errs.append(f"eval_run not found in DB: {eval_run_id!r}")
    return errs


# --- cross product + diff/write ---------------------------------------------------------

def build_rows(
    data: dict, fw_id: str, elements: list[dict], extenders: list[dict],
    scope: list[str] | None = None,
) -> list[dict]:
    """Expand the mapping into one row per (extender, job element) — the full cross
    product, or just `scope`'s extenders if given (so plan_and_apply() never sees,
    diffs, or re-stamps rows outside scope). Unlisted jobs (or all, if `jobless`)
    default to verdict=absent."""
    el_lookup = build_lookup(elements)
    ext_lookup = build_lookup(extenders)
    elements_sorted = sorted(elements, key=lambda e: e["slug"])
    extenders_sorted = sorted(extenders, key=lambda e: e["slug"])
    if scope is not None:
        scope_ids = {ext_lookup[s] for s in scope}
        extenders_sorted = [e for e in extenders_sorted if e["id"] in scope_ids]
    mapping_by_ext_id = {ext_lookup[m["extender"]]: m for m in data["mappings"]}

    rows = []
    for ext in extenders_sorted:
        m = mapping_by_ext_id[ext["id"]]
        jobs_by_el_id = {}
        if not m.get("jobless", False):
            for job in m.get("jobs", []):
                jobs_by_el_id[el_lookup[job["element"]]] = job
        for el in elements_sorted:
            job = jobs_by_el_id.get(el["id"])
            verdict = job["verdict"] if job else ABSENT
            evidence = job.get("evidence", "") if job else ""
            rows.append({
                "extender": ext["id"], "extender_slug": ext["slug"],
                "framework": fw_id,
                "element": el["id"], "element_slug": el["slug"],
                "verdict": verdict, "evidence": evidence,
            })
    return rows


def plan_and_apply(pb: PB, rows: list[dict], eval_run_id: str, dry_run: bool) -> tuple[int, int, int]:
    """Diff `rows` against existing coverage-v1 assessments; write unless dry_run.
    Returns (n_create, n_update, n_unchanged)."""
    fw_id = rows[0]["framework"]
    existing = {
        (a["extender"], a["element"]): a
        for a in pb.list_all("assessments", f"framework='{esc(fw_id)}' && assessor='{esc(ASSESSOR)}'")
    }
    n_create = n_update = n_unchanged = 0
    for row in rows:
        key = (row["extender"], row["element"])
        rec = existing.get(key)
        body = {
            "extender": row["extender"], "framework": row["framework"], "element": row["element"],
            "eval_run": eval_run_id, "verdict": row["verdict"], "evidence": row["evidence"],
            "assessor": ASSESSOR,
        }
        if rec is None:
            n_create += 1
            if not dry_run:
                pb.create("assessments", body)
        else:
            changed = (
                rec.get("verdict") != body["verdict"]
                or rec.get("evidence", "") != body["evidence"]
                or rec.get("eval_run") != body["eval_run"]
                or rec.get("assessor") != body["assessor"]
            )
            if changed:
                n_update += 1
                if not dry_run:
                    pb.update("assessments", rec["id"], body)
            else:
                n_unchanged += 1
    return n_create, n_update, n_unchanged


# --- CLI ---------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Load a judged extender->job coverage mapping into `assessments` "
                     "(assessor=coverage-v1), keyed on the full extender x job-element "
                     "cross product."
    )
    ap.add_argument("input", help="path to the mapping JSON (see module docstring for shape)")
    ap.add_argument("--dry-run", action="store_true",
                     help="validate and print the plan (create/update/unchanged counts); "
                          "make no writes")
    ap.add_argument(
        "--extenders",
        help="comma-separated extender slugs/names: restrict this pass to EXACTLY these "
             "extenders (EDB-26 scoped delta mode) — 'mappings' must match this set "
             "exactly, and only their rows are written/relinked; every other extender's "
             "rows are left untouched. Omitted: unchanged full-roster mode.",
    )
    args = ap.parse_args()

    try:
        with open(args.input, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as e:
        print(f"cannot read input file: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"malformed JSON in {args.input}: {e}")
        return 1

    shape_errs = validate_shape(data)
    if shape_errs:
        print("VALIDATION FAILED (input shape):\n  " + "\n  ".join(shape_errs))
        return 1

    scope = None
    if args.extenders:
        scope = [s.strip() for s in args.extenders.split(",") if s.strip()]

    pb = PB()
    fw_id, elements, extenders = fetch_reference(pb)
    db_errs = validate_against_db(pb, data, elements, extenders, scope)
    if db_errs:
        print("VALIDATION FAILED (against DB):\n  " + "\n  ".join(db_errs))
        return 1

    rows = build_rows(data, fw_id, elements, extenders, scope)
    n_create, n_update, n_unchanged = plan_and_apply(pb, rows, data["eval_run"], args.dry_run)
    scope_note = f" (scoped to {len(scope)} extenders)" if scope else ""
    if args.dry_run:
        print(f"[dry-run] plan for {len(rows)} assessment rows{scope_note}: "
              f"{n_create} create, {n_update} update, {n_unchanged} unchanged; no writes made")
    else:
        print(f"upserted {len(rows)} assessment rows{scope_note} as assessor={ASSESSOR!r} "
              f"({n_create} created, {n_update} updated, {n_unchanged} unchanged), "
              f"linked to eval_run={data['eval_run']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
