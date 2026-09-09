#!/usr/bin/env python3
"""Model-tier gate — the tier map resolves to REAL models, and no agent names one directly.

Agents declare a semantic dispatch tier (`light` / `mid` / `heavy`).
`primitives-core/hooks/_lib/model_catalog.json` is the only place a tier turns into a
concrete model id, so switching provider is one edit there rather than one per agent file.

Claude Code's agent frontmatter `model:` accepts only `sonnet` / `opus` / `haiku` /
`inherit` or a full model id, so each agent still carries a `model:` line — but that line
is a RENDERING of the map for this harness, not an authored choice. This gate re-renders it
from the tier and fails on any difference, which is what makes "no agent names a model"
true by derivation instead of by deletion.

Default mode is offline, and is a `make ci` gate:

  1. every tier's per-provider id exists in the projected catalog with a positive window
  2. the active provider has a mapping for EVERY tier — a missing one is red, naming the
     tier and the provider, because the runtime resolver answers None there and a hook
     that fails open must not be the only thing that notices
  3. every agent declares a `tier:` from the vocabulary
  4. every agent's `model:` equals its tier's Claude Code keyword
  5. no agent `model:` is a full model id (anything carrying a `/` or a digit — every
     harness keyword is a bare digit-free word)
  6. translation.yaml declares no second tier-to-id map (no `model_aliases` row with a
     `ref:` — the opencode generator resolves through the shared catalog instead)
  7. every projected entry — not just the pinned ones — carries a positive integer window,
     since `window_for` answers for any id a transcript names

The catalog is a PINNED, MINIMAL PROJECTION of `https://models.dev/api.json`: every model
with a positive integer token window, with that window and nothing else. It is vendored in-tree
because `make ci` is offline-and-zero-install by design, and an in-tree catalog is what
makes an invented id detectable with no network. The network half is the drift guard, the
same split `scripts/check_vendored_drift.py` already uses:

  --refresh   fetch upstream and rewrite the `providers` projection (hand-authored
              `tiers` and `active_provider` are never touched). This is the refresh path:
              run it when a provider ships a model, then re-pin the tier ids by hand.
  --drift     fetch and compare without writing; exits non-zero on a differing window, an
              id upstream no longer lists, an id upstream has that the projection does
              not, or an upstream that could not be reached at all — a gate that cannot
              measure is red, never green.

Neither network mode is in `make ci`. Run the comparison by hand:

    python3 scripts/check_model_tiers.py --drift     # needs network

WHAT EACH MODE CAN AND CANNOT CATCH. The offline mode checks a pinned id against the
PROJECTION, so it is circular by construction: pinning `claude-omniscient-42` AND adding
it to `providers` passes offline, green. That is inherent to an offline check and it is
accepted, not overlooked — but it means the two modes divide the error classes and
neither alone is sufficient:

  offline catches   an id absent from the projection; a non-positive or non-integer
                    window on any projected entry; a tier with no model for the active
                    provider; an agent whose `model:` no longer renders its declared tier;
                    an agent naming a model id; a second tier-to-id map in translation.yaml
  --drift catches   a FABRICATED projection entry (an id upstream never had); a STALE one
                    (a window upstream has since changed); a model retired upstream; and a
                    model upstream added that the projection is missing

So a hand-edited `providers` block is invisible to `make ci` and visible only to
`--drift`. Run `--drift` before trusting a projection you did not produce with `--refresh`.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = problems (prints every one).
Usage: python3 scripts/check_model_tiers.py [--refresh | --drift]
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "primitives-core", "hooks", "_lib"))

import model_tiers as MT  # noqa: E402
from check_roster import parse_translation, split_frontmatter  # noqa: E402

AGENTS = os.path.join(REPO, "primitives-core", "agents")
TRANSLATION = os.path.join(REPO, "translation.yaml")
UPSTREAM = "https://models.dev/api.json"
FETCH_TIMEOUT = 60

#: A `model:` value that names a model rather than a harness keyword. Every harness keyword
#: is a bare digit-free word (`sonnet` / `opus` / `haiku` / `inherit`) and every model id
#: carries a version number, so "a slash or a digit" is the whole rule — and it catches a
#: single-segment id like `claude-opus-5`, which a digit-DOTTED pattern misses.
FULL_MODEL_ID = re.compile(r"[/\d]")


def agent_fields(path):
    """The frontmatter keys this gate reads, as plain strings ('' when absent)."""
    with open(path, encoding="utf-8") as fh:
        fm, _ = split_frontmatter(fh.read())
    return {k: fm.get(k, "").strip() for k in ("name", "model", "tier")}


def agent_files(agents_dir):
    return [
        os.path.join(agents_dir, fn)
        for fn in sorted(os.listdir(agents_dir))
        if fn.endswith(".md") and fn.lower() != "readme.md"
    ]


def problems(catalog_path=None, agents_dir=None, translation_path=None):
    """Every offline check, as a flat list of messages. Empty list = clean."""
    agents_dir = agents_dir or AGENTS
    translation_path = translation_path or TRANSLATION
    try:
        catalog = MT.load(catalog_path)
    except ValueError as exc:
        return [str(exc)]

    found = []
    provider = MT.active_provider(catalog)
    projected = catalog["providers"]

    # EVERY projection entry, not just the pinned ones: `window_for` answers for any id a
    # transcript names, so a corrupted window on an unpinned model reaches a hook the same way.
    for prov, models in sorted(projected.items()):
        if not isinstance(models, dict):
            found.append(f"projected catalog for `{prov}` is not an object")
            continue
        for model_id, row in sorted(models.items()):
            context = row.get("context") if isinstance(row, dict) else None
            if not isinstance(context, int) or isinstance(context, bool) or context <= 0:
                found.append(
                    f"projected entry `{prov}/{model_id}` carries context window "
                    f"{context!r} — re-run --refresh")

    for tier in MT.tiers(catalog):
        for prov, model_id in sorted(catalog["tiers"][tier].get("models", {}).items()):
            if not isinstance(projected.get(prov, {}).get(model_id), dict):
                found.append(
                    f"tier `{tier}` pins `{prov}/{model_id}`, which the projected catalog "
                    f"for `{prov}` does not list — an invented or retired id")
        if MT.model_for(catalog, tier) is None:
            found.append(
                f"tier `{tier}` has no model for the active provider `{provider}` — the "
                "runtime resolver answers None there, so nothing downstream can dispatch it")
        if not MT.claude_code_keyword(catalog, tier):
            found.append(f"tier `{tier}` declares no `claude_code_keyword`")

    vocabulary = MT.tiers(catalog)
    for path in agent_files(agents_dir):
        rel = f"agents/{os.path.basename(path)}"
        fields = agent_fields(path)
        tier, model = fields["tier"], fields["model"]
        if not tier:
            found.append(
                f"[{rel}] declares no `tier:` — a dispatch tier is the declaration, the "
                f"`model:` line is only its rendering (vocabulary: {vocabulary})")
            continue
        if tier not in vocabulary:
            found.append(f"[{rel}] tier `{tier}` is not in the vocabulary {vocabulary}")
            continue
        if FULL_MODEL_ID.search(model):
            found.append(
                f"[{rel}] `model: {model}` names a model id directly — the map owns model "
                "ids; frontmatter carries the harness keyword its tier renders to")
            continue
        expected = MT.claude_code_keyword(catalog, tier)
        if model != expected:
            found.append(
                f"[{rel}] `model: {model}` does not render `tier: {tier}` — the map says "
                f"`{expected}`; change the tier, or the map, not this line")

    if os.path.isfile(translation_path):
        for row in parse_translation(translation_path)["model_aliases"]:
            if row.get("ref"):
                found.append(
                    f"translation.yaml: model_aliases row `{row.get('alias')}` carries "
                    f"`ref: {row['ref']}` — that is a second tier-to-id map; the alias "
                    "resolves through model_catalog.json")
    return found


def _fetch(url=UPSTREAM):
    """The upstream catalog as a dict. Raises OSError-family on an unreachable upstream.

    The explicit User-Agent is load-bearing: urllib's default is answered with 403.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "check-model-tiers/1"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def project(upstream, providers):
    """Project models with positive token windows; image-only models have none."""
    out = {}
    for prov in sorted(providers):
        models = (upstream.get(prov) or {}).get("models") or {}
        out[prov] = {
            mid: {"context": (models[mid].get("limit") or {}).get("context")}
            for mid in sorted(models)
            if type((context := (models[mid].get("limit") or {}).get("context"))) is int
            and context > 0
        }
    return out


def _providers(catalog):
    """Every provider the map or the projection mentions — pin an id, then refresh."""
    named = set(catalog["providers"])
    for row in catalog["tiers"].values():
        named.update(row.get("models", {}))
    return named


def _write(catalog, path):
    # NOT sort_keys: `tiers` is declared cheapest-first and that order is the vocabulary
    # the resolver reports. Determinism comes from project() emitting sorted providers
    # and sorted ids, and from every other key being rewritten in place.
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2)
        fh.write("\n")


def refresh(catalog_path=None, upstream=None):
    path = catalog_path or MT.CATALOG_PATH
    catalog = MT.load(path)
    # `is None`, not `or`: an empty-but-valid upstream body must reach the projection as
    # the emptiness it is, never be quietly replaced by a second fetch that went better.
    catalog["providers"] = project(_fetch() if upstream is None else upstream,
                                   _providers(catalog))
    _write(catalog, path)
    counts = ", ".join(f"{p}: {len(m)}" for p, m in sorted(catalog["providers"].items()))
    print(f"✓ model catalog projection refreshed — {path} ({counts})")
    return 0


def drift(catalog_path=None, upstream=None):
    """Compare the projection against upstream. Returns a list of problems."""
    catalog = MT.load(catalog_path)
    fresh = project(_fetch() if upstream is None else upstream, _providers(catalog))
    found = []
    for prov, models in sorted(catalog["providers"].items()):
        for mid, row in sorted(models.items()):
            live = fresh.get(prov, {}).get(mid)
            if live is None:
                found.append(f"not_found: `{prov}/{mid}` is no longer listed upstream")
            elif live["context"] != row.get("context"):
                found.append(
                    f"drift: `{prov}/{mid}` context {row.get('context')} projected, "
                    f"{live['context']} upstream")
        added = sorted(set(fresh.get(prov, {})) - set(models))
        if added:
            found.append(
                f"drift: `{prov}` lists {len(added)} model(s) the projection does not "
                f"({', '.join(added)}) — run --refresh")
    return found


def main(argv):
    ap = argparse.ArgumentParser(
        description="Tier map gate: every pinned model id is real, and no agent names one.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--refresh", action="store_true",
                      help=f"fetch {UPSTREAM} and rewrite the projection (network)")
    mode.add_argument("--drift", action="store_true",
                      help="compare the projection against upstream without writing (network)")
    args = ap.parse_args(argv)

    if args.refresh or args.drift:
        try:
            upstream = _fetch()
        except (urllib.error.URLError, OSError, ValueError) as exc:
            print(f"✗ model catalog — {UPSTREAM} unreachable ({exc}); this is not evidence "
                  "that the projection is clean, so the gate is red")
            return 1
        if args.refresh:
            return refresh(upstream=upstream)
        found = drift(upstream=upstream)
        if found:
            print(f"✗ model catalog drift — {len(found)} finding(s):")
            for f in found:
                print(f"  - {f}")
            return 1
        print(f"✓ model catalog projection matches {UPSTREAM}")
        return 0

    found = problems()
    if found:
        print(f"✗ model tiers — {len(found)} problem(s):")
        for f in found:
            print(f"  - {f}")
        return 1
    catalog = MT.load()
    pins = ", ".join(
        f"{t}={MT.model_for(catalog, t)}" for t in MT.tiers(catalog))
    print(f"✓ model tiers — {len(agent_files(AGENTS))} agents resolve through the map "
          f"[{MT.active_provider(catalog)}: {pins}]")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
