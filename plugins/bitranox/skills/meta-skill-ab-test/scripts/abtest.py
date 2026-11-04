#!/usr/bin/env python3
"""abtest: A/B test a skill against its variants on one real task in the real repository.

Subcommands (every one takes --json; exit 0 yes / 1 no / 2 could not run):
  init <run_dir> [--repo --base --skills-ref --skill]   write the profile, task and PREREG skeletons
  seal <run_dir>                                       validate and commit them; fixes the weights
  run <run_dir> [--dry-run] [--only ARM] ...           the serial interleaved arms (resumes)
  score <run_dir>                                      per-arm scores and void rules
  prune-run <run_dir>                                  delete the run's branches in the workpiece

The run dir is its own git repo so the pre-registration is append-only. Its journal.jsonl records
every arm attempt; `run` skips an arm the journal says ran, and sets aside (renames) the directory
and branch of an attempt that did not finish (paused, interrupted, failed, killed, or a dry run
before a live one) before running that arm again; the credentials copy and the worktree such an
attempt left are removed first. A session that ends the way the CLI reports a refused request (a
login-looking failure, only CLI synthetic messages, or a usage-limit notice) is the only time the
out-of-band login probe is asked; its answer pauses the run, names no cause, and the arm runs
again on resume rather than being voided (design S4).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import abarm
import abguard
import abscore
from _ablib import (
    EXIT_ERROR,
    EXIT_NO,
    EXIT_YES,
    append_jsonl,
    envelope,
    git,
    rotated_schedule,
    sha256_file,
    utc_now,
)
from abprofile import SKELETON, Profile, ProfileError, load_profile
from abstream import OPUS_PREFIX, SYNTHETIC_REASON_PREFIX

__all__ = [
    "DEFAULT_CREDENTIALS",
    "DEFAULT_SKILLS_REPO",
    "OPUS_PREFIX",
    "WEIGHTS",
    "JournalError",
    "RunContext",
    "RunRefused",
    "build_parser",
    "load_journal",
    "main",
    "record",
    "run_arm",
]

LoginCheck = Callable[[Path], str]
DEFAULT_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"
DEFAULT_SKILLS_REPO = Path.home() / ".claude" / "plugins" / "marketplaces" / "bitranox-skills"  # the clone every install has
WEIGHTS = {"correctness": 0.30, "task_coverage": 0.25, "tests": 0.20, "beyond_plan_fixes": 0.10,
           "readability": 0.10, "scope_creep": 0.05}
PREREG_SKELETON = """# Pre-registration

## Question
<what the variants are expected to change, in one sentence>

## Hypotheses
<H1 ... per variant: direction and the criterion it should move>

## Decision rule
Pairwise blind judge (design S2), A/B swap tie rule, control first then finalists; labels per design S5.4.
"""
GITIGNORE = ("frozen/\narms/*/cfg\narms/*/home\narms/*/stream.jsonl\narms/*/bundle.git\narms/*/guard\n"
             "arms/*/transcripts\narms/*/uncommitted.patch\narms/*/untracked.tar\n")
# Where an arm's session transcripts (copied out of its config dir before that is deleted) go.
TRANSCRIPTS = "transcripts"
JOURNAL, TORN = "journal.jsonl", "journal.torn"
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
SEAL_GIT = ("-c", "user.name=abtest", "-c", "user.email=abtest@localhost", "-c", "commit.gpgsign=false",
            "-c", "core.hooksPath=/dev/null")


class RunRefused(RuntimeError):
    """A precondition of the subcommand is not met; exit 2 with this message."""


class JournalError(RuntimeError):
    """journal.jsonl holds an unparsable line before its last one; it cannot be trusted to resume."""


class UsageError(RuntimeError):
    """The command line does not parse; reported like any other could-not-run."""


@dataclass(frozen=True)
class RunContext:
    run_dir: Path
    profile: Profile
    task: str
    credentials: Path
    skills_repo: Path
    dry_run: bool
    max_turns: int
    stop_grace_s: float

    @property
    def run_id(self) -> str:
        return self.run_dir.name


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
    if not _read_or_empty(run_dir / profile.workpiece.task_file).strip():
        problems.append(f"{profile.workpiece.task_file} is empty")
    prereg = _read_or_empty(run_dir / "PREREG.md")
    if not prereg.strip() or PLACEHOLDER_RE.search(prereg):
        problems.append("PREREG.md is empty or still holds a <placeholder>")
    for v in profile.variants:
        if not (run_dir / v.dir).is_dir() or not any(p.is_file() for p in (run_dir / v.dir).rglob("*")):
            problems.append(f"variants/{v.name}: {v.dir} holds no file")
    return problems


def _suite_sha(profile: Profile) -> str | None:
    if not profile.floor.suite:
        return None
    suite_path = profile.workpiece.repo / profile.floor.suite
    if not suite_path.is_file():
        raise RunRefused(f"floor.suite {suite_path} does not exist at the workpiece")
    return sha256_file(suite_path)


def _commit_seal(run_dir: Path, stamp: dict[str, Any]) -> None:
    """Append the stamp to PREREG.md, journal the seal and commit both; undo both when the commit fails."""
    prereg = run_dir / "PREREG.md"
    before = _read_text(prereg)
    with prereg.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n## Sealed\n\n```json\n" + json.dumps(stamp, indent=1, sort_keys=True) + "\n```\n")
    record(run_dir, step="seal", round=0, arm="", status="sealed")
    git(run_dir, "add", "-A")
    proc = git(run_dir, *SEAL_GIT, "commit", "-q", "-m", "seal")
    if proc.returncode != 0:
        prereg.write_text(before, encoding="utf-8")
        (run_dir / JOURNAL).unlink(missing_ok=True)
        git(run_dir, "reset", "-q")
        raise RunRefused(f"seal commit failed: {proc.stderr.strip()}")


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
    stamp = {"sealed_at": utc_now(), "weights": WEIGHTS, "suite_sha256": _suite_sha(profile), "arms": profile.arm_names(),
             "n": profile.run.n, "warmth_tolerance": profile.run.warmth_tolerance}
    _commit_seal(run_dir, stamp)
    _emit(args.json, "seal", stamp, True, f"sealed {run_dir}: {len(profile.arm_names())} arms x {profile.run.n} rounds")
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


def _arm_steps(ctx: RunContext, result: dict[str, Any], frozen: abarm.Frozen, label: str) -> None:
    p = ctx.profile
    arm_dir, ws, branch = _paths(ctx, label)
    cfg = arm_dir / "cfg"
    env = abarm.arm_env(cfg, abarm.arm_home(arm_dir, p.run.home_links), p.run.env_keep)
    result["install"] = abarm.install_plugin(cfg, frozen, ctx.credentials, env)
    _ignore_worktrees(ctx)
    result["worktree"] = abarm.make_worktree(p.workpiece.repo, p.workpiece.base, branch, ws, copy_untracked_claude_md=True)
    result["guard"] = abguard.snapshot(ws, arm_dir / "guard")
    if not ctx.dry_run:
        result.update(abarm.dispatch(arm_dir, ws, env, abarm.claude_argv(ctx.task, ctx.max_turns),
                                     max_tokens=p.run.max_tokens, deadline_s=p.run.deadline_s,
                                     stop_grace_s=ctx.stop_grace_s))
    # Right after the session, before the floor writes into the worktree (build output, the suite).
    result["uncommitted"] = _save_uncommitted(ctx, arm_dir, ws)
    _guard_after(result, arm_dir / "guard")
    result["floor"] = abscore.run_floor(ws, p, arm_dir)
    result["bundle_commits"] = abarm.bundle(ws, p.workpiece.base, arm_dir / "bundle.git")


def _ignore_worktrees(ctx: RunContext) -> None:
    """Make sure .claude/worktrees/ is ignored; journal it at once when the harness added the line.

    The line is shared by every arm (only the first one adds it), so whether the harness added it
    belongs to the run, not to an arm's state file: prune-run removes it only when this row says so.
    """
    if abarm.ensure_worktrees_ignored(ctx.profile.workpiece.repo):
        record(ctx.run_dir, step=EXCLUDE_STEP, round=0, arm="", status="added")


def _save_uncommitted(ctx: RunContext, arm_dir: Path, ws: Path) -> dict[str, Any]:
    """abarm.save_uncommitted with the profile's cache paths and the harness's own CLAUDE.md copy skipped."""
    repo = ctx.profile.workpiece.repo
    return abarm.save_uncommitted(ws, arm_dir, skip_prefixes=ctx.profile.floor.cache_paths,
                                  harness_copies={"CLAUDE.md": repo / "CLAUDE.md"})


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
        if ws.is_dir() and ("worktree" in result or _harness_worktree_left(ctx.profile.workpiece.repo, ws)):
            result["uncommitted"] = _save_uncommitted(ctx, arm_dir, ws)
    except (abarm.ArmError, OSError, tarfile.TarError) as exc:
        errors.append(f"save_uncommitted: {exc}")
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
    result: dict[str, Any] = {"arm": label, "round": round_no, "name": name, "dry_run": ctx.dry_run}
    frozen: abarm.Frozen | None = None
    try:
        frozen = abarm.freeze_variant(ctx.run_dir, ctx.profile, name, ctx.skills_repo)
        result["frozen"] = {"ref": frozen.skills_ref, "overlay_written": list(frozen.overlay_written)}
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


def _context(args: argparse.Namespace, run_dir: Path, profile: Profile) -> RunContext:
    if args.only and args.only not in profile.arm_names():
        raise RunRefused(f"--only {args.only!r} is not an arm of this run ({', '.join(profile.arm_names())})")
    if args.max_turns < 1:
        raise RunRefused("--max-turns must be at least 1")
    if not args.stop_grace_s > 0:
        raise RunRefused("--stop-grace-s must be above 0")
    return RunContext(run_dir=run_dir, profile=profile, task=_read_text(run_dir / profile.workpiece.task_file),
                      credentials=Path(args.credentials).expanduser(), skills_repo=Path(args.skills_repo).expanduser(),
                      dry_run=args.dry_run, max_turns=args.max_turns, stop_grace_s=args.stop_grace_s)


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
    try:
        result = run_arm(ctx, round_no, name)
    except KeyboardInterrupt:
        record(ctx.run_dir, step="arm", round=round_no, arm=name, status=INTERRUPTED, set_aside=aside)
        raise
    except Exception as exc:
        record(ctx.run_dir, step="arm", round=round_no, arm=name, status="error", error=str(exc)[:500], set_aside=aside)
        raise
    trigger = None if ctx.dry_run else _pause_trigger(result, ctx.run_dir / "arms" / result["arm"] / "stream.jsonl")
    status = "dry" if ctx.dry_run else ("paused" if trigger else "ran")
    record(ctx.run_dir, step="arm", round=round_no, arm=name, status=status, stop_reason=result.get("stop_reason"),
           set_aside=aside, pause_trigger=trigger)
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


def _require_prereg_committed(run_dir: Path) -> None:
    """Refuse a sealed run whose PREREG.md differs from what is committed: an amendment must be committed."""
    proc = git(run_dir, "status", "--porcelain", "--", "PREREG.md")
    if proc.returncode != 0:
        raise RunRefused(f"cannot read the git status of {run_dir / 'PREREG.md'}: {proc.stderr.strip()}")
    if proc.stdout.strip():
        raise RunRefused(f"{run_dir / 'PREREG.md'} has changes that are not committed ({proc.stdout.strip()}); "
                         f"the pre-registration is append-only: commit the amendment with "
                         f"`git -C {run_dir} add PREREG.md && git -C {run_dir} commit -m amend`, "
                         f"or undo it with `git -C {run_dir} checkout -- PREREG.md`")


def cmd_run(args: argparse.Namespace) -> int:
    run_dir = _run_dir(args.run_dir)
    _require_sealed(run_dir)
    _require_prereg_committed(run_dir)
    ctx = _context(args, run_dir, load_profile(run_dir / "abtest.toml"))
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


def cmd_score(args: argparse.Namespace) -> int:
    run_dir = _run_dir(args.run_dir)
    _require_sealed(run_dir)
    profile = load_profile(run_dir / "abtest.toml")
    results = _finished(run_dir)
    if not results:
        _emit(args.json, "score", {"arms": {}}, False, "no finished arm to score")
        return EXIT_NO
    scores = _score_all(run_dir, profile, results)
    for res in results.values():
        record(run_dir, step="score", round=res.get("round", 0), arm=res.get("name", ""), status="scored")
    _emit(args.json, "score", {"arms": scores}, True,
          "\n".join(f"{k}: cost={v['cost_usd']} floor={v['floor_passed']} void={v['void'] or '-'}" for k, v in scores.items()))
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


def cmd_prune_run(args: argparse.Namespace) -> int:
    """Prune every arm worktree of the run, then delete its branches.

    Every config dir left under arms/ (a hard-killed arm's, with its credentials copy) is deleted
    first, its transcripts kept. An arm whose worktree git no longer lists but whose <ws>.githooks
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
    refs = _run_branches(repo, run_id)
    deleted = [b for b in refs if git(repo, "branch", "-D", b).returncode == 0]
    errors += [f"branch {b} could not be deleted" for b in refs if b not in deleted]
    skipped = [f"frozen checkout {p} is left (release it from the skills repo)" for p in sorted((run_dir / "frozen").glob("*"))]
    exclude = _restore_exclude(run_dir, repo, errors)
    data = {"deleted": deleted, "errors": errors, "exclude": exclude, "cfg_removed": cfg_removed}
    _emit(args.json, "prune-run", data, not errors, f"deleted {len(deleted)} branch(es) under abx/{run_id}/"
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
    sp.add_argument("--credentials", default=str(DEFAULT_CREDENTIALS))
    sp.add_argument("--skills-repo", default=str(DEFAULT_SKILLS_REPO))
    sp.add_argument("--max-turns", type=int, default=400)
    sp.add_argument("--stop-grace-s", type=float, default=float(abarm.STOP_GRACE_S),
                    help="seconds a session's process group gets between SIGTERM and SIGKILL when it is ended")


def build_parser() -> argparse.ArgumentParser:
    ap = _Parser(prog="abtest.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
