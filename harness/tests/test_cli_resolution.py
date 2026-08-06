"""cli.main — candidate resolution (flat .md staging, exit-code contract).

Drives ``agent_harness.cli.main`` end to end with a stubbed adapter (no live
CLI, no subprocess) so we can assert resolution reaches the run stage for a
flat agent ``.md`` file, and that the exit-2 contract holds for the paths
that must never resolve — following the stub style of test_core.py.
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness import cli  # noqa: E402
from agent_harness.adapters.base import Adapter  # noqa: E402


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class _StubAdapter(Adapter):
    """Cheap stand-in: preflight ok, never actually invokes a subprocess."""

    name = "stub"

    def __init__(self, **_ignored):
        pass

    def preflight(self):
        return "ok"

    def cli_version(self):
        return "stub-0"

    def inject(self, kind, candidate_dir, tmpdir):  # pragma: no cover - unused
        raise AssertionError("inject must not be reached in these tests")

    def invocation(self, prompt, workspace, model, injection):  # pragma: no cover
        raise AssertionError("invocation must not be reached in these tests")

    def parse_log(self, raw):  # pragma: no cover - unused
        raise AssertionError("parse_log must not be reached in these tests")

    def success(self, returncode, record):  # pragma: no cover - unused
        raise AssertionError("success must not be reached in these tests")


class CliResolutionTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)


class TestFlatMdResolutionReachesRunStage(CliResolutionTestBase):
    def test_flat_md_candidate_dir_resolves_and_reaches_run_candidate(self):
        md = os.path.join(self.tmp, "solo-agent.md")
        _write(md, "---\nname: solo-agent\n---\nprompt body")

        calls = []

        def _fake_run_candidate(adapter, candidate, kind, candidate_dir, args):
            # Resolution must have staged a *directory* containing the .md,
            # distinct from the flat file path passed on the command line.
            self.assertTrue(os.path.isdir(candidate_dir))
            self.assertNotEqual(candidate_dir, md)
            self.assertTrue(os.path.isfile(os.path.join(candidate_dir, "solo-agent.md")))
            self.assertEqual(kind, "agent")
            calls.append(candidate_dir)

        with (
            mock.patch.object(cli, "get_adapter", return_value=_StubAdapter()),
            mock.patch.object(cli, "run_candidate", side_effect=_fake_run_candidate),
        ):
            rc = cli.main(["solo-agent", "--candidate-dir", md])

        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 1)
        # Staged dir is cleaned up once the run completes.
        self.assertFalse(os.path.exists(calls[0]))

    def test_flat_md_candidate_dir_reaches_smoke_stage(self):
        md = os.path.join(self.tmp, "solo-agent.md")
        _write(md, "---\nname: solo-agent\n---\nprompt body")

        def _fake_smoke(adapter, candidate, kind, candidate_dir, args):
            self.assertTrue(os.path.isdir(candidate_dir))
            self.assertEqual(kind, "agent")
            return True

        with (
            mock.patch.object(cli, "get_adapter", return_value=_StubAdapter()),
            mock.patch.object(cli, "smoke", side_effect=_fake_smoke),
        ):
            rc = cli.main(["solo-agent", "--candidate-dir", md, "--smoke"])

        self.assertEqual(rc, 0)


class TestResolverErrorNarrowScope(CliResolutionTestBase):
    def test_value_error_from_run_candidate_propagates_not_exit_2(self):
        """A ValueError raised *inside* the run (not by the resolver) must
        propagate to the caller — the resolver's try/except is narrowed to
        just the ``resolved_candidate_dir`` call, so this must NOT be
        misreported as a candidate-arg error with exit 2."""
        md = os.path.join(self.tmp, "solo-agent.md")
        _write(md, "---\nname: solo-agent\n---\nprompt body")

        staged_holder = {}

        def _raising_run_candidate(adapter, candidate, kind, candidate_dir, args):
            staged_holder["path"] = candidate_dir
            raise ValueError("boom")

        with (
            mock.patch.object(cli, "get_adapter", return_value=_StubAdapter()),
            mock.patch.object(cli, "run_candidate", side_effect=_raising_run_candidate),
        ):
            with self.assertRaisesRegex(ValueError, "boom"):
                cli.main(["solo-agent", "--candidate-dir", md])

        # The staged dir is still cleaned up even though the exception
        # propagated out of the `with stack:` body.
        self.assertFalse(os.path.exists(staged_holder["path"]))


class TestExitTwoContract(CliResolutionTestBase):
    def test_missing_candidate_dir_flag_is_exit_2(self):
        with mock.patch.object(cli, "get_adapter", return_value=_StubAdapter()):
            rc = cli.main(["solo-agent"])
        self.assertEqual(rc, 2)

    def test_nonexistent_path_is_exit_2(self):
        missing = os.path.join(self.tmp, "does-not-exist")
        with mock.patch.object(cli, "get_adapter", return_value=_StubAdapter()):
            rc = cli.main(["solo-agent", "--candidate-dir", missing])
        self.assertEqual(rc, 2)

    def test_non_md_file_is_exit_2(self):
        f = os.path.join(self.tmp, "notes.txt")
        _write(f, "not markdown")
        with mock.patch.object(cli, "get_adapter", return_value=_StubAdapter()):
            rc = cli.main(["solo-agent", "--candidate-dir", f])
        self.assertEqual(rc, 2)

    def test_unrecognizable_dir_is_exit_2(self):
        d = os.path.join(self.tmp, "unrecognizable")
        os.makedirs(d)
        _write(os.path.join(d, "README.md"), "readme only")
        with mock.patch.object(cli, "get_adapter", return_value=_StubAdapter()):
            rc = cli.main(["solo-agent", "--candidate-dir", d])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
