"""check_plugin_diagrams.py — the plugin-README diagram guard.

Fixture repos are built under a tempdir (never under primitives-core/, per the roster
guard's orphan rule) and the module's REPO/PLUGINS_DIR/PRIMITIVES_DIR constants are pointed
at them for the duration of each test.

Every check has a fixture that makes it go RED. A guard whose failure path is never
exercised is a guard nobody has tested — and this one's whole reason to exist is that a
broken diagram fails silently on GitHub.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_plugin_diagrams as D  # noqa: E402

HEALTHY = """# alpha

A bundle.

## How it fits together

```mermaid
flowchart LR
    In[Something arrives] --> S[alpha routes it]
    S -->|needs recon| Scout[probe]
    S -->|needs a write| Out[Result]
    Scout --> Out
```

## What you get
"""


class DiagramGuard(unittest.TestCase):
    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-plugin-diagrams-")
        self.saved = {k: getattr(D, k) for k in ("REPO", "PLUGINS_DIR", "PRIMITIVES_DIR")}
        D.REPO = self.fix
        D.PLUGINS_DIR = os.path.join(self.fix, "plugins")
        D.PRIMITIVES_DIR = os.path.join(self.fix, "primitives-core")
        # two primitives exist in the collection; only `alpha` and `probe` ship in plugin alpha
        for sid in ("alpha", "probe", "elsewhere"):
            os.makedirs(os.path.join(self.fix, "primitives-core", "skills", sid))
        os.makedirs(os.path.join(self.fix, "plugins", "alpha", "skills", "alpha"))
        os.makedirs(os.path.join(self.fix, "plugins", "alpha", "skills", "probe"))
        self.readme = os.path.join(self.fix, "plugins", "alpha", "README.md")
        self._write(HEALTHY)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(D, k, v)
        shutil.rmtree(self.fix, ignore_errors=True)

    def _write(self, text):
        with open(self.readme, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _only_problem(self):
        found = D.problems()
        self.assertEqual(len(found), 1, f"expected exactly one problem, got {found}")
        return found[0]

    # --- baseline -----------------------------------------------------------------

    def test_healthy_readme_is_clean(self):
        self.assertEqual(D.problems(), [])

    # --- check 1: presence --------------------------------------------------------

    def test_readme_without_a_mermaid_fence_is_flagged(self):
        self._write("# alpha\n\nProse only, no diagram.\n")
        self.assertIn("no ```mermaid block", self._only_problem())

    def test_missing_readme_is_flagged(self):
        os.remove(self.readme)
        self.assertIn("missing", self._only_problem())

    def test_a_fence_that_is_not_mermaid_does_not_count(self):
        self._write("# alpha\n\n```python\nprint('hi')\n```\n")
        self.assertIn("no ```mermaid block", self._only_problem())

    # --- check 2: the house rule --------------------------------------------------

    def test_parenthesis_in_a_node_label_is_flagged(self):
        self._write(HEALTHY.replace("S[alpha routes it]", "S[alpha routes it (fast)]"))
        p = self._only_problem()
        self.assertIn("house rule", p)
        self.assertIn("(", p)

    def test_parenthesis_in_an_edge_label_is_flagged(self):
        self._write(HEALTHY.replace("|needs recon|", "|needs recon (maybe)|"))
        self.assertIn("house rule", self._only_problem())

    def test_ampersand_in_a_label_is_flagged(self):
        self._write(HEALTHY.replace("In[Something arrives]", "In[Something & arrives]"))
        self.assertIn("house rule", self._only_problem())

    def test_cylinder_shape_is_not_mistaken_for_a_banned_parenthesis(self):
        # `[( )]` is a legitimate database shape, not a parenthesis inside a label.
        self._write(HEALTHY.replace("Out[Result]", "Out[(Result store)]"))
        self.assertEqual(D.problems(), [])

    def test_circle_shape_is_not_mistaken_for_a_banned_parenthesis(self):
        self._write(HEALTHY.replace("Out[Result]", "Out((Result))"))
        self.assertEqual(D.problems(), [])

    # --- check 3: reserved word as a bare node id ---------------------------------

    def test_reserved_word_as_a_bare_node_id_is_flagged(self):
        # measured: `load --> end` renders NOTHING and mermaid-cli still exits 0
        self._write("# alpha\n\n```mermaid\nflowchart LR\n    load --> end\n```\n")
        p = self._only_problem()
        self.assertIn("reserved word", p)
        self.assertIn("end", p)

    def test_reserved_word_on_the_left_of_an_arrow_is_flagged(self):
        self._write("# alpha\n\n```mermaid\nflowchart LR\n    class --> B[Two]\n```\n")
        self.assertIn("reserved word", self._only_problem())

    def test_reserved_word_as_a_label_is_allowed(self):
        # the sanctioned fix: arbitrary id, real word kept as the label
        self._write("# alpha\n\n```mermaid\nflowchart LR\n    load[Load] --> fin[end]\n```\n")
        self.assertEqual(D.problems(), [])

    def test_subgraph_end_terminator_is_not_a_reserved_word_violation(self):
        body = "flowchart TD\n    subgraph Box\n        A[One]\n    end\n    A --> B[Two]"
        self._write(f"# alpha\n\n```mermaid\n{body}\n```\n")
        self.assertEqual(D.problems(), [])

    # --- check 4: theme safety ----------------------------------------------------

    def test_hardcoded_fill_is_flagged(self):
        self._write(HEALTHY.replace("    Scout --> Out\n", "    Scout --> Out\n    style Out fill:#fff\n"))
        self.assertIn("fill", self._only_problem())

    def test_classdef_fill_is_flagged(self):
        self._write(HEALTHY.replace("    Scout --> Out\n", "    Scout --> Out\n    classDef hot fill:#f00\n"))
        self.assertIn("fill", self._only_problem())

    # --- check 4: node ceiling ----------------------------------------------------

    def test_node_count_over_the_ceiling_is_flagged(self):
        rows = "\n".join(f"    N{i}[Node {i}] --> N{i + 1}[Node {i + 1}]" for i in range(D.MAX_NODES + 2))
        self._write(f"# alpha\n\n```mermaid\nflowchart TD\n{rows}\n```\n")
        self.assertIn("exceeds the ceiling", self._only_problem())

    def test_node_count_at_the_ceiling_is_allowed(self):
        # exactly MAX_NODES nodes — the ceiling is inclusive
        rows = "\n".join(f"    N{i} --> N{i + 1}" for i in range(D.MAX_NODES - 1))
        self._write(f"# alpha\n\n```mermaid\nflowchart TD\n{rows}\n```\n")
        self.assertEqual(D.problems(), [])

    def test_subgraph_title_does_not_count_as_a_node(self):
        body = "flowchart TD\n    subgraph Some Container\n        A[One]\n    end\n    A --> B[Two]"
        self._write(f"# alpha\n\n```mermaid\n{body}\n```\n")
        self.assertEqual(D.problems(), [])
        self.assertEqual(D._node_ids(body), {"A", "B"})

    def test_inline_dotted_edge_label_does_not_count_as_a_node(self):
        # `-.text.->` is as valid as `-.->|text|`; both must mask the label the same way
        body = "flowchart TD\n  A -.calls.-> B\n  B -->|ok| C\n"
        self.assertEqual(D._node_ids(body), {"A", "B", "C"})

    def test_inline_labels_on_plain_and_thick_edges_do_not_count_as_nodes(self):
        self.assertEqual(D._node_ids("flowchart TD\n  A --calls--> B\n"), {"A", "B"})
        self.assertEqual(D._node_ids("flowchart TD\n  A == calls ==> B\n"), {"A", "B"})

    def test_unlabelled_edges_and_chains_keep_every_node(self):
        self.assertEqual(D._node_ids("flowchart TD\n  A --> B --> C\n"), {"A", "B", "C"})
        self.assertEqual(D._node_ids("flowchart TD\n  A --- B --- C\n"), {"A", "B", "C"})
        self.assertEqual(D._node_ids("flowchart TD\n  A -.-> B ==> C\n"), {"A", "B", "C"})

    def test_reserved_word_in_an_inline_dotted_label_is_allowed(self):
        self._write("# alpha\n\n```mermaid\nflowchart LR\n    load -.end.-> fin[Fin]\n```\n")
        self.assertEqual(D.problems(), [])

    # --- check 5: ghost primitives ------------------------------------------------

    def test_naming_a_primitive_the_plugin_does_not_ship_is_flagged(self):
        self._write(HEALTHY.replace("S[alpha routes it]", "S[elsewhere routes it]"))
        p = self._only_problem()
        self.assertIn("does not ship", p)
        self.assertIn("elsewhere", p)

    def test_a_retired_primitive_left_in_a_diagram_is_flagged(self):
        # the foreman->atelier class of bug: the id no longer exists in the assembly
        shutil.rmtree(os.path.join(self.fix, "plugins", "alpha", "skills", "probe"))
        self.assertIn("does not ship", self._only_problem())

    def test_a_word_that_is_not_a_primitive_id_is_not_flagged(self):
        self._write(HEALTHY.replace("In[Something arrives]", "In[A nonprimitive word arrives]"))
        self.assertEqual(D.problems(), [])

    def test_membership_is_derived_from_disk_not_from_a_list(self):
        self.assertEqual(D._assembly_members("alpha"), {"alpha", "probe"})
        os.makedirs(os.path.join(self.fix, "plugins", "alpha", "skills", "elsewhere"))
        self.assertEqual(D._assembly_members("alpha"), {"alpha", "probe", "elsewhere"})

    def test_loose_files_in_an_assembly_are_not_members(self):
        hooks = os.path.join(self.fix, "plugins", "alpha", "hooks")
        os.makedirs(hooks)
        with open(os.path.join(hooks, "hooks.json"), "w") as fh:
            fh.write("{}")
        self.assertNotIn("hooks.json", D._assembly_members("alpha"))

    # --- shape of the report ------------------------------------------------------

    def test_every_problem_is_reported_not_just_the_first(self):
        self._write(
            HEALTHY.replace("S[alpha routes it]", "S[elsewhere routes it (fast)]")
        )
        found = D.problems()
        self.assertGreaterEqual(len(found), 2)
        self.assertTrue(any("house rule" in p for p in found))
        self.assertTrue(any("does not ship" in p for p in found))

    def test_multiple_fences_are_all_checked(self):
        self._write(HEALTHY + "\n```mermaid\nflowchart LR\n    X[elsewhere here]\n```\n")
        p = self._only_problem()
        self.assertIn("mermaid block 2", p)


if __name__ == "__main__":
    unittest.main()
