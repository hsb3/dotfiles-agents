"""Tests for primitives-core/hooks/skills-cli-guard/hook.py.

Every case drives `main()` in-process with a PreToolUse payload on stdin and reads what it
printed: one deny object, or nothing.
"""

import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK_PATH = os.path.join(REPO_ROOT, "primitives-core", "hooks", "skills-cli-guard", "hook.py")

_spec = importlib.util.spec_from_file_location("skills_cli_guard_hook", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

OVERRIDE = "ATELIER_SKILLS_CLI_OVERRIDE=1"


def run(stdin_text):
    saved = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = io.StringIO(stdin_text), io.StringIO()
    try:
        hook.main()
        return sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = saved


def payload(command, tool="Bash"):
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool,
                       "tool_input": {"command": command}})


def bash(command):
    return run(payload(command))


class GuardCase(unittest.TestCase):

    def assertDenied(self, command):
        out = bash(command)
        self.assertTrue(out, "not denied: %r" % command)
        decision = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(decision["hookEventName"], "PreToolUse")
        self.assertEqual(decision["permissionDecision"], "deny")
        return decision["permissionDecisionReason"]

    def assertSilent(self, command):
        self.assertEqual(bash(command), "", "denied: %r" % command)


class RunnerSpellingTests(GuardCase):

    def test_npx(self):
        self.assertDenied("npx skills add some/repo")

    def test_npx_yes_flags(self):
        self.assertDenied("npx -y skills add some/repo")
        self.assertDenied("npx --yes skills add some/repo")

    def test_npx_versioned_package(self):
        self.assertDenied("npx skills@latest add some/repo")
        self.assertDenied("npx skills@1.2.3 remove -g --all")

    def test_bunx(self):
        self.assertDenied("bunx skills add some/repo")

    def test_bun_x(self):
        self.assertDenied("bun x skills add some/repo")

    def test_pnpx(self):
        self.assertDenied("pnpx skills add some/repo")

    def test_pnpm_dlx(self):
        self.assertDenied("pnpm dlx skills add some/repo")

    def test_yarn_dlx(self):
        self.assertDenied("yarn dlx skills add some/repo")

    def test_npm_exec(self):
        self.assertDenied("npm exec skills add some/repo")

    def test_npm_exec_double_dash(self):
        self.assertDenied("npm exec -- skills add some/repo")

    def test_runner_by_path(self):
        self.assertDenied("/usr/local/bin/npx skills add some/repo")

    def test_bare_run_with_no_arguments_is_denied(self):
        self.assertDenied("npx skills")


class HelpExemptionTests(GuardCase):

    def test_help_and_version_pass(self):
        for flag in ("--help", "-h", "--version", "-V"):
            with self.subTest(flag=flag):
                self.assertSilent("npx skills " + flag)

    def test_help_with_stderr_redirect_passes(self):
        self.assertSilent("npx skills --help 2>&1 | head -40")

    def test_help_beside_a_real_argument_is_denied(self):
        self.assertDenied("npx skills add some/repo --help")


class CommandPositionTests(GuardCase):

    def test_after_each_separator(self):
        for sep in (";", "&&", "||", "|", "\n"):
            with self.subTest(sep=sep):
                self.assertDenied("cd /repo " + sep + " npx skills add some/repo")

    def test_after_leading_assignments(self):
        self.assertDenied("CI=1 FOO=bar npx skills add some/repo")

    def test_inside_command_substitution(self):
        self.assertDenied("out=$(npx skills list)")
        self.assertDenied("echo $(npx skills list)")

    def test_inside_backticks(self):
        self.assertDenied("out=`npx skills list`")

    def test_inside_a_subshell(self):
        self.assertDenied("(npx skills add some/repo)")

    def test_after_a_keyword(self):
        self.assertDenied("if true; then npx skills add some/repo; fi")

    def test_continued_line(self):
        self.assertDenied("npx \\\n  skills add some/repo")

    def test_after_a_heredoc_closes(self):
        self.assertDenied("cat <<EOF > notes\nhello\nEOF\nnpx skills add some/repo")

    def test_after_a_complete_line_before_an_unterminated_quote(self):
        self.assertDenied("npx skills add some/repo\necho 'oops")


class TextIsSilentTests(GuardCase):

    def test_quoted_arguments(self):
        self.assertSilent('echo "npx skills add x"')
        self.assertSilent('git commit -m "npx skills add x; bunx skills remove -g --all"')
        self.assertSilent("rg 'npx skills'")
        self.assertSilent("echo 'a && npx skills add x'")

    def test_heredoc_bodies(self):
        for opener in ("<<EOF", "<<'EOF'", '<<"EOF"', "<< EOF"):
            with self.subTest(opener=opener):
                self.assertSilent("cat " + opener + " > f\nnpx skills add x\nEOF")

    def test_dash_heredoc_body(self):
        self.assertSilent("cat <<-EOF > f\n\tnpx skills add x\n\tEOF")

    def test_heredoc_body_with_unbalanced_quote(self):
        self.assertSilent("cat <<'EOF' > f\nit's here\nnpx skills add x\nEOF\necho done")

    def test_comments(self):
        self.assertSilent("# npx skills add x")
        self.assertSilent("true # npx skills add x")

    def test_other_packages(self):
        self.assertSilent("npx skillset add x")
        self.assertSilent("npx @x/skills add x")
        self.assertSilent("npx prettier skills")

    def test_skills_as_an_argument(self):
        self.assertSilent("ls ~/.claude/skills")
        self.assertSilent("echo $(date) npx skills add x")

    def test_unterminated_quote_fails_open(self):
        self.assertSilent("echo \"oops\nnpx skills add x")


class OverrideTests(GuardCase):

    def test_prefix_passes(self):
        self.assertSilent(OVERRIDE + " npx skills add some/repo")
        self.assertSilent("cd /repo && " + OVERRIDE + " npx skills add some/repo")

    def test_prefix_among_other_assignments_passes(self):
        self.assertSilent("CI=1 " + OVERRIDE + " npx skills add some/repo")

    def test_on_a_previous_line_still_denies(self):
        self.assertDenied(OVERRIDE + "\nnpx skills add some/repo")

    def test_on_a_previous_command_still_denies(self):
        self.assertDenied("export " + OVERRIDE + "; npx skills add some/repo")
        self.assertDenied(OVERRIDE + "; npx skills add some/repo")

    def test_as_an_argument_still_denies(self):
        self.assertDenied("npx skills add some/repo " + OVERRIDE)

    def test_covers_only_its_own_command(self):
        self.assertDenied(OVERRIDE + " npx skills list && npx skills add some/repo")

    def test_deny_reason_names_the_trap_safe_path_and_override(self):
        reason = self.assertDenied("npx skills add some/repo")
        self.assertIn("skills-lock.json", reason)
        self.assertIn("by hand", reason)
        self.assertIn(OVERRIDE + " npx skills", reason)


class FailOpenTests(unittest.TestCase):

    def test_bad_stdin(self):
        for text in ("", "not json", "[1, 2]", "null"):
            with self.subTest(text=text):
                self.assertEqual(run(text), "")

    def test_non_bash_tool(self):
        self.assertEqual(run(payload("npx skills add x", tool="Write")), "")

    def test_missing_or_odd_command(self):
        for data in ({"tool_name": "Bash"},
                     {"tool_name": "Bash", "tool_input": {}},
                     {"tool_name": "Bash", "tool_input": "npx skills add x"},
                     {"tool_name": "Bash", "tool_input": {"command": 5}}):
            with self.subTest(data=data):
                self.assertEqual(run(json.dumps(data)), "")


class CardReproductionTests(unittest.TestCase):
    """The hook as the harness runs it: a separate process, payload on stdin, exit 0."""

    def test_npx_skills_add_is_denied_end_to_end(self):
        proc = subprocess.run(
            [sys.executable, HOOK_PATH], input=payload("npx skills add some/repo"),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        decision = json.loads(proc.stdout)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
