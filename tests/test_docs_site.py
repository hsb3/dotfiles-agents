"""Project Pages links must keep the repo prefix and resolve real headings."""
import tempfile
import unittest
from pathlib import Path
from scripts.build_docs import rewrite, validate


class DocsSiteTests(unittest.TestCase):
    def test_project_links_and_missing_heading(self):
        link = {'t': 'Link', 'c': [['', [], []], [], ['../README.md#install', '']]}
        result = rewrite(link, Path('docs/site.md'), {Path('README.md')}, '/dotfiles-agents', 'dev')
        self.assertEqual(result['c'][-1][0], '/dotfiles-agents/README.html#install')
        link['c'][-1][0] = '../.github/CONTRIBUTING.md'
        result = rewrite(link, Path('docs/site.md'), {Path('.github/CONTRIBUTING.md')}, '/dotfiles-agents', 'dev')
        self.assertEqual(result['c'][-1][0], '/dotfiles-agents/contributing.html')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'index.html').write_text('<a href="/dotfiles-agents/README.html#install">Install</a>')
            (root / 'README.html').write_text('<h1 id="install">Install</h1>')
            self.assertEqual(validate(root, '/dotfiles-agents'), 2)
            (root / 'README.html').write_text('<h1 id="renamed">Install</h1>')
            with self.assertRaisesRegex(ValueError, 'missing heading'):
                validate(root, '/dotfiles-agents')
            (root / 'index.html').write_text('<a href="/README.html">Wrong root</a>')
            with self.assertRaisesRegex(ValueError, 'escapes project subpath'):
                validate(root, '/dotfiles-agents')
