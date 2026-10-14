"""Timing guard for card z0h1: heredoc terminator search must stay near-linear.

Each adversarial shape is a large unterminated (or abandoned) heredoc command run
through both git guards' pure entry points; every call must finish within BUDGET of CPU time,
well under the 10 s hook timeout. n per shape is the smallest that put the
quadratic implementation at >= 2x BUDGET. Stdlib-only.
"""

import time
import unittest

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


for _g, _run in GUARDS.items():
    for _s, (_n, _b) in SHAPES.items():
        setattr(GitGuardTiming, f"test_{_g}_{_s}", _make(_g, _run, _s, _n, _b))

if __name__ == "__main__":
    unittest.main()
