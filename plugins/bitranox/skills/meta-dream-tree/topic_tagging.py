"""Build the inputs a bulk judge needs to choose topics, and turn its rows into engine batches.

Choosing the topics of many facts, or of every level of a tree, is the same bounded judgment made
over many items: "is this item about topic T", once per topic of the tree's closed list. This
tool prepares that judgment for `jev-judge` (skill `bitranox:ai-llm-jev-judge`) and reads its
answers back. It never calls the judge and never writes the memory store; the engine's
`set-topics --batch` and `set-level-topics` do the writing.

  questions --from D --out questions.json
      One yes/no (`noul`) question per topic of the tree's list, id = the topic, from its meaning.
  items --from D --facts-at LEVEL --out items.jsonl
      One item per unpinned pointer line at LEVEL: {"id": slug, "state": {"title", "hook"}}.
  items --from D --levels --out items.jsonl
      One item per level below the tree top that has a descriptor:
      {"id": path below the top, "state": {"path", "descriptor"}} (its TOPICS line left out).
  decide --from D --rows rows.jsonl --kind facts|levels --threshold T --out decided.jsonl
         --unsure-out unsure.jsonl [--band LOW HIGH]
      A row is DECIDED when it is ok, answers every topic of the list, and no answer lies inside
      the unsure band (default 0.2 to 0.8, bounds excluded): its topics are those answered at
      T or above. facts: {"slug", "topics"} lines, the file `set-topics --batch` takes. levels:
      {"level", "topics"} lines, one `set-level-topics` call each. Every other row goes to the
      unsure file with its reason and answers, for a model to tag by reading. An answer counts
      only when it is a finite probability within 0..1; any other value is no answer.
      `--out` and `--unsure-out` must name two files.

`set-topics --batch` refuses the WHOLE batch for one line it cannot apply, so a decided file
must hold none. A fact row is therefore put through the engine's own row check
(`memory_engine._topic_row_problem`): an id that is no valid slug, one no level of the tree
points at, a pinned fact, a body without frontmatter, or a line the engine may not bind goes to
the unsure file with the engine's reason, whatever the judge answered.

`decide` takes at most `memory_engine.MAX_TOPIC_BATCH` rows, for both kinds: a decided file of
more rows is one `set-topics --batch` refuses, so a larger rows file is refused here, and the
route is to split the items file into parts of at most that many lines and run the judge and
`decide` once per part.

Items and rows are streamed, one line held at a time; `decide` also keeps the id of each row,
to send a second row for one item to the unsure file, so what it holds grows by one short id per
row and the row limit above bounds it. For `--kind facts` it also holds, read before the first
row, the engine's pointer record of every fact of the tree (`_pointer_owners`): that
grows with the store, never with the rows file. Every output is written to a temporary file
beside its target and renamed into place only when the whole input was read, so a run that
fails leaves an earlier output as it was and no half file. Prints one JSON summary on stdout.
Exit codes: 0 done; 2 could not run (bad arguments, an input it cannot read, no topic list).
"""

import argparse
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import memory_engine as ME  # noqa: E402
import self_improve_signals as sig  # noqa: E402
import topic_placement as tp  # noqa: E402
import topic_store  # noqa: E402
import uuid_store as us  # noqa: E402

MAX_ROW_BYTES = 1 << 20
"""Longest line of a rows file this reads: a row holds one answer per topic of a list capped at
`topic_store.MAX_LIST`, far under this."""


class TaggingError(ValueError):
    """An input this tool cannot use; the CLI reports it as `! error` and exits 2."""


def _topic_list(start):
    anchor = ME._anchor(os.path.abspath(str(start)))
    data = topic_store.load(anchor)
    if data is None:
        raise TaggingError("%s has no topic list (memory_engine.py topics-set-list --proj %s "
                           "--from-file LIST.json writes one)" % (anchor, anchor))
    return anchor, data["topics"]


def build_questions(topics):
    """The judge's questions for a topic list {tag: meaning}: one `noul` per topic, id = the tag."""
    return [{
        "id": tag,
        "type": "noul",
        "instructions": ("The item is either a rule (its title and one-line trigger) or a "
                         "directory (its path and a description of everything below it). "
                         "Topic '%s': %s. For a rule: does it hold wherever this topic is in "
                         "use, and only there? For a directory: is this topic in use below it?"
                         % (tag, topics[tag])),
        "criteria": {"true": "the item is about topic '%s'" % tag,
                     "false": "the item is not about it, or holds regardless of it"},
    } for tag in sorted(topics)]


def iter_fact_items(level):
    """One item per unpinned, migrated pointer line at `level`, in block order."""
    text = ME.read_store_text(sig.claude_local_md_path(level))
    for ptr in us.parse_pointer_index(text)[1]:
        if not ptr.pin and not ptr.legacy:
            yield {"id": ptr.slug, "state": {"title": ptr.title, "hook": ptr.hook}}


def iter_level_items(anchor):
    """One item per curated level below the tree top that has a descriptor, in path order."""
    for level in sorted(ME.curated_levels_under(anchor)):
        key = topic_store.level_key(anchor, level)
        scope = us.parse_pointer_index(ME.read_store_text(sig.claude_local_md_path(level)))[0]
        if not key or not scope.strip():
            continue
        lines = [ln for ln in scope.splitlines() if not ln.startswith("TOPICS:")]
        yield {"id": key, "state": {"path": key, "descriptor": "\n".join(lines).strip()}}


def _probability(entry):
    """The judge's value in `entry` when it is a number within 0..1, else None (NaN and the
    infinities included: NaN fails both comparisons)."""
    value = entry.get("value") if isinstance(entry, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if 0.0 <= value <= 1.0 else None


def judge_row(row, topics, threshold, band):
    """(topics, reason) for one judge row: (sorted tags, None) when decided, else (None, why)."""
    if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
        return None, "no string id"
    if row.get("ok") is not True:
        return None, "failed: %s" % (row.get("reason") or "not ok")
    answers = row.get("answers")
    if not isinstance(answers, dict):
        return None, "no answers"
    taken = []
    for tag in sorted(topics):
        value = _probability(answers.get(tag))
        if value is None:
            return None, "no answer for %s" % tag
        if band[0] < value < band[1]:
            return None, "unsure about %s (%.2f)" % (tag, value)
        if value >= threshold:
            taken.append(tag)
    if len(taken) > tp.MAX_TOPICS:
        return None, "%d topics, over the %d one item may carry" % (len(taken), tp.MAX_TOPICS)
    return taken, None


def _iter_rows(path):
    """Yield (line number, row or None) for each non-blank line of a rows file."""
    try:
        with open(path, "rb") as fh:
            for number, raw in enumerate(iter(lambda: fh.readline(MAX_ROW_BYTES + 1), b""), 1):
                if len(raw) > MAX_ROW_BYTES:
                    raise TaggingError("%s: line %d is over %d bytes" % (path, number, MAX_ROW_BYTES))
                if not raw.strip():
                    continue
                try:
                    yield number, json.loads(raw.decode("utf-8"))
                except (ValueError, RecursionError):
                    yield number, None
    except OSError as exc:
        raise TaggingError("cannot read %s: %s" % (path, exc.strerror or exc)) from exc


@contextlib.contextmanager
def _replacing(*targets):
    """Yield one text file per target, each a temporary file beside it; rename them into place
    when the block ends, and remove them when it raises. A reader of a target therefore sees the
    old file or the whole new one, never a half-written one, and a refused run leaves no file."""
    opened = []
    try:
        for target in targets:
            path = Path(target)
            fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent))
            opened.append((os.fdopen(fd, "w", encoding="utf-8", newline="\n"), tmp, path))
        yield [fh for fh, _tmp, _path in opened]
        for fh, _tmp, _path in opened:
            fh.close()
        for _fh, tmp, path in opened:
            os.replace(tmp, path)
    except BaseException:
        for fh, tmp, _path in opened:
            fh.close()
            with contextlib.suppress(OSError):
                os.unlink(tmp)
        raise


def _over_batch_limit(rows_path):
    return TaggingError(
        "%s holds more than %d rows, the most one `memory_engine.py set-topics --batch` takes: "
        "split the items file (or this rows file) into parts of at most %d lines and run the "
        "judge and `decide` once per part" % (rows_path, ME.MAX_TOPIC_BATCH, ME.MAX_TOPIC_BATCH))


def fact_owners(anchor):
    """The engine's pointer record (`memory_engine._pointer_owners`) of every fact a level of the
    tree at `anchor` points at, from the engine's own level walk and pointer parser: what
    `set-topics` resolves a slug against. Two walks of the levels, one for the slugs and the
    engine's own for their record; grows with the store, not with any rows file."""
    pointed = set()
    for level in ME.curated_levels_under(anchor):
        pointed.update(ptr.slug for ptr in us.parse_pointer_index(
            ME.read_store_text(sig.claude_local_md_path(level)))[1])
    return ME._pointer_owners(anchor, pointed)


def _decided_line(key, ident, taken, kind):
    """(line, None) for a decided row, or (None, why) when the engine would refuse its line.

    The byte limit is a backstop, unreachable for a row the engine's check passed: such a slug
    names a body file (a filename of at most 255 bytes on the filesystems the store lives on)
    and carries at most tp.MAX_TOPICS tags of at most 32 characters. It is kept so a later change
    to one of those limits cannot hand the engine a line it refuses."""
    line = json.dumps({key: ident, "topics": taken}, sort_keys=True) + "\n"
    if kind == "facts" and len(line.encode("utf-8")) > ME.MAX_TOPIC_BATCH_LINE_BYTES:
        return None, ("its batch line is over the %d bytes `set-topics --batch` reads"
                      % ME.MAX_TOPIC_BATCH_LINE_BYTES)
    return line, None


def _unsure_line(row, number, why, topics):
    ident = row.get("id") if isinstance(row, dict) else None
    answers = row.get("answers") if isinstance(row, dict) else None
    values = {tag: answers[tag].get("value") for tag in sorted(topics)
              if isinstance(answers, dict) and isinstance(answers.get(tag), dict)}
    return json.dumps({"id": ident, "line": number, "reason": why, "answers": values},
                      sort_keys=True) + "\n"


def decide(rows_path, topics, kind, threshold, band, out_path, unsure_path, *, anchor):
    """Split a rows file into the decided batch and the unsure rest; returns the counts. An id
    seen twice is unsure the second time: two answers for one item are no decision. A fact row
    the engine would refuse (`_topic_row_problem` against the tree at `anchor`) is unsure with
    the engine's reason. Raises TaggingError, writing neither output, for a file of more than
    MAX_TOPIC_BATCH rows."""
    key = "slug" if kind == "facts" else "level"
    owners = fact_owners(anchor) if kind == "facts" else None
    counts = {"rows": 0, "decided": 0, "unsure": 0}
    seen = set()
    with _replacing(out_path, unsure_path) as (out, unsure):
        for number, row in _iter_rows(rows_path):
            if counts["rows"] >= ME.MAX_TOPIC_BATCH:
                raise _over_batch_limit(rows_path)
            counts["rows"] += 1
            taken, why = judge_row(row, topics, threshold, band) if row is not None \
                else (None, "line %d is not a JSON object" % number)
            ident = row.get("id") if isinstance(row, dict) else None
            if owners is not None and isinstance(ident, str) and ident:
                # The engine's reason wins: no reading of the answers makes its line applicable.
                why = ME._topic_row_problem(ident, tuple(taken or ()), anchor, topics, owners) or why
            if why is None and ident in seen:
                taken, why = None, "a second row for this id"
            if isinstance(ident, str):
                seen.add(ident)
            line = None
            if why is None:
                line, why = _decided_line(key, ident, taken, kind)
            if why is None:
                counts["decided"] += 1
                out.write(line)
            else:
                counts["unsure"] += 1
                unsure.write(_unsure_line(row, number, why, topics))
    return counts


def _write_items(items, out_path):
    count = 0
    with _replacing(out_path) as (out,):
        for item in items:
            out.write(json.dumps(item, sort_keys=True) + "\n")
            count += 1
    return count


def _same_file(first, second):
    """True when two paths name one file: the same file on disk when both exist (a hard link
    included), else the same resolved path."""
    if os.path.exists(first) and os.path.exists(second):
        return os.path.samefile(first, second)
    return os.path.normcase(os.path.realpath(first)) == os.path.normcase(os.path.realpath(second))


def _run(args):
    anchor, topics = _topic_list(args.start)
    if args.cmd == "questions":
        questions = build_questions(topics)
        with _replacing(args.out) as (out,):
            out.write(json.dumps(questions, indent=2, sort_keys=True) + "\n")
        return {"command": "questions", "questions": len(questions), "out": args.out}
    if args.cmd == "items":
        items = iter_level_items(anchor) if args.levels else iter_fact_items(os.path.abspath(args.facts_at))
        return {"command": "items", "items": _write_items(items, args.out), "out": args.out}
    low, high = args.band
    if not (0.0 <= low <= high <= 1.0 and 0.0 <= args.threshold <= 1.0):
        raise TaggingError("--threshold and --band take probabilities, LOW <= HIGH, within 0..1")
    if _same_file(args.out, args.unsure_out):
        raise TaggingError("--out and --unsure-out name the same file %s: the unsure rows would "
                           "replace the decided ones" % args.out)
    counts = decide(args.rows, topics, args.kind, args.threshold, (low, high), args.out,
                    args.unsure_out, anchor=anchor)
    return dict(counts, command="decide", out=args.out, unsure_out=args.unsure_out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("questions", help="one yes/no question per topic of the tree's list")
    q.add_argument("--from", dest="start", required=True, help="any dir of the tree")
    q.add_argument("--out", required=True)
    i = sub.add_parser("items", help="the items to judge: the facts at one level, or the levels")
    i.add_argument("--from", dest="start", required=True, help="any dir of the tree")
    what = i.add_mutually_exclusive_group(required=True)
    what.add_argument("--facts-at", dest="facts_at", default=None, help="the level whose facts are judged")
    what.add_argument("--levels", action="store_true", help="every described level below the top")
    i.add_argument("--out", required=True)
    d = sub.add_parser("decide", help="turn judge rows into an engine batch and an unsure rest")
    d.add_argument("--from", dest="start", required=True, help="any dir of the tree")
    d.add_argument("--rows", required=True, help="the judge's rows.jsonl")
    d.add_argument("--kind", required=True, choices=["facts", "levels"])
    d.add_argument("--threshold", required=True, type=float, help="a topic is taken at this probability or above")
    d.add_argument("--band", nargs=2, type=float, default=[0.2, 0.8], metavar=("LOW", "HIGH"),
                   help="an answer strictly between these is unsure (default 0.2 0.8)")
    d.add_argument("--out", required=True)
    d.add_argument("--unsure-out", dest="unsure_out", required=True)
    args = ap.parse_args(argv)
    try:
        summary = _run(args)
    except (TaggingError, topic_store.TopicStoreError, ME.TreeWalkError) as exc:
        print("! error: %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print("! error: %s: %s" % (exc.strerror or exc, exc.filename or ""), file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
