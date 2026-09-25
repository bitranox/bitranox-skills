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

`--sample N` shows N of the prompts a predicate FIRED on (either predicate, when two are given),
or the first N prompts when no predicate is given; `--json` carries the same N. Unreadable
transcripts and directories are listed on stderr.

Exit codes: 0 fine, 1 the corpus held no prompt, 2 usage or IO error - a --root that does not
exist, a predicate option without its module, --count together with --module (--count calls no
predicate; drop it to get the firing counts), or any transcript or directory that could not be
read (the counts printed then cover only what was read).
"""

import argparse
import json
import os
import sys
from pathlib import Path

__all__ = [
    "DEFAULT_ROOT", "TYPED_ENTRYPOINTS", "UsageError", "collect_prompts", "diff_predicates",
    "extract_prompts", "main", "prompt_key", "prompt_text_of", "read_transcript",
    "transcript_lines", "transcript_prefix",
]

DEFAULT_ROOT = "~/.claude/projects"
# `entrypoint` separates a person typing from a headless node being driven. Both are `type: user`,
# and an SDK node's brief reads exactly like a prompt, so a rule priced on both measures a
# population it will never run against.
TYPED_ENTRYPOINTS = ("cli",)
DEFAULT_FUNC = "notice"

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


def read_transcript(path):
    """A transcript's text, decoded the one way every line number here is counted against.

    Bytes, not text mode: text mode turns a lone \\r into a line break and so renumbers every
    later line. utf-8-sig: a BOM would otherwise make the first record unparseable.
    """
    return Path(path).read_bytes().decode("utf-8-sig", errors="replace")


def transcript_lines(text):
    """The lines of a transcript, split the one way `line` numbers here count them.

    Newline only, because JSONL is newline-delimited: JSON may carry U+2028/U+2029/U+0085
    unescaped inside a string, and a half-written line may hold a raw \\f, \\x1c or \\r, and
    splitlines() breaks each of those in two, dropping the record and shifting every later number.
    """
    return text.split("\n")


def transcript_prefix(text, line):
    """The transcript as it stood before 1-based `line`: every earlier line, byte for byte.

    A replay rebuilds a prompt's state from this, so it must end exactly where `extract_prompts`
    numbered the prompt; a caller cutting it with its own split drifts at the first odd record.
    """
    return "\n".join(transcript_lines(text)[:max(0, line - 1)])


def extract_prompts(text, source="", sidechain=False):
    """Every typed prompt in one transcript, with the context a replay needs to rebuild its state.

    Each carries `source` and the 1-based `line` it came from, so a caller can reconstruct the
    transcript PREFIX (`transcript_prefix`) and ask the production code what state it would have
    built at that moment, rather than reimplementing that state here and drifting from it.
    """
    out = []
    for number, line in enumerate(transcript_lines(text), start=1):
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


def _transcripts(base, skipped):
    """Every *.jsonl below `base`, sorted. Symlinked directories are not followed, as rglob did not.

    os.walk rather than rglob because rglob drops a directory it cannot open without a word, and
    a corpus that quietly lost a project reads exactly like a smaller corpus.
    """
    def _record(err):
        skipped.append("%s: %s" % (err.filename, err))

    found = []
    for dirpath, _dirs, names in os.walk(base, onerror=_record):
        found.extend(Path(dirpath) / n for n in names if n.endswith(".jsonl"))
    return sorted(found)


def collect_prompts(root, sidechain=False):
    """Every DISTINCT typed prompt below `root`, deduped by record uuid.

    Resuming or forking a session copies the earlier transcript into a new file, so one real
    prompt sits in two .jsonl under the same uuid; counting it twice inflates every denominator
    quietly. A record with no uuid is never collapsed, since absent is not the same value twice.
    Subagent transcripts nest two levels deeper than the session files, so the walk is recursive,
    and a directory it cannot open lands in `skipped` rather than silently shrinking the corpus.
    """
    base = Path(root).expanduser()
    skipped = []
    files = _transcripts(base, skipped) if base.is_dir() else ([base] if base.is_file() else [])
    prompts, files_read, seen, duplicates = [], 0, set(), 0
    for path in files:
        try:
            text = read_transcript(path)
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


def prompt_key(prompt, index):
    """The name a prompt goes by in a diff: its uuid, else `source:line`, else `#index`.

    A record with no uuid is never the same value twice, so keying on the raw uuid made every
    uuid-less prompt one `None` and a diff over them reported a single shared firing.
    """
    if prompt.get("uuid") is not None:
        return prompt["uuid"]
    if prompt.get("source") or prompt.get("line") is not None:
        return "%s:%s" % (prompt.get("source", ""), prompt.get("line"))
    return "#%d" % index


def diff_predicates(prompts, a, b):
    """Which prompts each predicate fires on, as SETS.

    A count says two rules are equally noisy; it cannot say they are noisy about the same
    prompts, and a narrowing that also admits something new nets out to zero. Each prompt is
    named by `prompt_key`, so prompts without a uuid do not all collapse into one None.
    """
    a_ids, b_ids = [], []
    for index, prompt in enumerate(prompts):
        text = prompt.get("prompt") or ""
        if a(text):
            a_ids.append(prompt_key(prompt, index))
        if b(text):
            b_ids.append(prompt_key(prompt, index))
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
    p.add_argument("--func", help="name of the predicate (default %s)" % DEFAULT_FUNC)
    p.add_argument("--module-b", help="a SECOND predicate, to diff firing sets against")
    p.add_argument("--func-b", help="name of the second predicate (default %s)" % DEFAULT_FUNC)
    p.add_argument("--count", action="store_true", help="only count prompts, call no predicate")
    p.add_argument("--sidechain", action="store_true", help="include subagent briefs")
    p.add_argument("--sample", type=int, default=0,
                   help="print N firings to read (N prompts when no predicate is given)")
    p.add_argument("--json", action="store_true", dest="as_json")
    return p.parse_args(argv)


def _check_predicate_options(args):
    """A predicate option whose module is missing was silently ignored; refuse it instead."""
    if args.module is None and (args.module_b or args.func or args.func_b):
        raise UsageError("--func, --module-b and --func-b need --module")
    if args.module_b is None and args.func_b:
        raise UsageError("--func-b needs --module-b")
    if args.count and args.module is not None:
        # --count calls no predicate, so honouring both printed a bare prompt count and asked the
        # named predicate nothing. Without --count the output already carries its firing count.
        raise UsageError("--count calls no predicate, so it cannot be combined with --module; "
                         "drop --count to print the predicate's firing counts")


def _check_root(root):
    base = Path(root).expanduser()
    if not (base.is_dir() or base.is_file()):
        # Reading nothing from a typo'd path looked exactly like an empty corpus (exit 1).
        raise UsageError("--root %s does not exist" % base)


def _firings(prompts, diff):
    """The prompts either predicate fired on, in corpus order: what --sample is for."""
    fired = set(diff["both"]) | set(diff["a_only"]) | set(diff["b_only"])
    return [p for i, p in enumerate(prompts) if prompt_key(p, i) in fired]


def _render(report, sample):
    out = ["root: %s" % report["root"],
           "files read: %d   prompts: %d   duplicates skipped: %d"
           % (report["files_read"], len(report["prompts"]), report["duplicates_skipped"])]
    diff = report.get("diff")
    if diff:
        out.append("a fired: %d   b fired: %d   both: %d   a only: %d   b only: %d"
                   % (diff["a_fired"], diff["b_fired"], len(diff["both"]), len(diff["a_only"]),
                      len(diff["b_only"])))
    for prompt in sample:
        out.append("  %s | %s" % (prompt["uuid"], " ".join(prompt["prompt"].split())[:120]))
    return "\n".join(out)


def _harden_stdout():
    """Escape what the console cannot encode rather than fail the whole listing.

    Under a cp1252 console or pipe (Windows, launched by plain `python` or `uv run`) one prompt
    holding an emoji failed the run. Called only when run as a script, so an importer's stdout is
    never reconfigured.
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(errors="backslashreplace")
        except (OSError, ValueError):                    # a stream that cannot be reconfigured
            pass


def _run(args):
    _check_predicate_options(args)
    _check_root(args.root)
    report = collect_prompts(args.root, sidechain=args.sidechain)
    sample = report["prompts"]
    if args.module:
        first = _load(args.module, args.func or DEFAULT_FUNC)
        second = (_load(args.module_b, args.func_b or DEFAULT_FUNC) if args.module_b
                  else (lambda _t: False))
        report["diff"] = diff_predicates(report["prompts"], first, second)
        sample = _firings(report["prompts"], report["diff"])
    sample = sample[:args.sample] if args.sample > 0 else []
    payload = dict(report, prompts=sample)
    print(json.dumps(payload, indent=2) if args.as_json else _render(report, sample))
    for line in report["skipped"]:
        print("corpus_prompts: skipped: %s" % line, file=sys.stderr)
    if report["skipped"]:
        return 2                                         # a partial corpus is an IO error, not a count
    return 0 if report["prompts"] else 1


def main(argv=None):
    try:
        return _run(_parse(sys.argv[1:] if argv is None else argv))
    except UsageError as exc:
        print("corpus_prompts: %s" % exc, file=sys.stderr)
        return 2
    except Exception as exc:                             # noqa: BLE001 - a CLI reports, never traces
        print("corpus_prompts: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    _harden_stdout()
    sys.exit(main())
