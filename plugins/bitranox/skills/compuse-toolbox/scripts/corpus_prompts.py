#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["orjson"]
# ///
"""Replay every PROMPT a person actually typed, from the Claude Code transcript corpus, through a
predicate - and diff two predicates by the prompts they fire on, not by how many.

Why this is separate from `guard_replay`: that one replays TOOL CALLS and scores a guard by rate
and by whether a gate refused the call. A prompt has no gate and no exit code, so precision means
nothing here; the question is which prompts a rule speaks on. Pricing a prompt-side rule meant
hand-rolling the corpus walk each time, and the last one that mattered lived in a session
scratchpad and is gone.

Counting is the wrong comparison. Two rules can fire the same NUMBER of times on different
prompts, so a count diff of zero is exactly the shape that hides a change. `diff_predicates`
returns the SETS.

Which records count is measured, not assumed. Over 300 transcripts, 14,884 `type: user` records
split 13,790 `tool_result` / 890 plain string / 203 list-of-text: the overwhelming majority of
user records are the assistant's own tool traffic wearing the user role. A prompt here is a user
record that carries text rather than a tool result, is not `isMeta`, is not a subagent's brief
(`isSidechain`), and whose `entrypoint` is a person at a terminal rather than a headless SDK node.

`origin` is deliberately not used. It is present on 245 of those 14,884 records, so filtering on
it drops ~98% of the corpus on the machines this runs on.

The prompts this yields are RAW. Whether one is a slash command, a pasted envelope or a
notification is the caller's rule to apply, not this tool's - the bitranox hooks answer it with
`hooks/prompt_text.py`, and a second copy here would drift from it.

Your predicate is called as `f(text)`, with the prompt's TEXT and nothing else - not the record,
and not a second positional argument. That differs from `guard_replay`, whose predicate takes
`f(command)` or `f(command, cwd)` because a guard that resolves paths answers differently per
session directory. A prompt has no cwd that changes its meaning, so there is nothing to forward
and no second-argument convention to get wrong. Anything truthy counts as a firing.

Run:
  corpus_prompts.py --module ../../hooks/skill-router.py --func some_predicate
  corpus_prompts.py --module a.py --func f --module-b b.py --func-b f --json
  corpus_prompts.py --count            # how many prompts the corpus holds, calls no predicate

Exit codes: 0 fine, 1 the corpus held no prompt, 2 usage or IO error.
"""

import argparse
import json
import sys
from pathlib import Path

__all__ = [
    "DEFAULT_ROOT", "TYPED_ENTRYPOINTS", "UsageError", "collect_prompts", "diff_predicates",
    "extract_prompts", "main", "prompt_text_of",
]

DEFAULT_ROOT = "~/.claude/projects"
# `entrypoint` separates a person typing from a headless node being driven. Both are `type: user`,
# and an SDK node's brief reads exactly like a prompt, so a rule priced on both measures a
# population it will never run against.
TYPED_ENTRYPOINTS = ("cli",)

try:                                                     # pragma: no cover - speed, not behaviour
    import orjson

    def _loads(raw):
        return orjson.loads(raw)
except ImportError:                                      # a hook env provisions no PEP 723 deps
    def _loads(raw):
        return json.loads(raw)


class UsageError(Exception):
    """Bad arguments or an unreadable path - reported, never a traceback."""


def prompt_text_of(message):
    """The text of a user message, or None when the record is not text at all.

    A `tool_result` block is not a prompt however it is wrapped, and a list of text blocks is
    joined rather than dropped: both shapes occur in the real corpus.
    """
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    texts = [b.get("text") for b in content
             if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]
    if not texts or any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    return "\n".join(texts)


def extract_prompts(text, source="", sidechain=False):
    """Every typed prompt in one transcript, with the context a replay needs to rebuild its state.

    Each carries `source` and the 1-based `line` it came from, so a caller can reconstruct the
    transcript PREFIX and ask the production code what state it would have built at that moment,
    rather than reimplementing that state here and drifting from it.
    """
    out = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rec = _loads(line)
        except Exception:                                # noqa: BLE001 - a half-written line is a skip
            continue
        if not isinstance(rec, dict) or rec.get("type") != "user":
            continue
        if rec.get("isMeta") or rec.get("toolUseResult") is not None:
            continue
        if rec.get("isSidechain") and not sidechain:
            continue
        if rec.get("entrypoint") not in TYPED_ENTRYPOINTS:
            continue
        body = prompt_text_of(rec.get("message"))
        if not body:
            continue
        out.append({"uuid": rec.get("uuid"), "prompt": body, "cwd": rec.get("cwd"),
                    "session_id": rec.get("sessionId"), "git_branch": rec.get("gitBranch"),
                    "timestamp": rec.get("timestamp"), "source": source, "line": number,
                    "sidechain": bool(rec.get("isSidechain"))})
    return out


def collect_prompts(root, sidechain=False):
    """Every DISTINCT typed prompt below `root`, deduped by record uuid.

    Resuming or forking a session copies the earlier transcript into a new file, so one real
    prompt sits in two .jsonl under the same uuid; counting it twice inflates every denominator
    quietly. A record with no uuid is never collapsed, since absent is not the same value twice.
    Subagent transcripts nest two levels deeper than the session files, so the walk is `rglob`.
    """
    base = Path(root).expanduser()
    files = sorted(base.rglob("*.jsonl")) if base.is_dir() else ([base] if base.is_file() else [])
    prompts, files_read, skipped, seen, duplicates = [], 0, [], set(), 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            skipped.append("%s: %s" % (path, exc))
            continue
        files_read += 1
        for prompt in extract_prompts(text, source=str(path), sidechain=sidechain):
            uuid = prompt["uuid"]
            if uuid is not None:
                if uuid in seen:
                    duplicates += 1
                    continue
                seen.add(uuid)
            prompts.append(prompt)
    return {"prompts": prompts, "files_read": files_read, "duplicates_skipped": duplicates,
            "skipped": skipped, "root": str(base)}


def diff_predicates(prompts, a, b):
    """Which prompts each predicate fires on, as SETS.

    A count says two rules are equally noisy; it cannot say they are noisy about the same
    prompts, and a narrowing that also admits something new nets out to zero.
    """
    a_ids, b_ids = [], []
    for prompt in prompts:
        text = prompt.get("prompt") or ""
        if a(text):
            a_ids.append(prompt.get("uuid"))
        if b(text):
            b_ids.append(prompt.get("uuid"))
    a_set, b_set = set(a_ids), set(b_ids)
    return {"a_fired": len(a_ids), "b_fired": len(b_ids), "total": len(prompts),
            "both": sorted(a_set & b_set, key=str),
            "a_only": sorted(a_set - b_set, key=str),
            "b_only": sorted(b_set - a_set, key=str)}


def _load(module, func):
    import guard_replay                                  # noqa: PLC0415 - only the CLI needs it

    return guard_replay.load_predicate(module, func)


def _parse(argv):
    p = argparse.ArgumentParser(description="Replay typed prompts through a predicate.")
    p.add_argument("--root", default=DEFAULT_ROOT, help="transcript corpus (default %(default)s)")
    p.add_argument("--module", help="file defining the predicate")
    p.add_argument("--func", default="notice", help="name of the predicate (default %(default)s)")
    p.add_argument("--module-b", help="a SECOND predicate, to diff firing sets against")
    p.add_argument("--func-b", default="notice", help="name of the second predicate")
    p.add_argument("--count", action="store_true", help="only count prompts, call no predicate")
    p.add_argument("--sidechain", action="store_true", help="include subagent briefs")
    p.add_argument("--sample", type=int, default=0, help="print N firings to read")
    p.add_argument("--json", action="store_true", dest="as_json")
    return p.parse_args(argv)


def _render(report, sample):
    out = ["root: %s" % report["root"],
           "files read: %d   prompts: %d   duplicates skipped: %d"
           % (report["files_read"], len(report["prompts"]), report["duplicates_skipped"])]
    diff = report.get("diff")
    if diff:
        out.append("a fired: %d   b fired: %d   both: %d   a only: %d   b only: %d"
                   % (diff["a_fired"], diff["b_fired"], len(diff["both"]), len(diff["a_only"]),
                      len(diff["b_only"])))
    for prompt in report["prompts"][:sample]:
        out.append("  %s | %s" % (prompt["uuid"], " ".join(prompt["prompt"].split())[:120]))
    for line in report["skipped"][:5]:
        out.append("skipped: %s" % line)
    return "\n".join(out)


def main(argv=None):
    try:
        args = _parse(sys.argv[1:] if argv is None else argv)
        report = collect_prompts(args.root, sidechain=args.sidechain)
        if not args.count and args.module:
            first = _load(args.module, args.func)
            second = _load(args.module_b, args.func_b) if args.module_b else (lambda _t: False)
            report["diff"] = diff_predicates(report["prompts"], first, second)
        payload = dict(report)
        if not args.sample:
            payload["prompts"] = []
        print(json.dumps(payload, indent=2) if args.as_json else _render(report, args.sample))
        return 0 if report["prompts"] else 1
    except UsageError as exc:
        print("corpus_prompts: %s" % exc, file=sys.stderr)
        return 2
    except Exception as exc:                             # noqa: BLE001 - a CLI reports, never traces
        print("corpus_prompts: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
