# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Prove the Python a written PLAN contains before it is handed off: extract the ```python blocks
of one plan section, put each at the repository path it names, and run pytest, pyright (strict)
and ruff on them.

Why: a plan's code is read by an implementer who trusts it, so a block that does not import, does
not type-check or fails its own test costs a whole dispatch to find out. Proving it by hand meant
a throwaway driver per plan, and each copy carried the last one's quirks: ruff fed on stdin with
no filename reports an import-order finding that does not exist at the real path, and pyright
handed a path list silently analyses nothing when the project config excludes that path.

Where a block goes, in this order:
  1. a path ending in `.py` in the fence's info string: ```` ```python tests/test_x.py ````
  2. a first line `# file: path` or `# path: path` inside the block
  3. the LAST backticked `.py` path in the prose just above the fence (up to three non-blank
     lines, stopping at a heading or another fence), with a `:12-30` line suffix dropped -
     the shape a plan step like "Create `src/pkg/mod.py`:" already has.
A block with no path is NOT checked and is named as unplaced; blocks naming one path are joined in
order, so a test block and a later test block for the same file become one file. A block is
treated as the whole new content of its file: a fragment meant to be spliced into an existing file
is checked as a file on its own.

How the checks run. The repository is COPIED to a temporary directory (without `.git`, `.venv*`,
`node_modules` and the tool caches) and the blocks are written over the copy, so the real tree is
never touched and the blocks see the project's other modules. Then:
  * pytest - only when a placed path is a test file (`test_*.py` / `*_test.py`), on the project's
    interpreter (`--python`, else `./.venv`'s, else this one) with the copy's `src/` and root
    first on PYTHONPATH, so an editable install of the REAL tree cannot answer for the copy.
    Collecting nothing is a failure, never a pass.
  * pyright - strict, on exactly the placed files (tests included), through a config written into
    the copy; the run must report it analysed every placed file, because a path the project
    config excludes is otherwise "0 errors" over nothing.
  * ruff check - each placed file fed on stdin with `--stdin-filename <its repo path>`, from the
    REAL repository root, so the project's ruff config and first-party detection apply.
Choose with `--check` (repeatable; default all three). A tool is found as `--ruff CMD` /
`--pyright CMD`, else on PATH, else through `uv tool run`; one that cannot be found is exit 2.

Run:
  uv run scripts/plan_codecheck.py --plan PLAN.md --section "Task 3" --repo .
  uv run scripts/plan_codecheck.py --plan PLAN.md --check pytest --python .venv/bin/python --json

Exit codes: 0 = every placed block passed every check that applied and no block was unplaced,
1 = a check failed (the plan's code is wrong), or some block had no path and so was never checked
(`--allow-unplaced` accepts that), 2 = could not check: no such plan or section, a section heading
that matches twice, no python block, no block placed, a path outside the repository, a tool that
cannot be found or crashed, or an internal error. `--json` prints `{ok, command, data, skipped}` on
every exit, 2 included; `ok` is false exactly on exit 2; `skipped` names the unplaced blocks and
any check that did not apply.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from _cli_envelope import EXIT_ERROR, EXIT_NO, EXIT_YES, EnvelopeArgumentParser, emit, guarded

__all__ = [
    "Block", "CheckResult", "PlanError", "copy_repo", "extract_blocks", "main", "place_blocks",
    "run_checks", "section_lines",
]

CHECKS = ("pytest", "pyright", "ruff")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t#]*$")
_PATH_MARKER = re.compile(r"^\s*#\s*(?:file|path)\s*:\s*(\S+\.py)\s*$")
_BACKTICK_PY = re.compile(r"`([^`\s]+?\.py)(?::[0-9][0-9,-]*)?`")
_COPY_SKIP = {".git", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
              ".tox", ".nox"}
_PROSE_LOOKBACK = 3

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class PlanError(Exception):
    """The plan cannot be checked at all (exit 2)."""


@dataclass
class Block:
    """One ```python block: its 1-based opening line, info string, text and placement."""

    line: int
    info: str
    text: str
    prose: list[str] = field(default_factory=list)
    path: str | None = None


@dataclass
class CheckResult:
    """The outcome of one check: pass, fail, error (could not run) or skipped."""

    check: str
    status: str
    detail: str = ""
    argv: list[str] = field(default_factory=list)


def _split_lines(text: str) -> list[str]:
    # Newline only: splitlines() also breaks on form feed and U+2028, which would renumber lines.
    lines = text.replace("\r\n", "\n").split("\n")
    return lines[:-1] if lines and lines[-1] == "" else lines


def section_lines(text: str, section: str | None) -> list[tuple[int, str]]:
    """(1-based line, text) for the section whose heading contains `section`, or the whole file.

    The section runs to the next heading of the same or a higher level outside a code fence.

    Raises:
        PlanError: no heading matches, or more than one does.
    """
    numbered = list(enumerate(_split_lines(text), start=1))
    if section is None:
        return numbered
    headings = []
    fence = None
    for number, line in numbered:
        fence, fenced = _fence_step(fence, line)
        heading = None if fenced else _HEADING.match(line)
        if heading:
            headings.append((number, len(heading.group(1)), heading.group(2) or ""))
    hits = [h for h in headings if section in h[2]]
    if not hits:
        raise PlanError(f"no heading contains {section!r}")
    if len(hits) > 1:
        where = ", ".join(f"line {h[0]}" for h in hits)
        raise PlanError(f"{len(hits)} headings contain {section!r} ({where}); name it exactly")
    start, level, _ = hits[0]
    end = next((n for n, lvl, _ in headings if n > start and lvl <= level), len(numbered) + 1)
    return [(n, line) for n, line in numbered if start <= n < end]


def _fence_step(fence: str | None, line: str) -> tuple[str | None, bool]:
    """Advance CommonMark fence state; return (new state, whether `line` is fence or fenced)."""
    match = _FENCE.match(line)
    if fence is None:
        if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
            return match.group(1), True
        return None, False
    if (match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence)
            and not match.group(2).strip()):
        return None, True
    return fence, True


def _is_python(info: str) -> bool:
    words = info.strip().split()
    return bool(words) and words[0].lower() in ("python", "py", "python3")


def extract_blocks(lines: Sequence[tuple[int, str]]) -> list[Block]:
    """Every ```python block in `lines`, with the prose lines that precede its opener."""
    blocks: list[Block] = []
    fence = None
    current: Block | None = None
    body: list[str] = []
    prose: list[str] = []
    for number, line in lines:
        before = fence
        fence, _fenced = _fence_step(fence, line)
        if before is None and fence is not None:
            opener = _FENCE.match(line)
            info = opener.group(2) if opener else ""
            current = Block(number, info.strip(), "", prose[-_PROSE_LOOKBACK:]) \
                if _is_python(info) else None
            body, prose = [], []
        elif before is not None and fence is None:
            if current is not None:
                current.text = "\n".join(body) + "\n"
                blocks.append(current)
            current = None
        elif fence is not None:
            body.append(line)
        elif _HEADING.match(line):
            prose = []
        elif line.strip():
            prose.append(line)
    return blocks


def _placement(block: Block) -> str | None:
    for word in block.info.split()[1:]:
        candidate = word.split("=", 1)[-1].strip("\"'")
        if candidate.endswith(".py"):
            return candidate
    first = block.text.split("\n", 1)[0]
    marker = _PATH_MARKER.match(first)
    if marker:
        return marker.group(1)
    for line in reversed(block.prose):
        found = _BACKTICK_PY.findall(line)
        if found:
            return found[-1]
    return None


def place_blocks(blocks: list[Block], repo: Path) -> tuple[dict[str, str], list[Block]]:
    """Map repo-relative POSIX path -> joined text, and the blocks with no path.

    Raises:
        PlanError: a block names a path outside the repository.
    """
    placed: dict[str, list[str]] = {}
    unplaced: list[Block] = []
    for block in blocks:
        raw = _placement(block)
        if raw is None:
            unplaced.append(block)
            continue
        rel = PurePosixPath(raw.replace("\\", "/"))
        if rel.is_absolute() or ".." in rel.parts or re.match(r"^[A-Za-z]:", raw):
            raise PlanError(f"block at line {block.line} names {raw!r}, outside the repository")
        block.path = str(rel)
        placed.setdefault(block.path, []).append(block.text)
    return {p: "\n\n".join(texts) for p, texts in placed.items()}, unplaced


def copy_repo(repo: Path, dest: Path) -> Path:
    """Copy `repo` to `dest/repo` without VCS metadata, virtualenvs or caches."""
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in _COPY_SKIP or n.startswith(".venv")}

    target = dest / "repo"
    shutil.copytree(repo, target, symlinks=True, ignore=ignore)
    return target


def _project_python(repo: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    venv = repo / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(venv) if venv.is_file() else sys.executable


def _tool_argv(name: str, explicit: str | None) -> list[str] | None:
    if explicit:
        return shlex.split(explicit, posix=os.name != "nt")
    found = shutil.which(name)
    if found:
        return [found]
    uv = shutil.which("uv")
    return [uv, "tool", "run", name] if uv else None


def _is_test(path: str) -> bool:
    name = PurePosixPath(path).name
    return name.startswith("test_") or name.endswith("_test.py")


def _tail(text: str, lines: int = 25) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def _run(run: Runner, argv: list[str], **kw: object) -> subprocess.CompletedProcess[str]:
    return run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


def _check_pytest(copy: Path, files: list[str], python: str, run: Runner,
                  timeout: float) -> CheckResult:
    tests = [f for f in files if _is_test(f)]
    if not tests:
        return CheckResult("pytest", "skipped", "no placed path is a test file")
    # An interpreter without pytest fails every run with exit 1, which would read as the PLAN's
    # failure; under `uv run` with no ./.venv this interpreter is uv's throwaway one, which has none.
    probe = _run(run, [python, "-c", "import pytest"], cwd=copy, timeout=timeout)
    if probe.returncode != 0:
        return CheckResult("pytest", "error",
                           f"{python} has no pytest; pass --python with the project's interpreter",
                           [python, "-c", "import pytest"])
    paths = [str(copy / "src"), str(copy)] + [p for p in [os.environ.get("PYTHONPATH")] if p]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(paths), "PYTHONDONTWRITEBYTECODE": "1"}
    argv = [python, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests]
    proc = _run(run, argv, cwd=copy, env=env, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        return CheckResult("pytest", "pass", _tail(out, 3), argv)
    if proc.returncode in (1, 2, 5):            # failed, collection error, collected nothing
        return CheckResult("pytest", "fail", _tail(out), argv)
    return CheckResult("pytest", "error", f"pytest exited {proc.returncode}: {_tail(out)}", argv)


def _check_pyright(copy: Path, files: list[str], python: str, tool: list[str] | None, run: Runner,
                   timeout: float) -> CheckResult:
    if tool is None:
        return CheckResult("pyright", "error", "pyright not found (on PATH, or via uv)")
    config = {"include": files, "typeCheckingMode": "strict",
              "extraPaths": ["src"] if (copy / "src").is_dir() else []}
    cfg = copy / "pyrightconfig.json"
    cfg.write_text(json.dumps(config), encoding="utf-8")
    argv = [*tool, "--outputjson", "--pythonpath", python, "-p", str(cfg)]
    proc = _run(run, argv, cwd=copy, timeout=timeout)
    try:
        report = json.loads(proc.stdout or "")
        summary = report["summary"]
    except (ValueError, KeyError, TypeError):
        return CheckResult("pyright", "error",
                           f"pyright exited {proc.returncode} without a report: "
                           f"{_tail((proc.stdout or '') + (proc.stderr or ''))}", argv)
    analysed = int(summary.get("filesAnalyzed", 0))
    if analysed < len(files):
        return CheckResult("pyright", "error",
                           f"pyright analysed {analysed} of {len(files)} placed files", argv)
    errors = [f"{Path(d.get('file', '')).name}:{d['range']['start']['line'] + 1}: {d.get('message')}"
              for d in report.get("generalDiagnostics", []) if d.get("severity") == "error"]
    if errors:
        return CheckResult("pyright", "fail", "\n".join(errors[:25]), argv)
    return CheckResult("pyright", "pass", f"{analysed} files, 0 errors", argv)


def _check_ruff(repo: Path, placed: dict[str, str], tool: list[str] | None, run: Runner,
                timeout: float) -> CheckResult:
    if tool is None:
        return CheckResult("ruff", "error", "ruff not found (on PATH, or via uv)")
    findings = []
    for rel, text in placed.items():
        argv = [*tool, "check", "--stdin-filename", rel, "-"]
        proc = _run(run, argv, cwd=repo, input=text, timeout=timeout)
        if proc.returncode == 1:
            findings.append(f"{rel}:\n{_tail(proc.stdout or '')}")
        elif proc.returncode != 0:
            return CheckResult("ruff", "error",
                               f"ruff exited {proc.returncode} on {rel}: {_tail(proc.stderr or '')}",
                               argv)
    if findings:
        return CheckResult("ruff", "fail", "\n".join(findings))
    return CheckResult("ruff", "pass", f"{len(placed)} files clean")


def run_checks(repo: Path, placed: dict[str, str], checks: Sequence[str], *, python: str | None = None,
               ruff: str | None = None, pyright: str | None = None, timeout: float = 600.0,
               run: Runner = subprocess.run) -> list[CheckResult]:
    """Write `placed` over a copy of `repo` and run each named check. Never touches `repo`."""
    results: list[CheckResult] = []
    # ignore_cleanup_errors: on Windows a child that still holds a file open would otherwise turn
    # a finished check into a crash at cleanup.
    with tempfile.TemporaryDirectory(prefix="plan_codecheck-", ignore_cleanup_errors=True) as tmp:
        copy = copy_repo(repo, Path(tmp))
        for rel, text in placed.items():
            target = copy / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="")
        files = sorted(placed)
        interp = _project_python(repo, python)
        for check in checks:
            try:
                if check == "pytest":
                    results.append(_check_pytest(copy, files, interp, run, timeout))
                elif check == "pyright":
                    results.append(_check_pyright(copy, files, interp,
                                                  _tool_argv("pyright", pyright), run, timeout))
                else:
                    results.append(_check_ruff(repo, placed, _tool_argv("ruff", ruff), run,
                                               timeout))
            except (OSError, subprocess.SubprocessError) as exc:
                results.append(CheckResult(check, "error", f"{type(exc).__name__}: {exc}"))
    return results


def _verdict(results: list[CheckResult], unplaced: list[Block], allow_unplaced: bool) -> int:
    if any(r.status == "error" for r in results):
        return EXIT_ERROR
    if any(r.status == "fail" for r in results) or (unplaced and not allow_unplaced):
        return EXIT_NO
    return EXIT_YES


def _report(results: list[CheckResult], placed: dict[str, str], unplaced: list[Block]) -> None:
    for rel in sorted(placed):
        print(f"placed   {rel}")
    for block in unplaced:
        print(f"UNPLACED block at line {block.line} (no path: info string, # file:, or a "
              f"backticked .py above it)")
    for r in results:
        print(f"{r.status.upper():8} {r.check}")
        if r.detail and r.status != "pass":
            print("    " + r.detail.replace("\n", "\n    "))


@guarded("plan_codecheck")
def main(argv: Sequence[str] | None = None) -> int:
    ap = EnvelopeArgumentParser(prog="plan_codecheck", envelope_command="plan_codecheck",
                                description="Run pytest, pyright and ruff on a plan's python blocks.")
    ap.add_argument("--plan", required=True, help="the plan markdown file")
    ap.add_argument("--section", help="text of the heading whose section to check [whole file]")
    ap.add_argument("--repo", default=".", help="repository root the paths are relative to [.]")
    ap.add_argument("--check", action="append", choices=CHECKS,
                    help="a check to run (repeatable) [all three]")
    ap.add_argument("--python", help="interpreter for pytest/pyright [./.venv's, else this one]")
    ap.add_argument("--ruff", help="ruff command [ruff on PATH, else uv tool run ruff]")
    ap.add_argument("--pyright", help="pyright command [pyright on PATH, else uv tool run pyright]")
    ap.add_argument("--timeout", type=float, default=600.0, help="seconds per tool run [600]")
    ap.add_argument("--allow-unplaced", action="store_true",
                    help="a block with no path does not by itself make the run exit 1")
    ap.add_argument("--json", action="store_true", help="print the {ok,command,data,skipped} envelope")
    args = ap.parse_args(argv)

    def fail(message: str) -> int:
        if args.json:
            return emit(EXIT_ERROR, "plan_codecheck", error=message)
        print(f"plan_codecheck: {message}", file=sys.stderr)
        return EXIT_ERROR

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        return fail(f"--repo {args.repo}: not a directory")
    if args.timeout <= 0:
        return fail("--timeout must be positive")
    try:
        text = Path(args.plan).read_text(encoding="utf-8-sig")
        blocks = extract_blocks(section_lines(text, args.section))
        if not blocks:
            raise PlanError("no ```python block in " + (repr(args.section) if args.section
                                                        else "the plan"))
        placed, unplaced = place_blocks(blocks, repo)
        if not placed:
            raise PlanError(f"none of the {len(blocks)} python blocks names a path")
    except (OSError, UnicodeDecodeError, PlanError) as exc:
        return fail(str(exc))
    checks = list(dict.fromkeys(args.check or CHECKS))
    results = run_checks(repo, placed, checks, python=args.python, ruff=args.ruff,
                         pyright=args.pyright, timeout=args.timeout)
    code = _verdict(results, unplaced, args.allow_unplaced)
    skipped = [f"block at line {b.line}: no path" for b in unplaced]
    skipped += [f"{r.check}: {r.detail}" for r in results if r.status == "skipped"]
    if args.json:
        data = {"placed": sorted(placed), "unplaced": [b.line for b in unplaced],
                "checks": [r.__dict__ for r in results]}
        error = next((r.detail for r in results if r.status == "error"), None)
        return emit(code, "plan_codecheck", data, skipped=skipped, error=error)
    _report(results, placed, unplaced)
    return code


if __name__ == "__main__":
    sys.exit(main())
