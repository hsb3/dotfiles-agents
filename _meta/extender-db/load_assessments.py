"""Load judged assessment JSON (produced by W1 judge/reviewer agents) into the DB,
and compare two verdict sets for the adversarial agreement gate.

Session-run only — agents produce JSON files, never DB writes (PLAN.md W1 architecture).

    python3 load_assessments.py load --assessor judged-v1 judge-*.json
    python3 load_assessments.py compare --left judge-*.json --right reviewer-*.json

Input JSON shape (see scratchpad JUDGING-CRITERIA.md): {"skills": [{"slug", "archetypes":
{"primary", "secondary": [], "evidence"}, "sections": {"<slug>": {"verdict", "evidence"}}}]}

Mapping into the assessments collection:
  hsb3-skill-archetypes:  primary -> present, secondary -> partial, all others -> absent
  skill-section-taxonomy: verdict written as-is (present | partial | absent)
"""

import argparse
import glob
import json
import sys

from pb import PB, esc

ARCHETYPE_FW = "hsb3-skill-archetypes"
SECTION_FW = "skill-section-taxonomy"
VALID_VERDICTS = {"present", "partial", "absent"}


def load_inputs(patterns):
    skills = {}
    for pat in patterns:
        paths = glob.glob(pat) or [pat]
        for path in sorted(paths):
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            for s in data["skills"]:
                if s["slug"] in skills:
                    raise SystemExit(f"duplicate slug across inputs: {s['slug']} ({path})")
                skills[s["slug"]] = s
    return skills


def fetch_reference(pb):
    fws = {f["slug"]: f["id"] for f in pb.list_all("frameworks")}
    els = {}
    for e in pb.list_all("framework_elements"):
        els.setdefault(e["framework"], {})[e["slug"]] = e["id"]
    exts = {e["slug"]: e["id"] for e in pb.list_all("extenders", "kind='skill'")}
    return fws, els, exts


def validate(skills, arch_slugs, sect_slugs, ext_slugs):
    errs = []
    for slug, s in skills.items():
        if slug not in ext_slugs:
            errs.append(f"{slug}: not a skill extender in the DB")
            continue
        a = s["archetypes"]
        if a["primary"] not in arch_slugs:
            errs.append(f"{slug}: unknown primary archetype {a['primary']!r}")
        for sec in a.get("secondary", []):
            if sec not in arch_slugs:
                errs.append(f"{slug}: unknown secondary archetype {sec!r}")
            if sec == a["primary"]:
                errs.append(f"{slug}: primary repeated in secondary")
        missing = sect_slugs - set(s["sections"])
        unknown = set(s["sections"]) - sect_slugs
        if missing:
            errs.append(f"{slug}: missing sections {sorted(missing)}")
        if unknown:
            errs.append(f"{slug}: unknown sections {sorted(unknown)}")
        for k, v in s["sections"].items():
            if v["verdict"] not in VALID_VERDICTS:
                errs.append(f"{slug}: bad verdict {v['verdict']!r} for {k}")
    return errs


def cmd_load(args):
    pb = PB()
    skills = load_inputs(args.files)
    fws, els, exts = fetch_reference(pb)
    arch_els = els[fws[ARCHETYPE_FW]]
    sect_els = els[fws[SECTION_FW]]
    errs = validate(skills, set(arch_els), set(sect_els), set(exts))
    if errs:
        print("VALIDATION FAILED:\n  " + "\n  ".join(errs))
        return 1
    n = 0
    for slug, s in sorted(skills.items()):
        ext = exts[slug]
        a = s["archetypes"]
        for aslug, el_id in arch_els.items():
            if aslug == a["primary"]:
                verdict, evidence = "present", a.get("evidence", "")
            elif aslug in a.get("secondary", []):
                verdict, evidence = "partial", "secondary archetype"
            else:
                verdict, evidence = "absent", ""
            pb.upsert(
                "assessments",
                f"extender='{ext}' && framework='{fws[ARCHETYPE_FW]}' && element='{el_id}' && assessor='{esc(args.assessor)}'",
                {"extender": ext, "framework": fws[ARCHETYPE_FW], "element": el_id,
                 "verdict": verdict, "evidence": evidence, "assessor": args.assessor},
            )
            n += 1
        for sslug, el_id in sect_els.items():
            v = s["sections"][sslug]
            pb.upsert(
                "assessments",
                f"extender='{ext}' && framework='{fws[SECTION_FW]}' && element='{el_id}' && assessor='{esc(args.assessor)}'",
                {"extender": ext, "framework": fws[SECTION_FW], "element": el_id,
                 "verdict": v["verdict"], "evidence": v.get("evidence", ""),
                 "assessor": args.assessor},
            )
            n += 1
        print(f"loaded {slug}: primary={a['primary']}")
    print(f"{n} assessment rows upserted as assessor={args.assessor!r} "
          f"({len(skills)} skills)")
    return 0


def cmd_compare(args):
    left = load_inputs(args.left)
    right = load_inputs(args.right)
    overlap = sorted(set(left) & set(right))
    if not overlap:
        print("no overlapping skills")
        return 1
    prim_agree, sect_agree, sect_total = 0, 0, 0
    for slug in overlap:
        lp, rp = left[slug]["archetypes"]["primary"], right[slug]["archetypes"]["primary"]
        mark = "AGREE" if lp == rp else "DISAGREE"
        prim_agree += lp == rp
        print(f"{slug}: primary {mark}  left={lp} right={rp}")
        for k in sorted(left[slug]["sections"]):
            lv = left[slug]["sections"][k]["verdict"]
            rv = right[slug]["sections"].get(k, {}).get("verdict")
            sect_total += 1
            if lv == rv:
                sect_agree += 1
            else:
                print(f"    section {k}: left={lv} right={rv}")
    print(f"\nprimary-archetype agreement: {prim_agree}/{len(overlap)}")
    print(f"section-verdict agreement:   {sect_agree}/{sect_total} "
          f"({100 * sect_agree / sect_total:.0f}%)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_load = sub.add_parser("load")
    p_load.add_argument("--assessor", required=True)
    p_load.add_argument("files", nargs="+")
    p_cmp = sub.add_parser("compare")
    p_cmp.add_argument("--left", nargs="+", required=True)
    p_cmp.add_argument("--right", nargs="+", required=True)
    args = ap.parse_args()
    return cmd_load(args) if args.cmd == "load" else cmd_compare(args)


if __name__ == "__main__":
    sys.exit(main())
