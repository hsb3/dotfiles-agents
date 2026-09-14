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

    def test_active_403_preserves_the_session(self):
        self.run_module("""
const session = new Session(async (url) =>
  new Response(JSON.stringify(url.endsWith('auth-with-password') ? {token: 'memory-token'} : {message: 'forbidden'}), {
    status: url.endsWith('auth-with-password') ? 200 : 403,
  }),
);
await session.login('a@example.test', 'secret');
session.setSelection('runs', ['run-1']);
session.setLoaded('catalog', {id: 'catalog'});
const denied = await session.request('/api/collections/files/records');
assert.deepEqual(denied, {kind: 'access', status: 403});
assert.equal(session.token, 'memory-token');
assert.deepEqual(session.snapshot(), {selections: {runs: ['run-1']}, loaded: {catalog: {id: 'catalog'}}});
""")

    def test_jwt_expiry_clears_only_its_generation(self):
        self.run_module("""
const timers = [];
const clock = {
  now: () => 1_000,
  setTimeout: (callback, delay) => { const timer = {callback, delay, cancelled: false}; timers.push(timer); return timer; },
  clearTimeout: (timer) => { timer.cancelled = true; },
};
const token = (exp) => 'header.' + btoa(JSON.stringify({exp})).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '') + '.signature';
let login = 0;
const session = new Session(async () => new Response(JSON.stringify({token: token(login++ ? 20 : 2)})), clock);
await session.login('a@example.test', 'secret');
assert.equal(timers[0].delay, 1_000);
await session.login('a@example.test', 'secret');
session.setSelection('fresh', ['record-2']);
assert.equal(timers[0].cancelled, true);
timers[0].callback();
assert.equal(session.token, token(20));
assert.deepEqual(session.snapshot().selections, {fresh: ['record-2']});
timers[1].callback();
assert.equal(session.token, '');
assert.deepEqual(session.snapshot(), {selections: {}, loaded: {}});
""")

    def test_immediately_expired_jwt_login_is_not_successful(self):
        self.run_module("""
const token = 'header.' + btoa(JSON.stringify({exp: 1})).replaceAll('=', '') + '.signature';
const clock = {now: () => 1_000, setTimeout: () => { throw new Error('expired token must not schedule'); }, clearTimeout: () => {}};
const session = new Session(async () => new Response(JSON.stringify({token})), clock);
const result = await session.login('a@example.test', 'secret');
assert.equal(result.kind, 'error');
assert.equal(session.token, '');
assert.deepEqual(session.snapshot(), {selections: {}, loaded: {}});
""")

    def test_default_clock_keeps_native_timer_receiver_for_login_and_logout(self):
        script = """import assert from 'node:assert/strict';
const nativeSetTimeout = globalThis.setTimeout;
const nativeClearTimeout = globalThis.clearTimeout;
let setCalls = 0; let clearCalls = 0;
globalThis.setTimeout = function(callback, delay) {
  assert.equal(this, globalThis);
  setCalls += 1;
  return nativeSetTimeout(callback, delay);
};
globalThis.clearTimeout = function(timer) {
  assert.equal(this, globalThis);
  clearCalls += 1;
  return nativeClearTimeout(timer);
};
try {
  const { Session } = await import(%s + '?native-timer-receiver');
  const token = 'header.' + btoa(JSON.stringify({exp: Math.floor(Date.now() / 1_000) + 60})).replaceAll('=', '') + '.signature';
  const session = new Session(async () => new Response(JSON.stringify({token})));
  assert.equal((await session.login('a@example.test', 'secret')).kind, 'ok');
  session.logout();
  assert.equal(setCalls, 1);
  assert.equal(clearCalls, 1);
} finally {
  globalThis.setTimeout = nativeSetTimeout;
  globalThis.clearTimeout = nativeClearTimeout;
}
""" % json.dumps(API.as_uri())
        result = subprocess.run(
            ["bun", "--no-install", "--input-type=module", "-e", script], text=True,
            capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_clear_subscribers_observe_only_effective_clears(self):
        self.run_module("""
const timers = [];
const clock = {
  now: () => 1_000,
  setTimeout: (callback, delay) => { const timer = {callback, delay, cancelled: false}; timers.push(timer); return timer; },
  clearTimeout: (timer) => { timer.cancelled = true; },
};
const token = 'header.' + btoa(JSON.stringify({exp: 2})).replaceAll('=', '') + '.signature';
const session = new Session(async () => new Response(JSON.stringify({token})), clock);
const observed = [];
session.subscribe(() => observed.push([session.token, session.snapshot()]));
await session.login('a@example.test', 'secret');
session.setLoaded('catalog', {id: 'catalog'});
timers[0].callback();
assert.deepEqual(observed, [['', {selections: {}, loaded: {}}]]);
const denied = new Session(async (url) => new Response(JSON.stringify(url.endsWith('auth-with-password') ? {token: 'memory-token'} : {}), {status: url.endsWith('auth-with-password') ? 200 : 403}));
let forbiddenCalls = 0;
denied.subscribe(() => forbiddenCalls++);
await denied.login('a@example.test', 'secret');
await denied.request('/api/collections/files/records');
assert.equal(forbiddenCalls, 0);
const unsubscribed = new Session(async () => new Response(JSON.stringify({token: 'memory-token'})));
let calls = 0;
const unsubscribe = unsubscribed.subscribe(() => calls++);
unsubscribe();
await unsubscribed.login('a@example.test', 'secret');
unsubscribed.logout();
assert.equal(calls, 0);
const staleTimers = [];
const staleClock = {now: () => 1_000, setTimeout: (callback, delay) => { const timer = {callback, delay}; staleTimers.push(timer); return timer; }, clearTimeout: () => {}};
let staleLogin = 0;
const expiring = new Session(async () => new Response(JSON.stringify({token: 'header.' + btoa(JSON.stringify({exp: staleLogin++ ? 20 : 2})).replaceAll('=', '') + '.signature'})), staleClock);
await expiring.login('a@example.test', 'secret');
await expiring.login('a@example.test', 'secret');
let staleTimerCalls = 0;
expiring.subscribe(() => staleTimerCalls++);
staleTimers[0].callback();
assert.equal(staleTimerCalls, 0);
let resolve, attempts = 0;
const staleResponse = new Session(async (url) => url.endsWith('auth-with-password')
  ? new Response(JSON.stringify({token: 'token-' + ++attempts}))
  : new Promise((done) => { resolve = done; }));
await staleResponse.login('a@example.test', 'secret');
const pending = staleResponse.request('/api/collections/files/records');
await Promise.resolve();
await staleResponse.login('a@example.test', 'secret');
let staleResponseCalls = 0;
staleResponse.subscribe(() => staleResponseCalls++);
resolve(new Response('expired', {status: 401}));
await pending;
assert.equal(staleResponseCalls, 0);
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
