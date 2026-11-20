#!/usr/bin/env python3
"""Stop + PostToolUse hook: act at the context limit before the harness compacts the session.

Shortly before the harness auto-compacts, it asks the session to save a checkpoint (OPEN-WORK.md
plus handover.md) and keep working; compact-resume.py hands the checkpoint back after the
compaction. The harness compacts about 33k tokens below CLAUDE_CODE_AUTO_COMPACT_WINDOW (measured,
see _HARNESS_RESERVE), so that variable must hold the context limit, and the request says so when
it does not. The request goes out on PostToolUse as well as on Stop, because a long autonomous turn
can pass both the save point and the compaction without stopping once - probe-verified on 2.1.310,
where five compactions ran inside one turn and the turn carried on after each. A handover the user
asks for is the meta-context-watcher skill's business, not this hook's; a stored `context_mode`
setting is not read, so every install behaves this way.

A long session gets worse before it gets full, and nothing says so. Chroma's 2025 study measured
accuracy falling from roughly 300-400k tokens on a 1M window and from about 50k on a 200k one, with
the lost-in-the-middle effect costing 30% or more on retrieval. Left alone, Claude Code's own
auto-compact does not act until close to the full window (the model-config docs put its default
auto-compact window on a 1M model at about 967k); CLAUDE_CODE_AUTO_COMPACT_WINDOW moves it. So there is a long stretch where the
session is measurably worse than it reads, and when the harness finally does act it COMPACTS, which
keeps a summary and drops the working detail - unless that detail was saved first.

This repo already handles compaction, but only in retrospect: `PreCompact` salvages learning signals
and `PostCompact` nudges `meta-dream-nap` to tidy MEMORY. Neither watches context approaching the
wall, and neither writes down TASK STATE - the nap deliberately prunes that as noise.

HOW THE SIZE IS MEASURED, which is the part that had to be discovered rather than assumed. NO hook
event carries a token count: the only token fields in the whole hook contract are `max_output_tokens`
as a StopFailure error type and a subagent's `totalTokens`, neither of which is session context. But
the transcript records real per-request usage, so the last record carrying `message.usage` gives

    input_tokens + cache_creation_input_tokens + cache_read_input_tokens

which is the context that request actually carried - a measurement, not a bytes/4 proxy. It also
self-corrects after a compaction, because the next request's usage drops on its own. A record that
carried no request is skipped: an API error the harness logs as a `<synthetic>` assistant record
with every usage field 0 would otherwise read as a compaction.

THE WINDOW comes from the model FAMILY, which `message.model` carries on every assistant record.
That id never includes Claude Code's `[1m]` suffix, and it does not need to: measured across 1485
local transcripts, every non-haiku family has actually carried far more than a 200K window can hold
(opus-5 999,946; opus-4-8 999,911; fable-5 997,450; sonnet-5 665,313), while haiku peaked at
119,393. The peaks stopping just under 1,000,000 is the window boundary showing itself in the data.
So the family settles it: opus, fable, sonnet and mythos are 1M; haiku 4.5 is 200K. Haiku 5 is 1M:
its `claude -p` modelUsage reports contextWindow 1000000, and its transcripts carry requests above
200K.

A family the TABLE has not met - a gateway model like glm-5.3 behind ANTHROPIC_BASE_URL - must not
land on the 200K default, because that errs LARGE for a model actually running 1M: the request fires
far too early and then the misconfigured check sees 200K < 1M so nothing catches the stale default either -
the silent-inert failure this hook exists to prevent. For exactly that case Claude Code defines
`CLAUDE_CODE_MAX_CONTEXT_TOKENS` (model-config docs, "correct the window for a gateway or custom
model id"): the launcher declares the real window because the API advertises none. Probe-verified
on 2.1.269: the variable reaches a Stop hook's subprocess environment, and the bitranox glm
launcher (claude_on_inco/claude-glm.sh) sets it to 1,000,000. It is read ONLY for a family the
table does not know - for a known family the table wins, so a stale globally-exported value cannot
silently override a measured family window.

THE ASSUMPTION IN THAT TABLE, stated because its failure is silent. Those transcripts come from ONE
machine and one account tier, so the table asserts that current opus, fable, sonnet and mythos run
1M for EVERYONE. If some tier or plan runs a 200K opus, that session gets a 400K threshold it can
never reach - it would compact near 166K - and the misconfigured check below cannot catch it either,
because 166K is far under the 1M being assumed. The symptom is the hook simply never speaking, which
is the symptom nobody reports.

The remedy is `context_window`: setting it to a real token count overrides the table entirely. A
deliberate trade - the alternative was to assume 200K until each session proved otherwise, which is
correct for every tier but asks early on every genuine 1M session.

For a model OUTSIDE the table entirely (a gateway id like glm-5.3) the fallback is not a guess but
the launcher's own declaration: `CLAUDE_CODE_MAX_CONTEXT_TOKENS` names the window precisely because
the API behind a custom model id advertises none (model-config docs). That leg answers only when
the family is unknown - see the window paragraph above for why.

When the measured context exceeds the window in use, that IS reported rather than ignored - a
threshold nothing can cross is indistinguishable from a watcher that works. It catches an
over-large explicit knob; it cannot catch an over-large assumption, per the paragraph above.

THE LIMIT is min(percentage of the window, absolute cap), because the two research findings
disagree on a big window and both are worth honouring. It is the value CLAUDE_CODE_AUTO_COMPACT_WINDOW
should hold. The percentage leg keeps the compaction a cushion below the window; the absolute leg
catches the case the percentage misses entirely - a 1M session sailing past the measured rot onset
while only 40% full. The save point sits far enough below the resulting compaction point that the
checkpoint can be written before the compaction arrives (_SAVE_MARGIN_MIN).

PROVENANCE OF THE 400k CAP, stated plainly because it decides when a session compacts: it is one
published finding (Chroma's 2025 context-rot study, which measured accuracy falling from roughly
300-400k on a 1M window) read second-hand from a summary, not something measured here. It is wrong
in the safe direction - too low means an earlier checkpoint and compaction, never a session working
on past the rot onset - and the knob exists to move it.

A REPEAT request is spaced by 10% of the window. A reading back below the save point means the
harness compacted, so the request re-arms and the next crossing asks for a fresh checkpoint; above
it, a repeat refreshes the checkpoint only when the harness is not compacting. A request earned by
the checkpoint's own write is answered by it and stays unsaid. A Stop yields entirely
when a post-compaction nap is already owed: the Stop gate refuses to stop on that obligation and
stacking a second block would make the two fight over the same turn. Fail-open on every error path -
a broken watcher must never wedge a turn.

Pure standard library, ASCII only; launched via run-python.sh so it works on Windows too.
"""

import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Callable, Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Literal, TypeIs, cast

import checkpoint_names
import self_improve_signals as sig

# One decoded JSON object: a hook event, a transcript record, its `message` or `usage` block. The
# values are whatever the harness wrote, so each reader narrows the field it uses.
type _JsonRecord = dict[str, object]
# A path argument as os.path.getsize and open take it, a file descriptor included.
type _PathArg = str | bytes | int | os.PathLike[str] | os.PathLike[bytes]
# What compact_verdict decides for one reading.
type Verdict = Literal["quiet", "save", "misconfigured"]

# int() refuses what it cannot convert with TypeError or ValueError, and every caller here catches
# both: a knob, an environment value or a usage field is whatever was stored, so the conversion IS
# the check. Typed as taking `object` because that is what those callers hold.
_coerce_int = cast("Callable[[object], int]", int)


def _is_record(value: object) -> TypeIs[_JsonRecord]:
    """True for a decoded JSON object. Its keys are str for anything json.loads produced."""
    return isinstance(value, dict)


def _is_path_arg(value: object) -> TypeIs[_PathArg]:
    """True for anything os.path.getsize and open accept as a path, a file descriptor included."""
    return isinstance(value, (str, bytes, int, os.PathLike))


def _is_environment(value: object) -> TypeIs[Mapping[str, object]]:
    """True for an environment mapping: os.environ itself (a Mapping, not a dict) or a plain dict."""
    return isinstance(value, Mapping)


def _is_str_path(value: object) -> TypeIs[str | os.PathLike[str]]:
    """True for a str or path object, the shapes a project directory arrives in."""
    return isinstance(value, (str, os.PathLike))

# Enough tail to reach a recent assistant record even when the last turn wrote a large tool result,
# while staying a single bounded read on a multi-megabyte transcript.
_TAIL_BYTES = 2 * 1024 * 1024

_DEFAULT_WINDOW = 200_000
_RE_ASK_FRACTION = 10           # re-ask each time context grows another 1/10th of the window

# Context window per model FAMILY, matched on the id `message.model` carries. Measured over 1485
# local transcripts rather than inferred: every non-haiku family has carried far more than a 200K
# window could hold, and the observed peaks stop just under 1,000,000. Claude Code's `[1m]` suffix
# appears in `~/.claude.json` but never in `message.model`, and it turns out to be redundant - the
# current families run 1M regardless. Source for the roster: the bundled `claude-api` skill's model
# table (cached 2026-06-24).
# Haiku splits by generation: haiku 5 reports contextWindow 1000000 in a `claude -p` modelUsage
# record and has carried requests above 200K, while haiku 4.5 never has. The first matching prefix
# wins, so the haiku-5 row must sit ahead of the generic haiku one.
_FAMILY_WINDOWS = (("claude-fable", 1_000_000), ("claude-mythos", 1_000_000),
                   ("claude-opus", 1_000_000), ("claude-sonnet", 1_000_000),
                   ("claude-haiku-5", 1_000_000), ("claude-haiku", 200_000),
                   ("oss-128k", 128_000))

# What the launcher declared for a model the family table has not met. Read only in that case -
# see the module docstring for why a known family ignores it.
_ENV_MAX_CONTEXT = "CLAUDE_CODE_MAX_CONTEXT_TOKENS"

# The harness's own auto-compact window. Probe-verified on 2.1.310: an `env` block in settings.json
# sets it for the session AND reaches a hook's environment, so the hook can check it is aligned.
_ENV_COMPACT_WINDOW = "CLAUDE_CODE_AUTO_COMPACT_WINDOW"
# How far BELOW that window the harness actually compacts. Measured with scripted probes on 2.1.310
# at windows of 100k and 200k: compaction fired at estimated contexts of 69-99k and 166-178k, while
# requests of 84k and 171k still went through - a fixed reserve of roughly 33k, not a percentage.
_HARNESS_RESERVE = 33_000
# The least room left between the checkpoint request and that compaction point. One tool result
# added up to 42k in the same probes, so a smaller gap can let the compaction overtake the save.
_SAVE_MARGIN_MIN = 40_000


def window_for_model(model_id: object, environ: Mapping[str, object] | None = None) -> int:
    """The context window this model family runs. PURE.

    A family the table knows answers from the table alone - the environment is not consulted for
    it, so a globally-exported `CLAUDE_CODE_MAX_CONTEXT_TOKENS` left over from another model can
    never override a measured family window. An UNKNOWN family (a gateway model id the table has
    not met) reads that variable when the caller passes an environment mapping, because the
    launcher set it precisely to declare this model's window; only when even that is absent does it
    fall back to 200K, which errs SMALL on purpose: too small only asks for a checkpoint early, while
    too large sets a threshold the session can never reach and the hook goes silently inert - the
    failure this whole check exists to prevent.
    """
    mid = str(model_id or "").lower()
    if mid.endswith("[1m]"):                  # `~/.claude.json` spells it this way; harmless here
        mid = mid[:-4]
    for prefix, window in _FAMILY_WINDOWS:
        if mid.startswith(prefix):
            return window
    if environ is not None:
        declared = _env_max_context(environ)
        if declared:
            return declared
    return _DEFAULT_WINDOW


def _env_max_context(environ: object) -> int:
    """The window a launcher declared for a custom model, or 0 when it declared none. PURE.

    `None` (no environment passed at all) counts as no declaration, not an error. Any mapping is
    read, os.environ included: decide() passes that one, and a dict-only check never saw it.
    """
    if not _is_environment(environ):
        return 0
    try:
        value = _coerce_int(environ.get(_ENV_MAX_CONTEXT) or 0)
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


# The harness logs an API error reply (a 429, an overload) as an assistant record of its own, with
# model "<synthetic>", `isApiErrorMessage` set and every usage field 0; all 213 such records in the
# local transcripts carried a 0 total. Read as a measurement it says the session holds 0 tokens,
# which is exactly what a compaction looks like, so the request re-armed and the checkpoint's own
# Write was asked again and stamped after the file, and the resume reported no checkpoint (one
# measured miss). A real request always carries its system prompt, so a 0 total measures nothing
# either; two such records with a real model id turned up in a 600-transcript sample.
_SYNTHETIC_MODEL = "<synthetic>"
_CONTEXT_LEGS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


class _Unreadable(ValueError):
    """A usage block whose fields are not numbers; each reader keeps its own policy for it."""


def _reading(record: object) -> tuple[int, object] | None:
    """(context tokens, model id) a transcript record measured, or None when it measured none. PURE.

    None for anything but a real request's usage: no usage block, an API-error or `<synthetic>`
    record, or a 0 total. Raises _Unreadable for a usage block whose fields are not numbers.
    """
    if not _is_record(record) or record.get("isApiErrorMessage"):
        return None
    message = record.get("message")
    if not _is_record(message) or message.get("model") == _SYNTHETIC_MODEL:
        return None                           # a string or list message carries no usage
    usage = message.get("usage")
    if not _is_record(usage):
        return None
    try:
        total = sum(_coerce_int(usage.get(leg) or 0) for leg in _CONTEXT_LEGS)
    except (TypeError, ValueError) as exc:
        raise _Unreadable(str(exc)) from None
    return (total, message.get("model")) if total > 0 else None


def _tail_records(transcript_path: object, tail_bytes: int) -> list[object] | None:
    """The JSON records in the transcript's last `tail_bytes`, oldest first, or None. IMPURE.

    A line that does not parse is skipped: the seek can land mid-line, and that partial line is
    dropped before the read anyway. A path of a type the file calls refuse reads as unreadable.
    """
    if not _is_path_arg(transcript_path):
        return None
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as handle:
            if size > tail_bytes:
                handle.seek(size - tail_bytes)
                handle.readline()             # drop the partial line the seek landed in
            data = handle.read()
    except (OSError, TypeError, ValueError):
        return None
    records: list[object] = []
    for raw in data.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line.decode("utf-8", "replace")))
        except ValueError:
            continue
    return records


def read_session(transcript_path: object,
                 tail_bytes: int = _TAIL_BYTES) -> tuple[int | None, object]:
    """(current_tokens, family_model) from ONE tail read. IMPURE.

    Both come from the same records, so reading them together avoids a second pass over a
    multi-megabyte transcript on every turn. A record that measured nothing (see _reading) moves
    neither, so an API error neither reads as 0 tokens nor names the window by `<synthetic>`.
    """
    records = _tail_records(transcript_path, tail_bytes)
    if records is None:
        return None, None
    current: int | None = None
    model: object = None
    for record in records:
        try:
            reading = _reading(record)
        except _Unreadable:
            continue
        if reading is None:
            continue
        current = reading[0]                  # the LAST one wins; the loop runs forward
        if reading[1]:
            model = reading[1]
    return current, model


def context_tokens(transcript_path: object, tail_bytes: int = _TAIL_BYTES) -> int | None:
    """Context carried by the most recent request, or None when it cannot be read. IMPURE (reads).

    The three fields sum to what the request actually sent: fresh input, whatever was written to
    cache this turn, and whatever was read from cache. Omitting the cache legs would report a
    handful of tokens on a session hundreds of thousands deep, because almost all of a long
    session's context arrives as a cache read.

    Scans the tail BACKWARDS and stops at the first record that measured a request, so the answer
    is the latest one; an unreadable usage block there answers None.
    """
    records = _tail_records(transcript_path, tail_bytes)
    for record in reversed(records or ()):
        try:
            reading = _reading(record)
        except _Unreadable:
            return None
        if reading is not None:
            return reading[0]
    return None


def threshold(window: object, pct: object, cap: object) -> int | None:
    """The context limit: the token count the harness should compact at. PURE.

    Whichever leg bites first. The result is floored at 1 so a zero or negative knob cannot make a
    reading of 0 tokens count as crossed. The floor does NOT stop an early request: a knob at 0 or 1
    still asks on the first measured turn, because that is what such a setting asks for. Bounding
    the knobs to sensible values is the settings CLI's job (it accepts 1..100 and >= 1), and a
    higher clamp here would silently override a value that tool accepted.
    """
    try:
        by_pct = _coerce_int(window) * _coerce_int(pct) // 100
        return max(1, min(by_pct, _coerce_int(cap)))
    except (TypeError, ValueError):
        return None


def harness_window(environ: object) -> int:
    """The auto-compact window the harness was given, or 0 when none is visible. PURE."""
    if not _is_environment(environ):
        return 0
    try:
        value = _coerce_int(environ.get(_ENV_COMPACT_WINDOW) or 0)
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


def compaction_point(limit: int, harness: int) -> int:
    """Where the harness will compact, in tokens. PURE.

    A harness window SMALLER than the limit compacts earlier, so it wins. An unset or larger one
    is a misalignment the save request reports; the limit is then the value it should be set to,
    and the save is timed against it.
    """
    window = harness if 0 < harness < limit else limit
    return max(1, int(window) - _HARNESS_RESERVE)


def save_point(compact_at: int) -> int:
    """The context at which the checkpoint is requested: room for the save before the compaction."""
    return max(1, int(compact_at) - max(_SAVE_MARGIN_MIN, int(compact_at) // 10))


def compact_verdict(tokens: int | None, window: object, pct: object, cap: object,
                    harness: int) -> tuple[Verdict, dict[str, int]]:
    """('quiet'|'save'|'misconfigured', detail dict). PURE - all the arithmetic, no IO.

    `misconfigured` is a real answer, not an error: measuring more context than the window is
    supposed to hold means `context_window` is wrong (a 1M model left on the 200k default), and
    saying so is the difference between a watcher that reports and one that silently never fires.
    """
    limit = threshold(window, pct, cap)
    if tokens is None or limit is None:
        return "quiet", {}
    compact_at = compaction_point(limit, harness)
    save_at = save_point(compact_at)
    detail = {"tokens": tokens, "window": _coerce_int(window), "limit": limit,
              "pct": _coerce_int(pct), "cap": _coerce_int(cap), "harness": harness,
              "compact_at": compact_at, "save_at": save_at}
    if tokens > _coerce_int(window):
        return "misconfigured", detail
    if tokens >= save_at:
        return "save", detail
    return "quiet", detail


def _asked_flag(session: object) -> pathlib.Path:
    """Session-keyed state, so one left by an older session can never suppress this one."""
    return sig.touched_file(session).with_suffix(".handover-asked")


def _misconfigured_flag(session: object) -> pathlib.Path:
    """The misconfigured notice's OWN once-per-session latch.

    Kept apart from `_asked_flag` because the two answer different questions: reading "has this
    session been told anything" off the request's flag would let an earlier checkpoint request
    silence the notice for the rest of the session - exactly when a reading past the window proves
    the window wrong.
    """
    return sig.touched_file(session).with_suffix(".handover-misconfigured")


def already_reported(session: object) -> bool:
    """True once this session has seen the misconfigured notice - it says itself once."""
    try:
        return _misconfigured_flag(session).is_file()
    except OSError:
        return False


def mark_reported(session: object) -> None:
    try:
        flag = _misconfigured_flag(session)
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("1\n", encoding="utf-8")
    except OSError:
        pass                                  # an unwritable latch means it may say it twice


def asked_at(session: object) -> int:
    """Context level of the last ask, or 0 when this session has not been asked. IMPURE (reads)."""
    try:
        return int(_asked_flag(session).read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def mark_asked(session: object, tokens: int) -> None:
    try:
        flag = _asked_flag(session)
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text(str(int(tokens)) + "\n", encoding="utf-8")
    except (OSError, TypeError, ValueError):
        pass                                  # an unwritable flag means it may ask twice, not wedge


def due(tokens: int, limit: int, window: int, last_asked: int) -> bool:
    """True when this reading earns an ask. PURE.

    The first ask is the threshold. After that, a reading still above it asks again only once
    context has grown another 1/10th of the window - by which point a fresh checkpoint holds
    genuinely more than the last one rather than the same state written twice.
    """
    if tokens < limit:
        return False
    if not last_asked:
        return True
    return tokens >= last_asked + max(1, int(window) // _RE_ASK_FRACTION)


#: git reads these before cwd, and a hook launched under a linked-worktree push inherits GIT_DIR: an
#: inherited one would answer the tracking question below about some other repository.
_GIT_SCOPE_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                   "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE",
                   "GIT_PREFIX", "GIT_QUARANTINE_PATH")


def _git(proj: object, *args: str) -> tuple[int, str]:
    """(returncode, stdout) of a read-only git call in `proj`. Raises OSError/SubprocessError."""
    env = {k: v for k, v in os.environ.items() if k not in _GIT_SCOPE_VARS}
    env["LC_ALL"] = "C"
    done = subprocess.run(["git", *args], cwd=str(proj), env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=3)
    return done.returncode, done.stdout


class HandoverTracking(StrEnum):
    """What git holds of the handover.md a session would overwrite."""

    TRACKED = "tracked"          # git holds its history
    UNTRACKED = "untracked"      # it exists but git has no copy: gitignored, never added, no repo
    ABSENT = "absent"            # nothing to overwrite
    UNKNOWN = "unknown"          # git could not be asked


def handover_tracking(proj: object) -> HandoverTracking:
    """Whether the handover.md a session would overwrite has earlier versions in git. IMPURE.

    It is a per-repo fact - some repos gitignore the file, others commit it - so the save request
    tests it instead of asserting either. Never raises.
    """
    try:
        rc, top = _git(proj, "rev-parse", "--show-toplevel")
        if rc != 0:
            if not _is_str_path(proj):
                raise TypeError(proj)         # what pathlib.Path raises for it: the answer is unknown
            return _present_or_absent(pathlib.Path(proj))
        root = top.strip()
        rc, _out = _git(root, "ls-files", "--error-unmatch", "--", "handover.md")
        if rc == 0:
            return HandoverTracking.TRACKED
        return _present_or_absent(pathlib.Path(root))
    except Exception:                         # noqa: BLE001 - a missing git must not wedge a turn
        return HandoverTracking.UNKNOWN


def _present_or_absent(root: pathlib.Path) -> HandoverTracking:
    return HandoverTracking.UNTRACKED if (root / "handover.md").exists() else HandoverTracking.ABSENT


# Keyed by every member, so a tracking value outside the vocabulary is a ValueError in _save
# rather than a `.get` that silently drops the warning; ABSENT has nothing to overwrite.
_OVERWRITE_WARNING = MappingProxyType({
    HandoverTracking.ABSENT: None,
    HandoverTracking.TRACKED: (
        "The handover is written by OVERWRITING the outgoing one. `handover.md` is tracked here, "
        "so its earlier versions are in git history - but nobody diffs a handover against its "
        "predecessor looking for what went missing, so carry anything still open into "
        "`OPEN-WORK.md` before you overwrite it, not after."),
    HandoverTracking.UNTRACKED: (
        "The handover is written by OVERWRITING the outgoing one, and git holds no copy of "
        "`handover.md` here, so anything still open that you do not first carry into "
        "`OPEN-WORK.md` is gone with no earlier version to recover it from. Reconcile before you "
        "overwrite, not after."),
    HandoverTracking.UNKNOWN: (
        "The handover is written by OVERWRITING the outgoing one, and whether git keeps its "
        "earlier versions could not be checked here (`git ls-files --error-unmatch handover.md` "
        "answers it). If it does not, anything still open that you do not first carry into "
        "`OPEN-WORK.md` is gone for good. Reconcile before you overwrite, not after."),
})


# A session in plan mode may write only its plan file, so the request says where the checkpoint goes
# there. Measured: three plan-mode sessions put it into the plan file on their own and were then
# told no checkpoint was saved; the harness attaches the plan file after a compaction itself, and
# compact-resume points at it.
_PLAN_MODE_NOTE = (
    "This session is in plan mode, where the plan file is the only file you may write. Put the "
    "checkpoint into the plan file as a section of its own (`## Checkpoint`, with its "
    "`## Lessons for the next nap`) instead of `handover.md`, and leave the plan itself intact; the "
    "harness attaches the plan file after the compaction, and the resume points at it. Carry the "
    "unfinished items into `OPEN-WORK.md` once plan mode ends.")


def _save(detail: Mapping[str, int | str],
          tracking: HandoverTracking | str = HandoverTracking.UNKNOWN, *,
          plan_mode: bool = False) -> str:
    fill = {k: format(v, ",") if isinstance(v, int) and k != "pct" else v for k, v in detail.items()}
    text = (
        "This session is carrying %(tokens)s tokens of context. The harness auto-compacts at about "
        "%(compact_at)s, and a compaction keeps only a summary of the working detail. Save a "
        "checkpoint NOW, then keep working:\n\n"
        "1. Invoke bitranox:meta-context-watcher and follow its checkpoint procedure: carry"
        " every unfinished item and every unmet user request into `OPEN-WORK.md`, and "
        "write `handover.md` - in flight, decisions, the exact next action, and `## Lessons for the "
        "next nap`. Replace the whole file with the Write tool, never append to it: a first line "
        "still reading `# STALE` from an earlier hand-back keeps the new checkpoint from being "
        "handed back, and a file written through Bash is never handed back as yours: the resume "
        "only lists it. Read the clock with `date` before you stamp it, and correct a stamp "
        "afterwards with the Edit tool, not a shell edit. "
        "Commit nothing just for this.\n"
        "2. Then CONTINUE the task you were on. Do not stop, do not ask the user, and do not tell "
        "them to /clear: the compaction follows automatically, and the checkpoint is handed back "
        "to you right after it."
    ) % fill
    harness, limit = detail.get("harness"), detail["limit"]
    if not harness or (isinstance(harness, int) and isinstance(limit, int) and harness > limit):
        text += (
            "\n\nThe harness is not set to compact at the %(limit)s limit (%(env)s is %(now)s), so "
            "nothing will compact until its own default, far later, and this checkpoint goes stale "
            "meanwhile. Tell the user once and offer to set %(env)s=%(raw)d in the env block of "
            "~/.claude/settings.json through the update-config skill; it takes effect in the next "
            "session." % {"limit": fill["limit"], "env": _ENV_COMPACT_WINDOW, "raw": detail["limit"],
                          "now": fill["harness"] if detail.get("harness") else "unset"})
    if plan_mode:
        text += "\n\n" + _PLAN_MODE_NOTE
    warning = _OVERWRITE_WARNING[HandoverTracking(tracking)]
    return text + "\n\n" + warning if warning else text


def _misconfigured(detail: Mapping[str, int | str]) -> str:
    return (
        "The context watcher measured %(tokens)s tokens, which is MORE than the %(window)s window "
        "it was measuring against (%(source)s) - so the threshold can never be reached. This is "
        "reported rather than ignored because a threshold nothing can cross looks exactly like a "
        "watcher that works.\n\n"
        "The window is normally derived from the model this project has used, or - for a model no "
        "family table knows - declared by the launcher via CLAUDE_CODE_MAX_CONTEXT_TOKENS. If both "
        "failed, set `context_window` to the real figure via bitranox:meta-memory-settings. Until "
        "then this check is inert."
    ) % {k: format(v, ",") if isinstance(v, int) and k != "pct" else v for k, v in detail.items()}


def resolve_window(cfg: Mapping[str, object], model: object = None,
                   environ: Mapping[str, object] | None = None) -> tuple[int, str]:
    """(window, how it was established). PURE.

    An explicit `context_window` wins - the escape hatch for a model the table has not met.
    Otherwise the family decides; an unknown family takes what the launcher declared in
    `CLAUDE_CODE_MAX_CONTEXT_TOKENS` ("declared"), and failing that the 200K default. The label
    records which leg answered, which the misconfigured notice quotes.
    """
    explicit = cfg.get("context_window") or 0
    try:
        if _coerce_int(explicit) > 0:
            return _coerce_int(explicit), "configured"
    except (TypeError, ValueError):
        pass
    if model:
        if _family_known(model):
            return window_for_model(model, environ), "detected"
        declared = _env_max_context(environ)
        if declared:
            return declared, "declared"
    return _DEFAULT_WINDOW, "assumed"


def _family_known(model_id: object) -> bool:
    """True when the family table has a window for this model id. PURE."""
    mid = str(model_id or "").lower()
    if mid.endswith("[1m]"):
        mid = mid[:-4]
    return any(mid.startswith(prefix) for prefix, _window in _FAMILY_WINDOWS)


def is_subagent_event(event: Mapping[str, object]) -> bool:
    """True when a subagent fired this event: it names an `agent_id`, or its transcript is one. PURE.

    The second form covers an event whose `transcript_path` already points at a subagent's own
    `agent-<id>.jsonl`, the shape sha-literal-nudge also accepts.
    """
    if event.get("agent_id"):
        return True
    return pathlib.Path(str(event.get("transcript_path") or "")).name.startswith("agent-")


def decide(event: Mapping[str, object], cfg: Mapping[str, object]) -> str | None:
    """The text for this Stop or PostToolUse event, or None to stay quiet. IMPURE (reads).

    On Stop the caller turns it into a block reason, on PostToolUse into additionalContext. Both
    events carry the same checkpoint request: a long autonomous turn can pass both the save point
    and the compaction without ever stopping, so a Stop-only request would arrive after the
    compaction it was meant to precede. `cfg` is read for `nudges`, `context_window` and the two
    `context_handover_*` knobs only; any other key, a stored `context_mode` included, changes
    nothing.

    `stop_hook_active` means a Stop hook already kept this turn going. Blocking that continuation
    again would stack a second interruption on one turn and spend the consecutive-block budget, so
    it stays quiet and marks nothing; the next ordinary Stop asks instead.

    A subagent's tool call fires this hook too, with the MAIN session's `session_id` and
    `transcript_path` plus its own `agent_id`. Answering it would hand the main session's request
    to the subagent, and the session's asked flag would then hold the main session silent until
    another tenth of the window: measured in one session, three compaction cycles lost their
    request this way while subagents ran past the save point. So a subagent's event is quiet and
    marks nothing, and the main session's next tool call or Stop asks.
    """
    on_stop = (event.get("hook_event_name") or "Stop") == "Stop"
    if on_stop and event.get("stop_hook_active"):
        return None
    if is_subagent_event(event):
        return None
    session = str(event.get("session_id") or "")
    transcript = event.get("transcript_path") or ""
    if not session or not transcript:
        return None
    if not cfg.get("nudges", True):
        return None
    # A post-compaction nap is already an obligation the Stop gate refuses to stop on. Two blocks
    # on one turn would fight over it and burn the consecutive-block budget, so a Stop yields. A
    # mid-turn note blocks nothing, so it has nothing to fight over and does not yield. A nap the
    # user declined blocks nothing either.
    proj = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if on_stop:
        try:
            if _is_str_path(proj) and sig.nap_owed_blocks(proj, session):
                return None
        except Exception:                     # noqa: BLE001 - a missing helper must not wedge a turn
            pass
    tokens, model = read_session(transcript)
    window, source = resolve_window(cfg, model, os.environ)
    pct, cap = cfg.get("context_handover_pct", 70), cfg.get("context_handover_cap", 400000)
    plan_mode: bool = event.get("permission_mode") == "plan"
    return _decide_compact(session, proj, tokens, window, source, pct, cap, plan_mode=plan_mode,
                           wrote=checkpoint_write(event, plan_mode=plan_mode))


_WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit"})


def checkpoint_write(event: Mapping[str, object], *, plan_mode: bool = False) -> str | None:
    """The checkpoint file the tool call behind this PostToolUse wrote, or None. PURE.

    A Write, Edit or MultiEdit of a checkpoint-named file (the rule compact-resume hands back by,
    from `checkpoint_names`); in plan mode any of them, because the
    plan file is the only file such a session may write and the request sends the checkpoint there.
    PostToolUse fires only for a call that succeeded.
    """
    if event.get("hook_event_name") != "PostToolUse" or event.get("tool_name") not in _WRITE_TOOLS:
        return None
    tool_input = event.get("tool_input")
    path = tool_input.get("file_path") if _is_record(tool_input) else None
    if not isinstance(path, str) or not path:
        return None
    if plan_mode or checkpoint_names.is_checkpoint_name(pathlib.PurePath(path).name):
        return path
    return None


def _stamp_before(path: str) -> float | None:
    """A checkpoint-asked stamp before `path`'s mtime, or None when it cannot be read. IMPURE.

    One millisecond under the mtime, because the stamp is stored to three decimals and a value
    rounded up past the mtime would make compact-resume reject the very file it describes.
    """
    try:
        return os.path.getmtime(path) - 0.001
    except (OSError, TypeError, ValueError):
        return None


def _decide_compact(session: str, proj: object, tokens: int | None, window: int, source: str,
                    pct: object, cap: object, *, plan_mode: bool = False,
                    wrote: str | None = None) -> str | None:
    """Request a checkpoint once per crossing of the save point. IMPURE.

    A reading back BELOW the save point after a request means the harness compacted, so the request
    re-arms and the next crossing asks for a fresh checkpoint. Above it, `due` spaces repeats by a
    tenth of the window, which refreshes a checkpoint only when the harness is not compacting.

    When the call that earned the request is itself the checkpoint's write (`wrote`), that write
    answers it: the request is latched at this level and stamped just before the file, and nothing
    is said. Asking would stamp the moment AFTER the write, and compact-resume, which accepts only
    a checkpoint written after the request, would then report that none was saved - measured once
    on a first crossing after a compaction, where the session wrote handover.md on its own.
    """
    state, detail = compact_verdict(tokens, window, pct, cap, harness_window(dict(os.environ)))
    if tokens is None or not detail:      # an empty detail is exactly a reading of nothing
        return None
    if state == "misconfigured":
        if already_reported(session):
            return None
        mark_reported(session)
        return _misconfigured({**detail, "source": source})
    last = asked_at(session)
    if state != "save":
        if last:
            mark_asked(session, 0)
        return None
    if not due(tokens, detail["save_at"], window, last):
        return None
    answered_at = _stamp_before(wrote) if wrote else None
    mark_asked(session, tokens)
    if answered_at is not None:
        sig.mark_checkpoint_asked(session, now=answered_at)
        return None
    sig.mark_checkpoint_asked(session)
    # Asked only here, on the rare turn that requests a save, so an ordinary turn never pays for git.
    return _save(detail, handover_tracking(proj), plan_mode=plan_mode)


def main() -> int:
    try:
        event: object = json.load(sys.stdin)
    except Exception:                         # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not _is_record(event):
        return 0
    try:
        reason = decide(event, sig.load_config())
    except Exception:                         # noqa: BLE001 - a broken watcher must never wedge a turn
        return 0
    if not reason:
        return 0
    if event.get("hook_event_name") == "PostToolUse":
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse", "additionalContext": reason}}))
    else:
        sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                         # noqa: BLE001 - fail open
        sys.exit(0)
