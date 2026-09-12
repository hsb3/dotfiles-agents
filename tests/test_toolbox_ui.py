"""Focused behavioral checks for the no-dependency Toolbox adapter."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "evals" / "ui" / "app.js"


@unittest.skipUnless(shutil.which("node"), "Node is required for the browser-module adapter checks")
class ToolboxAdapterTests(unittest.TestCase):
    def run_module(self, body):
        script = """import assert from 'node:assert/strict';
import { active, api, collectPages, comparisonFields, fileUrl, pageRecords, text } from %s;
%s
""" % (json.dumps(APP.as_uri()), body)
        result = subprocess.run(["node", "--input-type=module", "-e", script], text=True,
                                capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_adapter_paginates_uses_exact_fields_and_handles_errors(self):
        self.run_module("""
let requests = [];
let page = 0;
const fetcher = async (url, options = {}) => {
  requests.push([url, options]); page += 1;
  return new Response(JSON.stringify({items: page === 1 ? [{id: 'one'}] : [{id: 'two'}], page, totalPages: 2}), {status: 200});
};
const fields = 'id,harness,campaign,candidate,case,config,model,passed,num_turns,cost_usd,duration_ms,error,ts,created';
const items = await collectPages('/api/collections/runs/records', fields, fetcher, 'plain-token');
assert.deepEqual(items.map((item) => item.id), ['one', 'two']);
assert.match(requests[0][0], new RegExp('fields=' + encodeURIComponent(fields)));
assert.equal(requests[0][1].headers.get('Authorization'), 'plain-token');
let tokenRequest;
await api('/api/files/token', {method: 'POST'}, async (url, options) => { tokenRequest = [url, options]; return new Response('{}'); }, 'plain-token');
assert.equal(tokenRequest[1].method, 'POST');
assert.equal(tokenRequest[1].headers.get('Authorization'), 'plain-token');
await assert.rejects(() => api('/bad', {}, async () => new Response('nope', {status: 403})), /403/);
""")

    def test_live_page_request_is_one_page_and_generation_guard_blocks_stale_results(self):
        self.run_module("""
let requests = [];
const fields = 'id,harness,campaign,candidate,case,config,model,passed,num_turns,cost_usd,duration_ms,error,ts,created';
const result = await pageRecords('/api/collections/runs/records', fields, 3, async (url, options) => {
  requests.push([url, options]); return new Response(JSON.stringify({items: [{id: 'three'}], page: 3, totalPages: 9}));
}, 'plain-token');
assert.equal(requests.length, 1);
assert.match(requests[0][0], /page=3/);
assert.match(requests[0][0], new RegExp('fields=' + encodeURIComponent(fields)));
assert.equal(result.totalPages, 9);
assert.equal(active(4, 4, 'token'), true);
assert.equal(active(4, 5, 'token'), false);
assert.equal(active(4, 4, ''), false);
assert.deepEqual(comparisonFields.map((entry) => entry[1]), ['campaign', 'candidate', 'case', 'harness', 'config', 'model', 'passed', 'num_turns', 'cost_usd', 'duration_ms', 'error', 'ts']);
""")

    def test_file_urls_are_encoded_and_unsafe_values_are_text_only(self):
        self.run_module("""
assert.equal(fileUrl({id: 'run /?', blob: 'evil name?.txt'}, 'short token'), '/api/files/artifacts/run%20%2F%3F/evil%20name%3F.txt?token=short%20token');
const node = {textContent: '', innerHTML: 'unchanged'};
text(node, '<img src=x onerror=alert(1)>');
assert.equal(node.textContent, '<img src=x onerror=alert(1)>');
assert.equal(node.innerHTML, 'unchanged');
""")
        source = APP.read_text()
        self.assertNotIn("innerHTML", source)
        self.assertIn("textContent", source)
        self.assertNotIn("localStorage", source)
        self.assertNotIn("URLSearchParams(location", source)
        self.assertIn('"/api/toolbox/catalog"', source)
        self.assertNotIn('"/toolbox-catalog.json"', source)
        self.assertIn("password.value = \"\"", source)
        self.assertIn("AbortController", source)
        self.assertNotIn("Concept A", (ROOT / "evals" / "ui" / "index.html").read_text())


if __name__ == "__main__":
    unittest.main()
