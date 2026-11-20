"""Which file names count as a context checkpoint (a handover).

Two hooks must answer this question identically. `context-watcher.py` decides whether the tool call
behind a PostToolUse wrote the checkpoint, so that write answers the save request instead of
earning a second one; `compact-resume.py` decides which files it may hand back after the
compaction. If the two disagreed, a write the watcher counted as the checkpoint would never be
handed back, or a file the resume hands back would draw a fresh request first. One module owns the
rule so they cannot drift apart.

The names: the canonical `handover.md`, and two improvised forms sessions were measured to use -
`<anything>-handover.md` (a worktree outside any repo, `wt-feature-handover.md`) and
`handover-<topic>.md` (a checkpoint kept in the scratchpad). Each improvised form needs a non-empty
part in front of or behind its fixed text, so `-handover.md` and `handover-.md` do not count, and
`handover.prev.md`, the backup of an earlier checkpoint, matches neither form. Matching is exact
and case-sensitive. Whether an improvised name must also carry the checkpoint heading is the
resume's own concern, not part of this rule.

Pure standard library, ASCII only; imported by name from the hooks directory, which run-python.sh
puts first on sys.path for every hook it launches.
"""

__all__ = ["CHECKPOINT_NAME", "IMPROVISED_PREFIX", "IMPROVISED_SUFFIX", "is_checkpoint_name"]

#: The canonical checkpoint file the meta-context-watcher skill writes.
CHECKPOINT_NAME = "handover.md"
#: An improvised name ending in this, with something in front of it.
IMPROVISED_SUFFIX = "-handover.md"
#: An improvised name starting with this and ending in `.md`, with a topic between the two.
IMPROVISED_PREFIX = "handover-"
_MD = ".md"


def is_checkpoint_name(name: str) -> bool:
    """True for `handover.md`, `<anything>-handover.md` and `handover-<topic>.md`. PURE.

    Args:
        name: A bare file name, never a path: callers pass the last path component.

    Returns:
        Whether a file of that name can hold a checkpoint.

    Examples:
        >>> [is_checkpoint_name(n) for n in ("handover.md", "wt-x-handover.md", "handover-a.md")]
        [True, True, True]
        >>> [is_checkpoint_name(n) for n in ("-handover.md", "handover-.md", "handover.prev.md")]
        [False, False, False]
    """
    if name == CHECKPOINT_NAME:
        return True
    if name.endswith(IMPROVISED_SUFFIX) and len(name) > len(IMPROVISED_SUFFIX):
        return True
    return (name.startswith(IMPROVISED_PREFIX) and name.endswith(_MD)
            and len(name) > len(IMPROVISED_PREFIX) + len(_MD))
