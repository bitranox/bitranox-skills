"""Write-time advisories for a curated memory fact.

Two fact classes poison a store over time, both taken from the do-not-capture
list in Hermes Agent's agent/background_review.py (read 2026-08-15):

1. A bare NEGATIVE claim about a tool hardens into a refusal the agent cites
   against itself long after the thing was fixed.
2. An UNRESOLVED failure written up as a procedure presents untested attempts
   as validated guidance a later session trusts and repeats.

These are ADVISORIES, never refusals: an incident record legitimately describes
a broken thing, and refusing would make it unrecordable. A negative claim is
excused when it is falsifiable - it carries a version or a date, so a later
reader can re-test it.
"""

from __future__ import annotations

import re

__all__ = ["advise", "NEGATIVE_RX", "FALSIFIABLE_RX", "UNRESOLVED_RX"]

NEGATIVE_RX = re.compile(
    r"\b(?:"
    r"do(?:es)?\s+not\s+work|doesn't\s+work|don't\s+work"
    r"|is\s+broken|are\s+broken"
    r"|is\s+not\s+supported|unsupported"
    r"|never\s+works|cannot\s+be\s+used"
    r")\b",
    re.IGNORECASE,
)

# A version (1.2.3, v1.2, 5.201.0) or an ISO date makes the claim re-testable.
FALSIFIABLE_RX = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b|\b\d{4}-\d{2}-\d{2}\b")

UNRESOLVED_RX = re.compile(
    r"\b(?:"
    r"none\s+of\s+(?:them|these|which)\s+worked"
    r"|did\s+not\s+find\s+a\s+working"
    r"|still\s+(?:not|un)\s*(?:solved|resolved|working)"
    r"|next\s+session\s+should\s+(?:retry|try)"
    r"|gave\s+up"
    r")\b",
    re.IGNORECASE,
)

_NEGATIVE_ADVICE = (
    "hook reads as a bare negative claim about a tool; these harden into "
    "refusals cited long after the fix. Add the version or the date that makes "
    "it re-testable, or record the WORKING alternative instead."
)
_UNRESOLVED_ADVICE = (
    "body describes an unresolved failure while the hook reads as a procedure; "
    "that presents untested attempts as validated guidance. Label the dead ends "
    "as unsolved, or do not capture until a working method exists."
)


def advise(hook: str, body: str) -> list[str]:
    """Return zero or more advisory sentences for a drafted fact.

    Args:
        hook: the trigger-first pointer hook.
        body: the fact body (may be empty on a hook-only update).

    Returns:
        A list of complete advisory sentences, without a leading marker.

    Examples:
        >>> advise("When using the foo tool, know it is broken.", "")[0][:4]
        'hook'
        >>> advise("When releasing, run make test.", "")
        []
    """
    out: list[str] = []
    hook = hook or ""
    body = body or ""
    if NEGATIVE_RX.search(hook) and not FALSIFIABLE_RX.search(hook):
        out.append(_NEGATIVE_ADVICE)
    if UNRESOLVED_RX.search(body):
        out.append(_UNRESOLVED_ADVICE)
    return out
