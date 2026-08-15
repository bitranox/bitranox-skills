"""Write-time advisories for a curated memory fact.

Two fact classes poison a store over time, both taken from the do-not-capture
list in Hermes Agent's agent/background_review.py (read 2026-08-15):

1. A bare NEGATIVE claim about a tool hardens into a refusal the agent cites
   against itself long after the thing was fixed.
2. An UNRESOLVED failure written up as a procedure presents untested attempts
   as validated guidance a later session trusts and repeats.

These are ADVISORIES, never refusals: an incident record legitimately describes
a broken thing, and refusing would make it unrecordable. A negative claim is
excused when it is falsifiable - it carries a version or a date - but only when
that version or date scopes the claim itself. The falsifiability check is
clause-scoped: it looks at the comma/semicolon-delimited clause containing the
negative claim, plus the clause immediately after it (to catch the "is broken;
fixed in 1.3.0" idiom), never at an unrelated trigger clause or a distant
sentence that merely happens to mention a version or date elsewhere in the hook.
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

_CLAUSE_RX = re.compile(r"[,;]")


def _falsifiability_scope(hook: str, negative_match: re.Match[str]) -> str:
    """Return the slice of hook a falsifiability marker must fall in to excuse the claim.

    A version or date only excuses a negative claim when it scopes that claim,
    not when it merely appears somewhere else in the hook (a leading trigger
    clause, or an unrelated later sentence). The scope is the clause containing
    the negative claim plus the clause immediately after it, split on commas and
    semicolons - wide enough to cover "X is broken; fixed in 1.3.0", narrow
    enough to exclude "released around 2026-08-01, know X is broken".

    Args:
        hook: the full hook string that negative_match was found in.
        negative_match: the NEGATIVE_RX match locating the claim.

    Returns:
        The substring FALSIFIABLE_RX should be searched against.
    """
    clauses = _CLAUSE_RX.split(hook)
    offset = 0
    for index, clause in enumerate(clauses):
        clause_end = offset + len(clause)
        if offset <= negative_match.start() < clause_end:
            following = clauses[index + 1] if index + 1 < len(clauses) else ""
            return clause + following
        offset = clause_end + 1  # +1 skips the consumed comma/semicolon
    return hook


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
    negative_match = NEGATIVE_RX.search(hook)
    if negative_match is not None:
        scope = _falsifiability_scope(hook, negative_match)
        if not FALSIFIABLE_RX.search(scope):
            out.append(_NEGATIVE_ADVICE)
    if UNRESOLVED_RX.search(body):
        out.append(_UNRESOLVED_ADVICE)
    return out
