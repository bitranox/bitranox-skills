"""The abtest.toml profile: tomllib plus frozen dataclasses, every problem reported at once.

Stdlib on purpose (design S5.6): the repo gate runs this suite with no PEP 723 dependency, so a
Pydantic import would fail the gate. Commands are argv lists and run without a shell.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
NAME_RE = re.compile(r"^V[0-9A-Za-z_-]{1,20}$")
DEFAULT_ENV_KEEP = ("PATH", "LANG", "LC_ALL", "TERM", "TZ")
DEFAULT_HOME_LINKS = (".cargo", ".rustup", ".local", ".cache", ".gitconfig")
# [run] sandbox: "bwrap" runs the session inside a bubblewrap sandbox the harness builds;
# "bwrap-host-proc" is the same sandbox with the host's /proc bound read-only, for hosts that
# refuse a private one (an LXC container with lxcfs); "none" is an explicit opt-out that every
# journal row and score then shows (user decisions 2026-11-04: refuse a live arm unless the
# profile names its sandbox; offer the host-/proc variant). There is no default on purpose.
SANDBOX_BWRAP, SANDBOX_BWRAP_HOST_PROC, SANDBOX_NONE = "bwrap", "bwrap-host-proc", "none"
SANDBOX_BWRAP_KINDS = (SANDBOX_BWRAP, SANDBOX_BWRAP_HOST_PROC)
SANDBOX_VALUES = (*SANDBOX_BWRAP_KINDS, SANDBOX_NONE)
SANDBOX_MISSING = ('run.sandbox: missing; a live arm runs only inside a sandbox: set sandbox = "bwrap" '
                   '(in an LXC container "bwrap-host-proc", or sandbox = "none" knowingly, which every '
                   'journal row and score then shows)')

SKELETON = '''# meta-skill-ab-test profile. Fill every <...>; `abtest.py seal` validates it.
[workpiece]
repo = "<absolute path of the real repository>"
base = "<40-char sha every arm starts from>"
task_file = "task.md"

[control]
skills_ref = "<bitranox-skills sha that carries BITRANOX_MEMORY_WRITES>"
skill = "<skill directory name under plugins/bitranox/skills/>"

[[variant]]
name = "V1"
dir = "variants/V1"
changes = ["<one change per entry>"]
markers = []
# A bare arm: remove_skill = true deletes the skill from that arm's frozen plugin instead of
# overlaying it (then leave out dir and keep markers empty). task_file = "task-V1.md" gives the
# arm its own prompt (a bare arm's prompt must not name the missing skill); default: [workpiece].

[floor]
gate = ["make", "test"]
# suite = "acceptance/test_task.py"
# suite_cmd = ["pytest", "{suite}", "-q"]
cache_paths = [".venv", "target"]
timeout_s = 1800

[run]
model = "opus"
n = 3
deadline_s = 14400
max_tokens = 6000000
warmth_tolerance = 0.25
# "bwrap": the session sees the filesystem read-only except its worktree, home, config dir and the
# repo's .git; the real home is hidden. "none" runs it unconfined, and the journal and score say so.
# In an LXC container (lxcfs refuses a private /proc) use "bwrap-host-proc": host /proc read-only.
sandbox = "bwrap"
'''


class ProfileError(ValueError):
    """The profile is not usable; the message lists every problem, one per line."""


@dataclass(frozen=True)
class Workpiece:
    repo: Path
    base: str
    task_file: str


@dataclass(frozen=True)
class Control:
    skills_ref: str
    skill: str


@dataclass(frozen=True)
class Variant:
    """One [[variant]] table.

    Attributes:
        name: V<short id>.
        dir: the overlay directory relative to the run dir; None for a remove_skill variant.
        changes: what the variant changes, one entry each.
        markers: lines the variant's text must carry; always empty for a remove_skill variant.
        remove_skill: the arm runs the plugin WITHOUT the skill under test (a bare arm).
        task_file: this arm's prompt relative to the run dir; None falls back to [workpiece].task_file.
    """

    name: str
    dir: str | None
    changes: tuple[str, ...]
    markers: tuple[str, ...]
    remove_skill: bool = False
    task_file: str | None = None


@dataclass(frozen=True)
class Floor:
    gate: tuple[str, ...]
    suite: str | None
    suite_cmd: tuple[str, ...]
    cache_paths: tuple[str, ...]
    timeout_s: int


@dataclass(frozen=True)
class Run:
    model: str
    n: int
    deadline_s: int
    max_tokens: int
    warmth_tolerance: float
    env_keep: tuple[str, ...]
    home_links: tuple[str, ...]
    # One of SANDBOX_VALUES, or None when the key is missing: a dry run may go ahead, while a
    # live run and a seal refuse it (SANDBOX_MISSING).
    sandbox: str | None = None


@dataclass(frozen=True)
class Profile:
    path: Path
    workpiece: Workpiece
    control: Control
    variants: tuple[Variant, ...]
    floor: Floor
    run: Run

    def arm_names(self) -> list[str]:
        return ["C", *(v.name for v in self.variants)]

    def variant(self, name: str) -> Variant | None:
        """The [[variant]] named `name`, or None (for "C" or an unknown name)."""
        return next((v for v in self.variants if v.name == name), None)

    def task_file_for(self, name: str) -> str:
        """The prompt file of arm `name` relative to the run dir: its own task_file, else the workpiece's."""
        v = self.variant(name)
        return v.task_file if v is not None and v.task_file is not None else self.workpiece.task_file

    def task_files(self) -> list[str]:
        """Every distinct prompt file an arm of this profile reads, the workpiece's first."""
        return list(dict.fromkeys(self.task_file_for(n) for n in self.arm_names()))

    def suite_argv(self) -> list[str] | None:
        if self.floor.suite is None:
            return None
        return [a.replace("{suite}", self.floor.suite) for a in self.floor.suite_cmd]


class _Check:
    """Collects problems so the user sees all of them in one run, not one per edit."""

    def __init__(self) -> None:
        self.problems: list[str] = []

    def str_list(self, table: dict[str, Any], key: str, where: str, *, required: bool = True,
                 default: tuple[str, ...] = ()) -> tuple[str, ...]:
        v = table.get(key)
        if v is None:
            if required:
                self.problems.append(f"{where}.{key}: missing")
            return default
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            self.problems.append(f"{where}.{key}: must be a list of strings (an argv list, never one shell string)")
            return default
        return tuple(v)

    def text(self, table: dict[str, Any], key: str, where: str, *, default: str | None = None) -> str:
        v = table.get(key, default)
        if not isinstance(v, str) or not v or v.startswith("<"):
            self.problems.append(f"{where}.{key}: missing or still a <placeholder>")
            return ""
        return v

    def integer(self, table: dict[str, Any], key: str, where: str, *, minimum: int, default: int | None = None) -> int:
        v = table.get(key, default)
        if not isinstance(v, int) or isinstance(v, bool) or v < minimum:
            self.problems.append(f"{where}.{key}: must be an integer >= {minimum}")
            return minimum
        return v

    def sha(self, table: dict[str, Any], key: str, where: str) -> str:
        v = self.text(table, key, where)
        if v and not SHA_RE.match(v):
            self.problems.append(f"{where}.{key}: must be a full 40-char lowercase sha")
        return v


def _table(c: _Check, data: dict[str, Any], key: str) -> dict[str, Any]:
    """The [key] table, or {} after reporting a wrong shape (an array, a scalar) as a problem."""
    v = data.get(key)
    if v is None:
        return {}
    if not isinstance(v, dict):
        c.problems.append(f"{key}: must be a table")
        return {}
    return v


def _variant_tables(c: _Check, data: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    """The [[variant]] entries with their index; a wrong shape is reported, never an AttributeError."""
    v = data.get("variant")
    if v is None or v == []:
        c.problems.append("variant: at least one [[variant]] is required")
        return []
    if not isinstance(v, list):
        c.problems.append("variant: must be an array of tables ([[variant]])")
        return []
    tables = [(i, t) for i, t in enumerate(v) if isinstance(t, dict)]
    c.problems.extend(f"variant[{i}]: must be a table" for i, t in enumerate(v) if not isinstance(t, dict))
    return tables


def _changes(c: _Check, t: dict[str, Any], where: str) -> tuple[str, ...]:
    """At least one change, none blank and none still the skeleton's <placeholder>."""
    before = len(c.problems)
    changes = c.str_list(t, "changes", where)
    if len(c.problems) > before:
        return changes
    if not changes:
        c.problems.append(f"{where}.changes: at least one change is required")
    for k, entry in enumerate(changes):
        if not entry.strip() or entry.strip().startswith("<"):
            c.problems.append(f"{where}.changes: entry {k} is empty or still a <placeholder>")
    return changes


def _remove_skill(c: _Check, t: dict[str, Any], where: str) -> bool:
    v = t.get("remove_skill", False)
    if not isinstance(v, bool):
        c.problems.append(f"{where}.remove_skill: must be true or false")
        return False
    return v


def _variant_task_file(c: _Check, t: dict[str, Any], where: str) -> str | None:
    v = t.get("task_file")
    if v is None:
        return None
    if not isinstance(v, str) or not _is_inside_relative(v) or v.strip().startswith("<"):
        c.problems.append(f"{where}.task_file: must be a non-empty relative path inside the run dir, "
                          "not absolute and with no '..', when set")
        return None
    return v


def _variant_dir(c: _Check, t: dict[str, Any], where: str, remove_skill: bool) -> str | None:
    """The overlay dir; a remove_skill variant has none, and naming one is refused, never ignored."""
    if not remove_skill:
        return c.text(t, "dir", where)
    if "dir" in t:
        c.problems.append(f"{where}.dir: must be absent when remove_skill = true (the arm has no skill to overlay)")
    return None


def _variant(c: _Check, i: int, t: dict[str, Any], seen: set[str]) -> Variant:
    where = f"variant[{i}]"
    name = c.text(t, "name", where)
    if name and not NAME_RE.match(name):
        c.problems.append(f"{where}.name: must match V<short id> (C is the control)")
    if name in seen:
        c.problems.append(f"{where}.name: duplicate {name!r}")
    seen.add(name)
    remove_skill = _remove_skill(c, t, where)
    markers = c.str_list(t, "markers", where, required=False)
    if remove_skill and markers:
        c.problems.append(f"{where}.markers: must be empty when remove_skill = true (the arm has no skill text)")
    return Variant(name=name, dir=_variant_dir(c, t, where, remove_skill), changes=_changes(c, t, where),
                   markers=markers, remove_skill=remove_skill, task_file=_variant_task_file(c, t, where))


def _variants(c: _Check, data: dict[str, Any]) -> tuple[Variant, ...]:
    seen: set[str] = set()
    return tuple(_variant(c, i, t, seen) for i, t in _variant_tables(c, data))


def _workpiece(c: _Check, wp: dict[str, Any]) -> Workpiece:
    repo_text = c.text(wp, "repo", "workpiece")
    repo = Path(repo_text).expanduser()
    # An empty repo_text is already reported; Path("") is the cwd, whose .git says nothing.
    if repo_text and not repo.is_absolute():
        c.problems.append("workpiece.repo: must be an absolute path")
    elif repo_text and not (repo / ".git").exists():
        c.problems.append(f"workpiece.repo: {repo} is not a git repository")
    return Workpiece(repo=repo.resolve(), base=c.sha(wp, "base", "workpiece"),
                     task_file=c.text(wp, "task_file", "workpiece", default="task.md"))


def _control(c: _Check, ct: dict[str, Any]) -> Control:
    return Control(skills_ref=c.sha(ct, "skills_ref", "control"), skill=c.text(ct, "skill", "control"))


def _is_inside_relative(text: str) -> bool:
    """A non-empty relative path that cannot leave the workpiece: not absolute, no drive, no '..'."""
    posix = PurePosixPath(text.replace("\\", "/"))
    return (bool(text.strip()) and not posix.is_absolute() and not PureWindowsPath(text).drive
            and ".." not in posix.parts)


def _suite(c: _Check, fl: dict[str, Any]) -> str | None:
    suite = fl.get("suite")
    if suite is None:
        return None
    if not isinstance(suite, str) or not _is_inside_relative(suite):
        c.problems.append("floor.suite: must be a non-empty relative path, not absolute and with no '..', when set")
        return None
    return suite


def _floor(c: _Check, fl: dict[str, Any]) -> Floor:
    suite = _suite(c, fl)
    floor = Floor(gate=c.str_list(fl, "gate", "floor"), suite=suite,
                  suite_cmd=c.str_list(fl, "suite_cmd", "floor", required=suite is not None),
                  cache_paths=c.str_list(fl, "cache_paths", "floor", required=False),
                  timeout_s=c.integer(fl, "timeout_s", "floor", minimum=1, default=1800))
    if suite is not None and "{suite}" not in " ".join(floor.suite_cmd):
        c.problems.append("floor.suite_cmd: must contain the {suite} placeholder")
    return floor


def _warmth_tolerance(c: _Check, rn: dict[str, Any]) -> float:
    tol = rn.get("warmth_tolerance", 0.25)
    if not isinstance(tol, (int, float)) or isinstance(tol, bool) or not 0 < tol < 1:
        c.problems.append("run.warmth_tolerance: must be a number in (0, 1)")
        return 0.25
    return float(tol)


def _sandbox(c: _Check, rn: dict[str, Any]) -> str | None:
    """The [run] sandbox value; a missing key is None here, refused only where an arm would run."""
    v = rn.get("sandbox")
    if v is None:
        return None
    if v not in SANDBOX_VALUES:
        c.problems.append('run.sandbox: must be "bwrap", "bwrap-host-proc" or "none"')
        return None
    return str(v)


def _run(c: _Check, rn: dict[str, Any]) -> Run:
    run = Run(model=c.text(rn, "model", "run", default="opus"),
              n=c.integer(rn, "n", "run", minimum=1), deadline_s=c.integer(rn, "deadline_s", "run", minimum=60),
              max_tokens=c.integer(rn, "max_tokens", "run", minimum=1000), warmth_tolerance=_warmth_tolerance(c, rn),
              env_keep=c.str_list(rn, "env_keep", "run", required=False, default=DEFAULT_ENV_KEEP),
              home_links=c.str_list(rn, "home_links", "run", required=False, default=DEFAULT_HOME_LINKS),
              sandbox=_sandbox(c, rn))
    if run.model != "opus":
        c.problems.append("run.model: only 'opus' is allowed (user directive: every arm runs on opus)")
    return run


def load_profile(path: Path) -> Profile:
    """Parse and validate abtest.toml; raise ProfileError listing every problem."""
    c = _Check()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ProfileError(f"{path}: {exc}") from exc
    workpiece = _workpiece(c, _table(c, data, "workpiece"))
    control = _control(c, _table(c, data, "control"))
    variants = _variants(c, data)
    floor = _floor(c, _table(c, data, "floor"))
    run = _run(c, _table(c, data, "run"))
    if c.problems:
        raise ProfileError("\n".join(c.problems))
    return Profile(path=path.resolve(), workpiece=workpiece, control=control, variants=variants, floor=floor, run=run)
