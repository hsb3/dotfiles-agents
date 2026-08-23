"""The layer boundary is structural, and the waiting doctrine depends on it.

`delegation/references/waiting.md` tells a manager that a message to a live
execution agent can never be answered, and tells each execution agent that its
report is its only channel. Both claims are true only while `manager` is the
sole agent carrying `SendMessage`. Granting it downward would silently turn the
shipped doctrine into a lie — and would also hand workers a sibling channel,
which is what the negative list in `briefs.md` exists to prevent.

So the frontmatter is pinned here, together with the one-way clause each
execution agent's body must carry.
"""

import re
import unittest
from pathlib import Path

AGENTS = Path(__file__).resolve().parent.parent / "primitives-core" / "agents"

EXECUTION = ("builder.md", "reviewer.md", "scout.md")
ONE_WAY_HEADING = "## A message you receive is one-way"


def tools(name):
    """The `tools:` list from an agent definition's frontmatter."""
    body = (AGENTS / name).read_text(encoding="utf-8")
    m = re.search(r"^tools:(.*)$", body, re.MULTILINE)
    assert m, f"{name} has no tools: key"
    return {t.strip() for t in m.group(1).split(",") if t.strip()}


class AgentLayerBoundary(unittest.TestCase):
    def test_manager_is_the_only_agent_that_can_spawn_or_message(self):
        self.assertLessEqual({"Agent", "SendMessage"}, tools("manager.md"))

    def test_execution_agents_carry_neither(self):
        for name in EXECUTION:
            got = tools(name)
            for tool in ("Agent", "SendMessage"):
                with self.subTest(agent=name, tool=tool):
                    self.assertNotIn(tool, got)

    def test_execution_agents_state_the_one_way_rule(self):
        for name in EXECUTION:
            with self.subTest(agent=name):
                self.assertIn(
                    ONE_WAY_HEADING, (AGENTS / name).read_text(encoding="utf-8")
                )


if __name__ == "__main__":
    unittest.main()
