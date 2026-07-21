"""agent_harness — reusable extender-evaluation harness.

Drive Claude Code (and, from Wave 2, opencode) headlessly against a fixture
workspace with a candidate extender injected, grade the outcome, append one
ledger row. Self-contained uv project; zero imports from the surrounding repo
(extraction = move this directory). See DESIGN.md and README.md.
"""

__version__ = "0.1.0"
