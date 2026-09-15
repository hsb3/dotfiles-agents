"""Production performance UI checks rendered through React's server renderer."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "evals" / "ui" / "src" / "performance.tsx"
VIEWS = ROOT / "evals" / "ui" / "src" / "views.tsx"
UI_DEPS = ROOT / "evals" / "ui" / "node_modules"
HAS_UI_DEPS = all((UI_DEPS / name).exists() for name in (
    "react", "react-dom", "@carbon/react", "@carbon/charts", "@carbon/charts-react",
))


@unittest.skipUnless(shutil.which("bun") and HAS_UI_DEPS, "Bun and UI production dependencies are required for React UI checks")
class PerformanceRuntimeHelpers(unittest.TestCase):
    def run_module(self, body):
        script = """import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import * as performance from %s;
import { parseRoute, Shell } from %s;
%s
""" % (json.dumps(MODULE.as_uri()), json.dumps(VIEWS.as_uri()), body)
        result = subprocess.run(["bun", "--no-install", "--input-type=module", "-e", script], text=True,
                                capture_output=True, check=False, cwd=ROOT / "evals" / "ui")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_v1_revision_validity_and_response_metrics_preserve_observed_zeroes(self):
        self.run_module("""
const v1 = {measurement: {version: 1, available: {tokens: true, duration_ms: true}, source_identity: {revision: {available: true, value: 'abc123'}}, execution: {validity: 'valid', reason: 'grade failed'}}};
assert.equal(performance.sourceRevision(v1), 'abc123');
assert.equal(performance.sourceRevision({measurement: {version: 1, source_identity: {revision: {available: false, value: 'secret'}}}}), null);
assert.deepEqual(performance.executionValidity(v1), {validity: 'valid', reason: 'grade failed'});
assert.deepEqual(performance.executionValidity({measurement: {version: 2, execution: {validity: 'valid'}}}), {validity: null, reason: null});
assert.deepEqual(performance.executionPreconditions({measurement: {version: 1, available: {}, execution: {preconditions: {fixture: 'local'}}}}), {fixture: 'local'});
assert.equal(performance.executionPreconditions({measurement: {version: 2, available: {}, execution: {preconditions: {fixture: 'unknown'}}}}), null);
assert.equal(performance.responseMetric({...v1, tokens: 0}, 'tokens'), 0);
assert.equal(performance.responseMetric({...v1, duration_ms: 0}, 'duration_ms'), 0);
assert.equal(performance.responseMetric({tokens: 0, measurement: {version: 1, available: {tokens: false}}}, 'tokens'), null);
""")

    def test_file_token_result_keeps_stale_and_error_states_distinct(self):
        self.run_module("""
assert.deepEqual(performance.fileTokenResult(false, {kind: 'ok', token: 'fresh'}), {state: 'stale'});
assert.deepEqual(performance.fileTokenResult(true, {kind: 'ok', token: 'fresh'}), {state: 'ready', token: 'fresh'});
assert.deepEqual(performance.fileTokenResult(true, {kind: 'access'}), {state: 'access'});
assert.deepEqual(performance.fileTokenResult(true, {kind: 'error'}), {state: 'error'});
const requests = new Map([['artifact-a', 1], ['artifact-b', 1]]);
assert.equal(performance.fileRequestIsCurrent(requests, 'artifact-a', 1), true);
requests.set('artifact-b', 2);
assert.equal(performance.fileRequestIsCurrent(requests, 'artifact-a', 1), true);
assert.equal(performance.fileRequestIsCurrent(requests, 'artifact-b', 1), false);
""")

    def test_routes_selection_list_state_and_signed_exit_status_follow_production_rules(self):
        self.run_module("""
assert.equal(parseRoute('#performance?run=run-1'), 'performance');
assert.equal(parseRoute('#main-content', 'documentation'), 'documentation');
const first = {id: 'first'}; const second = {id: 'second'}; const third = {id: 'third'};
assert.deepEqual(performance.nextSelection([first], second), [first, second]);
assert.deepEqual(performance.nextSelection([first, second], third), [first, second]);
assert.deepEqual(performance.nextSelection([first, second], first), [second]);
const state = {page: 3, campaignPage: 4, focus: null};
assert.deepEqual(performance.performanceListState(state, 'runs-changed'), {page: 1, campaignPage: 4, focus: null});
assert.deepEqual(performance.performanceListState(state, 'campaigns-changed'), {page: 3, campaignPage: 1, focus: null});
assert.deepEqual(performance.performanceListState(state, 'return-runs'), {page: 3, campaignPage: 4, focus: 'runs'});
assert.equal(performance.exitStatus({exit_code: -9, measurement: {version: 1, available: {exit_code: true}}}), -9);
assert.equal(performance.exitStatus({exit_code: -9, measurement: {version: 1, available: {exit_code: false}}}), null);
""")

    def test_shell_exposes_a_navigation_control_and_all_route_links(self):
        self.run_module("""
const html = renderToStaticMarkup(React.createElement(Shell, {route: 'home', logout: () => {}}, React.createElement('p', null, 'Content')));
assert.match(html, /aria-label="Open navigation"/);
for (const route of ['home', 'catalog', 'documentation', 'performance', 'evaluations']) assert.match(html, new RegExp(`href="\\#${route}"`));
""")

    def test_tool_records_hide_raw_wallclock_without_a_measurement_envelope(self):
        self.run_module("""
const html = renderToStaticMarkup(React.createElement(performance.ToolRecords, {result: {state: 'populated', data: {items: [{id: 'tool-1', run: 'run-1', tool_call_id: 'call-1', tool_name: 'Read', wallclock_ms: 0}], totalItems: 1}}, page: 1, setPage: () => {}}));
assert.match(html, /Timing/);
assert.match(html, /<td[^>]*>Unavailable<\\/td>/);
assert.doesNotMatch(html, /<td[^>]*>0<\\/td>/);
""")

    def test_comparison_renders_tiny_observed_costs_and_difference(self):
        self.run_module("""
const observation = (id, config, cost_usd) => ({id, config, campaign: 'campaign-1', candidate: 'candidate-1', case: 'case-1', harness: 'harness-1', model: 'model-1', duration_ms: 1, cost_usd, measurement: {version: 1, available: {duration_ms: true, cost_usd: true}, execution: {validity: 'valid'}}});
const html = renderToStaticMarkup(React.createElement(performance.Comparison, {selected: [observation('baseline', 'baseline', 0.000001), observation('with', 'with', 0.000002)]}));
for (const text of ['Duration', 'Cost', '1.00e-6 USD', '2.00e-6 USD', '(100%)']) assert.ok(html.includes(text), text);
assert.ok(html.includes('With minus baseline'));
""")


if __name__ == "__main__":
    unittest.main()
