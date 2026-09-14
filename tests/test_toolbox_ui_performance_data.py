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
assert.deepEqual(performance.sortRuns([unknown, measured('b', 4), measured('a', 4), measured('c', 1)], 'duration_ms', 'desc').map((run) => run.id), ['a', 'b', 'c', 'z']);
""")

    def test_metric_sort_collects_the_family_before_slicing_away_legacy_zeroes(self):
        self.run_module("""
const known = Array.from({length: 25}, (_, index) => ({
  id: 'known-' + String(index).padStart(2, '0'), duration_ms: index,
  measurement: {version: 1, available: {duration_ms: true}},
}));
const legacy = {id: 'legacy-zero', duration_ms: 0, measurement: {version: 1, available: {duration_ms: false}}};
const seen = [];
const session = {request: async (url) => {
  seen.push(url);
  const page = Number(new URL('https://toolbox.test' + url).searchParams.get('page'));
  return {kind: 'ok', data: {
    items: page === 1 ? [legacy, ...known.slice(0, 24)] : [known[24]],
    page, totalPages: 2, totalItems: 26,
  }};
}};
const first = await performance.runs(session, {page: 1, perPage: 25, metricSort: {metric: 'duration_ms', direction: 'asc'}});
const second = await performance.runs(session, {page: 2, perPage: 25, metricSort: {metric: 'duration_ms', direction: 'asc'}});
assert.equal(first.kind, 'ok');
assert.deepEqual(first.data.items.map((run) => run.id), known.map((run) => run.id));
assert.equal(first.data.totalItems, 26);
assert.equal(first.data.totalPages, 2);
assert.equal(second.kind, 'ok');
assert.deepEqual(second.data.items.map((run) => run.id), ['legacy-zero']);
for (const url of seen) assert.equal(new URL('https://toolbox.test' + url).searchParams.get('sort'), '+id');
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
assert.deepEqual(incomplete.data.artifacts.map((item) => item.id), ['direct', 'from-tool']);
""")

    def test_evidence_propagates_the_first_owned_artifact_page_failure(self):
        self.run_module("""
for (const failure of [
  {kind: 'access', status: 403},
  {kind: 'error', status: 500, message: 'artifacts failed'},
]) {
  const session = {request: async (url) => {
    if (url.includes('/artifacts/records?')) return failure;
    throw new Error('unexpected request: ' + url);
  }};
  assert.equal(await performance.evidenceForRun(session, 'run-1'), failure);
}
""")

    def test_evidence_keeps_first_owned_artifacts_when_a_later_owned_page_fails(self):
        self.run_module("""
const session = {request: async (url) => {
  if (url.includes('/artifacts/records?') && url.includes('page=2'))
    return {kind: 'error', status: 500, message: 'second page failed'};
  if (url.includes('/artifacts/records?'))
    return {kind: 'ok', data: {items: [{id: 'owned', sha256: 'owned', run: 'run-1'}], page: 1, totalPages: 2, totalItems: 2}};
  if (url.includes('/run_events/') || url.includes('/tool_calls/'))
    return {kind: 'ok', data: {items: [], page: 1, totalPages: 1, totalItems: 0}};
  throw new Error('unexpected request: ' + url);
}};
const result = await performance.evidenceForRun(session, 'run-1');
assert.equal(result.kind, 'ok');
assert.equal(result.data.completeness, 'unknown');
assert.deepEqual(result.data.artifacts.map((item) => item.id), ['owned']);
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

    def test_evidence_keeps_successful_references_when_the_sibling_family_or_lookup_fails(self):
        self.run_module("""
const page = (items) => ({kind: 'ok', data: {items, page: 1, totalPages: 1, totalItems: items.length}});
const owned = {id: 'owned', sha256: 'owned', run: 'run-1', blob: 'owned.txt'};
const partialFamily = {request: async (url) => {
  if (url.includes('/artifacts/records/event-ref')) return {kind: 'ok', data: {id: 'event-ref', sha256: 'event', run: 'other', blob: 'event.txt'}};
  if (url.includes('/artifacts/records?')) return page([owned]);
  if (url.includes('/run_events/')) return page([{id: 'event', run: 'run-1', artifact: 'event-ref'}]);
  if (url.includes('/tool_calls/')) return {kind: 'error', status: 500, message: 'tools failed'};
  throw new Error(url);
}};
const familyResult = await performance.evidenceForRun(partialFamily, 'run-1');
assert.equal(familyResult.kind, 'ok');
assert.equal(familyResult.data.completeness, 'unknown');
assert.deepEqual(familyResult.data.artifacts.map((item) => item.id), ['owned', 'event-ref']);
const partialLookup = {request: async (url) => {
  if (url.includes('/artifacts/records/missing')) return {kind: 'error', status: 500, message: 'missing'};
  if (url.includes('/artifacts/records/good')) return {kind: 'ok', data: {id: 'good', sha256: 'good', run: 'other', blob: 'good.txt'}};
  if (url.includes('/artifacts/records?')) return page([owned]);
  if (url.includes('/run_events/')) return page([{id: 'event', run: 'run-1', artifact: 'missing'}]);
  if (url.includes('/tool_calls/')) return page([{id: 'tool', run: 'run-1', artifact: 'good'}]);
  throw new Error(url);
}};
const lookupResult = await performance.evidenceForRun(partialLookup, 'run-1');
assert.equal(lookupResult.kind, 'ok');
assert.equal(lookupResult.data.completeness, 'unknown');
assert.deepEqual(lookupResult.data.artifacts.map((item) => item.id), ['owned', 'good']);
""")

    def test_evidence_keeps_page_one_references_when_a_later_event_page_fails(self):
        self.run_module("""
const page = (items, page, totalPages) => ({kind: 'ok', data: {items, page, totalPages, totalItems: items.length}});
const session = {request: async (url) => {
  if (url.includes('/artifacts/records/event-ref')) return {kind: 'ok', data: {id: 'event-ref', sha256: 'event', run: 'other', blob: 'event.txt'}};
  if (url.includes('/artifacts/records?')) return page([{id: 'owned', sha256: 'owned', run: 'run-1', blob: 'owned.txt'}], 1, 1);
  if (url.includes('/run_events/') && url.includes('page=2')) return {kind: 'error', status: 500, message: 'second page failed'};
  if (url.includes('/run_events/')) return page([{id: 'event', run: 'run-1', artifact: 'event-ref'}], 1, 2);
  if (url.includes('/tool_calls/')) return page([], 1, 1);
  throw new Error(url);
}};
const result = await performance.evidenceForRun(session, 'run-1');
assert.equal(result.kind, 'ok');
assert.equal(result.data.completeness, 'unknown');
assert.deepEqual(result.data.artifacts.map((item) => item.id), ['owned', 'event-ref']);
""")

    def test_campaign_detail_uses_exact_escaped_relation_filters(self):
        self.run_module("""
let urls = [];
const session = {request: async (url) => { urls.push(url); return {kind: 'ok', data: {items: [], page: 1, totalPages: 1, totalItems: 0}}; }};
const campaign = 'campaign\\\\id\\'\"';
await performance.campaigns(session, campaign);
await performance.responsesForCampaign(session, campaign);
await performance.assessmentsForCampaign(session, campaign);
const parsed = urls.map((url) => new URL('https://toolbox.test' + url));
assert.equal(parsed[1].searchParams.get('filter'), 'run = \\'campaign\\\\\\\\id\\\\\\'\\\\\"\\'');
assert.equal(parsed[2].searchParams.get('filter'), 'eval_run = \\'campaign\\\\\\\\id\\\\\\'\\\\\"\\'');
assert.ok(parsed[1].searchParams.get('fields').includes('prompt,response_text,response_json'));
assert.ok(parsed[1].searchParams.get('fields').includes('tokens,duration_ms,measurement'));
assert.equal(parsed[2].searchParams.get('expand'), 'extender,framework,element');
assert.equal(parsed[2].searchParams.get('fields'), 'id,extender,framework,element,eval_run,verdict,score,evidence,assessor,expand.extender.id,expand.extender.name,expand.framework.id,expand.framework.name,expand.element.id,expand.element.name,created,updated');
""")


if __name__ == '__main__':
    unittest.main()
