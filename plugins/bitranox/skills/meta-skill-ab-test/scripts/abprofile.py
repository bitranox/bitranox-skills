"""The abtest.toml profile: tomllib plus frozen dataclasses, every problem reported at once.

Stdlib on purpose (design S5.6): the repo gate runs this suite with no PEP 723 dependency, so a
Pydantic import would fail the gate. Commands are argv lists and run without a shell.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
NAME_RE = re.compile(r"^V[0-9A-Za-z_-]{1,20}$")
DEFAULT_ENV_KEEP = ("PATH", "LANG", "LC_ALL", "TERM", "TZ")
DEFAULT_HOME_LINKS = (".cargo", ".rustup", ".local", ".cache", ".gitconfig")

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
    name: str
    dir: str
    changes: tuple[str, ...]
    markers: tuple[str, ...]


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


def _variant(c: _Check, i: int, t: dict[str, Any], seen: set[str]) -> Variant:
    where = f"variant[{i}]"
    name = c.text(t, "name", where)
    if name and not NAME_RE.match(name):
        c.problems.append(f"{where}.name: must match V<short id> (C is the control)")
    if name in seen:
        c.problems.append(f"{where}.name: duplicate {name!r}")
    seen.add(name)
    return Variant(name=name, dir=c.text(t, "dir", where),
                   changes=c.str_list(t, "changes", where), markers=c.str_list(t, "markers", where, required=False))


def load_profile(path: Path) -> Profile:
    """Parse and validate abtest.toml; raise ProfileError listing every problem."""
    c = _Check()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ProfileError(f"{path}: {exc}") from exc
    wp, ct, fl, rn = (data.get(k) or {} for k in ("workpiece", "control", "floor", "run"))
    repo_text = c.text(wp, "repo", "workpiece")
    repo = Path(repo_text).expanduser()
    # An empty repo_text is already reported; Path("") is the cwd, whose .git says nothing.
    if repo_text and not (repo / ".git").exists():
        c.problems.append(f"workpiece.repo: {repo} is not a git repository")
    base = c.text(wp, "base", "workpiece")
    if base and not SHA_RE.match(base):
        c.problems.append("workpiece.base: must be a full 40-char lowercase sha")
    workpiece = Workpiece(repo=repo.resolve(), base=base, task_file=c.text(wp, "task_file", "workpiece", default="task.md"))
    ref = c.text(ct, "skills_ref", "control")
    if ref and not SHA_RE.match(ref):
        c.problems.append("control.skills_ref: must be a full 40-char lowercase sha")
    control = Control(skills_ref=ref, skill=c.text(ct, "skill", "control"))
    seen: set[str] = set()
    variants = tuple(_variant(c, i, t, seen) for i, t in enumerate(data.get("variant") or []))
    if not variants:
        c.problems.append("variant: at least one [[variant]] is required")
    suite = fl.get("suite")
    if suite is not None and (not isinstance(suite, str) or not suite):
        c.problems.append("floor.suite: must be a non-empty relative path when set")
        suite = None
    floor = Floor(gate=c.str_list(fl, "gate", "floor"), suite=suite,
                  suite_cmd=c.str_list(fl, "suite_cmd", "floor", required=suite is not None),
                  cache_paths=c.str_list(fl, "cache_paths", "floor", required=False),
                  timeout_s=c.integer(fl, "timeout_s", "floor", minimum=1, default=1800))
    if suite is not None and "{suite}" not in " ".join(floor.suite_cmd):
        c.problems.append("floor.suite_cmd: must contain the {suite} placeholder")
    tol = rn.get("warmth_tolerance", 0.25)
    if not isinstance(tol, (int, float)) or isinstance(tol, bool) or not 0 < tol < 1:
        c.problems.append("run.warmth_tolerance: must be a number in (0, 1)")
        tol = 0.25
    run = Run(model=c.text(rn, "model", "run", default="opus"),
              n=c.integer(rn, "n", "run", minimum=1), deadline_s=c.integer(rn, "deadline_s", "run", minimum=60),
              max_tokens=c.integer(rn, "max_tokens", "run", minimum=1000), warmth_tolerance=float(tol),
              env_keep=c.str_list(rn, "env_keep", "run", required=False, default=DEFAULT_ENV_KEEP),
              home_links=c.str_list(rn, "home_links", "run", required=False, default=DEFAULT_HOME_LINKS))
    if run.model != "opus":
        c.problems.append("run.model: only 'opus' is allowed (user directive: every arm runs on opus)")
    if c.problems:
        raise ProfileError("\n".join(c.problems))
    return Profile(path=path.resolve(), workpiece=workpiece, control=control, variants=variants, floor=floor, run=run)
