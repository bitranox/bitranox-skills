# meta-skill-ab-test Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `meta-skill-ab-test`, a bitranox skill plus scripts that compares the shipped version of a skill against modified variants on one real task in the real repository, judging the resulting code pairwise, its exact cost and an executed floor, while keeping every arm's work on a branch.

**Architecture:** One CLI (`abtest.py`) drives a run directory: a TOML profile and a sealed pre-registration, then serial interleaved arms, each a nested git worktree of the workpiece repository with its own Claude config dir and a frozen plugin checkout, each scored from its stream and the profile's floor commands, then a pairwise opus judge over blinded diffs, labels, and a report. A new plugin switch (`BITRANOX_MEMORY_WRITES=off`) keeps arms from writing the shared memory store; a snapshot guard is the backstop.

**Tech Stack:** Python 3.14 (the plugin floor; stdlib only in gate-tested scripts: `tomllib`, `dataclasses`, `subprocess`, `hashlib`), `claude` CLI (`-p --output-format stream-json`), `claude plugin marketplace add` / `plugin install`, git worktrees and bundles, the Claude Agent SDK via one PEP 723 script (`uv run`) for the judge, pytest with the repo's CI dependency set.

## Global Constraints

- The design is FROZEN at bitranox-skills commit `24273510` (`docs/plans/2026-11-03-ab-test-skill-design.md`, sections 1-4 plus the section 5 amendments). Every task cites it as "design SN"; a task that needs the design changed STOPS and reports.
- Authoring (this plan, SKILL.md text, the pre-registration, an acceptance suite) is done in the fable session itself; every implementer subagent is dispatched with `model: "opus"`; every arm and judge runs `--model opus` and is voided when its init record names another model (user directive 2026-11-02, re-confirmed 2026-11-03).
- No `Co-Authored-By`, no `Generated with` footer, no Claude or AI mention in any commit message, file or PR (tree-top iron rule); the two reminders that ask for one are overridden by it.
- Commit messages are written to a file and passed with `git commit -F <file> -- <paths>`; never `-m`, never a bare commit in the shared checkout; the message file is written in its OWN earlier command, not the commit's.
- Every shipped `.py` under `plugins/bitranox/` has a sibling `tests/test_<script>.py`, and the suite runs with CI's dependency set: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest <dir> -q` (repo CLAUDE.md). A skill script imports only the stdlib at module level; a third-party import (the Agent SDK) lives in a PEP 723 script that is run via `uv run` and whose tests `pytest.importorskip` it.
- Every change under `plugins/bitranox/` ships with a version bump made by `uv run plugins/bitranox/hooks/bump_version.py --part <minor|patch> --changelog <notes.md>` from the repo root (it bumps `plugin.json`, `pyproject.toml` and adds the CHANGELOG section), then `python3 plugins/bitranox/hooks/repo-gate.py --ci` must pass, then commit + push + `uv run <plugin cache>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD` in the FOREGROUND. A new skill also regenerates `skill_triggers.json` (`build_skill_triggers.py`), `docs/skills.md` (`build_skill_docs.py`) and the README skill count.
- ASCII punctuation only in every file this plan creates (no em dashes, no curly quotes); the tell-sweep hook blocks a file that carries one.
- Marketplace work happens in a dedicated worktree created from `origin/master` after a fetch (never in the shared checkout), and pushes go `HEAD:master`.
- Linux only. Windows is untested and the skill text says so.
- Secrets: the arm's credentials copy (`~/.claude/.credentials.json`, mode 0600) is copied into the arm's config dir and DELETED when the arm ends; no script prints, logs or echoes it; no test reads the real file.
- Private names stay out of this public repo: the testing workpiece is named only by its role ("the workpiece repository", "the plan branch"); the profile for the first real experiment lives in the run directory outside every repo, never here.

---

## Frozen inputs

| Input                                                 | Where                                                                                                                                                                                                                              | Pin        |
|-------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| Design, sections 1-5                                  | `docs/plans/2026-11-03-ab-test-skill-design.md`                                                                                                                                                                                    | `24273510` |
| Prototype harness (arm runner, accounting, installer) | `../RESEARCH/workflow/probes/abx/` on `main`: `abxlib.py`, `run_arm.py`, `make_variant.py`, `interleave.py`                                                                                                                        | `1d9b424`  |
| Prototype scorers (SDK guard, SDK call, fix cost)     | `../RESEARCH` branch `abx-better-work-axis`: `sdk_guard.py`, `abx_sdk_call.py`, `fixeslib.py`, `fixes_extract.py`, `fixes_cost.py`                                                                                                 | `2838fe1`  |
| Plugin seams the switch touches                       | `plugins/bitranox/hooks/{self_improve_signals,memory_engine,mod_bridge,session-start,self-improve-gate,self-improve-audit,subagent-capture}.py`, `skills/meta-self-improve/contrib_queue.py`, `skills/meta-dream-tree/factedit.py` | `4019c1ca` |
| Testing workpiece for M5 (kept from the paused A/B)   | the workpiece repository's branch `abx-vnc-diag-base` at `033e25e8a`, plan `docs/plans/2026-11-02-vnc-diag-overlay.md`                                                                                                             | branch     |

## Elephants in the room (reviewed before planning)

1. **Scope for one builder.** M0 (probe) half a day; M1 (switch) one day; M2 (harness core) two days; M3 (judge) two days; M4 (skill text, liveness pair) one day; M5 (first experiment) is wall-clock, not work. Six days of build is more than a day, so this plan has three altitudes and details tasks only to checkpoint 2.
2. **Riskiest assumptions, ranked.** (a) A nested worktree under `<repo>/.claude/worktrees/` gives the arm the real cascade and the plugin's SessionStart does not write into the shared tree: UNMEASURED, decided by the M0 probe (checkpoint 1). (b) The memory-writes switch stops every tree write: proven by one test per write path plus the probe re-run after M1. (c) `claude plugin marketplace add <dir>` + `plugin install` into a foreign `CLAUDE_CONFIG_DIR` still works on the current CLI (measured on 2.1.317 in the prototype; re-measured by M2's dry run). (d) The pairwise blind judge separates variants: decided by M4's liveness pair, after checkpoint 2. (e) A judged advantage can be priced from the stream by its commit: holds only when arms commit per task; otherwise the charge is 0 and flagged (design S5.2).
3. **Over-engineering versus need.** Kept: the resume journal (a 12-arm run is 12 to 22 h and WILL be interrupted), the quota check (the CLI reports a 429 as a login failure), the finalists phase (user decision), the rubric beside the verdict (user decision). Cut: parallel arms (user chose serial), the prototype's mutation battery and absolute judge (design S5.7), the idea-marker variant builder, Windows.
4. **Adopt versus rebuild.** Adopted by port, about 900 lines: stream accounting, headless env and plugin install, workspace creation, dispatch with caps, the SDK guard and call, the input-side price table and span cost, git candidate extraction. Rebuilt small: the scheduler (inside `abtest.py run`), the scorer (profile commands instead of cargo literals), labels and report. Reused as is: `skills/meta-dream-tree/store_manifest.py` (backup/verify of the memory chain) for the snapshot guard.
5. **Does it solve the actual problem?** Yes: the user's words were "keep the code, make a diff, and let the llm decide about which code quality is better, besides exact token usage"; the floor, the branch per arm and the memory switch are what make the result safe to run in the real repository.

## HIGH plan

| Milestone | Deliverable                                                                                                                 | Checkpoint / decision it feeds                                                                                         |
|-----------|-----------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| M0        | Probe: one short headless arm in a nested worktree of the workpiece repo; a JSON record of what loaded and what was written | **Checkpoint 1:** which writes the switch must cover, whether the runner must copy `CLAUDE.local.md` into the worktree |
| M1        | `BITRANOX_MEMORY_WRITES=off` in the plugin: refusals on every write path, quiet nudges, a test per path, docs, bump, push   | none; M2 needs the release so `skills_ref` can carry it                                                                |
| M2 (MVP)  | `abtest.py init / seal / run / score / prune-run` with profile, arms, floor, cost, bundle, prune, journal, guard            | **Checkpoint 2:** dry run on the workpiece base, then ONE real control arm: duration, cost, isolation held             |
| M3        | `abtest.py judge / report`: pairwise + rubric, finalists, fix pricing, labels                                               | the liveness pair decides whether the judge separates                                                                  |
| M4        | SKILL.md (fable), liveness pair on a small Python workpiece (opus), docs regen                                              | release of the skill                                                                                                   |
| M5        | First real experiment: the paused A/B's question on the kept plan branch                                                    | the first KEPT/HARMFUL verdicts; revise the skill from what it teaches                                                 |

**MVP slice:** M2 alone is already useful: serial interleaved arms, exact cost, an executed floor, every arm on a branch. Judging can be done by hand on the bundles until M3 lands.

**Cut:** parallel scheduling, Windows, any absolute quality score outside the pairwise call, a web report.

**Risks:** see elephants 2(a)-(e); plus the cost of M5 (12 arms at the measured 25 USD and 1.0 to 1.8 h each, about 300 USD and 12 to 22 h, before judge cost).

## MID plan

### Components and interfaces

```
plugins/bitranox/skills/meta-skill-ab-test/scripts/
  _ablib.py     envelope(ok, command, data, skipped) -> str; EXIT_YES/NO/ERROR; run(argv, cwd, env, timeout)
                -> CompletedProcess[str]; git(repo, *args); sha256_file(p); tree_hashes(dir) -> dict[str,str];
                rotated_schedule(arms, rounds) -> list[list[str]]; median(xs); dashkey(path); utc_now() -> str
  abprofile.py  @dataclass(frozen) Workpiece, Control, Variant, Floor, Run, Profile; load_profile(path) -> Profile
                (raises ProfileError with every problem listed); Profile.arm_names() -> list[str]
  abstream.py   StreamAccount (feed/per_model/summary, void on a non-opus main model), input_usage(usage) -> dict,
                PRICES, account_stream_file(path) -> StreamAccount, first_cache_read(path) -> int | None
  abarm.py      freeze_variant(run_dir, profile, name, skills_repo) -> Frozen; install_plugin(cfg, frozen, credentials, claude="claude")
                -> dict; make_worktree(repo, base, branch, path) -> dict; arm_env(cfg, home, keep) -> dict;
                dispatch(arm_dir, ws, env, argv, max_tokens, deadline_s) -> dict; bundle(ws, base, out) -> int;
                prune(arm_dir, ws, cache_paths) -> dict; delete_cfg(cfg)
  abguard.py    snapshot(chain_from, out) -> Path; verify(out) -> list[str]; check_login(cfg) -> str
  abscore.py    run_floor(tree, floor, timeout) -> dict; score_arm(arm_dir, profile, peers) -> dict (writes scores.json)
  abtest.py     the CLI; subcommands init, seal, run, score, judge, report, prune-run; journal.jsonl per run
  sdk_guard.py  (ported as is) decide(), make_hook(), disallowed_for()
  ab_sdk_call.py (ported, PEP 723) one guarded SDK call from a job file to an out file
  M3: abjudge.py (pairwise + rubric prompt, blinding, swap), abfixes.py (git candidates, span cost), abverdict.py (labels, report)
```

### Run directory layout (`~/.abtest/<run-id>/`, its own git repo)

```
abtest.toml            the profile (committed at seal)
task.md                the task text (committed at seal)
PREREG.md              hypotheses, decision rule, weights, suite sha256 (committed at seal; amendments append)
variants/<name>/       the modified skill files (overlay onto the control's skill dir)
frozen/<name>/         detached checkout of bitranox-skills at skills_ref with the overlay applied (gitignored)
arms/r<round>-<name>/  cfg/ (deleted at arm end), home/, stream.jsonl, stderr.txt, result.json, scores.json,
                       bundle.git, guard/ (manifest before/after)
journal.jsonl          one line per completed step: {"step": "arm", "round": 1, "arm": "V1", "status": "scored", "at": ...}
```

### Verification per milestone

- M0: `probe-result.json` exists and names: the CLAUDE files the transcript loaded, every path under the tree whose mtime moved during the run, the manifest diff, the cost. Checkpoint 1 is a written decision in `EXECUTION-USER-REVIEW.md`.
- M1: `pytest plugins/bitranox/hooks/tests/test_memory_writes_switch.py` green AND the M0 probe re-run with the released plugin and `BITRANOX_MEMORY_WRITES=off` shows an EMPTY write set in the tree (same instrument, different answer).
- M2: the skill's suite green; `abtest.py run --dry-run` on the workpiece base passes the floor; one real control arm finishes with `result.json`, `scores.json`, a bundle, a branch, a deleted cfg and a clean guard. Checkpoint 2 records duration and cost.
- M3: on the one real arm plus a copy of it as a fake variant, `judge` produces a tie on every criterion in both orders (a control against itself must tie).
- M4: the liveness pair: planted defect LOSES, identical copy TIES; `repo-gate.py --ci` green; CI green on the push.
- M5: a report with one row per variant and a void list; verdicts logged.

## File structure (what each file is responsible for)

- `plugins/bitranox/hooks/self_improve_signals.py` (modify): the one predicate `memory_writes_off()`, the refusal line, the `MemoryWritesOff` exception. Everything else imports it from here.
- `plugins/bitranox/hooks/memory_engine.py` (modify): refuse in every write verb and in the CLI dispatch.
- `plugins/bitranox/hooks/mod_bridge.py` (modify): `memory_add` and `contrib_add` answer the refusal envelope.
- `plugins/bitranox/skills/meta-self-improve/contrib_queue.py` + `hooks/self_improve_signals.add_contribution` (modify): refuse on add.
- `plugins/bitranox/skills/meta-dream-tree/factedit.py` (modify): refuse `apply` before staging anything.
- `plugins/bitranox/hooks/session-start.py`, `self-improve-gate.py`, `self-improve-audit.py`, `subagent-capture.py` (modify): quiet when off.
- `plugins/bitranox/hooks/tests/test_memory_writes_switch.py` (create): one test per write path, one per quiet hook.
- `docs/reference.md` (modify): one table row for the variable.
- `plugins/bitranox/skills/meta-skill-ab-test/` (create): scripts and tests listed above, `SKILL.md` in M4.
- `plugins/bitranox/skill-taxonomy.json`: no change, `meta` exists.

---
## DETAILED plan, milestone M0: the nested-worktree probe

### Task 1: Probe what a headless arm in a nested worktree loads and writes

**Files:**
- Create: `~/.abtest/probe-2026-11-03/probe_nested_worktree.py` (a scratch PEP 723 script OUTSIDE every repository; it names the workpiece path, which must not enter this public repo)
- Create (by running it): `~/.abtest/probe-2026-11-03/probe-result.json`, `stream.jsonl`
- Record: one paragraph in `EXECUTION-USER-REVIEW.md` (checkpoint 1) and the numbers in `OPEN-WORK.md` [27]

**Interfaces:**
- Consumes: the `claude` CLI on PATH; `~/.claude/.credentials.json` (mode 0600); `<plugin cache>/skills/meta-dream-tree/store_manifest.py backup|verify`; the workpiece repository and its plan branch at `033e25e8a`; the bitranox-skills checkout at `origin/master`.
- Produces: `probe-result.json` with keys `init_model`, `session_id`, `total_cost_usd`, `claude_files_loaded` (list of paths), `skill_count`, `worktree_untracked` (git status lines of the worktree after the run), `tree_paths_changed` (paths outside the worktree whose mtime moved), `manifest_verify_rc`, `manifest_verify_tail`.

**Out of scope** - do NOT touch, though they look related:
- `plugins/bitranox/hooks/session-start.py` - the probe MEASURES what it writes today; changing it is Task 7.
- Any file in the workpiece repository other than the throwaway worktree - the probe must leave the repository as it found it.

**STOP conditions** - stop and report rather than improvise, if:
- `claude --version` fails or `~/.claude/.credentials.json` is not mode 0600;
- `claude plugin install` into the scratch config dir exits non-zero (elephant 2c: re-measure before building on it);
- the headless run exits with a stream whose init record names a model that is not an opus id;
- the manifest verify reports a change OUTSIDE the worktree (that is the finding; report it, do not "fix" the store).

- [ ] **Step 1: Write the probe script**

Cost: one turn, startup only. From the prototype's first-message usage (about 20,500 cache-write and 11,500 cache-read tokens at the opus price table) that is about 0.20 USD; unverified until this run records it.

```python
# /// script
# requires-python = ">=3.11"
# ///
"""Probe: one short headless claude run in a NESTED worktree of the workpiece repository.

Measures (a) which CLAUDE.md / CLAUDE.local.md files the session loaded, (b) what the plugin's
SessionStart wrote into the worktree and anywhere else in the tree, (c) the memory-chain manifest
before and after. Writes probe-result.json. Leaves the repository as found (both worktrees removed,
the credentials copy deleted) even when a step fails.
Usage: python3 probe_nested_worktree.py --workpiece <repo> --base <sha> --skills <bitranox-skills checkout>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = max(Path.home().glob(".claude/plugins/cache/bitranox-skills/bitranox/*/"),
             key=lambda d: tuple(int(x) if x.isdigit() else 0 for x in d.name.split(".")))  # text sort picks 10.9 over 10.11
MANIFEST = PLUGIN / "skills" / "meta-dream-tree" / "store_manifest.py"
PROMPT = "Reply with the single word READY and nothing else."
SKIP_DIRS = {".git", "target", "node_modules", ".venv", "__pycache__"}


def run(argv: list[str], cwd: Path | None = None, env: dict[str, str] | None = None,
        timeout: float = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,  # nosec B603
                          encoding="utf-8", errors="replace", timeout=timeout, check=False)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", "-C", str(repo), *args])


def dashkey(path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "-", str(path))


def mtimes(roots: list[Path], skip: set[Path]) -> dict[str, int]:
    """path -> mtime_ns for every file under roots, pruning build dirs and `skip` subtrees."""
    out: dict[str, int] = {}
    for root in roots:
        if root.is_file():
            out[str(root)] = root.stat().st_mtime_ns
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            d = Path(dirpath)
            dirnames[:] = [n for n in dirnames if n not in SKIP_DIRS and d / n not in skip]
            for f in filenames:
                p = d / f
                try:
                    out[str(p)] = p.stat().st_mtime_ns
                except OSError:
                    continue
    return out


def chain_dirs(worktree: Path) -> list[Path]:
    """The worktree's ancestors up to the filesystem root, as CLAUDE files + memory store dirs."""
    roots: list[Path] = []
    for d in [worktree, *worktree.parents]:
        for name in ("CLAUDE.md", "CLAUDE.local.md", ".claude-memory", "OPEN-WORK.md"):
            p = d / name
            if p.exists():
                roots.append(p)
    return roots


def loaded_claude_files(transcript: Path) -> list[str]:
    text = transcript.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(r"Contents of (\S+/CLAUDE(?:\.local)?\.md)", text)))


def install_plugin(cfg: Path, frozen: Path, env: dict[str, str]) -> list[dict]:
    steps = []
    for argv in (["claude", "plugin", "marketplace", "add", str(frozen), "--json"],
                 ["claude", "plugin", "install", "bitranox@bitranox-skills", "--json"]):
        proc = run(argv, cwd=cfg.parent, env=env, timeout=300)
        steps.append({"argv": argv[1:4], "rc": proc.returncode, "tail": proc.stderr.strip()[-300:]})
        if proc.returncode != 0:
            raise RuntimeError(f"{' '.join(argv[:4])} failed rc={proc.returncode}")
    return steps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workpiece", required=True)
    ap.add_argument("--base", required=True, help="full sha of the plan branch's commit")
    ap.add_argument("--skills", required=True, help="bitranox-skills checkout")
    args = ap.parse_args()
    wp = Path(args.workpiece).resolve()
    skills = Path(args.skills).resolve()
    worktree = wp / ".claude" / "worktrees" / "abprobe"
    frozen = HERE / "frozen"
    cfg = HERE / "cfg"
    home = HERE / "home"
    guard = HERE / "guard"
    result: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    try:
        creds = Path.home() / ".claude" / ".credentials.json"
        assert creds.is_file() and (creds.stat().st_mode & 0o777) == 0o600, "credentials not 0600"
        if git(wp, "check-ignore", "-q", ".claude/worktrees/abprobe").returncode != 0:
            with (wp / ".git" / "info" / "exclude").open("a", encoding="utf-8") as f:
                f.write(".claude/worktrees/\n")
            result["exclude_added"] = True
        assert git(wp, "worktree", "add", "--detach", str(worktree), args.base).returncode == 0
        assert git(worktree, "rev-parse", "HEAD").stdout.strip() == args.base
        head = git(skills, "rev-parse", "origin/master").stdout.strip()
        assert git(skills, "worktree", "add", "--detach", str(frozen), head).returncode == 0
        result["skills_ref"] = head
        cfg.mkdir(mode=0o700)
        home.mkdir()
        shutil.copyfile(creds, cfg / ".credentials.json")
        (cfg / ".credentials.json").chmod(0o600)
        env = {"PATH": os.environ["PATH"], "HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg),
               "LANG": os.environ.get("LANG", "C.UTF-8"), "TERM": "dumb"}
        result["install"] = install_plugin(cfg, frozen, env)
        assert run(["python3", str(MANIFEST), "backup", "--from", str(worktree), "--scope", "chain",
                    "--out", str(guard)]).returncode == 0
        before = mtimes(chain_dirs(worktree) + [worktree], skip={worktree / ".git"})
        untracked_before = git(worktree, "status", "--porcelain").stdout
        argv = ["claude", "-p", PROMPT, "--model", "opus", "--output-format", "stream-json",
                "--verbose", "--max-turns", "1", "--dangerously-skip-permissions"]
        t0 = time.monotonic()
        with (HERE / "stream.jsonl").open("w", encoding="utf-8") as out:
            proc = subprocess.run(argv, cwd=worktree, env=env, stdin=subprocess.DEVNULL,  # nosec B603
                                  stdout=out, stderr=subprocess.PIPE, text=True, timeout=900, check=False)
        result["wall_s"] = round(time.monotonic() - t0, 1)
        result["process_rc"] = proc.returncode
        result["stderr_tail"] = proc.stderr[-500:]
        for line in (HERE / "stream.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") == "system" and rec.get("subtype") == "init":
                result["init_model"] = rec.get("model")
                result["session_id"] = rec.get("session_id")
                result["skill_count"] = len(rec.get("skills") or [])
            elif rec.get("type") == "result":
                result["total_cost_usd"] = rec.get("total_cost_usd")
                result["model_usage"] = rec.get("modelUsage")
        transcript = cfg / "projects" / dashkey(worktree) / f"{result.get('session_id')}.jsonl"
        result["claude_files_loaded"] = loaded_claude_files(transcript) if transcript.is_file() else "no transcript"
        after = mtimes(chain_dirs(worktree) + [worktree], skip={worktree / ".git"})
        result["tree_paths_changed"] = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
        result["worktree_untracked"] = sorted(set(git(worktree, "status", "--porcelain").stdout.splitlines())
                                              - set(untracked_before.splitlines()))
        verify = run(["python3", str(MANIFEST), "verify", "--out", str(guard)])
        result["manifest_verify_rc"] = verify.returncode
        result["manifest_verify_tail"] = (verify.stdout + verify.stderr).strip().splitlines()[-6:]
    except Exception as exc:  # noqa: BLE001 - the probe reports, it never hides a failure
        result["error"] = repr(exc)
    finally:
        try:
            (cfg / ".credentials.json").unlink()
        except OSError:
            pass
        shutil.rmtree(cfg, ignore_errors=True)
        git(wp, "worktree", "remove", "--force", str(worktree))
        git(skills, "worktree", "remove", "--force", str(frozen))
        (HERE / "probe-result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: result.get(k) for k in ("init_model", "total_cost_usd", "claude_files_loaded",
                                                  "tree_paths_changed", "worktree_untracked",
                                                  "manifest_verify_rc", "error")}, indent=1))
    return 0 if "error" not in result else 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it**

Run (from the probe dir, the workpiece path substituted; the credentials file is read by the script, never printed):
`cd ~/.abtest/probe-2026-11-03 && PYTHONUNBUFFERED=1 python3 probe_nested_worktree.py --workpiece <workpiece-repo> --base 033e25e8adc43116b7c16a3ff57629aaa744a3df --skills <bitranox-skills checkout> > probe.log 2>&1; echo RC=$? >> probe.log`
Expected: `RC=0`; `probe-result.json` has `init_model` starting with `claude-opus`, `claude_files_loaded` a non-empty list, `manifest_verify_rc` 0 or 1.

- [ ] **Step 3: Read the three answers and record checkpoint 1**

Read `probe-result.json`:
1. `claude_files_loaded`: does it list the workpiece repo's own `CLAUDE.local.md` (the project-level memory index)? If NOT, M2's `make_worktree` (Task 12) copies `<repo>/CLAUDE.local.md` into the worktree before the arm starts (design S5.1).
2. `worktree_untracked` and `tree_paths_changed`: every path SessionStart wrote. Expected from the code: a `CLAUDE.local.md` in the worktree if heal created one. Any path OUTSIDE the worktree is a write the switch must stop; add it to Task 3's verb list if the engine made it, or to Task 7 if a hook did.
3. `manifest_verify_rc`: 0 means the chain's pointers and bodies are unchanged.

Append to `EXECUTION-USER-REVIEW.md` (newest first) a dated entry "[27] checkpoint 1: probe result" quoting the three answers and the decision each one makes, and put the cost and wall time into `OPEN-WORK.md` [27]'s `open:` field.

- [ ] **Step 4: Keep the probe artefacts**

`probe_nested_worktree.py`, `probe-result.json` and `stream.jsonl` stay in `~/.abtest/probe-2026-11-03/`; nothing is committed anywhere (the script names the private workpiece path). The same probe is re-run in Task 8 step 6 with the released switch.

## DETAILED plan, milestone M1: the memory-writes switch

All M1 tasks are done in ONE marketplace worktree: `git -C <bitranox-skills checkout> fetch -q origin && git -C <bitranox-skills checkout> worktree add --detach <scratch>/wt-m1 origin/master`. Tests run from that worktree's root with the CI dependency set (Global Constraints). Commit after each task with `-F`; the bump and push are Task 8.

### Task 2: The predicate, the refusal line, the exception

**Files:**
- Modify: `plugins/bitranox/hooks/self_improve_signals.py` (module level, directly below `QUEUE_KEY_PREFIX = "queue_key:"`)
- Test: `plugins/bitranox/hooks/tests/test_memory_writes_switch.py` (create)

**Interfaces:**
- Produces: `MEMORY_WRITES_ENV: str = "BITRANOX_MEMORY_WRITES"`, `MEMORY_WRITES_OFF_LINE: str`, `class MemoryWritesOff(RuntimeError)`, `memory_writes_off(environ: Mapping[str, str] | None = None) -> bool`, `refuse_if_memory_writes_off() -> None` (raises `MemoryWritesOff`). Every later task imports these from `self_improve_signals`.

**Out of scope** - do NOT touch, though they look related:
- `BITRANOX_HOOKS_OFF` in `hooks/run-python.sh` - the dev kill-switch; the new switch must leave every hook RUNNING.
- `~/.claude/.bitranox-memory.json` (memory settings) - the switch is per process, set by a harness, never a stored setting.

**STOP conditions** - stop and report rather than improvise, if:
- `QUEUE_KEY_PREFIX` is not at module level in `self_improve_signals.py`;
- the hooks test conftest cannot import `self_improve_signals` by that name (it does at `4019c1ca`).

- [ ] **Step 1: Write the failing tests**

```python
"""BITRANOX_MEMORY_WRITES=off: every write path refuses with one line, every nudge stays quiet.

One test per path. Each pair has a GREEN control (writes on) beside the RED arm (writes off), so a
test that passes because the path is broken for another reason cannot pass both.
"""
import io
import json
import sys

import pytest

import self_improve_signals as sig

OFF = {"BITRANOX_MEMORY_WRITES": "off"}


@pytest.mark.parametrize("value, expected", [
    ("off", True), ("OFF", True), (" off ", True),
    ("on", False), ("0", False), ("false", False), ("", False),
])
def test_memory_writes_off_reads_exactly_one_spelling(value, expected):
    assert sig.memory_writes_off({"BITRANOX_MEMORY_WRITES": value}) is expected


def test_memory_writes_off_unset_is_on():
    assert sig.memory_writes_off({}) is False


def test_refuse_raises_only_when_off(monkeypatch):
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    sig.refuse_if_memory_writes_off()
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff) as exc:
        sig.refuse_if_memory_writes_off()
    assert "BITRANOX_MEMORY_WRITES=off" in str(exc.value)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/test_memory_writes_switch.py -q`
Expected: FAIL with `AttributeError: module 'self_improve_signals' has no attribute 'memory_writes_off'`

- [ ] **Step 3: Add the predicate**

Below `QUEUE_KEY_PREFIX = "queue_key:"`:

```python
MEMORY_WRITES_ENV = "BITRANOX_MEMORY_WRITES"
MEMORY_WRITES_OFF_LINE = (
    "memory writes are off for this session (BITRANOX_MEMORY_WRITES=off): nothing was recorded. "
    "A harness sets this per run; the lesson belongs in that run's report, not the shared store.")


class MemoryWritesOff(RuntimeError):
    """A memory write path was reached while BITRANOX_MEMORY_WRITES=off.

    Raised at the TOP of every write path (engine verbs, the mod tools, the contribution queue,
    factedit apply) so nothing is staged before the refusal; callers turn it into one line and the
    plugin-wide "could not run" exit (2), or the mod tools' error envelope.
    """


def memory_writes_off(environ=None):
    """True when the process runs with BITRANOX_MEMORY_WRITES=off (case-insensitive, trimmed).

    One spelling only: "0", "false" or a typo leave writes ON, because a switch that fails closed
    on a typo would silently disable the store for a normal session.
    """
    env = os.environ if environ is None else environ
    return (env.get(MEMORY_WRITES_ENV) or "").strip().lower() == "off"


def refuse_if_memory_writes_off():
    """Raise MemoryWritesOff when the switch is set; the first statement of every write path."""
    if memory_writes_off():
        raise MemoryWritesOff(MEMORY_WRITES_OFF_LINE)
```

- [ ] **Step 4: Run the tests to verify they pass**

Same command. Expected: `10 passed`.

- [ ] **Step 5: Commit**

Write `<scratch>/m1-t2.txt` with the subject `self_improve_signals: BITRANOX_MEMORY_WRITES=off predicate and refusal` and one body line naming the three names it adds; then
`git -C <scratch>/wt-m1 add plugins/bitranox/hooks/tests/test_memory_writes_switch.py && git -C <scratch>/wt-m1 commit -F <scratch>/m1-t2.txt -- plugins/bitranox/hooks/self_improve_signals.py plugins/bitranox/hooks/tests/test_memory_writes_switch.py`

### Task 3: The memory engine refuses every write verb

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py`: first statement of `add_with_advice` (line 448), `move_entry` (915), `relocate_entry` (1249), `rename_entry` (1441), `retitle_entry` (1559), `ensure_all_trees` (1771); an early return in `heal` (1173); a module constant `WRITE_VERBS`; one check in `main` right after `args = ap.parse_args(...)` (line 2005)
- Test: `plugins/bitranox/hooks/tests/test_memory_writes_switch.py` (extend)

**Interfaces:**
- Consumes: `sig.refuse_if_memory_writes_off`, `sig.memory_writes_off`, `sig.MEMORY_WRITES_OFF_LINE` (Task 2); `memory_engine` already imports `self_improve_signals as sig` (line 37).
- Produces: `memory_engine.WRITE_VERBS: frozenset[str]`; every listed function raises `sig.MemoryWritesOff` before touching a file; `main([...])` returns 2 and prints `! refused: <line>` on stdout for a write verb; `heal(proj)` returns its normal dict with an extra key `"skipped"` and every other key empty.

**Out of scope** - do NOT touch, though they look related:
- `tree-top` and `lint` verbs - read-only; they stay available to an arm so recall and diagnostics keep working.
- `store-edit-guard.py` and `BITRANOX_MEMORY_ENGINE` - a different switch (admits DIRECT file writes); unrelated.

**STOP conditions** - stop and report rather than improvise, if:
- a listed function's first statement is a docstring followed by a `nonlocal`/decorator pattern the insertion would break (none at `4019c1ca`);
- `heal`'s report literal (line 1182) has keys other than `healed, orphans, invalid_pointers, unreadable, levels`: include every key it has, empty;
- the M0 probe recorded a tree write made by an engine function NOT in this list: add that function here and say so in the commit message.

- [ ] **Step 1: Write the failing tests**

Append to `test_memory_writes_switch.py`:

```python
import memory_engine as ME

FACT = dict(title="Probe fact", hook="When probing the switch, expect a refusal.", body="body", type_="feedback")


def test_engine_add_refuses_when_off_and_writes_when_on(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        ME.add_with_advice(str(tmp_path), **FACT)
    assert not (tmp_path / "CLAUDE.local.md").exists(), "the refusal must come before any write"
    argv = ["add", "--proj", str(tmp_path), "--title", FACT["title"], "--hook", FACT["hook"],
            "--body", FACT["body"], "--type", "feedback"]
    assert ME.main(argv) == 2
    assert sig.MEMORY_WRITES_OFF_LINE in capsys.readouterr().out
    assert not (tmp_path / "CLAUDE.local.md").exists()
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES")
    assert ME.main(argv) == 0, "control: the same add works with the switch unset"
    assert (tmp_path / "CLAUDE.local.md").exists()


@pytest.mark.parametrize("verb", sorted(ME.WRITE_VERBS))
def test_every_write_verb_is_refused_at_the_cli(verb, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert ME.main([verb]) == 2, "the refusal precedes argparse, so required arguments never matter"
    assert "! refused:" in capsys.readouterr().out


def test_heal_is_a_silent_no_op_when_off(tmp_path, monkeypatch):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    report = ME.heal(str(tmp_path))
    assert report["skipped"] == sig.MEMORY_WRITES_OFF_LINE and report["healed"] == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fn, args", [
    (ME.move_entry, ("a", "b", "slug")),
    (ME.relocate_entry, ("a", "b", "slug")),
    (ME.rename_entry, ("a", "slug", "slug2")),
    (ME.retitle_entry, ("a", "slug", "Title")),
    (ME.ensure_all_trees, ()),
])
def test_library_write_functions_raise_first(fn, args, monkeypatch):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        fn(*args)
```

- [ ] **Step 2: Run them to verify they fail**

Same command. Expected: FAIL; `test_every_write_verb...` errors with `AttributeError: ... 'WRITE_VERBS'`, the add test fails at `pytest.raises`.

- [ ] **Step 3: Implement**

Module level, beside `import self_improve_signals as sig`:

```python
WRITE_VERBS = frozenset({"add", "amend-pinned", "move", "relocate", "rename", "retitle", "set-scope",
                         "heal", "ensure-memory-structure", "ensure-all-trees"})
"""CLI verbs that write the store or a pointer block; refused under BITRANOX_MEMORY_WRITES=off."""
```

First statement of `add_with_advice`, `move_entry`, `relocate_entry`, `rename_entry`, `retitle_entry`, `ensure_all_trees` (after the docstring):

```python
    sig.refuse_if_memory_writes_off()
```

In `heal`, after the docstring and before the report literal:

```python
    if sig.memory_writes_off():
        return {"healed": [], "orphans": [], "invalid_pointers": [], "unreadable": [], "levels": 0,
                "skipped": sig.MEMORY_WRITES_OFF_LINE}
```

In `main`, BEFORE `args = ap.parse_args(...)` (argparse exits 2 on a missing required argument before any later check could run; the parser has no global options, so the verb is always the first word):

```python
    raw = sys.argv[1:] if argv is None else argv
    if raw and raw[0] in WRITE_VERBS and sig.memory_writes_off():
        return _refused(sig.MEMORY_WRITES_OFF_LINE)
```

- [ ] **Step 4: Run the switch tests and the engine's own suites**

Run: the same command with `plugins/bitranox/hooks/tests/test_memory_writes_switch.py plugins/bitranox/hooks/tests/test_memory_engine*.py -q`
Expected: all pass (the existing engine tests never set the variable, so they are unaffected).

- [ ] **Step 5: Commit**

Message file subject: `memory_engine: refuse every write verb under BITRANOX_MEMORY_WRITES=off`; body: the verb list and "heal becomes a reported no-op, since SessionStart calls it on every start".
`git -C <scratch>/wt-m1 commit -F <scratch>/m1-t3.txt -- plugins/bitranox/hooks/memory_engine.py plugins/bitranox/hooks/tests/test_memory_writes_switch.py`

### Task 4: The mod tools memory_add and contrib_add answer the refusal

**Files:**
- Modify: `plugins/bitranox/hooks/mod_bridge.py` line 36 (`REFUSALS = (...)`)
- Modify: `plugins/bitranox/hooks/self_improve_signals.py` `add_contribution` (line 700): first statement after the docstring
- Test: `plugins/bitranox/hooks/tests/test_memory_writes_switch.py` (extend)

**Interfaces:**
- Consumes: `sig.MemoryWritesOff` (Task 2); `ME.add_with_advice` now raises (Task 3).
- Produces: `sig.add_contribution(...)` raises `MemoryWritesOff` before reading or writing the queue; `mod_bridge.main()` answers `{"ok": false, "tool": "<name>", "error": {"kind": "MemoryWritesOff", "message": <line>}}` with exit 1 for `memory_add` and `contrib_add`. Task 5 relies on `add_contribution` raising.

**Out of scope** - do NOT touch, though they look related:
- `backlog_add` / `backlog_close` - they edit the repo's `OPEN-WORK.md`, which in an arm is the arm's own worktree, part of its work, never the shared store.
- `hooks/mods/register.ts` - the relay only; its tool descriptions need no change.

**STOP conditions** - stop and report rather than improvise, if:
- `REFUSALS` is not a tuple literal at line 36, or `main()` does not route `REFUSALS` to exit 1;
- `add_contribution`'s first statements read the queue before any point where a raise could go (insert the refusal above them).

- [ ] **Step 1: Write the failing tests**

```python
import mod_bridge


def _bridge(monkeypatch, capsys, tool, payload):
    request = json.dumps({"tool": tool, "input": payload}).encode("utf-8")
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(request), encoding="utf-8"))
    rc = mod_bridge.main()
    return rc, json.loads(capsys.readouterr().out)


def test_mod_memory_add_refuses_when_off(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    monkeypatch.chdir(tmp_path)
    rc, out = _bridge(monkeypatch, capsys, "memory_add",
                      {"level": str(tmp_path), "title": "T", "hook": "When x, do y.", "body": "b", "type": "feedback"})
    assert rc == 1 and out["ok"] is False and out["error"]["kind"] == "MemoryWritesOff"
    assert not (tmp_path / "CLAUDE.local.md").exists()


def test_mod_contrib_add_refuses_when_off(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    rc, out = _bridge(monkeypatch, capsys, "contrib_add", {"what": "w", "target": "skill:x", "why": "y"})
    assert rc == 1 and out["error"]["kind"] == "MemoryWritesOff"
    assert not list((tmp_path / ".claude").rglob("*.contrib.jsonl"))


def test_mod_contrib_add_queues_when_on(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    rc, out = _bridge(monkeypatch, capsys, "contrib_add", {"what": "w", "target": "skill:x", "why": "y"})
    assert rc == 0 and out["data"]["queued"] is True
    assert list((tmp_path / ".claude").rglob("*.contrib.jsonl"))
```

- [ ] **Step 2: Run them to verify they fail**

Expected: the two `when_off` tests fail (`rc == 0` or an `_internal` envelope, since `MemoryWritesOff` is not in `REFUSALS` yet, and `contrib_add` still queues).

- [ ] **Step 3: Implement**

`self_improve_signals.add_contribution`, first statement after its docstring:

```python
    refuse_if_memory_writes_off()
```

`mod_bridge.py` line 36: add `sig.MemoryWritesOff` to the `REFUSALS` tuple.

- [ ] **Step 4: Run the tests to verify they pass**

Same command with `test_memory_writes_switch.py` and the existing `test_mod_bridge*.py` (wherever the gate collects them; `grep -rl "import mod_bridge" plugins/bitranox --include=test_*.py` names them). Expected: all pass.

- [ ] **Step 5: Commit**

Subject: `mod_bridge, add_contribution: refuse under BITRANOX_MEMORY_WRITES=off`.
`git -C <scratch>/wt-m1 commit -F <scratch>/m1-t4.txt -- plugins/bitranox/hooks/mod_bridge.py plugins/bitranox/hooks/self_improve_signals.py plugins/bitranox/hooks/tests/test_memory_writes_switch.py`

### Task 5: contrib_queue.py add prints the one line

**Files:**
- Modify: `plugins/bitranox/skills/meta-self-improve/contrib_queue.py`, the `add` branch (line 327, `try: queued = sig.add_contribution(...)`)
- Test: `plugins/bitranox/skills/meta-self-improve/tests/test_contrib_queue_memory_writes.py` (create)

**Interfaces:**
- Consumes: `sig.add_contribution` raising `sig.MemoryWritesOff` (Task 4); the module's existing `sig` import.
- Produces: `contrib_queue.main(["add", "--what", ..., proj])` returns 2 and prints `! refused: <line>` to stderr when off.

**Out of scope** - do NOT touch, though they look related:
- `list`, `queues`, `shipped`, `rejected` - read-only; they stay available.
- `ship`, `drop`, `claim`, `release` - they also write the queue, but only a maintainer runs them, never an arm; leaving them alone keeps the change to the path an arm can reach. Say so in the commit message.

**STOP conditions** - stop and report rather than improvise, if:
- the `add` branch no longer wraps `sig.add_contribution` in a `try` (then add the `except` beside the OSError one wherever the call is).

- [ ] **Step 1: Write the failing test**

```python
"""contrib_queue add under BITRANOX_MEMORY_WRITES=off: one line, exit 2, nothing queued."""
import pytest

import contrib_queue


def test_add_refuses_when_off_and_queues_when_on(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))      # the queue lives under ~/.claude; keep it here
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert contrib_queue.main(["add", "--what", "teach X", "--target", "skill:y", str(tmp_path)]) == 2
    assert "! refused:" in capsys.readouterr().err
    assert not list((tmp_path / ".claude").rglob("*.contrib.jsonl"))
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES")
    assert contrib_queue.main(["add", "--what", "teach X", "--target", "skill:y", str(tmp_path)]) == 0
    assert len(list((tmp_path / ".claude").rglob("*.contrib.jsonl"))) == 1
```

- [ ] **Step 2: Run it to verify it fails**

Run: the CI command with `plugins/bitranox/skills/meta-self-improve/tests/test_contrib_queue_memory_writes.py -q`
Expected: FAIL with an uncaught `MemoryWritesOff` traceback (Task 4 made the library raise; the CLI does not catch it yet).

- [ ] **Step 3: Implement**

In the `add` branch, add an `except` BEFORE the existing `except OSError`:

```python
        except sig.MemoryWritesOff as exc:
            print("! refused: %s" % exc, file=sys.stderr)
            return 2
```

- [ ] **Step 4: Run the test to verify it passes**

Same command plus `tests/test_contrib_queue.py`. Expected: all pass.

- [ ] **Step 5: Commit**

Subject: `contrib_queue: add refuses under BITRANOX_MEMORY_WRITES=off`.
`git -C <scratch>/wt-m1 commit -F <scratch>/m1-t5.txt -- plugins/bitranox/skills/meta-self-improve/contrib_queue.py plugins/bitranox/skills/meta-self-improve/tests/test_contrib_queue_memory_writes.py`

### Task 6: factedit apply refuses before staging anything

**Files:**
- Modify: `plugins/bitranox/skills/meta-dream-tree/factedit.py`: an import beside `OWN_ENGINE` (line 109), and the first statement of `cmd_apply` (line ~921) and `cmd_apply_batch` (line 1047)
- Test: `plugins/bitranox/skills/meta-dream-tree/tests/test_factedit_memory_writes.py` (create)

**Interfaces:**
- Consumes: `self_improve_signals.memory_writes_off`, `MEMORY_WRITES_OFF_LINE` from the plugin's `hooks/` dir, which factedit already resolves as `OWN_ENGINE.parent`.
- Produces: `factedit.main(["apply", ...])` returns 2 with the line on stderr, and no stage dir is created.

**Out of scope** - do NOT touch, though they look related:
- `factedit show` - read-only.
- The engine subprocess factedit launches - it would refuse anyway (Task 3); this task keeps the refusal BEFORE the staging copy and gives it the same line.

**STOP conditions** - stop and report rather than improvise, if:
- `OWN_ENGINE` is not `Path(__file__).resolve().parents[2] / "hooks" / "memory_engine.py"` (the hooks dir is then found differently; use that);
- `BadInput` does not map to exit 2 in `main` (read how `FactEditError` is reported and use the class that exits 2).

- [ ] **Step 1: Write the failing test**

```python
"""factedit apply under BITRANOX_MEMORY_WRITES=off refuses before it stages a file."""
import factedit


def test_apply_refuses_before_staging(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    body = tmp_path / "body.md"
    body.write_text("new body\n", encoding="utf-8")
    stage = tmp_path / "stage"
    rc = factedit.main(["apply", "--slug", "no-such-fact", "--body-file", str(body),
                        "--stage-dir", str(stage), "--from", str(tmp_path)])
    assert rc == 2
    assert "BITRANOX_MEMORY_WRITES=off" in capsys.readouterr().err
    assert not stage.exists(), "the refusal must precede the staging copy"
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL (rc is 2 for a different reason, "no such fact", with no mention of the switch; the assertion on stderr text fails).

- [ ] **Step 3: Implement**

Beside `OWN_ENGINE`:

```python
sys.path.insert(0, str(OWN_ENGINE.parent))
import self_improve_signals as sig  # noqa: E402 - the hooks dir is only known after OWN_ENGINE
```

First statement of `cmd_apply` and of `cmd_apply_batch`:

```python
    if sig.memory_writes_off():
        raise BadInput(sig.MEMORY_WRITES_OFF_LINE)
```

- [ ] **Step 4: Run the test and factedit's suites**

Same command with `plugins/bitranox/skills/meta-dream-tree/tests/test_factedit*.py`. Expected: all pass.

- [ ] **Step 5: Commit**

Subject: `factedit: apply refuses under BITRANOX_MEMORY_WRITES=off before staging`.
`git -C <scratch>/wt-m1 commit -F <scratch>/m1-t6.txt -- plugins/bitranox/skills/meta-dream-tree/factedit.py plugins/bitranox/skills/meta-dream-tree/tests/test_factedit_memory_writes.py`

### Task 7: The nudges and capture hooks stay quiet

**Files:**
- Modify: `plugins/bitranox/hooks/session-start.py`: `_self_heal` (line ~588), `dream_nudge` (534), `audit_context` (120); extend the `from self_improve_signals import (...)` list (line 30) with `memory_writes_off`
- Modify: `plugins/bitranox/hooks/self-improve-gate.py` `main` (line 323): early return after the event is parsed
- Modify: `plugins/bitranox/hooks/self-improve-audit.py` `main` (line 250): same
- Modify: `plugins/bitranox/hooks/subagent-capture.py` `main` (line 277): same
- Test: `plugins/bitranox/hooks/tests/test_memory_writes_switch.py` (extend)

**Interfaces:**
- Consumes: `memory_writes_off` (Task 2); the conftest aliases `session_start`, `self_improve_gate`, `self_improve_audit`, `subagent_capture` (registered in `hooks/tests/conftest.py` `_HOOK_MODULES`).
- Produces: under the switch, `session_start._self_heal(proj)` writes nothing, `session_start.dream_nudge(proj)` and `session_start.audit_context(proj)` return `None`/empty, and the three `main()`s return 0 printing nothing.

**Out of scope** - do NOT touch, though they look related:
- `recall-memory.py` - recall must keep working in an arm; its ledger lives under the arm's own HOME (`sig._audit_dir()`), so it is not a shared-store write.
- `skill-router.py`, every PreToolUse guard - the arm must behave like a real session.
- `context-watcher.py` - its handover prompts are part of normal behaviour.

**STOP conditions** - stop and report rather than improvise, if:
- `self-improve-audit.py` has no `self_improve_signals` import (it may read the module under another name: use the name it has, or add `import self_improve_signals as sig` beside its other hook imports);
- `audit_context` returns something other than a string or `None` (then return its empty form).

- [ ] **Step 1: Write the failing tests**

```python
import session_start
import self_improve_gate
import self_improve_audit
import subagent_capture


def _event(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('{"type":"user","message":{"role":"user","content":"x"}}\n', encoding="utf-8")
    return {"transcript_path": str(transcript), "cwd": str(tmp_path), "session_id": "s1",
            "hook_event_name": "Stop", "agent_id": "a1", "agent_transcript_path": str(transcript)}


@pytest.mark.parametrize("hook", [self_improve_gate, self_improve_audit, subagent_capture])
def test_capture_hooks_are_silent_when_off(hook, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_event(tmp_path))))
    assert hook.main() == 0
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""
    assert not list((tmp_path / ".claude").rglob("*")), "no audit file, no state file"


def test_session_start_heal_and_nudges_are_quiet_when_off(tmp_path, monkeypatch):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    session_start._self_heal(str(tmp_path))
    assert list(tmp_path.iterdir()) == []
    assert session_start.dream_nudge(str(tmp_path)) is None
    assert not session_start.audit_context(str(tmp_path))
```

- [ ] **Step 2: Run them to verify they fail**

Expected: `_self_heal` writes `CLAUDE.local.md` into `tmp_path` (heal is now a no-op under the switch from Task 3, so this one may already pass: that is fine, it then proves Task 3 from the hook's side); at least one of the three hook `main()`s prints or writes.

- [ ] **Step 3: Implement**

`session-start.py`: add `memory_writes_off` to the `from self_improve_signals import (...)` list; first statement of `_self_heal`, `dream_nudge` and `audit_context`:

```python
    if memory_writes_off():
        return None
```

`self-improve-gate.py` `main`, after the `event` is parsed and before the transcript check:

```python
    if _sig.memory_writes_off():
        return 0
```

`self-improve-audit.py` and `subagent-capture.py` `main`, the same line with their own `sig` name.

- [ ] **Step 4: Run the tests to verify they pass**

Same command with `test_memory_writes_switch.py test_session_start.py test_self_improve_gate*.py`. Expected: all pass.

- [ ] **Step 5: Commit**

Subject: `hooks: self-heal, dream and capture nudges stay quiet under BITRANOX_MEMORY_WRITES=off`.
`git -C <scratch>/wt-m1 commit -F <scratch>/m1-t7.txt -- plugins/bitranox/hooks/session-start.py plugins/bitranox/hooks/self-improve-gate.py plugins/bitranox/hooks/self-improve-audit.py plugins/bitranox/hooks/subagent-capture.py plugins/bitranox/hooks/tests/test_memory_writes_switch.py`

### Task 8: Document, bump, gate, push, and re-run the probe

**Files:**
- Modify: `docs/reference.md` (the environment-variable table at line 62)
- Modify (by the jig): `plugins/bitranox/.claude-plugin/plugin.json`, `pyproject.toml`, `CHANGELOG.md`
- Create (scratch): `<scratch>/m1-notes.md` (the CHANGELOG section body)

**Interfaces:**
- Consumes: everything Tasks 2-7 committed on the worktree.
- Produces: a released plugin version (minor bump, e.g. `10.12.0`) whose `hooks/self_improve_signals.py` contains `BITRANOX_MEMORY_WRITES`; Task 12's `freeze_variant` checks for that name.

**Out of scope** - do NOT touch, though they look related:
- `README.md` skill count and `docs/skills.md` - no skill was added in M1.
- `.github/workflows/ci.yml` - the CI dependency set is unchanged (stdlib only).

**STOP conditions** - stop and report rather than improvise, if:
- `bump_version.py` refuses because origin moved (another session released): `git fetch`, `git merge --ff-only origin/master` in the worktree, re-run the jig;
- `repo-gate.py --ci` reports a failure in a test this plan never touched: stash nothing, run the same test on `origin/master` in a second detached worktree first;
- the probe re-run (step 6) still shows a tree write: that is a finding for the user, not a reason to widen the switch on the spot.

- [ ] **Step 1: Add the reference row**

After the `BITRANOX_HOOKS_OFF=1` row in `docs/reference.md`, one row in the same four columns (the table formatter hook aligns it):

`| BITRANOX_MEMORY_WRITES=off | unset | Every memory write path refuses with one line and exit 2 (engine verbs add/move/relocate/rename/retitle/set-scope/heal/ensure-*, factedit apply, the memory_add and contrib_add tools, contrib_queue add) and the self-improve, dream and audit nudges stay quiet; recall, the router and every guard keep running | A harness that runs headless sessions it must not let write the shared store (meta-skill-ab-test sets it per arm). Never for a normal session: a lesson learned under it is lost unless the harness records it |`

- [ ] **Step 2: Write the CHANGELOG notes and bump**

`<scratch>/m1-notes.md`:

```markdown
### Added

- `BITRANOX_MEMORY_WRITES=off`: every memory write path (the engine's write verbs, `factedit apply`, the `memory_add` and `contrib_add` tools, `contrib_queue add`) refuses with one line and exit 2, and the self-improve, dream and audit nudges stay quiet, while recall, the skill router and every guard keep running. Set per session by a harness that runs headless sessions in a real repository and must keep them out of the shared store; a test per write path proves each refusal and its control.
```

DONE AT THE FRONT OF THE BRANCH (2026-11-03, commit bf1948e5 on ab-m1-switch, 10.11.3 -> 10.12.0): the repo's commit gate refuses any commit under `plugins/` while `plugin.json` equals origin's version, so the bump has to precede the per-task commits, which then ride on it. Skip this step; Step 4 commits only `docs/reference.md`. For M2 make the same bump the first commit of its branch.

- [ ] **Step 3: Run the CI-parity gate**

Run: `python3 plugins/bitranox/hooks/repo-gate.py --ci > <scratch>/m1-gate.log 2>&1; echo RC=$? >> <scratch>/m1-gate.log` and read the file.
Expected: `RC=0`.

- [ ] **Step 4: Commit the bump**

Message file subject: `BITRANOX_MEMORY_WRITES=off: a per-session memory-writes switch (10.12.0)` (the version the jig printed); body: one line per write path covered and "tests: one per path, each with a writes-on control".
`git -C <scratch>/wt-m1 commit -F <scratch>/m1-t8.txt -- docs/reference.md`

- [ ] **Step 5: Push and watch CI**

`git -C <scratch>/wt-m1 push origin HEAD:master` (the pre-push hook runs the suite; several minutes), then in the FOREGROUND:
`uv run <plugin cache>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD` from the worktree.
Expected: exit 0. Then `git -C <main checkout> fetch -q origin && git -C <main checkout> merge --ff-only origin/master`, and `git worktree remove <scratch>/wt-m1`.

- [ ] **Step 6: Re-run the M0 probe with the switch**

Edit `~/.abtest/probe-2026-11-03/probe_nested_worktree.py`: add `"BITRANOX_MEMORY_WRITES": "off"` to the `env` dict (the frozen checkout now comes from the pushed `origin/master`, so it carries the switch). Re-run Step 2 of Task 1 into `probe-after.log`.
Expected: `worktree_untracked == []` and `tree_paths_changed == []` and `manifest_verify_rc == 0`. Record both runs side by side in `EXECUTION-USER-REVIEW.md` under checkpoint 1 (same instrument, two answers), with the cost of each.

---
## DETAILED plan, milestone M2: the harness core (MVP)

All M2 tasks are done in ONE marketplace worktree created from `origin/master` AFTER M1 is pushed (so the frozen checkouts it makes carry the switch). Skill home: `plugins/bitranox/skills/meta-skill-ab-test/`; every path below is relative to the repo root unless it starts with `~`. The test command is the CI one (Global Constraints) with `plugins/bitranox/skills/meta-skill-ab-test/tests/ -q`; it is called "the suite command" below. Commit after each task with `-F`; the bump, gate and push are Task 16.

Two seams carry the whole suite, built in Task 9 and reused by every later task:
- **a fake `claude` binary** on PATH (`tests/fakes/claude`), which answers `--version`, `plugin marketplace add <dir> --json` (copies the dir into `$CLAUDE_CONFIG_DIR/plugins/cache/bitranox-skills/bitranox/<version>/` and records it in `installed_plugins.json`), `plugin install bitranox@bitranox-skills --json` (a no-op after the add) and `-p <prompt> ...` (replays `tests/fixtures/stream-control.jsonl` to stdout, and makes one commit in its cwd so the bundle has content);
- **a scratch workpiece repository** (`scratch_repo` fixture): `git init`, a `CLAUDE.local.md`, a `gate.sh` that exits 1 when a file named `BROKEN` exists, one commit.

### Task 9: `_ablib.py`, the test seams, and the conftest

**Files:**
- Create: `plugins/bitranox/skills/meta-skill-ab-test/scripts/_ablib.py`
- Create: `plugins/bitranox/skills/meta-skill-ab-test/tests/conftest.py`
- Create: `plugins/bitranox/skills/meta-skill-ab-test/tests/fakes/claude` (mode 100755 in the index: `git update-index --chmod=+x`)
- Modify: `.gitattributes` (one line: `plugins/bitranox/skills/meta-skill-ab-test/tests/fakes/* text eol=lf`, beside the subagent-driven-development line that pins its extensionless scripts, for the same reason)
- Create: `plugins/bitranox/skills/meta-skill-ab-test/tests/fixtures/stream-control.jsonl`
- Create: `plugins/bitranox/skills/meta-skill-ab-test/tests/fixtures/skills-repo/` (a two-file plugin: `.claude-plugin/plugin.json`, `hooks/self_improve_signals.py` holding the string `BITRANOX_MEMORY_WRITES`, `skills/demo-skill/SKILL.md`)
- Test: `plugins/bitranox/skills/meta-skill-ab-test/tests/test__ablib.py`

**Interfaces:**
- Produces (every later task imports these from `_ablib`): `EXIT_YES = 0`, `EXIT_NO = 1`, `EXIT_ERROR = 2`; `envelope(command, data, *, ok=True, skipped=None) -> str`; `run(argv, *, cwd=None, env=None, timeout=None) -> CompletedProcess[str]`; `git(repo, *args) -> CompletedProcess[str]`; `sha256_file(path) -> str`; `tree_hashes(root) -> dict[str, str]`; `rotated_schedule(arms, rounds) -> list[list[str]]`; `median(values) -> float`; `dashkey(path) -> str`; `utc_now() -> str`; `read_jsonl(path) -> list[dict]`; `append_jsonl(path, row) -> None`.
- Produces for the tests: fixtures `fake_claude_path` (a dir holding the fake binary, to prepend to PATH), `scratch_repo` (Path of the scratch workpiece, HEAD sha in `scratch_repo / ".base"`), `skills_repo` (a git repo made from `fixtures/skills-repo/` with one commit).

**Out of scope** - do NOT touch, though they look related:
- `skills/compuse-toolbox/scripts/_cli_envelope.py` - the toolbox's envelope helper; this skill ships its own copy because a skill must import nothing from a sibling skill (each is installed on its own).
- The prototype's `parse_cargo_test`, `count_rust_tests`, `ledger_counters`, `transcript_counters` - Rust and prototype-specific; the floor is a profile command (design S3), so none of these are ported.

**STOP conditions** - stop and report rather than improvise, if:
- `git check-attr eol -- plugins/bitranox/skills/meta-skill-ab-test/tests/fakes/claude` prints anything but `lf` after the `.gitattributes` line is added;
- `git update-index --chmod=+x` does not show `100755` in `git ls-files -s` afterwards.

- [ ] **Step 1: Write the conftest, the fake binary and the fixtures**

`tests/conftest.py`:

```python
"""Put scripts/ on sys.path; provide the fake claude binary, a scratch workpiece and a skills repo."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

FIXTURES = HERE / "fixtures"


def _git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@x"})
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,  # nosec B603
                          encoding="utf-8", env=env, check=False)
    assert proc.returncode == 0, f"git {' '.join(args)}: {proc.stderr}"
    return proc.stdout.strip()


@pytest.fixture
def fake_claude_path(tmp_path):
    """A dir holding an executable `claude` that replays fixtures; prepend it to PATH."""
    d = tmp_path / "fakebin"
    d.mkdir()
    target = d / "claude"
    shutil.copyfile(HERE / "fakes" / "claude", target)
    target.chmod(0o755)
    return d


@pytest.fixture
def scratch_repo(tmp_path):
    """A workpiece: one commit, a CLAUDE.local.md, a gate that fails when BROKEN exists."""
    repo = tmp_path / "workpiece"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "CLAUDE.md").write_text("# workpiece\n", encoding="utf-8")
    (repo / "CLAUDE.local.md").write_text("WHAT: scratch workpiece\n", encoding="utf-8")
    (repo / "gate.sh").write_text("#!/bin/sh\ntest ! -e BROKEN\n", encoding="utf-8")
    (repo / "gate.sh").chmod(0o755)
    (repo / ".gitignore").write_text("CLAUDE.local.md\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    (repo / ".base").write_text(_git(repo, "rev-parse", "HEAD"), encoding="utf-8")
    return repo


@pytest.fixture
def skills_repo(tmp_path):
    """A git repo made from fixtures/skills-repo: the two-file plugin a frozen checkout is cut from."""
    repo = tmp_path / "skills"
    shutil.copytree(FIXTURES / "skills-repo", repo)
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "plugin")
    (repo / ".ref").write_text(_git(repo, "rev-parse", "HEAD"), encoding="utf-8")
    return repo


@pytest.fixture
def arm_env_base(fake_claude_path):
    """The PATH an arm sees under test: the fake claude first, then the real PATH (for git)."""
    return {"PATH": f"{fake_claude_path}{os.pathsep}{os.environ['PATH']}"}
```

`tests/fakes/claude` (a Python script; first line `#!/usr/bin/env python3`):

```python
#!/usr/bin/env python3
"""A fake `claude` for the suite. Reads CLAUDE_CONFIG_DIR like the real one.

--version                                   prints a version line
plugin marketplace add <dir> --json         copies <dir> to the config dir's plugin cache
plugin install bitranox@bitranox-skills --json   records the install
-p <prompt> ...                             replays FAKE_CLAUDE_STREAM (a stream.jsonl path) to
                                            stdout and makes one commit in the cwd
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main(argv):
    cfg = Path(os.environ["CLAUDE_CONFIG_DIR"])
    if argv[:1] == ["--version"]:
        print("9.9.9 (fake)")
        return 0
    if argv[:3] == ["plugin", "marketplace", "add"]:
        src = Path(argv[3])
        version = json.loads((src / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        dst = cfg / "plugins" / "cache" / "bitranox-skills" / "bitranox" / version
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git"))
        (cfg / "plugins").mkdir(parents=True, exist_ok=True)
        (cfg / "plugins" / "installed_plugins.json").write_text(json.dumps(
            {"version": 2, "plugins": {"bitranox@bitranox-skills": [{"installPath": str(dst)}]}}),
            encoding="utf-8")
        print(json.dumps({"ok": True}))
        return 0
    if argv[:2] == ["plugin", "install"]:
        print(json.dumps({"ok": True}))
        return 0
    if argv[:1] == ["-p"]:
        stream = Path(os.environ["FAKE_CLAUDE_STREAM"])
        sys.stdout.write(stream.read_text(encoding="utf-8"))
        sys.stdout.flush()
        Path("arm-work.txt").write_text("done by the fake arm\n", encoding="utf-8")
        env = dict(os.environ, GIT_AUTHOR_NAME="arm", GIT_AUTHOR_EMAIL="arm@x",
                   GIT_COMMITTER_NAME="arm", GIT_COMMITTER_EMAIL="arm@x")
        subprocess.run(["git", "add", "arm-work.txt"], check=True, env=env)
        subprocess.run(["git", "commit", "-q", "-m", "Task 1: arm work"], check=True, env=env)
        return 0
    print(f"fake claude: unknown argv {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`tests/fixtures/stream-control.jsonl` (three lines; the numbers are the shape the real CLI emits, small on purpose):

```json
{"type":"system","subtype":"init","model":"claude-opus-5-5","claude_code_version":"9.9.9","session_id":"fake-session-1","permissionMode":"bypassPermissions","plugins":[{"name":"bitranox"}],"skills":["a","b"]}
{"type":"assistant","message":{"id":"msg_1","model":"claude-opus-5-5","usage":{"input_tokens":10,"cache_creation_input_tokens":20000,"cache_read_input_tokens":11000,"output_tokens":50,"cache_creation":{"ephemeral_5m_input_tokens":0,"ephemeral_1h_input_tokens":20000}}}}
{"type":"result","subtype":"success","total_cost_usd":0.25,"num_turns":1,"duration_ms":1200,"modelUsage":{"claude-opus-5-5":{"inputTokens":10,"cacheCreationInputTokens":20000,"cacheReadInputTokens":11000,"outputTokens":50,"costUSD":0.25}}}
```

`tests/fixtures/skills-repo/.claude-plugin/plugin.json`: `{"name": "bitranox", "version": "0.0.1-fixture"}`; `tests/fixtures/skills-repo/hooks/self_improve_signals.py`: one line, `MEMORY_WRITES_ENV = "BITRANOX_MEMORY_WRITES"`; `tests/fixtures/skills-repo/skills/demo-skill/SKILL.md`: a frontmatter block with `name: demo-skill` and one body line `Control text.`

- [ ] **Step 2: Write the failing tests**

```python
"""_ablib: the shared helpers every abtest script uses."""
import json
import os

import pytest

import _ablib as L


def test_envelope_shape():
    d = json.loads(L.envelope("x", {"a": 1}, ok=False, skipped=["s"]))
    assert d == {"ok": False, "command": "x", "data": {"a": 1}, "skipped": ["s"]}


def test_run_never_raises_on_nonzero(tmp_path):
    proc = L.run(["sh", "-c", "echo out; echo err >&2; exit 3"], cwd=tmp_path)
    assert (proc.returncode, proc.stdout.strip(), proc.stderr.strip()) == (3, "out", "err")


def test_git_strips_inherited_git_vars(scratch_repo, monkeypatch):
    monkeypatch.setenv("GIT_DIR", "/nonexistent-git-dir")
    assert L.git(scratch_repo, "rev-parse", "HEAD").stdout.strip() == (scratch_repo / ".base").read_text()


def test_tree_hashes_skip_tests_caches_and_pyc(tmp_path):
    (tmp_path / "SKILL.md").write_text("a", encoding="utf-8")
    (tmp_path / "tests").mkdir(); (tmp_path / "tests" / "t.py").write_text("b", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir(); (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"c")
    (tmp_path / "scripts").mkdir(); (tmp_path / "scripts" / "s.py").write_text("d", encoding="utf-8")
    assert sorted(L.tree_hashes(tmp_path)) == ["SKILL.md", "scripts/s.py"]
    assert L.tree_hashes(tmp_path)["SKILL.md"] == L.sha256_file(tmp_path / "SKILL.md")


def test_rotated_schedule_rotates_the_start():
    assert L.rotated_schedule(["C", "V1", "V2"], 3) == [["C", "V1", "V2"], ["V1", "V2", "C"], ["V2", "C", "V1"]]
    with pytest.raises(ValueError):
        L.rotated_schedule([], 1)


def test_median_even_and_odd():
    assert L.median([3.0, 1.0, 2.0]) == 2.0
    assert L.median([4.0, 1.0, 3.0, 2.0]) == 2.5
    with pytest.raises(ValueError):
        L.median([])


def test_dashkey_replaces_every_non_alphanumeric(tmp_path):
    assert L.dashkey(tmp_path / "a.b_c") == str(tmp_path / "a.b_c").replace("/", "-").replace(".", "-").replace("_", "-")


def test_jsonl_round_trip(tmp_path):
    p = tmp_path / "j.jsonl"
    L.append_jsonl(p, {"step": "a"})
    L.append_jsonl(p, {"step": "b"})
    assert L.read_jsonl(p) == [{"step": "a"}, {"step": "b"}]
    assert L.read_jsonl(tmp_path / "missing.jsonl") == []


def test_fake_claude_answers_version_and_install(fake_claude_path, skills_repo, tmp_path):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    env = {"PATH": f"{fake_claude_path}{os.pathsep}{os.environ['PATH']}", "CLAUDE_CONFIG_DIR": str(cfg)}
    assert L.run(["claude", "--version"], env=env).stdout.startswith("9.9.9")
    assert L.run(["claude", "plugin", "marketplace", "add", str(skills_repo), "--json"], env=env).returncode == 0
    reg = json.loads((cfg / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))
    assert (reg["plugins"]["bitranox@bitranox-skills"][0]["installPath"]).endswith("0.0.1-fixture")
```

- [ ] **Step 3: Run them to verify they fail**

Run: the suite command. Expected: `ModuleNotFoundError: No module named '_ablib'`.

- [ ] **Step 4: Write `_ablib.py`**

```python
"""Shared helpers for the meta-skill-ab-test scripts: envelope, subprocess, git, hashes, schedule.

Stdlib only: the repo gate runs this suite in a bare environment. Every script in this directory
imports from here and from nothing outside the directory, because a skill is installed on its own.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

EXIT_YES = 0
EXIT_NO = 1
EXIT_ERROR = 2
EXCLUDED_TREE_DIRS = {"__pycache__", ".skillwriter", "tests"}


def envelope(command: str, data: Any, *, ok: bool = True, skipped: list[str] | None = None) -> str:
    """The {ok, command, data, skipped} JSON envelope every subcommand prints under --json."""
    return json.dumps({"ok": ok, "command": command, "data": data, "skipped": skipped or []}, indent=1)


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    """Run argv without a shell, capturing UTF-8 text; never raises on a non-zero exit."""
    return subprocess.run(argv, cwd=str(cwd) if cwd else None, env=env, capture_output=True,  # nosec B603
                          text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """git -C repo args..., with every inherited GIT_* variable stripped from the child env."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return run(["git", "-C", str(repo), *args], env=env)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    """{relative posix path: sha256} of the files a skill ships (tests, caches and .pyc excluded)."""
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDED_TREE_DIRS for part in rel.parts) or p.suffix == ".pyc":
            continue
        out[rel.as_posix()] = sha256_file(p)
    return out


def rotated_schedule(arms: list[str], rounds: int) -> list[list[str]]:
    """Round r runs the arms rotated by r, so no arm always goes first (design S1)."""
    if not arms:
        raise ValueError("no arms")
    k = len(arms)
    return [[arms[(i + r) % k] for i in range(k)] for r in range(rounds)]


def median(values: list[float]) -> float:
    s = sorted(values)
    if not s:
        raise ValueError("median of nothing")
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def dashkey(path: Path) -> str:
    """Claude Code's ~/.claude/projects directory name for a cwd: every non-alphanumeric is '-'."""
    return re.sub(r"[^a-zA-Z0-9]", "-", str(path))


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: the suite command. Expected: `9 passed`.

- [ ] **Step 6: Commit**

`git -C <scratch>/wt-m2 add .gitattributes plugins/bitranox/skills/meta-skill-ab-test && git -C <scratch>/wt-m2 update-index --chmod=+x plugins/bitranox/skills/meta-skill-ab-test/tests/fakes/claude && git -C <scratch>/wt-m2 ls-files -s plugins/bitranox/skills/meta-skill-ab-test/tests/fakes/claude` (must print `100755`), then the message file (subject `meta-skill-ab-test: shared helpers, test seams (fake claude, scratch repo)`) and `git -C <scratch>/wt-m2 commit -F <scratch>/m2-t9.txt -- .gitattributes plugins/bitranox/skills/meta-skill-ab-test`.

### Task 10: `abprofile.py`, the profile

**Files:**
- Create: `plugins/bitranox/skills/meta-skill-ab-test/scripts/abprofile.py`
- Test: `plugins/bitranox/skills/meta-skill-ab-test/tests/test_abprofile.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (stdlib `tomllib`).
- Produces: `class ProfileError(ValueError)` (its message lists every problem, one per line); frozen dataclasses `Workpiece(repo: Path, base: str, task_file: str)`, `Control(skills_ref: str, skill: str)`, `Variant(name: str, dir: str, changes: tuple[str, ...], markers: tuple[str, ...])`, `Floor(gate: tuple[str, ...], suite: str | None, suite_cmd: tuple[str, ...], cache_paths: tuple[str, ...], timeout_s: int)`, `Run(model: str, n: int, deadline_s: int, max_tokens: int, warmth_tolerance: float, env_keep: tuple[str, ...], home_links: tuple[str, ...])`, `Profile(path: Path, workpiece, control, variants: tuple[Variant, ...], floor, run)` with `arm_names() -> list[str]` (`["C", <variant names>...]`) and `suite_argv() -> list[str] | None` (`suite_cmd` with `{suite}` substituted); `load_profile(path: Path) -> Profile`; `SKELETON: str` (the TOML `init` writes).

**Out of scope** - do NOT touch, though they look related:
- The judge weights (design S5.4) - they are fixed in `PREREG.md` at `seal` (Task 15), not in the profile, so a later weight change is an append-only amendment.
- A `[judge]` table - M3's business.

**STOP conditions** - stop and report rather than improvise, if:
- `tomllib` is missing (the plugin floor is 3.14; a 3.10 interpreter in the gate would be the gate's fault, report it).

- [ ] **Step 1: Write the failing tests**

```python
"""abprofile: a TOML profile becomes frozen dataclasses, or a ProfileError naming every problem."""
import pytest

import abprofile as P

GOOD = """
[workpiece]
repo = "{repo}"
base = "{base}"
task_file = "task.md"

[control]
skills_ref = "{ref}"
skill = "demo-skill"

[[variant]]
name = "V1"
dir = "variants/V1"
changes = ["one change"]
markers = []

[floor]
gate = ["./gate.sh"]
cache_paths = ["target"]
timeout_s = 60

[run]
model = "opus"
n = 2
deadline_s = 100
max_tokens = 5000
"""


def _write(tmp_path, scratch_repo, text=GOOD, **over):
    base = (scratch_repo / ".base").read_text()
    body = text.format(repo=scratch_repo, base=over.get("base", base), ref="a" * 40)
    p = tmp_path / "abtest.toml"
    p.write_text(body, encoding="utf-8")
    return p


def test_good_profile_loads(tmp_path, scratch_repo):
    prof = P.load_profile(_write(tmp_path, scratch_repo))
    assert prof.arm_names() == ["C", "V1"]
    assert prof.floor.gate == ("./gate.sh",) and prof.floor.suite is None and prof.suite_argv() is None
    assert prof.run.warmth_tolerance == 0.25 and prof.run.n == 2
    assert prof.run.env_keep == ("PATH", "LANG", "LC_ALL", "TERM", "TZ")
    assert prof.workpiece.repo == scratch_repo.resolve()


def test_suite_argv_substitutes_the_suite(tmp_path, scratch_repo):
    text = GOOD.replace('gate = ["./gate.sh"]', 'gate = ["./gate.sh"]\nsuite = "acceptance/t.py"\nsuite_cmd = ["pytest", "{{suite}}", "-q"]')
    prof = P.load_profile(_write(tmp_path, scratch_repo, text))
    assert prof.suite_argv() == ["pytest", "acceptance/t.py", "-q"]


def test_every_problem_is_listed(tmp_path, scratch_repo):
    text = (GOOD.replace('name = "V1"', 'name = "C"')
                .replace('gate = ["./gate.sh"]', 'gate = "make test"')
                .replace("n = 2", "n = 0"))
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text, base="not-a-sha"))
    msg = str(exc.value)
    for needle in ("workpiece.base", "variant[0].name", "floor.gate", "run.n"):
        assert needle in msg, msg


def test_duplicate_variant_names_and_missing_repo(tmp_path, scratch_repo):
    text = GOOD + '\n[[variant]]\nname = "V1"\ndir = "variants/V1b"\nchanges = ["x"]\nmarkers = []\n'
    text = text.replace('repo = "{repo}"', 'repo = "{repo}/nonexistent"')
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text))
    assert "variant[1].name" in str(exc.value) and "workpiece.repo" in str(exc.value)


def test_skeleton_fails_validation_until_filled(tmp_path):
    p = tmp_path / "abtest.toml"
    p.write_text(P.SKELETON, encoding="utf-8")
    with pytest.raises(P.ProfileError):
        P.load_profile(p)
```

- [ ] **Step 2: Run them to verify they fail**

Expected: `ModuleNotFoundError: No module named 'abprofile'`.

- [ ] **Step 3: Write `abprofile.py`**

```python
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
    repo = Path(c.text(wp, "repo", "workpiece")).expanduser()
    if not (repo / ".git").exists():
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Expected: `5 passed` in `test_abprofile.py` (and Task 9's 9 still green).

- [ ] **Step 5: Commit**

Subject: `meta-skill-ab-test: abprofile, the validated TOML profile`.
`git -C <scratch>/wt-m2 add plugins/bitranox/skills/meta-skill-ab-test && git -C <scratch>/wt-m2 commit -F <scratch>/m2-t10.txt -- plugins/bitranox/skills/meta-skill-ab-test`

### Task 11: `abstream.py`, stream accounting and prices

**Files:**
- Create: `plugins/bitranox/skills/meta-skill-ab-test/scripts/abstream.py`
- Test: `plugins/bitranox/skills/meta-skill-ab-test/tests/test_abstream.py`

**Interfaces:**
- Consumes: `tests/fixtures/stream-control.jsonl` (Task 9).
- Produces: `OPUS_PREFIX = "claude-opus"`, `FORBIDDEN_MODEL_SUBSTRINGS = ("fable", "mythos")`, `PRICES: dict[str, dict[str, float]]` (USD per million tokens, keys `input, output, cache_read, cache_write_5m, cache_write_1h`), `INPUT_CLASSES`, `class UnknownModel(KeyError)`, `input_usage(usage) -> dict[str, int]`, `input_units(model, usage) -> int` (1e-9 USD), `price_input(model, usage) -> float`, `class StreamAccount` with `.feed(record)`, `.per_model()`, `.summary()`, `.void_reasons`, `.first_cache_read: int | None`; `account_stream_file(path) -> StreamAccount`.

**Out of scope** - do NOT touch, though they look related:
- The prototype's `price_gate` / `reproduction_check` - they audited the prototype's own accounting; `score` (Task 14) reads `total_cost_usd` and per-model usage from the result record, and the input-side table serves M3's fix pricing.

**STOP conditions** - stop and report rather than improvise, if:
- the price table needs a model id the prototype table does not carry: add the row with the price from the published price list and name the source in the commit message; never guess a price.

- [ ] **Step 1: Write the failing tests**

```python
"""abstream: one stream.jsonl becomes an account (tokens per model, cost, void reasons)."""
import json
from pathlib import Path

import pytest

import abstream as S

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "stream-control.jsonl"


def test_control_fixture_accounts_cleanly():
    acct = S.account_stream_file(FIXTURE)
    s = acct.summary()
    assert s["model"] == "claude-opus-5-5" and s["void_reasons"] == []
    assert (s["main_new_tokens"], s["main_cache_read"], s["main_output_tokens"]) == (20010, 11000, 50)
    assert s["total_cost_usd"] == 0.25 and s["per_model"]["claude-opus-5-5"]["new_tokens"] == 20010
    assert acct.first_cache_read == 11000


def test_non_opus_main_model_is_void():
    acct = S.StreamAccount()
    acct.feed({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5"})
    assert acct.void_reasons == ["session model is 'claude-sonnet-5-5', not an opus id"]


def test_forbidden_model_in_usage_is_void_and_haiku_is_not():
    acct = S.StreamAccount()
    acct.feed({"type": "result", "modelUsage": {"claude-haiku-5-5": {}, "claude-fable-5-1": {}}})
    assert acct.void_reasons == ["model claude-fable-5-1 appears in modelUsage"]


def test_assistant_messages_are_counted_once_per_id():
    acct = S.StreamAccount()
    msg = {"type": "assistant", "message": {"id": "m1", "model": "claude-opus-5-5",
                                            "usage": {"input_tokens": 5, "cache_read_input_tokens": 7}}}
    acct.feed(msg)
    acct.feed(msg)
    assert (acct.new_tokens, acct.cache_read, acct.assistant_messages) == (5, 7, 1)


def test_input_usage_prefers_the_split_and_prices_exactly():
    u = S.input_usage({"input_tokens": 1, "cache_read_input_tokens": 2, "cache_creation_input_tokens": 30,
                       "cache_creation": {"ephemeral_5m_input_tokens": 10, "ephemeral_1h_input_tokens": 20}})
    assert u == {"input": 1, "cache_read": 2, "cache_write_5m": 10, "cache_write_1h": 20}
    assert S.input_usage({"cache_creation_input_tokens": 30}) == {"input": 0, "cache_read": 0, "cache_write_5m": 30, "cache_write_1h": 0}
    units = S.input_units("claude-opus-5-5", u)
    assert units == 1 * 4000 + 2 * 200 + 10 * 5000 + 20 * 8000
    with pytest.raises(S.UnknownModel):
        S.input_units("claude-unknown", u)


def test_non_json_lines_are_skipped(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text("garbage\n" + FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    assert S.account_stream_file(p).summary()["total_cost_usd"] == 0.25
```

- [ ] **Step 2: Run them to verify they fail**

Expected: `ModuleNotFoundError: No module named 'abstream'`.

- [ ] **Step 3: Write `abstream.py`**

```python
"""Accounting for a `claude -p --output-format stream-json` stream, and the input-side price table.

Ported from the prototype's abxlib.StreamAccount and fixeslib.input_usage. The main model must be
an opus id (the run is void otherwise); delegation to haiku inside the arm is allowed and counted
per model (user decision 2026-11-03).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

OPUS_PREFIX = "claude-opus"
FORBIDDEN_MODEL_SUBSTRINGS = ("fable", "mythos")
INPUT_CLASSES = ("input", "cache_read", "cache_write_5m", "cache_write_1h")
# USD per million tokens. Add a row from the published price list, never from memory.
PRICES: dict[str, dict[str, float]] = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write_5m": 5.00, "cache_write_1h": 8.00},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write_5m": 0.125, "cache_write_1h": 0.20},
}
# Thousandths of a dollar per million tokens, so every sum is an exact integer in 1e-9 USD: a
# float sum in another order reads equal token counts as "above" by a rounding error.
PRICE_MILLI = {m: {k: round(v * 1000) for k, v in p.items()} for m, p in PRICES.items()}
NANO = 1e9


class UnknownModel(KeyError):
    """A model id with no row in PRICES; pricing it would be a guess."""


def input_usage(usage: dict[str, Any]) -> dict[str, int]:
    """The INPUT side of one message's usage, split by price class."""
    cc = usage.get("cache_creation") or {}
    five, one_h = cc.get("ephemeral_5m_input_tokens"), cc.get("ephemeral_1h_input_tokens")
    if five is None and one_h is None:
        # Without the split the whole creation count takes the 5m rate, the cheaper one.
        five, one_h = usage.get("cache_creation_input_tokens") or 0, 0
    return {"input": int(usage.get("input_tokens") or 0), "cache_read": int(usage.get("cache_read_input_tokens") or 0),
            "cache_write_5m": int(five or 0), "cache_write_1h": int(one_h or 0)}


def input_units(model: str, usage: dict[str, int]) -> int:
    """The input side of one message in 1e-9 USD, priced by its own model."""
    if model not in PRICES:
        raise UnknownModel(model)
    p = PRICE_MILLI[model]
    return sum(int(usage.get(k, 0)) * p[k] for k in INPUT_CLASSES)


def price_input(model: str, usage: dict[str, int]) -> float:
    return input_units(model, usage) / NANO


@dataclass
class StreamAccount:
    """What one stream says about one run; feed() is idempotent per assistant message id."""

    model: str | None = None
    claude_version: str | None = None
    session_id: str | None = None
    permission_mode: str | None = None
    plugins: list[str] = field(default_factory=list)
    skill_count: int = 0
    new_tokens: int = 0
    cache_read: int = 0
    output_tokens: int = 0
    assistant_messages: int = 0
    first_cache_read: int | None = None
    seen_ids: set[str] = field(default_factory=set)
    per_message_model: dict[str, int] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    void_reasons: list[str] = field(default_factory=list)

    def feed(self, record: dict[str, Any]) -> None:
        kind = record.get("type")
        if kind == "system" and record.get("subtype") == "init":
            self.model = record.get("model")
            self.claude_version = record.get("claude_code_version")
            self.session_id = record.get("session_id")
            self.permission_mode = record.get("permissionMode")
            self.plugins = [str(p.get("name", p)) if isinstance(p, dict) else str(p) for p in record.get("plugins") or []]
            self.skill_count = len(record.get("skills") or [])
            if not str(self.model or "").startswith(OPUS_PREFIX):
                self.void_reasons.append(f"session model is {self.model!r}, not an opus id")
        elif kind == "assistant":
            message = record.get("message") or {}
            mid = message.get("id")
            if mid and mid in self.seen_ids:
                return
            if mid:
                self.seen_ids.add(mid)
            usage = message.get("usage") or {}
            cache_read = int(usage.get("cache_read_input_tokens") or 0)
            if self.first_cache_read is None:
                self.first_cache_read = cache_read
            self.new_tokens += int(usage.get("input_tokens") or 0) + int(usage.get("cache_creation_input_tokens") or 0)
            self.cache_read += cache_read
            self.output_tokens += int(usage.get("output_tokens") or 0)
            self.assistant_messages += 1
            model = str(message.get("model") or "")
            self.per_message_model[model] = self.per_message_model.get(model, 0) + 1
        elif kind == "result":
            self.result = record
            for model_id in record.get("modelUsage") or {}:
                if any(s in model_id for s in FORBIDDEN_MODEL_SUBSTRINGS):
                    self.void_reasons.append(f"model {model_id} appears in modelUsage")

    def per_model(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for model_id, u in ((self.result or {}).get("modelUsage") or {}).items():
            out[model_id] = {"new_tokens": int(u.get("inputTokens") or 0) + int(u.get("cacheCreationInputTokens") or 0),
                             "cache_read": int(u.get("cacheReadInputTokens") or 0),
                             "output_tokens": int(u.get("outputTokens") or 0), "cost_usd": float(u.get("costUSD") or 0.0)}
        return out

    def summary(self) -> dict[str, Any]:
        r = self.result or {}
        return {"model": self.model, "claude_version": self.claude_version, "session_id": self.session_id,
                "permission_mode": self.permission_mode, "plugins": self.plugins, "skill_count": self.skill_count,
                "main_new_tokens": self.new_tokens, "main_cache_read": self.cache_read,
                "main_output_tokens": self.output_tokens, "assistant_messages": self.assistant_messages,
                "first_cache_read": self.first_cache_read, "per_message_model": self.per_message_model,
                "per_model": self.per_model(), "total_cost_usd": r.get("total_cost_usd"), "num_turns": r.get("num_turns"),
                "duration_ms": r.get("duration_ms"), "result_subtype": r.get("subtype"),
                "has_result": self.result is not None, "void_reasons": list(self.void_reasons)}


def account_stream_file(path: Path) -> StreamAccount:
    """Account every JSON line of a saved stream; a non-JSON line is skipped, never fatal."""
    acct = StreamAccount()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                acct.feed(record)
    return acct
```

- [ ] **Step 4: Run the tests to verify they pass**

Expected: `6 passed` in `test_abstream.py`.

- [ ] **Step 5: Commit**

Subject: `meta-skill-ab-test: abstream, stream accounting and the input price table`.
`git -C <scratch>/wt-m2 add plugins/bitranox/skills/meta-skill-ab-test && git -C <scratch>/wt-m2 commit -F <scratch>/m2-t11.txt -- plugins/bitranox/skills/meta-skill-ab-test`

### Task 12: `abarm.py`, one arm's lifecycle pieces

**Files:**
- Create: `plugins/bitranox/skills/meta-skill-ab-test/scripts/abarm.py`
- Test: `plugins/bitranox/skills/meta-skill-ab-test/tests/test_abarm.py`

**Interfaces:**
- Consumes: `_ablib.run/git/tree_hashes/sha256_file`, `abstream.StreamAccount`, `abprofile.Profile/Variant`; the fake `claude`, `scratch_repo`, `skills_repo` fixtures.
- Produces: `class ArmError(RuntimeError)`; `@dataclass(frozen=True) Frozen(path: Path, skills_ref: str, skill_dir: Path, overlay_written: tuple[str, ...], hashes: dict[str, str])`; `freeze_variant(run_dir, profile, name, skills_repo) -> Frozen`; `install_plugin(cfg, frozen, credentials, env, *, settings_keep=("skillListingBudgetFraction",)) -> dict`; `make_worktree(repo, base, branch, path, *, copy_untracked_claude_md) -> dict`; `arm_env(cfg, home, keep) -> dict[str, str]`; `arm_home(arm_dir, links) -> Path`; `claude_argv(prompt, max_turns) -> list[str]`; `dispatch(arm_dir, ws, env, argv, *, max_tokens, deadline_s) -> dict`; `bundle(ws, base, out) -> int`; `prune(ws, repo, cache_paths) -> dict`; `delete_cfg(cfg) -> None`; `PRE_PUSH_HOOK: str`.

**Out of scope** - do NOT touch, though they look related:
- The prototype's `link_packages` (a Rust-specific gitignored `.packages` dir) - a workpiece that needs a gitignored dir linked declares it in `run.home_links` or keeps it absolute; a worktree shares the repo's config, so nothing else is needed.
- `git clone -s` (the prototype's workspace) - replaced by a nested worktree (design S1, decided by checkpoint 1).

**STOP conditions** - stop and report rather than improvise, if:
- checkpoint 1 (2026-11-03, measured) found the arm loads the repo-root `CLAUDE.local.md` through the ancestor walk but NOT an untracked repo-root `CLAUDE.md` (a nested worktree skips the parent's CLAUDE.md), and runs its one session at the CLI's default `skillListingBudgetFraction` because the plugin's raise lands only next session; `make_worktree` therefore copies an untracked `CLAUDE.md` (never `CLAUDE.local.md`, which would then load twice) and `install_plugin` seeds `settings.json` from the user's settings. If either premise reads false on the code you find, STOP;
- `git worktree add` refuses because `.claude/worktrees/` is not ignorable (the exclude write fails): report the repo's `.git/info/exclude` state.

- [ ] **Step 1: Write the failing tests**

```python
"""abarm: freeze, install, worktree, dispatch, bundle, prune; through the fake claude and a scratch repo."""
import dataclasses
import json
import os
from pathlib import Path

import pytest

import _ablib as L
import abarm as A
import abprofile as P

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _profile(tmp_path, scratch_repo, skills_repo):
    ref = (skills_repo / ".ref").read_text()
    text = f'''
[workpiece]
repo = "{scratch_repo}"
base = "{(scratch_repo / '.base').read_text()}"
task_file = "task.md"
[control]
skills_ref = "{ref}"
skill = "demo-skill"
[[variant]]
name = "V1"
dir = "variants/V1"
changes = ["louder"]
markers = ["LOUDER"]
[floor]
gate = ["./gate.sh"]
cache_paths = ["target"]
[run]
model = "opus"
n = 1
deadline_s = 100
max_tokens = 5000
'''
    run_dir = tmp_path / "run"
    (run_dir / "variants" / "V1").mkdir(parents=True)
    (run_dir / "variants" / "V1" / "SKILL.md").write_text("---\nname: demo-skill\n---\nLOUDER text.\n", encoding="utf-8")
    (run_dir / "abtest.toml").write_text(text, encoding="utf-8")
    return run_dir, P.load_profile(run_dir / "abtest.toml")


def test_freeze_control_and_variant(tmp_path, scratch_repo, skills_repo):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    c = A.freeze_variant(run_dir, prof, "C", skills_repo)
    v = A.freeze_variant(run_dir, prof, "V1", skills_repo)
    assert c.overlay_written == () and v.overlay_written == ("SKILL.md",)
    assert "LOUDER" in (v.skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "LOUDER" not in (c.skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert c.hashes["SKILL.md"] != v.hashes["SKILL.md"]
    assert A.freeze_variant(run_dir, prof, "C", skills_repo).path == c.path, "idempotent: same checkout"


def test_freeze_refuses_a_ref_without_the_switch(tmp_path, scratch_repo, skills_repo):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    (skills_repo / "hooks" / "self_improve_signals.py").write_text("# no switch here\n", encoding="utf-8")
    L.git(skills_repo, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-am", "drop the switch")
    ref = L.git(skills_repo, "rev-parse", "HEAD").stdout.strip()
    prof2 = P.Profile(path=prof.path, workpiece=prof.workpiece, control=P.Control(skills_ref=ref, skill="demo-skill"),
                      variants=prof.variants, floor=prof.floor, run=prof.run)
    with pytest.raises(A.ArmError, match="BITRANOX_MEMORY_WRITES"):
        A.freeze_variant(run_dir, prof2, "C", skills_repo)


def test_install_plugin_verifies_bytes(tmp_path, scratch_repo, skills_repo, arm_env_base):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    frozen = A.freeze_variant(run_dir, prof, "V1", skills_repo)
    creds = tmp_path / "creds.json"
    creds.write_text('{"fake": true}', encoding="utf-8")
    creds.chmod(0o600)
    cfg = run_dir / "arms" / "r1-V1" / "cfg"
    info = A.install_plugin(cfg, frozen, creds, arm_env_base)
    assert info["drift"] == [] and info["installed_version"] == "0.0.1-fixture"
    seeded = json.loads((cfg / "settings.json").read_text(encoding="utf-8"))
    assert set(seeded) <= {"skillListingBudgetFraction"}, "only the named keys are seeded"
    assert (cfg / ".credentials.json").stat().st_mode & 0o777 == 0o600
    # A re-install overwrites the cache, so drift is planted on the frozen side's recorded hashes.
    bad = dataclasses.replace(frozen, hashes=dict(frozen.hashes, **{"SKILL.md": "0" * 64}))
    with pytest.raises(A.ArmError, match="drift"):
        A.install_plugin(cfg, bad, creds, arm_env_base)


def test_make_worktree_branch_hook_and_untracked_claude_md(scratch_repo, tmp_path):
    L.git(scratch_repo, "rm", "-q", "--cached", "CLAUDE.md")
    L.git(scratch_repo, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", "untrack")
    base = L.git(scratch_repo, "rev-parse", "HEAD").stdout.strip()
    (scratch_repo / "CLAUDE.md").write_text("# untracked root rules\n", encoding="utf-8")
    path = scratch_repo / ".claude" / "worktrees" / "abx-t-r1-C"
    info = A.make_worktree(scratch_repo, base, "abx/t/r1-C", path, copy_untracked_claude_md=True)
    assert info["head"] == base and info["claude_md_copied"] is True
    assert (path / "CLAUDE.md").read_text(encoding="utf-8") == "# untracked root rules\n"
    assert not (path / "CLAUDE.local.md").exists(), "CLAUDE.local.md already loads via the ancestor walk"
    assert L.git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "abx/t/r1-C"
    assert L.git(scratch_repo, "check-ignore", "-q", ".claude/worktrees/x").returncode == 0
    assert L.git(path, "push", "origin", "HEAD").returncode != 0, "the pre-push hook refuses"
    with pytest.raises(A.ArmError):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", path, copy_untracked_claude_md=False)


def test_make_worktree_leaves_a_tracked_claude_md_alone(scratch_repo):
    base = (scratch_repo / ".base").read_text()
    path = scratch_repo / ".claude" / "worktrees" / "abx-t-r1-V1"
    info = A.make_worktree(scratch_repo, base, "abx/t/r1-V1", path, copy_untracked_claude_md=True)
    assert info["claude_md_copied"] is False
    assert (path / "CLAUDE.md").read_text(encoding="utf-8") == "# workpiece\n"


def test_arm_env_is_built_from_scratch(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("SECRET_THING", "x")
    env = A.arm_env(tmp_path / "cfg", tmp_path / "home", ("PATH", "LANG"))
    assert "CLAUDECODE" not in env and "SECRET_THING" not in env
    assert env["BITRANOX_MEMORY_WRITES"] == "off" and env["CLAUDE_CONFIG_DIR"] == str(tmp_path / "cfg")
    assert env["HOME"] == str(tmp_path / "home") and env["PATH"] == os.environ["PATH"]


def test_arm_home_links_only_what_exists(tmp_path, monkeypatch):
    real = tmp_path / "realhome"
    (real / ".cargo").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(real))
    home = A.arm_home(tmp_path / "arm", (".cargo", ".rustup"))
    assert (home / ".cargo").is_symlink() and not (home / ".rustup").exists()


def test_dispatch_streams_and_bundles(tmp_path, scratch_repo, arm_env_base, fake_claude_path):
    base = (scratch_repo / ".base").read_text()
    ws = scratch_repo / ".claude" / "worktrees" / "abx-t-r1-C"
    A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    arm_dir = tmp_path / "arm"
    arm_dir.mkdir()
    env = dict(A.arm_env(arm_dir / "cfg", arm_dir / "home", ("PATH",)), **arm_env_base,
               FAKE_CLAUDE_STREAM=str(FIXTURES / "stream-control.jsonl"))
    (arm_dir / "cfg").mkdir()
    res = A.dispatch(arm_dir, ws, env, A.claude_argv("do the task", 5), max_tokens=10**7, deadline_s=60)
    assert res["stop_reason"] == "finished" and res["process_rc"] == 0 and res["total_cost_usd"] == 0.25
    assert (arm_dir / "stream.jsonl").stat().st_size > 0
    assert A.bundle(ws, base, arm_dir / "bundle.git") == 1
    assert L.git(scratch_repo, "bundle", "verify", str(arm_dir / "bundle.git")).returncode == 0
    (ws / "target").mkdir()
    (ws / "target" / "big").write_bytes(b"x" * 1000)
    pruned = A.prune(ws, scratch_repo, ("target",))
    assert pruned["cache_bytes"] >= 1000 and not ws.exists()
    assert L.git(scratch_repo, "rev-parse", "--verify", "-q", "abx/t/r1-C").returncode == 0, "the branch stays"


def test_dispatch_token_cap_ends_the_run(tmp_path, scratch_repo, arm_env_base):
    base = (scratch_repo / ".base").read_text()
    ws = scratch_repo / ".claude" / "worktrees" / "abx-t-r1-V1"
    A.make_worktree(scratch_repo, base, "abx/t/r1-V1", ws, copy_untracked_claude_md=False)
    arm_dir = tmp_path / "arm2"
    (arm_dir / "cfg").mkdir(parents=True)
    env = dict(A.arm_env(arm_dir / "cfg", arm_dir / "home", ("PATH",)), **arm_env_base,
               FAKE_CLAUDE_STREAM=str(FIXTURES / "stream-control.jsonl"))
    res = A.dispatch(arm_dir, ws, env, A.claude_argv("x", 5), max_tokens=100, deadline_s=60)
    assert res["stop_reason"] == "token_cap"


def test_delete_cfg_removes_the_credentials_copy(tmp_path):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / ".credentials.json").write_text("{}", encoding="utf-8")
    A.delete_cfg(cfg)
    assert not cfg.exists()
```

- [ ] **Step 2: Run them to verify they fail**

Expected: `ModuleNotFoundError: No module named 'abarm'`.

- [ ] **Step 3: Write `abarm.py`**

```python
"""One arm's lifecycle pieces: freeze the skill, install it, make the worktree, run, bundle, prune.

Ported from the prototype's abxlib (arm_home, headless_env, installed_plugin_path, apply_overlay),
make_variant (install + byte check) and run_arm (dispatch with caps). The workspace is a nested
worktree of the real repository instead of a clone (design S1): the cascade must match real work.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _ablib import git, run, tree_hashes
from abprofile import Profile
from abstream import StreamAccount

SKILLS_REL = "plugins/bitranox/skills"
SWITCH_FILE = "plugins/bitranox/hooks/self_improve_signals.py"
SWITCH_NAME = "BITRANOX_MEMORY_WRITES"
PLUGIN_ID = "bitranox@bitranox-skills"
PRE_PUSH_HOOK = "#!/bin/sh\necho 'abtest arm: pushing is refused; the branch is collected by the harness' >&2\nexit 1\n"


class ArmError(RuntimeError):
    """A step of the arm could not be completed as specified; the arm is not started or is void."""


@dataclass(frozen=True)
class Frozen:
    path: Path
    skills_ref: str
    skill_dir: Path
    overlay_written: tuple[str, ...]
    hashes: dict[str, str]


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


def freeze_variant(run_dir: Path, profile: Profile, name: str, skills_repo: Path) -> Frozen:
    """A detached checkout of bitranox-skills at skills_ref under run_dir/frozen/<name>, overlay applied.

    Idempotent: an existing checkout at the same ref is reused (its overlay is re-applied, which is
    a no-op when nothing changed). The ref must carry the memory-writes switch (design S5.3).
    """
    ref = profile.control.skills_ref
    path = run_dir / "frozen" / name
    if path.exists():
        head = git(path, "rev-parse", "--verify", "-q", "HEAD").stdout.strip()
        if head != ref:
            raise ArmError(f"{path} exists at {head}, not {ref}")
    else:
        proc = git(skills_repo, "worktree", "add", "--detach", str(path), ref)
        if proc.returncode != 0:
            raise ArmError(f"worktree add of {ref} failed: {proc.stderr.strip()}")
    switch = path / SWITCH_FILE
    if not switch.is_file() or SWITCH_NAME not in switch.read_text(encoding="utf-8"):
        raise ArmError(f"skills_ref {ref} does not carry {SWITCH_NAME}; an arm would write the shared store")
    skill_dir = path / SKILLS_REL / profile.control.skill
    if not skill_dir.is_dir():
        raise ArmError(f"skill {profile.control.skill} is not at {skill_dir}")
    variant_dir = None if name == "C" else run_dir / next(v.dir for v in profile.variants if v.name == name)
    if variant_dir is not None and not variant_dir.is_dir():
        raise ArmError(f"variant dir {variant_dir} is missing")
    written = _apply_overlay(variant_dir, skill_dir)
    return Frozen(path=path, skills_ref=ref, skill_dir=skill_dir, overlay_written=written, hashes=tree_hashes(skill_dir))


def installed_plugin_path(cfg: Path) -> Path | None:
    registry = cfg / "plugins" / "installed_plugins.json"
    if not registry.is_file():
        return None
    data = json.loads(registry.read_text(encoding="utf-8"))
    for entry in (data.get("plugins") or {}).get(PLUGIN_ID) or []:
        if entry.get("installPath"):
            return Path(entry["installPath"])
    return None


def install_plugin(cfg: Path, frozen: Frozen, credentials: Path, env: dict[str, str], *,
                   settings_keep: tuple[str, ...] = ("skillListingBudgetFraction",)) -> dict[str, Any]:
    """Install the frozen plugin into cfg and verify the installed skill byte for byte.

    env must carry PATH (so `claude` resolves); CLAUDE_CONFIG_DIR is set here. The credentials
    file is copied in at mode 0600 and must be removed by delete_cfg when the arm ends.
    settings_keep names the user settings.json keys seeded into cfg/settings.json: a fresh config
    dir runs its only session at the CLI defaults (measured at checkpoint 1: the skill listing
    budget the plugin raises applies only from the next session), which is not normal work.
    """
    cfg.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        user = json.loads((Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        user = {}
    seeded = {k: user[k] for k in settings_keep if k in user}
    (cfg / "settings.json").write_text(json.dumps(seeded), encoding="utf-8")
    if not credentials.is_file():
        raise ArmError(f"no credentials file at {credentials}")
    target = cfg / ".credentials.json"
    shutil.copyfile(credentials, target)
    target.chmod(0o600)
    env = dict(env, CLAUDE_CONFIG_DIR=str(cfg))
    steps = []
    for argv in (["claude", "plugin", "marketplace", "add", str(frozen.path), "--json"],
                 ["claude", "plugin", "install", PLUGIN_ID, "--json"]):
        proc = run(argv, cwd=cfg.parent, env=env, timeout=300)
        steps.append({"argv": argv[1:4], "rc": proc.returncode})
        if proc.returncode != 0:
            raise ArmError(f"{' '.join(argv[:4])} failed rc={proc.returncode}: {proc.stderr.strip()[-500:]}")
    installed = installed_plugin_path(cfg)
    if installed is None:
        raise ArmError("the config dir records no installed bitranox plugin")
    installed_hashes = tree_hashes(installed / "skills" / frozen.skill_dir.name)
    drift = sorted(k for k in set(frozen.hashes) | set(installed_hashes) if frozen.hashes.get(k) != installed_hashes.get(k))
    version = json.loads((installed / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version")
    info = {"installed_path": str(installed), "installed_version": version, "drift": drift, "steps": steps,
            "settings_seeded": sorted(seeded)}
    if drift:
        raise ArmError(f"installed skill drifts from the frozen checkout: {drift}")
    return info


def make_worktree(repo: Path, base: str, branch: str, path: Path, *, copy_untracked_claude_md: bool) -> dict[str, Any]:
    """A nested worktree of repo at base on a NEW branch, with a refusing pre-push hook.

    `.claude/worktrees/` is added to repo's .git/info/exclude when not already ignored, so the
    arm's tree never shows up as untracked in the real checkout.
    """
    if path.exists():
        raise ArmError(f"worktree {path} already exists")
    if git(repo, "check-ignore", "-q", ".claude/worktrees/probe").returncode != 0:
        exclude = repo / ".git" / "info" / "exclude"
        if not exclude.parent.is_dir():
            raise ArmError(f"{exclude.parent} is missing; is {repo} a linked worktree itself?")
        with exclude.open("a", encoding="utf-8") as fh:
            fh.write(".claude/worktrees/\n")
    proc = git(repo, "worktree", "add", "-b", branch, str(path), base)
    if proc.returncode != 0:
        raise ArmError(f"worktree add failed: {proc.stderr.strip()}")
    head = git(path, "rev-parse", "HEAD").stdout.strip()
    if head != base:
        raise ArmError(f"worktree HEAD {head} is not the base {base}")
    hooks = path.parent / f"{path.name}.githooks"
    hooks.mkdir(exist_ok=True)
    (hooks / "pre-push").write_text(PRE_PUSH_HOOK, encoding="utf-8")
    (hooks / "pre-push").chmod(0o755)
    git(path, "config", "core.hooksPath", str(hooks))
    # Measured at checkpoint 1: a nested worktree skips the parent repo's CLAUDE.md but still loads
    # the repo-root CLAUDE.local.md through the ancestor walk. So an UNTRACKED root CLAUDE.md is
    # copied in (a tracked one is already in the checkout), and CLAUDE.local.md never is (it would
    # then load twice).
    copied = False
    root_md = repo / "CLAUDE.md"
    if (copy_untracked_claude_md and root_md.is_file() and not (path / "CLAUDE.md").exists()
            and git(repo, "ls-files", "--error-unmatch", "CLAUDE.md").returncode != 0):
        shutil.copyfile(root_md, path / "CLAUDE.md")
        copied = True
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

    CLAUDECODE is never inherited (a nested claude refuses to start inside another), and the
    memory-writes switch is always on.
    """
    env = {k: os.environ[k] for k in keep if k in os.environ and k != "CLAUDECODE"}
    env.update({"HOME": str(home), "CLAUDE_CONFIG_DIR": str(cfg), "BITRANOX_MEMORY_WRITES": "off"})
    return env


def claude_argv(prompt: str, max_turns: int) -> list[str]:
    return ["claude", "-p", prompt, "--model", "opus", "--output-format", "stream-json", "--verbose",
            "--max-turns", str(max_turns), "--dangerously-skip-permissions"]


def dispatch(arm_dir: Path, ws: Path, env: dict[str, str], argv: list[str], *, max_tokens: int,
             deadline_s: float) -> dict[str, Any]:
    """Stream the session to arm_dir/stream.jsonl, account it, end it on a cap or the deadline."""
    stream_path, stderr_path = arm_dir / "stream.jsonl", arm_dir / "stderr.txt"
    acct = StreamAccount()
    stop_reason = "finished"
    started = time.monotonic()
    with stream_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err, \
            subprocess.Popen(argv, cwd=str(ws), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,  # nosec B603
                             stderr=err, text=True, encoding="utf-8", errors="replace") as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            out.write(line)
            out.flush()
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                acct.feed(record)
            if acct.void_reasons:
                stop_reason = "void"
            elif acct.new_tokens >= max_tokens:
                stop_reason = "token_cap"
            elif time.monotonic() - started >= deadline_s:
                stop_reason = "deadline"
            if stop_reason != "finished":
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break
        rc = proc.wait()
    summary = acct.summary()
    summary.update({"stop_reason": stop_reason, "process_rc": rc, "wall_s": round(time.monotonic() - started, 1),
                    "stream": str(stream_path)})
    return summary


def bundle(ws: Path, base: str, out: Path) -> int:
    """git bundle of base..HEAD into out; the number of commits bundled (0 writes no file)."""
    count = int(git(ws, "rev-list", "--count", f"{base}..HEAD").stdout.strip() or 0)
    if count == 0:
        return 0
    proc = git(ws, "bundle", "create", str(out), f"{base}..HEAD")
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
    proc = git(repo, "worktree", "remove", "--force", str(ws))
    if proc.returncode != 0:
        raise ArmError(f"worktree remove failed: {proc.stderr.strip()}")
    hooks = ws.parent / f"{ws.name}.githooks"
    shutil.rmtree(hooks, ignore_errors=True)
    return {"cache_bytes": freed, "worktree_removed": not ws.exists()}


def delete_cfg(cfg: Path) -> None:
    """Unlink the credentials copy first, then the whole config dir; never fails on a missing path."""
    try:
        (cfg / ".credentials.json").unlink()
    except OSError:
        pass
    shutil.rmtree(cfg, ignore_errors=True)
```

- [ ] **Step 4: Run the tests to verify they pass**

Expected: `11 passed` in `test_abarm.py`. If `test_make_worktree...`'s push assertion fails because the scratch repo has no `origin`, the hook still refuses first (git runs pre-push before contacting the remote); if it exits 128 before the hook, change the assertion to run the hook file directly: `L.run([str(hooks / "pre-push")]).returncode == 1`.

- [ ] **Step 5: Commit**

Subject: `meta-skill-ab-test: abarm, the arm lifecycle (freeze, install, worktree, dispatch, bundle, prune)`.
`git -C <scratch>/wt-m2 add plugins/bitranox/skills/meta-skill-ab-test && git -C <scratch>/wt-m2 commit -F <scratch>/m2-t12.txt -- plugins/bitranox/skills/meta-skill-ab-test`

### Task 13: `abguard.py`, the store snapshot and the out-of-band login check

**Files:**
- Create: `plugins/bitranox/skills/meta-skill-ab-test/scripts/abguard.py`
- Test: `plugins/bitranox/skills/meta-skill-ab-test/tests/test_abguard.py`
- Create: `plugins/bitranox/skills/meta-skill-ab-test/tests/fakes/store_manifest_fake.py` (a stand-in with the same CLI: `backup --from --scope --out --json` writes `manifest.json`; `verify --out --json` exits 1 with a JSON diff when a file named `CHANGED` exists beside the manifest, else 0)

**Interfaces:**
- Consumes: `skills/meta-dream-tree/store_manifest.py` (the shipped one; resolved relative to this skill: `Path(__file__).resolve().parents[2] / "meta-dream-tree" / "store_manifest.py"`); `_ablib.run`.
- Produces: `class GuardError(RuntimeError)`; `snapshot(chain_from, out, *, manifest=MANIFEST) -> dict` (`{"taken": bool, "entries": int, "skipped": str | None}`; `taken` is False with a reason when the chain has no memory store, which is a legal workpiece); `verify(out, *, manifest=MANIFEST) -> list[str]` (empty when identical; one line per change; raises `GuardError` on exit 2); `check_login(credentials, *, post=_post) -> str` (`"ok"`, `"login"`, `"quota"`, or `"unknown:<status>"`); `_post(url, headers, body) -> tuple[int, str]`.

**Out of scope** - do NOT touch, though they look related:
- `store_manifest.py` itself - reused as is; a gap in it is a `meta-dream-tree` fix in its own change.
- Reading the memory store directly - the guard only compares manifests.

**STOP conditions** - stop and report rather than improvise, if:
- the request shape in step 4 does not return 200 against the real credential in step 6 (the OAuth header set is UNVERIFIED here): report the status and body, never the token; do not loop over header guesses;
- `store_manifest.py backup` on the real workpiece chain exits 2 with anything but the no-store message.

- [ ] **Step 1: Write the fake manifest script and the failing tests**

`tests/fakes/store_manifest_fake.py`:

```python
"""Stand-in for store_manifest.py with the same CLI surface the guard drives."""
import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    bk = sub.add_parser("backup")
    bk.add_argument("--from", dest="start", required=True)
    bk.add_argument("--scope", default="tree")
    bk.add_argument("--out", required=True)
    bk.add_argument("--json", action="store_true")
    vf = sub.add_parser("verify")
    vf.add_argument("--out", required=True)
    vf.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if a.cmd == "backup":
        if "nostore" in a.start:
            print(json.dumps({"ok": False, "command": "backup", "data": {"error": "no .claude-memory/ store at the memory anchor of " + a.start}}))
            return 2
        out.mkdir(parents=True, exist_ok=True)
        (out / "manifest.json").write_text("{}", encoding="utf-8")
        print(json.dumps({"ok": True, "command": "backup", "data": {"entries": 3}}))
        return 0
    if (out / "CHANGED").exists():
        print(json.dumps({"ok": True, "command": "verify", "data": {"identical": False, "changed": [{"slug": "x", "what": "hook"}], "added": [], "removed": [], "moved": []}}))
        return 1
    print(json.dumps({"ok": True, "command": "verify", "data": {"identical": True, "changed": [], "added": [], "removed": [], "moved": []}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`tests/test_abguard.py`:

```python
"""abguard: the manifest snapshot and the out-of-band login check, through their real seams."""
import json
from pathlib import Path

import pytest

import abguard as G

FAKE = Path(__file__).resolve().parent / "fakes" / "store_manifest_fake.py"


def test_snapshot_and_verify_through_the_cli(tmp_path):
    out = tmp_path / "guard"
    assert G.snapshot(tmp_path, out, manifest=FAKE) == {"taken": True, "entries": 3, "skipped": None}
    assert G.verify(out, manifest=FAKE) == []
    (out / "CHANGED").write_text("", encoding="utf-8")
    assert G.verify(out, manifest=FAKE) == ["changed: {'slug': 'x', 'what': 'hook'}"]


def test_snapshot_skips_a_chain_without_a_store(tmp_path):
    chain = tmp_path / "nostore"
    chain.mkdir()
    res = G.snapshot(chain, tmp_path / "guard", manifest=FAKE)
    assert res["taken"] is False and "no .claude-memory" in res["skipped"]
    assert G.verify(tmp_path / "guard", manifest=FAKE) == [], "nothing taken, nothing to compare"


def test_the_shipped_manifest_script_exists_and_has_the_cli():
    assert G.MANIFEST.is_file(), G.MANIFEST
    text = G.MANIFEST.read_text(encoding="utf-8")
    assert '"--out"' in text and '"--scope"' in text and '"verify"' in text


@pytest.mark.parametrize("status, expected", [(200, "ok"), (401, "login"), (429, "quota"), (500, "unknown:500"), (0, "unknown:0")])
def test_check_login_classifies_the_status(tmp_path, status, expected):
    creds = tmp_path / "c.json"
    creds.write_text(json.dumps({"claudeAiOauth": {"accessToken": "tok-not-real"}}), encoding="utf-8")
    seen = {}

    def fake_post(url, headers, body):
        seen["url"], seen["auth"] = url, headers.get("authorization")
        return status, "{}"

    assert G.check_login(creds, post=fake_post) == expected
    assert seen["url"].endswith("/v1/messages") and seen["auth"] == "Bearer tok-not-real"


def test_check_login_without_a_token_is_login(tmp_path):
    creds = tmp_path / "c.json"
    creds.write_text("{}", encoding="utf-8")
    assert G.check_login(creds, post=lambda *a: (200, "")) == "login"
```

- [ ] **Step 2: Run them to verify they fail**

Expected: `ModuleNotFoundError: No module named 'abguard'`.

- [ ] **Step 3: Write `abguard.py`**

```python
"""The memory-store guard (a manifest before and after each arm) and the out-of-band login check.

The guard drives skills/meta-dream-tree/store_manifest.py as a subprocess: its exit code is the
answer (0 identical, 1 differs, 2 could not run). The login check asks the API directly because
the CLI reports an exhausted quota (429) with the same "not logged in" text as a bad token (401),
and a run must PAUSE on the first and VOID nothing (design S4).
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from _ablib import run

MANIFEST = Path(__file__).resolve().parents[2] / "meta-dream-tree" / "store_manifest.py"
NO_STORE_MARK = "no .claude-memory"
API_URL = "https://api.anthropic.com/v1/messages"
PostFn = Callable[[str, dict[str, str], bytes], tuple[int, str]]


class GuardError(RuntimeError):
    """The guard could not run; the arm must not start (or its result cannot be trusted)."""


def _manifest(argv: list[str], manifest: Path) -> tuple[int, dict[str, Any]]:
    proc = run([sys.executable, str(manifest), *argv, "--json"], timeout=600)
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        data = {}
    return proc.returncode, data


def snapshot(chain_from: Path, out: Path, *, manifest: Path = MANIFEST) -> dict[str, Any]:
    """Back up the chain's pointer files and store under out; skipped (not taken) without a store."""
    rc, data = _manifest(["backup", "--from", str(chain_from), "--scope", "chain", "--out", str(out)], manifest)
    if rc == 0:
        return {"taken": True, "entries": int((data.get("data") or {}).get("entries") or 0), "skipped": None}
    error = str((data.get("data") or {}).get("error") or "")
    if rc == 2 and NO_STORE_MARK in error:
        return {"taken": False, "entries": 0, "skipped": error}
    raise GuardError(f"store_manifest backup rc={rc}: {error or data}")


def verify(out: Path, *, manifest: Path = MANIFEST) -> list[str]:
    """One line per change since the snapshot; empty when identical or when no snapshot was taken."""
    if not (out / "manifest.json").is_file():
        return []
    rc, data = _manifest(["verify", "--out", str(out)], manifest)
    if rc == 2:
        raise GuardError(f"store_manifest verify could not run: {data}")
    d = data.get("data") or {}
    lines = []
    for kind in ("added", "removed", "changed", "moved"):
        lines.extend(f"{kind}: {item}" for item in d.get(kind) or [])
    if rc == 1 and not lines:
        lines.append("differs (no detail in the verify output)")
    return lines


def _post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310 - fixed https URL
            return resp.status, resp.read().decode("utf-8", "replace")[:500]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:500]
    except (urllib.error.URLError, OSError) as exc:
        # No network, DNS down: reported as unknown:0, which pauses the run like a quota would.
        return 0, repr(exc)


def check_login(credentials: Path, *, post: PostFn = _post) -> str:
    """ok / login / quota / unknown:<status>, from one minimal request with the arm's credential.

    The token is read from the credentials copy and sent once; it is never logged or returned.
    """
    try:
        token = (json.loads(credentials.read_text(encoding="utf-8")).get("claudeAiOauth") or {}).get("accessToken")
    except (OSError, json.JSONDecodeError):
        token = None
    if not token:
        return "login"
    headers = {"authorization": f"Bearer {token}", "anthropic-version": "2023-06-01",
               "anthropic-beta": "oauth-2025-04-20", "content-type": "application/json"}
    body = json.dumps({"model": "claude-haiku-5-5", "max_tokens": 1,
                       "messages": [{"role": "user", "content": "hi"}]}).encode("utf-8")
    status, _ = post(API_URL, headers, body)
    if status == 200:
        return "ok"
    if status == 401:
        return "login"
    if status == 429:
        return "quota"
    return f"unknown:{status}"
```

- [ ] **Step 4: Run the tests to verify they pass**

Expected: `9 passed` in `test_abguard.py`.

- [ ] **Step 5: Commit**

Subject: `meta-skill-ab-test: abguard, the store snapshot and the out-of-band login check`.
`git -C <scratch>/wt-m2 add plugins/bitranox/skills/meta-skill-ab-test && git -C <scratch>/wt-m2 commit -F <scratch>/m2-t13.txt -- plugins/bitranox/skills/meta-skill-ab-test`

- [ ] **Step 6: Probe the real request shape once (about 0.001 USD)**

From a scratch dir, with the REAL credentials path given to `check_login` and nothing printed but the one word:
`cd <scratch> && python3 -c "import sys; sys.path.insert(0, '<wt-m2>/plugins/bitranox/skills/meta-skill-ab-test/scripts'); import abguard; from pathlib import Path; print(abguard.check_login(Path.home() / '.claude' / '.credentials.json'))"`
Expected: `ok`. Any other word is the STOP condition above; record the word in `EXECUTION-USER-REVIEW.md` either way.

### Task 14: `abscore.py`, the floor and the per-arm score

**Files:**
- Create: `plugins/bitranox/skills/meta-skill-ab-test/scripts/abscore.py`
- Test: `plugins/bitranox/skills/meta-skill-ab-test/tests/test_abscore.py`

**Interfaces:**
- Consumes: `abprofile.Profile/Floor`, `_ablib.run/median`, an arm dir holding `result.json` (the `dispatch` summary plus `guard_changes`, `floor`, `bundle_commits` written by Task 15) and the fixture stream.
- Produces: `run_floor(tree, profile, log_dir) -> dict` (`{"passed": bool, "steps": [{"name": "gate"|"suite", "argv": [...], "rc": int, "wall_s": float, "log": path}]}`); `score_arm(arm_dir, profile, peers) -> dict` (writes `scores.json`: `{"arm", "cost_usd", "per_model", "main_new_tokens", "first_cache_read", "floor_passed", "bundle_commits", "void": [reasons], "wall_s"}`; `peers` is the list of the OTHER finished arms' `result.json` dicts, for the warmth check).

**Out of scope** - do NOT touch, though they look related:
- Anything that reads the diff or the transcript for quality - M3.
- The prototype's `score_arm.py` Rust parsing - the floor is the profile's argv lists; its exit code is the answer.

**STOP conditions** - stop and report rather than improvise, if:
- a floor command needs a shell feature (a pipe, `&&`, a glob): the profile forbids one shell string (design S5.6); report which command and let the user wrap it in a script inside the workpiece.

- [ ] **Step 1: Write the failing tests**

```python
"""abscore: the floor runs the profile's argv lists; the score reads result.json and the peers."""
import json
from pathlib import Path

import abprofile as P
import abscore as S

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _profile(tmp_path, scratch_repo, skills_repo, suite=False):
    extra = '\nsuite = "check.sh"\nsuite_cmd = ["sh", "{suite}"]' if suite else ""
    text = f'''
[workpiece]
repo = "{scratch_repo}"
base = "{(scratch_repo / '.base').read_text()}"
task_file = "task.md"
[control]
skills_ref = "{(skills_repo / '.ref').read_text()}"
skill = "demo-skill"
[[variant]]
name = "V1"
dir = "variants/V1"
changes = ["x"]
[floor]
gate = ["./gate.sh"]{extra}
cache_paths = []
timeout_s = 30
[run]
model = "opus"
n = 2
deadline_s = 100
max_tokens = 5000
'''
    p = tmp_path / "abtest.toml"
    p.write_text(text, encoding="utf-8")
    return P.load_profile(p)


def test_floor_runs_gate_then_suite_and_logs(tmp_path, scratch_repo, skills_repo):
    prof = _profile(tmp_path, scratch_repo, skills_repo, suite=True)
    (scratch_repo / "check.sh").write_text("echo suite ok\n", encoding="utf-8")
    res = S.run_floor(scratch_repo, prof, tmp_path / "logs")
    assert res["passed"] is True and [s["name"] for s in res["steps"]] == ["gate", "suite"]
    assert "suite ok" in Path(res["steps"][1]["log"]).read_text(encoding="utf-8")


def test_floor_fails_on_the_gate_and_skips_the_suite(tmp_path, scratch_repo, skills_repo):
    prof = _profile(tmp_path, scratch_repo, skills_repo, suite=True)
    (scratch_repo / "BROKEN").write_text("", encoding="utf-8")
    res = S.run_floor(scratch_repo, prof, tmp_path / "logs")
    assert res["passed"] is False and [s["name"] for s in res["steps"]] == ["gate"] and res["steps"][0]["rc"] == 1


def _result(**over):
    base = {"arm": "r1-C", "model": "claude-opus-5-5", "has_result": True, "stop_reason": "finished",
            "void_reasons": [], "total_cost_usd": 0.25, "main_new_tokens": 20010, "first_cache_read": 11000,
            "per_model": {"claude-opus-5-5": {"new_tokens": 20010, "cache_read": 11000, "output_tokens": 50, "cost_usd": 0.25}},
            "wall_s": 1.2, "guard_changes": [], "floor": {"passed": True, "steps": []}, "bundle_commits": 1}
    base.update(over)
    return base


def test_score_of_a_clean_arm(tmp_path, scratch_repo, skills_repo):
    prof = _profile(tmp_path, scratch_repo, skills_repo)
    arm = tmp_path / "arms" / "r1-C"
    arm.mkdir(parents=True)
    (arm / "result.json").write_text(json.dumps(_result()), encoding="utf-8")
    s = S.score_arm(arm, prof, peers=[_result(first_cache_read=11500)])
    assert s["void"] == [] and s["cost_usd"] == 0.25 and s["floor_passed"] is True
    assert json.loads((arm / "scores.json").read_text(encoding="utf-8")) == s


def test_every_void_rule_fires_by_itself(tmp_path, scratch_repo, skills_repo):
    prof = _profile(tmp_path, scratch_repo, skills_repo)
    cases = {
        "model": _result(void_reasons=["session model is 'x', not an opus id"]),
        "no result": _result(has_result=False, total_cost_usd=None),
        "deadline": _result(stop_reason="deadline"),
        "token_cap": _result(stop_reason="token_cap"),
        "guard": _result(guard_changes=["changed: slug x"]),
        "warmth": _result(first_cache_read=20000),
    }
    for name, res in cases.items():
        arm = tmp_path / "arms" / f"r1-{name}"
        arm.mkdir(parents=True)
        (arm / "result.json").write_text(json.dumps(res), encoding="utf-8")
        s = S.score_arm(arm, prof, peers=[_result(first_cache_read=11000), _result(first_cache_read=11200)])
        assert len(s["void"]) == 1, (name, s["void"])


def test_warmth_needs_two_peers_and_uses_the_tolerance(tmp_path, scratch_repo, skills_repo):
    prof = _profile(tmp_path, scratch_repo, skills_repo)
    arm = tmp_path / "arms" / "r1-C"
    arm.mkdir(parents=True)
    (arm / "result.json").write_text(json.dumps(_result(first_cache_read=20000)), encoding="utf-8")
    assert S.score_arm(arm, prof, peers=[_result(first_cache_read=11000)])["void"] == [], "one peer: no median yet"
    assert S.score_arm(arm, prof, peers=[_result(first_cache_read=16100), _result(first_cache_read=16100)])["void"] == []
    assert S.score_arm(arm, prof, peers=[_result(first_cache_read=15000), _result(first_cache_read=15000)])["void"] != []
```

- [ ] **Step 2: Run them to verify they fail**

Expected: `ModuleNotFoundError: No module named 'abscore'`.

- [ ] **Step 3: Write `abscore.py`**

```python
"""The floor (the profile's gate and suite, as argv lists) and the per-arm score with void rules.

Void rules (design S4) apply to every arm the same way and a void arm counts as nothing: main
model not opus, no result record, deadline or token cap, store guard fired, first-message cache
read out of line with the other finished arms (design S5.5, warmth_tolerance).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from _ablib import median, run
from abprofile import Profile

WARMTH_MIN_PEERS = 2


def _step(name: str, argv: list[str], tree: Path, timeout: int, log: Path) -> dict[str, Any]:
    t0 = time.monotonic()
    try:
        proc = run(argv, cwd=tree, timeout=timeout)
        rc, out = proc.returncode, proc.stdout + proc.stderr
    except Exception as exc:  # noqa: BLE001 - a timeout or a missing binary is a floor FAILURE, not a crash
        rc, out = 124, f"{name} did not complete: {exc!r}\n"
    log.write_text(out, encoding="utf-8")
    return {"name": name, "argv": argv, "rc": rc, "wall_s": round(time.monotonic() - t0, 1), "log": str(log)}


def run_floor(tree: Path, profile: Profile, log_dir: Path) -> dict[str, Any]:
    """Run the gate, then the suite (when set); the suite is skipped once the gate failed."""
    log_dir.mkdir(parents=True, exist_ok=True)
    steps = [_step("gate", list(profile.floor.gate), tree, profile.floor.timeout_s, log_dir / "floor-gate.log")]
    suite = profile.suite_argv()
    if suite is not None and steps[0]["rc"] == 0:
        steps.append(_step("suite", suite, tree, profile.floor.timeout_s, log_dir / "floor-suite.log"))
    return {"passed": all(s["rc"] == 0 for s in steps), "steps": steps}


def _void_reasons(res: dict[str, Any], profile: Profile, peers: list[dict[str, Any]]) -> list[str]:
    reasons = list(res.get("void_reasons") or [])
    if not res.get("has_result"):
        reasons.append("no result record in the stream")
    if res.get("stop_reason") in ("deadline", "token_cap"):
        reasons.append(f"ended by {res['stop_reason']}")
    if res.get("guard_changes"):
        reasons.append("store guard fired: " + "; ".join(res["guard_changes"]))
    mine = res.get("first_cache_read")
    reads = [p["first_cache_read"] for p in peers if isinstance(p.get("first_cache_read"), int)]
    if mine is not None and len(reads) >= WARMTH_MIN_PEERS:
        m = median([float(r) for r in reads])
        if m > 0 and abs(mine - m) / m > profile.run.warmth_tolerance:
            reasons.append(f"first-message cache read {mine} is off the peers' median {m:.0f} by more than {profile.run.warmth_tolerance}")
    return reasons


def score_arm(arm_dir: Path, profile: Profile, peers: list[dict[str, Any]]) -> dict[str, Any]:
    """Read arm_dir/result.json, apply the void rules against peers, write and return scores.json."""
    res = json.loads((arm_dir / "result.json").read_text(encoding="utf-8"))
    score = {"arm": res.get("arm", arm_dir.name), "cost_usd": res.get("total_cost_usd"),
             "per_model": res.get("per_model") or {}, "main_new_tokens": res.get("main_new_tokens"),
             "first_cache_read": res.get("first_cache_read"), "floor_passed": bool((res.get("floor") or {}).get("passed")),
             "bundle_commits": int(res.get("bundle_commits") or 0), "wall_s": res.get("wall_s"),
             "void": _void_reasons(res, profile, peers)}
    (arm_dir / "scores.json").write_text(json.dumps(score, indent=1, sort_keys=True), encoding="utf-8")
    return score
```

- [ ] **Step 4: Run the tests to verify they pass**

Expected: `5 passed` in `test_abscore.py`.

- [ ] **Step 5: Commit**

Subject: `meta-skill-ab-test: abscore, the floor and the per-arm score with void rules`.
`git -C <scratch>/wt-m2 add plugins/bitranox/skills/meta-skill-ab-test && git -C <scratch>/wt-m2 commit -F <scratch>/m2-t14.txt -- plugins/bitranox/skills/meta-skill-ab-test`

### Task 15: `abtest.py`, the CLI: init, seal, run, score, prune-run

**Files:**
- Create: `plugins/bitranox/skills/meta-skill-ab-test/scripts/abtest.py`
- Test: `plugins/bitranox/skills/meta-skill-ab-test/tests/test_abtest.py`

**Interfaces:**
- Consumes: everything from Tasks 9-14, by the names in their Produces blocks.
- Produces: `main(argv=None, *, login_check=abguard.check_login) -> int` (the login check is injected at the entry point so tests never touch the network and never monkeypatch a sibling module) with subcommands `init <run_dir> [--repo --base --skills-ref --skill]`, `seal <run_dir>`, `run <run_dir> [--dry-run] [--only C] [--credentials <path>] [--skills-repo <path>] [--max-turns N]`, `score <run_dir>`, `prune-run <run_dir>`; `--json` on every one; exit 0 yes / 1 no / 2 could not run; `run_arm(ctx, round_no, name) -> dict` (one arm start to finish; `ctx` is the `RunContext` dataclass below); `journal.jsonl` rows `{"step": "seal"|"arm"|"score"|"pause", "round", "arm", "status", "at"}`. M3 adds `judge` and `report` beside these.

**Out of scope** - do NOT touch, though they look related:
- `judge`, `report` - M3; the parser must not carry stubs for them (a stub that prints "not implemented" is a verb that writes no row).
- Parallel arms - cut (user decision: serial).

**STOP conditions** - stop and report rather than improvise, if:
- `seal` would need to commit into a run dir that is not a git repo and `git init` fails there;
- the real `claude` refuses `--dangerously-skip-permissions` in the headless form (CLI change): report the stderr tail.

- [ ] **Step 1: Write the failing tests**

```python
"""abtest CLI: init, seal, run (dry and fake-live), score, prune-run, resume; through the fake claude."""
import json
import os
from pathlib import Path

import _ablib as L
import abtest as T

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _init_and_fill(tmp_path, scratch_repo, skills_repo, n=1):
    run_dir = tmp_path / "run1"
    assert T.main(["init", str(run_dir), "--repo", str(scratch_repo), "--base", (scratch_repo / ".base").read_text(),
                   "--skills-ref", (skills_repo / ".ref").read_text(), "--skill", "demo-skill"]) == 0
    toml = (run_dir / "abtest.toml").read_text(encoding="utf-8")
    toml = toml.replace('gate = ["make", "test"]', 'gate = ["./gate.sh"]').replace("n = 3", f"n = {n}")
    toml = toml.replace('changes = ["<one change per entry>"]', 'changes = ["louder"]')
    # FAKE_CLAUDE_STREAM must reach the arm: the arm env is built from env_keep only.
    toml = toml.replace("warmth_tolerance = 0.25", 'warmth_tolerance = 0.25\nenv_keep = ["PATH", "LANG", "FAKE_CLAUDE_STREAM"]')
    (run_dir / "abtest.toml").write_text(toml, encoding="utf-8")
    (run_dir / "task.md").write_text("Do the task.\n", encoding="utf-8")
    # seal refuses a PREREG that still holds a <placeholder>, so the skeleton is replaced, not appended to.
    (run_dir / "PREREG.md").write_text("# Pre-registration\n\nQuestion: is V1 cheaper?\nH1: V1 is cheaper.\n", encoding="utf-8")
    (run_dir / "variants" / "V1" / "SKILL.md").write_text("---\nname: demo-skill\n---\nLOUDER.\n", encoding="utf-8")
    return run_dir


def _env(fake_claude_path, tmp_path):
    creds = tmp_path / "creds.json"
    creds.write_text(json.dumps({"claudeAiOauth": {"accessToken": "fake"}}), encoding="utf-8")
    creds.chmod(0o600)
    return {"PATH": f"{fake_claude_path}{os.pathsep}{os.environ['PATH']}",
            "FAKE_CLAUDE_STREAM": str(FIXTURES / "stream-control.jsonl")}, creds


def test_init_writes_skeletons_and_a_git_repo(tmp_path, scratch_repo, skills_repo):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    assert (run_dir / ".git").is_dir() and (run_dir / "variants" / "V1").is_dir()
    assert "frozen/" in (run_dir / ".gitignore").read_text(encoding="utf-8")
    assert T.main(["init", str(run_dir)]) == 1, "refuses to overwrite"


def test_seal_validates_commits_and_is_once(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    assert T.main(["seal", str(run_dir), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and out["data"]["weights"]["correctness"] == 0.30
    assert L.git(run_dir, "status", "--porcelain").stdout == "" and "weights" in (run_dir / "PREREG.md").read_text(encoding="utf-8")
    assert T.main(["seal", str(run_dir)]) == 1, "already sealed"


def test_seal_refuses_a_bad_profile(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    (run_dir / "abtest.toml").write_text("[workpiece]\nrepo = 1\n", encoding="utf-8")
    assert T.main(["seal", str(run_dir), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_run_refuses_before_seal(tmp_path, scratch_repo, skills_repo):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    assert T.main(["run", str(run_dir), "--dry-run"]) == 2


def test_dry_run_exercises_everything_but_claude_p(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ, **env))
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(["run", str(run_dir), "--dry-run", "--credentials", str(creds), "--skills-repo", str(skills_repo)]) == 0
    rows = L.read_jsonl(run_dir / "journal.jsonl")
    assert [r["status"] for r in rows if r["step"] == "arm"] == ["dry", "dry"]
    for name in ("r1-C", "r1-V1"):
        arm = run_dir / "arms" / name
        assert (arm / "result.json").is_file() and not (arm / "cfg").exists() and not (arm / "stream.jsonl").exists()
        assert json.loads((arm / "result.json").read_text(encoding="utf-8"))["floor"]["passed"] is True
    assert not (scratch_repo / ".claude" / "worktrees" / f"abx-{run_dir.name}-r1-C").exists()
    assert L.git(scratch_repo, "rev-parse", "--verify", "-q", f"abx/{run_dir.name}/r1-C").returncode == 0


def test_live_run_then_score_then_resume_skips_paid_steps(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, n=2)
    env, creds = _env(fake_claude_path, tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ, **env))
    assert T.main(["seal", str(run_dir)]) == 0
    ok = lambda creds_path: "ok"  # noqa: E731 - the injected login check; no network under test
    assert T.main(["run", str(run_dir), "--only", "C", "--credentials", str(creds), "--skills-repo", str(skills_repo)], login_check=ok) == 0
    rows = L.read_jsonl(run_dir / "journal.jsonl")
    assert [(r["round"], r["arm"], r["status"]) for r in rows if r["step"] == "arm"] == [(1, "C", "ran"), (2, "C", "ran")]
    arm = run_dir / "arms" / "r1-C"
    res = json.loads((arm / "result.json").read_text(encoding="utf-8"))
    assert res["total_cost_usd"] == 0.25 and res["bundle_commits"] == 1 and not (arm / "cfg").exists()
    assert (arm / "bundle.git").is_file() and (arm / "stream.jsonl").is_file()
    assert T.main(["score", str(run_dir), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["arms"]["r1-C"]["void"] == [] and (arm / "scores.json").is_file()
    before = (arm / "result.json").stat().st_mtime_ns
    assert T.main(["run", str(run_dir), "--only", "C", "--credentials", str(creds), "--skills-repo", str(skills_repo)], login_check=ok) == 0
    assert (arm / "result.json").stat().st_mtime_ns == before, "resume never repeats a paid arm"


def test_quota_pauses_the_run(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ, **env))
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(["run", str(run_dir), "--credentials", str(creds), "--skills-repo", str(skills_repo)], login_check=lambda c: "quota") == 1
    rows = L.read_jsonl(run_dir / "journal.jsonl")
    assert rows[-1]["step"] == "pause" and rows[-1]["status"] == "quota"
    assert not (run_dir / "arms" / "r1-C" / "stream.jsonl").exists()


def test_prune_run_deletes_the_branches(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    monkeypatch.setattr(os, "environ", dict(os.environ, **env))
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(["run", str(run_dir), "--dry-run", "--credentials", str(creds), "--skills-repo", str(skills_repo)]) == 0
    assert T.main(["prune-run", str(run_dir)]) == 0
    assert L.git(scratch_repo, "branch", "--list", f"abx/{run_dir.name}/*").stdout.strip() == ""
```

- [ ] **Step 2: Run them to verify they fail**

Expected: `ModuleNotFoundError: No module named 'abtest'`.

- [ ] **Step 3: Write `abtest.py`**

```python
#!/usr/bin/env python3
"""abtest: A/B test a skill against its variants on one real task in the real repository.

Subcommands (every one takes --json; exit 0 yes / 1 no / 2 could not run):
  init <run_dir> [--repo --base --skills-ref --skill]   write the profile, task and PREREG skeletons
  seal <run_dir>                                       validate and commit them; fixes the weights
  run <run_dir> [--dry-run] [--only ARM] ...           the serial interleaved arms (resumes)
  score <run_dir>                                      per-arm scores and void rules
  prune-run <run_dir>                                  delete the run's branches in the workpiece

The run dir is its own git repo so the pre-registration is append-only. Judging and the report
are M3 (`judge`, `report`).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import abarm
import abguard
import abscore
from _ablib import EXIT_ERROR, EXIT_NO, EXIT_YES, append_jsonl, envelope, git, read_jsonl, rotated_schedule, sha256_file, utc_now
from abprofile import SKELETON, Profile, ProfileError, load_profile
from abstream import OPUS_PREFIX  # noqa: F401 - re-exported for M3's judge

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
GITIGNORE = "frozen/\narms/*/cfg\narms/*/home\narms/*/stream.jsonl\narms/*/bundle.git\narms/*/guard\n"


class RunRefused(RuntimeError):
    """A precondition of the subcommand is not met; exit 2 with this message."""


@dataclass(frozen=True)
class RunContext:
    run_dir: Path
    profile: Profile
    task: str
    credentials: Path
    skills_repo: Path
    dry_run: bool
    max_turns: int


def _emit(as_json: bool, command: str, data: dict[str, Any], ok: bool, text: str, skipped: list[str] | None = None) -> None:
    if as_json:
        print(envelope(command, data, ok=ok, skipped=skipped))
    else:
        print(text)


def _journal(run_dir: Path) -> list[dict[str, Any]]:
    return read_jsonl(run_dir / "journal.jsonl")


def _done(run_dir: Path, step: str, round_no: int, arm: str) -> bool:
    return any(r.get("step") == step and r.get("round") == round_no and r.get("arm") == arm
               and r.get("status") in ("ran", "dry", "scored") for r in _journal(run_dir))


def _record(run_dir: Path, **row: Any) -> None:
    append_jsonl(run_dir / "journal.jsonl", dict(row, at=utc_now()))


def _require_sealed(run_dir: Path) -> None:
    if not any(r.get("step") == "seal" for r in _journal(run_dir)):
        raise RunRefused(f"{run_dir} is not sealed; run `abtest.py seal` first")


def cmd_init(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser()
    if run_dir.exists():
        _emit(args.json, "init", {"run_dir": str(run_dir)}, False, f"{run_dir} already exists; refusing to overwrite")
        return EXIT_NO
    run_dir.mkdir(parents=True)
    (run_dir / "variants" / "V1").mkdir(parents=True)
    text = SKELETON
    for key, value in (("<absolute path of the real repository>", args.repo), ("<40-char sha every arm starts from>", args.base),
                       ("<bitranox-skills sha that carries BITRANOX_MEMORY_WRITES>", args.skills_ref),
                       ("<skill directory name under plugins/bitranox/skills/>", args.skill)):
        if value:
            text = text.replace(key, str(value))
    (run_dir / "abtest.toml").write_text(text, encoding="utf-8")
    (run_dir / "task.md").write_text("", encoding="utf-8")
    (run_dir / "PREREG.md").write_text(PREREG_SKELETON, encoding="utf-8")
    (run_dir / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    proc = git(run_dir, "init", "-q", "-b", "main")
    if proc.returncode != 0:
        raise RunRefused(f"git init failed in {run_dir}: {proc.stderr.strip()}")
    _emit(args.json, "init", {"run_dir": str(run_dir)}, True,
          f"initialised {run_dir}: fill abtest.toml, task.md, PREREG.md and variants/, then seal")
    return EXIT_YES


def cmd_seal(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser()
    if any(r.get("step") == "seal" for r in _journal(run_dir)):
        _emit(args.json, "seal", {}, False, f"{run_dir} is already sealed; amendments are appended to PREREG.md and committed")
        return EXIT_NO
    profile = load_profile(run_dir / "abtest.toml")
    task = (run_dir / profile.workpiece.task_file).read_text(encoding="utf-8") if (run_dir / profile.workpiece.task_file).is_file() else ""
    prereg = (run_dir / "PREREG.md").read_text(encoding="utf-8") if (run_dir / "PREREG.md").is_file() else ""
    problems = []
    if not task.strip():
        problems.append(f"{profile.workpiece.task_file} is empty")
    if not prereg.strip() or "<" in prereg:
        problems.append("PREREG.md is empty or still holds a <placeholder>")
    for v in profile.variants:
        if not any((run_dir / v.dir).rglob("*")):
            problems.append(f"variants/{v.name}: {v.dir} holds no file")
    if problems:
        raise RunRefused("; ".join(problems))
    suite_sha = None
    if profile.floor.suite:
        suite_path = profile.workpiece.repo / profile.floor.suite
        if not suite_path.is_file():
            raise RunRefused(f"floor.suite {suite_path} does not exist at the workpiece")
        suite_sha = sha256_file(suite_path)
    stamp = {"sealed_at": utc_now(), "weights": WEIGHTS, "suite_sha256": suite_sha, "arms": profile.arm_names(),
             "n": profile.run.n, "warmth_tolerance": profile.run.warmth_tolerance}
    with (run_dir / "PREREG.md").open("a", encoding="utf-8") as fh:
        fh.write("\n## Sealed\n\n```json\n" + json.dumps(stamp, indent=1, sort_keys=True) + "\n```\n")
    git(run_dir, "add", "-A")
    proc = git(run_dir, "-c", "user.name=abtest", "-c", "user.email=abtest@localhost", "commit", "-q", "-m", "seal")
    if proc.returncode != 0:
        raise RunRefused(f"seal commit failed: {proc.stderr.strip()}")
    _record(run_dir, step="seal", round=0, arm="", status="sealed")
    _emit(args.json, "seal", stamp, True, f"sealed {run_dir}: {len(profile.arm_names())} arms x {profile.run.n} rounds")
    return EXIT_YES


def run_arm(ctx: RunContext, round_no: int, name: str) -> dict[str, Any]:
    """One arm, start to finish; the result dict is also written to arms/r<round>-<name>/result.json."""
    p = ctx.profile
    label = f"r{round_no}-{name}"
    arm_dir = ctx.run_dir / "arms" / label
    arm_dir.mkdir(parents=True, exist_ok=True)
    repo = p.workpiece.repo
    ws = repo / ".claude" / "worktrees" / f"abx-{ctx.run_dir.name}-{label}"
    branch = f"abx/{ctx.run_dir.name}/{label}"
    cfg, home = arm_dir / "cfg", abarm.arm_home(arm_dir, p.run.home_links)
    result: dict[str, Any] = {"arm": label, "round": round_no, "name": name, "dry_run": ctx.dry_run}
    try:
        frozen = abarm.freeze_variant(ctx.run_dir, p, name, ctx.skills_repo)
        result["frozen"] = {"ref": frozen.skills_ref, "overlay_written": list(frozen.overlay_written)}
        env = abarm.arm_env(cfg, home, p.run.env_keep)
        result["install"] = abarm.install_plugin(cfg, frozen, ctx.credentials, env)
        result["worktree"] = abarm.make_worktree(repo, p.workpiece.base, branch, ws, copy_untracked_claude_md=True)
        result["guard"] = abguard.snapshot(ws, arm_dir / "guard")
        if not ctx.dry_run:
            result.update(abarm.dispatch(arm_dir, ws, env, abarm.claude_argv(ctx.task, ctx.max_turns),
                                         max_tokens=p.run.max_tokens, deadline_s=p.run.deadline_s))
        result["guard_changes"] = abguard.verify(arm_dir / "guard")
        result["floor"] = abscore.run_floor(ws, p, arm_dir)
        result["bundle_commits"] = abarm.bundle(ws, p.workpiece.base, arm_dir / "bundle.git")
        result["prune"] = abarm.prune(ws, repo, p.floor.cache_paths)
    finally:
        abarm.delete_cfg(cfg)
        if ws.exists():
            # A failure above left the tree: remove it so the next attempt can start clean; the branch stays.
            git(repo, "worktree", "remove", "--force", str(ws))
        (arm_dir / "result.json").write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    return result


def cmd_run(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser()
    _require_sealed(run_dir)
    profile = load_profile(run_dir / "abtest.toml")
    ctx = RunContext(run_dir=run_dir, profile=profile, task=(run_dir / profile.workpiece.task_file).read_text(encoding="utf-8"),
                     credentials=Path(args.credentials).expanduser(), skills_repo=Path(args.skills_repo).expanduser(),
                     dry_run=args.dry_run, max_turns=args.max_turns)
    done, skipped = [], []
    for round_no, order in enumerate(rotated_schedule(profile.arm_names(), profile.run.n), start=1):
        for name in order:
            if args.only and name != args.only:
                continue
            if _done(run_dir, "arm", round_no, name):
                skipped.append(f"r{round_no}-{name} already ran")
                continue
            if not ctx.dry_run:
                state = args.login_check(ctx.credentials)
                if state != "ok":
                    _record(run_dir, step="pause", round=round_no, arm=name, status=state)
                    _emit(args.json, "run", {"done": done, "paused_at": f"r{round_no}-{name}", "reason": state}, True,
                          f"paused before r{round_no}-{name}: credential check says {state}", skipped)
                    return EXIT_NO
            result = run_arm(ctx, round_no, name)
            status = "dry" if ctx.dry_run else "ran"
            _record(run_dir, step="arm", round=round_no, arm=name, status=status, stop_reason=result.get("stop_reason"))
            done.append({"arm": result["arm"], "status": status, "cost_usd": result.get("total_cost_usd"),
                         "wall_s": result.get("wall_s"), "floor_passed": result["floor"]["passed"]})
    _emit(args.json, "run", {"done": done}, True, "\n".join(f"{d['arm']}: {d['status']} cost={d['cost_usd']} floor={d['floor_passed']}" for d in done) or "nothing to run", skipped)
    return EXIT_YES


def cmd_score(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser()
    _require_sealed(run_dir)
    profile = load_profile(run_dir / "abtest.toml")
    arms = {d.name: json.loads((d / "result.json").read_text(encoding="utf-8"))
            for d in sorted((run_dir / "arms").glob("r*-*")) if (d / "result.json").is_file()}
    scores = {}
    for label, res in arms.items():
        peers = [r for other, r in arms.items() if other != label and not r.get("dry_run") and r.get("has_result")]
        scores[label] = abscore.score_arm(run_dir / "arms" / label, profile, peers)
        _record(run_dir, step="score", round=res.get("round", 0), arm=res.get("name", ""), status="scored")
    _emit(args.json, "score", {"arms": scores}, True,
          "\n".join(f"{k}: cost={v['cost_usd']} floor={v['floor_passed']} void={v['void'] or '-'}" for k, v in scores.items()) or "no arms")
    return EXIT_YES


def cmd_prune_run(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser()
    profile = load_profile(run_dir / "abtest.toml")
    repo = profile.workpiece.repo
    prefix = f"abx/{run_dir.name}/"
    branches = [b.strip().lstrip("* ") for b in git(repo, "branch", "--list", prefix + "*").stdout.splitlines() if b.strip()]
    for line in git(repo, "worktree", "list", "--porcelain").stdout.split("\n\n"):
        if f"abx-{run_dir.name}-" in line:
            path = line.split("\n")[0].removeprefix("worktree ")
            git(repo, "worktree", "remove", "--force", path)
    deleted = [b for b in branches if git(repo, "branch", "-D", b).returncode == 0]
    _emit(args.json, "prune-run", {"deleted": deleted}, True, f"deleted {len(deleted)} branch(es) under {prefix}")
    return EXIT_YES


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="abtest.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("init", cmd_init), ("seal", cmd_seal), ("run", cmd_run), ("score", cmd_score), ("prune-run", cmd_prune_run)):
        sp = sub.add_parser(name)
        sp.add_argument("run_dir")
        sp.add_argument("--json", action="store_true")
        sp.set_defaults(fn=fn)
        if name == "init":
            for opt in ("--repo", "--base", "--skills-ref", "--skill"):
                sp.add_argument(opt)
        if name == "run":
            sp.add_argument("--dry-run", action="store_true", help="everything but the paid claude -p step")
            sp.add_argument("--only", help="run only this arm name (C or a variant name)")
            sp.add_argument("--credentials", default=str(DEFAULT_CREDENTIALS))
            sp.add_argument("--skills-repo", default=str(DEFAULT_SKILLS_REPO))
            sp.add_argument("--max-turns", type=int, default=400)
    return ap


def main(argv: list[str] | None = None, *, login_check: LoginCheck = abguard.check_login) -> int:
    """Entry point; login_check is the one injectable seam (tests pass a stub, never a monkeypatch)."""
    args = build_parser().parse_args(argv)
    args.login_check = login_check
    try:
        return args.fn(args)
    except (ProfileError, RunRefused, abarm.ArmError, abguard.GuardError, OSError) as exc:
        _emit(args.json, args.cmd, {"error": str(exc)}, False, f"error: {exc}")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Expected: `8 passed` in `test_abtest.py`, and the whole skill suite green (about 46 tests). The `error:` text on stdout under `--json` is the envelope with `ok: false`, as `test_seal_refuses_a_bad_profile` checks.

- [ ] **Step 5: Commit**

Subject: `meta-skill-ab-test: abtest CLI (init, seal, run, score, prune-run) with a resume journal`.
`git -C <scratch>/wt-m2 add plugins/bitranox/skills/meta-skill-ab-test && git -C <scratch>/wt-m2 commit -F <scratch>/m2-t15.txt -- plugins/bitranox/skills/meta-skill-ab-test`

### Task 16: Ship M2 and reach checkpoint 2

**Files:**
- Create: `plugins/bitranox/skills/meta-skill-ab-test/SKILL.md` (a SHORT provisional text: frontmatter with `name: meta-skill-ab-test` and a `description:` that names the trigger - "Use when comparing a shipped bitranox skill against modified variants on one real task in the real repository, judging cost and code pairwise" - and a body of the five subcommands with one line each; the full text is M4, authored on fable)
- Modify (by the generators): `plugins/bitranox/skill_triggers.json`, `docs/skills.md`, `README.md` (the skill count)
- Modify (by the jig): `plugins/bitranox/.claude-plugin/plugin.json`, `pyproject.toml`, `CHANGELOG.md`
- Create (outside every repo): `~/.abtest/<run-id>/` for the dry run and the one real control arm

**Interfaces:**
- Consumes: Tasks 9-15; the pushed M1 release (its sha is the `skills_ref`).
- Produces: a released plugin version carrying the skill; checkpoint 2's numbers in `EXECUTION-USER-REVIEW.md` and `OPEN-WORK.md` [27].

**Out of scope** - do NOT touch, though they look related:
- The full SKILL.md - M4 (fable authoring).
- Any variant - checkpoint 2 runs the CONTROL only (`--only C`), one round.

**STOP conditions** - stop and report rather than improvise, if:
- `build_skill_triggers.py` or `build_skill_docs.py` refuses the provisional SKILL.md (a frontmatter rule): fix the frontmatter, never the generator;
- the dry run's floor FAILS on the workpiece base (the base itself is red): report; the profile's `gate` may be wrong, or the base needs a different commit;
- the real control arm ends `void`, `deadline` or `token_cap`: report the reason with the cost; do not start a second paid arm.

- [ ] **Step 1: The provisional SKILL.md, the generators, the bump**

Write the provisional `SKILL.md` as described (ASCII only). Then from the worktree root:
`python3 plugins/bitranox/hooks/build_skill_triggers.py && python3 plugins/bitranox/hooks/build_skill_docs.py` and raise the skill count by one on every README line that states it (`grep -nE '[0-9]+ skills' README.md` lists them; measured 2026-11-03: three lines).
`<scratch>/m2-notes.md`:

```markdown
### Added

- `meta-skill-ab-test` (MVP): `abtest.py init / seal / run / score / prune-run` compare a shipped skill against variants on one real task in the real repository: serial interleaved arms in nested worktrees with their own config dir and a frozen plugin checkout, exact per-model cost from the stream, an executed floor from the profile, a bundle and a branch per arm, a memory-store guard and `BITRANOX_MEMORY_WRITES=off`, and a resume journal. Judging and the report follow in a later release.
```

Run: `uv run plugins/bitranox/hooks/bump_version.py --part minor --changelog <scratch>/m2-notes.md`

DONE AT THE FRONT OF THE BRANCH: repo-gate refuses a commit under `plugins/` while `plugin.json` equals origin's version, so this bump (with the notes above) is the FIRST commit on the wt-m2 branch, made by the controller before Task 9 is dispatched, as M1's was (bf1948e5). Skip the Run here, and Step 2's commit leaves `CHANGELOG.md pyproject.toml plugins/bitranox/.claude-plugin/plugin.json` out of its pathspec; if origin moved past that version meanwhile, re-bump from origin's `plugin.json` in its own commit.

- [ ] **Step 2: Gate, commit, push, watch CI**

`python3 plugins/bitranox/hooks/repo-gate.py --ci > <scratch>/m2-gate.log 2>&1; echo RC=$? >> <scratch>/m2-gate.log`, read it, expect `RC=0`.
Message file subject: `meta-skill-ab-test: the A/B harness MVP (<version>)`. Then
`git -C <scratch>/wt-m2 add -A plugins/bitranox/skills/meta-skill-ab-test plugins/bitranox/skill_triggers.json docs/skills.md README.md .gitattributes && git -C <scratch>/wt-m2 commit -F <scratch>/m2-t16.txt -- plugins/bitranox/skills/meta-skill-ab-test plugins/bitranox/skill_triggers.json docs/skills.md README.md .gitattributes CHANGELOG.md pyproject.toml plugins/bitranox/.claude-plugin/plugin.json`
`git -C <scratch>/wt-m2 push origin HEAD:master`, then FOREGROUND `uv run <plugin cache>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`; expect exit 0. Fast-forward the main checkout and remove the worktree as in Task 8 step 5.

- [ ] **Step 3: The dry run on the workpiece base (no cost)**

From the INSTALLED plugin (`~/.claude/plugins/cache/bitranox-skills/bitranox/<version>/skills/meta-skill-ab-test/scripts/abtest.py`, after `/plugin marketplace update` and `/reload-plugins`, both typed by the user):
1. `python3 <scripts>/abtest.py init ~/.abtest/<run-id> --repo <workpiece> --base 033e25e8adc43116b7c16a3ff57629aaa744a3df --skills-ref <M1 release sha, 40 chars> --skill process-agents-subagent-driven-development`
2. Fill `abtest.toml` (`gate` = the workpiece's real gate as an argv list; `cache_paths` = its build dir; `n = 1`; `deadline_s` = 7200), `task.md` (the prototype's prompt text for the plan branch, from `EXECUTION-USER-REVIEW.md`'s record of it), `PREREG.md` (question + one hypothesis), `variants/V1/SKILL.md` (a copy of the control's SKILL.md with one marker line added; it is never run here).
3. `python3 <scripts>/abtest.py seal ~/.abtest/<run-id>` then `python3 <scripts>/abtest.py run ~/.abtest/<run-id> --dry-run --only C --json > <scratch>/dry.json 2>&1; echo RC=$? >> <scratch>/dry.json`.
Expected: `RC=0`; `arms/r1-C/result.json` has `floor.passed: true`, `guard.taken: true`, `install.drift: []`, `install.settings_seeded: ["skillListingBudgetFraction"]`, `worktree.claude_md_copied: true` (the workpiece's root CLAUDE.md is untracked); the workpiece shows a branch `abx/<run-id>/r1-C` and NO worktree. Then `prune-run` to drop that branch.

- [ ] **Step 4: ONE real control arm (checkpoint 2; about 25 USD and 1 to 2 h, unverified for this version)**

`python3 <scripts>/abtest.py run ~/.abtest/<run-id> --only C > <scratch>/arm1.log 2>&1; echo RC=$? >> <scratch>/arm1.log` in the FOREGROUND of a dedicated terminal (the user's, since it outlives a tool call: give them the line), then `python3 <scripts>/abtest.py score ~/.abtest/<run-id> --json`.
Read: `result.json` (`stop_reason`, `wall_s`, `total_cost_usd`, `per_model`, `guard_changes`, `bundle_commits`, `floor.passed`), `scores.json` (`void`), `git -C <workpiece> status --porcelain` (must be unchanged), `ls <workpiece>/.claude/worktrees/` (must not hold the arm), `ls ~/.abtest/<run-id>/arms/r1-C/` (no `cfg/`), and the CLAUDE files the arm transcript loaded: the repo's `CLAUDE.md` exactly once (the worktree copy) and its `CLAUDE.local.md` exactly once (count the `Contents of .../CLAUDE` lines in the transcript the stream's session_id names, as the M0 probe did).

- [ ] **Step 5: Record checkpoint 2**

Append to `EXECUTION-USER-REVIEW.md` "[27] checkpoint 2" with the eight numbers above and the decisions they make: the deadline for M5 (about 2x the measured wall time), the token cap, whether the guard stayed clean under the switch, and whether the warmth check can be applied with `n = 3`. Put the cost and duration into `OPEN-WORK.md` [27]. Then STOP: M3, M4 and M5 get their tasks after this checkpoint is read.

---

## Later milestones: tasks come after checkpoint 2

M3 (`abjudge.py`, `abfixes.py`, `abverdict.py`, the `judge` and `report` subcommands, the port of `sdk_guard.py` and `ab_sdk_call.py`), M4 (the full SKILL.md on fable, the liveness pair on a small Python workpiece, docs regeneration) and M5 (the first real experiment) are planned at HIGH and MID altitude above and get their DETAILED tasks once checkpoint 2 is decided: the measured duration and cost of one real arm fix the deadline and the cap, and whether the control arm's bundle holds per-task commits decides how M3 prices a beyond-plan advantage (design S5.2). Task-level code written before that would be a stale brief.

---

## Self-review (run after writing, fixed inline)

1. Spec coverage: design S1 (arms, worktree, config dir, switch, guard, opus assert) -> Tasks 12, 13, 15; S3 profile and CLI verbs init/seal/run/score/prune-run -> Tasks 10, 15; judge/report -> M3 (after the checkpoint, by design); S4 void rules, quota check, resume -> Tasks 13, 14, 15; S5.1 -> Task 1 + Task 12's `copy_untracked_claude_md` and `settings_keep` (checkpoint 1); S5.3 -> Tasks 2-8 + Task 12's switch check; S5.5 -> Task 14; S5.6 -> Task 10; S5.7 -> nothing ported, by design.
2. Placeholder scan: none of TBD/TODO/"similar to"; the angle-bracket placeholders are the profile skeleton's own and the test asserts they are refused.
3. Type consistency: `Profile.arm_names()`, `suite_argv()`, `Frozen.hashes`, `install_plugin(...)["drift"]`, `dispatch(...)["stop_reason"]`, `score_arm(...)["void"]`, journal statuses `ran|dry|scored|sealed|<quota state>` are used by the same names in Tasks 12-15.
4. Absence checks: Task 7's test asserts an EMPTY `.claude` tree under the arm HOME; Task 12's tests assert the worktree is gone and the branch stays; Task 15's resume test asserts an unchanged mtime, not a log line.
5. Observable pass criteria: every checkpoint names a file and a key (`probe-result.json`, `result.json`, `scores.json`, `journal.jsonl`) or a git command.
6. Quoted user decisions: serial interleaved -> `rotated_schedule` in `cmd_run` (no parallelism anywhere); control then finalists and the rubric in the pairwise call -> M3; branch per arm, worktree removed -> Task 12 `bundle`/`prune` and Task 15; new narrow switch -> Tasks 2-8; price from the variant's fixes -> M3 (after checkpoint 2); authoring on fable, executions on opus -> Global Constraints and `run.model == "opus"` in Task 10.
