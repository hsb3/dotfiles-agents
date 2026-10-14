"""Timing guard for card z0h1: heredoc terminator search must stay near-linear.

Each adversarial shape is a large unterminated (or abandoned) heredoc command run
through both git guards' pure entry points; every call must finish within BUDGET of CPU time,
well under the 10 s hook timeout. n per shape is the smallest that put the
quadratic implementation at >= 2x BUDGET. Stdlib-only.
"""

import resource
import time
import unittest

from tests import test_live_worker_git_guard as live_hook
from tests.test_git_guard_differential import LIVE, SCOPE, scope_flags

BUDGET = 2.0


def _live(command):
    return LIVE._mutating_call(command)


def _scope(command):
    return scope_flags(command)


GUARDS = {"live": _live, "scope": _scope}

# shape name -> (lines, builder(n))
SHAPES = {
    "unterminated_words": (9500, lambda n: "\n".join(f"cat <<'W{k}'" for k in range(n))),
    "repeated_eof": (6500, lambda n: "\n".join("cat <<EOF" for _ in range(n))),
    "rollback": (6500, lambda n: "\n".join(f"cat <<A <<B{k}" for k in range(n)) + "\nA"),
    "trailing_backslash": (
        6500, lambda n: "\n".join("cat <<EOF" for _ in range(n)) + "\nx\\"),
    "paren": (4000, lambda n: "\n".join(f"x=$(cat <<W{k}" for k in range(n))),
}


class GitGuardTiming(unittest.TestCase):
    pass


def _make(guard, run, shape, lines, build):
    def test(self):
        command = build(lines)
        start = time.process_time()  # CPU time: host load cannot flake it, a quadratic still costs
        run(command)
        elapsed = time.process_time() - start
        self.assertLess(
            elapsed, BUDGET,
            f"guard={guard} shape={shape} lines={lines} elapsed={elapsed:.2f}s "
            f"(budget {BUDGET}s)")
    return test


class LiveHookDecisionTiming(unittest.TestCase):
    """The whole hook, live worker present: a call the first reading finds is
    decided before the slower nest readings run (8wzs, review D1)."""

    def test_plain_push_before_nested_subshells_is_denied_in_budget(self):
        case = live_hook.LiveWorkerGitGuardTests("run")
        case.setUp()
        self.addCleanup(case.doCleanups)
        case._sidecar("e1111111111111111")
        command = "git push origin HEAD;\necho `a`\n" + "\n".join(
            f"( cat <<W{k}" for k in range(12000))
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        result = case._run(case._payload(command))
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        elapsed = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
        self.assertIn("push", case._assert_denied(result))
        self.assertLess(elapsed, BUDGET, f"full hook elapsed={elapsed:.2f}s (budget {BUDGET}s)")


for _g, _run in GUARDS.items():
    for _s, (_n, _b) in SHAPES.items():
        setattr(GitGuardTiming, f"test_{_g}_{_s}", _make(_g, _run, _s, _n, _b))

if __name__ == "__main__":
    unittest.main()
