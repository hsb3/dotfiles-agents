"""project-memory's two scripts: in-repo memory wiring and cross-machine migration.

Both are safe-by-default tools whose entire value is the safety guarantee, not the
happy path: init must never clobber a file a user has already edited, and migrate must
print its plan without touching the filesystem until --apply is passed. Those two
guarantees are what this file proves; everything else here is supporting plumbing
(status/path/list reporting, plan/execute mechanics) needed to reach them.

subprocess.run (project_memory's `git rev-parse`) and the PROJECTS root (migrate's
~/.claude/projects lookup) are both patched so nothing touches the real git repo or the
real home directory.
"""

import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "primitives-core", "skills", "project-memory", "scripts")
sys.path.insert(0, SCRIPTS)

import project_memory as pm  # noqa: E402
import migrate_memory as mm  # noqa: E402


def run_captured(func, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = func(*args, **kwargs)
    return result, buf.getvalue()


def patched_repo_root(path: Path):
    """project_memory.repo_root() shells to `git rev-parse`, and cmd_init/cmd_status read
    Path.home() unconditionally; stub both so no test reaches the real home directory."""
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=f"{path}\n")
    home = path.parent / "home"
    home.mkdir(exist_ok=True)
    stack = contextlib.ExitStack()
    stack.enter_context(mock.patch("project_memory.subprocess.run", return_value=completed))
    stack.enter_context(mock.patch.object(pm.Path, "home", return_value=home))
    return stack


class ProjectMemoryInit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        # repo_root() resolves symlinks (e.g. macOS /tmp -> /private/var); match it up
        # front so every path built from self.repo compares equal to what the script sees.
        self.repo = self.repo.resolve()

    def _init(self, **overrides):
        args = argparse.Namespace(portable=False, migrate=False)
        for k, v in overrides.items():
            setattr(args, k, v)
        with patched_repo_root(self.repo):
            return run_captured(pm.cmd_init, args)

    def test_creates_memory_stub_and_wires_local_settings(self):
        rc, out = self._init()
        self.assertEqual(0, rc)
        memory_md = self.repo / ".claude" / "memory" / "MEMORY.md"
        settings = self.repo / ".claude" / "settings.local.json"
        self.assertTrue(memory_md.exists())
        self.assertIn(self.repo.name, memory_md.read_text())
        data = json.loads(settings.read_text())
        self.assertEqual(str(self.repo / ".claude" / "memory"), data["autoMemoryDirectory"])
        self.assertIn("project-memory (managed)", (self.repo / ".gitignore").read_text())
        self.assertIn("[ok] project memory wired", out)

    def test_never_overwrites_a_preexisting_memory_md_or_settings(self):
        self._init()
        mem_dir = self.repo / ".claude" / "memory"
        settings = self.repo / ".claude" / "settings.local.json"
        gitignore = self.repo / ".gitignore"

        # Simulate a user editing the stub and adding an unrelated settings key.
        (mem_dir / "MEMORY.md").write_text("# hand-edited notes\n- keep this\n")
        settings_data = json.loads(settings.read_text())
        settings_data["someOtherKey"] = "untouched"
        settings.write_text(json.dumps(settings_data, indent=2) + "\n")

        before = {
            p: p.read_bytes()
            for p in (self.repo / ".claude").rglob("*")
            if p.is_file()
        }
        before[gitignore] = gitignore.read_bytes()

        self._init()  # re-init on an already-configured repo

        after = {
            p: p.read_bytes()
            for p in (self.repo / ".claude").rglob("*")
            if p.is_file()
        }
        after[gitignore] = gitignore.read_bytes()

        self.assertEqual(before, after, "re-init must leave every pre-existing file byte-identical")

    def test_portable_writes_tilde_relative_path_to_tracked_settings(self):
        home = Path(self.tmp.name)
        repo = home / "proj"
        repo.mkdir()
        args = argparse.Namespace(portable=True, migrate=False)
        with patched_repo_root(repo), mock.patch.object(pm.Path, "home", return_value=home):
            rc, out = run_captured(pm.cmd_init, args)
        self.assertEqual(0, rc)
        tracked = json.loads((repo / ".claude" / "settings.json").read_text())
        self.assertEqual("~/proj/.claude/memory", tracked["autoMemoryDirectory"])
        self.assertFalse((repo / ".claude" / "settings.local.json").exists())

    def test_migrate_copies_native_md_files_and_skips_existing_dest(self):
        home = Path(self.tmp.name) / "home"
        home.mkdir()
        with patched_repo_root(self.repo), mock.patch.object(pm.Path, "home", return_value=home):
            native = pm.native_memory_dir(self.repo)
            native.mkdir(parents=True)
            (native / "learned.md").write_text("native content\n")
            (native / "MEMORY.md").write_text("native index\n")

            # Pre-seed the destination MEMORY.md so it must be skipped, not overwritten.
            dest_mem = self.repo / ".claude" / "memory"
            dest_mem.mkdir(parents=True)
            (dest_mem / "MEMORY.md").write_text("already here\n")

            args = argparse.Namespace(portable=False, migrate=True)
            rc, out = run_captured(pm.cmd_init, args)

        self.assertEqual(0, rc)
        self.assertEqual("native content\n", (dest_mem / "learned.md").read_text())
        self.assertEqual("already here\n", (dest_mem / "MEMORY.md").read_text())
        self.assertIn("migrated   : 1 file(s)", out)


class ProjectMemoryStatusPathList(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.repo = self.repo.resolve()  # match repo_root()'s symlink resolution

    def test_status_reports_in_repo_when_configured(self):
        with patched_repo_root(self.repo):
            run_captured(pm.cmd_init, argparse.Namespace(portable=False, migrate=False))
            _, out = run_captured(pm.cmd_status, argparse.Namespace())
        self.assertIn("-> in-repo", out)

    def test_status_reports_native_default_when_unconfigured(self):
        with patched_repo_root(self.repo):
            _, out = run_captured(pm.cmd_status, argparse.Namespace())
        self.assertIn("not set — using hidden native default", out)

    def test_path_prints_configured_dir_when_set(self):
        with patched_repo_root(self.repo):
            run_captured(pm.cmd_init, argparse.Namespace(portable=False, migrate=False))
            _, out = run_captured(pm.cmd_path, argparse.Namespace())
        self.assertEqual(str(self.repo / ".claude" / "memory"), out.strip())

    def test_path_prints_native_dir_when_unconfigured(self):
        home = Path(self.tmp.name) / "home"
        home.mkdir()
        with patched_repo_root(self.repo), mock.patch.object(pm.Path, "home", return_value=home):
            _, out = run_captured(pm.cmd_path, argparse.Namespace())
            expected = str(pm.native_memory_dir(self.repo))
        self.assertEqual(expected, out.strip())

    def test_list_reports_no_projects_dir(self):
        home = Path(self.tmp.name) / "no-claude-here"
        home.mkdir()
        with mock.patch.object(pm.Path, "home", return_value=home):
            rc, out = run_captured(pm.cmd_list, argparse.Namespace())
        self.assertEqual(0, rc)
        self.assertIn("no ~/.claude/projects directory", out)


class MigratePlanAndExecute(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = Path(self.tmp.name) / "src"
        self.dst = Path(self.tmp.name) / "dst"
        self.src.mkdir()
        (self.src / "a.md").write_text("a\n")
        (self.src / "b.md").write_text("b\n")

    def test_plan_marks_copy_for_new_and_skip_or_overwrite_for_existing(self):
        self.dst.mkdir()
        (self.dst / "b.md").write_text("stale b\n")
        files = sorted(self.src.glob("*.md"))

        plan_no_force = mm.plan_copies(files, self.src, self.dst, force=False)
        self.assertEqual(
            [("copy", "a.md"), ("skip", "b.md")],
            [(action, s.name) for action, s, _ in plan_no_force],
        )

        plan_force = mm.plan_copies(files, self.src, self.dst, force=True)
        self.assertEqual(
            [("copy", "a.md"), ("overwrite", "b.md")],
            [(action, s.name) for action, s, _ in plan_force],
        )

    def test_execute_copies_and_leaves_skips_untouched(self):
        self.dst.mkdir()
        (self.dst / "b.md").write_text("stale b\n")
        files = sorted(self.src.glob("*.md"))
        plan = mm.plan_copies(files, self.src, self.dst, force=False)

        copied, skipped = mm.execute(plan)

        self.assertEqual((1, 1), (copied, skipped))
        self.assertEqual("a\n", (self.dst / "a.md").read_text())
        self.assertEqual("stale b\n", (self.dst / "b.md").read_text(), "skip must not touch existing file")


class MigrateMainCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.projects = Path(self.tmp.name) / "projects"
        old_mem = self.projects / "old-slug" / "memory"
        old_mem.mkdir(parents=True)
        (old_mem / "MEMORY.md").write_text("index\n")
        (old_mem / "topic.md").write_text("topic\n")
        self.patch_projects = mock.patch.object(mm, "PROJECTS", self.projects)
        self.patch_projects.start()
        self.addCleanup(self.patch_projects.stop)

    def _run(self, argv):
        with mock.patch.object(sys, "argv", ["migrate_memory.py", *argv]):
            _, out = run_captured(mm.main)
        return out

    def test_dry_run_writes_nothing(self):
        dst = self.projects / "new-slug"
        before = list(self.projects.rglob("*"))

        out = self._run(["--from-slug", "old-slug", "--to-slug", "new-slug"])

        after = list(self.projects.rglob("*"))
        self.assertEqual(before, after, "dry run must not touch the filesystem")
        self.assertFalse(dst.exists())
        self.assertIn("copy", out)
        self.assertIn("Dry run. Add --apply to copy.", out)

    def test_apply_copies_files_into_destination(self):
        dst_mem = self.projects / "new-slug" / "memory"

        self._run(["--from-slug", "old-slug", "--to-slug", "new-slug", "--apply"])

        self.assertEqual("index\n", (dst_mem / "MEMORY.md").read_text())
        self.assertEqual("topic\n", (dst_mem / "topic.md").read_text())

    def test_force_controls_overwrite_of_existing_destination_file(self):
        dst_mem = self.projects / "new-slug" / "memory"
        dst_mem.mkdir(parents=True)
        (dst_mem / "topic.md").write_text("stale destination copy\n")

        self._run(["--from-slug", "old-slug", "--to-slug", "new-slug", "--apply"])
        self.assertEqual(
            "stale destination copy\n",
            (dst_mem / "topic.md").read_text(),
            "without --force, an existing destination file must survive",
        )

        self._run(["--from-slug", "old-slug", "--to-slug", "new-slug", "--apply", "--force"])
        self.assertEqual("topic\n", (dst_mem / "topic.md").read_text())


if __name__ == "__main__":
    unittest.main()
