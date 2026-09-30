#!/usr/bin/env python3
"""Grant authenticated read access to the agreed toolbox collections.

Dry-run is the default. Pass --apply only after reviewing the reported names.
"""

import argparse

from pb import PB


AUTH_RULE = "@request.auth.id != ''"
COLLECTIONS = (
    "frameworks", "sources", "extenders", "framework_elements", "files",
    "distributions", "eval_runs", "eval_responses", "assessments",
    "job_coverage", "run_events", "tool_calls",
)
READ_RULES = ("listRule", "viewRule")


def set_authenticated_read(pb, apply=False):
    """Return (changed, noop) collection names after validating every target."""
    patches = []
    for name in COLLECTIONS:
        collection = pb.get_collection(name)
        if collection is None:
            raise ValueError(f"{name}: collection not found")
        patch = {}
        for rule in READ_RULES:
            value = collection.get(rule)
            if value not in (None, AUTH_RULE):
                raise ValueError(f"{name}.{rule}: unexpected rule {value!r}")
            if value is None:
                patch[rule] = AUTH_RULE
        if patch:
            patches.append((name, patch))
    changed = tuple(name for name, _ in patches)
    noop = tuple(name for name in COLLECTIONS if name not in changed)
    if apply:
        for name, patch in patches:
            pb.update_collection(name, patch)
    return changed, noop


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the validated read rules")
    args = parser.parse_args(argv)
    changed, noop = set_authenticated_read(PB(), apply=args.apply)
    print("changed=" + ",".join(changed))
    print("noop=" + ",".join(noop))


if __name__ == "__main__":
    main()
