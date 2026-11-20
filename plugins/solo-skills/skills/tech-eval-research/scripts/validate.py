#!/usr/bin/env -S uv run --quiet --python >=3.11 --with jsonschema --with pyyaml python
"""Validate every artifact against its schema and cross-check ids.

Run: scripts/validate.py [--root PATH]
Exit: 0 ok, 1 schema or reference findings, 2 usage, config, missing file or parse error.
"""
import sys

import evalkit
from evalkit import ConfigError, EvalError, ReferenceMismatch, SchemaViolation


def validate(p: evalkit.Project) -> list[EvalError]:
    """All findings for the project; raises EvalError when a required spec or schema is unusable."""
    # Imported here, after argument parsing, so --help needs no third-party package.
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError

    errors: list[EvalError] = []
    validators = {}

    def validator(schema):
        if schema not in validators:
            path = p.schemas / f"{schema}.schema.yaml"
            doc = p.yaml(path)
            try:
                Draft202012Validator.check_schema(doc)
            except SchemaError as e:
                raise ConfigError(p.rel(path), f"not a valid JSON Schema: {e.message}") from None
            validators[schema] = Draft202012Validator(doc, format_checker=FormatChecker())
        return validators[schema]

    def check(inst, schema, shown, at=""):
        """Record schema violations; True when inst matches, so cross-checks may index it safely."""
        found = sorted(validator(schema).iter_errors(inst), key=lambda e: [str(x) for x in e.absolute_path])
        for e in found:
            errors.append(SchemaViolation(shown, e.message, at + ("/".join(map(str, e.absolute_path)) or "<root>")))
        return not found

    def ref(shown, where, message):
        errors.append(ReferenceMismatch(shown, message, where))

    def ids(items, shown, where, key="id"):
        seen = set()
        for x in items:
            if x[key] in seen:
                ref(shown, where, f"duplicate {key} {x[key]!r}")
            seen.add(x[key])
        return seen

    def same(got, want, shown, where, what):
        if got != want:
            ref(shown, where, f"answered {sorted(got)} != required {sorted(want)}" if what is None
                else f"keys != {what}; extra={sorted(got - want)} missing={sorted(want - got)}")

    for schema in ("requirements", "eval-rubric", "findings", "runs"):  # landscape only when used
        validator(schema)
    req_path, rub_path, land_path = (p.spec / n for n in ("requirements.yaml", "eval-rubric.yaml", "landscape.yaml"))
    req_at, rub_at = p.rel(req_path), p.rel(rub_path)
    req, rub = p.yaml(req_path), p.yaml(rub_path)
    spec_ok = check(req, "requirements", req_at) & check(rub, "eval-rubric", rub_at)
    # Every cross-check below needs schema-valid specs; without them only schema checks run.
    if spec_ok:
        cap_ids = ids(req["capabilities"], req_at, "capabilities")
        bias_caps = cap_ids - {c["id"] for c in req["capabilities"] if c["required"] == "hard"}
        filter_ids = ids(req["hard_filters"], req_at, "hard_filters")
        bias_ids = ids(req["biases"], req_at, "biases")
        cand_kind = {c["id"]: c["kind"] for c in req["candidates"]}
        ids(req["candidates"], req_at, "candidates")
        proof_ids = ids(req["proofs"], req_at, "proofs")
        desired = {x["id"] for x in req["proofs"] if x["weight_class"] == "desired"}
        for i, pr in enumerate(req["proofs"]):
            if pr["baseline"] != "none" and cand_kind.get(pr["baseline"]) != "baseline":
                ref(req_at, f"proofs/{i}", f"baseline {pr['baseline']!r} is not a kind=baseline candidate")
        ids(rub["capability_verdicts"], rub_at, "capability_verdicts", key="verdict")
        weights = rub["ranking"]
        same(set(weights["capability_weights"]), bias_caps, rub_at, "ranking/capability_weights", "bias capabilities")
        same(set(weights["bias_weights"]), bias_ids, rub_at, "ranking/bias_weights", "biases")
        same(set(weights["proof_weights"]), desired, rub_at, "ranking/proof_weights", "desired proofs")

    if land_path.exists():
        try:
            land = p.yaml(land_path)
        except EvalError as e:
            errors.append(e)
        else:
            if check(land, "landscape", p.rel(land_path)) and spec_ok:
                for i, e in enumerate(land["entries"]):
                    for c in e.get("candidates", []):
                        if c not in cand_kind:
                            ref(p.rel(land_path), f"entries/{i}", f"unknown candidate {c!r}")

    # Findings: ids resolve to the requirements; in-layer findings answer every filter and capability.
    for fp in p.findings_files():
        at = p.rel(fp)
        try:
            f = p.yaml(fp)
        except EvalError as e:
            errors.append(e)
            continue
        if not check(f, "findings", at) or not spec_ok:
            continue
        if f["candidate"] not in cand_kind:
            ref(at, "candidate", f"{f['candidate']!r} not in requirements candidates")
            continue
        if fp.stem != f["candidate"]:
            ref(at, "candidate", f"filename should be {f['candidate']}.yaml")
        if f["kind"] != cand_kind[f["candidate"]]:
            ref(at, "kind", f"{f['kind']!r} disagrees with requirements ({cand_kind[f['candidate']]!r})")
        if f["layer_fit"]["verdict"] == "in-layer":
            if f["kind"] == "candidate":
                same(ids(f["filters"], at, "filters"), filter_ids, at, "filters", None)
            same(ids(f["capabilities"], at, "capabilities"), cap_ids, at, "capabilities", None)
            same(ids(f.get("biases", []), at, "biases"), bias_ids, at, "biases", None)
            got = ids(f.get("proofs", []), at, "proofs")
            if got - proof_ids:
                ref(at, "proofs", f"unknown proof ids {sorted(got - proof_ids)}")
            # shortcut: proofs land concurrently, so a partial set is valid; the report task checks completeness
        ids(f.get("maturity", {}).get("signals", []), at, "maturity/signals")
        for i, vr in enumerate(f.get("verification", [])):
            if vr["outcome"] == "refuted" and not vr.get("correction"):
                ref(at, f"verification/{i}", f"refuted claim without correction: {vr['claim']!r}")

    for rp in p.runs_files():
        at = p.rel(rp)
        try:
            records = p.jsonl(rp)
        except EvalError as e:
            errors.append(e)
            continue
        for n, rec in records:
            if not check(rec, "runs", at, f"{n}:") or not spec_ok:
                continue
            if rec["proof"] not in proof_ids:
                ref(at, n, f"unknown proof {rec['proof']!r}")
            if rec["candidate"] not in cand_kind.keys() | {"none"}:
                ref(at, n, f"unknown candidate {rec['candidate']!r}")
            for a in rec["artifacts"]:
                if not p.artifact_exists(a):
                    ref(at, n, f"artifact missing: {a}")
    return errors


def main(argv=None) -> int:
    def body(p):
        errors = validate(p)
        if not errors:
            print("ok")
        return errors

    return evalkit.run(body, __doc__, argv)


if __name__ == "__main__":
    sys.exit(main())
