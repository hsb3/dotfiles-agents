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

    def test_home_has_approved_title_lede_and_action_oriented_cards(self):
        self.run_module("""
const html = renderToStaticMarkup(React.createElement(Home));
for (const phrase of ['Your Toolbox', 'Find tools for your workflow, read their documentation, and explore recorded performance and evaluations.', 'Find packaged tools and primitives for a workflow.', 'Read stored instructions and references.', 'Explore recorded runs, comparisons, and evidence.', 'Review current assessments and coverage.']) assert.ok(html.includes(phrase));
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
import { distributions, documentationFor, evaluations, extenderById, extenders, filterCatalog, jobCoverage, recordScope, sourceById } from %s;
let urls = []; const session = new Session(async (url) => { urls.push(url); return new Response(JSON.stringify({items: [], page: 2, totalPages: 3})); });
assert.deepEqual(filterCatalog([{name: 'Handoff'}, {description: 'Review changes'}], 'review').length, 1);
await extenders(session, `a'b`, 2); await documentationFor(session, 'ext-1'); await jobCoverage(session); await distributions(session, 3); await extenderById(session, 'ext-1'); await sourceById(session, 'source-1'); await evaluations(session, 'ext-1');
const paths = urls.map((url) => new URL('https://toolbox.test' + url));
assert.match(paths[0].searchParams.get('filter'), /slug ~ 'a\\\\'b'|name ~ 'a\\\\'b'|description ~ 'a\\\\'b'/);
assert.equal(paths[0].searchParams.get('page'), '2');
assert.equal(paths[1].searchParams.get('filter'), "extender = 'ext-1'");
for (const field of ['extender', 'content', 'role']) assert.match(paths[1].searchParams.get('fields'), new RegExp(field));
assert.equal(paths[2].searchParams.get('expand'), 'job');
for (const field of ['eval_run', 'disposition', 'expand.job.id', 'expand.job.name']) assert.match(paths[2].searchParams.get('fields'), new RegExp(field.replace('.', '\\.')));
assert.equal(paths[3].searchParams.get('page'), '3');
for (const field of ['entry_file', 'source']) assert.match(paths[4].searchParams.get('fields'), new RegExp(field));
for (const field of ['name', 'url', 'publisher_kind', 'maintenance']) assert.match(paths[5].searchParams.get('fields'), new RegExp(field));
assert.match(paths[6].searchParams.get('fields'), /eval_run/);
assert.equal(paths[6].searchParams.get('filter'), "extender = 'ext-1'");
assert.equal(paths[6].searchParams.get('expand'), 'extender,framework,element');
assert.equal(recordScope('#documentation?extender=ext%%2F1', 'extender'), 'ext/1');
assert.equal(recordScope('#evaluations?extender=ext-1', 'extender'), 'ext-1');
assert.equal(recordScope('#documentation?extender=', 'extender'), undefined);
""" % (json.dumps((ROOT / "evals" / "ui" / "src" / "api.ts").as_uri()), json.dumps(DATA.as_uri()))
        result = subprocess.run(["bun", "--input-type=module", "-e", script], text=True, capture_output=True, check=False, cwd=ROOT / "evals" / "ui")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_extender_source_access_and_errors_propagate(self):
        script = """import assert from 'node:assert/strict';
import { Session } from %s;
import { extenderWithSource } from %s;
const expanded = await extenderWithSource(new Session(async (url) =>
  url.startsWith('/api/collections/extenders/')
    ? new Response(JSON.stringify({id: 'ext-1', source: 'source-1'}))
    : new Response(JSON.stringify({id: 'source-1', name: 'Named source'})),
), 'ext-1');
assert.equal(expanded.kind, 'ok');
assert.equal(expanded.data.expand.source.name, 'Named source');
for (const [status, kind] of [[403, 'access'], [500, 'error']]) {
  const session = new Session(async (url) => {
    if (url.startsWith('/api/collections/extenders/'))
      return new Response(JSON.stringify({id: 'ext-1', source: 'source-1'}));
    return new Response('source failed', {status});
  });
  const result = await extenderWithSource(session, 'ext-1');
  assert.equal(result.kind, kind);
  assert.equal(result.status, status);
}
""" % (json.dumps((ROOT / "evals" / "ui" / "src" / "api.ts").as_uri()), json.dumps(DATA.as_uri()))
        result = subprocess.run(["bun", "--input-type=module", "-e", script], text=True,
                                capture_output=True, check=False, cwd=ROOT / "evals" / "ui")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_documentation_and_evaluation_rows_render_actual_relations(self):
        script = """import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { DocumentationReader } from %s;
import { AssessmentRows, CoverageRows } from %s;
const documentation = renderToStaticMarkup(React.createElement(DocumentationReader, {parent: {id: 'ext-1', slug: 'ext', name: 'Ext', kind: 'skill', description: '', body: 'Stored body', entry_file: 'README.md', source: 'source-1', expand: {source: {id: 'source-1', name: 'Example source', url: 'https://example.test/source', publisher_kind: 'first-party', maintenance: 'active'}}}}));
assert.match(documentation, /Stored body/);
assert.match(documentation, /README.md/);
assert.ok(documentation.includes('https://example.test/source'));
for (const value of ['Example source', 'first-party', 'active']) assert.match(documentation, new RegExp(value));
assert.doesNotMatch(documentation, /href=\"source-1\"/);
assert.match(documentation, /#evaluations\\?extender=ext-1/);
const assessments = renderToStaticMarkup(React.createElement(AssessmentRows, {rows: [{id: 'a-1', framework: 'framework', element: 'element', extender: 'ext-1', verdict: 'pass', evidence: 'evidence', assessor: 'reviewer', eval_run: 'run-7', expand: {extender: {name: 'Named extender'}, framework: {name: 'Named framework'}, element: {name: 'Named element'}}}]}));
for (const value of ['Named extender', 'Named framework', 'Named element']) assert.match(assessments, new RegExp(value));
assert.match(assessments, /#performance\\?campaign=run-7/);
const coverage = renderToStaticMarkup(React.createElement(CoverageRows, {rows: [{id: 'c-1', job: 'job-id', eval_run: 'run-8', status: 'covered', disposition: 'accepted', rationale: 'current association', expand: {job: {id: 'job-id', name: 'Named job'}}}]}));
for (const value of ['job-id', 'Named job', 'run-8', 'covered', 'accepted', 'current association']) assert.match(coverage, new RegExp(value));
assert.doesNotMatch(coverage, /Job job-id/);
const fallback = renderToStaticMarkup(React.createElement(CoverageRows, {rows: [{id: 'c-2', job: 'fallback-id', status: '', disposition: '', rationale: ''}]}));
assert.match(fallback, /fallback-id/);
assert.match(coverage, /#performance\\?campaign=run-8/);
""" % (json.dumps((ROOT / "evals" / "ui" / "src" / "documentation.tsx").as_uri()), json.dumps((ROOT / "evals" / "ui" / "src" / "evaluations.tsx").as_uri()))
        result = subprocess.run(["bun", "--input-type=module", "-e", script], text=True,
                                capture_output=True, check=False, cwd=ROOT / "evals" / "ui")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
