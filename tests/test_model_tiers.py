"""Model-tier map + its real-catalog gate (card 58xa).

Two things are under test and they fail differently on purpose:

  - `primitives-core/hooks/_lib/model_tiers.py` is the RUNTIME resolver a hook imports.
    It never raises on a value it does not recognize (an unknown model id is `None`), so a
    hook that asks about a model nobody pinned degrades instead of dying mid-session.
  - `scripts/check_model_tiers.py` is the GATE. Everything the resolver answers `None` to
    is a red failure there, named with the tier and provider that produced it.

The fixtures below build their own catalogs in tempdirs — including a fictional provider,
which is how "switching provider means editing one map" is proved without shipping a
provider nobody dispatches.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "primitives-core", "hooks", "_lib"))

import check_model_tiers as GATE  # noqa: E402
import model_tiers as MT  # noqa: E402

AGENTS = os.path.join(REPO, "primitives-core", "agents")
TRANSLATION = os.path.join(REPO, "translation.yaml")


def _shipped():
    return MT.load()


def _write(catalog, where):
    path = os.path.join(where, "model_catalog.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2)
    return path


class TestResolver(unittest.TestCase):
    def setUp(self):
        self.catalog = _shipped()

    def test_vocabulary_is_semantic_not_a_model_family(self):
        self.assertEqual(MT.tiers(self.catalog), ["light", "mid", "heavy"])

    def test_active_provider_is_anthropic(self):
        self.assertEqual(MT.active_provider(self.catalog), "anthropic")

    def test_model_for_resolves_tier_and_provider_to_a_concrete_id(self):
        self.assertEqual(MT.model_for(self.catalog, "light"), "claude-haiku-4-5")
        self.assertEqual(MT.model_for(self.catalog, "mid"), "claude-sonnet-5")
        self.assertEqual(MT.model_for(self.catalog, "heavy"), "claude-opus-5")

    def test_model_for_unmapped_tier_is_none_not_an_exception(self):
        self.assertIsNone(MT.model_for(self.catalog, "featherweight"))

    def test_model_for_unmapped_provider_is_none(self):
        self.assertIsNone(MT.model_for(self.catalog, "light", provider="acme"))

    def test_claude_code_keyword_per_tier(self):
        self.assertEqual(
            [MT.claude_code_keyword(self.catalog, t) for t in MT.tiers(self.catalog)],
            ["haiku", "sonnet", "opus"],
        )
        self.assertIsNone(MT.claude_code_keyword(self.catalog, "featherweight"))

    def test_window_for_real_id(self):
        """6gw5's watermark hook reads a live context window off a concrete id."""
        self.assertEqual(MT.window_for(self.catalog, "claude-opus-5"), 1000000)
        self.assertGreater(MT.window_for(self.catalog, "claude-haiku-4-5"), 0)

    def test_window_for_strips_a_harness_suffix(self):
        """CC writes a windowed variant into transcripts as `claude-opus-5[1m]`."""
        self.assertEqual(
            MT.window_for(self.catalog, "claude-opus-5[1m]"),
            MT.window_for(self.catalog, "claude-opus-5"),
        )

    def test_window_for_bare_transcript_ids_resolve(self):
        for observed in ("claude-opus-4-8", "claude-haiku-4-5-20251001"):
            self.assertIsInstance(MT.window_for(self.catalog, observed), int, observed)

    def test_window_for_unknown_id_is_none_never_an_exception(self):
        self.assertIsNone(MT.window_for(self.catalog, "claude-imaginary-9"))
        self.assertIsNone(MT.window_for(self.catalog, ""))

    def test_catalog_path_sits_beside_the_module(self):
        self.assertTrue(os.path.isfile(MT.CATALOG_PATH))
        self.assertEqual(
            os.path.dirname(MT.CATALOG_PATH), os.path.dirname(os.path.abspath(MT.__file__))
        )

    def test_every_provider_model_carries_a_positive_window(self):
        provider = MT.active_provider(self.catalog)
        models = self.catalog["providers"][provider]
        self.assertGreater(len(models), 3)
        for mid, row in models.items():
            self.assertGreater(row["context"], 0, mid)

    def test_load_of_a_malformed_catalog_raises_for_the_gate(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "model_catalog.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        with self.assertRaises(ValueError):
            MT.load(path)

    def test_load_of_an_absent_catalog_raises_for_the_gate(self):
        with self.assertRaises(ValueError):
            MT.load(os.path.join(tempfile.gettempdir(), "no-such-model-catalog.json"))

    def test_load_of_a_structurally_wrong_catalog_raises(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with self.assertRaises(ValueError):
            MT.load(_write({"tiers": {}}, d))


class TestGateOnTheShippedTree(unittest.TestCase):
    def test_real_tree_is_green(self):
        self.assertEqual(GATE.problems(), [])

    def test_main_exits_zero(self):
        self.assertEqual(GATE.main([]), 0)

    def test_help_works(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "scripts", "check_model_tiers.py"), "--help"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.strip())


class TestGateFixtures(unittest.TestCase):
    """Each case mutates one thing and asserts the gate goes red naming it."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.catalog = _shipped()

    def _catalog_path(self, catalog=None):
        return _write(catalog or self.catalog, self.dir)

    def _agents_dir(self, edits=None):
        """A copy of the real agents dir, optionally with per-agent line rewrites."""
        d = os.path.join(self.dir, "agents")
        shutil.copytree(AGENTS, d)
        for name, (old, new) in (edits or {}).items():
            path = os.path.join(d, name)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn(old, text, f"{name}: fixture anchor missing")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace(old, new, 1))
        return d

    def test_copy_of_the_real_tree_is_still_green(self):
        """Guards every negative case below from passing for the wrong reason."""
        self.assertEqual(
            GATE.problems(catalog_path=self._catalog_path(), agents_dir=self._agents_dir()), []
        )

    def test_invented_model_id_fails(self):
        bad = copy.deepcopy(self.catalog)
        bad["tiers"]["heavy"]["models"]["anthropic"] = "claude-opus-9000"
        found = GATE.problems(catalog_path=self._catalog_path(bad), agents_dir=self._agents_dir())
        self.assertTrue(any("claude-opus-9000" in p for p in found), found)

    def test_model_id_with_a_zero_window_fails(self):
        bad = copy.deepcopy(self.catalog)
        bad["providers"]["anthropic"]["claude-opus-5"]["context"] = 0
        found = GATE.problems(catalog_path=self._catalog_path(bad), agents_dir=self._agents_dir())
        self.assertTrue(any("claude-opus-5" in p for p in found), found)

    def test_tier_with_no_mapping_for_the_active_provider_fails_loudly(self):
        bad = copy.deepcopy(self.catalog)
        del bad["tiers"]["mid"]["models"]["anthropic"]
        found = GATE.problems(catalog_path=self._catalog_path(bad), agents_dir=self._agents_dir())
        self.assertTrue(
            any("mid" in p and "anthropic" in p for p in found),
            f"the failure must name BOTH the tier and the provider: {found}",
        )

    def test_agent_model_that_does_not_render_its_tier_fails(self):
        agents = self._agents_dir({"scout.md": ("model: haiku", "model: opus")})
        found = GATE.problems(catalog_path=self._catalog_path(), agents_dir=agents)
        self.assertTrue(any("scout" in p and "haiku" in p for p in found), found)

    def test_agent_with_no_tier_fails(self):
        agents = self._agents_dir({"builder.md": ("tier: mid\n", "")})
        found = GATE.problems(catalog_path=self._catalog_path(), agents_dir=agents)
        self.assertTrue(any("builder" in p and "tier" in p for p in found), found)

    def test_agent_with_an_unknown_tier_fails(self):
        agents = self._agents_dir({"builder.md": ("tier: mid", "tier: medium-ish")})
        found = GATE.problems(catalog_path=self._catalog_path(), agents_dir=agents)
        self.assertTrue(any("medium-ish" in p for p in found), found)

    def test_agent_naming_a_full_model_id_fails(self):
        agents = self._agents_dir(
            {"reviewer.md": ("model: opus", "model: anthropic/claude-opus-5")}
        )
        found = GATE.problems(catalog_path=self._catalog_path(), agents_dir=agents)
        self.assertTrue(any("reviewer" in p for p in found), found)

    def test_agent_naming_a_dotted_model_id_fails(self):
        agents = self._agents_dir({"reviewer.md": ("model: opus", "model: claude-opus-4-1")})
        found = GATE.problems(catalog_path=self._catalog_path(), agents_dir=agents)
        self.assertTrue(any("reviewer" in p for p in found), found)

    def test_a_second_tier_to_id_map_in_translation_yaml_fails(self):
        path = os.path.join(self.dir, "translation.yaml")
        with open(TRANSLATION, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace("  - alias: haiku\n", "  - alias: haiku\n    ref: anthropic/claude-haiku-4-5\n", 1))
        found = GATE.problems(
            catalog_path=self._catalog_path(), agents_dir=self._agents_dir(),
            translation_path=path,
        )
        self.assertTrue(any("haiku" in p and "model_aliases" in p for p in found), found)

    def test_a_broken_catalog_is_a_gate_failure_not_a_traceback(self):
        path = os.path.join(self.dir, "model_catalog.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        found = GATE.problems(catalog_path=path, agents_dir=self._agents_dir())
        self.assertTrue(found)


class TestProviderSwitchIsOneEdit(unittest.TestCase):
    """AC#5: a provider switch edits the map, never the N agent files.

    The fictional provider lives only in this tempdir — shipping one in the real catalog
    would put an id in the tree that no `--drift` run could ever confirm.
    """

    ACME = {
        "light": "acme-spark-1",
        "mid": "acme-forge-1",
        "heavy": "acme-anvil-1",
    }

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        catalog = _shipped()
        catalog["active_provider"] = "acme"
        for tier, mid in self.ACME.items():
            catalog["tiers"][tier]["models"]["acme"] = mid
        catalog["providers"]["acme"] = {
            mid: {"context": 400000} for mid in self.ACME.values()
        }
        self.catalog = catalog
        self.path = _write(catalog, self.dir)

    def test_every_agent_resolves_under_the_new_provider(self):
        for name in sorted(os.listdir(AGENTS)):
            if not name.endswith(".md") or name.lower() == "readme.md":
                continue
            tier = GATE.agent_fields(os.path.join(AGENTS, name))["tier"]
            self.assertEqual(
                MT.model_for(self.catalog, tier), self.ACME[tier],
                f"{name} did not follow the provider switch",
            )

    def test_gate_is_green_with_no_agent_file_edited(self):
        self.assertEqual(GATE.problems(catalog_path=self.path, agents_dir=AGENTS), [])

    def test_windows_come_from_the_new_provider(self):
        self.assertEqual(MT.window_for(self.catalog, "acme-anvil-1"), 400000)


class TestAgentFrontmatter(unittest.TestCase):
    """AC#2 stated as a property of the tree, not of the gate's internals."""

    ROLES = {
        "scout": "light",
        "builder": "mid", "code-reviewer": "mid", "pb-builder": "mid", "rig-builder": "mid",
        "manager": "heavy", "reviewer": "heavy", "pb-reviewer": "heavy",
        "pocketbase-security-auditor": "heavy",
    }

    def test_every_roster_agent_declares_its_dispatch_tier(self):
        found = {}
        for name in sorted(os.listdir(AGENTS)):
            if not name.endswith(".md") or name.lower() == "readme.md":
                continue
            found[name[:-3]] = GATE.agent_fields(os.path.join(AGENTS, name))["tier"]
        self.assertEqual(found, self.ROLES)

    def test_no_agent_model_line_is_an_authored_choice(self):
        catalog = _shipped()
        for name, tier in self.ROLES.items():
            fields = GATE.agent_fields(os.path.join(AGENTS, f"{name}.md"))
            self.assertEqual(fields["model"], MT.claude_code_keyword(catalog, tier), name)


if __name__ == "__main__":
    unittest.main()
