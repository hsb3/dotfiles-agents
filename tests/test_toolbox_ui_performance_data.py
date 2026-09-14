"""Behavioral contract for the Toolbox performance data adapter."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "evals" / "ui" / "src" / "performance-data.ts"


@unittest.skipUnless(shutil.which("bun"), "Bun is required for TypeScript module checks")
class PerformanceDataTests(unittest.TestCase):
    def run_module(self, body):
        script = """import assert from 'node:assert/strict';
import * as performance from %s;
%s
""" % (json.dumps(MODULE.as_uri()), body)
        result = subprocess.run(["bun", "--eval", script], text=True, capture_output=True,
                                check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_run_queries_escape_every_authorized_family_field_before_paging(self):
        self.run_module("""
const input = `a\\\\b'\\"c`;
const filter = performance.runSearchFilter(input, 'with');
for (const field of ['id', 'campaign', 'candidate', 'case', 'model', 'harness'])
  assert.match(filter, new RegExp(field + ' ~ '));
assert.match(filter, /config = 'with'/);
assert.match(filter, /a\\\\\\\\b\\\\'\\\\"c/);
assert.equal(performance.pageSize(25), 25);
assert.equal(performance.pageSize(50), 50);
assert.equal(performance.pageSize(99), 25);
let seen = '';
const session = { request: async (url) => { seen = url; return {kind: 'ok', data: {items: [], page: 1, totalPages: 1, totalItems: 0}}; } };
await performance.runs(session, {query: input, config: 'with', page: 2, perPage: 50, sort: '+duration_ms'});
const url = new URL('https://toolbox.test' + seen);
assert.equal(url.searchParams.get('page'), '2');
assert.equal(url.searchParams.get('perPage'), '50');
assert.equal(url.searchParams.get('sort'), '+duration_ms,+id');
assert.equal(url.searchParams.get('filter'), filter);
""")

    def test_known_metrics_sort_with_missing_last_and_a_stable_id_tie_breaker(self):
        self.run_module("""
const measured = (id, duration) => ({id, duration_ms: duration, measurement: {version: 1, available: {duration_ms: true}}});
const unknown = {id: 'z', duration_ms: 0, measurement: {version: 1, available: {duration_ms: false}}};
assert.deepEqual(performance.sortRuns([unknown, measured('b', 4), measured('a', 4), measured('c', 1)], 'duration_ms', 'asc').map((run) => run.id), ['c', 'a', 'b', 'z']);
assert.deepEqual(performance.sortRuns([unknown, measured('b', 4), measured('a', 4), measured('c', 1)], 'duration_ms', 'desc').map((run) => run.id), ['b', 'a', 'c', 'z']);
""")

    def test_evidence_collects_all_reference_pages_deduplicates_sha_and_reports_unknown_completeness(self):
        self.run_module("""
const calls = [];
const pages = {
  '/api/collections/artifacts/records': {items: [{id: 'direct', sha256: 'same', run: 'run-1', blob: 'direct.txt', byte_size: 0}], page: 1, totalPages: 1, totalItems: 1},
  '/api/collections/run_events/records': {items: [{id: 'event-1', artifact: 'from-event'}], page: 1, totalPages: 2, totalItems: 2},
  '/api/collections/run_events/records?page=2': {items: [{id: 'event-2', artifact: 'from-tool'}], page: 2, totalPages: 2, totalItems: 2},
  '/api/collections/tool_calls/records': {items: [{id: 'tool-1', artifact: 'from-event'}], page: 1, totalPages: 1, totalItems: 1},
};
const session = { request: async (url) => {
  calls.push(url);
  const key = url.includes('/run_events/') && url.includes('page=2') ? '/api/collections/run_events/records?page=2'
    : url.includes('/artifacts/records/direct') ? 'direct'
    : url.includes('/artifacts/records/from-event') ? 'from-event'
    : url.includes('/artifacts/records/from-tool') ? 'from-tool'
    : url.includes('/run_events/') ? '/api/collections/run_events/records'
    : url.includes('/tool_calls/') ? '/api/collections/tool_calls/records'
    : '/api/collections/artifacts/records';
  if (key === 'direct') return {kind: 'ok', data: pages['/api/collections/artifacts/records'].items[0]};
  if (key === 'from-event') return {kind: 'ok', data: {id: 'from-event', sha256: 'same', run: 'other', blob: 'copy.txt'}};
  if (key === 'from-tool') return {kind: 'ok', data: {id: 'from-tool', sha256: 'other', run: 'other', blob: 'tool.txt'}};
  return {kind: 'ok', data: pages[key]};
} };
const evidence = await performance.evidenceForRun(session, 'run-1');
assert.equal(evidence.kind, 'ok');
assert.equal(evidence.data.completeness, 'complete');
assert.deepEqual(evidence.data.artifacts.map((item) => item.id), ['direct', 'from-tool']);
assert.ok(calls.some((url) => url.includes('/run_events/') && url.includes('page=2')));
const failing = { request: async (url) => url.includes('/tool_calls/') ? {kind: 'error', status: 500, message: 'nope'} : session.request(url) };
const incomplete = await performance.evidenceForRun(failing, 'run-1');
assert.equal(incomplete.kind, 'ok');
assert.equal(incomplete.data.completeness, 'unknown');
assert.deepEqual(incomplete.data.artifacts.map((item) => item.id), ['direct']);
""")

    def test_file_urls_use_only_a_short_lived_file_token_and_unknown_size_stays_unavailable(self):
        self.run_module("""
const href = performance.protectedArtifactUrl({id: 'artifact/1', blob: 'proof name.txt'}, 'file-token');
assert.equal(href, '/api/files/artifacts/artifact%2F1/proof%20name.txt?token=file-token');
assert.ok(!href.includes('Authorization'));
assert.equal(performance.artifactByteSize({byte_size: 0}), 0);
assert.equal(performance.artifactByteSize({}), null);
assert.equal(performance.artifactByteSize({byte_size: -1}), null);
""")

    def test_typed_campaign_detail_uses_real_ids_prompts_raw_evidence_and_current_associations(self):
        self.run_module("""
let urls = [];
const session = {request: async (url) => { urls.push(url); return {kind: 'ok', data: {items: [], page: 1, totalPages: 1, totalItems: 0}}; }};
await performance.campaigns(session, 'fixture');
await performance.responsesForCampaign(session, 'campaign-id');
await performance.assessmentsForCampaign(session, 'campaign-id');
for (const needle of ['eval_runs', 'eval_responses', 'assessments', 'prompt', 'response_text', 'response_json', 'eval_run'])
  assert.ok(urls.join('\\n').includes(needle), needle);
""")


if __name__ == '__main__':
    unittest.main()
