"""Production UI behavior checks rendered through React's server renderer."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "evals" / "ui" / "src" / "ui.tsx"
VIEWS = ROOT / "evals" / "ui" / "src" / "views.tsx"


@unittest.skipUnless(shutil.which("bun"), "Bun is required for React UI checks")
class ToolboxUiTests(unittest.TestCase):
    def run_module(self, body):
        script = """import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { App } from %s;
import { submitLogin } from %s;
%s
""" % (json.dumps(VIEWS.as_uri()), json.dumps(UI.as_uri()), body)
        result = subprocess.run(["bun", "--input-type=module", "-e", script], text=True,
                                capture_output=True, check=False, cwd=ROOT / "evals" / "ui")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_home_has_four_oriented_actions_in_owner_navigation_order(self):
        self.run_module("""
const html = renderToStaticMarkup(React.createElement(App, { route: 'home' }));
for (const phrase of ['Catalog discovers packaged workflows/plugins and database primitives.', 'Documentation reads stored instructions, references, and source context.', 'Performance explains when measurement provenance and comparability become available.', 'Evaluations inspects current assessments and per-job coverage.']) assert.ok(html.includes(phrase));
const order = ['Home', 'Catalog', 'Documentation', 'Performance', 'Evaluations'].map((name) => html.indexOf('>' + name + '<'));
assert.deepEqual([...order].sort((a, b) => a - b), order);
for (const route of ['catalog', 'documentation', 'performance', 'evaluations']) assert.match(html, new RegExp('href=\\"#' + route + '\\"'));
""")

    def test_routes_expose_distinct_states_and_text_only_reader(self):
        self.run_module("""
for (const state of ['loading', 'access', 'error', 'empty']) {
  const html = renderToStaticMarkup(React.createElement(App, { route: 'catalog', catalogState: state }));
  assert.match(html, /Loading catalog|Catalog access expired|Could not load catalog|No catalog records/);
}
const html = renderToStaticMarkup(React.createElement(App, { route: 'documentation', documentText: '<img src=x onerror=alert(1)>' }));
assert.match(html, /&lt;img src=x onerror=alert\\(1\\)&gt;/);
assert.doesNotMatch(html, /<img src=x/);
""")

    def test_password_is_cleared_for_success_and_failure(self):
        self.run_module("""
let password = 'secret';
await submitLogin({ login: async () => ({ kind: 'ok', data: { token: 'memory' } }) }, 'user@example.test', password, (value) => { password = value; });
assert.equal(password, '');
password = 'secret';
await submitLogin({ login: async () => ({ kind: 'error', status: 0, message: 'No connection' }) }, 'user@example.test', password, (value) => { password = value; });
assert.equal(password, '');
""")


if __name__ == "__main__":
    unittest.main()
