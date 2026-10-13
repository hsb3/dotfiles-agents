# agent-harness

Measures whether a coding-agent extender (a skill, a set of subagent definitions or a Claude Code plugin, the
**candidate**) makes a headless coding agent better at real tasks: every case runs with the candidate injected
(`with`) and without it (`baseline`) under Claude Code, opencode or Codex, each trial is graded by the case's
`check.py` and an LLM rubric grader, and one JSON row per trial is appended to `results.jsonl`. `SPEC.md` is the
full statement of behaviour.

```sh
bun install
bun src/cli.ts --help
bun src/cli.ts <candidate> --candidate-dir <path> --cases-dir <dir>          # run the grid (resumes)
bun src/cli.ts <candidate> --candidate-dir <path> --smoke                     # loadability check
bun src/cli.ts <candidate> --report                                           # pass rates and deltas
bun src/cli.ts campaign --cases-dir <dir> --candidates-root <dir> --dry-run   # weekly campaign
sh scripts/launchd.sh install <cases-dir> <candidates-root>                   # schedule it (macOS)
```

Gate: `bunx tsc --noEmit && bun test`. The tests run stub `claude`, `opencode`, `codex` and `python3`
executables and never reach the network.
