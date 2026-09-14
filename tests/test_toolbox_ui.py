"""Production UI behavior checks rendered through React's server renderer."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "evals" / "ui" / "src" / "ui.tsx"
VIEWS = ROOT / "evals" / "ui" / "src" / "views.tsx"
DATA = ROOT / "evals" / "ui" / "src" / "data.ts"


@unittest.skipUnless(shutil.which("bun"), "Bun is required for React UI checks")
class ToolboxUiTests(unittest.TestCase):
    def run_module(self, body):
        script = """import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { Home } from %s;
import { submitLogin } from %s;
%s
""" % (json.dumps(VIEWS.as_uri()), json.dumps(UI.as_uri()), body)
        result = subprocess.run(["bun", "--input-type=module", "-e", script], text=True,
                                capture_output=True, check=False, cwd=ROOT / "evals" / "ui")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_home_has_four_oriented_actions_in_owner_navigation_order(self):
        self.run_module("""
const html = renderToStaticMarkup(React.createElement(Home));
for (const phrase of ['Catalog discovers packaged workflows/plugins and database primitives.', 'Documentation reads stored instructions, references, and source context.', 'Performance explains when measurement provenance and comparability become available.', 'Evaluations inspects current assessments and per-job coverage.']) assert.ok(html.includes(phrase));
const order = ['Home', 'Catalog', 'Documentation', 'Performance', 'Evaluations'].map((name) => html.indexOf('>' + name + '<'));
assert.deepEqual([...order].sort((a, b) => a - b), order);
for (const route of ['catalog', 'documentation', 'performance', 'evaluations']) assert.match(html, new RegExp('href=\\"#' + route + '\\"'));
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

    def test_catalog_filter_and_real_relation_queries(self):
        script = """import assert from 'node:assert/strict';
import { Session } from %s;
import { documentationFor, extenders, filterCatalog, jobCoverage } from %s;
let urls = []; const session = new Session(async (url) => { urls.push(url); return new Response(JSON.stringify({items: [], page: 2, totalPages: 3})); });
assert.deepEqual(filterCatalog([{name: 'Handoff'}, {description: 'Review changes'}], 'review').length, 1);
await extenders(session, `a'b`, 2); await documentationFor(session, 'ext-1'); await jobCoverage(session);
const paths = urls.map((url) => new URL('https://toolbox.test' + url));
assert.match(paths[0].searchParams.get('filter'), /slug ~ 'a\\\\'b'|name ~ 'a\\\\'b'|description ~ 'a\\\\'b'/);
assert.equal(paths[0].searchParams.get('page'), '2');
assert.equal(paths[1].searchParams.get('filter'), "extender = 'ext-1'");
assert.equal(paths[2].searchParams.get('expand'), 'job');
assert.match(paths[2].searchParams.get('fields'), /expand.job.name/);
""" % (json.dumps((ROOT / "evals" / "ui" / "src" / "api.ts").as_uri()), json.dumps(DATA.as_uri()))
        result = subprocess.run(["bun", "--input-type=module", "-e", script], text=True, capture_output=True, check=False, cwd=ROOT / "evals" / "ui")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
