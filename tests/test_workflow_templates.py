"""Drift guard: the standard's workflow templates vs this repo's live workflows.

Dependabot watches .github/workflows/ but NOT the template assets under
primitives-core/skills/repo-meta-structure/assets/github/workflows/ — so the
copy-into-new-repos set goes stale silently. These tests fail whenever a
dependabot bump lands in .github/ without the same pin in the templates,
forcing the sync in the same change.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIVE = REPO / ".github" / "workflows"
ASSETS = (
    REPO
    / "primitives-core"
    / "skills"
    / "repo-meta-structure"
    / "assets"
    / "github"
    / "workflows"
)

USES = re.compile(r"uses:\s*(\S+?)@(\S+)")


def action_pins(path: Path) -> dict[str, set[str]]:
    pins: dict[str, set[str]] = {}
    for action, ref in USES.findall(path.read_text()):
        pins.setdefault(action, set()).add(ref)
    return pins


class TestWorkflowTemplateDrift(unittest.TestCase):
    def test_claude_workflows_byte_identical_to_templates(self):
        """claude.yml / claude-review.yml are verbatim copies of the templates."""
        for name in ("claude.yml", "claude-review.yml"):
            with self.subTest(workflow=name):
                self.assertEqual(
                    (ASSETS / name).read_text(),
                    (LIVE / name).read_text(),
                    f"{name}: template and live copy differ — sync them in the same change",
                )

    def test_action_pins_match_across_templates_and_live(self):
        """Every action used in both places is pinned to the same ref(s).

        Covers ci.yml too (which legitimately differs in content but must not
        drift on action versions).
        """
        live: dict[str, set[str]] = {}
        templ: dict[str, set[str]] = {}
        for f in LIVE.glob("*.yml"):
            for action, refs in action_pins(f).items():
                live.setdefault(action, set()).update(refs)
        for f in ASSETS.glob("*.yml"):
            for action, refs in action_pins(f).items():
                templ.setdefault(action, set()).update(refs)
        for action in sorted(set(live) & set(templ)):
            with self.subTest(action=action):
                self.assertEqual(
                    templ[action],
                    live[action],
                    f"{action}: template pins {sorted(templ[action])} but live "
                    f"workflows pin {sorted(live[action])} — bump the template",
                )

    def test_single_pin_per_action_in_templates(self):
        """Templates never carry two different refs for the same action."""
        for f in ASSETS.glob("*.yml"):
            for action, refs in action_pins(f).items():
                with self.subTest(template=f.name, action=action):
                    self.assertEqual(
                        1, len(refs), f"{f.name}: {action} pinned at {sorted(refs)}"
                    )


if __name__ == "__main__":
    unittest.main()
