"""Tests for primitives-core/hooks/zsh-modifier-lint/hook.py.

The unit cases run main() in-process on a JSON payload. The differential leg runs each probe
under /bin/zsh -f (isolated HOME, minimal env) next to the same probe with the name braced,
and asserts the lint fires exactly when zsh's output differs.
"""

import importlib.util
import io
import json
import os
import string
import subprocess
import sys
import tempfile
import time
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK_PATH = os.path.join(REPO_ROOT, "primitives-core", "hooks", "zsh-modifier-lint", "hook.py")

_spec = importlib.util.spec_from_file_location("zsh_modifier_lint_hook", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

OVERRIDE = "ATELIER_ZSH_MODIFIER_OVERRIDE=1"
LETTERS = "acehlqrstuAPQ"
ZSH = "/bin/zsh"


def run(stdin_text):
    """main() with `stdin_text` on stdin -> (exit code, stdout)."""
    stdin, stdout = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = io.StringIO(stdin_text), io.StringIO()
    code = 0
    try:
        hook.main()
    except SystemExit as e:
        code = e.code or 0
    finally:
        out = sys.stdout.getvalue()
        sys.stdin, sys.stdout = stdin, stdout
    return code, out


def reason(command):
    """The deny reason for a Bash `command`, or "" when the hook stays silent."""
    code, out = run(json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}))
    if code != 0:
        raise AssertionError("exit {0}".format(code))
    if not out.strip():
        return ""
    spec = json.loads(out)["hookSpecificOutput"]
    assert spec["hookEventName"] == "PreToolUse"
    assert spec["permissionDecision"] == "deny"
    return spec["permissionDecisionReason"]


class Denies(unittest.TestCase):

    def assertDenies(self, command):
        self.assertTrue(reason(command), "expected a deny: {0!r}".format(command))

    def test_card_reproduction_names_the_braced_rewrite(self):
        r = reason("T=main; git push origin $T:refs/heads/x")
        self.assertIn("$T:refs/heads/x", r)
        self.assertIn('"${T}:refs/heads/x"', r)
        self.assertIn(OVERRIDE + " <command>", r)

    def test_every_modifier_letter_denies(self):
        for letter in LETTERS:
            with self.subTest(letter=letter):
                self.assertDenies("echo $T:{0}x".format(letter))

    def test_ampersand_denies_where_it_is_not_a_separator(self):
        self.assertDenies('echo "$T:&x"')
        self.assertDenies("cat <<EOF\n$T:&x\nEOF")

    def test_positional_parameters_deny(self):
        self.assertDenies("echo $1:r")
        self.assertDenies("echo $12:h")

    def test_expanding_contexts_deny(self):
        for command in ('echo "$T:r"',
                        "cat <<EOF\n$T:r\nEOF",
                        "cat <<-EOF\n\t$T:r\n\tEOF",
                        "x=$(basename $T:r)",
                        'x="$(basename $T:r)"',
                        "x=`basename $T:r`",
                        "echo a$T:r",
                        "echo $T$U:h"):
            with self.subTest(command=command):
                self.assertDenies(command)

    def test_prefix_modifiers_deny(self):
        self.assertDenies("git push origin $B:feature/x")
        self.assertDenies("git push origin $B:gh-pages")
        self.assertDenies("echo $T:ws/a/b/")

    def test_path_style_assignment_with_a_letter_denies(self):
        self.assertDenies("P=$PATH:essential")

    def test_hit_after_a_quoted_heredoc_terminator_denies(self):
        self.assertDenies("cat <<'EOF'\n$T:r\nEOF\necho $T:r")

    def test_rewrite_adds_quotes_only_where_they_are_syntax(self):
        self.assertIn("`${T}:r`", reason('echo "$T:r"'))
        self.assertIn("`${T}:r`", reason("cat <<EOF\n$T:r\nEOF"))
        self.assertIn('`"${T}:r"`', reason("echo $T:r"))

    def test_rewrite_stops_at_an_enclosing_brace(self):
        self.assertIn('`$T:r` -> `"${T}:r"`', reason("echo ${X:-$T:r}"))

    def test_every_hit_is_listed_up_to_the_cap(self):
        r = reason("echo $A:r $B:r $C:r $D:r $E:r $F:r $G:r")
        for name in "ABCDE":
            self.assertIn("${%s}:r" % name, r)
        self.assertNotIn("${F}", r)
        self.assertIn("2 more", r)


class Silent(unittest.TestCase):

    def test_forms_zsh_does_not_modify_pass(self):
        for command in ("echo '$T:r'",
                        "echo $'$T:r'",
                        "echo $'it\\'s $T:r'",
                        "cat <<'EOF'\n$T:r\nEOF",
                        'cat <<"EOF"\n$T:r\nEOF',
                        "cat <<\\EOF\n$T:r\nEOF",
                        "cat <<'EOF'\n$T:r",
                        "cat <<EOF\n\\$T:r $T\\:r\nEOF",
                        "echo ${T}:r",
                        '"${T}:refs/heads/x"',
                        "echo \\$T:r",
                        "echo $T\\:r",
                        '"$T":r',
                        "echo $PATH:/usr/bin",
                        "echo $HOME:$X",
                        "echo $T:-x $T:=x $T:+x $T:?x",
                        "echo $T:&x",
                        "echo $T:fix/y $T:wip $T:x $T:Fx",
                        "echo $$T:r",
                        "echo hi # $T:r",
                        "echo $T:\\r",
                        'echo "$(echo \'$T:r\')"',
                        "git push origin HEAD:refs/heads/x"):
            with self.subTest(command=command):
                self.assertEqual(reason(command), "")


class Override(unittest.TestCase):

    def test_prefix_on_the_offending_command_passes(self):
        self.assertEqual(reason(OVERRIDE + " git push origin $T:refs/heads/x"), "")
        self.assertEqual(reason("A=1 " + OVERRIDE + " echo $T:r"), "")
        self.assertEqual(reason("true; " + OVERRIDE + " echo $T:r"), "")
        self.assertEqual(reason(OVERRIDE + " cat <<EOF\n$T:r\nEOF"), "")
        self.assertEqual(reason(OVERRIDE + " echo $(echo $T:r)"), "")

    def test_prefix_elsewhere_still_denies(self):
        for command in (OVERRIDE + "\ngit push origin $T:refs/heads/x",
                        OVERRIDE + "; echo $T:r",
                        "echo " + OVERRIDE + " $T:r",
                        "ATELIER_ZSH_MODIFIER_OVERRIDE=0 echo $T:r"):
            with self.subTest(command=command):
                self.assertTrue(reason(command))

    def test_prefix_covers_only_its_own_command(self):
        r = reason(OVERRIDE + " echo $T:r; echo $U:h")
        self.assertIn("$U:h", r)
        self.assertNotIn("$T:r", r)


class FailOpen(unittest.TestCase):

    def test_malformed_or_foreign_payloads_are_silent(self):
        for text in ("", "not json", "[]", '"x"',
                     json.dumps({"tool_name": "Write", "tool_input": {"command": "echo $T:r"}}),
                     json.dumps({"tool_name": "Bash"}),
                     json.dumps({"tool_name": "Bash", "tool_input": "echo $T:r"}),
                     json.dumps({"tool_name": "Bash", "tool_input": {"command": 7}})):
            with self.subTest(stdin=text):
                self.assertEqual(run(text), (0, ""))

    def test_script_entry_point_fails_open(self):
        proc = subprocess.run([sys.executable, HOOK_PATH], input="{", capture_output=True,
                              text=True, timeout=10)
        self.assertEqual((proc.returncode, proc.stdout), (0, ""))

    def test_script_entry_point_denies(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "echo $T:r"}})
        proc = subprocess.run([sys.executable, HOOK_PATH], input=payload,
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("deny", proc.stdout)


class Timing(unittest.TestCase):
    """Each shape gets 2 s of the hook's 10 s timeout, which fails open when it runs out."""

    def test_deep_nesting_finishes_inside_the_budget(self):
        shapes = (
            ("$(" * 2000 + "x" * 200000, 0),
            # a hit per command under every frame: the override check must not walk the stack
            ("$(" * 2000 + "$x:r;" * 40000, 1),
            # an override check per command start must stop at the end of its command
            ("A=$x:r;" * 40000, 1),
            ("A=$x:r\n" * 40000, 1),
        )
        for command, denied in shapes:
            with self.subTest(command=command[-20:], size=len(command)):
                started = time.monotonic()
                try:
                    proc = subprocess.run(
                        [sys.executable, HOOK_PATH],
                        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
                        capture_output=True, text=True, timeout=10)
                except subprocess.TimeoutExpired:
                    self.fail("ran past the hook's 10 s timeout")
                self.assertLess(time.monotonic() - started, 2.0)
                self.assertEqual(len(proc.stdout.splitlines()), denied)


@unittest.skipUnless(os.path.exists(ZSH), "no /bin/zsh (Linux CI)")
class ZshDifferential(unittest.TestCase):
    """zsh is the oracle: the lint fires iff the unbraced probe expands differently."""

    PRE = "T=/a/b.c; set -- /a/b.c; "

    WORDS = [
        "$T:refs/heads/x", '"$T:refs/heads/x"', "$1:rx", "$T:feature/x", "$T:gh-pages",
        "$T:warn", "$T:fix/y", "$T:wip", "$T:gs/a/z/", "$T:ffr", "P=$T:essential",
        "a$T:rx", "$T$T:hx", "$T:r:h", "$(print -r -- $T:rx)", '"$(print -r -- $T:rx)"',
        "$T:-x", "$T:=x", "$T:+x", "$T:?x", "$T:/usr/bin", "$T:$T", "$T\\:rx",
        '"$T\\:rx"', '"$T":rx', "$T:\\rx", "$T:Fx", "$T:Wx", "$T:&x", '"$T:&x"',
    ]

    # the four places zsh expands a parameter
    FORMS = ["print -r -- {0}", 'print -r -- "{0}"', "cat <<EOF\n{0}\nEOF",
             "print -r -- $(print -r -- {0})"]

    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.TemporaryDirectory(prefix="zsh-modifier-lint-")

    @classmethod
    def tearDownClass(cls):
        cls.home.cleanup()

    def zsh(self, script):
        proc = subprocess.run([ZSH, "-f", "-c", self.PRE + script],
                              env={"HOME": self.home.name, "PATH": "/usr/bin:/bin"},
                              cwd=self.home.name, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=10)
        return proc.stdout, proc.stderr

    def assertAgrees(self, script):
        braced = script.replace("$T", "${T}").replace("$1", "${1}")
        corrupts = self.zsh(script) != self.zsh(braced)
        fired = bool(reason(self.PRE + script))
        self.assertEqual(fired, corrupts, "{0!r}: zsh {1}, lint {2}".format(
            script, "corrupts" if corrupts else "leaves it", "fired" if fired else "silent"))

    def test_lint_fires_exactly_when_zsh_corrupts(self):
        for word in self.WORDS:
            with self.subTest(word=word):
                self.assertAgrees("print -r -- " + word)

    def test_modifier_class_is_complete(self):
        for form in self.FORMS:
            for char in string.ascii_letters + "&":
                with self.subTest(form=form, char=char):
                    self.assertAgrees(form.format("$T:{0}x".format(char)))

    def test_prefix_modifiers_are_complete(self):
        for prefix in "fgw":
            for char in string.ascii_letters + "&":
                with self.subTest(prefix=prefix, char=char):
                    self.assertAgrees('print -r -- "$T:{0}{1}x"'.format(prefix, char))


if __name__ == "__main__":
    unittest.main()
