"""Adapter API — the vendor seam.

One module per vendor (claude, opencode, …) implements `Adapter`. The run core
(``agent_harness.core``) is vendor-agnostic and talks to adapters only through
this interface, so a new harness is added by dropping in a module and registering
it (``adapters/__init__.py``) — the core never changes.

The six-member contract (DESIGN §3):

    name                                          # "claude" | "opencode"
    preflight() -> "ok" | "missing" | "noauth"    # CLI on PATH + auth probe
    inject(kind, candidate_dir, tmpdir)
        -> Injection(flags, files, supported)     # supported=False => explicit skip
    invocation(prompt, workspace, model, injection) -> (argv, env)
    parse_log(raw) -> NormalizedRecord            # vendor log -> neutral record
    success(returncode, record) -> bool

Plus one helper the ledger needs and every vendor can answer cheaply:

    cli_version() -> str                          # recorded per row
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Injection:
    """What an adapter must add to a run to load one candidate extender.

    flags     — CLI flags appended to the invocation (e.g. ``--plugin-dir X``).
    files     — paths the adapter materialised for the injection (synthetic
                plugin dirs, temp manifests); informational, cleaned with tmpdir.
    supported — False means this harness genuinely cannot host this kind; the run
                core emits an explicit ``passed=None`` skip row instead of running.
    """

    flags: list = field(default_factory=list)
    files: list = field(default_factory=list)
    supported: bool = True


@dataclass
class NormalizedRecord:
    """Vendor-neutral fold of one run's log (DESIGN §3).

    Adapters map their own log format (Claude stream-json, opencode `--format
    json`, …) onto these fields so the eval/ledger layer stays vendor-agnostic.
    ``plugins`` is optional context for the loadability smoke; not every vendor
    populates it.
    """

    result: str = ""
    tool_names: list = field(default_factory=list)
    plugin_errors: list = field(default_factory=list)
    plugins: list = field(default_factory=list)
    skill_used: bool = False
    exit_code: Optional[int] = None
    cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    num_turns: Optional[int] = None
    error: Optional[str] = None


class Adapter(abc.ABC):
    """Base class for a vendor adapter. Implement the six members below."""

    #: vendor id, e.g. "claude" — used in the ledger, resume key, and report cells.
    name: str = ""

    @abc.abstractmethod
    def preflight(self) -> str:
        """Return "ok" | "missing" | "noauth" — cheap readiness probe."""

    @abc.abstractmethod
    def inject(self, kind: str, candidate_dir: str, tmpdir: str) -> Injection:
        """Build the injection that loads exactly this candidate for `kind`."""

    @abc.abstractmethod
    def invocation(self, prompt, workspace, model, injection: Injection):
        """Return ``(argv, env)`` — list-form argv (never a shell string) and the
        (scrubbed) environment for the child process."""

    @abc.abstractmethod
    def parse_log(self, raw: str) -> NormalizedRecord:
        """Fold the vendor's raw run log into a NormalizedRecord."""

    @abc.abstractmethod
    def success(self, returncode: int, record: NormalizedRecord) -> bool:
        """Vendor-specific notion of a successful CLI run (exit-code semantics
        differ per vendor). Distinct from the grading pass rule."""

    def cli_version(self) -> str:  # pragma: no cover - overridden by real adapters
        """Version string recorded per ledger row. Default: unknown."""
        return "unknown"
