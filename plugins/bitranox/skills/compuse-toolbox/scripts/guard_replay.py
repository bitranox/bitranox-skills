# /// script
# requires-python = ">=3.10"
# dependencies = ["orjson"]
# ///
"""Replay every real Bash command in a Claude Code transcript corpus through a guard predicate,
and report BOTH how often it fires and how often it was RIGHT.

Why: a PreToolUse guard is written against the shapes its author thought of, and its unit tests
prove exactly that - it fires on the hazard and stays quiet on the counter-examples someone
imagined. Neither says whether it is QUIET in the wild, and neither says whether the times it
speaks are times worth speaking. Both have been measured wrong here on shipped hooks: one arm
fired on 7.8% of 60,517 real commands because routine nested-sub-repo work is structurally
identical to the hazard, and a later version was checked only for its RATE, leaving 131 of 344
firings with nothing to warn about.

So this reports rate and PRECISION as separate numbers, because the first does not answer the
second. Precision here means: of the calls the guard would have spoken on, how many were actually
refused by a gate - the only ones where speaking earlier would have saved anybody anything.

The cwd is not optional. A guard that resolves paths answers differently per session directory, so
a replay that drops it measures a different question than the one the guard is asked at runtime.
Each call is replayed with the cwd its record carries.

A predicate's SECOND argument is filled by the NAME of its second parameter, never by arity: name
it `cwd` to receive the call's directory, or `tool_name` to receive the tool being replayed. Any
other name is left at its default. Arity alone once handed a CWD to a `notice(command, tool_name)`
hook, which did not crash - it measured a reading production never uses and reported a rate for it.
The report's `forwarded_second_arg` states which one a run actually used.

READ THE PRECISION FIGURE FOR WHAT IT ASKS. It answers one question: of the calls this guard would
have spoken on, how many did a GATE actually refuse? That is the right question for a guard whose
whole point is a command that cannot succeed as written, and the WRONG question for one whose
hazard is something else - a warning about a plausible-but-wrong result is never followed by a
block, so it scores 0% here while being perfectly useful. A 0% is a prompt to ask what this
guard's hazard actually looks like in the record, not a verdict. For those, use `--sample` and
read the firings.

The RATE, by contrast, means the same thing for every guard: how much of ordinary work it speaks
on. That is the number that decides whether people start ignoring the channel.

Run:
  `uv run scripts/guard_replay.py --module ../../hooks/my-guard.py`
  `uv run scripts/guard_replay.py --module ../../hooks/my-guard.py --func notice --sample 5 --json`
  `uv run scripts/guard_replay.py --module g.py --root ~/.claude/projects --tool Bash`

Exit codes: 0 it fired at least once, 1 it never fired (loud on purpose - a guard that cannot
speak and a corpus you never really read print the same otherwise), 2 usage error, 3 nothing was
replayed (no files, or no calls of that tool).
"""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import re
import sys
from pathlib import Path

try:                                                     # fast path when available (uv run installs it)
    import orjson

    def _loads(raw):
        return orjson.loads(raw)

    def _dumps(obj):
        return orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode()
except ModuleNotFoundError:                              # stdlib fallback so the script runs anywhere
    import json as _json

    def _loads(raw):
        return _json.loads(raw)

    def _dumps(obj):
        return _json.dumps(obj, indent=2, ensure_ascii=False)


class UsageError(Exception):
    """A caller mistake worth naming, rather than an AttributeError from three frames deep."""


# What Claude Code writes into a tool_result when a PreToolUse hook refuses the call. It is the
# DEFAULT rather than the definition: a block recorded some other way would be counted as an
# ordinary failure and quietly deflate precision, so `--block-pattern` exists to widen it and the
# report always states which pattern produced the number.
DEFAULT_BLOCK_PATTERN = r"PreToolUse"


def is_gate_block(error_text, pattern: str = DEFAULT_BLOCK_PATTERN) -> bool:
    """True when this tool_result is a GATE refusing the call, not a command that ran and failed.

    The distinction is the whole point of the precision figure. A non-zero exit means the command
    executed; a guard speaking earlier would have saved nobody from it.
    """
    if not error_text:
        return False
    return bool(re.search(pattern, error_text))


class UnsupportedTool(ValueError):
    """A tool name whose payload field the extractor does not know.

    Raised rather than answered with an empty list, because the caller cannot tell those apart and
    reports the wrong one: before this existed, `--tool Write` exited 3 saying "found no Write
    calls", which blames the corpus for an emptiness the extractor caused.
    """


# Which field of a tool_use `input` carries the text a guard would judge. A guard about what gets
# WRITTEN is judged on the text about to land, so Edit contributes `new_string` and not the text
# it replaces.
TOOL_PAYLOAD = {
    "Bash": "command",
    "Write": "content",
    "Edit": "new_string",
}


def payload_field(tool: str) -> str:
    """The input field to read for `tool`, or refuse naming what is known."""
    try:
        return TOOL_PAYLOAD[tool]
    except KeyError:
        raise UnsupportedTool(
            "cannot read %r calls: no payload field is known for that tool. Known tools: %s."
            % (tool, ", ".join(sorted(TOOL_PAYLOAD)))
        ) from None


def extract_calls(text: str, tool: str = "Bash", field: str = None):
    """Every call of `tool` in one transcript, each with the cwd it ran under and its error.

    `field` overrides which input field is handed to the predicate. The default is the tool's
    WRITTEN payload; a guard about WHERE a write lands is judged on `file_path` instead, and
    pricing it on the content would measure the wrong question while reporting a confident rate.

    A malformed line is skipped rather than fatal: a transcript being written while it is read
    routinely ends mid-line, and aborting there would silently truncate the corpus.
    """
    field = field or payload_field(tool)
    calls, errors = [], {}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            rec = _loads(line)
        except Exception:                                # noqa: BLE001 - any parse failure is a skip
            continue
        if not isinstance(rec, dict):
            continue
        cwd = rec.get("cwd")
        content = (rec.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == tool:
                command = (block.get("input") or {}).get(field)
                if isinstance(command, str):
                    calls.append({"id": block.get("id"), "command": command,
                                  "cwd": cwd, "error": None})
            elif block.get("type") == "tool_result" and block.get("is_error"):
                body = block.get("content")
                errors[block.get("tool_use_id")] = body if isinstance(body, str) else _dumps(body)
    for call in calls:
        call["error"] = errors.get(call["id"])
    return calls


# What a predicate's SECOND positional parameter may be filled with, keyed by its NAME. Anything
# not listed here is left at its default and the predicate is called with the command alone.
_SECOND_ARG_NAMES = ("cwd", "tool_name")


def _second_arg_kind(predicate):
    """What to pass as this predicate's second argument - `"cwd"`, `"tool_name"`, or None.

    Decided by the parameter's NAME, never by arity, and that distinction is the whole function.
    Asking only "does it take two positional parameters?" filled the second slot whatever it meant,
    so `notice(command, tool_name=None)` - the house shape across the bitranox hooks - was handed a
    CWD as its tool name. Nothing failed: an unrecognised tool takes the strict fallback inside
    `shell_text`, so the guard kept answering, and the replay reported a fire rate for a code path
    production never runs. A wrong number that arrives quietly is worse than a crash.

    An unknown name is left alone rather than guessed at. `bracket_leaks(cmd, haystack=None)` is a
    real signature in this plugin, and a cwd in its haystack slot would change what the guard
    searches without saying so.
    """
    name = _second_param_name(predicate)
    return name if name in _SECOND_ARG_NAMES else None


def _second_param_name(predicate):
    """The NAME of this predicate's second positional parameter, or None if it has none.

    Separate from `_second_arg_kind` so a caller can tell "there is nothing to fill" from "there is
    something and I do not know what it means" - the two look identical downstream and only the
    second is worth telling anyone about.
    """
    try:
        params = inspect.signature(predicate).parameters
    except (TypeError, ValueError):                      # a builtin or C callable: assume one arg
        return None
    positional = [p for p in params.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    return positional[1].name if len(positional) >= 2 else None


def _spread_sample(fires, n):
    """`n` firings drawn evenly across `fires`, in corpus order - never the first `n`.

    The corpus is walked file by file, so the firings arrive grouped by PROJECT. Filling the
    sample from the front therefore hands back whichever project sorts first, and it reads exactly
    like a representative sample of the whole run.

    Measured 2026-08-30: 40 of 557 firings read this way put a residual at ~10 percent, because
    those 40 came almost entirely from one project that writes scripts via heredocs; classifying
    all 557 put it at ~2 percent. The full set also held four shapes the 40 never contained, and
    those four were a live regression. A spread cannot make a small sample sufficient, but it stops
    it being systematically one project's habits.
    """
    if n <= 0:
        return []
    if n >= len(fires):
        picked = list(fires)
    else:
        step = len(fires) / n
        picked = [fires[int(i * step)] for i in range(n)]
    return [{"command": c["command"], "cwd": c["cwd"], "error": c["error"]} for c in picked]


def classify(calls, predicate, sample: int = 0, block_pattern: str = DEFAULT_BLOCK_PATTERN,
             tool: str = "Bash"):
    """Run the predicate over every call and split the firings by what actually happened.

    A predicate that raises is COUNTED, never swallowed into the quiet bucket: a guard crashing on
    a real command is a defect, and a replay that hid it would report the crash as good behaviour.

    `tool` is the tool whose calls are being replayed, and it is forwarded to a predicate that
    declares a `tool_name` parameter, so the guard is measured on the reading production gives it.
    """
    second = _second_arg_kind(predicate)
    declared = _second_param_name(predicate)
    if declared and not second:
        # Said ONCE, before the loop, and on stderr so it cannot corrupt the JSON on stdout. This
        # is a behaviour CHANGE for a caller upgrading: that parameter used to receive the cwd,
        # by arity and regardless of meaning. Announcing it is the whole lesson of the bug being
        # fixed here - a result that shifts without saying so is the expensive kind.
        print("warning: second parameter %r is not recognised (expected one of %s); "
              "calling the predicate with the command alone"
              % (declared, ", ".join(_SECOND_ARG_NAMES)), file=sys.stderr)
    extra = {"cwd": None, "tool_name": tool}
    fires, blocked, errored, clean, predicate_errors = [], 0, 0, 0, 0
    for call in calls:
        extra["cwd"] = call["cwd"]
        try:
            verdict = (predicate(call["command"], extra[second]) if second
                       else predicate(call["command"]))
        except Exception:                                # noqa: BLE001 - a crash is a finding, not a stop
            predicate_errors += 1
            continue
        if not verdict:
            continue
        fires.append(call)
        if is_gate_block(call["error"], block_pattern):
            blocked += 1
        elif call["error"]:
            errored += 1
        else:
            clean += 1
    # Drawn AFTER the walk, so it can span the whole corpus rather than its first file.
    samples = _spread_sample(fires, sample)
    total = len(calls)
    return {
        "commands": total,
        "fires": len(fires),
        "fire_rate_pct": round(100 * len(fires) / total, 3) if total else None,
        "blocked": blocked,
        "errored": errored,
        "completed_fine": clean,
        "precision_pct": round(100 * blocked / len(fires), 2) if fires else None,
        "predicate_errors": predicate_errors,
        "block_pattern": block_pattern,
        # Which second argument the predicate was given, so a reader can tell WHICH reading of the
        # guard was measured. Leaving this implicit is what let a cwd-as-tool_name run pass as real.
        "forwarded_second_arg": second,
        "samples": samples,
    }


def load_predicate(path: str, func_name: str):
    """Import a predicate from a file path, hyphenated hook modules included.

    The module's own directory goes on `sys.path` first, because a hook routinely imports a
    sibling helper and would otherwise die on an import the real runtime resolves fine.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        raise UsageError("no such module file: %s" % p)
    parent = str(p.resolve().parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    spec = importlib.util.spec_from_file_location(re.sub(r"\W", "_", p.stem), p)
    if spec is None or spec.loader is None:
        raise UsageError("cannot load a module from %s" % p)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:                             # noqa: BLE001 - report which file, not a bare trace
        raise UsageError("failed to import %s: %s" % (p, exc)) from exc
    fn = getattr(module, func_name, None)
    if not callable(fn):
        raise UsageError("%s defines no callable named %r" % (p, func_name))
    return fn


def replay(root: str, predicate, tool: str = "Bash", sample: int = 0,
           block_pattern: str = DEFAULT_BLOCK_PATTERN, field: str = None):
    """Walk every *.jsonl below `root` and classify every DISTINCT call of `tool` found in them.

    Distinct matters: resuming or forking a session copies the earlier transcript into a new file,
    so one real call sits in two .jsonl under the same tool_use id. Counting it twice inflates the
    denominator and deflates the rate, and it does it silently - the corpus merely looks bigger.
    A call with no id is never collapsed, since absent is not the same value twice.
    """
    base = Path(root).expanduser()
    calls, files_read, skipped, seen, duplicates = [], 0, [], set(), 0
    for f in sorted(base.rglob("*.jsonl")) if base.is_dir() else ([base] if base.is_file() else []):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            skipped.append("%s: %s" % (f, exc))
            continue
        files_read += 1
        for call in extract_calls(text, tool=tool, field=field):
            if call["id"] is not None:
                if call["id"] in seen:
                    duplicates += 1
                    continue
                seen.add(call["id"])
            calls.append(call)
    report = classify(calls, predicate, sample=sample, block_pattern=block_pattern, tool=tool)
    report["files_read"] = files_read
    report["duplicates_skipped"] = duplicates
    report["skipped"] = skipped
    report["root"] = str(base)
    return report


def exit_code(report) -> int:
    """0 fired, 1 never fired, 3 nothing was replayed at all."""
    if not report.get("commands"):
        return 3
    return 0 if report.get("fires") else 1


def _parse(argv):
    ap = argparse.ArgumentParser(
        description="Replay real Bash commands through a guard predicate; report rate AND precision.")
    ap.add_argument("--module", required=True, help="path to the .py holding the predicate")
    ap.add_argument("--func", default="notice", help="predicate name in that module (default: notice)")
    ap.add_argument("--root", default="~/.claude/projects", help="corpus dir or a single .jsonl")
    ap.add_argument("--tool", default="Bash", help="tool_use name to replay (default: Bash)")
    ap.add_argument("--field", default=None,
                    help="input field handed to the predicate instead of the tool's written "
                         "payload (e.g. file_path, to price a guard on WHERE a write lands)")
    ap.add_argument("--sample", type=int, default=0,
                    help="print N example firings, spread evenly across the corpus "
                         "(not the first N). A sample cannot establish a RATIO - "
                         "classify every firing for that.")
    ap.add_argument("--block-pattern", default=DEFAULT_BLOCK_PATTERN,
                    help="regex marking a tool_result as a GATE block (default: %(default)s)")
    ap.add_argument("--json", action="store_true", help="emit the report as a JSON envelope")
    return ap.parse_args(argv)


def _render(report) -> str:
    lines = [
        "corpus:    %s" % report["root"],
        "files:     %d read%s" % (report["files_read"],
                                  ", %d skipped" % len(report["skipped"]) if report["skipped"] else ""),
        "commands:  %d%s" % (report["commands"],
                              " (%d duplicate record(s) of the same call skipped)"
                              % report["duplicates_skipped"] if report["duplicates_skipped"] else ""),
        "fires:     %d (%s%%)" % (report["fires"], report["fire_rate_pct"]),
        "  gate-blocked:   %d" % report["blocked"],
        "  failed anyway:  %d" % report["errored"],
        "  completed fine: %d" % report["completed_fine"],
        "precision: %s%% (blocked / fires, block-pattern %r)" % (report["precision_pct"],
                                                                 report["block_pattern"]),
    ]
    if report["predicate_errors"]:
        lines.append("predicate raised on %d command(s) - that is a defect, not noise"
                     % report["predicate_errors"])
    for s in report["samples"]:
        lines.append("--- sample (cwd %s)\n%s" % (s["cwd"], s["command"]))
    return "\n".join(lines)


def main(argv=None) -> int:
    """Load the predicate, replay the corpus, report. Warnings go to stderr, never into the data."""
    args = _parse(sys.argv[1:] if argv is None else argv)
    try:
        predicate = load_predicate(args.module, args.func)
    except UsageError as exc:
        print("guard_replay: %s" % exc, file=sys.stderr)
        if args.json:
            print(_dumps({"ok": False, "command": "replay", "skipped": [str(exc)], "data": None}))
        return 2
    try:
        report = replay(args.root, predicate, tool=args.tool, sample=args.sample,
                        block_pattern=args.block_pattern, field=args.field)
    except UnsupportedTool as exc:
        # A refusal the caller can read, not a traceback: the whole point of raising here is that
        # an unreadable tool must not be reported as an empty corpus.
        print("guard_replay: %s" % exc, file=sys.stderr)
        if args.json:
            print(_dumps({"ok": False, "command": "replay", "skipped": [str(exc)], "data": None}))
        return 2
    rc = exit_code(report)
    if rc == 3:
        print("guard_replay: read %d file(s) and found no %s calls - nothing was replayed"
              % (report["files_read"], args.tool), file=sys.stderr)
    elif rc == 1:
        print("guard_replay: the predicate never fired over %d command(s)" % report["commands"],
              file=sys.stderr)
    if args.json:
        print(_dumps({"ok": rc == 0, "command": "replay", "skipped": report["skipped"],
                      "data": report}))
    else:
        print(_render(report))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
