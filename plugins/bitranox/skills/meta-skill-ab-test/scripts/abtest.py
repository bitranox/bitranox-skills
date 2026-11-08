#!/usr/bin/env python3
"""abtest: A/B test a skill against its variants on one real task in the real repository.

Subcommands (every one takes --json; exit 0 yes / 1 no / 2 could not run):
  init <run_dir> [--repo --base --skills-ref --skill]   write the profile, task and PREREG skeletons
  seal <run_dir>                                       validate and commit them; fixes the weights
  run <run_dir> [--dry-run] [--only ARM] ...           the serial interleaved arms (resumes)
  score <run_dir>                                      per-arm scores, void rules, store-change flags
  prune-run <run_dir>                                  delete the run's branches in the workpiece

The run dir is its own git repo so the pre-registration is append-only. Its journal.jsonl records
every arm attempt; `run` skips an arm the journal says ran, and sets aside (renames) the directory
and branch of an attempt that did not finish (paused, interrupted, failed, killed, or a dry run
before a live one) before running that arm again; the credentials copy and the worktree such an
attempt left are removed first, after its transcripts and any uncommitted work are copied into
the arm dir (as every arm's are). run refuses inputs that changed since the seal, and every
arm's floor runs the acceptance suite as sealed. A session that ends the way the CLI reports a refused request (a
login-looking failure, only CLI synthetic messages, or a usage-limit notice) is the only time the
out-of-band login probe is asked; its answer pauses the run, names no cause, and the arm runs
again on resume rather than being voided (design S4).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any

if sys.platform != "win32":
    # flock for the run dir lock. Windows has no fcntl; the suite still imports this module there.
    import fcntl

import abarm
import abguard
import abscore
import abtrace
from _ablib import (
    EXIT_ERROR,
    EXIT_NO,
    EXIT_YES,
    append_jsonl,
    envelope,
    git,
    git_env,
    rotated_schedule,
    run,
    sha256_file,
    utc_now,
)
from abprofile import SANDBOX_BWRAP_KINDS, SANDBOX_MISSING, SKELETON, Profile, ProfileError, load_profile
from abstream import OPUS_PREFIX, SYNTHETIC_REASON_PREFIX

__all__ = [
    "OPUS_PREFIX",
    "WEIGHTS",
    "JournalError",
    "RunContext",
    "RunRefused",
    "build_parser",
    "default_credentials",
    "default_skills_repo",
    "load_journal",
    "main",
    "record",
    "run_arm",
]

LoginCheck = Callable[[Path], str]
WEIGHTS = {"correctness": 0.30, "task_coverage": 0.25, "tests": 0.20, "beyond_plan_fixes": 0.10,
           "readability": 0.10, "scope_creep": 0.05}


def default_credentials() -> Path:
    """The login `run` checks and installs from when --credentials is not given: the one in the
    user's Claude config dir (abarm.user_config_dir, which follows CLAUDE_CONFIG_DIR). Per call."""
    return abarm.user_config_dir() / ".credentials.json"


def default_skills_repo() -> Path:
    """The marketplace clone every install has, in the user's Claude config dir. Per call."""
    return abarm.user_config_dir() / "plugins" / "marketplaces" / "bitranox-skills"


PREREG_SKELETON = """# Pre-registration

## Question
<what the variants are expected to change, in one sentence>

## Hypotheses
<H1 ... per variant: direction and the criterion it should move>

## Decision rule
Pairwise blind judge (design S2), A/B swap tie rule, control first then finalists; labels per design S5.4.
"""
GITIGNORE = ("frozen/\narms/*/cfg\narms/*/home\narms/*/stream.jsonl\narms/*/bundle.git\narms/*/guard\n"
             "arms/*/transcripts\narms/*/uncommitted.patch\narms/*/untracked.tar\njournal.jsonl\njournal.torn\n"
             "run.lock\n")
# The file `run` holds an exclusive flock on while it runs, the holder's pid written in it. Two runs
# on one run dir raced before it: the second swept the first's live config dir and set its arm aside.
# flock is released by the kernel when the holder dies, however it dies, so no pid is ever stale.
LOCK_FILE = "run.lock"
# Where an arm's session transcripts (copied out of its config dir before that is deleted) go.
TRANSCRIPTS = "transcripts"
JOURNAL, TORN = "journal.jsonl", "journal.torn"
# The run dir's copy of the acceptance suite, committed at the seal: what every arm's floor runs.
SEALED_DIR = "sealed"
# The run id names branches (abx/<id>/...) and worktree dirs, so it must be a plain ref component.
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
# A live run skips only what really ran; a dry run also skips what an earlier dry run did.
DONE_LIVE, DONE_DRY = ("ran",), ("ran", "dry")
INTERRUPTED = "interrupted"
# The journal step recording that the harness appended .claude/worktrees/ to the workpiece's
# info/exclude ("added") and that prune-run took it out again ("removed").
EXCLUDE_STEP = "exclude"
# What the CLI prints when it calls a failed request a login failure: a bad token (401) and a
# refused or rate-limited request (429) read the same, which is why only the probe can tell.
LOGIN_MARKS = ("not logged in", "/login")
# A CLI notice that the account's usage window is used up ("You've hit your weekly limit").
LIMIT_MARKS = ("usage limit", "weekly limit", "session limit", "hit your", "limit reached")
AUTH_FAILED = "authentication_failed"
# The three ways a session can end that pause the run: what was observed, never a cause.
PAUSE_LOGIN, PAUSE_SYNTHETIC_ONLY, PAUSE_LIMIT = ("a login-looking failure", "only CLI synthetic messages",
                                                  "a usage-limit notice")
# The pause before an arm starts: the login the arm copies would expire before the arm's
# deadline. Refreshing is the user's step (a normal Claude session refreshes the real file); the
# run pauses rather than starting an arm that may lose its login mid-way (design S4: pause, not void).
PAUSE_EXPIRY = "a login that expires before the arm's deadline"
# A seal refuses a PREREG.md still holding a skeleton placeholder; a bare "<" ("cost < 0.10") is prose.
PLACEHOLDER_RE = re.compile(r"<[^>\n]+>")
EPILOG = """[run] sandbox in abtest.toml: "bwrap" runs each live session in a bubblewrap sandbox (writable:
its worktree, home, config dir, the repo's .git; real home hidden; the repo's other worktree
registrations read-only, so an arm's git worktree prune or add cannot touch them); "bwrap-host-proc" is the same with the
host's /proc read-only (an LXC container); "none" opts out, recorded per arm.

[[variant]] remove_skill = true (no dir, no markers): a bare arm, the plugin without the skill under test.
[[variant]] task_file = "task-V1.md": that arm's own prompt (default [workpiece].task_file); seal records
its sha256 per arm, run refuses a changed one, and the journal, result.json and score name it.
[floor] suite_from = "/abs/path": seal copies the acceptance suite from there instead of <repo>/<suite>.
[workpiece] link = [".packages"]: gitignored workpiece paths a fresh worktree lacks (a vendored protoc),
symlinked into every arm's worktree before its session; read-only under bwrap. seal refuses an entry that
is missing, tracked, not ignored, or ignored only by a dir-only pattern (".packages/"): ignore it as
"/.packages".
[run] unattended_note = "...": appended to every arm's prompt alike after a blank line (the bare arm's
too); its sha256 is in each journal row and result.json. score's ended_with_question flags an arm whose
session's last text ends with "?" (it stopped to ask); a flag, never a void.
--json prints one pretty-printed envelope: parse the whole stdout as one JSON document."""
# How much of an arm's last text the question flag shows: its end, where the question is.
QUESTION_SHOWN = 200
SEAL_GIT = ("-c", "user.name=abtest", "-c", "user.email=abtest@localhost", "-c", "commit.gpgsign=false",
            "-c", "core.hooksPath=/dev/null")


class RunRefused(RuntimeError):
    """A precondition of the subcommand is not met; exit 2 with this message."""


class JournalError(RuntimeError):
    """journal.jsonl holds an unparsable line before its last one; it cannot be trusted to resume."""


class UsageError(RuntimeError):
    """The command line does not parse; reported like any other could-not-run."""


@dataclass(frozen=True)
class ArmTask:
    """The prompt one arm is given: its file relative to the run dir, the text and its sha256."""

    file: str
    text: str
    sha256: str


@dataclass(frozen=True)
class RunContext:
    run_dir: Path
    profile: Profile
    tasks: dict[str, ArmTask]
    credentials: Path
    skills_repo: Path
    dry_run: bool
    max_turns: int
    stop_grace_s: float
    sealed_suite: abscore.SealedSuite | None

    @property
    def run_id(self) -> str:
        return self.run_dir.name

    def arm_meta(self, name: str) -> dict[str, Any]:
        """What every journal row and result.json of arm `name` records beside its outcome."""
        task = self.tasks[name]
        note = self.profile.run.unattended_note
        return {"sandbox": self.profile.run.sandbox, "task_file": task.file, "task_sha256": task.sha256,
                "unattended_note_sha256": None if note is None else hashlib.sha256(note.encode("utf-8")).hexdigest()}

    def prompt(self, name: str) -> str:
        """Arm `name`'s task text, then the profile's unattended_note after a blank line when it has one."""
        text, note = self.tasks[name].text, self.profile.run.unattended_note
        if note is None:
            return text
        ended = text if text.endswith("\n") else text + "\n"
        return f"{ended}\n{note}\n"


def _warn(text: str) -> None:
    print(f"abtest: warning: {text}", file=sys.stderr)


def _emit(as_json: bool, command: str, data: dict[str, Any], ok: bool, text: str, skipped: list[str] | None = None) -> None:
    print(envelope(command, data, ok=ok, skipped=skipped) if as_json else text)


# --- the journal ---------------------------------------------------------------------------------

def _parse_journal(path: Path) -> tuple[list[str], list[dict[str, Any]], str | None]:
    """(the good lines, their rows, the torn last line or None); a bad earlier line raises."""
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        if isinstance(row, dict):
            rows.append(row)
        elif i == len(lines) - 1:
            return lines[:-1], rows, line
        else:
            raise JournalError(f"{path}: line {i + 1} is not a JSON object; only a torn LAST line is tolerated")
    return lines, rows, None


def load_journal(run_dir: Path) -> list[dict[str, Any]]:
    """Every journal row; a torn last line (a run killed mid-append) is moved to journal.torn.

    The repair keeps the next append from landing on the torn fragment's line, and the fragment
    is kept beside the journal rather than deleted. It is reported on stderr.

    Raises:
        JournalError: an unparsable line sits before the last one.
    """
    path = run_dir / JOURNAL
    if not path.is_file():
        return []
    good, rows, torn = _parse_journal(path)
    if torn is not None:
        with (run_dir / TORN).open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(torn + "\n")
        tmp = path.with_suffix(".tmp")
        tmp.write_text("".join(ln + "\n" for ln in good), encoding="utf-8", newline="\n")
        os.replace(tmp, path)
        _warn(f"{path}: the last line was torn (a run killed mid-append); moved it to {run_dir / TORN}")
    return rows


def record(run_dir: Path, **row: Any) -> None:
    """Append one journal row stamped with `at`, on a line of its own even after a torn write."""
    path = run_dir / JOURNAL
    if path.is_file() and path.stat().st_size and not path.read_bytes().endswith(b"\n"):
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n")
    append_jsonl(path, dict(row, at=utc_now()))


def _sealed(run_dir: Path) -> bool:
    return any(r.get("step") == "seal" for r in load_journal(run_dir))


def _require_sealed(run_dir: Path) -> None:
    if not _sealed(run_dir):
        raise RunRefused(f"{run_dir} is not sealed; run `abtest.py seal` first")


def _done(run_dir: Path, round_no: int, arm: str, statuses: tuple[str, ...]) -> bool:
    return any(r.get("step") == "arm" and r.get("round") == round_no and r.get("arm") == arm
               and r.get("status") in statuses for r in load_journal(run_dir))


def _run_dir(raw: str) -> Path:
    run_dir = Path(raw).expanduser()
    if not RUN_ID_RE.match(run_dir.name):
        raise RunRefused(f"run dir name {run_dir.name!r} must match {RUN_ID_RE.pattern}: it names branches")
    return run_dir


# --- init and seal -------------------------------------------------------------------------------

def _fill_skeleton(args: argparse.Namespace) -> str:
    text = SKELETON
    for key, value in (("<absolute path of the real repository>", args.repo), ("<40-char sha every arm starts from>", args.base),
                       ("<bitranox-skills sha that carries BITRANOX_MEMORY_WRITES>", args.skills_ref),
                       ("<skill directory name under plugins/bitranox/skills/>", args.skill)):
        if value:
            text = text.replace(key, str(value))
    return text


def _run_branches(repo: Path, run_id: str) -> list[str]:
    """The branches under abx/<run_id>/ in repo: an earlier run of the same id left them."""
    proc = git(repo, "for-each-ref", "--format=%(refname:short)", f"refs/heads/abx/{run_id}/")
    if proc.returncode != 0:
        raise RunRefused(f"cannot list the branches of {repo}: {proc.stderr.strip()}")
    return proc.stdout.split()


def _arm_made_worktrees(repo: Path, run_dir: Path) -> list[tuple[Path, str | None]]:
    """The worktrees of repo registered under run_dir/arms, with each one's branch (None: detached).

    An arm can register a worktree of its own in its home (a parallel node: arms/<label>/home/wt/
    node-8), outside the abx-<run>-<label> namespace and its abx/<run>/ branches. The path under
    the run's own arms dir is what says the run made it; a worktree anywhere else is never listed.
    """
    proc = git(repo, "worktree", "list", "--porcelain")
    if proc.returncode != 0:
        raise RunRefused(f"cannot list the worktrees of {repo}: {proc.stderr.strip()}")
    arms = (run_dir / "arms").resolve()
    found: list[tuple[Path, str | None]] = []
    for block in proc.stdout.split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        path = Path(fields["worktree"]) if "worktree" in fields else None
        if path is not None and path.resolve().is_relative_to(arms):
            found.append((path, fields.get("branch", "").removeprefix("refs/heads/") or None))
    return found


def _refuse_run_id_collision(repo: Path, run_id: str) -> None:
    """Refuse a run id whose branches already exist: its arms would be refused as leftovers, and
    prune-run would delete the other run's branches with this one's."""
    taken = _run_branches(repo, run_id)
    if taken:
        raise RunRefused(f"the workpiece {repo} already has {len(taken)} branch(es) under abx/{run_id}/ "
                         f"(first: {taken[0]}): pick another run dir name, or prune the old run first")


def cmd_init(args: argparse.Namespace) -> int:
    run_dir = _run_dir(args.run_dir)
    if run_dir.exists():
        _emit(args.json, "init", {"run_dir": str(run_dir)}, False, f"{run_dir} already exists; refusing to overwrite")
        return EXIT_NO
    if args.repo:
        _refuse_run_id_collision(Path(args.repo).expanduser(), run_dir.name)
    (run_dir / "variants" / "V1").mkdir(parents=True)
    (run_dir / "abtest.toml").write_text(_fill_skeleton(args), encoding="utf-8")
    (run_dir / "task.md").write_text("", encoding="utf-8")
    (run_dir / "PREREG.md").write_text(PREREG_SKELETON, encoding="utf-8")
    (run_dir / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    proc = git(run_dir, "init", "-q", "-b", "main")
    if proc.returncode != 0:
        raise RunRefused(f"git init failed in {run_dir}: {proc.stderr.strip()}")
    _emit(args.json, "init", {"run_dir": str(run_dir)}, True,
          f"initialised {run_dir}: fill abtest.toml, task.md, PREREG.md and variants/, then seal")
    return EXIT_YES


def _read_text(path: Path) -> str:
    """A run-dir text file the user wrote, as UTF-8.

    Raises:
        RunRefused: the file is not valid UTF-8 (a traceback would name no file).
        OSError: the file cannot be read.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RunRefused(f"{path} is not UTF-8 text ({exc.reason} at byte {exc.start}); re-save it as UTF-8") from exc


def _read_or_empty(path: Path) -> str:
    return _read_text(path) if path.is_file() else ""


def _seal_problems(run_dir: Path, profile: Profile) -> list[str]:
    problems = []
    # Checked here, not only before a live run: abtest.toml is frozen at the seal, so a profile
    # sealed without the key could never run a live arm.
    if profile.run.sandbox is None:
        problems.append(SANDBOX_MISSING)
    for task_file in profile.task_files():
        if not _read_or_empty(run_dir / task_file).strip():
            problems.append(f"{task_file} is missing or empty")
    prereg = _read_or_empty(run_dir / "PREREG.md")
    if not prereg.strip() or PLACEHOLDER_RE.search(prereg):
        problems.append("PREREG.md is empty or still holds a <placeholder>")
    for v in profile.variants:
        if v.dir is None:
            continue  # a remove_skill variant: the arm runs without the skill, nothing to overlay
        if not (run_dir / v.dir).is_dir() or not any(p.is_file() for p in (run_dir / v.dir).rglob("*")):
            problems.append(f"variants/{v.name}: {v.dir} holds no file")
    problems += [p for entry in profile.workpiece.link if (p := _link_problem(profile.workpiece.repo, entry))]
    return problems


def _link_problem(repo: Path, entry: str) -> str | None:
    """Why workpiece.link `entry` cannot be linked into an arm's worktree; None when it can.

    Only ignored build output is linkable: a tracked path is in every worktree already, and an
    unignored one would show as the arm's own work. In a worktree the entry is a symlink, which a
    dir-only pattern (`name/`) does not match, so the entry must be ignored AS a symlink;
    link_paths checks that again in each worktree.
    """
    if not (repo / entry).exists():
        return f"workpiece.link: {entry} does not exist in the workpiece {repo}"
    if git(repo, "ls-files", "--", entry).stdout.strip():
        return f"workpiece.link: {entry} is tracked by git; a worktree has it already"
    # -q decides; -v alone would also count a matching negated (!) pattern as ignored.
    if git(repo, "check-ignore", "-q", "--no-index", "--", entry).returncode != 0:
        return f"workpiece.link: {entry} is not ignored by git; ignore it as /{entry} (e.g. in .git/info/exclude)"
    if not _ignored_as_symlink(repo, entry):
        # -v prints <source>:<line>:<pattern><TAB><path>: the pattern that ignores the directory.
        verbose = git(repo, "check-ignore", "-v", "--no-index", "--", entry).stdout
        pattern = verbose.split("\t", 1)[0].split(":", 2)[-1]
        return (f"workpiece.link: {entry} is ignored only as a directory ({pattern}), so its symlink in a "
                f"worktree would not be; also ignore it as /{entry}, without the trailing slash")
    return None


def _ignored_as_symlink(repo: Path, entry: str) -> bool:
    """Would git ignore `entry` where it is a symlink, as in an arm's worktree? Nothing is written to repo.

    git asks the filesystem whether a path is a directory, so the question is put to a scratch
    work tree that holds a symlink at `entry` and copies of the .gitignore files on its way; the
    repository's own info/exclude and core.excludesFile apply through --git-dir as usual.
    """
    git_dir = git(repo, "rev-parse", "--absolute-git-dir").stdout.strip()
    with tempfile.TemporaryDirectory(prefix="abtest-link-") as tmp:
        scratch = Path(tmp)
        parts = Path(entry).parts
        for depth in range(len(parts)):
            source = repo.joinpath(*parts[:depth], ".gitignore")
            if source.is_file():
                target = scratch.joinpath(*parts[:depth], ".gitignore")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        link = scratch / entry
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(repo / entry)
        proc = run(["git", "--git-dir", git_dir, "--work-tree", str(scratch), "-C", str(scratch),
                    "check-ignore", "-q", "--no-index", "--", entry], env=git_env())
    return proc.returncode == 0


def _seal_suite(run_dir: Path, profile: Profile) -> str | None:
    """Copy the acceptance suite into sealed/ (committed with the seal); its sha256, None without a suite.

    The copy, not the workpiece's file, is what every arm's floor runs: the workpiece's suite may
    be untracked (then no worktree has it) or edited later, and an arm could edit its own. The
    source is floor.suite_from when set (a suite kept outside the workpiece, which then stays
    untouched), else <workpiece repo>/<floor.suite>; the copy lands at sealed/<floor.suite> either way.
    """
    if not profile.floor.suite:
        return None
    if profile.floor.suite_from is not None:
        suite_path = Path(profile.floor.suite_from)
        if not suite_path.is_file():
            raise RunRefused(f"floor.suite_from {suite_path} does not exist or is not a file")
    else:
        suite_path = profile.workpiece.repo / profile.floor.suite
        if not suite_path.is_file():
            raise RunRefused(f"floor.suite {suite_path} does not exist at the workpiece "
                             "(a suite kept elsewhere is named by floor.suite_from)")
    sealed = run_dir / SEALED_DIR / profile.floor.suite
    sealed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(suite_path, sealed)
    return sha256_file(sealed)


def _task_stamp(run_dir: Path, profile: Profile) -> dict[str, dict[str, str]]:
    """{arm name: {"file", "sha256"}} of the prompt each arm is given; the seal records it."""
    return {name: {"file": f, "sha256": sha256_file(run_dir / f)}
            for name, f in ((n, profile.task_file_for(n)) for n in profile.arm_names())}


def _commit_seal(run_dir: Path, stamp: dict[str, Any]) -> str:
    """Append the stamp to PREREG.md and commit the inputs, then journal the seal with that commit.

    The journal row comes AFTER the commit because it names the commit (a committed file cannot
    name the commit that adds it); journal.jsonl is gitignored, the run's own output. A failed
    commit undoes the PREREG.md append and the staging. Returns the seal commit.
    """
    prereg = run_dir / "PREREG.md"
    before = _read_text(prereg)
    with prereg.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n## Sealed\n\n```json\n" + json.dumps(stamp, indent=1, sort_keys=True) + "\n```\n")
    git(run_dir, "add", "-A")
    proc = git(run_dir, *SEAL_GIT, "commit", "-q", "-m", "seal")
    if proc.returncode != 0:
        prereg.write_text(before, encoding="utf-8")
        git(run_dir, "reset", "-q")
        shutil.rmtree(run_dir / SEALED_DIR, ignore_errors=True)
        raise RunRefused(f"seal commit failed: {proc.stderr.strip()}")
    commit = _git_out(run_dir, "rev-parse", "--verify", "-q", "HEAD").strip()
    record(run_dir, step="seal", round=0, arm="", status="sealed", commit=commit, suite_sha256=stamp["suite_sha256"],
           suite_from=stamp["suite_from"], task_files=stamp["task_files"])
    return commit


def cmd_seal(args: argparse.Namespace) -> int:
    run_dir = _run_dir(args.run_dir)
    if _sealed(run_dir):
        _emit(args.json, "seal", {}, False, f"{run_dir} is already sealed; amendments are appended to PREREG.md and committed")
        return EXIT_NO
    profile = load_profile(run_dir / "abtest.toml")
    _refuse_run_id_collision(profile.workpiece.repo, run_dir.name)
    problems = _seal_problems(run_dir, profile)
    if problems:
        raise RunRefused("; ".join(problems))
    stamp = {"sealed_at": utc_now(), "weights": WEIGHTS, "suite_sha256": _seal_suite(run_dir, profile), "arms": profile.arm_names(),
             "n": profile.run.n, "warmth_tolerance": profile.run.warmth_tolerance,
             "task_files": _task_stamp(run_dir, profile), "suite_from": profile.floor.suite_from}
    commit = _commit_seal(run_dir, stamp)
    _emit(args.json, "seal", dict(stamp, commit=commit), True, f"sealed {run_dir}: {len(profile.arm_names())} arms x {profile.run.n} rounds")
    return EXIT_YES


# --- one arm -------------------------------------------------------------------------------------

def _paths(ctx: RunContext, label: str) -> tuple[Path, Path, str]:
    """(arm dir, worktree path, branch) of one arm."""
    ws = ctx.profile.workpiece.repo / ".claude" / "worktrees" / f"abx-{ctx.run_id}-{label}"
    return ctx.run_dir / "arms" / label, ws, f"abx/{ctx.run_id}/{label}"


def _guard_after(result: dict[str, Any], guard_dir: Path) -> None:
    """Verify only a snapshot that was taken: a missing manifest would read as no change."""
    guard = result["guard"]
    if guard.get("taken"):
        result["guard_changes"] = abguard.verify(guard_dir)
    else:
        result["guard_changes"] = []
        result["guard_skipped"] = guard.get("skipped")


def _session_argv(ctx: RunContext, name: str, frozen: abarm.Frozen, ws: Path, home: Path, cfg: Path) -> list[str]:
    """claude_argv with arm `name`'s prompt, behind the bubblewrap prefix when the profile names a bwrap sandbox."""
    argv = abarm.claude_argv(ctx.prompt(name), ctx.max_turns)
    sandbox = ctx.profile.run.sandbox
    if sandbox not in SANDBOX_BWRAP_KINDS:
        return argv
    read_only = (*abarm.home_link_targets(home, ctx.profile.run.home_links), ctx.profile.workpiece.repo, frozen.path)
    mounts = abarm.SandboxMounts(ws=ws, home=home, cfg=cfg, git_common_dir=abarm.git_common_dir(ws),
                                 real_home=Path.home(), read_only=read_only)
    return abarm.sandbox_argv(mounts, sandbox=sandbox) + argv


def _arm_steps(ctx: RunContext, result: dict[str, Any], frozen: abarm.Frozen, label: str) -> None:
    p = ctx.profile
    arm_dir, ws, branch = _paths(ctx, label)
    cfg = arm_dir / "cfg"
    home = abarm.arm_home(arm_dir, p.run.home_links)
    env = abarm.arm_env(cfg, home, p.run.env_keep)
    result["install"] = abarm.install_plugin(cfg, frozen, ctx.credentials, env)
    _ignore_worktrees(ctx)
    result["worktree"] = abarm.make_worktree(p.workpiece.repo, p.workpiece.base, branch, ws, copy_untracked_claude_md=True)
    result["linked"] = abarm.link_paths(p.workpiece.repo, ws, p.workpiece.link)
    result["guard"] = abguard.snapshot(ws, arm_dir / "guard")
    if not ctx.dry_run:
        result.update(abarm.dispatch(arm_dir, ws, env, _session_argv(ctx, result["name"], frozen, ws, home, cfg),
                                     max_tokens=p.run.max_tokens, deadline_s=p.run.deadline_s,
                                     stop_grace_s=ctx.stop_grace_s))
    # Right after the session, before the floor writes into the worktree (build output, the suite).
    result["uncommitted"] = _save_uncommitted(ctx, arm_dir, ws)
    if result["uncommitted"].get("error"):
        _warn(f"{label}: {result['uncommitted']['error']}")
    _guard_after(result, arm_dir / "guard")
    result["floor"] = abscore.run_floor(ws, p, arm_dir, sealed_suite=ctx.sealed_suite)
    result["bundle_commits"] = abarm.bundle(ws, p.workpiece.base, arm_dir / "bundle.git")


def _ignore_worktrees(ctx: RunContext) -> None:
    """Make sure .claude/worktrees/ is ignored; journal it at once when the harness added the line.

    The line is shared by every arm (only the first one adds it), so whether the harness added it
    belongs to the run, not to an arm's state file: prune-run removes it only when this row says so.
    """
    if abarm.ensure_worktrees_ignored(ctx.profile.workpiece.repo):
        record(ctx.run_dir, step=EXCLUDE_STEP, round=0, arm="", status="added")


def _save_uncommitted(ctx: RunContext, arm_dir: Path, ws: Path) -> dict[str, Any]:
    """abarm.save_uncommitted with the profile's cache paths and the harness's own CLAUDE.md copy skipped.

    Never raises: a save that fails is recorded as {"left_work": None, "error": ...}, because
    failing the arm for it would make a paid session run again on resume.
    """
    repo = ctx.profile.workpiece.repo
    try:
        return abarm.save_uncommitted(ws, arm_dir, skip_prefixes=ctx.profile.floor.cache_paths,
                                      harness_copies={"CLAUDE.md": repo / "CLAUDE.md"})
    except (abarm.ArmError, OSError) as exc:
        return {"left_work": None, "error": f"save_uncommitted: {exc}"}


def _salvage(ctx: RunContext, result: dict[str, Any], arm_dir: Path, ws: Path) -> list[str]:
    """Copy out what the arm's cleanup would destroy; the errors, never raised.

    The transcripts live in the config dir delete_cfg removes, and work left uncommitted lives in
    the worktree prune removes. The worktree is read only when it is the harness's own (make_worktree
    returned it, or git lists it at this arm's path): a directory git does not know is never read.
    The uncommitted work is saved here only when the arm did not get as far as saving it itself
    (an error or an interrupt before or during the session).
    """
    errors = []
    try:
        result["transcripts"] = abarm.save_transcripts(arm_dir / "cfg", arm_dir / TRANSCRIPTS)
    except OSError as exc:
        errors.append(f"save_transcripts: {exc}")
    if "uncommitted" in result:
        return errors
    try:
        ours = ws.is_dir() and ("worktree" in result or _harness_worktree_left(ctx.profile.workpiece.repo, ws))
    except OSError as exc:
        return [*errors, f"save_uncommitted: {exc}"]
    if ours:
        result["uncommitted"] = _save_uncommitted(ctx, arm_dir, ws)
        errors += [result["uncommitted"]["error"]] if result["uncommitted"].get("error") else []
    return errors


def _sweep_cfgs(run_dir: Path) -> list[str]:
    """Delete every arms/*/cfg (transcripts copied out first); the config dirs deleted.

    Only a hard kill (OOM, power loss) leaves one, holding a credentials copy. _set_aside removes
    it when its arm runs again, but `run --only V1` never visits r1-C and prune-run visits no arm
    dir at all, so run and prune-run sweep every arm dir, set-aside attempts included.
    """
    swept = []
    for cfg in sorted((run_dir / "arms").glob("*/cfg")):
        try:
            abarm.save_transcripts(cfg, cfg.parent / TRANSCRIPTS)
        except OSError as exc:
            _warn(f"{cfg}: the transcripts could not be copied out before the delete: {exc}")
        abarm.delete_cfg(cfg)
        swept.append(str(cfg))
    return swept


def _registered(repo: Path, ws: Path) -> bool:
    """Whether git lists ws as a worktree of repo (compared by real path)."""
    out = git(repo, "worktree", "list", "--porcelain").stdout
    real = os.path.realpath(ws)
    return any(os.path.realpath(line[len("worktree "):]) == real for line in out.splitlines() if line.startswith("worktree "))


def _harness_worktree_left(repo: Path, ws: Path) -> bool:
    """Whether the harness's own worktree, or the hooks dir beside it, is left at this arm's path.

    ws sits in the harness's abx-<run>-<label> namespace, so a registered worktree or a
    <ws>.githooks there was made by an earlier attempt of this arm. A plain directory git does
    not know is not: make_worktree refuses it and names the cleanup.
    """
    hooks = ws.parent / f"{ws.name}.githooks"
    return hooks.exists() or hooks.is_symlink() or _registered(repo, ws)


def _cleanup(ctx: RunContext, result: dict[str, Any], frozen: abarm.Frozen | None, ws: Path) -> dict[str, Any]:
    """Prune the worktree this arm made and release its frozen checkout; never raises, errors are listed.

    The worktree is pruned when make_worktree returned it, and also when it was interrupted after
    `worktree add` (the path is registered, or its hooks dir exists, though "worktree" is not in
    the result yet). prune itself handles a directory that is already gone.
    """
    out: dict[str, Any] = {"prune": None, "frozen_released": False, "errors": []}
    repo = ctx.profile.workpiece.repo
    try:
        if "worktree" in result or _harness_worktree_left(repo, ws):
            out["prune"] = abarm.prune(ws, repo, ctx.profile.floor.cache_paths)
    except (abarm.ArmError, OSError) as exc:
        out["errors"].append(f"prune: {exc}")
    try:
        if frozen is not None:
            abarm.release_frozen(frozen, ctx.skills_repo)
            out["frozen_released"] = True
    except (abarm.ArmError, OSError) as exc:
        out["errors"].append(f"release_frozen: {exc}")
    return out


def _write_result(arm_dir: Path, result: dict[str, Any]) -> None:
    (arm_dir / "result.json").write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")


def run_arm(ctx: RunContext, round_no: int, name: str) -> dict[str, Any]:
    """One arm, start to finish; the result dict is also written to arms/r<round>-<name>/result.json.

    result.json is written whatever happens, a Ctrl-C included (stop_reason "interrupted", which
    the scorer voids). On every path the transcripts are copied out of the config dir and any
    uncommitted work out of the worktree first; then the credentials copy is deleted (even when
    that copying is interrupted), the worktree pruned and the frozen checkout released, and the
    exception is re-raised.
    """
    label = f"r{round_no}-{name}"
    arm_dir, ws, _ = _paths(ctx, label)
    arm_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"arm": label, "round": round_no, "name": name, "dry_run": ctx.dry_run,
                              **ctx.arm_meta(name)}
    frozen: abarm.Frozen | None = None
    try:
        frozen = abarm.freeze_variant(ctx.run_dir, ctx.profile, name, ctx.skills_repo)
        result["frozen"] = {"ref": frozen.skills_ref, "overlay_written": list(frozen.overlay_written),
                            "skill_removed": frozen.skill_removed, "removed": list(frozen.removed)}
        _arm_steps(ctx, result, frozen, label)
    except KeyboardInterrupt:
        result["session_stop_reason"] = result.get("stop_reason")
        result["stop_reason"] = INTERRUPTED
        raise
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        salvage_errors: list[str] = []
        try:
            salvage_errors = _salvage(ctx, result, arm_dir, ws)
        finally:
            abarm.delete_cfg(arm_dir / "cfg")
        result["cleanup"] = _cleanup(ctx, result, frozen, ws)
        result["cleanup"]["errors"][:0] = salvage_errors
        _write_result(arm_dir, result)
    return result


# --- run -----------------------------------------------------------------------------------------

def _has_branch(repo: Path, branch: str) -> bool:
    return git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}").returncode == 0


def _set_aside(ctx: RunContext, label: str) -> str | None:
    """Rename an unfinished attempt's arm dir and branch to <label>.attempt-<k>; the new name or None.

    A hard kill (OOM, power loss) runs no finally: it leaves the credentials copy in the arm's
    cfg and the harness's worktree with its hooks dir. The transcripts and any uncommitted work
    are copied into the arm dir first, then the copy is deleted BEFORE the rename, so no set-aside
    directory carries it, and the worktree is pruned so the rerun is not refused as an earlier
    arm's leftover. k is the first number free for both the directory and the branch.

    Raises:
        abarm.ArmError: the left-over worktree could not be pruned (the message names the cleanup).
        RunRefused: the branch could not be renamed.
    """
    arm_dir, ws, branch = _paths(ctx, label)
    repo = ctx.profile.workpiece.repo
    for error in _salvage(ctx, {}, arm_dir, ws):
        _warn(f"{label}: {error}")
    abarm.delete_cfg(arm_dir / "cfg")
    if _harness_worktree_left(repo, ws):
        abarm.prune(ws, repo, ctx.profile.floor.cache_paths)
    has_branch = _has_branch(repo, branch)
    if not arm_dir.exists() and not has_branch:
        return None
    k = 1
    while (arm_dir.parent / f"{label}.attempt-{k}").exists() or _has_branch(repo, f"{branch}.attempt-{k}"):
        k += 1
    suffix = f".attempt-{k}"
    if has_branch:
        proc = git(repo, "branch", "-m", branch, branch + suffix)
        if proc.returncode != 0:
            raise RunRefused(f"cannot set aside branch {branch}: {proc.stderr.strip()}")
    if arm_dir.exists():
        arm_dir.rename(arm_dir.parent / (label + suffix))
    return label + suffix


def _auth_failed_in(stream: Path) -> bool:
    """Whether a stream record carries the CLI's authentication_failed error."""
    if not stream.is_file():
        return False
    for line in stream.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        if isinstance(rec, dict) and (rec.get("error") == AUTH_FAILED or (isinstance(msg, dict) and msg.get("error") == AUTH_FAILED)):
            return True
    return False


def _pause_trigger(result: dict[str, Any], stream: Path) -> str | None:
    """How the session ended if it ended the way a refused request does; None for a normal end.

    The CLI reports a 401 and a 429 alike, and an exhausted usage window as a synthetic notice
    that charges nothing: voiding such arms would void every arm left in the run (design S4
    pauses instead). Only the out-of-band probe can tell the cases apart, so this names what was
    seen, never why.
    """
    synthetic = [str(r)[len(SYNTHETIC_REASON_PREFIX):].lower() for r in result.get("void_reasons") or []
                 if str(r).startswith(SYNTHETIC_REASON_PREFIX)]
    if any(m in text for text in synthetic for m in LOGIN_MARKS) or _auth_failed_in(stream):
        return PAUSE_LOGIN
    if any(m in text for text in synthetic for m in LIMIT_MARKS):
        return PAUSE_LIMIT
    if synthetic and not result.get("assistant_messages"):
        return PAUSE_SYNTHETIC_ONLY
    return None


def _context(args: argparse.Namespace, run_dir: Path, profile: Profile,
             sealed_suite: abscore.SealedSuite | None) -> RunContext:
    if args.only and args.only not in profile.arm_names():
        raise RunRefused(f"--only {args.only!r} is not an arm of this run ({', '.join(profile.arm_names())})")
    if args.max_turns < 1:
        raise RunRefused("--max-turns must be at least 1")
    if not args.stop_grace_s > 0:
        raise RunRefused("--stop-grace-s must be above 0")
    return RunContext(run_dir=run_dir, profile=profile, tasks=_arm_tasks(run_dir, profile),
                      credentials=Path(args.credentials).expanduser() if args.credentials else default_credentials(),
                      skills_repo=Path(args.skills_repo).expanduser() if args.skills_repo else default_skills_repo(),
                      dry_run=args.dry_run, max_turns=args.max_turns, stop_grace_s=args.stop_grace_s,
                      sealed_suite=sealed_suite)


def _arm_tasks(run_dir: Path, profile: Profile) -> dict[str, ArmTask]:
    """{arm name: the prompt it is given}; a file shared by several arms is read once."""
    texts = {f: _read_text(run_dir / f) for f in profile.task_files()}
    return {n: ArmTask(file=f, text=texts[f], sha256=sha256_file(run_dir / f))
            for n, f in ((n, profile.task_file_for(n)) for n in profile.arm_names())}


def _schedule(profile: Profile, only: str | None) -> Iterator[tuple[int, str]]:
    for round_no, order in enumerate(rotated_schedule(profile.arm_names(), profile.run.n), start=1):
        yield from ((round_no, name) for name in order if not only or name == only)


def _attempt(ctx: RunContext, round_no: int, name: str) -> dict[str, Any]:
    """Set aside an unfinished earlier attempt, run the arm, journal a row however it ends.

    The row is written right after run_arm returns (only the pause classification, a read of the
    stream, runs in between), before the cleanup warnings and the login probe, so a kill there
    never makes a paid arm run twice. Its status is dry, ran, or paused
    (result["pause_trigger"] names what the session showed). An arm whose run_arm raises gets an
    interrupted or error row and runs again on resume; when it raised after the session was
    dispatched (a floor or bundle step), that rerun pays for the session again.
    """
    aside = _set_aside(ctx, f"r{round_no}-{name}")
    meta = ctx.arm_meta(name)
    try:
        result = run_arm(ctx, round_no, name)
    except KeyboardInterrupt:
        record(ctx.run_dir, step="arm", round=round_no, arm=name, status=INTERRUPTED, set_aside=aside, **meta)
        raise
    except Exception as exc:
        record(ctx.run_dir, step="arm", round=round_no, arm=name, status="error", error=str(exc)[:500], set_aside=aside,
               **meta)
        raise
    trigger = None if ctx.dry_run else _pause_trigger(result, ctx.run_dir / "arms" / result["arm"] / "stream.jsonl")
    status = "dry" if ctx.dry_run else ("paused" if trigger else "ran")
    record(ctx.run_dir, step="arm", round=round_no, arm=name, status=status, stop_reason=result.get("stop_reason"),
           set_aside=aside, pause_trigger=trigger, **meta)
    result.update(set_aside=aside, status=status, pause_trigger=trigger)
    return result


def _pause(ctx: RunContext, args: argparse.Namespace, round_no: int, name: str, result: dict[str, Any]) -> str:
    """Ask the probe about a paused arm, record its word; the message for the user."""
    label = f"r{round_no}-{name}"
    word = args.login_check(ctx.credentials)
    result["login_probe"] = word
    _write_result(ctx.run_dir / "arms" / label, result)
    record(ctx.run_dir, step="pause", round=round_no, arm=name, status=word, pause_trigger=result["pause_trigger"])
    return (f"paused after {label}: the session ended with {result['pause_trigger']} and the out-of-band probe "
            f"answered {word}; run the same command again to resume (the attempt is set aside and {label} runs again)")


def _login_lapses(ctx: RunContext) -> bool:
    """Whether the login in the real credentials file expires before an arm started now could end.

    An unknown expiry (no expiresAt, an unreadable file) never refuses: there is nothing to judge.
    """
    expiry = abguard.credentials_expiry_s(ctx.credentials)
    return expiry is not None and expiry < time.time() + ctx.profile.run.deadline_s


def _pause_before(ctx: RunContext, round_no: int, name: str) -> str:
    """Journal a paused row for an arm that was not started; the message for the user (no value of the file)."""
    label = f"r{round_no}-{name}"
    record(ctx.run_dir, step="arm", round=round_no, arm=name, status="paused", pause_trigger=PAUSE_EXPIRY,
           set_aside=None)
    return (f"paused before {label}: the login in {ctx.credentials} expires within the arm's deadline "
            f"({ctx.profile.run.deadline_s} s); the login must be refreshed first (use Claude normally once so it "
            "refreshes), then run the same command again to resume")


def _cleanup_warnings(result: dict[str, Any]) -> None:
    for err in (result.get("cleanup") or {}).get("errors") or []:
        _warn(f"{result.get('arm')}: {err}")


def _seal_row(run_dir: Path) -> dict[str, Any]:
    """The seal journal row, its commit verified to exist in the run dir's repository."""
    rows = [r for r in load_journal(run_dir) if r.get("step") == "seal"]
    row = rows[-1] if rows else {}
    commit = row.get("commit")
    if not isinstance(commit, str) or git(run_dir, "cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
        raise RunRefused(f"the seal record in {run_dir / JOURNAL} names no commit of {run_dir}; "
                         "the seal cannot be checked, so the run is refused")
    return row


def _sealed_suite(run_dir: Path, profile: Profile, row: dict[str, Any]) -> abscore.SealedSuite | None:
    """The sealed suite copy, refused when its sha256 differs from the one the seal recorded."""
    if profile.floor.suite is None:
        return None
    sha = row.get("suite_sha256")
    path = run_dir / SEALED_DIR / profile.floor.suite
    if not isinstance(sha, str) or not path.is_file() or sha256_file(path) != sha:
        raise RunRefused(f"the sealed suite {path} is missing or differs from the sha256 the seal recorded "
                         f"({sha}); the acceptance suite is frozen at the seal")
    return abscore.SealedSuite(path=path, sha256=sha)


def _git_out(run_dir: Path, *args: str) -> str:
    proc = git(run_dir, *args)
    if proc.returncode != 0:
        raise RunRefused(f"git {args[0]} failed in {run_dir}: {proc.stderr.strip()}")
    return proc.stdout


def _refuse_uncommitted(run_dir: Path, paths: list[str]) -> None:
    """Refuse any uncommitted or untracked change under the sealed inputs, naming each path."""
    dirty = _git_out(run_dir, "status", "--porcelain", "--untracked-files=all", "--", *paths).splitlines()
    if not dirty:
        return
    prereg = ("; PREREG.md is append-only: commit an amendment with "
              f"`git -C {run_dir} add PREREG.md && git -C {run_dir} commit -m amend`"
              if any(line[3:] == "PREREG.md" for line in dirty) else "")
    raise RunRefused(f"the sealed inputs of {run_dir} have changes that are not committed "
                     f"({'; '.join(line.strip() for line in dirty)}){prereg}; "
                     f"undo them with `git -C {run_dir} checkout -- <path>` (an untracked file: delete it)")


def _refuse_changed_since_seal(run_dir: Path, commit: str, paths: list[str]) -> None:
    """Refuse a committed change since the seal to a frozen input, and any PREREG.md change but an append."""
    changed = _git_out(run_dir, "diff", "--name-only", commit, "HEAD", "--", *paths).split()
    if changed:
        raise RunRefused(f"{', '.join(changed)} changed in a commit since the seal ({commit[:12]}); "
                         "the profile, the task files and the variants are frozen at the seal")
    sealed = _git_out(run_dir, "show", f"{commit}:PREREG.md")
    if not _git_out(run_dir, "show", "HEAD:PREREG.md").startswith(sealed):
        raise RunRefused(f"PREREG.md was rewritten since the seal ({commit[:12]}), not appended to; "
                         "the pre-registration is append-only")


def _require_seal_intact(run_dir: Path, profile: Profile) -> abscore.SealedSuite | None:
    """Refuse a run whose sealed inputs differ from the seal; the sealed suite every floor runs.

    Uncommitted or untracked changes under abtest.toml, every arm's task file, PREREG.md, variants/,
    sealed/ and .gitignore are refused (journal.jsonl and arms/ are the run's own output and are
    not looked at). A committed change since the seal commit is refused for abtest.toml, the task
    files, variants/ and sealed/; PREREG.md may grow by committed amendments, never be rewritten.
    The sealed suite copy must still hash to the sha256 the seal recorded (design S1).
    """
    row = _seal_row(run_dir)
    frozen = ["abtest.toml", *profile.task_files(), "variants", SEALED_DIR]
    _refuse_uncommitted(run_dir, [*frozen, "PREREG.md", ".gitignore"])
    _refuse_changed_since_seal(run_dir, row["commit"], frozen)
    _refuse_task_drift(run_dir, profile, row)
    return _sealed_suite(run_dir, profile, row)


def _refuse_task_drift(run_dir: Path, profile: Profile, row: dict[str, Any]) -> None:
    """Refuse an arm prompt whose file or sha256 differs from what the seal row recorded for that arm.

    A seal row from before per-arm prompts records none; git (above) then guards the task file alone.
    """
    sealed = row.get("task_files")
    if not isinstance(sealed, dict):
        return
    for name in profile.arm_names():
        f = profile.task_file_for(name)
        path = run_dir / f
        want = sealed.get(name)
        got = {"file": f, "sha256": sha256_file(path) if path.is_file() else None}
        if want != got:
            raise RunRefused(f"the prompt of arm {name} ({f}) differs from the seal ({want}); "
                             "every arm's task file is frozen at the seal")


def _require_sandbox(profile: Profile) -> None:
    """Refuse a live run whose profile names no sandbox, or whose bwrap cannot build one here.

    Probed once per `run`, before any arm: the arm env inherits this PATH (env_keep), so the
    bwrap found here is the one the session is started with.
    """
    if profile.run.sandbox is None:
        raise RunRefused(SANDBOX_MISSING)
    if profile.run.sandbox in SANDBOX_BWRAP_KINDS:
        problem = abarm.bwrap_problem(os.environ.get("PATH"), profile.run.sandbox)
        if problem:
            raise RunRefused(problem)


def _lock_holder(fd: int) -> str:
    """The pid the holder wrote into the lock file, or "unknown" (it may not have written it yet)."""
    try:
        text = os.pread(fd, 64, 0).decode("ascii", errors="replace").strip()
    except OSError:
        return "unknown"
    return text if text.isascii() and text.isdecimal() else "unknown"


@contextmanager
def _run_lock(run_dir: Path) -> Iterator[None]:
    """Hold an exclusive flock on <run_dir>/run.lock for the whole run, the holder's pid written in it.

    Raises:
        RunRefused: another process holds the lock (a `run` already going on this run dir).
    """
    if sys.platform == "win32":
        yield  # no flock here; the harness is Linux only
        return
    path = run_dir / LOCK_FILE
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RunRefused(f"another `run` holds {path} (pid {_lock_holder(fd)}); two runs on one run dir "
                             "would delete each other's live arm state: wait for it, or stop it "
                             "(Ctrl-C or SIGTERM end it cleanly)") from None
        os.ftruncate(fd, 0)
        os.pwrite(fd, f"{os.getpid()}\n".encode("ascii"), 0)
        yield
    finally:
        os.close(fd)  # closing the descriptor releases the flock


def _raise_interrupt(signum: int, frame: FrameType | None) -> None:
    raise KeyboardInterrupt


@contextmanager
def _sigterm_as_interrupt() -> Iterator[None]:
    """While a run goes, SIGTERM raises KeyboardInterrupt: the Ctrl-C path, which writes result.json and
    the journal row, ends the session's group and removes the credentials copy. Restored on exit.

    A handler can only be installed from the main thread; elsewhere SIGTERM keeps its own handling.
    """
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous = signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        yield
    finally:
        # None: the previous handler was not installed from Python; the default is what it was.
        signal.signal(signal.SIGTERM, signal.SIG_DFL if previous is None else previous)


def cmd_run(args: argparse.Namespace) -> int:
    run_dir = _run_dir(args.run_dir)
    _require_sealed(run_dir)
    # Before anything that touches arm state (_sweep_cfgs deletes every arms/*/cfg).
    with _run_lock(run_dir), _sigterm_as_interrupt():
        return _run_locked(args, run_dir)


def _run_locked(args: argparse.Namespace, run_dir: Path) -> int:
    """cmd_run's body, under the run dir lock."""
    profile = load_profile(run_dir / "abtest.toml")
    sealed_suite = _require_seal_intact(run_dir, profile)
    ctx = _context(args, run_dir, profile, sealed_suite)
    if not ctx.dry_run:
        _require_sandbox(profile)
    for cfg in _sweep_cfgs(run_dir):
        _warn(f"deleted the config dir a killed arm left at {cfg} (it held a credentials copy); "
              "its transcripts are kept beside it")
    done: list[dict[str, Any]] = []
    skipped: list[str] = []
    for round_no, name in _schedule(ctx.profile, args.only):
        if _done(run_dir, round_no, name, DONE_DRY if ctx.dry_run else DONE_LIVE):
            skipped.append(f"r{round_no}-{name} already ran")
            continue
        if not ctx.dry_run and _login_lapses(ctx):
            message = _pause_before(ctx, round_no, name)
            _emit(args.json, "run", {"done": done, "paused_at": f"r{round_no}-{name}", "pause_trigger": PAUSE_EXPIRY,
                                     "message": message}, False, message, skipped)
            return EXIT_NO
        result = _attempt(ctx, round_no, name)
        _cleanup_warnings(result)
        if result["status"] == "paused":
            message = _pause(ctx, args, round_no, name, result)
            _emit(args.json, "run", {"done": done, "paused_at": result["arm"], "login_probe": result["login_probe"],
                                     "pause_trigger": result["pause_trigger"], "message": message}, False, message, skipped)
            return EXIT_NO
        status = result["status"]
        done.append({"arm": result["arm"], "status": status, "cost_usd": result.get("total_cost_usd"),
                     "wall_s": result.get("wall_s"), "floor_passed": result["floor"]["passed"]})
    text = "\n".join(f"{d['arm']}: {d['status']} cost={d['cost_usd']} floor={d['floor_passed']}" for d in done)
    _emit(args.json, "run", {"done": done}, True, text or "nothing to run", skipped)
    return EXIT_YES


# --- score and prune-run -------------------------------------------------------------------------

def _finished(run_dir: Path) -> dict[str, dict[str, Any]]:
    """{label: result.json} of every arm the journal says ran or dry-ran, in journal order."""
    out: dict[str, dict[str, Any]] = {}
    for row in load_journal(run_dir):
        if row.get("step") != "arm" or row.get("status") not in DONE_DRY:
            continue
        label = f"r{row.get('round')}-{row.get('arm')}"
        path = run_dir / "arms" / label / "result.json"
        if path.is_file():
            out[label] = json.loads(path.read_text(encoding="utf-8"))
    return out


def _score_all(run_dir: Path, profile: Profile, results: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Score twice: first without warmth, then with the OTHER live arms that pass every other rule as peers.

    A void arm never sets the warmth median (controller decision 2026-11-04): its first-message
    cache read says nothing about how warm a normal arm starts.
    """
    first = {label: abscore.score_arm(run_dir / "arms" / label, profile, []) for label in results}
    eligible = {label: res for label, res in results.items()
                if not res.get("dry_run") and res.get("has_result") and not first[label]["void"]}
    return {label: abscore.score_arm(run_dir / "arms" / label, profile,
                                     [r for other, r in eligible.items() if other != label]) for label in results}


def _store_flag(label: str, score: dict[str, Any]) -> str | None:
    """The line that makes a store change impossible to miss; it flags the arm, it never voids it.

    The guard records rather than voids (user decision 2026-11-04): another session may have
    changed the shared store, so the change is checked against what the arm's transcripts show.
    """
    changes = score.get("store_changes") or []
    if not changes:
        return None
    return f"store changed: {len(changes)} entries, adjudicate against arms/{label}/{TRANSCRIPTS}/"


def _question_flag(score: dict[str, Any]) -> str | None:
    """The line that names an arm whose session ended by asking (nobody answers); a flag, never a void."""
    if score.get("ended_with_question") is not True:
        return None
    text = str(score.get("last_text") or "")
    return f"ended with a question: {text if len(text) <= QUESTION_SHOWN else '...' + text[-QUESTION_SHOWN:]}"


def _arm_flag(label: str, score: dict[str, Any]) -> str | None:
    """Every flag of the arm on one line, "; "-joined; None when it has none."""
    flags = [f for f in (_store_flag(label, score), _question_flag(score)) if f is not None]
    return "; ".join(flags) or None


def _score_line(label: str, score: dict[str, Any]) -> str:
    line = (f"{label}: cost={score['cost_usd']} floor={score['floor_passed']} void={score['void'] or '-'} "
            f"sandbox={score.get('sandbox') or '-'} task={score.get('task_file') or '-'}"
            f"@{(score.get('task_sha256') or '-')[:12]}"
            f" subagents={abtrace.describe_subagents(score.get('subagents'))}"
            f" ideas={abtrace.describe_ideas(score.get('idea_markers'))}"
            f" suite={abtrace.describe_suite(score.get('floor_suite'))}"
            f" gate={abtrace.describe_suite(score.get('floor_gate'))}")
    flag = _arm_flag(label, score)
    line = line if flag is None else f"{line} FLAG {flag}"
    # One line per idea under its arm: the first marker line the arm wrote for it.
    ideas = (score.get("idea_markers") or {}).get("ideas") or {}
    return "\n".join([line, *(f"  {label} idea {n}: {v['first']}" for n, v in ideas.items())])


def cmd_score(args: argparse.Namespace) -> int:
    run_dir = _run_dir(args.run_dir)
    _require_sealed(run_dir)
    profile = load_profile(run_dir / "abtest.toml")
    results = _finished(run_dir)
    if not results:
        _emit(args.json, "score", {"arms": {}, "flags": {}}, False, "no finished arm to score")
        return EXIT_NO
    scores = _score_all(run_dir, profile, results)
    for res in results.values():
        record(run_dir, step="score", round=res.get("round", 0), arm=res.get("name", ""), status="scored")
    flags = {label: flag for label, score in scores.items() if (flag := _arm_flag(label, score)) is not None}
    _emit(args.json, "score", {"arms": scores, "flags": flags}, True,
          "\n".join(_score_line(k, v) for k, v in scores.items()))
    return EXIT_YES


def _arm_worktrees(profile: Profile, run_id: str) -> list[Path]:
    """The worktree path of every arm of the run, from the profile (abx-<run>-r<round>-<name>).

    Built from the arm labels, never by matching the prefix abx-<run>-: a run id may itself hold
    a dash, so the prefix of run "x" would also match run "x-r1"'s worktrees.
    """
    root = profile.workpiece.repo / ".claude" / "worktrees"
    return [root / f"abx-{run_id}-r{round_no}-{name}" for round_no in range(1, profile.run.n + 1)
            for name in profile.arm_names()]


def _restore_exclude(run_dir: Path, repo: Path, errors: list[str]) -> str:
    """Take out the info/exclude line this run's harness added; what was done, as one word.

    "not_added" when no journal row says the harness added it (the user's own line stays),
    "removed", or "kept" while a harness worktree (abx-*) of any run is still under
    .claude/worktrees/, which would otherwise show up as untracked in the real checkout.
    """
    rows = [r.get("status") for r in load_journal(run_dir) if r.get("step") == EXCLUDE_STEP]
    if not rows or rows[-1] != "added":
        return "not_added"
    worktrees = repo / ".claude" / "worktrees"
    if worktrees.is_dir() and any(p.name.startswith("abx-") for p in worktrees.iterdir()):
        return "kept"
    try:
        abarm.remove_worktrees_exclude(repo)
    except abarm.ArmError as exc:
        errors.append(str(exc))
        return "kept"
    record(run_dir, step=EXCLUDE_STEP, round=0, arm="", status="removed")
    return "removed"


def _sandboxes(run_dir: Path) -> dict[str, str | None]:
    """{label: sandbox} of every arm the journal says ran live, the last row per label winning."""
    return {f"r{r.get('round')}-{r.get('arm')}": r.get("sandbox") for r in load_journal(run_dir)
            if r.get("step") == "arm" and r.get("status") in DONE_LIVE}


def _bundle_branches(repo: Path, run_dir: Path, refs: list[str]) -> str | None:
    """Write every branch of the run into <run_dir>/branches.bundle before any is deleted.

    An arm's own bundle.git holds only its final branch, so the set-aside attempts, a killed arm's
    branch and a parallel node's branch would be gone after the delete (measured: 17 of 62). A
    second prune with nothing left writes no bundle; an existing bundle is never replaced.
    Returns the error text, or None when the branches are bundled or there are none.
    """
    if not refs:
        return None
    target = run_dir / "branches.bundle"
    n = 1
    while target.exists():
        n += 1
        target = run_dir / f"branches-{n}.bundle"
    made = git(repo, "bundle", "create", str(target), *refs)
    if made.returncode != 0:
        return f"bundle of the run's branches failed, none deleted: {' '.join(made.stderr.split())[:200]}"
    return None


def cmd_prune_run(args: argparse.Namespace) -> int:
    """Prune every arm worktree of the run, then delete its branches.

    Every config dir left under arms/ (a hard-killed arm's, with its credentials copy) is deleted
    first, its transcripts kept. A worktree an arm registered itself under arms/ (a parallel node's)
    is removed by exact path with its branch. An arm whose worktree git no longer lists but whose <ws>.githooks
    is left (the user removed a locked worktree by hand with `worktree remove -f -f`) is pruned
    too: that removes the hooks dir and unsets the extension the harness set. The `.claude/worktrees/` line of the
    workpiece's info/exclude is removed only when the journal says the harness added it.
    """
    run_dir = _run_dir(args.run_dir)
    profile = load_profile(run_dir / "abtest.toml")
    repo, run_id = profile.workpiece.repo, run_dir.name
    cfg_removed = _sweep_cfgs(run_dir)
    errors = []
    for ws in _arm_worktrees(profile, run_id):
        if not _harness_worktree_left(repo, ws):
            continue
        try:
            abarm.prune(ws, repo, profile.floor.cache_paths)
        except abarm.ArmError as exc:
            errors.append(f"{ws}: {exc}")
    own_refs: list[str] = []
    for path, branch in _arm_made_worktrees(repo, run_dir):
        # remove by exact path, never `git worktree prune`: that drops every stale registration
        if git(repo, "worktree", "remove", "--force", str(path)).returncode != 0:
            errors.append(f"{path}: worktree remove failed")
        elif branch:
            own_refs.append(branch)
    refs = [*_run_branches(repo, run_id), *own_refs]
    bundle_error = _bundle_branches(repo, run_dir, refs)
    if bundle_error:
        errors.append(bundle_error)
        refs = []  # nothing is deleted that no bundle holds
    deleted = [b for b in refs if git(repo, "branch", "-D", b).returncode == 0]
    errors += [f"branch {b} could not be deleted" for b in refs if b not in deleted]
    skipped = [f"frozen checkout {p} is left (release it from the skills repo)" for p in sorted((run_dir / "frozen").glob("*"))]
    exclude = _restore_exclude(run_dir, repo, errors)
    sandbox = _sandboxes(run_dir)
    data = {"deleted": deleted, "errors": errors, "exclude": exclude, "cfg_removed": cfg_removed, "sandbox": sandbox}
    used = ", ".join(sorted({str(v) for v in sandbox.values()}))
    _emit(args.json, "prune-run", data, not errors, f"deleted {len(deleted)} branch(es) under abx/{run_id}/"
          + (f" (arms ran with sandbox: {used})" if used else "")
          + "".join(f"\nerror: {e}" for e in errors), skipped)
    if errors:
        print(f"abtest prune-run: error: {len(errors)} cleanup step(s) failed; first: {' '.join(errors[0].split())}",
              file=sys.stderr)
    return EXIT_ERROR if errors else EXIT_YES


# --- the command line ----------------------------------------------------------------------------

class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:  # argparse's own exit would print no JSON envelope
        raise UsageError(f"{self.prog}: {message}")


def _add_run_options(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--dry-run", action="store_true", help="everything but the paid claude -p step")
    sp.add_argument("--only", help="run only this arm name (C or a variant name)")
    sp.add_argument("--credentials", default=None,
                    help="the login file (default <Claude config dir>/.credentials.json)")
    sp.add_argument("--skills-repo", default=None,
                    help="the bitranox-skills clone (default <Claude config dir>/plugins/marketplaces/bitranox-skills)")
    sp.add_argument("--max-turns", type=int, default=400)
    sp.add_argument("--stop-grace-s", type=float, default=float(abarm.STOP_GRACE_S),
                    help="seconds a session's process group gets between SIGTERM and SIGKILL when it is ended")


def build_parser() -> argparse.ArgumentParser:
    ap = _Parser(prog="abtest.py", description=__doc__, epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    for name, fn in (("init", cmd_init), ("seal", cmd_seal), ("run", cmd_run), ("score", cmd_score), ("prune-run", cmd_prune_run)):
        sp = sub.add_parser(name)
        sp.add_argument("run_dir")
        sp.add_argument("--json", action="store_true")
        sp.set_defaults(fn=fn)
        if name == "init":
            for opt in ("--repo", "--base", "--skills-ref", "--skill"):
                sp.add_argument(opt)
        if name == "run":
            _add_run_options(sp)
    return ap


# UnicodeError: a file the user wrote that is not UTF-8 (abtest.toml, a result.json) is a could-not-run.
_COULD_NOT_RUN = (ProfileError, RunRefused, JournalError, UsageError, abarm.ArmError, abguard.GuardError, OSError,
                  subprocess.TimeoutExpired, json.JSONDecodeError, UnicodeError)


def _fail(as_json: bool, command: str, exc: BaseException) -> int:
    """Exit 2: the envelope under --json, and always exactly one line on stderr."""
    message = str(exc)
    if as_json:
        print(envelope(command, {"error": message, "type": type(exc).__name__}, ok=False))
    print(f"abtest {command}: error: {' '.join(message.split())}", file=sys.stderr)
    return EXIT_ERROR


def _command_of(argv: list[str]) -> str:
    return next((a for a in argv if not a.startswith("-")), "abtest")


def main(argv: list[str] | None = None, *, login_check: LoginCheck = abguard.check_login) -> int:
    """Entry point; login_check is the one injectable seam (tests pass a stub, never a monkeypatch).

    A KeyboardInterrupt is re-raised after the arm's result.json and journal row are written.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = build_parser().parse_args(argv)
    except UsageError as exc:
        return _fail("--json" in argv, _command_of(argv), exc)
    args.login_check = login_check
    try:
        return int(args.fn(args))
    except _COULD_NOT_RUN as exc:
        return _fail(args.json, args.cmd, exc)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("abtest: interrupted; the journal records the arm, run the same command to resume", file=sys.stderr)
        sys.exit(130)
