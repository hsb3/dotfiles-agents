"""The plain-file tracker: grammar, readiness, detection, and the triage round trip.

Same principle as test_kata_board.py: the parsing, the readiness rule and the in-place
rewrite are this script's own judgment and can be wrong on their own, so they are tested
directly. Effects are injected (`detect` takes a fake `run`) or pointed at a tempdir;
`main` is called only for the exit-code contract of list/export/apply.

What breaks silently if this drifts: a grammar error that stops being reported drops an
item from every inventory with no trace, an id that stops counting closed or broken files
re-mints a dead id, a blocker that stops gating hands out work before its prerequisite
lands, a `detect` that swallows a failed `gh` files into the wrong tracker, and a
`write_field` that touches more than one line rewrites the history the format promises is
append-only.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "primitives-core", "skills", "waves", "scripts")

sys.path.insert(0, SCRIPTS)

import file_tracker as ft  # noqa: E402

BODY = (
    "Free text.\n\n## Acceptance criteria\n- [ ] it works\n\n"
    "## Log\n- 2026-10-11 triage: P1, on the demo path\n"
)
GITHUB = "origin\tgit@github.com:o/r.git (fetch)\norigin\tgit@github.com:o/r.git (push)\n"
GITLAB = "origin\thttps://gitlab.com/o/r.git (fetch)\n"


def render(n, title=None, status="open", priority="", labels=(), blocked=(), body=BODY):
    """An item file exactly as the format writes it: `priority:` has no trailing space."""
    return (
        "---\n"
        f"id: t{n}\n"
        f"title: {title or f'Item {n}'}\n"
        f"status: {status}\n"
        f"priority:{' ' + priority if priority else ''}\n"
        f"labels: [{', '.join(labels)}]\n"
        f"blocked-by: [{', '.join(blocked)}]\n"
        "---\n" + body
    )


def run_main(argv):
    """(exit code, stdout, stderr); a SystemExit becomes its code instead of escaping."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = ft.main(argv)
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


def fake_run(remotes="", remotes_rc=0, issues="[]", issues_rc=0, issues_err="", gh_missing=False):
    """A `run` that answers `git remote -v` and `gh issue list` and records every call."""
    calls = []

    def run(argv, **_):
        calls.append(argv)
        if argv[0] == "git":
            return subprocess.CompletedProcess(argv, remotes_rc, remotes, "")
        assert argv[0] == "gh", argv
        if gh_missing:
            raise FileNotFoundError("gh")
        return subprocess.CompletedProcess(argv, issues_rc, issues, issues_err)

    run.calls = calls
    return run


class TrackerCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.tasks = os.path.join(self.root, ".tasks")

    def put(self, name, text):
        os.makedirs(self.tasks, exist_ok=True)
        with open(os.path.join(self.tasks, name), "w", encoding="utf-8") as handle:
            handle.write(text)

    def item(self, n, **kwargs):
        self.put(f"t{n}.md", render(n, **kwargs))

    def read(self, name):
        with open(os.path.join(self.tasks, name), encoding="utf-8") as handle:
            return handle.read()

    def tree(self):
        """Every file under the root -> bytes, so 'wrote nothing' includes new files."""
        found = {}
        for base, _, names in os.walk(self.root):
            for name in names:
                path = os.path.join(base, name)
                with open(path, "rb") as handle:
                    found[os.path.relpath(path, self.root)] = handle.read()
        return found


class Parse(TrackerCase):
    def parse(self, text, name="t1.md"):
        self.put(name, text)
        return ft.parse(os.path.join(self.tasks, name))

    def test_a_valid_item_carries_every_key_and_lists_are_lists(self):
        fields, problems = self.parse(
            render(1, title="Time out hung scans", priority="P1",
                   labels=["type:fix", "area:scanner"], blocked=["t9"])
        )
        self.assertEqual([], problems)
        self.assertEqual(list(ft.KEYS), list(fields))
        self.assertEqual("t1", fields["id"])
        self.assertEqual("open", fields["status"])
        self.assertEqual("P1", fields["priority"])
        self.assertEqual(["type:fix", "area:scanner"], fields["labels"])
        self.assertEqual(["t9"], fields["blocked-by"])

    def test_unset_values_are_empty_not_missing(self):
        text = render(1)
        self.assertIn("\npriority:\n", text, "the fixture must have no trailing space")
        fields, problems = self.parse(text)
        self.assertEqual([], problems)
        self.assertEqual("", fields["priority"])
        self.assertEqual([], fields["labels"])
        self.assertEqual([], fields["blocked-by"])

    def test_the_title_is_split_on_the_first_colon_space_only(self):
        fields, _ = self.parse(render(1, title="Fix: the scan: again"))
        self.assertEqual("Fix: the scan: again", fields["title"])


class Grammar(TrackerCase):
    BASE = render(1, title="A title", priority="P1", labels=["type:fix", "area:x"])

    def cases(self):
        base = self.BASE
        head = base.partition("blocked-by: []\n---\n")[0]
        return [
            ("missing key", base.replace("priority: P1\n", ""), "missing key(s): priority"),
            ("unknown key", base.replace("blocked-by: []\n", "blocked-by: []\nassignee: bob\n"),
             "unknown key 'assignee'"),
            ("duplicate key", base.replace("status: open\n", "status: open\nstatus: done\n"),
             "duplicate key 'status'"),
            ("out of order", base.replace("title: A title\nstatus: open\n",
                                          "status: open\ntitle: A title\n"),
             "keys out of order"),
            ("block list", base.replace("labels: [type:fix, area:x]\n", "labels:\n  - type:fix\n"),
             "labels must be a one-line"),
            ("empty title", base.replace("title: A title", "title:"), "title is empty"),
            ("id differs from the filename", base.replace("id: t1\n", "id: t2\n"),
             "does not match the filename"),
            ("unknown status", base.replace("status: open", "status: wip"), "status 'wip'"),
            ("band out of range", base.replace("priority: P1", "priority: P4"), "priority 'P4'"),
            ("band that is not a band", base.replace("priority: P1", "priority: high"),
             "priority 'high'"),
            ("unclosed frontmatter", head + "blocked-by: []\nbody only\n", "never closed"),
            ("no opening fence", base[len("---\n"):], "first line must be ---"),
            ("a line that is not key: value", base.replace("status: open\n", "status open\n"),
             "not 'key: value'"),
        ]

    def test_each_grammar_error_is_reported_by_path_and_not_skipped(self):
        for label, text, expected in self.cases():
            with self.subTest(label):
                self.put("t1.md", text)
                items, problems = ft.load(self.root)
                self.assertEqual([], items, "a broken item must not load as if it were fine")
                self.assertTrue(problems, "silently skipped")
                for problem in problems:
                    self.assertTrue(problem.startswith(".tasks/t1.md: "), problem)
                self.assertTrue(any(expected in p for p in problems), (expected, problems))

    def test_a_broken_file_does_not_hide_its_siblings(self):
        self.item(1)
        self.item(2, status="wip")
        items, problems = ft.load(self.root)
        self.assertEqual(["t1"], [i["id"] for i in items])
        self.assertEqual(1, len(problems))
        self.assertTrue(problems[0].startswith(".tasks/t2.md: "), problems)

    def test_blocked_by_naming_no_item_is_an_error(self):
        self.item(1, blocked=["t9"])
        _, problems = ft.load(self.root)
        self.assertIn(".tasks/t1.md: blocked-by 't9' names no item", problems)

    def test_a_blocker_that_is_itself_broken_is_not_reported_missing_and_still_gates(self):
        self.item(1, blocked=["t2"])
        self.item(2, status="wip")
        items, problems = ft.load(self.root)
        self.assertFalse([p for p in problems if "names no item" in p], problems)
        by_id = {i["id"]: i for i in items}
        self.assertEqual(["t2"], ft.open_blockers(by_id["t1"], by_id))

    def test_blocked_by_resolves_across_files(self):
        self.item(1, blocked=["t2"])
        self.item(2)
        self.assertEqual([], ft.load(self.root)[1])

    def test_a_stray_markdown_file_is_an_error(self):
        self.item(1)
        self.put("notes.md", "# scratch\n")
        items, problems = ft.load(self.root)
        self.assertEqual(["t1"], [i["id"] for i in items])
        self.assertEqual([".tasks/notes.md: not an item filename (t<n>.md)"], problems)

    def test_the_triage_view_and_non_markdown_files_are_ignored(self):
        self.put("triage.md", "not an item, not even frontmatter\n")
        self.put(".gitignore", "triage.md\n")
        self.assertEqual(([], []), ft.load(self.root))

    def test_a_missing_tasks_dir_is_an_empty_tracker(self):
        self.assertEqual(([], []), ft.load(self.root))

    def test_items_sort_by_number_not_by_name(self):
        for n in (10, 2, 1):
            self.item(n)
        items, _ = ft.load(self.root)
        self.assertEqual(["t1", "t2", "t10"], [i["id"] for i in items])


class Readiness(TrackerCase):
    def by_id(self):
        items, problems = ft.load(self.root)
        self.assertEqual([], problems)
        return {i["id"]: i for i in items}

    def test_an_open_blocker_gates_and_a_closed_one_does_not(self):
        self.item(1)
        self.item(2, status="done")
        self.item(3, status="dropped")
        self.item(4, blocked=["t1", "t2", "t3"])
        self.item(5, blocked=["t2", "t3"])
        by_id = self.by_id()
        self.assertEqual(["t1"], ft.open_blockers(by_id["t4"], by_id))
        self.assertEqual([], ft.open_blockers(by_id["t5"], by_id))
        self.assertEqual([], ft.open_blockers(by_id["t1"], by_id), "no blockers is ready")

    def test_list_prints_one_line_per_open_item_and_a_footer(self):
        self.item(1, title="First", priority="P1", labels=["type:fix", "area:x"])
        self.item(2, title="Second", blocked=["t1"])
        self.item(3, title="Third", status="done")
        self.item(4, title="Fourth", status="dropped")
        self.item(5, title="Fifth", blocked=["t3", "t4"])
        self.item(6, title="Sixth", blocked=["t1", "t3", "t2"])
        code, out, err = run_main(["--root", self.root, "list"])
        self.assertEqual((0, ""), (code, err))
        self.assertEqual([
            "t1\tP1\tready\ttype:fix,area:x\tFirst",
            "t2\t-\tblocked by t1\t-\tSecond",
            "t5\t-\tready\t-\tFifth",
            "t6\t-\tblocked by t1, t2\t-\tSixth",
            "# 4 open (2 ready), 2 closed; next id t7",
        ], out.splitlines())

    def test_list_all_includes_closed_items(self):
        self.item(1, title="First")
        self.item(2, title="Second", status="done")
        self.item(3, title="Third", status="dropped")
        code, out, _ = run_main(["--root", self.root, "list", "--all"])
        self.assertEqual(0, code)
        self.assertEqual([
            "t1\t-\tready\t-\tFirst",
            "t2\t-\tdone\t-\tSecond",
            "t3\t-\tdropped\t-\tThird",
            "# 1 open (1 ready), 2 closed; next id t4",
        ], out.splitlines())

    def test_list_on_an_absent_tracker_is_empty_and_clean(self):
        code, out, err = run_main(["--root", self.root, "list"])
        self.assertEqual((0, "# 0 open (0 ready), 0 closed; next id t1\n", ""), (code, out, err))

    def test_list_prints_what_parsed_and_exits_1_for_a_broken_file(self):
        self.item(1, title="Fine")
        self.item(2, status="wip")
        code, out, err = run_main(["--root", self.root, "list"])
        self.assertEqual(1, code)
        self.assertEqual(["t1\t-\tready\t-\tFine", "# 1 open (1 ready), 0 closed; next id t3"],
                         out.splitlines())
        self.assertTrue(err.startswith("BROKEN .tasks/t2.md: "), err)


class NextId(TrackerCase):
    def test_t1_when_there_is_nothing(self):
        self.assertEqual("t1", ft.next_id(self.root), "absent .tasks/")
        os.makedirs(self.tasks)
        self.assertEqual("t1", ft.next_id(self.root), "empty .tasks/")

    def test_it_is_the_highest_number_ever_used_plus_one(self):
        self.item(1)
        self.item(5)
        self.assertEqual("t6", ft.next_id(self.root), "a gap is not refilled")

    def test_closed_items_still_count(self):
        self.item(1, status="done")
        self.item(2, status="dropped")
        self.assertEqual("t3", ft.next_id(self.root))

    def test_a_broken_file_still_counts(self):
        self.item(1)
        self.put("t9.md", "not frontmatter at all\n")
        self.assertEqual("t10", ft.next_id(self.root))

    def test_numbers_compare_as_numbers(self):
        self.item(2)
        self.item(10)
        self.assertEqual("t11", ft.next_id(self.root))

    def test_notes_and_the_triage_view_are_not_ids(self):
        self.put("notes.md", "x\n")
        self.put("triage.md", "x\n")
        self.assertEqual("t1", ft.next_id(self.root))


class Detect(TrackerCase):
    def mkdir(self, name):
        os.makedirs(os.path.join(self.root, name))

    def board(self, name=".backlog"):
        """A Backlog.md board is a directory holding its config.yml."""
        self.mkdir(name)
        with open(os.path.join(self.root, name, "config.yml"), "w", encoding="utf-8") as handle:
            handle.write('project_name: "x"\n')

    def test_a_kata_binding_wins_over_everything_without_shelling_out(self):
        with open(os.path.join(self.root, ".kata.toml"), "w", encoding="utf-8") as handle:
            handle.write('project = "x"\n')
        self.mkdir(".backlog")
        self.mkdir(".tasks")

        def boom(*_, **__):
            raise AssertionError("detect must not shell out when .kata.toml binds the project")

        self.assertEqual("kata", ft.detect(self.root, run=boom)[0])

    def test_a_github_remote_with_issues_means_github(self):
        self.mkdir(".backlog")
        self.mkdir(".tasks")
        run = fake_run(remotes=GITHUB, issues='[{"number": 7}]')
        self.assertEqual("github", ft.detect(self.root, run=run)[0])
        gh = next(call for call in run.calls if call[0] == "gh")
        self.assertEqual("all", gh[gh.index("--state") + 1], "closed-only issues are still in use")

    def test_a_github_remote_with_zero_issues_falls_through(self):
        run = fake_run(remotes=GITHUB, issues="[]")
        tracker, reason = ft.detect(self.root, run=run)
        self.assertEqual("file", tracker)
        self.assertIn("falling back", reason)
        self.board()
        self.assertEqual("backlog", ft.detect(self.root, run=run)[0])

    def test_a_failing_gh_with_a_github_remote_is_loud(self):
        self.mkdir(".tasks")
        run = fake_run(remotes=GITHUB, issues_rc=1, issues_err="not logged in")
        with self.assertRaises(SystemExit) as raised:
            ft.detect(self.root, run=run)
        self.assertIn("not logged in", str(raised.exception.code))

    def test_a_missing_gh_with_a_github_remote_is_loud(self):
        self.mkdir(".tasks")
        with self.assertRaises(SystemExit) as raised:
            ft.detect(self.root, run=fake_run(remotes=GITHUB, gh_missing=True))
        self.assertIn("gh is not installed", str(raised.exception.code))

    def test_without_a_github_remote_gh_is_never_called(self):
        for label, run in [
            ("other host", fake_run(remotes=GITLAB)),
            ("no remote", fake_run(remotes="")),
            ("not a repo", fake_run(remotes=GITHUB, remotes_rc=128)),
        ]:
            with self.subTest(label):
                ft.detect(self.root, run=run)
                self.assertEqual({"git"}, {call[0] for call in run.calls})

    def test_backlog_beats_tasks_and_tasks_means_the_file_tracker(self):
        run = fake_run()
        self.mkdir(".tasks")
        tracker, reason = ft.detect(self.root, run=run)
        self.assertEqual("file", tracker)
        self.assertNotIn("falling back", reason)
        self.board()
        self.assertEqual("backlog", ft.detect(self.root, run=run)[0])

    def test_backlog_default_dir_counts_and_a_bare_dir_does_not(self):
        self.mkdir(".backlog")
        self.assertEqual("file", ft.detect(self.root, run=fake_run())[0])
        self.board("backlog")
        tracker, reason = ft.detect(self.root, run=fake_run())
        self.assertEqual(("backlog", True), (tracker, reason.startswith("backlog/")))

    def test_a_missing_git_skips_the_github_rung(self):
        def no_git(*_, **__):
            raise FileNotFoundError("git")

        self.assertEqual("file", ft.detect(self.root, run=no_git)[0])

    def test_nothing_found_falls_back_to_the_file_tracker_and_says_so(self):
        tracker, reason = ft.detect(self.root, run=fake_run())
        self.assertEqual("file", tracker)
        self.assertIn("falling back", reason)


class Snapshot(TrackerCase):
    def test_only_open_items_with_null_for_an_unset_priority(self):
        self.item(1, title="Triaged", priority="P1", labels=["type:fix", "area:x"])
        self.item(2, title="Untriaged")
        self.item(3, title="Shipped", status="done", priority="P0")
        items, problems = ft.load(self.root)
        self.assertEqual([], problems)
        snapshot = ft.build_snapshot(self.root, items)
        self.assertEqual({
            "board": {"name": os.path.basename(self.root), "backend": "file"},
            "fields": {
                "priority": {"options": ["P0", "P1", "P2", "P3"]},
                "labels": {"options": ["area:x", "type:fix"]},
            },
            "items": [
                {"key": "t1", "id": ".tasks/t1.md", "title": "Triaged", "state": "open",
                 "labels": ["area:x", "type:fix"], "fields": {"priority": "P1"}},
                {"key": "t2", "id": ".tasks/t2.md", "title": "Untriaged", "state": "open",
                 "labels": [], "fields": {"priority": None}},
            ],
        }, snapshot)
        json.dumps(snapshot)  # it has to survive the trip to the analyst

    def test_export_prints_json_of_the_open_items(self):
        self.item(1, priority="P2")
        self.item(2, status="dropped")
        code, out, _ = run_main(["--root", self.root, "export"])
        self.assertEqual(0, code)
        self.assertEqual(["t1"], [i["key"] for i in json.loads(out)["items"]])

    def test_export_out_writes_the_file_and_counts_untriaged(self):
        self.item(1, priority="P2")
        self.item(2)
        target = os.path.join(self.root, "snapshot.json")
        code, out, _ = run_main(["--root", self.root, "export", "--out", target])
        self.assertEqual(0, code)
        self.assertEqual(f"2 items (1 untriaged) -> {target}\n", out)
        with open(target, encoding="utf-8") as handle:
            self.assertEqual(["t1", "t2"], [i["key"] for i in json.load(handle)["items"]])

    def test_export_refuses_and_writes_nothing_when_any_file_is_broken(self):
        self.item(1)
        self.item(2, status="wip")
        target = os.path.join(self.root, "snapshot.json")
        before = self.tree()
        code, out, err = run_main(["--root", self.root, "export", "--out", target])
        self.assertNotIn(code, (0, None))
        self.assertEqual("", out)
        self.assertIn("BROKEN .tasks/t2.md: ", err)
        self.assertEqual(before, self.tree())

    def test_a_refusal_is_a_real_nonzero_exit_status(self):
        """SystemExit(str) is the contract's mechanism; only the interpreter makes it 1."""
        self.item(1, status="wip")
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "file_tracker.py"),
             "--root", self.root, "export"],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(1, proc.returncode)
        self.assertEqual("", proc.stdout)
        self.assertIn("BROKEN .tasks/t1.md: ", proc.stderr)


class Changeset(TrackerCase):
    def snapshot(self):
        self.item(1, priority="P1", labels=["area:x"])
        self.item(2)
        self.item(3, status="done", priority="P3")
        items, problems = ft.load(self.root)
        self.assertEqual([], problems)
        return ft.build_snapshot(self.root, items)

    def test_parse_skips_blanks_comments_and_a_header(self):
        text = "Key\tField\tValue\n\n# a comment\n  # indented comment\nt1\tpriority\tP2\n"
        self.assertEqual([("t1", "priority", "P2")], ft.parse_changeset(text))

    def test_parse_keeps_tabs_in_the_value_and_reads_a_missing_value_as_empty(self):
        rows = ft.parse_changeset("t1\tLabels\ta\tb\nt2\tpriority\n")
        self.assertEqual([("t1", "labels", "a\tb"), ("t2", "priority", "")], rows)

    def test_parse_rejects_a_row_without_a_field(self):
        with self.assertRaises(SystemExit) as raised:
            ft.parse_changeset("t1\n")
        self.assertIn("line 1", str(raised.exception.code))

    def test_plan_writes_only_cells_that_differ(self):
        writes, problems = ft.plan(self.snapshot(), [
            ("t1", "priority", "P1"),
            ("t1", "labels", "area:x"),
            ("t2", "priority", ""),
            ("t2", "labels", "b, a, b"),
            ("t1", "priority", "p2"),
        ])
        self.assertEqual([], problems)
        self.assertEqual([("t2", "labels", ["a", "b"]), ("t1", "priority", "P2")],
                         [w[:3] for w in writes])

    def test_plan_clears_a_priority_with_an_empty_value(self):
        writes, _ = ft.plan(self.snapshot(), [("t1", "priority", "")])
        self.assertEqual([("t1", "priority", "")], [w[:3] for w in writes])

    def test_plan_refuses_what_is_not_a_triage_cell(self):
        writes, problems = ft.plan(self.snapshot(), [
            ("t1", "status", "done"),
            ("t1", "assignee", "bob"),
            ("t1", "priority", "P9"),
            ("t9", "priority", "P1"),
            ("t3", "priority", "P0"),
        ])
        self.assertEqual([], writes)
        self.assertEqual([
            "t1: status is not a triage cell — readiness comes from blocked-by, "
            "and closing is the landing step",
            "t1: no file-tracker cell for field 'assignee'",
            "t1: priority 'P9' is not a band (P0-P3)",
            "t9: no open item with this id",
            "t3: no open item with this id",
        ], problems)


class WriteField(TrackerCase):
    def test_only_the_targeted_frontmatter_line_changes(self):
        body = "priority: P9\nlabels: [zzz]\n---\n\n## Log\n- 2026-10-11 triage: kept\n"
        self.item(1, priority="P1", labels=["a"], body=body)
        old = self.read("t1.md")
        ft.write_field(self.root, "t1", "priority", "P2")
        self.assertEqual(old.replace("priority: P1\n", "priority: P2\n", 1), self.read("t1.md"))

    def test_a_file_without_a_trailing_newline_stays_that_way(self):
        self.item(1, body="no newline at the end")
        ft.write_field(self.root, "t1", "priority", "P0")
        self.assertTrue(self.read("t1.md").endswith("---\nno newline at the end"))

    def test_crlf_line_endings_survive_a_rewrite(self):
        crlf = render(1, priority="P1").replace("\n", "\r\n").encode()
        os.makedirs(self.tasks, exist_ok=True)
        with open(os.path.join(self.tasks, "t1.md"), "wb") as handle:
            handle.write(crlf)
        ft.write_field(self.root, "t1", "priority", "P2")
        with open(os.path.join(self.tasks, "t1.md"), "rb") as handle:
            self.assertEqual(crlf.replace(b"priority: P1\r\n", b"priority: P2\r\n"), handle.read())

    def test_lists_render_on_one_line(self):
        self.item(1, labels=["old"])
        ft.write_field(self.root, "t1", "labels", ["a", "b"])
        self.assertIn("\nlabels: [a, b]\n", self.read("t1.md"))
        ft.write_field(self.root, "t1", "labels", [])
        self.assertIn("\nlabels: []\n", self.read("t1.md"))

    def test_an_empty_scalar_is_the_unset_form_with_no_trailing_space(self):
        self.item(1, priority="P1")
        ft.write_field(self.root, "t1", "priority", "")
        self.assertIn("\npriority:\n", self.read("t1.md"))
        self.assertEqual([], ft.load(self.root)[1])

    def test_the_result_still_parses_clean(self):
        self.item(1, priority="P1", labels=["a"])
        ft.write_field(self.root, "t1", "labels", ["b", "c"])
        ft.write_field(self.root, "t1", "priority", "P3")
        items, problems = ft.load(self.root)
        self.assertEqual([], problems)
        self.assertEqual((["b", "c"], "P3"), (items[0]["labels"], items[0]["priority"]))


class Apply(TrackerCase):
    def setUp(self):
        super().setUp()
        aux = tempfile.TemporaryDirectory()
        self.addCleanup(aux.cleanup)
        self.changeset_path = os.path.join(aux.name, "changeset.tsv")
        self.item(1, title="Untriaged")
        self.item(2, title="Triaged", priority="P1", labels=["area:x"])
        self.item(3, title="Shipped", status="done", priority="P3")

    def apply(self, *rows, write=True):
        with open(self.changeset_path, "w", encoding="utf-8") as handle:
            handle.write("key\tfield\tvalue\n" + "".join("\t".join(r) + "\n" for r in rows))
        argv = ["--root", self.root, "apply", "--changeset", self.changeset_path]
        return run_main(argv + ["--apply"] if write else argv)

    def test_a_dry_run_describes_the_writes_and_writes_nothing(self):
        before = self.tree()
        code, out, err = self.apply(("t1", "priority", "P2"), ("t2", "labels", "b, a"), write=False)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("DRY   t1 priority: None -> 'P2'\n", out)
        self.assertIn("DRY   t2 labels: ['area:x'] -> ['a', 'b']\n", out)
        self.assertIn("re-run with --apply", out)
        self.assertEqual(before, self.tree())

    def test_apply_rewrites_only_the_targeted_frontmatter_line(self):
        old = {name: self.read(name) for name in ("t1.md", "t2.md", "t3.md")}
        code, out, err = self.apply(("t1", "priority", "P2"), ("t2", "labels", "b, a"))
        self.assertEqual((0, ""), (code, err))
        self.assertIn("applied 2 cell change(s)", out)
        self.assertEqual(old["t1.md"].replace("priority:\n", "priority: P2\n", 1), self.read("t1.md"))
        self.assertEqual(old["t2.md"].replace("[area:x]", "[a, b]", 1), self.read("t2.md"))
        self.assertEqual(old["t3.md"], self.read("t3.md"))
        self.assertIn("## Log\n- 2026-10-11 triage: P1, on the demo path\n", self.read("t1.md"))

    def test_a_rerun_has_nothing_to_change(self):
        rows = (("t1", "priority", "P2"), ("t2", "labels", "b, a"))
        self.apply(*rows)
        after = self.tree()
        for write in (True, False):
            code, out, err = self.apply(*rows, write=write)
            self.assertEqual((0, ""), (code, err))
            self.assertIn("nothing to change", out)
            self.assertNotIn("DRY", out)
            self.assertNotIn("APPLY", out)
        self.assertEqual(after, self.tree())

    def test_unsupported_rows_are_skipped_loudly_and_valid_rows_still_apply(self):
        old = {name: self.read(name) for name in ("t2.md", "t3.md")}
        code, out, err = self.apply(
            ("t1", "priority", "P2"),
            ("t2", "status", "done"),
            ("t2", "assignee", "bob"),
            ("t9", "priority", "P1"),
            ("t3", "priority", "P0"),
        )
        self.assertEqual(1, code)
        self.assertEqual(4, err.count("SKIP "), err)
        self.assertIn("SKIP t2: status is not a triage cell", err)
        self.assertIn("SKIP t2: no file-tracker cell for field 'assignee'", err)
        self.assertIn("SKIP t9: no open item with this id", err)
        self.assertIn("SKIP t3: no open item with this id", err)
        self.assertIn("priority: P2\n", self.read("t1.md"))
        self.assertIn("applied 1 cell change(s)", out)
        self.assertEqual(old, {name: self.read(name) for name in old})

    def test_a_dry_run_also_exits_1_for_skipped_rows(self):
        before = self.tree()
        code, _, err = self.apply(("t2", "status", "done"), write=False)
        self.assertEqual(1, code)
        self.assertIn("SKIP t2: status", err)
        self.assertEqual(before, self.tree())

    def test_an_empty_priority_clears_to_the_unset_form(self):
        old = self.read("t2.md")
        code, _, _ = self.apply(("t2", "priority", ""))
        self.assertEqual(0, code)
        self.assertEqual(old.replace("priority: P1\n", "priority:\n", 1), self.read("t2.md"))
        self.assertEqual([], ft.load(self.root)[1])

    def test_apply_refuses_and_writes_nothing_when_any_file_is_broken(self):
        self.item(4, status="wip")
        before = self.tree()
        for write in (True, False):
            code, out, err = self.apply(("t1", "priority", "P2"), write=write)
            self.assertNotIn(code, (0, None))
            self.assertEqual("", out)
            self.assertIn("BROKEN .tasks/t4.md: ", err)
            self.assertEqual(before, self.tree())


if __name__ == "__main__":
    unittest.main()
