"""Tests for the plugin-feedback plugin — both reminder hooks and the reporter script.

The hooks run as subprocesses (their real invocation shape: JSON on stdin, one JSON
line on stdout), matching tests/test_worker_context.py: fixtures build into a tempdir
per test and the child environment is built from scratch with only PATH inherited.

The reporter is imported in process so its body-building logic is covered directly.
Nothing here shells out to `gh` or touches the network by default: every test of the
filing path substitutes a fake runner and asserts on the argv it was handed. The single
exception is opt-in and off in `make ci` — `PLUGIN_FEEDBACK_LIVE_TESTS=1` enables the one
check that the reporter's default labels still exist in the real target repo, and its gh
probe runs inside that test, never at import.
"""

import io
import itertools
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(REPO, "primitives-core", "hooks")
SESSION_HOOK = os.path.join(HOOKS, "plugin-feedback-session", "hook.py")
WORKER_HOOK = os.path.join(HOOKS, "plugin-feedback-worker", "hook.py")
PLUGIN_MANIFEST = os.path.join(
    REPO, "plugins", "plugin-feedback", ".claude-plugin", "plugin.json"
)

sys.path.insert(0, os.path.join(HOOKS, "plugin-feedback-session"))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import report_issue as R  # noqa: E402
import check_identity as IDENT  # noqa: E402

_SEQ = itertools.count()

# The published opt-out contract, asserted from the test's side on purpose: each hook
# dir is copied and symlinked on its own, so the name is duplicated in both hooks
# rather than imported across them.
DISABLE_ENV = "PLUGIN_FEEDBACK_DISABLED"

# Opt-in for the one test allowed to reach the network. Unset (the `make ci` case) it
# skips, and importing this module spawns no subprocess at all.
LIVE_TESTS_ENV = "PLUGIN_FEEDBACK_LIVE_TESTS"


def _session_id():
    return f"plugin-feedback-session-{next(_SEQ)}"


class _HookTestBase:
    """Shared subprocess driver and fail-open assertions for both hooks.

    A plain mixin, not a TestCase: unittest discovery would otherwise run this
    class's tests once on its own with no hook to point them at.
    """

    HOOK = None
    EVENT = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)

    # -- fixtures ------------------------------------------------------

    def _payload(self, **over):
        raise NotImplementedError

    def _run_hook(self, stdin_text=None, env=None, devnull=False):
        child_env = {"PATH": os.environ.get("PATH", "")}
        child_env.update(env or {})
        # cwd is the tempdir on purpose: `_assert_wrote_nothing` walks it, and a child
        # left in the runner's own directory would make that assertion vacuous — it
        # would look for strays somewhere the hook was never running.
        kwargs = dict(
            capture_output=True, text=True, env=child_env, timeout=30, cwd=self.cwd
        )
        if devnull:
            kwargs["stdin"] = subprocess.DEVNULL
        else:
            kwargs["input"] = stdin_text
        return subprocess.run([sys.executable, self.HOOK], **kwargs)

    def _context(self, result):
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        hso = body["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], self.EVENT)
        return hso["additionalContext"]

    def _assert_wrote_nothing(self):
        found = []
        for root, _dirs, files in os.walk(self.tmp.name):
            found.extend(os.path.join(root, f) for f in files)
        self.assertEqual(found, [])

    # -- shared fail-open contract ---------------------------------------

    def test_injects_a_pointer_to_the_reporter(self):
        context = self._context(self._run_hook(json.dumps(self._payload())))
        self.assertIn("report_issue.py", context)

    def test_malformed_stdin_fails_open_and_writes_nothing(self):
        result = self._run_hook("not json at all")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        self._assert_wrote_nothing()

    def test_empty_stdin_fails_open(self):
        result = self._run_hook("")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_absent_stdin_fails_open(self):
        result = self._run_hook(devnull=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_non_object_payload_fails_open(self):
        result = self._run_hook(json.dumps(["not", "a", "dict"]))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_missing_plugin_root_still_injects(self):
        """CLAUDE_PLUGIN_ROOT absent is the normal case in a bare shell — the hook
        falls back to a path derived from its own location and never goes quiet."""
        context = self._context(self._run_hook(json.dumps(self._payload())))
        self.assertIn("report_issue.py", context)

    def test_unwritable_plugin_root_still_injects(self):
        blocked = os.path.join(self.tmp.name, "blocked")
        os.makedirs(blocked, exist_ok=True)
        os.chmod(blocked, 0o000)
        self.addCleanup(os.chmod, blocked, stat.S_IRWXU)
        result = self._run_hook(
            json.dumps(self._payload()), env={"CLAUDE_PLUGIN_ROOT": blocked}
        )
        context = self._context(result)
        self.assertIn("report_issue.py", context)

    def test_opt_out_env_silences_the_hook(self):
        result = self._run_hook(
            json.dumps(self._payload()), env={DISABLE_ENV: "1"}
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_offer_is_scoped_to_this_marketplace(self):
        """The reporter files into the marketplace it shipped from, so the offer must
        say so. Promising `any installed plugin` sends a report about someone else's
        plugin into this marketplace's tracker, which is the destination bug."""
        context = self._context(self._run_hook(json.dumps(self._payload())))
        self.assertIn("marketplace", context.lower())
        self.assertNotIn("any installed plugin", context.lower())

    def test_injected_text_is_a_short_pointer(self):
        """The card's rule: the hook text points at the reporter, it does not inline
        the template. Bounded at 700 characters so a wall of instructions goes red."""
        context = self._context(self._run_hook(json.dumps(self._payload())))
        self.assertLessEqual(len(context), 700)


class SessionHookTests(_HookTestBase, unittest.TestCase):
    HOOK = SESSION_HOOK
    EVENT = "SessionStart"

    def _payload(self, **over):
        payload = {
            "session_id": _session_id(),
            "hook_event_name": "SessionStart",
            "cwd": self.cwd,
            "source": "startup",
        }
        payload.update(over)
        return payload

    def test_primary_session_may_file_either_kind(self):
        context = self._context(self._run_hook(json.dumps(self._payload())))
        self.assertIn("bug", context)
        self.assertIn("feature request", context)
        self.assertIn("contradicts the plugin's own stated contract", context)

    def test_silent_on_resume_and_compact(self):
        for source in ("resume", "compact"):
            with self.subTest(source=source):
                result = self._run_hook(json.dumps(self._payload(source=source)))
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), "")

    def test_fires_on_clear(self):
        context = self._context(self._run_hook(json.dumps(self._payload(source="clear"))))
        self.assertIn("report_issue.py", context)


class WorkerHookTests(_HookTestBase, unittest.TestCase):
    HOOK = WORKER_HOOK
    EVENT = "SubagentStart"

    def _payload(self, **over):
        payload = {
            "session_id": _session_id(),
            "hook_event_name": "SubagentStart",
            "agent_id": "agent-1",
            "agent_type": "builder",
            "cwd": self.cwd,
        }
        payload.update(over)
        return payload

    def test_worker_may_file_a_bug_directly(self):
        context = self._context(self._run_hook(json.dumps(self._payload())))
        self.assertIn("may file a bug directly", context.lower())
        self.assertIn("contradicts the plugin's own stated contract", context)

    def test_worker_must_not_file_a_feature_request(self):
        context = self._context(self._run_hook(json.dumps(self._payload())))
        self.assertIn("must not file a feature request", context.lower())
        self.assertIn("--draft", context)
        self.assertIn("dispatcher", context)

    def test_fires_regardless_of_source_field(self):
        """SubagentStart carries no `source`; the worker hook must not borrow the
        session hook's cold-start gate and go quiet on every dispatch."""
        context = self._context(self._run_hook(json.dumps(self._payload(source="resume"))))
        self.assertIn("report_issue.py", context)


class RepoResolutionTests(unittest.TestCase):
    """The target repo is data, never a literal baked into a shipped body."""

    # Shapes a repo literal takes. `github.com/` alone missed the scp form
    # (`git@github.com:owner/name.git`) and every non-GitHub forge, so a hardcoded
    # remote passed the guard the plugin's identity-neutrality claim rests on.
    FORGE_LITERALS = (
        "github.com/", "github.com:", "gitlab.com", "bitbucket.org", "codeberg.org",
        "git.sr.ht", "git@",
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _plugin_root(self, repository):
        root = os.path.join(self.tmp.name, "plugin")
        meta = os.path.join(root, ".claude-plugin")
        os.makedirs(meta, exist_ok=True)
        manifest = {"name": "demo", "version": "0.1.0"}
        if repository is not None:
            manifest["repository"] = repository
        with open(os.path.join(meta, "plugin.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=True)
        return root

    def _shipped_slug(self):
        """`owner/name` this plugin actually ships as, read from its manifest.

        The manifest is the sanctioned place for authorship (check_identity skips
        `.claude-plugin/` for exactly that reason), which makes it the right source
        for `what must NOT appear in the reporter` — it follows a rename instead of
        needing one more literal kept in step by hand.
        """
        with open(PLUGIN_MANIFEST, encoding="utf-8") as fh:
            slug = R.normalize_repo(json.load(fh).get("repository"))
        self.assertIsNotNone(slug, "plugin manifest carries no resolvable repository")
        return slug

    def test_no_repo_literal_in_the_source(self):
        """Three independent nets, none of them a second hand-kept token list:
        check_identity's own IDENTITY tokens (the owner handle among them), the forge
        shapes that lint does not model, and this plugin's own shipped slug."""
        with open(R.__file__, encoding="utf-8") as fh:
            source = fh.read()

        for rx, why in IDENT.IDENTITY:
            with self.subTest(token=why):
                self.assertIsNone(
                    rx.search(source), "reporter source carries {0}".format(why)
                )

        for literal in self.FORGE_LITERALS:
            with self.subTest(literal=literal):
                self.assertNotIn(literal, source)

        slug = self._shipped_slug()
        owner, name = slug.split("/", 1)
        for token in (slug, owner, name):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_env_var_wins(self):
        root = self._plugin_root("https://github.com/acme/from-manifest")
        env = {R.REPO_ENV: "acme/from-env", "CLAUDE_PLUGIN_ROOT": root}
        self.assertEqual(R.resolve_repo(env), "acme/from-env")

    def test_manifest_url_is_the_fallback(self):
        root = self._plugin_root("https://github.com/acme/widgets")
        self.assertEqual(R.resolve_repo({"CLAUDE_PLUGIN_ROOT": root}), "acme/widgets")

    def test_manifest_slug_and_git_forms(self):
        for value, want in (
            ("acme/widgets", "acme/widgets"),
            ("https://github.com/acme/widgets.git", "acme/widgets"),
            ("git@github.com:acme/widgets.git", "acme/widgets"),
            ({"url": "https://github.com/acme/widgets"}, "acme/widgets"),
        ):
            with self.subTest(value=value):
                root = self._plugin_root(value)
                self.assertEqual(R.resolve_repo({"CLAUDE_PLUGIN_ROOT": root}), "acme/widgets")

    def test_unresolvable_returns_none(self):
        self.assertIsNone(R.resolve_repo({"CLAUDE_PLUGIN_ROOT": self._plugin_root(None)}))
        self.assertIsNone(R.resolve_repo({"CLAUDE_PLUGIN_ROOT": self.tmp.name}))
        self.assertIsNone(R.resolve_repo({}))

    def test_garbage_manifest_returns_none(self):
        root = os.path.join(self.tmp.name, "broken")
        meta = os.path.join(root, ".claude-plugin")
        os.makedirs(meta, exist_ok=True)
        with open(os.path.join(meta, "plugin.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(R.resolve_repo({"CLAUDE_PLUGIN_ROOT": root}))


class BodyBuildingTests(unittest.TestCase):
    """A well-formed issue body from a fixture, with no network anywhere near it."""

    def _report(self, **over):
        fields = dict(
            kind=R.KIND_BUG,
            plugin="atelier",
            plugin_version="0.8.0",
            project="acme-service",
            date="2026-08-07",
            severity="major",
            summary="worker covenant never injected under strict",
            symptom="No additionalContext arrives at subagent start.",
            repro="Set enforce: strict in .claude/atelier.local.md, dispatch any subagent.",
            contract="Its README states that strict injects the covenant plus the tool-layer clause.",
            limitation="",
            workaround="Restate the covenant by hand in every brief.",
            fix="",
        )
        fields.update(over)
        return R.Report(**fields)

    def test_title_is_component_colon_outcome(self):
        self.assertEqual(
            R.build_title(self._report()),
            "atelier: worker covenant never injected under strict",
        )

    def test_body_carries_every_template_field(self):
        body = R.build_body(self._report(fix="Read the activation file before the guard."))
        for fragment in (
            "**Plugin:** atelier 0.8.0",
            "**Consuming project:** acme-service",
            "**Observed:** 2026-08-07",
            "**Severity:** major",
            "**Contract violated:** Its README states",
            "## What happens",
            "No additionalContext arrives at subagent start.",
            "## Repro",
            "enforce: strict",
            "## Workaround",
            "Restate the covenant by hand in every brief.",
            "## Suggested fix",
            "Read the activation file before the guard.",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, body)

    def test_body_is_deterministic(self):
        report = self._report()
        self.assertEqual(R.build_body(report), R.build_body(report))

    def test_optional_fix_degrades_to_an_explicit_none(self):
        body = R.build_body(self._report(fix=""))
        self.assertIn("## Suggested fix", body)
        self.assertIn(R.NO_FIX, body)

    def test_feature_body_states_the_limitation_not_a_contract(self):
        body = R.build_body(
            self._report(
                kind=R.KIND_FEATURE,
                contract="",
                limitation="No way to brief a worker on a per-wave rule.",
            )
        )
        self.assertIn("**Limitation hit:** No way to brief a worker", body)
        self.assertNotIn("Contract violated", body)

    def test_label_defaults_per_kind_and_is_overridable(self):
        self.assertEqual(R.resolve_label(R.KIND_BUG, {}), R.DEFAULT_LABELS[R.KIND_BUG])
        self.assertEqual(R.resolve_label(R.KIND_FEATURE, {}), R.DEFAULT_LABELS[R.KIND_FEATURE])
        self.assertEqual(
            R.resolve_label(R.KIND_BUG, {R.LABEL_ENV[R.KIND_BUG]: "defect"}), "defect"
        )
        self.assertEqual(R.resolve_label(R.KIND_BUG, {}, override="custom"), "custom")

    def test_argv_is_a_complete_gh_invocation(self):
        argv = R.build_argv("acme/widgets", "t", "b", "type:fix")
        self.assertEqual(argv[:3], ["gh", "issue", "create"])
        for flag, value in (
            ("--repo", "acme/widgets"),
            ("--title", "t"),
            ("--body", "b"),
            ("--label", "type:fix"),
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, argv)
                self.assertEqual(argv[argv.index(flag) + 1], value)


class _Completed:
    """The three attributes the reporter reads off a completed process."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _GhFake:
    """Base for the runner fakes: answers the reporter's read-only `gh` probes — this
    marketplace's plugin list and the target repo's label set — so a test only has to
    say what `gh issue create` does. `creates` is that subset of the recorded calls,
    which is what every filing assertion below counts."""

    LISTED = ("atelier", "plugin-feedback")
    LABELS = tuple(R.DEFAULT_LABELS.values())

    def __init__(self):
        self.calls = []

    @property
    def creates(self):
        return [argv for argv, _kw in self.calls if argv[:3] == ["gh", "issue", "create"]]

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if argv[:2] == ["gh", "api"]:
            return _Completed(
                stdout=json.dumps({"plugins": [{"name": n} for n in self.LISTED]})
            )
        if argv[:3] == ["gh", "label", "list"]:
            return _Completed(stdout=json.dumps([{"name": n} for n in self.LABELS]))
        return self._create()

    def _create(self):
        raise NotImplementedError


class _FakeRunner(_GhFake):
    """Stands in for subprocess.run; records the argv and never touches the network."""

    def __init__(self, returncode=0):
        _GhFake.__init__(self)
        self.returncode = returncode

    def _create(self):
        return _Completed(self.returncode, "https://example.invalid/issues/1\n", "")


class _LabelMissingRunner(_GhFake):
    """gh's actual behaviour when the label does not exist: the whole `issue create`
    fails, after the body has already been composed. Succeeds on the retry.

    It reports the label as PRESENT on the read-only probe, so the reporter's own
    live-label check cannot save this one — which is the point: the retry stays the
    backstop for the window between the check and the call, and for every repo whose
    labels gh could not answer for at all."""

    MESSAGE = "could not add label: 'type:feature' not found\n"

    def _create(self):
        if len(self.creates) == 1:
            return _Completed(1, "", self.MESSAGE)
        return _Completed(0, "https://example.invalid/issues/1\n", "")


class _BlindRunner(_FakeRunner):
    """gh installed but unable to answer a read — no auth, no network, rate limited.
    Only `issue create` works, which is the case the fail-open path exists for."""

    def __call__(self, argv, **kwargs):
        if argv[:3] == ["gh", "issue", "create"]:
            return _FakeRunner.__call__(self, argv, **kwargs)
        self.calls.append((argv, kwargs))
        return _Completed(1, "", "gh: could not resolve host\n")


class MainTests(unittest.TestCase):
    """The CLI edges, all driven with a fake runner — `gh` is never executed."""

    BUG_ARGS = [
        "bug",
        "--plugin", "atelier",
        "--plugin-version", "0.8.0",
        "--project", "acme-service",
        "--summary", "covenant never injected",
        "--symptom", "Nothing arrives at subagent start.",
        "--repro", "Dispatch any subagent.",
        "--contract", "The README promises the covenant under strict.",
    ]

    def setUp(self):
        # An empty plugin root, pinned: without it the manifest fallback resolves
        # against this checkout, and the unresolvable-repo test would silently flip
        # from asserting a refusal to asserting a filing the day someone adds a
        # `primitives-core/.claude-plugin/plugin.json`.
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _main(self, argv, env=None, runner=None, today="2026-08-07"):
        out = io.StringIO()
        runner = runner if runner is not None else _FakeRunner()
        env = dict(env or {})
        env.setdefault(R.REPO_ENV, "acme/widgets")
        env.setdefault("CLAUDE_PLUGIN_ROOT", self.tmp.name)
        code = R.main(argv, env=env, runner=runner, today=today, out=out)
        return code, out.getvalue(), runner

    def test_files_through_the_runner_once(self):
        code, _out, runner = self._main(self.BUG_ARGS)
        self.assertEqual(code, 0)
        self.assertEqual(len(runner.creates), 1)
        argv = runner.creates[0]
        self.assertEqual(argv[:3], ["gh", "issue", "create"])
        self.assertIn("acme/widgets", argv)
        self.assertIn(R.DEFAULT_LABELS[R.KIND_BUG], argv)

    def test_feature_default_is_the_label_the_marketplace_repo_carries(self):
        """Filed twice from the field (two separate consuming projects) before it was
        fixed: the default was `type:feature`, the repo's taxonomy is `type:feat`, so
        every feature filing failed out of the box."""
        self.assertEqual(R.DEFAULT_LABELS[R.KIND_FEATURE], "type:feat")

    def test_missing_label_files_unlabelled_instead_of_losing_the_report(self):
        """The label is the least important part of a report and the only part that can
        fail on its own. Losing a composed body over it costs the filer a full re-run."""
        runner = _LabelMissingRunner()
        code, out, runner = self._main(self.BUG_ARGS, runner=runner)
        self.assertEqual(code, 0)
        self.assertEqual(len(runner.creates), 2)
        retry = runner.creates[1]
        self.assertNotIn("--label", retry)
        self.assertIn("--body", retry)  # the report itself survived the retry
        self.assertIn("filing unlabelled", out)
        self.assertIn(R.LABEL_ENV[R.KIND_BUG], out)  # names the way to fix it for good

    def test_a_failure_that_is_not_about_the_label_is_not_retried(self):
        runner = _FakeRunner(returncode=1)
        code, _out, runner = self._main(self.BUG_ARGS, runner=runner)
        self.assertEqual(code, 1)
        self.assertEqual(len(runner.creates), 1)

    def test_argv_omits_the_flag_entirely_when_the_label_is_falsy(self):
        self.assertNotIn("--label", R.build_argv("acme/widgets", "t", "b", None))

    def test_filing_names_the_target_repo_before_it_files(self):
        """Where the issue lands is the one thing a reporter must never keep to
        itself: the destination is resolved from data the caller cannot see, so it
        is printed, with its provenance, before `gh` is reached."""
        code, out, _runner = self._main(self.BUG_ARGS)
        self.assertEqual(code, 0)
        self.assertIn("acme/widgets", out)
        self.assertIn(R.REPO_ENV, out)
        self.assertIn("marketplace", out.lower())

    def test_draft_prints_the_body_and_files_nothing(self):
        """Every gh call a draft makes must be a read, and a cheap one: asserting only
        `creates` is empty let the label list — a filing-path cost — slip onto this
        path unnoticed."""
        code, out, runner = self._main(self.BUG_ARGS + ["--draft"])
        self.assertEqual(code, 0)
        self.assertEqual([argv[:2] for argv, _kw in runner.calls], [["gh", "api"]])
        self.assertIn("atelier: covenant never injected", out)
        self.assertIn("## What happens", out)

    def test_draft_names_the_target_repo_and_its_provenance(self):
        _code, out, _runner = self._main(self.BUG_ARGS + ["--draft"])
        self.assertIn("acme/widgets", out)
        self.assertIn(R.REPO_ENV, out)
        self.assertIn("marketplace", out.lower())

    def test_manifest_resolved_target_names_the_manifest(self):
        """The provenance half of the same line: with no env override the target came
        from this plugin's manifest, and saying so is what lets a reader catch a
        report about someone else's plugin heading into the wrong tracker."""
        root = os.path.join(self.tmp.name, "plugin")
        meta = os.path.join(root, ".claude-plugin")
        os.makedirs(meta, exist_ok=True)
        with open(os.path.join(meta, "plugin.json"), "w", encoding="utf-8") as fh:
            json.dump({"name": "demo", "repository": "acme/from-manifest"}, fh)
        _code, out, _runner = self._main(
            self.BUG_ARGS + ["--draft"], env={R.REPO_ENV: "", "CLAUDE_PLUGIN_ROOT": root}
        )
        self.assertIn("acme/from-manifest", out)
        self.assertIn("manifest", out)

    def test_severity_defaults_to_the_least_severe(self):
        """An agent that never considered severity must not file a `major`. An
        under-marked report costs a maintainer one upgrade at read time; a queue where
        everything arrives `major` carries no priority signal at all."""
        self.assertEqual(R.DEFAULT_SEVERITY, R.SEVERITIES[-1])
        self.assertEqual(R.DEFAULT_SEVERITY, "minor")
        _code, out, _runner = self._main(self.BUG_ARGS + ["--draft"])
        self.assertIn("**Severity:** minor", out)

    def test_date_defaults_to_the_injected_clock(self):
        _code, out, _runner = self._main(self.BUG_ARGS + ["--draft"], today="2026-01-02")
        self.assertIn("**Observed:** 2026-01-02", out)

    def test_bug_without_a_contract_is_a_usage_error(self):
        argv = [a for a in self.BUG_ARGS]
        del argv[argv.index("--contract"):]
        code, out, runner = self._main(argv)
        self.assertEqual(code, 2)
        self.assertEqual(runner.creates, [])
        self.assertIn("--contract", out)

    def test_feature_without_a_limitation_is_a_usage_error(self):
        argv = ["feature"] + self.BUG_ARGS[1:]
        del argv[argv.index("--contract"):]
        code, out, runner = self._main(argv)
        self.assertEqual(code, 2)
        self.assertEqual(runner.creates, [])
        self.assertIn("--limitation", out)

    def test_unresolvable_repo_refuses_and_names_the_env_var(self):
        code, out, runner = self._main(self.BUG_ARGS, env={R.REPO_ENV: ""})
        self.assertEqual(code, 2)
        self.assertEqual(runner.creates, [])
        self.assertIn(R.REPO_ENV, out)

    def test_draft_works_without_a_resolvable_repo(self):
        """A worker drafting a feature request for its dispatcher must not need the
        target repo resolved — that is the dispatcher's problem at filing time."""
        argv = ["feature"] + self.BUG_ARGS[1:]
        argv[argv.index("--contract")] = "--limitation"
        code, out, _runner = self._main(argv + ["--draft"], env={R.REPO_ENV: ""})
        self.assertEqual(code, 0)
        self.assertIn("## What happens", out)

    def test_gh_failure_is_reported_as_nonzero(self):
        code, _out, runner = self._main(self.BUG_ARGS, runner=_FakeRunner(returncode=1))
        self.assertEqual(code, 1)
        self.assertEqual(len(runner.creates), 1)

    # -- the scope boundary, checked rather than described ------------------

    def _unlisted(self, *extra):
        """BUG_ARGS naming a plugin this marketplace's manifest does not list."""
        argv = list(self.BUG_ARGS)
        argv[argv.index("--plugin") + 1] = "some-other-marketplaces-plugin"
        return argv + list(extra)

    def test_a_plugin_this_marketplace_does_not_ship_is_refused(self):
        """The incident this exists for: a defect in a plugin from somewhere else was
        filed here, where no maintainer could act on it. Prose said not to; nothing
        checked. The refusal names what IS shipped so a typo is self-correcting."""
        code, out, runner = self._main(self._unlisted())
        self.assertEqual(code, 2)
        self.assertEqual(runner.creates, [])
        self.assertIn("atelier", out)
        self.assertIn("--allow-unlisted", out)

    def test_a_draft_is_refused_the_same_way(self):
        """A draft is a read of the same boundary, and a dispatcher handed a
        misdirected draft is exactly the reader this is meant to stop."""
        code, out, runner = self._main(self._unlisted("--draft"))
        self.assertEqual(code, 2)
        self.assertEqual(runner.creates, [])
        self.assertNotIn("## What happens", out)

    def test_the_override_files_it_anyway(self):
        """A stale manifest must not be able to hold a real report hostage — the
        boundary is a check with a documented way past it, not a wall."""
        code, _out, runner = self._main(self._unlisted("--allow-unlisted"))
        self.assertEqual(code, 0)
        self.assertEqual(len(runner.creates), 1)

    def _marketplace_at(self, path, names):
        """A marketplace manifest on disk, listing `names`."""
        meta = os.path.join(path, ".claude-plugin")
        os.makedirs(meta, exist_ok=True)
        with io.open(os.path.join(meta, "marketplace.json"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"plugins": [{"name": n} for n in names]}))

    def test_a_local_hit_answers_without_asking_gh(self):
        """A checkout carries the answer already; paying for a network read to learn
        what is on disk beside you is the cost this fast path exists to avoid."""
        root = os.path.join(self.tmp.name, "checkout", "plugin")
        os.makedirs(root)
        self._marketplace_at(os.path.join(self.tmp.name, "checkout"), ["atelier"])
        code, _out, runner = self._main(self.BUG_ARGS, env={"CLAUDE_PLUGIN_ROOT": root})
        self.assertEqual(code, 0)
        self.assertNotIn(["gh", "api"], [argv[:2] for argv, _kw in runner.calls])

    def test_a_manifest_from_another_tree_cannot_refuse_a_shipped_plugin(self):
        """The local read may only ever ALLOW. Whatever manifest happens to sit above
        the plugin root is some other tree's roster, and refusing on it turns a plugin
        this marketplace really does ship into an unfileable one."""
        root = os.path.join(self.tmp.name, "outer", "plugin")
        os.makedirs(root)
        self._marketplace_at(os.path.join(self.tmp.name, "outer"), ["someone-elses-plugin"])
        code, out, runner = self._main(self.BUG_ARGS, env={"CLAUDE_PLUGIN_ROOT": root})
        self.assertEqual(code, 0, out)
        self.assertEqual(len(runner.creates), 1)

    def test_the_walk_stops_at_the_enclosing_repo_root(self):
        """A manifest above the repo the plugin lives in is not this marketplace's, so
        it is never read: with gh unable to answer, the check is undeterminable rather
        than answered out of a stranger's file."""
        repo = os.path.join(self.tmp.name, "outer", "repo")
        root = os.path.join(repo, "plugin")
        os.makedirs(root)
        self._marketplace_at(os.path.join(self.tmp.name, "outer"), ["atelier"])
        with io.open(os.path.join(repo, ".git"), "w", encoding="utf-8") as fh:
            fh.write("gitdir: elsewhere\n")
        _code, out, _runner = self._main(
            self.BUG_ARGS, env={"CLAUDE_PLUGIN_ROOT": root}, runner=_BlindRunner()
        )
        self.assertIn("membership check", out)

    def test_an_unreadable_plugin_list_fails_open(self):
        """No plugin list, no check: a network blip must not swallow a report. The
        notice is what keeps the waiver visible instead of silent."""
        code, out, runner = self._main(self._unlisted(), runner=_BlindRunner())
        self.assertEqual(code, 0)
        self.assertEqual(len(runner.creates), 1)
        self.assertIn("membership check", out)

    def test_a_full_page_of_labels_reads_as_unknown(self):
        """gh pages the label list, so a response filling the page may be a truncated
        one. Read as complete, it strips a label the repo does carry."""
        runner = _FakeRunner()
        runner.LABELS = tuple("label-{0}".format(i) for i in range(R.LABEL_PAGE))
        code, out, runner = self._main(self.BUG_ARGS, runner=runner)
        self.assertEqual(code, 0)
        self.assertIn("--label", runner.creates[0])
        self.assertNotIn("filing unlabelled", out)

    def test_a_label_the_repo_does_not_carry_is_dropped_before_filing(self):
        """AC#2's half: the default label is checked against the repo's live set, so a
        rename costs a notice rather than a failed call the filer has to interpret."""
        runner = _FakeRunner()
        runner.LABELS = ("something-else",)
        code, out, runner = self._main(self.BUG_ARGS, runner=runner)
        self.assertEqual(code, 0)
        self.assertNotIn("--label", runner.creates[0])
        self.assertIn("filing unlabelled", out)
        self.assertIn(R.LABEL_ENV[R.KIND_BUG], out)


@unittest.skipUnless(os.environ.get(LIVE_TESTS_ENV), LIVE_TESTS_ENV + " is not set")
class LiveLabelTests(unittest.TestCase):
    """The one network-touching test in this file, and the only thing that can catch a
    label rename in the target repo: every other assertion here is against a fixture,
    which is exactly how a hardcoded default stayed wrong through two field filings.

    Opt-in, and the gh probe runs inside the test rather than at import — a probe in a
    decorator or at module scope shells out just for importing this file, which would put
    a network call inside `make ci`, where this repo keeps none."""

    def _live_labels(self):
        """The target repo's real labels, or a skip when gh cannot answer at all."""
        if not shutil.which("gh"):
            self.skipTest("gh is not installed")
        with io.open(PLUGIN_MANIFEST, encoding="utf-8") as fh:
            repo = R.normalize_repo(json.load(fh).get("repository"))
        self.assertIsNotNone(repo, "plugin manifest carries no resolvable repository")
        try:
            done = subprocess.run(
                ["gh", "label", "list", "--repo", repo, "--json", "name", "--limit", "200"],
                capture_output=True, text=True, timeout=10,
            )
            labels = {e["name"] for e in json.loads(done.stdout)} if not done.returncode else None
        except Exception:
            labels = None
        if not labels:
            self.skipTest("gh could not read {0}'s labels".format(repo))
        return labels

    def test_every_default_label_exists_in_the_target_repo(self):
        live = self._live_labels()
        for kind, label in sorted(R.DEFAULT_LABELS.items()):
            with self.subTest(kind=kind):
                self.assertIn(
                    label, live,
                    "default {0} label {1!r} is not a label the target repo carries".format(
                        kind, label
                    ),
                )


if __name__ == "__main__":
    unittest.main()
