"""Tests over the standalone skill catalog + its eligibility guard (issue #115).

The guard (check_skill_catalog) proves the committed catalog is clean; these tests prove the
guard itself is not vacuous — that it REJECTS the things it claims to (a bundled agent, an MCP
requirement, a sibling reference, a plugin-name clash, provenance drift) — plus a few
structural facts about the committed catalog. Stdlib-only.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_skill_catalog as C  # noqa: E402
from check_roster import parse_roster  # noqa: E402

EXPECTED_SIX = {
    "carbon-builder",
    "notion-api",
    "opencode-expertise",
    "dlt-pipelines",
    "subagent-creator",
    "private-fork",
}


def _fixtures():
    roster = {e["id"]: e for e in parse_roster(C.ROSTER)}
    skill_ids = {e["id"] for e in roster.values() if e.get("type") == "skill"}
    bundles = set(C.parse_bundle_ids(C.PLUGINS_YAML))
    return roster, skill_ids, bundles


def _entry(cid, **over):
    e = {
        "id": cid,
        "standalone": "true",
        "clients": ["claude-code", "opencode"],
        "depends_on_skills": [],
        "prerequisites": [],
        "provenance": "authored",
    }
    e.update(over)
    return e


def _problems(entry):
    roster, skill_ids, bundles = _fixtures()
    probs = []
    C.check_entry(entry, roster, skill_ids, bundles, probs)
    return probs


class CommittedCatalog(unittest.TestCase):
    def test_committed_catalog_is_clean(self):
        problems, n = C.run_checks()
        self.assertEqual(
            problems, [], "committed skill-catalog.yaml must pass its own guard"
        )
        self.assertEqual(n, len(EXPECTED_SIX))

    def test_the_six_are_present(self):
        ids = {e["id"] for e in C.parse_catalog(C.CATALOG)}
        self.assertEqual(ids, EXPECTED_SIX)

    def test_every_committed_entry_is_individually_eligible(self):
        for cid in EXPECTED_SIX:
            with self.subTest(cid=cid):
                self.assertEqual(_problems(_entry(cid)), [])


class GuardRejects(unittest.TestCase):
    """Each catalogued-but-ineligible case must produce at least one problem naming the cause."""

    def test_rejects_bundled_agent(self):
        # nanobanana ships primitives-core/skills/nanobanana/agents/openai.yaml
        probs = _problems(_entry("nanobanana", provenance="authored"))
        self.assertTrue(any("agents/ subdir" in p for p in probs), probs)

    def test_rejects_mcp_requirement(self):
        # comms carries requires: [local-mcp] in the roster
        probs = _problems(_entry("comms", provenance="authored"))
        self.assertTrue(any("local-mcp" in p for p in probs), probs)

    def test_rejects_unknown_id(self):
        probs = _problems(_entry("does-not-exist"))
        self.assertTrue(any("no roster entry" in p for p in probs), probs)

    def test_rejects_nonempty_depends_on_skills(self):
        probs = _problems(_entry("carbon-builder", depends_on_skills=["notion-api"]))
        self.assertTrue(
            any("depends_on_skills must be empty" in p for p in probs), probs
        )

    def test_rejects_provenance_drift(self):
        probs = _problems(_entry("carbon-builder", provenance="sourced"))
        self.assertTrue(any("provenance" in p and "drift" in p for p in probs), probs)

    def test_rejects_client_not_in_targets(self):
        # a made-up client that is not among the roster targets[]
        probs = _problems(_entry("carbon-builder", clients=["claude-code", "made-up"]))
        self.assertTrue(any("unknown client" in p for p in probs), probs)

    def test_rejects_plugin_name_clash_with_bundle(self):
        _, skill_ids, bundles = _fixtures()
        self.assertTrue(bundles, "expected bundle ids from plugins.yaml")
        clash = sorted(bundles)[0]
        roster = {e["id"]: e for e in parse_roster(C.ROSTER)}
        # Only meaningful if the bundle id is also a skill id; otherwise assert the namespacing
        # rule directly by injecting the bundle id as a fake skill entry.
        probs = []
        fake_roster = dict(roster)
        fake_roster[clash] = {
            "id": clash,
            "type": "skill",
            "origin": "authored",
            "targets": ["claude-code", "opencode"],
            "source": roster["carbon-builder"]["source"],
        }
        C.check_entry(_entry(clash), fake_roster, skill_ids | {clash}, bundles, probs)
        self.assertTrue(any("clashes with bundle id" in p for p in probs), probs)


if __name__ == "__main__":
    unittest.main()
