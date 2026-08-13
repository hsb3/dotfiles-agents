"""Tests for primitives-core/hooks/handoff-freshness-guard/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a
JSON line on stdout only on block or non-blocking guidance) against a
hand-written .claude/atelier.local.md activation file and candidate/override
handoff files. Stdlib-only; fixtures build into a tempdir per test, and the
environment passed to the subprocess is built from scratch with only PATH
inherited.
"""

import itertools
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "handoff-freshness-guard", "hook.py",
)

_SEQ = itertools.count()

STALE_SECONDS = 60 * 60  # well past the 30-minute default freshness window

STAMP = ".claude/handoff.stamp"
LOCATION = "Kaneo board task DFA-233"

# The candidate trio, spelled out so the external-mode assertions can prove the
# block text never sends someone whose handoff is on a board to a repo file.
TRIO = ("_meta/HANDOFF.md", "HANDOFF.md", ".claude/HANDOFF.md")


def _session_id():
    return f"handoff-guard-session-{next(_SEQ)}"


class HandoffFreshnessGuardOverrideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.log_path = os.path.join(self.tmp.name, "logs", "handoff-guard.jsonl")

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

    def _write_file(self, relpath, content="content\n", stale=False):
        full = os.path.join(self.cwd, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        if stale:
            old = time.time() - STALE_SECONDS
            os.utime(full, (old, old))
        return full

    def _log_records(self):
        with open(self.log_path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def _payload(self, trigger="manual", session_id=None):
        return {
            "session_id": session_id or _session_id(),
            "hook_event_name": "PreCompact",
            "trigger": trigger,
            "cwd": self.cwd,
        }

    def _run_hook(self, payload):
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HANDOFF_GUARD_LOG_PATH": self.log_path,
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

    def _assert_blocked(self, result):
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        self.assertEqual(body["decision"], "block")
        return body

    # -- tests -----------------------------------------------------------

    def test_override_absent_missing_trio_blocks_manual_with_exact_message(self):
        """BACKWARD COMPAT: no activation file, no candidates at all --
        byte-identical to pre-external-mode behavior, blocking manual
        compaction with a message naming the standard trio."""
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertEqual(
            body["reason"],
            "No handoff file found (_meta/HANDOFF.md, HANDOFF.md, or "
            ".claude/HANDOFF.md) — run /handoff first, then /compact.",
        )

    def test_override_absent_missing_trio_auto_never_blocks_exact_message(self):
        """BACKWARD COMPAT: the no-key auto-trigger message is unchanged."""
        result = self._run_hook(self._payload(trigger="auto"))
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        self.assertNotIn("decision", body)
        self.assertEqual(
            body["systemMessage"],
            "Auto-compaction is proceeding with a stale/missing handoff "
            "file. Run /handoff soon to avoid losing externalized state "
            "on the next compaction.",
        )

    def test_override_existing_file_wins_over_stale_standard_candidate(self):
        """BACKWARD COMPAT: the bare-path scalar form still takes full
        precedence over the trio."""
        self._write_file("_meta/HANDOFF.md", stale=True)  # trio: stale, would block alone
        self._write_file("docs/HANDOFF.md")  # override: fresh
        self._write_activation(handoff="docs/HANDOFF.md")
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)  # fresh override wins -> allowed silently

    def test_override_stale_file_blocks_manual_with_exact_message(self):
        """BACKWARD COMPAT: the stale-file block text, asserted exactly. It
        is the one file-mode string external mode has a rival for, so a
        regression here would be a message swapped between the two modes."""
        self._write_file("docs/HANDOFF.md", stale=True)
        self._write_activation(handoff="docs/HANDOFF.md")
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertEqual(
            body["reason"],
            "Handoff is stale/missing — run /handoff first, then /compact.",
        )
        self.assertEqual(body["systemMessage"], body["reason"])

    def test_override_nonexistent_path_does_not_fall_back(self):
        """BACKWARD COMPAT: a named-but-absent file blocks naming that file,
        with the pre-external-mode string byte for byte."""
        self._write_file("HANDOFF.md")  # fresh trio candidate, would allow if searched
        self._write_activation(handoff="docs/HANDOFF.md")  # never created
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertEqual(
            body["reason"],
            "No handoff file found (docs/HANDOFF.md) — run /handoff first, "
            "then /compact.",
        )
        self.assertNotIn("_meta/HANDOFF.md, HANDOFF.md", body["reason"])

    def test_override_outside_project_root_falls_back(self):
        """BACKWARD COMPAT: an escaping scalar path stays fail-open."""
        self._write_file("HANDOFF.md")  # fresh trio candidate
        self._write_activation(handoff="/etc/hosts")  # exists, outside project root
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)  # falls back to trio search, which is fresh

    def test_unparseable_activation_falls_back(self):
        self._write_file("HANDOFF.md")
        self._write_activation(raw_text="not even yaml, just noise\n")
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)

    def test_activation_with_other_keys_not_handoff_falls_back(self):
        self._write_file("HANDOFF.md")
        self._write_activation(raw_text="---\nenforce: strict\n---\n")
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)

    # -- external mode: armed ---------------------------------------------

    def test_external_missing_stamp_blocks_manual_naming_the_stamp_and_location(self):
        """The #319 defect: a project whose handoff lives on a board was told
        to create a repo file it must never create."""
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertEqual(
            body["reason"],
            "No handoff signal found (stamp .claude/handoff.stamp has never "
            "been touched; the handoff lives at: Kaneo board task DFA-233) — "
            "update the handoff and touch the stamp, then /compact.",
        )
        self.assertEqual(body["systemMessage"], body["reason"])
        for candidate in TRIO:
            self.assertNotIn(candidate, body["reason"])

    def test_external_missing_stamp_without_location_omits_the_location_clause(self):
        self._write_mapping(mode="external", stamp=STAMP)
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertEqual(
            body["reason"],
            "No handoff signal found (stamp .claude/handoff.stamp has never "
            "been touched) — update the handoff and touch the stamp, then "
            "/compact.",
        )

    def test_external_fresh_stamp_allows_silently(self):
        self._write_file(STAMP)
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)

    def test_external_stale_stamp_blocks_manual_naming_the_stamp_and_location(self):
        self._write_file(STAMP, stale=True)
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertEqual(
            body["reason"],
            "Handoff signal is stale (stamp .claude/handoff.stamp; the handoff "
            "lives at: Kaneo board task DFA-233) — update the handoff and touch "
            "the stamp, then /compact.",
        )
        self.assertEqual(body["systemMessage"], body["reason"])
        for candidate in TRIO:
            self.assertNotIn(candidate, body["reason"])

    def test_external_stale_stamp_without_location_omits_the_location_clause(self):
        self._write_file(STAMP, stale=True)
        self._write_mapping(mode="external", stamp=STAMP)
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertEqual(
            body["reason"],
            "Handoff signal is stale (stamp .claude/handoff.stamp) — update "
            "the handoff and touch the stamp, then /compact.",
        )

    def test_external_stale_stamp_auto_never_blocks(self):
        self._write_file(STAMP, stale=True)
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload(trigger="auto"))
        self.assertEqual(result.returncode, 0)
        body = json.loads(result.stdout)
        self.assertNotIn("decision", body)
        self.assertEqual(
            body["systemMessage"],
            "Auto-compaction is proceeding with a stale/missing handoff signal "
            "(stamp .claude/handoff.stamp). Update the handoff and touch the "
            "stamp soon to avoid losing externalized state on the next "
            "compaction.",
        )

    def test_external_stamp_governs_over_a_fresh_standard_candidate(self):
        """External mode is authoritative: a fresh _meta/HANDOFF.md sitting on
        disk does not rescue a stale stamp, and is never named."""
        self._write_file("_meta/HANDOFF.md")  # fresh trio candidate
        self._write_file(STAMP, stale=True)
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload(trigger="manual"))
        body = self._assert_blocked(result)
        self.assertIn("stamp .claude/handoff.stamp", body["reason"])
        self.assertNotIn("_meta/HANDOFF.md", body["reason"])

    def test_external_armed_logs_the_mode_and_the_absolute_stamp_path(self):
        stamp = self._write_file(STAMP)
        self._write_mapping(mode="external", stamp=STAMP, location=LOCATION)
        self._run_hook(self._payload(trigger="manual"))
        record = self._log_records()[-1]
        self.assertEqual(record["handoff_mode"], "external")
        self.assertEqual(record["handoff_path"], stamp)
        self.assertEqual(record["status"], "fresh")
        self.assertIs(record["blocked"], False)

    def test_file_mode_logs_the_mode_too(self):
        """`handoff_mode` is the one added log field, and file mode carries it
        rather than leaving it unset. The whole key set is asserted, so this
        also catches a pre-existing field dropped while adding the new one."""
        self._write_file("HANDOFF.md")
        self._run_hook(self._payload(trigger="manual"))
        record = self._log_records()[-1]
        self.assertEqual(record["handoff_mode"], "file")
        self.assertEqual(
            sorted(record),
            ["blocked", "cwd", "handoff_age_minutes", "handoff_mode",
             "handoff_path", "session_id", "status", "trigger", "ts"],
        )

    # -- external mode: inert shapes fall back to the trio -----------------
    #
    # These four are the fail-open clauses of the contract, and they are the
    # one group here that also passes against the pre-external-mode hook --
    # necessarily so, since "unusable config behaves as if the key were
    # absent" is defined as the OLD behavior. They are regression guards for
    # the new parser, which now understands these shapes and could arm on
    # one: `activation.py check` is where the same shapes are proven to be
    # newly *reported* as inert.

    def test_external_without_a_stamp_falls_back_to_the_trio(self):
        self._write_file("HANDOFF.md")  # fresh trio candidate
        self._write_mapping(mode="external", location=LOCATION)
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)

    def test_external_with_an_out_of_root_stamp_falls_back_to_the_trio(self):
        self._write_file("HANDOFF.md")
        self._write_mapping(mode="external", stamp="../../etc/hosts",
                            location=LOCATION)
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)

    def test_unknown_mode_falls_back_to_the_trio(self):
        self._write_file("HANDOFF.md")
        self._write_mapping(mode="board", stamp=STAMP, location=LOCATION)
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)

    # -- file mode written as a mapping ------------------------------------

    def test_file_mode_mapping_with_a_path_matches_the_bare_scalar_form(self):
        """Form B `{mode: file, path: X}` is defined as identical to Form A
        `handoff: X` -- asserted as identical output, not merely similar."""
        self._write_file("HANDOFF.md")  # fresh trio candidate, must stay unused
        self._write_mapping(mode="file", path="docs/HANDOFF.md")
        mapping_result = self._run_hook(self._payload(trigger="manual"))

        self._write_activation(handoff="docs/HANDOFF.md")
        scalar_result = self._run_hook(self._payload(trigger="manual"))

        self.assertEqual(mapping_result.stdout, scalar_result.stdout)
        self.assertEqual(
            json.loads(mapping_result.stdout)["reason"],
            "No handoff file found (docs/HANDOFF.md) — run /handoff first, "
            "then /compact.",
        )

    def test_file_mode_mapping_without_a_path_falls_back_to_the_trio(self):
        self._write_file("HANDOFF.md")
        self._write_mapping(mode="file")
        result = self._run_hook(self._payload(trigger="manual"))
        self._assert_silent(result)

    def test_malformed_stdin_fails_open(self):
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input="not json",
            capture_output=True,
            text=True,
            env={"PATH": os.environ.get("PATH", ""), "HANDOFF_GUARD_LOG_PATH": self.log_path},
            timeout=30,
        )
        self._assert_silent(result)


if __name__ == "__main__":
    unittest.main()
