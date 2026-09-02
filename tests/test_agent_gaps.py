"""agent_gaps.py — gap attribution over synthetic subagent transcripts.

Fixtures are built in a tempdir at the real on-disk depth
(`<root>/<slug>/<session_id>/subagents/agent-<id>.jsonl`), so the walker's glob is
exercised for real rather than simulated. No file under ~/.claude is read: every
assertion here is against bytes this module wrote.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import agent_gaps as G  # noqa: E402

T0 = datetime(2026, 8, 23, 22, 0, 0, tzinfo=timezone.utc)


def ts(offset):
    """ISO-8601 Z stamp `offset` seconds after T0, in the shape real transcripts use."""
    return (T0 + timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def user_event(offset, text="ok"):
    return {"type": "user", "timestamp": ts(offset), "message": {"role": "user", "content": text}}


def result_event(offset):
    return {
        "type": "user",
        "timestamp": ts(offset),
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "done"}]},
    }


def tool_event(offset, name, tool_input):
    return {
        "type": "assistant",
        "timestamp": ts(offset),
        "message": {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": ""},
                {"type": "tool_use", "name": name, "input": tool_input},
            ],
        },
    }


def text_event(offset, text="thinking out loud"):
    return {
        "type": "assistant",
        "timestamp": ts(offset),
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


UNCONDITIONAL = "for i in $(seq 1 60); do command sleep 10; done"
POLL = 'for i in $(seq 1 30); do if curl -s x; then break; fi; sleep 5; done'


def write_transcript(root, slug, session, agent, events, extra_lines=()):
    d = os.path.join(root, slug, session, "subagents")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "agent-%s.jsonl" % agent)
    lines = [json.dumps(e) for e in events]
    lines.extend(extra_lines)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


class FixtureCorpus(unittest.TestCase):
    """Three transcripts covering every bucket the report can emit.

    A: a commanded 600s unconditional sleep, a sub-threshold gap, a 100s poll gap.
    B: a 300s Agent gap, plus one unparseable line.
    C: a 200s gap before any tool_use (`none`), then an 80s Read gap.
    """

    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="agent-gaps-")
        cls.a = write_transcript(
            cls.root, "-Users-henry-proj", "sess-1", "aaa",
            [
                user_event(0),
                tool_event(10, "Bash", {"command": UNCONDITIONAL}),
                result_event(610),                                   # gap 600 -> unconditional
                tool_event(620, "Bash", {"command": POLL}),          # gap 10  -> below threshold
                result_event(720),                                   # gap 100 -> poll
            ],
        )
        cls.b = write_transcript(
            cls.root, "-Users-henry-proj", "sess-1", "bbb",
            [
                user_event(0),
                tool_event(5, "Agent", {"description": "child work"}),
                result_event(305),                                   # gap 300 -> Agent
            ],
            extra_lines=["{not json at all"],
        )
        cls.c = write_transcript(
            cls.root, "-Users-henry-other", "sess-2", "ccc",
            [
                user_event(0),
                text_event(200),                                     # gap 200 -> none
                tool_event(210, "Read", {"file_path": "/tmp/x"}),
                result_event(290),                                   # gap 80  -> Read
            ],
        )
        cls.report = G.scan(cls.root, 60.0)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def buckets(self):
        return {b["cause"]: b for b in self.report["buckets"]}

    def test_totals(self):
        self.assertEqual(self.report["transcripts"], 3)
        self.assertEqual(self.report["events"], 12)
        self.assertEqual(self.report["unparseable_lines"], 1)
        self.assertEqual(self.report["elapsed_seconds"], 720 + 305 + 290)
        self.assertEqual(self.report["gap_count"], 5)
        self.assertEqual(self.report["gap_seconds"], 600 + 100 + 300 + 200 + 80)

    def test_bucket_seconds(self):
        got = {c: b["seconds"] for c, b in self.buckets().items()}
        self.assertEqual(
            got,
            {
                "Bash:sleep-unconditional": 600.0,
                "Agent": 300.0,
                "none": 200.0,
                "Bash:sleep-poll": 100.0,
                "Read": 80.0,
            },
        )

    def test_bucket_order_is_seconds_desc_then_name(self):
        self.assertEqual(
            [b["cause"] for b in self.report["buckets"]],
            ["Bash:sleep-unconditional", "Agent", "none", "Bash:sleep-poll", "Read"],
        )

    def test_commanded_seconds_on_sleep_buckets_only(self):
        b = self.buckets()
        self.assertEqual(b["Bash:sleep-unconditional"]["commanded_seconds"], 600.0)
        self.assertEqual(b["Bash:sleep-poll"]["commanded_seconds"], 150.0)
        self.assertNotIn("commanded_seconds", b["Agent"])
        self.assertNotIn("commanded_seconds", b["none"])

    def test_shares(self):
        b = self.buckets()["Bash:sleep-unconditional"]
        self.assertAlmostEqual(b["share_of_gaps"], 600.0 / 1280.0, places=6)
        self.assertAlmostEqual(b["share_of_elapsed"], 600.0 / 1315.0, places=6)
        self.assertAlmostEqual(self.report["gap_share_of_elapsed"], 1280.0 / 1315.0, places=6)

    def test_unexplained_is_stated_explicitly(self):
        u = self.report["unexplained"]
        self.assertEqual(u["seconds"], 200.0)
        self.assertEqual(u["count"], 1)
        self.assertAlmostEqual(u["share_of_gaps"], 200.0 / 1280.0, places=6)

    def test_top_gaps(self):
        rep = G.scan(self.root, 60.0, top=3)
        self.assertEqual([g["seconds"] for g in rep["top"]], [600.0, 300.0, 200.0])
        self.assertEqual(rep["top"][0]["cause"], "Bash:sleep-unconditional")
        self.assertEqual(rep["top"][0]["path"], self.a)
        self.assertEqual(rep["top"][0]["command"], UNCONDITIONAL)
        self.assertIsNone(rep["top"][2]["command"])

    def test_command_excerpt_is_capped_at_100_chars(self):
        long_cmd = "for i in $(seq 1 60); do command sleep 10; done # " + "x" * 300
        root = tempfile.mkdtemp(prefix="agent-gaps-long-")
        try:
            write_transcript(root, "slug", "sess", "ddd", [
                user_event(0),
                tool_event(1, "Bash", {"command": long_cmd}),
                result_event(601),
            ])
            rep = G.scan(root, 60.0, top=1)
            self.assertEqual(len(rep["top"][0]["command"]), 100)
            self.assertTrue(long_cmd.startswith(rep["top"][0]["command"]))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_text_mode_names_the_unexplained_bucket(self):
        out = G.render_text(self.report)
        self.assertIn("unexplained", out)
        self.assertIn("200.0", out)


class InCallSplit(unittest.TestCase):
    """A gap starting at the tool_use event was spent INSIDE the call; one starting at
    any later event began after the call already returned, and is charged to that call
    only because the attribution rule has nothing else to charge it to."""

    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="agent-gaps-incall-")
        write_transcript(cls.root, "slug", "sess", "iii", [
            user_event(0),
            tool_event(1, "Bash", {"command": "git diff"}),
            result_event(301),      # gap 300 starting AT the tool_use -> in-call
            text_event(1301),       # gap 1000 starting at the tool_result -> post-call
        ])
        cls.report = G.scan(cls.root, 60.0)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_both_gaps_land_in_the_same_cause_bucket(self):
        self.assertEqual([b["cause"] for b in self.report["buckets"]], ["Bash"])
        self.assertEqual(self.report["buckets"][0]["seconds"], 1300.0)

    def test_bucket_carries_the_in_call_share(self):
        self.assertEqual(self.report["buckets"][0]["in_call_seconds"], 300.0)

    def test_report_totals_split_in_call_from_post_call(self):
        self.assertEqual(self.report["in_call_seconds"], 300.0)
        self.assertEqual(self.report["post_call_seconds"], 1000.0)

    def test_top_gaps_carry_the_flag(self):
        rep = G.scan(self.root, 60.0, top=2)
        self.assertEqual([g["in_call"] for g in rep["top"]], [False, True])

    def test_text_mode_states_the_split(self):
        self.assertIn("after the last call returned", G.render_text(self.report))


class CliBehaviour(unittest.TestCase):
    def run_cli(self, argv):
        import io

        buf = io.StringIO()
        code = G.main(argv, buf)
        return code, buf.getvalue()

    def test_empty_root_exits_zero(self):
        root = tempfile.mkdtemp(prefix="agent-gaps-empty-")
        try:
            code, out = self.run_cli(["--root", root])
            self.assertEqual(code, 0)
            self.assertIn("0 transcripts", out)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_empty_root_json_exits_zero(self):
        root = tempfile.mkdtemp(prefix="agent-gaps-empty-")
        try:
            code, out = self.run_cli(["--root", root, "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["transcripts"], 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_json_output_is_stable_across_runs(self):
        root = tempfile.mkdtemp(prefix="agent-gaps-stable-")
        try:
            write_transcript(root, "slug", "sess", "eee", [
                user_event(0),
                tool_event(1, "Bash", {"command": UNCONDITIONAL}),
                result_event(601),
            ])
            write_transcript(root, "slug", "sess", "fff", [
                user_event(0),
                tool_event(1, "Agent", {"description": "child"}),
                result_event(601),
            ])
            first = self.run_cli(["--root", root, "--json", "--top", "5"])
            second = self.run_cli(["--root", root, "--json", "--top", "5"])
            self.assertEqual(first, second)
            self.assertEqual(json.loads(first[1])["transcripts"], 2)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_threshold_is_honoured(self):
        root = tempfile.mkdtemp(prefix="agent-gaps-thr-")
        try:
            write_transcript(root, "slug", "sess", "ggg", [
                user_event(0),
                tool_event(1, "Read", {"file_path": "/tmp/x"}),
                result_event(31),
            ])
            self.assertEqual(G.scan(root, 60.0)["gap_count"], 0)
            self.assertEqual(G.scan(root, 30.0)["gap_count"], 1)
        finally:
            shutil.rmtree(root, ignore_errors=True)


class BashSleepClassification(unittest.TestCase):
    """The command-string parser, exercised on shapes taken from the real corpus."""

    def test_seq_loop_without_break_is_unconditional(self):
        self.assertEqual(
            G.bash_bucket("for i in $(seq 1 55); do command sleep 10; done"),
            ("Bash:sleep-unconditional", 550.0),
        )

    def test_seq_loop_with_break_is_a_poll(self):
        self.assertEqual(
            G.bash_bucket('for i in $(seq 1 60); do if [ "$c" = 200 ]; then break; fi; sleep 2; done'),
            ("Bash:sleep-poll", 120.0),
        )

    def test_break_alone_makes_a_loop_a_poll(self):
        # No `if`/`[ `/`&&` in this body: the only exit signal is the `break` token, so
        # this is the case that fails if `break` drops out of the exit-test set.
        self.assertEqual(
            G.bash_bucket("for i in $(seq 1 10); do echo $i; break; sleep 2; done"),
            ("Bash:sleep-poll", 20.0),
        )

    def test_until_loop_head_is_the_terminating_condition(self):
        bucket, commanded = G.bash_bucket(
            "until [ \"$(docker inspect -f '{{.State.Health.Status}}' web)\" = healthy ]; do sleep 3; done"
        )
        self.assertEqual(bucket, "Bash:sleep-poll")
        self.assertIsNone(commanded)

    def test_a_path_ending_in_done_does_not_terminate_the_loop_body(self):
        # Verbatim shape from the corpus: `impl-done` contains a `done` on a \b boundary,
        # which truncates the body to nothing and loses both the break and the trip count.
        self.assertEqual(
            G.bash_bucket(
                "for i in $(seq 1 40); do if [ -f /tmp/wave2/impl-done ]; then break; fi; sleep 15; done; echo waited"
            ),
            ("Bash:sleep-poll", 600.0),
        )

    def test_until_head_is_a_plain_command_not_a_bracket_test(self):
        # Taken verbatim in shape from the corpus: no `[`, no `if`, no literal `grep -q`
        # token (it is `-qE` / `pgrep`), yet both loops exit as soon as the command flips.
        for cmd in (
            'until grep -qE "DoD met|DoD not met" /tmp/log; do sleep 30; done',
            'until ! pgrep -qf "scripts/dod.sh"; do sleep 30; done; echo FINISHED',
        ):
            self.assertEqual(G.bash_bucket(cmd)[0], "Bash:sleep-poll", cmd)

    def test_while_pgrep_head_is_a_poll(self):
        self.assertEqual(
            G.bash_bucket('while pgrep -f "bash scripts/dod.sh" >/dev/null; do sleep 30; done')[0],
            "Bash:sleep-poll",
        )

    def test_while_true_loop_has_no_terminating_condition(self):
        self.assertEqual(
            G.bash_bucket("while true; do sleep 5; done"),
            ("Bash:sleep-unconditional", None),
        )

    def test_bare_sleep_is_unconditional(self):
        self.assertEqual(G.bash_bucket("sleep 45; wc -l logs/delegation.jsonl"), ("Bash:sleep-unconditional", 45.0))

    def test_multiple_bare_sleeps_sum(self):
        self.assertEqual(G.bash_bucket("sleep 4; echo a; sleep 8; echo b"), ("Bash:sleep-unconditional", 12.0))

    def test_unknown_duration_is_none_not_zero(self):
        bucket, commanded = G.bash_bucket("sleep $DELAY; echo done")
        self.assertEqual(bucket, "Bash:sleep-unconditional")
        self.assertIsNone(commanded)

    def test_poll_wins_when_a_command_mixes_both(self):
        bucket, _ = G.bash_bucket(
            "lsof -ti :8095 | xargs kill; sleep 1; for i in $(seq 1 60); do curl -s x && break; sleep 2; done"
        )
        self.assertEqual(bucket, "Bash:sleep-poll")

    def test_command_without_sleep_stays_in_the_plain_bash_bucket(self):
        self.assertEqual(G.bash_bucket("git status --short"), ("Bash", None))

    def test_the_word_sleep_in_prose_is_not_a_sleep_call(self):
        self.assertEqual(G.bash_bucket('echo "sleeping now"'), ("Bash", None))


class TimestampParsing(unittest.TestCase):
    def test_millisecond_z_stamp(self):
        self.assertAlmostEqual(
            G.parse_ts("2026-08-23T22:00:10.500Z") - G.parse_ts("2026-08-23T22:00:00.000Z"), 10.5
        )

    def test_whole_second_z_stamp(self):
        self.assertIsNotNone(G.parse_ts("2026-08-23T22:00:00Z"))

    def test_offset_stamp(self):
        self.assertEqual(G.parse_ts("2026-08-23T18:00:00.000-04:00"), G.parse_ts("2026-08-23T22:00:00.000Z"))

    def test_missing_or_junk_is_none(self):
        self.assertIsNone(G.parse_ts(None))
        self.assertIsNone(G.parse_ts("not-a-time"))


class TimestamplessEvents(unittest.TestCase):
    def test_fork_context_ref_line_does_not_break_the_walk(self):
        root = tempfile.mkdtemp(prefix="agent-gaps-fork-")
        try:
            path = write_transcript(root, "slug", "sess", "hhh", [
                user_event(0),
                tool_event(1, "Bash", {"command": UNCONDITIONAL}),
                result_event(601),
            ])
            with open(path, "r", encoding="utf-8") as fh:
                body = fh.read()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"type": "fork-context-ref", "uuid": "x"}) + "\n" + body)
            rep = G.scan(root, 60.0)
            self.assertEqual(rep["gap_count"], 1)
            self.assertEqual(rep["gap_seconds"], 600.0)
            self.assertEqual(rep["unparseable_lines"], 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)


class ScriptEntryPoint(unittest.TestCase):
    def test_runs_as_a_subprocess_on_an_empty_root(self):
        script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "agent_gaps.py"
        )
        root = tempfile.mkdtemp(prefix="agent-gaps-cli-")
        try:
            proc = subprocess.run(
                [sys.executable, script, "--root", root, "--json"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["gap_count"], 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
