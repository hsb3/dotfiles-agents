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
import { documentationFor, extenderById, pageRecords, pocketBaseLiteral, safeHref } from %s;
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
  return new Response('expired', {status: 403});
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

    def test_session_request_aborts_and_rejects_late_success(self):
        self.run_module("""
let resolve, signal;
const session = new Session(async (url, options = {}) => {
  if (url.endsWith('auth-with-password')) return new Response(JSON.stringify({token: 'memory-token'}));
  signal = options.signal;
  return new Promise((done) => { resolve = done; });
});
await session.login('a@example.test', 'secret');
const pending = session.request('/api/collections/files/records');
await Promise.resolve();
session.logout();
assert.equal(signal.aborted, true);
resolve(new Response(JSON.stringify({items: [{id: 'late'}]})));
const late = await pending;
assert.equal(late.kind, 'error');
assert.equal(session.token, '');
""")

    def test_stale_access_cannot_clear_a_newer_login(self):
        self.run_module("""
let resolve, logins = 0;
const session = new Session(async (url) => {
  if (url.endsWith('auth-with-password')) return new Response(JSON.stringify({token: 'token-' + ++logins}));
  return new Promise((done) => { resolve = done; });
});
await session.login('a@example.test', 'secret');
const pending = session.request('/api/collections/files/records');
await Promise.resolve();
await session.login('a@example.test', 'secret');
session.setSelection('fresh', ['record-2']);
resolve(new Response('expired', {status: 401}));
const late = await pending;
assert.equal(late.kind, 'error');
assert.equal(session.token, 'token-2');
assert.deepEqual(session.snapshot().selections, {fresh: ['record-2']});
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
const input = `a\\\\b'\"c`;
const result = await pageRecords(session, '/api/collections/files/records', {fields: 'id,extender,role,content,relpath', page: 2, filter: `extender = ${pocketBaseLiteral(input)}`, sort: '+relpath'});
assert.equal(result.kind, 'ok');
assert.match(seen[1][0], /filter=.*&sort=.*&fields=.*&page=2/);
assert.equal(new URL('https://toolbox.test' + seen[1][0]).searchParams.get('filter'), `extender = 'a\\\\\\\\b\\\\'\\\\"c'`);
assert.equal(new URL('https://toolbox.test' + seen[1][0]).searchParams.get('sort'), '+relpath,+id');
const docs = await documentationFor(session, 'ext-1');
assert.equal(docs.kind, 'ok');
assert.match(seen[2][0], /sort=%2Brelpath%2C%2Bid/);
const extender = await extenderById(session, 'ext-1');
assert.equal(extender.kind, 'ok');
assert.equal(new URL('https://toolbox.test' + seen[3][0]).searchParams.get('fields'), 'id,body,entry_file,source');
const file = await protectedFileToken(session);
assert.deepEqual(file, {kind: 'ok', token: 'short-lived'});
assert.equal(seen[4][0], '/api/files/token');
assert.equal(seen[4][1].headers.get('Authorization'), 'memory-token');
assert.equal(safeHref('https://example.test/source'), 'https://example.test/source');
assert.equal(safeHref('/documentation/ext-1'), '/documentation/ext-1');
for (const unsafe of ['javascript:alert(1)', 'data:text/html,x', '//example.test/x', 'https://user@example.test/x', 'not a url']) assert.equal(safeHref(unsafe), undefined);
for (const malformed of ['https:\\\\evil.example/x', 'http:\\\\evil.example/x', 'https:/evil.example/x']) assert.equal(safeHref(malformed), undefined);
""")

    def test_file_tokens_must_not_be_blank(self):
        self.run_module("""
const session = new Session(async (url) => new Response(JSON.stringify(url.endsWith('auth-with-password') ? {token: 'memory-token'} : {token: '   '})));
await session.login('a@example.test', 'secret');
const file = await protectedFileToken(session);
assert.deepEqual(file, {kind: 'error', status: 0, message: 'File token missing'});
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
