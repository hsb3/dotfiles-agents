"""Runnable checks for the TypeScript Toolbox API adapter."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "evals" / "ui" / "src" / "api.ts"
DATA = ROOT / "evals" / "ui" / "src" / "data.ts"


@unittest.skipUnless(shutil.which("bun"), "Bun is required for TypeScript adapter checks")
class ToolboxUiAdapterTests(unittest.TestCase):
    def run_module(self, body):
        script = """import assert from 'node:assert/strict';
import { Session, login, protectedFileToken, request } from %s;
import { pageRecords, pocketBaseLiteral } from %s;
%s
""" % (json.dumps(API.as_uri()), json.dumps(DATA.as_uri()), body)
        result = subprocess.run(
            ["bun", "--input-type=module", "-e", script], text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_auth_and_expiry_keep_private_state_in_memory(self):
        self.run_module("""
let calls = [];
const fetcher = async (url, options = {}) => {
  calls.push([url, options]);
  if (url.endsWith('auth-with-password')) return new Response(JSON.stringify({token: 'memory-token'}));
  return new Response('expired', {status: 401});
};
const session = new Session(fetcher);
assert.equal((await login('a@example.test', 'secret', fetcher)).kind, 'ok');
await session.login('a@example.test', 'secret');
session.setSelection('runs', ['run-1']);
session.setLoaded('catalog', {id: 'catalog'});
const expired = await session.request('/api/collections/runs/records');
assert.equal(expired.kind, 'access');
assert.equal(session.token, '');
assert.deepEqual(session.snapshot(), {selections: {}, loaded: {}});
assert.equal(calls[0][0], '/api/collections/users/auth-with-password');
assert.equal(JSON.parse(calls[0][1].body).password, 'secret');
assert.equal(calls[2][1].headers.get('Authorization'), 'memory-token');
""")

    def test_filters_escape_before_pagination_and_file_tokens_stay_out_of_urls(self):
        self.run_module("""
let seen = [];
const fetcher = async (url, options = {}) => {
  seen.push([url, options]);
  return new Response(JSON.stringify(url.endsWith('auth-with-password') ? {token: 'memory-token'} : url === '/api/files/token' ? {token: 'short-lived'} : {items: []}));
};
const session = new Session(fetcher);
await session.login('a@example.test', 'secret');
const result = await pageRecords('/api/collections/files/records', {fields: 'id,extender,role,content,relpath', page: 2, filter: `extender = ${pocketBaseLiteral(`a\\\\b'\"c`)}`, sort: '+relpath', token: session.token, fetcher});
assert.equal(result.kind, 'ok');
assert.match(seen[1][0], /filter=.*&sort=.*&fields=.*&page=2/);
assert.match(seen[1][0], /%5C%5C/);
assert.match(seen[1][0], /%27/);
assert.match(seen[1][0], /%22/);
const file = await protectedFileToken(session);
assert.deepEqual(file, {kind: 'ok', token: 'short-lived'});
assert.equal(seen[2][0], '/api/files/token');
assert.equal(seen[2][1].headers.get('Authorization'), 'memory-token');
""")

    def test_late_response_cannot_restore_cleared_state(self):
        self.run_module("""
let resolve;
const session = new Session(async () => new Response(JSON.stringify({token: 'memory-token'})));
await session.login('a@example.test', 'secret');
const pending = session.load('runs', () => new Promise((done) => { resolve = done; }));
session.logout();
resolve([{id: 'late'}]);
assert.equal(await pending, undefined);
assert.deepEqual(session.snapshot(), {selections: {}, loaded: {}});
""")


if __name__ == "__main__":
    unittest.main()
