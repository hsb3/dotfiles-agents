"""Load an evaluation run's provenance (campaign metadata, prompts, raw agent
responses) into eval_runs / eval_responses, and link existing assessment rows to it.

Session-run only, like load_assessments.py — agents produce artifacts, never DB writes.

    python3 load_eval_run.py manifest.json [manifest2.json ...]

Manifest shape (paths are resolved relative to the manifest file):
{
  "run": {
    "slug": "w1-judged-2026-07-20",
    "kind": "judged",                     # mechanical | judged | adversarial-review |
                                          # adjudication | comparative | experiment
    "method": "how the run was designed and executed",
    "criteria_file": "JUDGING-CRITERIA.md",   # or inline "criteria_text"
    "frameworks": ["hsb3-skill-archetypes"],  # slugs
    "status": "complete",
    "notes": ""
  },
  "responses": [
    {
      "role": "judge-1",                  # unique within the run
      "agent_type": "foreman-kit:builder",
      "model": "sonnet",
      "prompt": "...",                    # or "prompt_file"
      "response_text": "final message",   # or "response_text_file"
      "response_json_file": "judge-1.json",   # or inline "response_json"
      "extenders": ["handoff", "foreman"],    # slugs covered
      "tokens": 65840, "duration_ms": 174422
    }
  ],
  "link_assessor": "judged-v1"            # optional: stamp eval_run on those rows
}
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pb import PB, esc  # noqa: E402


def _read(base, spec, inline_key, file_key):
    if inline_key in spec:
        return spec[inline_key]
    if file_key in spec:
        with open(os.path.join(base, spec[file_key]), encoding="utf-8") as fh:
            return fh.read()
    return ""


def load_manifest(pb, path):
    base = os.path.dirname(os.path.abspath(path))
    with open(path, encoding="utf-8") as fh:
        m = json.load(fh)
    fw_ids = {f["slug"]: f["id"] for f in pb.list_all("frameworks")}
    all_ext = {e["slug"]: e for e in pb.list_all("extenders")}
    ext_ids = {s: e["id"] for s, e in all_ext.items() if not e.get("retired")}

    # Resolve every response's extenders before the first write: failing inside the loop
    # below would leave an eval_runs row with no responses, which a re-run then reuses.
    unresolved = sorted({
        f"{s} ({'retired' if s in all_ext else 'no such extender'})"
        for resp in m.get("responses", [])
        for s in resp.get("extenders", []) if s not in ext_ids
    })
    if unresolved:
        raise SystemExit(f"{path}: cannot link response extenders: {', '.join(unresolved)}")

    r = m["run"]
    run, created = pb.upsert("eval_runs", f"slug='{esc(r['slug'])}'", {
        "slug": r["slug"],
        "kind": r["kind"],
        "method": r.get("method", ""),
        "criteria_text": _read(base, r, "criteria_text", "criteria_file"),
        "frameworks": [fw_ids[s] for s in r.get("frameworks", [])],
        "status": r.get("status", "complete"),
        "notes": r.get("notes", ""),
    })
    print(f"run {'created' if created else 'updated'}: {r['slug']}")

    for resp in m.get("responses", []):
        rj = resp.get("response_json")
        if rj is None and "response_json_file" in resp:
            with open(os.path.join(base, resp["response_json_file"]), encoding="utf-8") as fh:
                rj = json.load(fh)
        pb.upsert("eval_responses",
                  f"run='{run['id']}' && role='{esc(resp['role'])}'", {
                      "run": run["id"],
                      "role": resp["role"],
                      "agent_type": resp.get("agent_type", ""),
                      "model": resp.get("model", ""),
                      "prompt": _read(base, resp, "prompt", "prompt_file"),
                      "response_text": _read(base, resp, "response_text", "response_text_file"),
                      "response_json": rj if rj is not None else {},
                      "extenders": [ext_ids[s] for s in resp.get("extenders", [])],
                      "tokens": resp.get("tokens", 0),
                      "duration_ms": resp.get("duration_ms", 0),
                  })
        print(f"  response: {resp['role']}")

    assessor = m.get("link_assessor")
    if assessor:
        n = 0
        for a in pb.list_all("assessments", f"assessor='{esc(assessor)}'"):
            if a.get("eval_run") != run["id"]:
                pb.update("assessments", a["id"], {"eval_run": run["id"]})
                n += 1
        print(f"  linked {n} assessment rows (assessor={assessor})")


def main():
    pb = PB()
    for path in sys.argv[1:]:
        load_manifest(pb, path)


if __name__ == "__main__":
    main()
