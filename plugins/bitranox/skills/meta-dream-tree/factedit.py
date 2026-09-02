# /// script
# requires-python = ">=3.10"
# ///
"""Read a bitranox memory fact, and recompose its hook plus body through the engine.

Why: editing a stored fact is a five-step chore that keeps being hand-rolled - find which LEVEL
owns the slug, read the pointer hook AND the body, draft a new hook, check it against the engine's
cap, then assemble a `memory_engine.py add` or `amend-pinned` call with the text in FILES. It was
re-solved three times in one session as throwaway scripts (compose the body, measure the hook,
assemble the amend), which is one past the point where it should have been a tool.

Four things make it a chore rather than a one-liner, and each is a way to get it wrong:

1. **You cannot edit the files.** The store-edit-guard denies Write/Edit on a pointer block or a
   central body: `memory_engine.py` is the single write path. So a recomposition is always an
   engine invocation, never a text edit.
2. **The hook has a HARD cap the engine refuses on**, and it refuses rather than truncating,
   because a silent word-boundary cut leaves an always-loaded line that still reads as a complete
   instruction. Measuring the draft before the call is the difference between one round trip and
   three. The cap is read from the LIVE engine here, never hardcoded, so a plugin bump cannot
   leave this lying about the limit.
3. **The hook must go through a FILE.** `--hook "$(cat f)"` is a shell command substitution that
   the guard denies, so every real-length hook needs a staged file. This writes them.
4. **A pinned fact refuses an ordinary `add`.** The verb depends on the stored `bx:pin` flag, and
   the flag is on the pointer line, which is the thing you were trying to read in the first place.
   This picks the verb from what is stored instead of from memory.

The engine keeps a hook-only update's body description in sync with the pointer, so amending just
the hook is safe; `show` reports it when the two have drifted apart anyway, which is the state a
hand-edit leaves behind.

Not a locator: "which level holds this slug" and "what is where in the tree" are answered by
`mem_levels.py` in the shipped `bitranox:compuse-toolbox` skill. This resolves the level only
because it needs it to call the engine.

Run: `uv run tools/factedit.py show --slug feedback-no-em-dashes --from /path/in/tree`
     `uv run tools/factedit.py check --hook-file draft.txt`
     `uv run tools/factedit.py apply --slug <slug> --from <dir> --hook-file new.txt --dry-run`
     `uv run tools/factedit.py apply --slug <slug> --from <dir> --hook-file new.txt --body-file b.md`

Exit codes: 0 = yes (found / would be accepted / applied), 1 = no (no such fact / the engine
refuses this hook / the engine refused the write), 2 = error (no engine, unreadable tree, bad
arguments). Advisories are PRODUCT, so they ride in the envelope's `data`; operational warnings
go to stderr and never into stdout.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

LEVEL_FILE = "CLAUDE.local.md"
STORE_DIRNAME = ".claude-memory"
FACTS_SUBDIR = "facts"

# Where a plugin-installed engine lives. The version segment is a glob on purpose: a hardcoded
# version goes stale on the next plugin bump, and this tool must read the LIVE caps or it is
# lying about them.
_CACHE_GLOB = ".claude/plugins/cache/bitranox-skills/bitranox/*/hooks/memory_engine.py"
_MARKETPLACE = ".claude/plugins/marketplaces/bitranox-skills/plugins/bitranox/hooks/memory_engine.py"

# Mirrors the engine's own frontmatter reader: the body's `description:` IS the hook.
_DESC_RX = re.compile(r"(?m)^description:[ \t]*(.*)$")


class FactEditError(Exception):
    """Base for every condition this tool reports as a typed message rather than a traceback."""


class EngineNotFound(FactEditError):
    """The memory engine could not be located, so the live caps and parser are unavailable.

    This FAILS rather than falling back to remembered constants: a cap checker running on a stale
    number reports a green that means nothing, which is worse than refusing to answer.
    """


class NoAnchor(FactEditError):
    """No `.claude-memory/` store above the starting directory - there is no tree here."""


class UnknownFact(FactEditError):
    """No pointer for this slug at any level of the chain."""


class BadInput(FactEditError):
    """The arguments cannot describe a recomposition (nothing to change, or two sources for one)."""


@dataclass(frozen=True)
class EngineRules:
    """The engine's live lint surface, injected so the judging below is testable without a store."""

    soft_max: int
    hard_max: int
    escalate_at: int
    over_soft: Callable[[str], bool]
    over_hard: Callable[[str], bool]
    missing_trigger: Callable[[str], bool]
    advise: Callable[[str, str], list]
    recurrence: Callable[[str], int | None]
    parse_index: Callable[[str], tuple]
    engine_path: Path | None = None


@dataclass(frozen=True)
class Verdict:
    """What the engine would do with a drafted hook, and what it would say while doing it."""

    length: int
    accepted: bool
    refusals: list[str] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Fact:
    """A stored fact as it currently reads: its pointer line, and the body behind it."""

    slug: str
    level: Path
    anchor: Path
    title: str
    hook: str
    pin: bool
    body: str
    body_path: Path

    @property
    def body_description(self) -> str:
        """The hook as the BODY records it. Drifts from `hook` only after a hand-edit."""
        return body_description(self.body)

    @property
    def hook_in_sync(self) -> bool:
        """Whether the pointer hook and the body's `description:` still say the same thing."""
        return " ".join(self.hook.split()) == " ".join(self.body_description.split())


# ---- pure helpers -------------------------------------------------------------------------------

def body_description(text: str) -> str:
    """The `description:` value from a framed body's frontmatter, or '' when it has none. PURE."""
    m = _DESC_RX.search(text or "")
    return m.group(1).strip() if m else ""


def judge_hook(hook: str, body: str, rules: EngineRules) -> Verdict:
    """What the engine would make of this hook. PURE given `rules`.

    Refusals and advisories are kept apart on purpose: only a refusal changes the answer to "will
    this be accepted", and collapsing the two would make a long-but-legal hook look rejected.
    """
    text = (hook or "").strip()
    refusals: list[str] = []
    advisories: list[str] = []
    if rules.over_hard(text):
        refusals.append(
            f"hook is {len(text)} chars, over the {rules.hard_max}-char HARD cap - the engine "
            "refuses rather than truncating; move the detail into the body")
    elif rules.over_soft(text):
        advisories.append(
            f"hook is {len(text)} chars, over the {rules.soft_max}-char soft cap (advisory, legal "
            f"up to {rules.hard_max}); keep it self-sufficient, do not trim load-bearing detail")
    if rules.missing_trigger(text):
        advisories.append(
            "hook has no trigger phrase - lead with WHEN it applies ('When <situation>, "
            "<directive>'), or it will not fire during reasoning")
    advisories.extend(str(a) for a in rules.advise(text, body or ""))
    seen = rules.recurrence(body or "")
    if seen is not None and seen >= rules.escalate_at:
        advisories.append(
            f"the body records recurrence {seen} - prose has already failed that many times, so "
            "rewording it is not the fix; propose a guard or a jig in the same turn")
    return Verdict(length=len(text), accepted=not refusals,
                   refusals=refusals, advisories=advisories)


def chain_levels(start: Path) -> list[Path]:
    """Every dir from `start` upward that carries a CLAUDE.local.md, narrowest first."""
    found: list[Path] = []
    cur = Path(start).resolve()
    while True:
        if (cur / LEVEL_FILE).is_file():
            found.append(cur)
        if cur.parent == cur:
            return found
        cur = cur.parent


def anchor_dir(start: Path) -> Path:
    """The tree anchor: the first ancestor holding a `.claude-memory/` store."""
    cur = Path(start).resolve()
    while True:
        if (cur / STORE_DIRNAME).is_dir():
            return cur
        if cur.parent == cur:
            raise NoAnchor(f"no {STORE_DIRNAME}/ store at or above {Path(start).resolve()}")
        cur = cur.parent


def body_file(anchor: Path, slug: str) -> Path:
    """Where a fact's body lives: `<anchor>/.claude-memory/facts/<slug>.md`."""
    return Path(anchor) / STORE_DIRNAME / FACTS_SUBDIR / f"{slug}.md"


# ---- engine discovery and loading ---------------------------------------------------------------

def engine_candidates(home: Path | None = None) -> list[Path]:
    """Every memory_engine.py this machine offers, NEWEST FIRST by mtime.

    By mtime, never by the version string in the path: a plugin version sorts lexicographically
    (5.9.0 after 5.267.3) and picking the wrong one would silence a cap change without a word.
    """
    root = Path(home) if home else Path.home()
    found = [p for p in root.glob(_CACHE_GLOB) if p.is_file()]
    market = root / _MARKETPLACE
    if market.is_file():
        found.append(market)
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def find_engine(explicit: str | None = None, home: Path | None = None) -> Path:
    """The engine to read the rules from: --engine, then $BITRANOX_MEMORY_ENGINE, then newest."""
    for raw in (explicit, os.environ.get("BITRANOX_MEMORY_ENGINE")):
        if raw:
            path = Path(raw).expanduser()
            if not path.is_file():
                raise EngineNotFound(f"no memory_engine.py at {path}")
            return path
    found = engine_candidates(home)
    if not found:
        raise EngineNotFound(
            "no memory_engine.py found; pass --engine <path> or set BITRANOX_MEMORY_ENGINE")
    return found[0]


def load_rules(engine: Path) -> EngineRules:
    """Import the engine's lint modules and bind the LIVE caps and predicates."""
    hooks_dir = str(Path(engine).resolve().parent)
    sys.path.insert(0, hooks_dir)
    # Drop any previously-imported copy first. Both names are plain top-level modules, so a second
    # call with a DIFFERENT engine dir would otherwise get the cached first one and report that
    # engine's caps under this engine's path - the exact silent-wrong-answer this tool exists to
    # stop. Nothing else in this process imports them, so evicting them is safe.
    for name in ("uuid_store", "capture_constraints"):
        sys.modules.pop(name, None)
    importlib.invalidate_caches()
    try:
        us = importlib.import_module("uuid_store")
        cc = importlib.import_module("capture_constraints")
    except ImportError as exc:
        raise EngineNotFound(f"engine at {engine} is not importable: {exc}") from exc
    return EngineRules(
        soft_max=us.HOOK_SOFT_MAX,
        hard_max=us.HOOK_HARD_MAX,
        escalate_at=us.RECURRENCE_ESCALATE_AT,
        over_soft=us.hook_over_budget,
        over_hard=us.hook_over_hard_cap,
        missing_trigger=us.hook_missing_trigger,
        advise=cc.advise,
        recurrence=us.recurrence_count,
        parse_index=us.parse_pointer_index,
        engine_path=Path(engine).resolve(),
    )


# ---- reading a stored fact ----------------------------------------------------------------------

def read_fact(slug: str, start: Path, rules: EngineRules, level: Path | None = None) -> Fact:
    """The stored fact for `slug`, found by walking up from `start`. Raises UnknownFact.

    The pointer is parsed with the ENGINE's own parser rather than a local regex: a slug may carry
    a dot, and a hand-rolled `[a-z0-9-]+` does not merely truncate such a slug, it fails to match
    the line at all, so the fact reads as absent.

    Borrowing the parser means borrowing its Pointer, whose fields are `__slots__` and move with
    the plugin - reading one it has dropped raises on every fact in the store, and a fake pointer
    in a test cannot see that. `test_read_fact_only_uses_attributes_the_live_pointer_actually_carries`
    is what holds this to the installed engine.
    """
    anchor = anchor_dir(start)
    levels = [Path(level).resolve()] if level else chain_levels(start)
    for lvl in levels:
        try:
            text = (lvl / LEVEL_FILE).read_text(encoding="utf-8")
        except OSError:
            continue
        _scope, pointers = rules.parse_index(text)
        for ptr in pointers:
            if ptr.slug != slug:
                continue
            path = body_file(anchor, slug)
            try:
                body = path.read_text(encoding="utf-8")
            except OSError:
                body = ""
            return Fact(slug=slug, level=lvl, anchor=anchor, title=ptr.title,
                        hook=ptr.hook or "", pin=bool(ptr.pin),
                        body=body, body_path=path)
    raise UnknownFact(f"no pointer for {slug!r} at any level from {Path(start).resolve()}")


# ---- recomposition ------------------------------------------------------------------------------

def stage_text(stage: Path, name: str, text: str) -> Path:
    """Write one staged input file and return its path.

    Staging is not a convenience: the engine takes the hook via --hook-file precisely so a
    real-length hook never has to travel as a shell argument, where `$(cat f)` would be a command
    substitution the guard denies.
    """
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=True)
    path = stage / name
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return path


def _in_a_venv(interpreter: Path) -> bool:
    """True when this interpreter belongs to a virtualenv (<venv>/bin/python*, <venv>/pyvenv.cfg)."""
    return (Path(interpreter).parent.parent / "pyvenv.cfg").is_file()


def default_python(path_env: str | None = None) -> str:
    """The interpreter to launch the engine with: the first NON-VENV python3 on PATH.

    Neither of the obvious answers works. `sys.executable` under `uv run` is an EPHEMERAL build
    venv under the uv cache, so a --dry-run command printed for a human to paste names a path that
    is already gone; and a bare `shutil.which("python3")` finds that same venv, because uv puts it
    first on PATH. So venv interpreters are skipped explicitly. The engine is pure stdlib, so any
    real python3 runs it.
    """
    raw = os.environ.get("PATH", "") if path_env is None else path_env
    for entry in raw.split(os.pathsep):
        if not entry:
            continue
        for name in ("python3", "python3.exe"):
            cand = Path(entry) / name
            if cand.is_file() and os.access(cand, os.X_OK) and not _in_a_venv(cand):
                return str(cand)
    base = Path(sys.base_prefix) / "bin" / "python3"
    return str(base) if base.is_file() else sys.executable


def engine_argv(fact: Fact, engine: Path, *, hook_path: Path | None, body_path: Path | None,
                title: str | None, python: str | None = None) -> list[str]:
    """The exact engine invocation for this recomposition. PURE.

    The VERB comes from the stored pin flag, never from the caller: an ordinary `add` against a
    pinned fact raises before writing anything, and `amend-pinned` is the one deliberate way
    through. Getting that wrong costs a refusal, not damage, but it costs it every time.
    """
    argv = [python or default_python(), str(engine),
            "amend-pinned" if fact.pin else "add",
            "--proj", str(fact.level), "--slug", fact.slug]
    if fact.pin:
        if title:
            argv += ["--title", title]
    else:
        argv += ["--title", title or fact.title]
    if hook_path:
        argv += ["--hook-file", str(hook_path)]
    if body_path:
        argv += ["--body-file", str(body_path)]
    return argv


# ---- output -------------------------------------------------------------------------------------

def _emit(as_json: bool, command: str, ok: bool, data, skipped: list[str], text: str) -> None:
    """One envelope shape for every verb; the text rendering is the same content, unparsed."""
    if as_json:
        print(json.dumps({"ok": ok, "command": command, "data": data, "skipped": skipped},
                         indent=2))
    else:
        print(text)


def _fact_data(fact: Fact, verdict: Verdict, rules: EngineRules) -> dict:
    return {
        "slug": fact.slug,
        "level": str(fact.level),
        "anchor": str(fact.anchor),
        "title": fact.title,
        "pinned": fact.pin,
        "engine_verb": "amend-pinned" if fact.pin else "add",
        "hook": fact.hook,
        "hook_chars": verdict.length,
        "soft_max": rules.soft_max,
        "hard_max": rules.hard_max,
        "body_path": str(fact.body_path),
        "body_chars": len(fact.body),
        "body_description": fact.body_description,
        "hook_in_sync": fact.hook_in_sync,
        "accepted": verdict.accepted,
        "refusals": verdict.refusals,
        "advisories": verdict.advisories,
    }


def _render_fact(data: dict, body: str, show_body: bool) -> str:
    lines = [
        f"slug        {data['slug']}",
        f"level       {data['level']}",
        f"title       {data['title']}",
        f"pinned      {data['pinned']}  (engine verb: {data['engine_verb']})",
        (f"hook        {data['hook_chars']} chars "
         f"(soft {data['soft_max']}, hard {data['hard_max']})"),
        "",
        data["hook"],
        "",
        f"body        {data['body_path']}  ({data['body_chars']} chars)",
    ]
    if not data["hook_in_sync"]:
        lines += ["", "! the body's description: has DRIFTED from the pointer hook:",
                  f"  body says: {data['body_description']}"]
    for line in data["refusals"]:
        lines.append(f"! refused: {line}")
    for line in data["advisories"]:
        lines.append(f"~ advisory: {line}")
    if show_body:
        lines += ["", "---- body ----", body.rstrip("\n")]
    return "\n".join(lines)


# ---- verbs --------------------------------------------------------------------------------------

def _resolve_text(inline: str | None, path: str | None, flag: str) -> str | None:
    """One text input from either the inline flag or a file; never both, never guessed."""
    if inline is not None and path:
        raise BadInput(f"pass {flag} or {flag}-file, not both")
    if path:
        try:
            return Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise BadInput(f"cannot read {path}: {exc}") from exc
    return inline


def cmd_show(args, rules: EngineRules) -> int:
    fact = read_fact(args.slug, Path(args.start), rules,
                     level=Path(args.level) if args.level else None)
    verdict = judge_hook(fact.hook, fact.body, rules)
    data = _fact_data(fact, verdict, rules)
    if args.body:
        data["body"] = fact.body
    _emit(args.as_json, "show", True, data, [],
          _render_fact(data, fact.body, args.body))
    return 0


def cmd_check(args, rules: EngineRules) -> int:
    hook = _resolve_text(args.hook, args.hook_file, "--hook")
    if hook is None:
        raise BadInput("give a hook with --hook or --hook-file")
    body = _resolve_text(None, args.body_file, "--body") or ""
    skipped = [] if args.body_file else ["body advisories (no --body-file given)"]
    verdict = judge_hook(hook, body, rules)
    data = {"hook_chars": verdict.length, "soft_max": rules.soft_max,
            "hard_max": rules.hard_max, "accepted": verdict.accepted,
            "refusals": verdict.refusals, "advisories": verdict.advisories,
            "engine": str(rules.engine_path) if rules.engine_path else None}
    text = [f"{verdict.length} chars (soft {rules.soft_max}, hard {rules.hard_max}) - "
            + ("the engine would ACCEPT this hook" if verdict.accepted
               else "the engine would REFUSE this hook")]
    text += [f"! refused: {line}" for line in verdict.refusals]
    text += [f"~ advisory: {line}" for line in verdict.advisories]
    _emit(args.as_json, "check", verdict.accepted, data, skipped, "\n".join(text))
    return 0 if verdict.accepted else 1


def cmd_apply(args, rules: EngineRules) -> int:
    fact = read_fact(args.slug, Path(args.start), rules,
                     level=Path(args.level) if args.level else None)
    hook = _resolve_text(args.hook, args.hook_file, "--hook")
    body = _resolve_text(None, args.body_file, "--body")
    if hook is None and body is None and not args.title:
        raise BadInput("nothing to change: give --hook/--hook-file, --body-file or --title")
    hook = fact.hook if hook is None else hook.strip()
    verdict = judge_hook(hook, body if body is not None else fact.body, rules)
    if not verdict.accepted:
        data = {"slug": fact.slug, "level": str(fact.level), "accepted": False,
                "hook_chars": verdict.length, "refusals": verdict.refusals,
                "advisories": verdict.advisories}
        _emit(args.as_json, "apply", False, data, ["the engine was not invoked"],
              "\n".join([f"! refused: {line}" for line in verdict.refusals]
                        + ["the engine was not invoked; nothing was staged or written"]))
        return 1

    stage = Path(args.stage_dir) if args.stage_dir else Path(
        tempfile.mkdtemp(prefix="factedit-"))
    hook_path = stage_text(stage, f"{fact.slug}.hook.txt", hook)
    skipped: list[str] = []
    body_path = None
    if body is None:
        skipped.append("body unchanged (the engine keeps the stored one and syncs its description)")
    else:
        body_path = stage_text(stage, f"{fact.slug}.body.md", body)
    argv = engine_argv(fact, rules.engine_path, hook_path=hook_path, body_path=body_path,
                       title=args.title, python=args.python)

    data = {"slug": fact.slug, "level": str(fact.level), "pinned": fact.pin,
            "engine_verb": "amend-pinned" if fact.pin else "add",
            "stage_dir": str(stage), "hook_file": str(hook_path),
            "body_file": str(body_path) if body_path else None,
            "hook_chars": verdict.length, "accepted": True,
            "advisories": verdict.advisories, "argv": argv,
            "command": shlex.join(argv), "dry_run": bool(args.dry_run)}
    if args.dry_run:
        skipped.append("the engine was not invoked (--dry-run)")
        _emit(args.as_json, "apply", True, data, skipped,
              "\n".join([f"~ advisory: {a}" for a in verdict.advisories]
                        + [f"staged  {hook_path}"]
                        + ([f"staged  {body_path}"] if body_path else [])
                        + ["", shlex.join(argv)]))
        return 0

    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False)
    data["engine_stdout"] = (proc.stdout or "").strip()
    data["engine_returncode"] = proc.returncode
    if proc.stderr:
        # Operational noise from the engine, never part of the parsed stream.
        print(proc.stderr.rstrip("\n"), file=sys.stderr)
    ok = proc.returncode == 0
    data["accepted"] = ok
    _emit(args.as_json, "apply", ok, data, skipped,
          "\n".join([f"~ advisory: {a}" for a in verdict.advisories]
                    + [data["engine_stdout"] or "(engine printed nothing)"]))
    return 0 if ok else 1


# ---- CLI ----------------------------------------------------------------------------------------

def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--engine", default=None, help="path to memory_engine.py (default: newest found)")
    p.add_argument("--json", action="store_true", dest="as_json", help="emit a JSON envelope")


def _add_target(p: argparse.ArgumentParser) -> None:
    p.add_argument("--slug", required=True, help="the fact's identity")
    p.add_argument("--from", dest="start", default=".",
                   help="a dir inside the tree; the chain is walked up from here (default cwd)")
    p.add_argument("--level", default=None,
                   help="force the level that owns the pointer, skipping the chain walk")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    sh = sub.add_parser("show", help="read a fact: its hook, its body, and how the engine reads it")
    _add_target(sh)
    sh.add_argument("--body", action="store_true", help="also print the body")
    _add_common(sh)

    ck = sub.add_parser("check", help="would the engine accept this hook?")
    ck.add_argument("--hook", default=None, help="the drafted hook, inline")
    ck.add_argument("--hook-file", default=None, help="the drafted hook, from a file")
    ck.add_argument("--body-file", default=None,
                    help="the body it will ship with, so body advisories are checked too")
    _add_common(ck)

    ap_ = sub.add_parser("apply", help="recompose a fact through the engine (add or amend-pinned)")
    _add_target(ap_)
    ap_.add_argument("--hook", default=None, help="the new hook, inline (omit to keep the stored one)")
    ap_.add_argument("--hook-file", default=None, help="the new hook, from a file")
    ap_.add_argument("--body-file", default=None,
                     help="the new body (omit to keep the stored one)")
    ap_.add_argument("--title", default=None, help="a new title (omit to keep the stored one)")
    ap_.add_argument("--stage-dir", default=None,
                     help="where to write the staged hook/body files (default: a temp dir)")
    ap_.add_argument("--dry-run", action="store_true",
                     help="stage the files and print the engine command without running it")
    ap_.add_argument("--python", default=None,
                     help="interpreter to launch the engine with (default: python3 from PATH)")
    _add_common(ap_)
    return ap


_VERBS = {"show": cmd_show, "check": cmd_check, "apply": cmd_apply}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rules = load_rules(find_engine(args.engine))
        return _VERBS[args.cmd](args, rules)
    except FactEditError as exc:
        payload = {"ok": False, "command": args.cmd, "data": None,
                   "skipped": [], "error": f"{type(exc).__name__}: {exc}"}
        if args.as_json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1 if isinstance(exc, UnknownFact) else 2


if __name__ == "__main__":
    sys.exit(main())
