#!/usr/bin/env python3
"""Vendored-drift gate — every `origin: vendored` base/ still matches its pinned ref.

`docs/vendoring-rule.md` gates the `origin: vendored` provenance class on four criteria and
a contract, and names this checker as the enforcement behind it: a vendored body is
subjected to a drift status of `up_to_date | behind | diverged | not_found`, and `diverged`
— upstream rewrote history at the ref, or our copy was hand-edited outside the compose
layer — is a loud failure. `scripts/check_provenance.py` proves only that the CONTRACT is
present (non-null `upstream`, non-null immutable `ref`, a LICENSE in the vendored dir).
Presence is not identity: nothing there ever contacts the upstream, so until this existed,
"a hand-edit in base/ fails the provenance gate" was asserted in two shipped skill READMEs
and enforced nowhere.

What this proves, per `origin: vendored` roster entry:

  1. The upstream is fetched at the entry's exact pinned `ref` and the subtree named by
     `externals.yaml` is compared, path by path, against `<source>/base` in the working tree.
  2. The comparison runs in BOTH directions — a path only we have (added) and a path only
     upstream has (removed) each count as drift, not just a content difference on a shared
     path. `base/` is verbatim or it is not.
  3. Status is reported per entry:
       up_to_date — base/ matches the pinned ref byte for byte, and the ref is upstream HEAD
       behind     — base/ matches the ref, but upstream has moved past it. NOT a failure:
                    the pin is deliberate, and this is the signal to consider bumping it.
       diverged   — base/ does NOT match the ref. Loud failure.
       not_found  — the upstream is reachable but the ref is gone (history rewritten, or the
                    repo/path removed). Failure: the rule says such an entry is reclassified
                    `disposition: orphaned` by a human, so the gate holds until one does.
       unreachable — the upstream could not be reached. Failure, but NOT evidence of drift:
                    nothing was compared, and a gate that cannot measure is red rather than
                    green (decision-016 point 4).

Which subtree to compare comes from `externals.yaml`, indexed by (upstream, ref) rather
than by id — the roster id and the externals id are NOT the same string in general; matching on the pin itself is exact where matching on a name is a guess.

Where it runs: a step in the `drift guards` CI job, NOT in `make ci`. Reaching the upstream
needs NETWORK and `make ci` is offline-and-zero-install by design; a job of its own was
equally unavailable because `dev`'s branch protection pins required checks by job NAME, so
adding one would strand every open PR on a check that never reports. Same placement, and
for the same two reasons, as `scripts/check_version_bump.py`.

Network contract — uniform across every CI-only gate here (decision-016 point 4): a gate
that cannot measure is red, never green, so an unreachable upstream exits 1 saying outright
that it is not evidence of drift. A reachable upstream missing the ref is a different
failure, and the message names which one was hit.

Deliberately NOT covered: whether the pin SHOULD move (`behind` is informational — bumping
a pin is a deliberate act, per the rule); file modes; anything outside `base/`; and the
authored layer composed on top, which is ours to edit freely and is the whole point of
vendoring rather than referencing.

Stdlib-only, deterministic. Exit 0 = up_to_date or behind; exit 1 = diverged, not_found, or
an upstream that could not be reached at all.
Usage: python3 scripts/check_vendored_drift.py   (run from anywhere)
"""

import hashlib
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from check_roster import parse_roster  # noqa: E402

# Noise `cp`/checkout produce but git never tracks — pruned from BOTH sides so it cannot
# masquerade as drift.
PRUNE_DIRS = {"__pycache__", ".git"}
PRUNE_FILES = {".DS_Store"}
PRUNE_SUFFIX = (".pyc", ".pyo")

GIT_TIMEOUT = 120


def _git(args, cwd=None):
    """Run git; return (returncode, stdout). Never raises on a non-zero exit."""
    try:
        p = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=GIT_TIMEOUT
        )
        return p.returncode, p.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        return 1, ""


def _externals_paths():
    """(upstream, ref) -> path within that upstream, from externals.yaml.

    Hand-parsed: stdlib has no YAML and zero-install is an invariant here. Only the four
    scalar keys this gate needs are read, from `  - id:`-anchored blocks.
    """
    fp = os.path.join(REPO, "externals.yaml")
    out, cur = {}, {}

    def flush(entry):
        up, ref, path = entry.get("upstream"), entry.get("ref"), entry.get("path")
        if up and ref:
            out[(up, ref)] = path or ""

    with open(fp, encoding="utf-8") as fh:
        for line in fh:
            if line.lstrip().startswith("#") or not line.strip():
                continue
            stripped = line.strip()
            if stripped.startswith("- id:"):
                flush(cur)
                cur = {}
                continue
            for key in ("upstream", "ref", "path"):
                if stripped.startswith(f"{key}:"):
                    cur[key] = stripped[len(key) + 1:].strip().strip('"').strip("'")
    flush(cur)
    return out


def _walk_hashes(root):
    """rel-path -> sha256 for every file under root, with untracked noise pruned."""
    hashes = {}
    if not os.path.isdir(root):
        return hashes
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in PRUNE_DIRS)
        for f in sorted(files):
            if f in PRUNE_FILES or f.endswith(PRUNE_SUFFIX):
                continue
            fp = os.path.join(dirpath, f)
            if os.path.islink(fp) and not os.path.exists(fp):
                continue
            try:
                with open(fp, "rb") as fh:
                    hashes[os.path.relpath(fp, root)] = hashlib.sha256(fh.read()).hexdigest()
            except OSError:
                hashes[os.path.relpath(fp, root)] = "<unreadable>"
    return hashes


def _fetch_at_ref(upstream, ref, dest):
    """Materialize `upstream` at exactly `ref` in dest. Returns 'ok' | 'no_ref' | 'no_net'."""
    rc, _ = _git(["init", "-q", dest])
    if rc != 0:
        return "no_net"
    _git(["remote", "add", "origin", upstream], cwd=dest)
    # Is the host reachable at all? Both branches fail; this only decides WHICH
    # failure is named, an unreachable host or a rewritten/removed ref.
    rc, _ = _git(["ls-remote", "--exit-code", "origin", "HEAD"], cwd=dest)
    if rc != 0:
        return "no_net"
    rc, _ = _git(["fetch", "-q", "--depth=1", "origin", ref], cwd=dest)
    if rc != 0:
        return "no_ref"
    rc, _ = _git(["checkout", "-q", "FETCH_HEAD"], cwd=dest)
    return "ok" if rc == 0 else "no_ref"


def _upstream_head(upstream, dest):
    rc, out = _git(["ls-remote", "origin", "HEAD"], cwd=dest)
    if rc != 0 or not out:
        return None
    return out.split()[0]


def drift_status(entry, ext_paths, tmproot):
    """(status, detail) for one roster entry."""
    eid = entry.get("id", "?")
    src = entry.get("source", "")
    upstream, ref = entry.get("upstream"), entry.get("ref")
    base = os.path.join(REPO, src, "base")

    if not os.path.isdir(base):
        return "diverged", f"[{eid}] no base/ dir at {src}/base — vendored content is missing"

    key = (upstream, ref)
    if key not in ext_paths:
        return ("not_found",
                f"[{eid}] no externals.yaml entry pins {upstream} @ {ref} — the subtree to "
                f"compare is unknown, so the vendoring is unverifiable")
    sub = ext_paths[key]

    dest = os.path.join(tmproot, eid)
    state = _fetch_at_ref(upstream, ref, dest)
    if state == "no_net":
        return ("unreachable",
                f"[{eid}] upstream unreachable ({upstream}) — NOT evidence of drift, but "
                f"nothing was compared, and a gate that could not measure is red rather "
                f"than green (decision-016 point 4). Re-run once the upstream answers")
    if state == "no_ref":
        return ("not_found",
                f"[{eid}] {upstream} is reachable but ref {ref} is gone (history rewritten, "
                f"or the repo/path removed) — reclassify `disposition: orphaned` per "
                f"docs/vendoring-rule.md, or re-pin")

    theirs_root = os.path.join(dest, sub) if sub else dest
    ours, theirs = _walk_hashes(base), _walk_hashes(theirs_root)

    added = sorted(set(ours) - set(theirs))
    removed = sorted(set(theirs) - set(ours))
    changed = sorted(p for p in set(ours) & set(theirs) if ours[p] != theirs[p])

    if added or removed or changed:
        bits = []
        if changed:
            bits.append(f"changed: {', '.join(changed[:5])}"
                        + (f", +{len(changed) - 5} more" if len(changed) > 5 else ""))
        if added:
            bits.append(f"only in ours: {', '.join(added[:5])}"
                        + (f", +{len(added) - 5} more" if len(added) > 5 else ""))
        if removed:
            bits.append(f"only upstream: {', '.join(removed[:5])}"
                        + (f", +{len(removed) - 5} more" if len(removed) > 5 else ""))
        return ("diverged",
                f"[{eid}] base/ does not match {upstream} @ {ref} — " + "; ".join(bits)
                + ". base/ is verbatim or it is not: re-vendor at the pin, or move the pin")

    head = _upstream_head(upstream, dest)
    if head and head != ref:
        return "behind", f"[{eid}] matches the pin; upstream HEAD has moved to {head[:12]}"
    return "up_to_date", f"[{eid}] matches {upstream} @ {ref[:12]}"


def main():
    roster = parse_roster(os.path.join(REPO, "primitives-core.yaml"))
    vendored = [e for e in roster if (e.get("origin") or "").strip() == "vendored"]
    if not vendored:
        print("✓ vendored-drift: no `origin: vendored` entries to check")
        return 0

    ext_paths = _externals_paths()
    failures, notices, clean = [], [], []

    with tempfile.TemporaryDirectory() as tmproot:
        for e in sorted(vendored, key=lambda x: x.get("id", "")):
            status, detail = drift_status(e, ext_paths, tmproot)
            if status in ("diverged", "not_found", "unreachable"):
                failures.append(f"{status}: {detail}")
            elif status == "behind":
                notices.append(f"{status}: {detail}")
            else:
                clean.append(detail)

    for n in notices:
        print(f"  ℹ {n}")
    if failures:
        print(f"✗ vendored-drift: {len(failures)} failure(s)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"✓ vendored-drift clean — {len(clean) + len(notices)} vendored base(s) verified "
          f"against their pinned refs ({len(clean)} up_to_date, {len(notices)} behind)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
