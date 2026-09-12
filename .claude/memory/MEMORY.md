# Memory Index

Durable repository policy belongs in [AGENTS.md](../../AGENTS.md) and the linked docs; these notes retain only local findings that still guide implementation.

- [Signals need end-state checks](signals-that-lie.md) — CI output, Mermaid rendering, kata writes, and probes can report success without the intended result.
- [Tracker workflow rulings](feedback-tracker-workflow.md) — work only owner-selected cards and reproduce the current symptom before implementation and closure.
- [Kata sync recovery](kata-sync-enable-resets-cursor.md) — preserve and restore card fields around a sync re-enable.
- [Measure heuristics on a corpus](measure-a-heuristic-against-a-corpus.md) — score text matching against real history and an authoritative parser.
- [Avoid unguarded prose counts](no-unguarded-counts-in-prose.md) — phrase a claim so normal growth cannot falsify it unless a gate verifies the count.
- [LaunchAgent scripts use Bash 3.2](launchd-bash32-scripts.md) — check the shell launchd will execute, including a dry run.
