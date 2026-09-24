"""Tests for primitives-core/hooks/worktree-root/hook.py.

Runs the hook as a subprocess (JSON on stdin) against real git repos in a tempdir,
with HOME pointed into the tempdir so no user-level settings are read. Skips
without a git binary.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worktree_fixture import _GIT_IDENTITY, _git, _write, make_worktree, require_git  # noqa: E402

HOOK_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "primitives-core", "hooks",
    "worktree-root", "hook.py",
)


class WorktreeRootTests(unittest.TestCase):
    def setUp(self):
        require_git()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.home = os.path.join(self.base, "home")
        os.makedirs(self.home)
        self.main, self.linked = make_worktree(
            self.base, tracked={"README": "r\n", ".gitignore": ".claude/\n.worktrees/\n"})

    # -- helpers -------------------------------------------------------

    def run_hook(self, payload, **extra_env):
        env = {"PATH": os.environ.get("PATH", ""), "HOME": self.home, **extra_env}
        return subprocess.run([sys.executable, HOOK_PATH], input=json.dumps(payload),
                              capture_output=True, text=True, env=env, timeout=60)

    def create(self, name, cwd=None, **extra_env):
        return self.run_hook({"hook_event_name": "WorktreeCreate",
                              "cwd": cwd or self.main, "name": name}, **extra_env)

    def commit(self, cwd, msg):
        _git(cwd, *(_GIT_IDENTITY + ("commit", "-q", "--allow-empty", "-m", msg)))
        return _git(cwd, "rev-parse", "HEAD")

    def set_key(self, value):
        _write(self.main, ".claude/atelier.local.md",
               "---\ncheckout-root: {0}\n---\n".format(value))

    def created_path(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip().splitlines()[-1]

    def branches(self):
        return _git(self.main, "branch", "--format=%(refname:short)").split()

    # -- WorktreeCreate: placement and base --------------------------------

    def test_key_absent_native_path_branch_and_head_base_without_origin(self):
        head = self.commit(self.main, "ahead")
        path = self.created_path(self.create("feat/x"))
        self.assertEqual(path, os.path.join(self.main, ".claude", "worktrees", "feat+x"))
        self.assertIn("worktree-feat+x", self.branches())
        self.assertEqual(_git(path, "rev-parse", "HEAD"), head)

    def test_base_is_origin_head_when_a_local_origin_exists(self):
        origin = os.path.join(self.base, "origin.git")
        _git(self.base, "clone", "-q", "--bare", self.main, origin)
        _git(self.main, "remote", "add", "origin", origin)
        _git(self.main, "fetch", "-q", "origin")
        _git(self.main, "remote", "set-head", "origin", "-a")
        origin_head = _git(self.main, "rev-parse", "refs/remotes/origin/HEAD")
        self.commit(self.main, "local only")
        path = self.created_path(self.create("o"))
        self.assertEqual(_git(path, "rev-parse", "HEAD"), origin_head)

    def add_origin(self, url=None):
        origin = url or os.path.join(self.base, "origin.git")
        if url is None:
            _git(self.base, "clone", "-q", "--bare", self.main, origin)
        _git(self.main, "remote", "add", "origin", origin)
        return origin

    def test_base_falls_back_to_origin_main_without_origin_head(self):
        self.add_origin()
        _git(self.main, "fetch", "-q", "origin", "HEAD:refs/remotes/origin/main")
        _git(self.main, "remote", "set-head", "origin", "-d")
        base = _git(self.main, "rev-parse", "refs/remotes/origin/main")
        self.commit(self.main, "local only")
        path = self.created_path(self.create("om"))
        self.assertEqual(_git(path, "rev-parse", "HEAD"), base)

    def test_failed_fetch_is_non_fatal_and_uses_local_origin_main(self):
        self.add_origin(os.path.join(self.base, "missing.git"))
        base = _git(self.main, "rev-parse", "HEAD")
        _git(self.main, "update-ref", "refs/remotes/origin/main", base)
        self.commit(self.main, "local only")
        proc = self.create("ff")
        self.assertEqual(_git(self.created_path(proc), "rev-parse", "HEAD"), base)
        self.assertIn("fetch of origin/main failed", proc.stderr)

    def test_stale_fetch_head_refreshes_origin_before_branching(self):
        origin = self.add_origin()
        _git(self.main, "fetch", "-q", "origin")
        _git(self.main, "remote", "set-head", "origin", "-a")
        other = os.path.join(self.base, "other")
        _git(self.base, "clone", "-q", origin, other)
        fresh = self.commit(other, "upstream")
        _git(other, "push", "-q", "origin", "HEAD")
        os.utime(os.path.join(self.main, ".git", "FETCH_HEAD"), (0, 0))
        path = self.created_path(self.create("sf"))
        self.assertEqual(_git(path, "rev-parse", "HEAD"), fresh)

    def test_local_settings_override_project_settings(self):
        self.add_origin()
        _git(self.main, "fetch", "-q", "origin", "HEAD:refs/remotes/origin/main")
        base = _git(self.main, "rev-parse", "refs/remotes/origin/main")
        self.commit(self.main, "local only")
        _write(self.main, ".claude/settings.json", '{"worktree": {"baseRef": "head"}}')
        _write(self.main, ".claude/settings.local.json", '{"worktree": {"baseRef": "fresh"}}')
        path = self.created_path(self.create("lp"))
        self.assertEqual(_git(path, "rev-parse", "HEAD"), base)

    def test_user_settings_come_from_claude_config_dir_when_set(self):
        self.add_origin()
        _git(self.main, "fetch", "-q", "origin", "HEAD:refs/remotes/origin/main")
        base = _git(self.main, "rev-parse", "refs/remotes/origin/main")
        head = self.commit(self.main, "local only")
        _write(self.home, ".claude/settings.json", '{"worktree": {"baseRef": "head"}}')
        config = os.path.join(self.base, "config")
        os.makedirs(config)
        path = self.created_path(self.create("cd1", CLAUDE_CONFIG_DIR=config))
        self.assertEqual(_git(path, "rev-parse", "HEAD"), base)
        _write(config, "settings.json", '{"worktree": {"baseRef": "head"}}')
        path = self.created_path(self.create("cd2", CLAUDE_CONFIG_DIR=config))
        self.assertEqual(_git(path, "rev-parse", "HEAD"), head)

    def test_base_ref_head_setting_uses_head(self):
        origin = os.path.join(self.base, "origin.git")
        _git(self.base, "clone", "-q", "--bare", self.main, origin)
        _git(self.main, "remote", "add", "origin", origin)
        _git(self.main, "fetch", "-q", "origin")
        _git(self.main, "remote", "set-head", "origin", "-a")
        head = self.commit(self.main, "local only")
        _write(self.main, ".claude/settings.json", '{"worktree": {"baseRef": "head"}}')
        path = self.created_path(self.create("h"))
        self.assertEqual(_git(path, "rev-parse", "HEAD"), head)

    def test_key_set_places_under_checkout_root(self):
        self.set_key(".worktrees")
        path = self.created_path(self.create("k"))
        self.assertEqual(path, os.path.join(self.main, ".worktrees", "k"))
        self.assertTrue(os.path.isfile(os.path.join(path, "README")))

    def test_nested_call_lands_in_main_checkout_root(self):
        self.set_key(".worktrees")
        path = self.created_path(self.create("n", cwd=self.linked))
        self.assertEqual(path, os.path.join(self.main, ".worktrees", "n"))

    def test_nested_call_without_key_lands_in_main_native_root(self):
        path = self.created_path(self.create("n", cwd=self.linked))
        self.assertEqual(path, os.path.join(self.main, ".claude", "worktrees", "n"))

    def test_stdout_is_only_the_path(self):
        proc = self.create("only")
        self.assertEqual(proc.stdout.strip().splitlines(), [self.created_path(proc)])

    # -- WorktreeCreate: .worktreeinclude --------------------------------

    def test_worktreeinclude_copies_ignored_listed_files_only(self):
        _write(self.main, ".gitignore", ".claude/\n.env\nsecrets/\n*.log\nlink\n")
        _write(self.main, "tracked.txt", "committed\n")
        _git(self.main, "add", ".gitignore", "tracked.txt")
        self.commit(self.main, "ignore")
        _write(self.main, "tracked.txt", "modified\n")
        _write(self.main, ".worktreeinclude",
               "# comment\n.env\nsecrets/\ntracked.txt\nplain.txt\nlink\n")
        _write(self.main, ".env", "E\n")
        _write(self.main, "secrets/a.key", "a\n")
        _write(self.main, "secrets/sub/b.key", "b\n")
        _write(self.main, "other.log", "o\n")
        _write(self.main, "plain.txt", "p\n")
        os.symlink(os.path.join(self.main, ".env"), os.path.join(self.main, "link"))
        path = self.created_path(self.create("inc"))
        present = lambda rel: os.path.lexists(os.path.join(path, rel))  # noqa: E731
        for rel in (".env", "secrets/a.key", "secrets/sub/b.key"):
            self.assertTrue(present(rel), rel)
        for rel in ("other.log", "plain.txt", "link"):
            self.assertFalse(present(rel), rel)
        with open(os.path.join(path, "tracked.txt"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "committed\n")

    def test_worktreeinclude_never_writes_through_or_over_the_base_tree(self):
        outside = os.path.join(self.base, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.main, "link"))
        _write(self.main, "cfg.env", "committed\n")
        _git(self.main, "add", "link", "cfg.env")
        base = self.commit(self.main, "symlink and cfg")
        _git(self.main, "update-ref", "refs/remotes/origin/main", base)
        _git(self.main, "rm", "-q", "link", "cfg.env")
        self.commit(self.main, "drop them")
        _write(self.main, ".gitignore", ".claude/\nlink/\ncfg.env\n")
        _write(self.main, "link/a.key", "a\n")
        _write(self.main, "cfg.env", "local\n")
        _write(self.main, ".worktreeinclude", "link/\ncfg.env\n")
        path = self.created_path(self.create("esc"))
        self.assertEqual(os.listdir(outside), [])
        with open(os.path.join(path, "cfg.env"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "committed\n")

    def test_worktreeinclude_copy_failure_rolls_back(self):
        _write(self.main, ".gitignore", ".claude/\n.env\n")
        _write(self.main, ".worktreeinclude", ".env\n")
        secret = _write(self.main, ".env", "E\n")
        os.chmod(secret, 0)
        self.addCleanup(os.chmod, secret, 0o600)
        path = os.path.join(self.main, ".claude", "worktrees", "rb")
        self.assertRefused(self.create("rb"), "rolled back")
        self.assertFalse(os.path.lexists(path))
        self.assertNotIn("worktree-rb", self.branches())

    # -- WorktreeCreate: resume -------------------------------------------

    def test_second_create_resumes_the_registered_worktree(self):
        path = self.created_path(self.create("again"))
        _write(path, "work.txt", "w\n")
        proc = self.create("again")
        self.assertEqual(proc.stdout.strip().splitlines(), [path])
        self.assertEqual(self.created_path(proc), path)
        self.assertTrue(os.path.isfile(os.path.join(path, "work.txt")))

    # -- WorktreeCreate: refusals -----------------------------------------

    def assertRefused(self, proc, fragment):
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertEqual(proc.stdout, "")
        self.assertIn(fragment, proc.stderr)

    def test_refuses_dotdot_name(self):
        self.assertRefused(self.create("../escape"), "'..'")

    def test_refuses_absolute_name(self):
        self.assertRefused(self.create(os.path.join(self.base, "abs")), "relative")

    def test_refuses_empty_name(self):
        self.assertRefused(self.create(""), "non-empty")

    def test_refuses_variable_key(self):
        self.set_key("$HOME/wt")
        self.assertRefused(self.create("v"), "variables are not expanded")

    def test_refuses_key_outside_project(self):
        self.set_key("../elsewhere")
        self.assertRefused(self.create("v"), "strictly inside the project")

    def test_refuses_symlinked_root_escaping_project(self):
        outside = os.path.join(self.base, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.main, "wt"))
        self.set_key("wt")
        self.assertRefused(self.create("s"), "strictly inside the project")
        self.assertEqual(os.listdir(outside), [])

    def test_refuses_native_root_behind_a_symlinked_claude_dir(self):
        outside = os.path.join(self.base, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.main, ".claude"))
        self.assertRefused(self.create("r1"), "not strictly inside")
        self.assertEqual(os.listdir(outside), [])

    def test_refuses_name_that_is_a_symlink_to_a_registered_worktree(self):
        root = os.path.join(self.main, ".claude", "worktrees")
        os.makedirs(root)
        os.symlink(self.linked, os.path.join(root, "evil"))
        self.assertRefused(self.create("evil"), "resolves to")

    def test_refuses_existing_path(self):
        os.makedirs(os.path.join(self.main, ".claude", "worktrees", "taken"))
        self.assertRefused(self.create("taken"), "already exists")

    # -- SubagentStop ------------------------------------------------------

    def stop(self, agent_id, cwd):
        proc = self.run_hook({"hook_event_name": "SubagentStop", "agent_id": agent_id,
                              "cwd": cwd})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")
        return proc

    def test_subagent_stop_removes_clean_worktree_without_commits(self):
        path = self.created_path(self.create("agent-abc"))
        self.stop("abc", path)
        self.assertFalse(os.path.exists(path))
        self.assertNotIn("worktree-agent-abc", self.branches())

    def test_subagent_stop_keeps_dirty_worktree(self):
        path = self.created_path(self.create("agent-dirty"))
        _write(path, "new.txt", "x\n")
        self.stop("dirty", path)
        self.assertTrue(os.path.isdir(path))
        self.assertIn("worktree-agent-dirty", self.branches())

    def test_subagent_stop_keeps_worktree_with_new_commit(self):
        path = self.created_path(self.create("agent-work"))
        self.commit(path, "agent work")
        self.stop("work", path)
        self.assertTrue(os.path.isdir(path))
        self.assertIn("worktree-agent-work", self.branches())

    def test_subagent_stop_ignores_non_matching_cwd(self):
        path = self.created_path(self.create("agent-mine"))
        self.stop("other", path)
        self.stop("mine", self.main)
        self.assertTrue(os.path.isdir(path))

    def test_subagent_stop_keeps_detached_head_worktree(self):
        path = self.created_path(self.create("agent-det"))
        _git(path, "checkout", "-q", "--detach")
        self.stop("det", path)
        self.assertTrue(os.path.isdir(path))

    def test_subagent_stop_ignores_agent_branch_outside_the_root(self):
        path = os.path.join(self.main, ".worktrees", "agent-zz")
        _git(self.main, "worktree", "add", "-q", "-b", "worktree-agent-zz", path)
        self.stop("zz", path)
        self.assertTrue(os.path.isdir(path))

    def test_subagent_stop_git_failure_still_exits_zero(self):
        path = self.created_path(self.create("agent-bad"))
        _git(self.main, "worktree", "lock", path)
        self.stop("bad", path)
        self.assertTrue(os.path.isdir(path))

    # -- WorktreeRemove ----------------------------------------------------

    def test_worktree_remove_removes_and_deletes_branch(self):
        path = self.created_path(self.create("ew1"))
        proc = self.run_hook({"hook_event_name": "WorktreeRemove", "cwd": path,
                              "worktree_path": path})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(path))
        self.assertNotIn("worktree-ew1", self.branches())

    def test_worktree_remove_nonexistent_path_is_ok(self):
        proc = self.run_hook({"hook_event_name": "WorktreeRemove", "cwd": self.main,
                              "worktree_path": os.path.join(self.base, "gone")})
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_worktree_remove_refuses_main_checkout(self):
        proc = self.run_hook({"hook_event_name": "WorktreeRemove", "cwd": self.main,
                              "worktree_path": self.main})
        self.assertEqual(proc.returncode, 1)
        self.assertTrue(os.path.isdir(self.main))

    def test_worktree_remove_refuses_worktree_outside_the_root(self):
        _write(self.linked, "mine.txt", "m\n")
        proc = self.run_hook({"hook_event_name": "WorktreeRemove", "cwd": self.main,
                              "worktree_path": self.linked})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("left in place", proc.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.linked, "mine.txt")))

    def test_worktree_remove_refuses_unregistered_dir_in_root(self):
        stray = os.path.join(self.main, ".claude", "worktrees", "stray")
        os.makedirs(stray)
        proc = self.run_hook({"hook_event_name": "WorktreeRemove", "cwd": self.main,
                              "worktree_path": stray})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("is not a linked worktree", proc.stderr)
        self.assertTrue(os.path.isdir(stray))

    def remove(self, path):
        return self.run_hook({"hook_event_name": "WorktreeRemove", "cwd": path,
                              "worktree_path": path})

    def assertKept(self, proc, path, branch, fragment):
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn(fragment, proc.stderr)
        self.assertIn("left in place", proc.stderr)
        self.assertTrue(os.path.isdir(path))
        self.assertIn(branch, self.branches())

    def test_worktree_remove_keeps_dirty_tracked_change(self):
        self.set_key(".worktrees")
        path = self.created_path(self.create("r2"))
        _write(path, "README", "changed\n")
        self.assertKept(self.remove(path), path, "worktree-r2", "uncommitted changes")

    def test_worktree_remove_keeps_untracked_file(self):
        self.set_key(".worktrees")
        path = self.created_path(self.create("ru"))
        _write(path, "new.txt", "n\n")
        self.assertKept(self.remove(path), path, "worktree-ru", "uncommitted changes")

    def test_worktree_remove_keeps_untracked_file_when_status_hides_them(self):
        self.set_key(".worktrees")
        _git(self.main, "config", "status.showUntrackedFiles", "no")
        path = self.created_path(self.create("rh"))
        _write(path, "new.txt", "n\n")
        self.assertKept(self.remove(path), path, "worktree-rh", "uncommitted changes")

    def test_worktree_remove_keeps_assume_unchanged_edit(self):
        self.set_key(".worktrees")
        path = self.created_path(self.create("ra"))
        _git(path, "update-index", "--assume-unchanged", "README")
        _write(path, "README", "hidden edit\n")
        self.assertKept(self.remove(path), path, "worktree-ra", "hidden change")

    def test_worktree_remove_keeps_skip_worktree_edit(self):
        self.set_key(".worktrees")
        path = self.created_path(self.create("rs"))
        _git(path, "update-index", "--skip-worktree", "README")
        _write(path, "README", "hidden edit\n")
        self.assertKept(self.remove(path), path, "worktree-rs", "hidden change")

    def test_worktree_remove_outside_any_repo_names_the_path(self):
        outside = os.path.join(self.base, "loose")
        os.makedirs(outside)
        proc = self.remove(outside)
        self.assertEqual(proc.returncode, 1)
        self.assertIn(outside + " is not a worktree this hook manages", proc.stderr)
        self.assertTrue(os.path.isdir(outside))

    def test_worktree_remove_keeps_branch_with_own_commit(self):
        self.set_key(".worktrees")
        path = self.created_path(self.create("r3"))
        self.commit(path, "own work")
        self.assertKept(self.remove(path), path, "worktree-r3", "commits on no other ref")

    def test_worktree_remove_keeps_hand_made_worktree_with_untracked_files(self):
        self.set_key(".worktrees")
        path = os.path.join(self.main, ".worktrees", "lane")
        _git(self.main, "worktree", "add", "-q", "-b", "feature", path)
        _write(path, "wip", "w\n")
        self.assertKept(self.remove(path), path, "feature", "not worktree-lane")
        self.assertTrue(os.path.isfile(os.path.join(path, "wip")))

    def test_worktree_remove_keeps_clean_hand_made_worktree_on_other_branch(self):
        self.set_key(".worktrees")
        path = os.path.join(self.main, ".worktrees", "lane")
        _git(self.main, "worktree", "add", "-q", "-b", "feature", path)
        self.assertKept(self.remove(path), path, "feature", "not worktree-lane")

    def test_worktree_remove_keeps_users_own_worktree_foo_branch(self):
        # Same path and branch shape as a hook worktree: the unique-commit guard is what holds.
        self.set_key(".worktrees")
        path = os.path.join(self.main, ".worktrees", "foo")
        _git(self.main, "worktree", "add", "-q", "-b", "worktree-foo", path)
        self.commit(path, "user work")
        self.assertKept(self.remove(path), path, "worktree-foo", "commits on no other ref")

    def test_worktree_remove_under_key_removes_clean_tree_with_ignored_files(self):
        self.set_key(".worktrees")
        path = self.created_path(self.create("ok"))
        _write(path, ".claude/scratch", "ignored\n")
        proc = self.remove(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(path))
        self.assertNotIn("worktree-ok", self.branches())

    def test_worktree_remove_keeps_branch_when_not_merged_into_head(self):
        tip = self.commit(self.main, "main moves on")
        path = self.created_path(self.create("unmerged"))
        _git(self.main, "checkout", "-q", "-b", "elsewhere", "HEAD~1")
        proc = self.remove(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(path))
        self.assertIn("worktree-unmerged", self.branches())
        self.assertIn("kept branch", proc.stderr)
        self.assertEqual(_git(self.main, "rev-parse", "worktree-unmerged"), tip)

    def test_worktree_remove_accepts_native_path_while_key_is_set(self):
        self.set_key(".worktrees")
        path = os.path.join(self.main, ".claude", "worktrees", "nat")
        _git(self.main, "worktree", "add", "-q", "-b", "worktree-nat", path)
        proc = self.remove(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(path))
        self.assertNotIn("worktree-nat", self.branches())

    def test_worktree_remove_refuses_hook_shaped_worktree_outside_both_roots(self):
        self.set_key(".worktrees")
        path = os.path.join(self.main, ".claude", "x")
        _git(self.main, "worktree", "add", "-q", "-b", "worktree-x", path)
        self.assertKept(self.remove(path), path, "worktree-x", "is not directly under")

    def test_worktree_remove_native_path_while_key_is_set_keeps_dirty(self):
        self.set_key(".worktrees")
        path = os.path.join(self.main, ".claude", "worktrees", "natd")
        _git(self.main, "worktree", "add", "-q", "-b", "worktree-natd", path)
        _write(path, "wip", "w\n")
        self.assertKept(self.remove(path), path, "worktree-natd", "uncommitted changes")

    # -- layouts with no main checkout -------------------------------------

    def separate_git_dir_repo(self):
        top = os.path.join(self.base, "sep")
        _git(self.base, "init", "-q", "--separate-git-dir",
             os.path.join(self.base, "sep-git"), top)
        _write(top, ".gitignore", ".claude/\n")
        _git(top, "add", ".gitignore")
        self.commit(top, "sep")
        return top

    def submodule_repo(self):
        src = os.path.join(self.base, "subsrc")
        os.makedirs(src)
        _git(src, "init", "-q")
        _write(src, ".gitignore", ".claude/\n")
        _git(src, "add", ".gitignore")
        self.commit(src, "sub")
        sup = os.path.join(self.base, "sup")
        os.makedirs(sup)
        _git(sup, "init", "-q")
        _git(sup, "-c", "protocol.file.allow=always", "submodule", "add", "-q", src, "sub")
        return os.path.join(sup, "sub")

    def assert_native_round_trip(self, top):
        path = self.created_path(self.create("lay", cwd=top))
        self.assertEqual(path, os.path.join(top, ".claude", "worktrees", "lay"))
        proc = self.remove(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(path))

    def test_separate_git_dir_without_key_uses_native_layout(self):
        self.assert_native_round_trip(self.separate_git_dir_repo())

    def test_separate_git_dir_fresh_fetch_head_skips_fetch(self):
        top = self.separate_git_dir_repo()
        _git(top, "remote", "add", "origin", os.path.join(self.base, "no-such-origin"))
        _write(os.path.join(self.base, "sep-git"), "FETCH_HEAD", "")
        proc = self.create("fresh", cwd=top)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("fetch", proc.stderr)

    def test_separate_git_dir_with_key_refuses(self):
        top = self.separate_git_dir_repo()
        _write(top, ".claude/atelier.local.md", "---\ncheckout-root: .worktrees\n---\n")
        self.assertRefused(self.create("lay", cwd=top), "unsupported git layout")

    def test_submodule_without_key_uses_native_layout(self):
        self.assert_native_round_trip(self.submodule_repo())

    def test_submodule_with_key_refuses(self):
        top = self.submodule_repo()
        _write(top, ".claude/atelier.local.md", "---\ncheckout-root: .worktrees\n---\n")
        self.assertRefused(self.create("lay", cwd=top), "unsupported git layout")

    def test_other_event_is_silent(self):
        proc = self.run_hook({"hook_event_name": "PreToolUse", "cwd": self.main})
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
