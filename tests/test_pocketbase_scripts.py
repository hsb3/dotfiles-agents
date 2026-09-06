"""Unit coverage for the pocketbase skill's operator scripts.

These scripts sit between an agent and a live database, so what is pinned here is the
shape of every request they build, the branch they take when the server says no, and
where configuration comes from when two sources disagree. Every HTTP boundary is stubbed
at urlopen; nothing here reaches a server.

One trap the tests encode: the config-resolution class reloads pb_config, which mints a
new PBRequestError class object. Anything that imported the old one by value still
catches only that one, so a test always raises the error class *through the module under
test* (pb_auth.PBRequestError, not pb_config.PBRequestError).
"""

import contextlib
import importlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
from email.message import Message
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "primitives-core", "skills", "pocketbase")
SCRIPTS = os.path.join(SKILL, "scripts")

sys.path.insert(0, SCRIPTS)

import pb_config  # noqa: E402
import pb_auth  # noqa: E402
import pb_backups  # noqa: E402
import pb_collections  # noqa: E402
import pb_create_migration  # noqa: E402
import pb_e2e_helpers  # noqa: E402
import pb_health  # noqa: E402
import pb_records  # noqa: E402

SCRIPT_FILES = (
    "pb_auth.py", "pb_backups.py", "pb_collections.py", "pb_config.py",
    "pb_create_migration.py", "pb_e2e_helpers.py", "pb_health.py", "pb_records.py",
)


class FakeResponse:
    """Stand-in for the urlopen context manager."""

    def __init__(self, status=200, body=b"{}"):
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


def http_error(code, body=b"{}"):
    return urllib.error.HTTPError(
        "http://pb.test/api/x", code, "err", Message(), io.BytesIO(body))


@contextlib.contextmanager
def captured():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def payloads(text):
    """Every JSON object printed to stdout, in order (scripts interleave plain lines)."""
    decoder = json.JSONDecoder()
    found, i = [], 0
    while True:
        start = text.find("{", i)
        if start < 0:
            return found
        try:
            obj, end = decoder.raw_decode(text, start)
        except ValueError:
            i = start + 1
            continue
        found.append(obj)
        i = end


def run_main(module, argv):
    """Invoke a script's main() with a synthetic argv. Callers own the stdout capture."""
    with patch.object(sys, "argv", [module.__name__ + ".py"] + argv):
        module.main()


class ConfigResolution(unittest.TestCase):
    """Env beats .env, .env beats the default, and .env never clobbers a live env var."""

    def setUp(self):
        self.origin = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(self._restore)

    def _restore(self):
        # Leave pb_config on its documented defaults, not on whatever a test set.
        self._reload(self.tmp, {})
        os.chdir(self.origin)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _reload(self, cwd, env):
        with patch.dict(os.environ, env, clear=True):
            os.chdir(cwd)
            importlib.reload(pb_config)

    def _write_env(self, directory, text):
        with open(os.path.join(directory, ".env"), "w") as handle:
            handle.write(text)

    def test_defaults_apply_with_no_env_file_and_no_variables(self):
        self._reload(self.tmp, {})
        self.assertEqual(pb_config.PB_URL, "http://127.0.0.1:8090")
        self.assertEqual(pb_config.PB_SUPERUSER_EMAIL, "")
        self.assertEqual(pb_config.PB_SUPERUSER_PASSWORD, "")

    def test_env_file_supplies_values_and_trailing_slash_is_stripped(self):
        self._write_env(self.tmp, "PB_URL=http://pb.example:8090/\nPB_SUPERUSER_EMAIL=a@b.c\n")
        self._reload(self.tmp, {})
        self.assertEqual(pb_config.PB_URL, "http://pb.example:8090")
        self.assertEqual(pb_config.PB_SUPERUSER_EMAIL, "a@b.c")

    def test_environment_wins_over_env_file(self):
        self._write_env(self.tmp, "PB_URL=http://from-file\nPB_SUPERUSER_EMAIL=file@x.y\n")
        self._reload(self.tmp, {"PB_URL": "http://from-env", "PB_SUPERUSER_EMAIL": "env@x.y"})
        self.assertEqual(pb_config.PB_URL, "http://from-env")
        self.assertEqual(pb_config.PB_SUPERUSER_EMAIL, "env@x.y")

    def test_env_file_is_found_by_walking_up_from_a_subdirectory(self):
        nested = os.path.join(self.tmp, "a", "b")
        os.makedirs(nested)
        self._write_env(self.tmp, "PB_URL=http://parent-dir\n")
        self._reload(nested, {})
        self.assertEqual(pb_config.PB_URL, "http://parent-dir")

    def test_env_file_parser_skips_comments_blanks_and_strips_quotes(self):
        self._write_env(self.tmp, "\n".join([
            "# a comment",
            "",
            "NOT_A_PAIR",
            'PB_URL="http://quoted"  ',
            "PB_SUPERUSER_PASSWORD='pw with spaces'",
        ]))
        self._reload(self.tmp, {})
        self.assertEqual(pb_config.PB_URL, "http://quoted")
        self.assertEqual(pb_config.PB_SUPERUSER_PASSWORD, "pw with spaces")


class RequestConstruction(unittest.TestCase):
    """What pb_request actually puts on the wire."""

    def setUp(self):
        pb_config._cached_token = None
        self.addCleanup(setattr, pb_config, "_cached_token", None)
        patcher = patch.object(pb_config, "PB_URL", "http://pb.test")
        patcher.start()
        self.addCleanup(patcher.stop)

    def _error(self, code, body=b"{}"):
        # HTTPError holds an open fp; leaving it to the GC prints a ResourceWarning.
        error = http_error(code, body)
        self.addCleanup(error.close)
        return error

    def _send(self, *args, **kwargs):
        response = kwargs.pop("response", FakeResponse(200, b'{"ok":true}'))
        with patch("urllib.request.urlopen", return_value=response) as opened:
            result = pb_config.pb_request(*args, **kwargs)
        return opened.call_args[0][0], result

    def test_leading_slash_path_is_appended_to_the_base_url(self):
        request, _ = self._send("GET", "/api/health")
        self.assertEqual(request.full_url, "http://pb.test/api/health")

    def test_path_without_leading_slash_gets_a_separator(self):
        request, _ = self._send("GET", "api/health")
        self.assertEqual(request.full_url, "http://pb.test/api/health")

    def test_method_and_json_body_are_carried_through(self):
        request, _ = self._send("PATCH", "/api/x", data={"title": "hi"})
        self.assertEqual(request.get_method(), "PATCH")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"title": "hi"})

    def test_no_body_is_sent_when_data_is_omitted(self):
        request, _ = self._send("GET", "/api/health")
        self.assertIsNone(request.data)

    def test_content_type_is_always_set_and_token_becomes_a_raw_authorization_header(self):
        request, _ = self._send("POST", "/api/x", data={}, token="TOKEN123")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(request.get_header("Authorization"), "TOKEN123")

    def test_no_authorization_header_without_a_token(self):
        request, _ = self._send("GET", "/api/health")
        self.assertIsNone(request.get_header("Authorization"))

    def test_parsed_json_is_returned_by_default(self):
        _, result = self._send("GET", "/api/health")
        self.assertEqual(result, {"ok": True})

    def test_raw_response_returns_a_status_pair(self):
        _, result = self._send("GET", "/api/health", raw_response=True,
                               response=FakeResponse(201, b'{"id":"r1"}'))
        self.assertEqual(result, (201, {"id": "r1"}))

    def test_empty_body_parses_to_none(self):
        _, result = self._send("DELETE", "/api/x", raw_response=True,
                               response=FakeResponse(204, b""))
        self.assertEqual(result, (204, None))

    def test_http_error_raises_with_status_and_parsed_body(self):
        with patch("urllib.request.urlopen",
                   side_effect=self._error(404, b'{"message":"missing"}')):
            with self.assertRaises(pb_config.PBRequestError) as caught:
                pb_config.pb_request("GET", "/api/x")
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(caught.exception.data, {"message": "missing"})

    def test_http_error_with_raw_response_returns_instead_of_raising(self):
        with patch("urllib.request.urlopen",
                   side_effect=self._error(403, b'{"message":"nope"}')):
            result = pb_config.pb_request("GET", "/api/x", raw_response=True)
        self.assertEqual(result, (403, {"message": "nope"}))

    def test_unparseable_error_body_falls_back_to_the_exception_text(self):
        with patch("urllib.request.urlopen", side_effect=self._error(500, b"<html>")):
            with self.assertRaises(pb_config.PBRequestError) as caught:
                pb_config.pb_request("GET", "/api/x")
        self.assertIn("message", caught.exception.data)
        self.assertIn("500", caught.exception.data["message"])


class SuperuserToken(unittest.TestCase):
    """Caching, forced refresh, and the two ways authentication gives up."""

    def setUp(self):
        pb_config._cached_token = None
        self.addCleanup(setattr, pb_config, "_cached_token", None)
        for name, value in (("PB_SUPERUSER_EMAIL", "su@x.y"),
                            ("PB_SUPERUSER_PASSWORD", "pw")):
            patcher = patch.object(pb_config, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_credentials_are_posted_to_the_superusers_collection(self):
        with patch.object(pb_config, "pb_request", return_value={"token": "T1"}) as sent:
            self.assertEqual(pb_config.get_superuser_token(), "T1")
        self.assertEqual(sent.call_args[0][0], "POST")
        self.assertEqual(sent.call_args[0][1],
                         "/api/collections/_superusers/auth-with-password")
        self.assertEqual(sent.call_args[0][2], {"identity": "su@x.y", "password": "pw"})

    def test_second_call_uses_the_cache(self):
        with patch.object(pb_config, "pb_request", return_value={"token": "T1"}) as sent:
            pb_config.get_superuser_token()
            pb_config.get_superuser_token()
        self.assertEqual(sent.call_count, 1)

    def test_force_bypasses_the_cache(self):
        with patch.object(pb_config, "pb_request",
                          side_effect=[{"token": "T1"}, {"token": "T2"}]) as sent:
            pb_config.get_superuser_token()
            self.assertEqual(pb_config.get_superuser_token(force=True), "T2")
        self.assertEqual(sent.call_count, 2)

    def test_missing_credentials_exit_without_a_request(self):
        with patch.object(pb_config, "PB_SUPERUSER_PASSWORD", ""), \
                patch.object(pb_config, "pb_request") as sent, captured() as buf:
            with self.assertRaises(SystemExit) as caught:
                pb_config.get_superuser_token()
        self.assertEqual(caught.exception.code, 1)
        sent.assert_not_called()
        self.assertIn("must be set", payloads(buf.getvalue())[0]["data"]["message"])

    def test_rejected_credentials_exit_with_the_server_status(self):
        error = pb_config.PBRequestError(400, {"message": "bad"})
        with patch.object(pb_config, "pb_request", side_effect=error), captured() as buf:
            with self.assertRaises(SystemExit):
                pb_config.get_superuser_token()
        payload = payloads(buf.getvalue())[0]
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], 400)


class AuthedRequestRetry(unittest.TestCase):
    """A 401 buys exactly one forced re-auth; anything else propagates."""

    def setUp(self):
        pb_config._cached_token = None
        self.addCleanup(setattr, pb_config, "_cached_token", None)

    def test_success_passes_the_cached_token(self):
        with patch.object(pb_config, "get_superuser_token", return_value="T1"), \
                patch.object(pb_config, "pb_request", return_value={"ok": 1}) as sent:
            self.assertEqual(pb_config.pb_authed_request("GET", "/api/x"), {"ok": 1})
        self.assertEqual(sent.call_args[1]["token"], "T1")

    def test_401_retries_once_with_a_forced_fresh_token(self):
        error = pb_config.PBRequestError(401, {"message": "expired"})
        with patch.object(pb_config, "get_superuser_token",
                          side_effect=["T1", "T2"]) as token, \
                patch.object(pb_config, "pb_request",
                             side_effect=[error, {"ok": 1}]) as sent:
            result = pb_config.pb_authed_request("GET", "/api/x")
        self.assertEqual(result, {"ok": 1})
        self.assertEqual(sent.call_count, 2)
        self.assertEqual(sent.call_args[1]["token"], "T2")
        self.assertEqual(token.call_args[1], {"force": True})

    def test_non_401_error_is_not_retried(self):
        error = pb_config.PBRequestError(403, {"message": "forbidden"})
        with patch.object(pb_config, "get_superuser_token", return_value="T1"), \
                patch.object(pb_config, "pb_request", side_effect=error) as sent:
            with self.assertRaises(pb_config.PBRequestError):
                pb_config.pb_authed_request("GET", "/api/x")
        self.assertEqual(sent.call_count, 1)

    def test_print_result_emits_the_agreed_envelope(self):
        with captured() as buf:
            pb_config.print_result(True, 204, {"message": "done"})
        self.assertEqual(json.loads(buf.getvalue()),
                         {"success": True, "status": 204, "data": {"message": "done"}})


class AuthScript(unittest.TestCase):
    """pb_auth routes between user auth and superuser auth."""

    def test_user_collection_routes_to_auth_user(self):
        with patch.object(pb_auth, "auth_user") as routed, captured():
            run_main(pb_auth, ["--collection", "users", "--identity", "a@b.c",
                               "--password", "pw"])
        routed.assert_called_once_with("users", "a@b.c", "pw")

    def test_no_collection_routes_to_forced_superuser_auth(self):
        with patch.object(pb_auth, "get_superuser_token", return_value="T") as token, \
                captured():
            run_main(pb_auth, [])
        token.assert_called_once_with(force=True)

    def test_superusers_collection_is_treated_as_superuser_auth(self):
        with patch.object(pb_auth, "get_superuser_token", return_value="T") as token, \
                patch.object(pb_auth, "auth_user") as routed, captured():
            run_main(pb_auth, ["--collection", "_superusers"])
        token.assert_called_once_with(force=True)
        routed.assert_not_called()

    def test_user_auth_without_credentials_is_an_argparse_error(self):
        with self.assertRaises(SystemExit) as caught, captured(), \
                contextlib.redirect_stderr(io.StringIO()):
            run_main(pb_auth, ["--collection", "users", "--identity", "a@b.c"])
        self.assertEqual(caught.exception.code, 2)

    def test_auth_user_posts_to_the_collection_endpoint_and_reports_the_token(self):
        response = {"token": "TOK", "record": {"id": "u1"}}
        with patch.object(pb_auth, "pb_request", return_value=response) as sent, \
                captured() as buf:
            pb_auth.auth_user("users", "a@b.c", "pw")
        self.assertEqual(sent.call_args[0][1], "/api/collections/users/auth-with-password")
        self.assertEqual(sent.call_args[0][2], {"identity": "a@b.c", "password": "pw"})
        payload = payloads(buf.getvalue())[0]
        self.assertEqual(payload["data"]["token"], "TOK")
        self.assertEqual(payload["data"]["record"], {"id": "u1"})

    def test_auth_user_failure_exits_with_the_server_status(self):
        error = pb_auth.PBRequestError(400, {"message": "bad credentials"})
        with patch.object(pb_auth, "pb_request", side_effect=error), captured() as buf:
            with self.assertRaises(SystemExit) as caught:
                pb_auth.auth_user("users", "a@b.c", "pw")
        self.assertEqual(caught.exception.code, 1)
        payload = payloads(buf.getvalue())[0]
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], 400)


class HealthScript(unittest.TestCase):
    """The health probe's three outcomes plus its credential-dependent second stage."""

    def test_healthy_server_without_credentials_skips_the_auth_stage(self):
        with patch.object(pb_health, "pb_request", return_value={"code": 200}) as sent, \
                patch.object(pb_health, "PB_SUPERUSER_EMAIL", ""), \
                patch.object(pb_health, "PB_SUPERUSER_PASSWORD", ""), \
                patch.object(pb_health, "get_superuser_token") as token, \
                captured() as buf:
            run_main(pb_health, [])
        out = buf.getvalue()
        self.assertEqual(sent.call_args[0], ("GET", "/api/health"))
        self.assertEqual(payloads(out)[0]["data"]["health"], {"code": 200})
        token.assert_not_called()
        self.assertIn("Skipping superuser auth test", out)

    def test_credentials_trigger_a_forced_auth_and_a_truncated_token_preview(self):
        with patch.object(pb_health, "pb_request", return_value={"code": 200}), \
                patch.object(pb_health, "PB_SUPERUSER_EMAIL", "su@x.y"), \
                patch.object(pb_health, "PB_SUPERUSER_PASSWORD", "pw"), \
                patch.object(pb_health, "get_superuser_token",
                             return_value="A" * 40) as token, captured() as buf:
            run_main(pb_health, [])
        out = buf.getvalue()
        token.assert_called_once_with(force=True)
        self.assertEqual(payloads(out)[1]["data"]["token_preview"], "A" * 20 + "...")

    def test_a_half_configured_credential_pair_still_skips_the_auth_stage(self):
        with patch.object(pb_health, "pb_request", return_value={"code": 200}), \
                patch.object(pb_health, "PB_SUPERUSER_EMAIL", "su@x.y"), \
                patch.object(pb_health, "PB_SUPERUSER_PASSWORD", ""), \
                patch.object(pb_health, "get_superuser_token") as token, \
                captured() as buf:
            run_main(pb_health, [])
        token.assert_not_called()
        self.assertIn("Skipping superuser auth test", buf.getvalue())

    def test_http_error_from_the_health_endpoint_exits_one(self):
        error = pb_health.PBRequestError(503, {"message": "down"})
        with patch.object(pb_health, "pb_request", side_effect=error):
            with self.assertRaises(SystemExit) as caught, captured() as buf:
                run_main(pb_health, [])
        self.assertEqual(caught.exception.code, 1)
        self.assertEqual(payloads(buf.getvalue())[0]["status"], 503)

    def test_connection_failure_is_reported_as_status_zero(self):
        with patch.object(pb_health, "pb_request", side_effect=OSError("refused")):
            with self.assertRaises(SystemExit), captured() as buf:
                run_main(pb_health, [])
        payload = payloads(buf.getvalue())[0]
        self.assertEqual(payload["status"], 0)
        self.assertIn("Connection failed", payload["data"]["message"])


class BackupsScript(unittest.TestCase):
    """Subcommand routing and the four backup requests."""

    def test_subcommands_route_to_their_handlers(self):
        cases = [
            (["list"], "cmd_list"),
            (["create"], "cmd_create"),
            (["restore", "b.zip"], "cmd_restore"),
            (["delete", "b.zip"], "cmd_delete"),
        ]
        for argv, handler in cases:
            with self.subTest(argv=argv):
                with patch.object(pb_backups, handler) as routed, captured():
                    run_main(pb_backups, argv)
                self.assertEqual(routed.call_count, 1)

    def test_list_gets_the_backups_collection(self):
        with patch.object(pb_backups, "pb_authed_request",
                          return_value={"items": []}) as sent, captured() as buf:
            run_main(pb_backups, ["list"])
        self.assertEqual(sent.call_args[0], ("GET", "/api/backups"))
        self.assertEqual(payloads(buf.getvalue())[0]["data"], {"items": []})

    def test_create_without_a_name_sends_an_empty_body(self):
        with patch.object(pb_backups, "pb_authed_request") as sent, captured() as buf:
            run_main(pb_backups, ["create"])
        self.assertEqual(sent.call_args[0], ("POST", "/api/backups"))
        self.assertEqual(sent.call_args[1]["data"], {})
        self.assertEqual(payloads(buf.getvalue())[0]["data"]["message"], "Backup created")

    def test_create_with_a_name_sends_it_in_the_body(self):
        with patch.object(pb_backups, "pb_authed_request") as sent, captured() as buf:
            run_main(pb_backups, ["create", "snap.zip"])
        self.assertEqual(sent.call_args[1]["data"], {"name": "snap.zip"})
        self.assertIn("as snap.zip", payloads(buf.getvalue())[0]["data"]["message"])

    def test_restore_posts_to_the_key_specific_restore_path(self):
        with patch.object(pb_backups, "pb_authed_request") as sent, captured() as buf:
            run_main(pb_backups, ["restore", "snap.zip"])
        self.assertEqual(sent.call_args[0], ("POST", "/api/backups/snap.zip/restore"))
        self.assertEqual(payloads(buf.getvalue())[0]["status"], 204)

    def test_delete_targets_the_key(self):
        with patch.object(pb_backups, "pb_authed_request") as sent, captured() as buf:
            run_main(pb_backups, ["delete", "snap.zip"])
        self.assertEqual(sent.call_args[0], ("DELETE", "/api/backups/snap.zip"))

    def test_a_failing_restore_exits_one_with_the_server_status(self):
        error = pb_backups.PBRequestError(400, {"message": "no such backup"})
        with patch.object(pb_backups, "pb_authed_request", side_effect=error):
            with self.assertRaises(SystemExit) as caught, captured() as buf:
                run_main(pb_backups, ["restore", "missing.zip"])
        self.assertEqual(caught.exception.code, 1)
        payload = payloads(buf.getvalue())[0]
        self.assertFalse(payload["success"])
        self.assertEqual(payload["status"], 400)


class CollectionsScript(unittest.TestCase):
    """Query-string assembly, body sources, and the import wrapper."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as handle:
            handle.write(text)
        return path

    def test_subcommands_route_to_their_handlers(self):
        cases = [
            (["list"], "cmd_list"),
            (["get", "posts"], "cmd_get"),
            (["create", "{}"], "cmd_create"),
            (["update", "posts", "{}"], "cmd_update"),
            (["delete", "posts"], "cmd_delete"),
            (["import", "--file", "x.json"], "cmd_import"),
        ]
        for argv, handler in cases:
            with self.subTest(argv=argv):
                with patch.object(pb_collections, handler) as routed, captured():
                    run_main(pb_collections, argv)
                self.assertEqual(routed.call_count, 1)

    def test_list_filters_are_url_encoded_into_the_query_string(self):
        with patch.object(pb_collections, "pb_authed_request",
                          return_value={}) as sent, captured():
            # `--sort -created` would be read as an option flag; the = form is the
            # only way to pass a descending sort on the command line.
            run_main(pb_collections, ["list", "--filter", "type = 'base'",
                                      "--sort=-created", "--page", "2",
                                      "--perPage", "50"])
        self.assertEqual(
            sent.call_args[0][1],
            "/api/collections?filter=type%20%3D%20%27base%27&sort=-created"
            "&page=2&perPage=50")

    def test_list_without_options_sends_a_bare_path(self):
        with patch.object(pb_collections, "pb_authed_request",
                          return_value={}) as sent, captured():
            run_main(pb_collections, ["list"])
        self.assertEqual(sent.call_args[0][1], "/api/collections")

    def test_get_addresses_the_collection_by_name(self):
        with patch.object(pb_collections, "pb_authed_request",
                          return_value={"id": "c1"}) as sent, captured():
            run_main(pb_collections, ["get", "posts"])
        self.assertEqual(sent.call_args[0], ("GET", "/api/collections/posts"))

    def test_create_posts_the_inline_json_body(self):
        with patch.object(pb_collections, "pb_authed_request",
                          return_value={}) as sent, captured():
            run_main(pb_collections, ["create", '{"name":"posts"}'])
        self.assertEqual(sent.call_args[0], ("POST", "/api/collections"))
        self.assertEqual(sent.call_args[1]["data"], {"name": "posts"})

    def test_create_reads_a_body_from_file(self):
        path = self._write("schema.json", '{"name":"from_file"}')
        with patch.object(pb_collections, "pb_authed_request",
                          return_value={}) as sent, captured():
            run_main(pb_collections, ["create", "--file", path])
        self.assertEqual(sent.call_args[1]["data"], {"name": "from_file"})

    def test_update_patches_the_named_collection(self):
        with patch.object(pb_collections, "pb_authed_request",
                          return_value={}) as sent, captured():
            run_main(pb_collections, ["update", "posts", '{"name":"p2"}'])
        self.assertEqual(sent.call_args[0], ("PATCH", "/api/collections/posts"))
        self.assertEqual(sent.call_args[1]["data"], {"name": "p2"})

    def test_import_wraps_a_bare_array_in_a_collections_key(self):
        path = self._write("all.json", '[{"name":"a"},{"name":"b"}]')
        with patch.object(pb_collections, "pb_authed_request") as sent, captured():
            run_main(pb_collections, ["import", "--file", path])
        self.assertEqual(sent.call_args[0], ("PUT", "/api/collections/import"))
        self.assertEqual(sent.call_args[1]["data"],
                         {"collections": [{"name": "a"}, {"name": "b"}]})

    def test_import_passes_an_object_through_unwrapped(self):
        path = self._write("all.json", '{"collections":[{"name":"a"}],"deleteMissing":true}')
        with patch.object(pb_collections, "pb_authed_request") as sent, captured():
            run_main(pb_collections, ["import", "--file", path])
        self.assertEqual(sent.call_args[1]["data"],
                         {"collections": [{"name": "a"}], "deleteMissing": True})

    def test_body_is_required(self):
        args = type("Args", (), {"file": None, "json_data": None})()
        with self.assertRaises(SystemExit), captured() as buf:
            pb_collections._get_body(args)
        self.assertIn("required", payloads(buf.getvalue())[0]["data"]["message"])

    def test_malformed_inline_json_exits_one(self):
        args = type("Args", (), {"file": None, "json_data": "{nope"})()
        with self.assertRaises(SystemExit) as caught, captured() as buf:
            pb_collections._get_body(args)
        self.assertEqual(caught.exception.code, 1)
        self.assertIn("Invalid JSON", payloads(buf.getvalue())[0]["data"]["message"])

    def test_missing_file_exits_one(self):
        with self.assertRaises(SystemExit), captured() as buf:
            pb_collections._load_json_file(os.path.join(self.tmp, "absent.json"))
        self.assertIn("File not found", payloads(buf.getvalue())[0]["data"]["message"])

    def test_malformed_file_json_exits_one(self):
        path = self._write("bad.json", "{nope")
        with self.assertRaises(SystemExit), captured() as buf:
            pb_collections._load_json_file(path)
        self.assertIn("Invalid JSON in file",
                      payloads(buf.getvalue())[0]["data"]["message"])


class RecordsScript(unittest.TestCase):
    """The record CRUD paths and their shared query-string builder."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _args(self, **kwargs):
        return type("Args", (), kwargs)()

    def test_query_string_carries_every_list_parameter_in_order(self):
        args = self._args(filter="a = 1", sort="-created", expand="author",
                          fields="id,title", page=3, perPage=10)
        self.assertEqual(
            pb_records._build_qs(args),
            "?filter=a%20%3D%201&sort=-created&expand=author&fields=id%2Ctitle"
            "&page=3&perPage=10")

    def test_query_string_is_empty_when_nothing_is_set(self):
        self.assertEqual(pb_records._build_qs(self._args()), "")

    def test_list_appends_the_query_string_to_the_records_path(self):
        with patch.object(pb_records, "pb_authed_request",
                          return_value={"items": []}) as sent, captured():
            run_main(pb_records, ["list", "posts", "--filter", "published = true"])
        self.assertEqual(
            sent.call_args[0],
            ("GET", "/api/collections/posts/records?filter=published%20%3D%20true"))

    def test_get_supports_expand_and_fields_only(self):
        with patch.object(pb_records, "pb_authed_request",
                          return_value={"id": "r1"}) as sent, captured():
            run_main(pb_records, ["get", "posts", "r1", "--expand", "author",
                                  "--fields", "id"])
        self.assertEqual(
            sent.call_args[0],
            ("GET", "/api/collections/posts/records/r1?expand=author&fields=id"))

    def test_create_posts_the_body_to_the_collection(self):
        with patch.object(pb_records, "pb_authed_request",
                          return_value={"id": "r1"}) as sent, captured():
            run_main(pb_records, ["create", "posts", '{"title":"hi"}'])
        self.assertEqual(sent.call_args[0], ("POST", "/api/collections/posts/records"))
        self.assertEqual(sent.call_args[1]["data"], {"title": "hi"})

    def test_update_uses_patch_on_the_record_path(self):
        with patch.object(pb_records, "pb_authed_request",
                          return_value={"id": "r1"}) as sent, captured():
            run_main(pb_records, ["update", "posts", "r1", '{"title":"new"}',
                                  "--expand", "author"])
        self.assertEqual(
            sent.call_args[0],
            ("PATCH", "/api/collections/posts/records/r1?expand=author"))
        self.assertEqual(sent.call_args[1]["data"], {"title": "new"})

    def test_delete_reports_the_record_and_collection(self):
        with patch.object(pb_records, "pb_authed_request") as sent, captured() as buf:
            run_main(pb_records, ["delete", "posts", "r1"])
        self.assertEqual(sent.call_args[0],
                         ("DELETE", "/api/collections/posts/records/r1"))
        message = payloads(buf.getvalue())[0]["data"]["message"]
        self.assertIn("r1", message)
        self.assertIn("posts", message)

    def test_body_from_file_beats_the_positional_argument(self):
        path = os.path.join(self.tmp, "data.json")
        with open(path, "w") as handle:
            handle.write('{"from":"file"}')
        args = self._args(file=path, json_data='{"from":"argv"}')
        self.assertEqual(pb_records._get_body(args), {"from": "file"})

    def test_missing_body_file_exits_one(self):
        args = self._args(file=os.path.join(self.tmp, "absent.json"), json_data=None)
        with self.assertRaises(SystemExit), captured() as buf:
            pb_records._get_body(args)
        self.assertIn("File not found", payloads(buf.getvalue())[0]["data"]["message"])

    def test_malformed_body_json_exits_one(self):
        args = self._args(file=None, json_data="{nope")
        with self.assertRaises(SystemExit) as caught, captured() as buf:
            pb_records._get_body(args)
        self.assertEqual(caught.exception.code, 1)
        self.assertIn("Invalid JSON", payloads(buf.getvalue())[0]["data"]["message"])

    def test_no_body_at_all_exits_one(self):
        with self.assertRaises(SystemExit), captured() as buf:
            pb_records._get_body(self._args(file=None, json_data=None))
        self.assertIn("required", payloads(buf.getvalue())[0]["data"]["message"])

    def test_a_failing_list_exits_one_with_the_server_status(self):
        error = pb_records.PBRequestError(404, {"message": "no collection"})
        with patch.object(pb_records, "pb_authed_request", side_effect=error):
            with self.assertRaises(SystemExit) as caught, captured() as buf:
                run_main(pb_records, ["list", "ghosts"])
        self.assertEqual(caught.exception.code, 1)
        self.assertEqual(payloads(buf.getvalue())[0]["status"], 404)


class MigrationGenerator(unittest.TestCase):
    """File naming is the contract: PocketBase applies migrations in filename order."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_description_is_sanitized_into_a_filename_component(self):
        cases = [
            ("create_posts_collection", "create_posts_collection"),
            ("Add Status Field", "add_status_field"),
            ("  add--status!!field  ", "add_status_field"),
            ("__leading_and_trailing__", "leading_and_trailing"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(pb_create_migration.sanitize_name(raw), expected)

    def test_filename_is_the_unix_timestamp_then_the_safe_name(self):
        out_dir = os.path.join(self.tmp, "pb_migrations")
        with patch("time.time", return_value=1700000000.9), captured() as buf:
            run_main(pb_create_migration, ["Add Status Field", "--dir", out_dir])
        payload = payloads(buf.getvalue())[0]
        self.assertEqual(payload["data"]["filename"], "1700000000_add_status_field.js")
        self.assertEqual(os.listdir(out_dir), ["1700000000_add_status_field.js"])

    def test_the_generated_file_is_the_template_verbatim(self):
        out_dir = os.path.join(self.tmp, "pb_migrations")
        with open(pb_create_migration.TEMPLATE_PATH) as handle:
            template = handle.read()
        with captured() as buf:
            run_main(pb_create_migration, ["seed", "--dir", out_dir])
        written = payloads(buf.getvalue())[0]["data"]["file"]
        with open(written) as handle:
            self.assertEqual(handle.read(), template)
        self.assertIn("migrate((app)", template)

    def test_the_output_directory_is_created_when_absent(self):
        out_dir = os.path.join(self.tmp, "deep", "nested")
        with captured():
            run_main(pb_create_migration, ["seed", "--dir", out_dir])
        self.assertTrue(os.path.isdir(out_dir))

    def test_a_description_with_no_usable_characters_exits_one(self):
        with patch.object(pb_create_migration, "TEMPLATE_PATH",
                          pb_create_migration.TEMPLATE_PATH):
            with self.assertRaises(SystemExit) as caught, captured() as buf:
                run_main(pb_create_migration, ["!!!", "--dir", self.tmp])
        self.assertEqual(caught.exception.code, 1)
        self.assertIn("Invalid migration description",
                      payloads(buf.getvalue())[0]["data"]["message"])
        self.assertEqual(os.listdir(self.tmp), [])

    def test_a_missing_template_exits_one_before_writing_anything(self):
        absent = os.path.join(self.tmp, "no-template.js")
        with patch.object(pb_create_migration, "TEMPLATE_PATH", absent):
            with self.assertRaises(SystemExit) as caught, captured() as buf:
                run_main(pb_create_migration, ["seed", "--dir",
                                               os.path.join(self.tmp, "out")])
        self.assertEqual(caught.exception.code, 1)
        self.assertIn("Template not found",
                      payloads(buf.getvalue())[0]["data"]["message"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "out")))


class E2EHelpers(unittest.TestCase):
    """The helpers a project's own access-control tests are written against."""

    def test_runner_counts_checks_and_returns_a_shell_exit_code(self):
        with captured():
            runner = pb_e2e_helpers.TestRunner("suite")
            runner.check("passes", True)
            runner.check("also passes", 1 == 1)
            self.assertEqual(runner.summary(), 0)
            runner.check("fails", False, "detail")
            self.assertEqual(runner.summary(), 1)
        self.assertEqual((runner.passed, runner.failed), (2, 1))

    def test_req_always_asks_for_the_raw_status_pair(self):
        with patch.object(pb_e2e_helpers, "pb_request",
                          return_value=(200, {"ok": 1})) as sent:
            self.assertEqual(pb_e2e_helpers.req("GET", "/api/x"), (200, {"ok": 1}))
        self.assertTrue(sent.call_args[1]["raw_response"])

    def test_user_login_returns_the_token_and_record_id(self):
        response = (200, {"token": "T", "record": {"id": "u1"}})
        with patch.object(pb_e2e_helpers, "req", return_value=response) as sent:
            self.assertEqual(pb_e2e_helpers.user_login("a@b.c", "pw"), ("T", "u1"))
        self.assertEqual(sent.call_args[0][1],
                         "/api/collections/users/auth-with-password")

    def test_user_login_raises_on_a_non_200(self):
        with patch.object(pb_e2e_helpers, "req", return_value=(400, {"m": "no"})):
            with self.assertRaises(RuntimeError):
                pb_e2e_helpers.user_login("a@b.c", "pw")

    def test_create_test_user_sends_the_password_confirmation(self):
        with patch.object(pb_e2e_helpers, "req",
                          return_value=(201, {"id": "u2"})) as sent:
            self.assertEqual(pb_e2e_helpers.create_test_user("a@b.c", "pw", "A"), "u2")
        body = sent.call_args[0][2]
        self.assertEqual(body["passwordConfirm"], "pw")
        self.assertEqual(body["name"], "A")

    def test_create_test_user_raises_on_an_unexpected_status(self):
        with patch.object(pb_e2e_helpers, "req", return_value=(403, {"m": "no"})):
            with self.assertRaises(RuntimeError):
                pb_e2e_helpers.create_test_user("a@b.c", "pw", "A")

    def test_superuser_create_user_translates_the_request_error(self):
        error = pb_e2e_helpers.PBRequestError(400, {"message": "dup"})
        with patch.object(pb_e2e_helpers, "pb_authed_request", side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                pb_e2e_helpers.superuser_create_user("a@b.c", "pw", "A")
        self.assertIn("400", str(caught.exception))

    def test_pre_cleanup_deletes_every_match_and_swallows_errors(self):
        calls = []

        def fake(method, path, *args, **kwargs):
            calls.append((method, path))
            if method == "GET":
                return {"items": [{"id": "r1"}, {"id": "r2"}]}
            return None

        with patch.object(pb_e2e_helpers, "pb_authed_request", side_effect=fake):
            pb_e2e_helpers.pre_cleanup(["a@b.c"])
        self.assertEqual([c[0] for c in calls], ["GET", "DELETE", "DELETE"])
        self.assertIn("filter=email%20%3D%20%22a%40b.c%22", calls[0][1])

        error = pb_e2e_helpers.PBRequestError(500, {})
        with patch.object(pb_e2e_helpers, "pb_authed_request", side_effect=error):
            pb_e2e_helpers.pre_cleanup(["a@b.c"])

    def test_superuser_get_reports_the_error_status_instead_of_raising(self):
        error = pb_e2e_helpers.PBRequestError(404, {"message": "gone"})
        with patch.object(pb_e2e_helpers, "pb_authed_request", side_effect=error):
            self.assertEqual(pb_e2e_helpers.superuser_get("posts", "r1"),
                             (404, {"message": "gone"}))

    def test_superuser_list_url_encodes_the_filter(self):
        with patch.object(pb_e2e_helpers, "pb_authed_request",
                          return_value={"items": []}) as sent:
            status, _ = pb_e2e_helpers.superuser_list("posts", 'owner = "u1"')
        self.assertEqual(status, 200)
        self.assertEqual(sent.call_args[0][1],
                         '/api/collections/posts/records?filter=owner%20%3D%20%22u1%22')

    def test_superuser_delete_ignores_a_failed_delete(self):
        error = pb_e2e_helpers.PBRequestError(404, {})
        with patch.object(pb_e2e_helpers, "pb_authed_request", side_effect=error):
            pb_e2e_helpers.superuser_delete("posts", "r1")


class UsageStrings(unittest.TestCase):
    """`python` is not a command on a stock macOS shell; the usage lines must say python3."""

    def test_no_script_usage_line_invokes_bare_python(self):
        offenders = []
        for name in SCRIPT_FILES:
            with open(os.path.join(SCRIPTS, name)) as handle:
                for number, line in enumerate(handle, 1):
                    if "python scripts/" in line:
                        offenders.append("{0}:{1}".format(name, number))
        self.assertEqual(offenders, [])

    def test_the_documented_entry_points_still_show_an_invocation(self):
        for name in ("pb_auth.py", "pb_backups.py", "pb_collections.py",
                     "pb_create_migration.py", "pb_records.py"):
            with self.subTest(script=name):
                with open(os.path.join(SCRIPTS, name)) as handle:
                    self.assertIn("python3 scripts/" + name, handle.read())


if __name__ == "__main__":
    unittest.main()
