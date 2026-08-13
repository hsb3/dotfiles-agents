"""Tests for primitives-core/hooks/session-handoff-surfacer/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a
JSON line on stdout only when surfacing) against a hand-written
.claude/atelier.local.md activation file and candidate handoff files.
Stdlib-only; fixtures build into a tempdir per test, and the environment
passed to the subprocess is built from scratch with only PATH inherited.
"""

import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "session-handoff-surfacer", "hook.py",
)

_SEQ = itertools.count()

STAMP = ".claude/handoff.stamp"
LOCATION = "Kaneo board task DFA-233"

# Written into the stamp file itself. External mode must surface a POINTER, so
# nothing from inside the stamp may ever reach stdout.
SENTINEL = "STAMP-CONTENTS-MUST-NEVER-BE-SURFACED"


def _session_id():
    return f"handoff-surfacer-session-{next(_SEQ)}"


class SessionHandoffSurfacerOverrideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.log_path = os.path.join(self.tmp.name, "logs", "handoff-surfacer.jsonl")

    # -- fixtures ------------------------------------------------------

    def _write_activation(self, raw_text=None, handoff=None):
        claude_dir = os.path.join(self.cwd, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        path = os.path.join(claude_dir, "atelier.local.md")
        if raw_text is None:
            lines = ["---"]
            if handoff is not None:
                lines.append("handoff: {0}".format(handoff))
            lines.append("---")
            raw_text = "\n".join(lines) + "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(raw_text)
        return path

    def _write_mapping(self, **children):
        """The mapping form of `handoff:` — an empty value, one level of
        indented sub-keys. Children given as None are omitted entirely."""
        lines = ["---", "handoff:"]
        for key, value in children.items():
            if value is not None:
                lines.append("  {0}: {1}".format(key, value))
        lines.append("---")
        return self._write_activation(raw_text="\n".join(lines) + "\n")

    def _write_file(self, relpath, content="content\n"):
        full = os.path.join(self.cwd, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full

    def _log_records(self):
        with open(self.log_path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def _payload(self, source="startup", session_id=None):
        return {
            "session_id": session_id or _session_id(),
            "hook_event_name": "SessionStart",
            "source": source,
            "cwd": self.cwd,
        }

    def _run_hook(self, payload):
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HANDOFF_SURFACER_LOG_PATH": self.log_path,
        }
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def _assert_silent(self, result):
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def _surfaced_relpath(self, result):
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        msg = body["systemMessage"]
        # "atelier: surfaced project handoff (<relpath>)."
        return msg.split("(", 1)[1].rsplit(")", 1)[0]

    def _surfaced(self, result):
        """(additionalContext, systemMessage) for a surfacing run."""
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        self.assertEqual(
            body["hookSpecificOutput"]["hookEventName"], "SessionStart")
        return (body["hookSpecificOutput"]["additionalContext"],
                body["systemMessage"])

    # -- tests -----------------------------------------------------------

    def test_override_absent_standard_search_unaffected(self):
        """BACKWARD COMPAT: no activation file at all -- byte-identical to
        pre-external-mode behavior, the standard candidate-path search finds
        HANDOFF.md and the excerpt is unchanged."""
        self._write_file("HANDOFF.md", "root handoff\n")
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")
        body = json.loads(result.stdout)
        self.assertEqual(
            body["hookSpecificOutput"]["additionalContext"],
            "A project handoff exists at HANDOFF.md — read it before starting. "
            "First lines:\nroot handoff",
        )

    def test_override_existing_file_wins_over_standard_candidate(self):
        """BACKWARD COMPAT: the bare-path scalar form still wins and still
        carries the head excerpt, asserted as the exact whole message."""
        self._write_file("_meta/HANDOFF.md", "meta handoff\n")  # highest-precedence trio candidate
        self._write_file("docs/HANDOFF.md", "override handoff\n")
        self._write_activation(handoff="docs/HANDOFF.md")
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "docs/HANDOFF.md")
        context, system = self._surfaced(result)
        self.assertEqual(
            context,
            "A project handoff exists at docs/HANDOFF.md — read it before "
            "starting. First lines:\noverride handoff",
        )
        self.assertEqual(system, "atelier: surfaced project handoff (docs/HANDOFF.md).")

    def test_override_nonexistent_path_does_not_fall_back(self):
        """BACKWARD COMPAT: a named-but-absent file still means silence, not
        a fall back to the trio."""
        self._write_file("HANDOFF.md", "root handoff\n")  # would be found by standard search
        self._write_activation(handoff="docs/HANDOFF.md")  # never created
        result = self._run_hook(self._payload())
        self._assert_silent(result)

    def test_override_outside_project_root_falls_back(self):
        """BACKWARD COMPAT: an escaping scalar path stays fail-open."""
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_activation(handoff="/etc/hosts")  # exists, but outside project root
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    def test_unparseable_activation_falls_back(self):
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_activation(raw_text="not even yaml, just noise\n")
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    def test_activation_with_other_keys_not_handoff_falls_back(self):
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_activation(raw_text="---\nenforce: strict\n---\n")
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    # -- external mode: armed ---------------------------------------------

    def test_external_cold_start_surfaces_a_pointer_never_the_stamp_contents(self):
        self._write_file("_meta/HANDOFF.md", "stale repo handoff\n")  # trio, must lose
        self._write_file(STAMP, SENTINEL + "\n")
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload(source="startup"))
        context, system = self._surfaced(result)
        self.assertEqual(
            context,
            "This project's handoff lives outside the repo: Kaneo board task "
            "DFA-233. Read it before starting. Its freshness stamp is "
            ".claude/handoff.stamp.",
        )
        self.assertEqual(
            system,
            "atelier: surfaced external handoff pointer (Kaneo board task DFA-233).",
        )
        self.assertNotIn(SENTINEL, result.stdout)
        self.assertNotIn("stale repo handoff", result.stdout)

    def test_external_cold_start_surfaces_even_when_the_stamp_does_not_exist(self):
        """The #319 defect: a cold session on a board-handoff project got
        nothing at all. The stamp is only a freshness signal -- the handoff
        is on the board whether or not anything has touched the stamp."""
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload(source="startup"))
        context, system = self._surfaced(result)
        self.assertEqual(
            context,
            "This project's handoff lives outside the repo: Kaneo board task "
            "DFA-233. Read it before starting. Its freshness stamp is "
            ".claude/handoff.stamp.",
        )
        self.assertEqual(
            system,
            "atelier: surfaced external handoff pointer (Kaneo board task DFA-233).",
        )

    def test_external_cold_start_without_location_asks_where_the_handoff_lives(self):
        self._write_file(STAMP, SENTINEL + "\n")
        self._write_mapping(mode="external", stamp=STAMP)
        result = self._run_hook(self._payload(source="startup"))
        context, system = self._surfaced(result)
        self.assertEqual(
            context,
            "This project's handoff lives outside the repo — its freshness "
            "stamp is .claude/handoff.stamp, but this project set no location. "
            "Ask the user where the handoff lives.",
        )
        self.assertEqual(
            system,
            "atelier: surfaced external handoff pointer (stamp .claude/handoff.stamp).",
        )
        self.assertNotIn(SENTINEL, result.stdout)

    def test_external_clear_source_also_counts_as_cold(self):
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload(source="clear"))
        self.assertIn("Kaneo board task DFA-233", self._surfaced(result)[0])

    def test_external_warm_sources_stay_silent(self):
        """Unchanged from today: resume/compact already have the context."""
        for source in ("resume", "compact"):
            with self.subTest(source=source):
                self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
                result = self._run_hook(self._payload(source=source))
                self._assert_silent(result)

    def test_external_logs_the_mode_and_the_relative_stamp_path(self):
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        self._run_hook(self._payload(source="startup"))
        record = self._log_records()[-1]
        self.assertEqual(record["handoff_mode"], "external")
        self.assertEqual(record["handoff_path"], STAMP)
        self.assertIs(record["surfaced"], True)

    # -- external mode: inert shapes fall back to the trio -----------------
    #
    # As in the freshness guard's suite, these also pass against the
    # pre-external-mode hook -- "unusable config behaves as if the key were
    # absent" is defined as the OLD behavior. They guard the new parser
    # against arming on a shape it now understands.

    def test_external_without_a_stamp_falls_back_to_the_trio(self):
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_mapping(mode="external", location=LOCATION)
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    def test_external_with_an_out_of_root_stamp_falls_back_to_the_trio(self):
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_mapping(mode="external", stamp="../../etc/hosts",
                            location=LOCATION)
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    def test_unknown_mode_falls_back_to_the_trio(self):
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_mapping(mode="board", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    # -- file mode written as a mapping ------------------------------------

    def test_file_mode_mapping_with_a_path_matches_the_bare_scalar_form(self):
        """Form B `{mode: file, path: X}` is defined as identical to Form A
        `handoff: X` -- asserted as identical output, not merely similar."""
        self._write_file("HANDOFF.md", "root handoff\n")  # trio, must stay unused
        self._write_file("docs/HANDOFF.md", "override handoff\n")

        self._write_mapping(mode="file", path="docs/HANDOFF.md")
        mapping_result = self._run_hook(self._payload())

        self._write_activation(handoff="docs/HANDOFF.md")
        scalar_result = self._run_hook(self._payload())

        self.assertEqual(mapping_result.stdout, scalar_result.stdout)
        self.assertEqual(self._surfaced_relpath(mapping_result), "docs/HANDOFF.md")

    def test_file_mode_mapping_without_a_path_falls_back_to_the_trio(self):
        self._write_file("HANDOFF.md", "root handoff\n")
        self._write_mapping(mode="file")
        result = self._run_hook(self._payload())
        self.assertEqual(self._surfaced_relpath(result), "HANDOFF.md")

    def test_malformed_stdin_fails_open(self):
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input="not json",
            capture_output=True,
            text=True,
            env={"PATH": os.environ.get("PATH", ""), "HANDOFF_SURFACER_LOG_PATH": self.log_path},
            timeout=30,
        )
        self._assert_silent(result)


if __name__ == "__main__":
    unittest.main()
