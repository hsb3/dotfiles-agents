"""Adapter registry — name → adapter, plus dispatch.

Adding a harness (Wave 2: opencode) = write the module and add one line to
``ADAPTERS``; the run core dispatches through :func:`get_adapter` and never
imports a concrete adapter directly.
"""

from __future__ import annotations

from .base import Adapter, Injection, NormalizedRecord
from .claude import ClaudeAdapter
from .opencode import OpencodeAdapter


class UnknownHarness(ValueError):
    """Raised for a harness name that is not registered."""


#: Registered adapters, keyed by ``name``.
ADAPTERS = {
    ClaudeAdapter.name: ClaudeAdapter,
    OpencodeAdapter.name: OpencodeAdapter,
}


def list_adapters():
    """Sorted list of valid harness names."""
    return sorted(ADAPTERS)


def get_adapter(name: str, **kwargs) -> Adapter:
    """Instantiate the adapter for `name`.

    kwargs (e.g. allow_bash) flow to the adapter constructor. Unknown name ->
    :class:`UnknownHarness` listing the valid names (CLI maps this to exit 3).
    """
    try:
        cls = ADAPTERS[name]
    except KeyError:
        raise UnknownHarness(
            f"unknown harness {name!r}; valid harnesses: {', '.join(list_adapters())}"
        ) from None
    return cls(**kwargs)


__all__ = [
    "Adapter",
    "Injection",
    "NormalizedRecord",
    "ClaudeAdapter",
    "OpencodeAdapter",
    "UnknownHarness",
    "ADAPTERS",
    "list_adapters",
    "get_adapter",
]
