"""One arm's lifecycle pieces: freeze the skill, install it, make the worktree, run, bundle, prune.

The workspace is a nested worktree of the real repository, not a clone (design S1): the arm must
load the same CLAUDE.md cascade and memory index as real work does. Linux only: the session is
ended by signalling its process group, and the refusing pre-push hook is a /bin/sh script.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any

from _ablib import git, run, tree_hashes
from abprofile import Profile
from abstream import StreamAccount

__all__ = [
    "PLUGIN_ID",
    "PRE_PUSH_HOOK",
    "ArmError",
    "Frozen",
    "arm_env",
    "arm_home",
    "bundle",
    "claude_argv",
    "delete_cfg",
    "dispatch",
    "freeze_variant",
    "install_plugin",
    "installed_plugin_path",
    "make_worktree",
    "plugin_root",
    "prune",
]

PLUGIN_NAME = "bitranox"
PLUGIN_ID = "bitranox@bitranox-skills"
# Both relative to the plugin root, which in the bitranox-skills repo is plugins/bitranox/.
SWITCH_REL = "hooks/self_improve_signals.py"
SWITCH_NAME = "BITRANOX_MEMORY_WRITES"
WORKTREES_PROBE = ".claude/worktrees/probe"
WORKTREES_PATTERN = ".claude/worktrees/"
INSTALL_TIMEOUT_S = 300
STOP_GRACE_S = 60
PRE_PUSH_HOOK = "#!/bin/sh\necho 'abtest arm: pushing is refused; the branch is collected by the harness' >&2\nexit 1\n"


class ArmError(RuntimeError):
    """A step of the arm could not be completed as specified; the arm is not started or is void."""


@dataclass(frozen=True)
class Frozen:
    """A detached bitranox-skills checkout at skills_ref with one variant's overlay applied.

    Attributes:
        path: the checkout root, the directory `claude plugin marketplace add` is given.
        skills_ref: the commit it is checked out at.
        skill_dir: the skill under test inside the checkout's plugin root.
        overlay_written: the skill-relative paths the variant's files replaced (empty for C).
        hashes: {skill-relative path: sha256} of the skill as frozen; the install is checked against it.
    """

    path: Path
    skills_ref: str
    skill_dir: Path
    overlay_written: tuple[str, ...]
    hashes: dict[str, str]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """git() with a missing or unrunnable git binary reported as an ArmError, not a traceback."""
    try:
        return git(repo, *args)
    except OSError as exc:
        raise ArmError(f"git could not run: {exc}") from exc


def _git_ok(repo: Path, *args: str) -> str:
    """git() that must succeed; its stripped stdout."""
    proc = _git(repo, *args)
    if proc.returncode != 0:
        raise ArmError(f"git {args[0]} failed rc={proc.returncode}: {proc.stderr.strip()[-500:]}")
    return proc.stdout.strip()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ArmError(f"cannot read {path}: {exc}") from exc


def plugin_root(checkout: Path) -> Path:
    """Where the bitranox plugin sits in a checkout.

    A marketplace checkout (the real bitranox-skills repo) names it in marketplace.json, as
    `./plugins/bitranox`; a checkout that IS the plugin carries plugin.json at its root.

    Raises:
        ArmError: the checkout holds neither, or its marketplace has no local bitranox source.
    """
    market = checkout / ".claude-plugin" / "marketplace.json"
    if market.is_file():
        return _marketplace_source(checkout, _read_json(market))
    if (checkout / ".claude-plugin" / "plugin.json").is_file():
        return checkout
    raise ArmError(f"{checkout} holds neither .claude-plugin/marketplace.json nor .claude-plugin/plugin.json")


def _marketplace_source(checkout: Path, data: Any) -> Path:
    entries = data.get("plugins") if isinstance(data, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or entry.get("name") != PLUGIN_NAME:
            continue
        source = entry.get("source")
        if not isinstance(source, str):
            continue
        # normpath, not resolve(): the checkout may sit under a symlinked run dir, and the
        # returned path must stay comparable with the checkout path.
        root = Path(os.path.normpath(checkout / source))
        if root == checkout or checkout in root.parents:
            return root
    raise ArmError(f"{checkout}'s marketplace.json lists no {PLUGIN_NAME} plugin with a source inside the checkout")


def _apply_overlay(variant_dir: Path | None, skill_dir: Path) -> tuple[str, ...]:
    """Copy every file of the variant dir over the skill dir; the list of relative paths written."""
    if variant_dir is None:
        return ()
    written = []
    for src in sorted(p for p in variant_dir.rglob("*") if p.is_file()):
        rel = src.relative_to(variant_dir)
        dst = skill_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        written.append(rel.as_posix())
    return tuple(written)


def _checkout(skills_repo: Path, ref: str, path: Path) -> None:
    """A detached worktree of skills_repo at ref; an existing one is reused only at that same ref."""
    if path.exists():
        head = _git(path, "rev-parse", "--verify", "-q", "HEAD").stdout.strip()
        if head != ref:
            raise ArmError(f"{path} exists at {head or 'no commit'}, not {ref}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = _git(skills_repo, "worktree", "add", "--detach", str(path), ref)
    if proc.returncode != 0:
        raise ArmError(f"worktree add of {ref} failed: {proc.stderr.strip()}")


def _variant_dir(run_dir: Path, profile: Profile, name: str) -> Path | None:
    if name == "C":
        return None
    match = [v for v in profile.variants if v.name == name]
    if not match:
        raise ArmError(f"no variant named {name!r} in the profile")
    variant_dir = run_dir / match[0].dir
    if not variant_dir.is_dir():
        raise ArmError(f"variant dir {variant_dir} is missing")
    return variant_dir


def _require_switch(root: Path, ref: str) -> None:
    try:
        text = (root / SWITCH_REL).read_text(encoding="utf-8")
    except OSError:
        text = ""
    if SWITCH_NAME not in text:
        raise ArmError(f"skills_ref {ref} does not carry {SWITCH_NAME}; an arm would write the shared store")


def freeze_variant(run_dir: Path, profile: Profile, name: str, skills_repo: Path) -> Frozen:
    """A detached checkout of bitranox-skills at skills_ref under run_dir/frozen/<name>, overlay applied.

    Idempotent: an existing checkout at the same ref is reused (its overlay is re-applied, which is
    a no-op when nothing changed). The ref must carry the memory-writes switch (design S5.3).

    Args:
        run_dir: the run directory; variant dirs in the profile are relative to it.
        profile: the validated profile.
        name: "C" for the control, else a variant name from the profile.
        skills_repo: the bitranox-skills repository the checkout is cut from.

    Raises:
        ArmError: the checkout, the switch, the skill or the variant dir is not as required.
    """
    ref = profile.control.skills_ref
    path = run_dir / "frozen" / name
    _checkout(skills_repo, ref, path)
    root = plugin_root(path)
    _require_switch(root, ref)
    skill_dir = root / "skills" / profile.control.skill
    if not skill_dir.is_dir():
        raise ArmError(f"skill {profile.control.skill} is not at {skill_dir}")
    written = _apply_overlay(_variant_dir(run_dir, profile, name), skill_dir)
    return Frozen(path=path, skills_ref=ref, skill_dir=skill_dir, overlay_written=written, hashes=tree_hashes(skill_dir))


def installed_plugin_path(cfg: Path) -> Path | None:
    """The install path cfg's plugin registry records for the bitranox plugin; None when absent."""
    registry = cfg / "plugins" / "installed_plugins.json"
    if not registry.is_file():
        return None
    data = _read_json(registry)
    plugins = data.get("plugins") if isinstance(data, dict) else None
    entries = plugins.get(PLUGIN_ID) if isinstance(plugins, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict) and isinstance(entry.get("installPath"), str):
            return Path(entry["installPath"])
    return None


def _user_config_dir() -> Path:
    """The config dir of the person running the harness, whose settings an arm is seeded from."""
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(configured) if configured else Path.home() / ".claude"


def _seed_settings(cfg: Path, keep: tuple[str, ...]) -> list[str]:
    """Write cfg/settings.json holding only the `keep` keys of the user's settings; the keys written."""
    try:
        user = json.loads((_user_config_dir() / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        user = {}
    user = user if isinstance(user, dict) else {}
    seeded = {k: user[k] for k in keep if k in user}
    (cfg / "settings.json").write_text(json.dumps(seeded), encoding="utf-8")
    return sorted(seeded)


def _copy_credentials(credentials: Path, cfg: Path) -> None:
    """Copy the credentials into cfg, created at mode 0600 so no wider-mode copy ever exists."""
    if not credentials.is_file():
        raise ArmError(f"no credentials file at {credentials}")
    target = cfg / ".credentials.json"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(credentials.read_bytes())
    target.chmod(0o600)  # an already existing file keeps its old mode through O_CREAT


def _run_claude(argv: list[str], cwd: Path, env: dict[str, str]) -> dict[str, Any]:
    """One `claude plugin ...` step that must succeed; its argv head and rc."""
    try:
        proc = run(argv, cwd=cwd, env=env, timeout=INSTALL_TIMEOUT_S)
    except OSError as exc:
        raise ArmError(f"{argv[0]} could not start: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ArmError(f"{' '.join(argv[:4])} timed out after {INSTALL_TIMEOUT_S}s") from exc
    if proc.returncode != 0:
        raise ArmError(f"{' '.join(argv[:4])} failed rc={proc.returncode}: {proc.stderr.strip()[-500:]}")
    return {"argv": argv[1:4], "rc": proc.returncode}


def _verify_install(cfg: Path, frozen: Frozen) -> dict[str, Any]:
    installed = installed_plugin_path(cfg)
    if installed is None:
        raise ArmError("the config dir records no installed bitranox plugin")
    installed_hashes = tree_hashes(installed / "skills" / frozen.skill_dir.name)
    keys = set(frozen.hashes) | set(installed_hashes)
    drift = sorted(k for k in keys if frozen.hashes.get(k) != installed_hashes.get(k))
    manifest = _read_json(installed / ".claude-plugin" / "plugin.json")
    version = manifest.get("version") if isinstance(manifest, dict) else None
    return {"installed_path": str(installed), "installed_version": version, "drift": drift}


def install_plugin(cfg: Path, frozen: Frozen, credentials: Path, env: dict[str, str], *,
                   settings_keep: tuple[str, ...] = ("skillListingBudgetFraction",)) -> dict[str, Any]:
    """Install the frozen plugin into cfg and verify the installed skill byte for byte.

    A fresh config dir runs its only session at the CLI defaults (measured at checkpoint 1: the
    skill listing budget the plugin raises applies only from the next session), which is not
    normal work, so the `settings_keep` keys of the user's settings.json are seeded into cfg.

    Args:
        cfg: the arm's config dir (created at mode 0700).
        frozen: the checkout to install.
        credentials: the user's credentials file; copied in at mode 0600, removed by delete_cfg.
        env: must carry PATH so `claude` resolves; CLAUDE_CONFIG_DIR is set here.
        settings_keep: the user settings keys seeded into cfg/settings.json.

    Returns:
        installed_path, installed_version, drift (empty), steps and settings_seeded.

    Raises:
        ArmError: claude is missing, a step fails or times out, or the installed skill drifts.
    """
    cfg.mkdir(mode=0o700, parents=True, exist_ok=True)
    seeded = _seed_settings(cfg, settings_keep)
    _copy_credentials(credentials, cfg)
    env = dict(env, CLAUDE_CONFIG_DIR=str(cfg))
    steps = [_run_claude(argv, cfg.parent, env)
             for argv in (["claude", "plugin", "marketplace", "add", str(frozen.path), "--json"],
                          ["claude", "plugin", "install", PLUGIN_ID, "--json"])]
    info = _verify_install(cfg, frozen)
    if info["drift"]:
        raise ArmError(f"installed skill drifts from the frozen checkout: {info['drift']}")
    return dict(info, steps=steps, settings_seeded=seeded)


def _is_ignored(repo: Path, rel: str) -> bool:
    proc = _git(repo, "check-ignore", "-q", rel)
    if proc.returncode not in (0, 1):
        raise ArmError(f"git check-ignore failed rc={proc.returncode}: {proc.stderr.strip()}")
    return proc.returncode == 0


def _ensure_worktrees_ignored(repo: Path) -> None:
    """Add .claude/worktrees/ to the repo's info/exclude unless it is already ignored."""
    if _is_ignored(repo, WORKTREES_PROBE):
        return
    rel = Path(_git_ok(repo, "rev-parse", "--git-path", "info/exclude"))
    exclude = rel if rel.is_absolute() else repo / rel
    try:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        old = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
        with exclude.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(("\n" if old and not old.endswith("\n") else "") + WORKTREES_PATTERN + "\n")
    except OSError as exc:
        raise ArmError(f"cannot write {exclude}: {exc}") from exc
    if not _is_ignored(repo, WORKTREES_PROBE):
        raise ArmError(f"{WORKTREES_PATTERN} is not ignored in {repo} although {exclude} lists it; "
                       "a .gitignore negation un-ignores it")


def _install_refusing_hook(path: Path) -> Path:
    """A pre-push hook that refuses, configured for this worktree ONLY.

    A plain `git config` in a linked worktree writes the repository's shared config, so the real
    checkout's pushes would be refused too and, after prune, its hooks would point at a deleted
    dir. The per-worktree config needs extensions.worktreeConfig, which this sets on the repo.
    """
    hooks = path.parent / f"{path.name}.githooks"
    hooks.mkdir(exist_ok=True)
    hook = hooks / "pre-push"
    hook.write_text(PRE_PUSH_HOOK, encoding="utf-8", newline="\n")
    hook.chmod(0o755)
    _git_ok(path, "config", "extensions.worktreeConfig", "true")
    _git_ok(path, "config", "--worktree", "core.hooksPath", str(hooks))
    return hooks


def _copy_untracked_claude_md(repo: Path, path: Path) -> bool:
    """Copy the repo-root CLAUDE.md into the worktree when it is untracked; whether it was copied.

    Measured at checkpoint 1: a nested worktree skips the parent repo's CLAUDE.md but still loads
    the repo-root CLAUDE.local.md through the ancestor walk. So an untracked root CLAUDE.md is
    copied in (a tracked one is already in the checkout), and CLAUDE.local.md never is (it would
    then load twice).
    """
    root_md = repo / "CLAUDE.md"
    if not root_md.is_file() or (path / "CLAUDE.md").exists():
        return False
    if _git(repo, "ls-files", "--error-unmatch", "CLAUDE.md").returncode == 0:
        return False
    shutil.copyfile(root_md, path / "CLAUDE.md")
    return True


def make_worktree(repo: Path, base: str, branch: str, path: Path, *, copy_untracked_claude_md: bool) -> dict[str, Any]:
    """A nested worktree of repo at base on a NEW branch, with a refusing pre-push hook.

    `.claude/worktrees/` is added to the repo's info/exclude when not already ignored, so the
    arm's tree never shows up as untracked in the real checkout.

    Returns:
        head, branch, hooks_path and claude_md_copied.

    Raises:
        ArmError: the path exists, the worktrees dir cannot be ignored, or a git step fails.
    """
    if path.exists():
        raise ArmError(f"worktree {path} already exists")
    _ensure_worktrees_ignored(repo)
    proc = _git(repo, "worktree", "add", "-b", branch, str(path), base)
    if proc.returncode != 0:
        raise ArmError(f"worktree add failed: {proc.stderr.strip()}")
    head = _git_ok(path, "rev-parse", "HEAD")
    if head != base:
        raise ArmError(f"worktree HEAD {head} is not the base {base}")
    hooks = _install_refusing_hook(path)
    copied = copy_untracked_claude_md and _copy_untracked_claude_md(repo, path)
    return {"head": head, "branch": branch, "hooks_path": str(hooks), "claude_md_copied": copied}


def arm_home(arm_dir: Path, links: tuple[str, ...]) -> Path:
    """arm_dir/home with only the named entries of the real home linked in (toolchains, caches)."""
    home = arm_dir / "home"
    home.mkdir(parents=True, exist_ok=True)
    for name in links:
        link, target = home / name, Path.home() / name
        if target.exists() and not link.exists() and not link.is_symlink():
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target)
    return home


def arm_env(cfg: Path, home: Path, keep: tuple[str, ...]) -> dict[str, str]:
    """The arm's environment, built from scratch: only `keep` is inherited, nothing else.

    CLAUDECODE is never inherited, even when kept (a nested claude refuses to start inside
    another), and the memory-writes switch is always set.
    """
    env = {k: os.environ[k] for k in keep if k in os.environ and k != "CLAUDECODE"}
    env.update({"HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg), "BITRANOX_MEMORY_WRITES": "off"})
    return env


def claude_argv(prompt: str, max_turns: int) -> list[str]:
    """The headless opus session's argv, streaming JSON so dispatch can account it live."""
    return ["claude", "-p", prompt, "--model", "opus", "--output-format", "stream-json", "--verbose",
            "--max-turns", str(max_turns), "--dangerously-skip-permissions"]


def _signal_group(proc: subprocess.Popen[str], sig: int) -> None:
    """Signal the session's whole process group: its tool children hold the stdout pipe too."""
    try:
        os.killpg(proc.pid, sig)
    except (AttributeError, OSError):  # no killpg off POSIX, or the group is already gone
        try:
            proc.send_signal(sig)
        except OSError:
            pass


def _end(proc: subprocess.Popen[str]) -> None:
    _signal_group(proc, signal.SIGTERM)
    try:
        proc.wait(timeout=STOP_GRACE_S)
    except subprocess.TimeoutExpired:
        _signal_group(proc, getattr(signal, "SIGKILL", signal.SIGTERM))


class _Stopper:
    """Ends the session once, keeping the first reason; called from the reader and the deadline timer."""

    def __init__(self, proc: subprocess.Popen[str]) -> None:
        self.proc = proc
        self.reason: str | None = None
        self._lock = threading.Lock()

    def stop(self, reason: str, *, only_if_running: bool = False) -> None:
        with self._lock:
            # The deadline timer may fire just after a session ended by itself: that is no deadline.
            if self.reason is not None or (only_if_running and self.proc.poll() is not None):
                return
            self.reason = reason
        _end(self.proc)


def _cap_reason(acct: StreamAccount, max_tokens: int) -> str | None:
    if acct.void_reasons:
        return "void"
    if acct.new_tokens >= max_tokens:
        return "token_cap"
    return None


def _pump(proc: subprocess.Popen[str], out: IO[str], acct: StreamAccount, stopper: _Stopper, max_tokens: int) -> None:
    """Copy the session's stdout to out and the account, line by line, until EOF or a cap."""
    if proc.stdout is None:
        raise ArmError("the session has no stdout pipe")
    for line in proc.stdout:
        out.write(line)
        out.flush()
        acct.feed_line(line)
        reason = _cap_reason(acct, max_tokens)
        if reason:
            stopper.stop(reason)
            return


def _start(argv: list[str], ws: Path, env: dict[str, str], err: IO[str]) -> subprocess.Popen[str]:
    try:
        return subprocess.Popen(argv, cwd=str(ws), env=env, stdin=subprocess.DEVNULL,  # nosec B603
                                stdout=subprocess.PIPE, stderr=err, text=True, encoding="utf-8",
                                errors="replace", start_new_session=True)
    except OSError as exc:
        raise ArmError(f"{argv[0]} could not start in {ws}: {exc}") from exc


def _run_session(proc: subprocess.Popen[str], out: IO[str], acct: StreamAccount, *, max_tokens: int,
                 deadline_s: float) -> tuple[str, int]:
    """Pump the session under a deadline timer; (stop reason, exit code)."""
    stopper = _Stopper(proc)
    # The deadline runs on a timer, not between lines: a session that prints nothing (a hung
    # tool call) would otherwise never reach a check.
    timer = threading.Timer(deadline_s, stopper.stop, args=("deadline",), kwargs={"only_if_running": True})
    timer.daemon = True
    timer.start()
    try:
        _pump(proc, out, acct, stopper, max_tokens)
    except BaseException:
        stopper.stop("interrupted")
        raise
    finally:
        timer.cancel()
    return stopper.reason or "finished", proc.wait()


def dispatch(arm_dir: Path, ws: Path, env: dict[str, str], argv: list[str], *, max_tokens: int,
             deadline_s: float) -> dict[str, Any]:
    """Stream the session to arm_dir/stream.jsonl, account it, end it on a cap or the deadline.

    Args:
        arm_dir: where stream.jsonl and stderr.txt are written.
        ws: the session's cwd (the arm's worktree).
        env: the session's complete environment (arm_env plus PATH).
        argv: the session command, normally claude_argv().
        max_tokens: new input tokens (every model) at which the session is ended.
        deadline_s: wall seconds after which the session is ended.

    Returns:
        The stream account's summary plus stop_reason (finished, void, token_cap, deadline),
        process_rc, wall_s and stream. A void stream's reasons are in void_reasons.

    Raises:
        ArmError: the session binary could not be started.
    """
    stream_path, stderr_path = arm_dir / "stream.jsonl", arm_dir / "stderr.txt"
    acct = StreamAccount()
    started = time.monotonic()
    with (stream_path.open("w", encoding="utf-8", newline="\n") as out,
          stderr_path.open("w", encoding="utf-8") as err,
          _start(argv, ws, env, err) as proc):
        stop_reason, rc = _run_session(proc, out, acct, max_tokens=max_tokens, deadline_s=deadline_s)
    summary = acct.summary()
    summary.update({"stop_reason": stop_reason, "process_rc": rc, "wall_s": round(time.monotonic() - started, 1),
                    "stream": str(stream_path)})
    return summary


def bundle(ws: Path, base: str, out: Path) -> int:
    """git bundle of base..HEAD into out; the number of commits bundled (0 writes no file).

    Raises:
        ArmError: base..HEAD cannot be listed (an unknown base would otherwise read as no work).
    """
    count = int(_git_ok(ws, "rev-list", "--count", f"{base}..HEAD") or 0)
    if count == 0:
        return 0
    proc = _git(ws, "bundle", "create", str(out), f"{base}..HEAD")
    if proc.returncode != 0:
        raise ArmError(f"bundle failed: {proc.stderr.strip()}")
    return count


def _dir_bytes(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file() and not f.is_symlink())


def prune(ws: Path, repo: Path, cache_paths: tuple[str, ...]) -> dict[str, Any]:
    """Remove the build caches, then the worktree (run from repo, never from inside ws); keep the branch."""
    freed = 0
    for rel in cache_paths:
        p = ws / rel
        if p.is_dir() and not p.is_symlink():
            freed += _dir_bytes(p)
            shutil.rmtree(p, ignore_errors=True)
    proc = _git(repo, "worktree", "remove", "--force", str(ws))
    if proc.returncode != 0:
        raise ArmError(f"worktree remove failed: {proc.stderr.strip()}")
    shutil.rmtree(ws.parent / f"{ws.name}.githooks", ignore_errors=True)
    return {"cache_bytes": freed, "worktree_removed": not ws.exists()}


def delete_cfg(cfg: Path) -> None:
    """Unlink the credentials copy first, then the whole config dir; never fails on a missing path."""
    try:
        (cfg / ".credentials.json").unlink()
    except OSError:
        pass
    shutil.rmtree(cfg, ignore_errors=True)
