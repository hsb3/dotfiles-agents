"""Consumer packaging: missing skill, wrong dispatch name, or missing prompt is red.

Behavioral persistence and continuation require the disposable live proof; these
checks cover the shipped entrypoint, not the model's compliance with its prose.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CompactHandoffPackagingTests(unittest.TestCase):
    def test_entrypoint_resolves_to_the_authored_skill_without_shadowing(self):
        bundle = ROOT / 'plugins/atelier'
        command = bundle / 'commands/prepare-compact.md'
        skill = bundle / 'skills/compact-handoff/SKILL.md'
        self.assertEqual(
            command.read_text().split('---', 2)[2].strip(),
            'Invoke the `atelier:compact-handoff` skill and follow it.',
        )
        self.assertEqual(
            skill.resolve(),
            ROOT / 'primitives-core/skills/compact-handoff/SKILL.md',
        )
        frontmatter = skill.read_text().split('---', 2)[1]
        self.assertRegex(frontmatter, r'(?m)^name: compact-handoff$')
        self.assertFalse((bundle / 'commands/compact-handoff.md').exists())
        for reference in ('keep-drop.md', 'runtime-support.md'):
            target = skill.parent / 'references' / reference
            self.assertTrue(target.is_file(), reference)
            self.assertIn(f'(references/{reference})', skill.read_text())
        self.assertLessEqual(len(skill.read_text().splitlines()), 60)


if __name__ == '__main__':
    unittest.main()
