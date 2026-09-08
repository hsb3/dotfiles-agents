#!/usr/bin/env python3
"""model_tiers — resolve a provider-independent dispatch tier to a concrete model id.

An agent declares a tier (`light` / `mid` / `heavy`), never a model. `model_catalog.json`
beside this module is the single map from (tier, provider) to a concrete id, plus the
projected upstream catalog those ids are checked against and the context window each one
carries. Switching provider is an edit to `active_provider` in that one file.

Two readers, two different failure contracts:

  - `scripts/check_model_tiers.py` (the gate) calls `load()` and lets it RAISE: a catalog
    that will not parse is a red build, not a default.
  - a hook calls the resolvers and gets `None` for anything unmapped, so a session never
    dies because someone asked about a model nobody pinned.

`window_for` normalizes what Claude Code actually writes into a transcript: a bare catalog
id (`claude-opus-4-8`), a dated id (`claude-haiku-4-5-20251001`), or a windowed variant
carrying a bracketed suffix (`claude-opus-5[1m]`).

Stdlib-only, no network. The refresh and drift paths against the upstream catalog live in
`scripts/check_model_tiers.py`, which is not shipped.
"""

import json
import os
import re

CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_catalog.json")

#: `claude-opus-5[1m]` -> `claude-opus-5`; the harness appends the variant, the catalog does not.
_VARIANT_SUFFIX = re.compile(r"\[[^\]]*\]\s*$")


def load(path=None):
    """Parse the catalog. Raises ValueError on absent, unparseable, or wrong-shaped."""
    path = path or CATALOG_PATH
    try:
        with open(path, encoding="utf-8") as fh:
            catalog = json.load(fh)
    except OSError as exc:
        raise ValueError(f"model catalog unreadable at {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"model catalog at {path} is not valid JSON: {exc}") from exc
    for key in ("active_provider", "tiers", "providers"):
        if key not in catalog:
            raise ValueError(f"model catalog at {path} has no `{key}` key")
    if not isinstance(catalog["tiers"], dict) or not isinstance(catalog["providers"], dict):
        raise ValueError(f"model catalog at {path}: `tiers` and `providers` must be objects")
    return catalog


def active_provider(catalog):
    """The provider whose ids the harness actually dispatches."""
    return catalog["active_provider"]


def tiers(catalog):
    """The tier vocabulary, in declared order (cheapest first)."""
    return list(catalog["tiers"])


def model_for(catalog, tier, provider=None):
    """(tier, provider) -> concrete model id, or None when that pairing is unmapped."""
    row = catalog["tiers"].get(tier)
    if not row:
        return None
    return row.get("models", {}).get(provider or active_provider(catalog))


def claude_code_keyword(catalog, tier):
    """tier -> the keyword Claude Code agent frontmatter accepts, or None."""
    row = catalog["tiers"].get(tier)
    return row.get("claude_code_keyword") if row else None


def window_for(catalog, model_id, provider=None):
    """A concrete model id -> its context window in tokens, or None if unknown."""
    if not model_id:
        return None
    bare = _VARIANT_SUFFIX.sub("", model_id).strip()
    row = catalog["providers"].get(provider or active_provider(catalog), {}).get(bare)
    return row.get("context") if isinstance(row, dict) else None
