# Skill Decision Ledger Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> Authoring (skill text, this plan, PREREG) happens in the fable session; every dispatched
> execution runs on opus, pinned and asserted from the run's init record (user directive 2026-11-02).

**Goal:** Give every skill one append-only record of its decisions with reasons, so that a rule is
never dropped, reverted or re-proposed without the editor meeting the original reason first.

**Architecture:** One `decisions.jsonl` per skill inside its existing `.skillwriter/` dir, written
only through a small CLI/library in `plugins/bitranox/hooks/`. Each `rule` entry binds a decision
to a short text anchor quoted from the skill; the commit gate refuses a change whose shipped text
no longer contains a live anchor unless a superseding entry gives the reason, and the SKILL.md edit
guard hands the editing agent the skill's rejected and removed decisions before its first edit.
Hooks, jigs and scripts get no ledger: their record is a `Decisions` block in the module docstring
plus a regression test.

**Tech Stack:** Python 3.14+ standard library only (plugin floor, bare-env import rule), pytest,
JSON Lines, the existing `repo-gate.py` / `skill-edit-guard.py` hooks.

## Context

Skills in bitranox-skills change constantly (1,729 commits, 668 touching a SKILL.md) and A/B testing
of skill variants is starting. The worry: a rule changed forward is later changed back because the
reason is not where the next editor looks.

Measured on 2026-11-05 (commit e33f36b9, 3 behind origin/master):

- A history scan found 4 real forward-and-back cases: 2 flips (`devops-bmk` env model
  f0367056 -> d3a7a0d5 -> 48e94f13; `hooks/secret_patterns.py` 70be81d1 -> 76e5fe42) and 2 silent
  drop-then-restore cases (`meta-dream-project` tier note added b13255aa, dropped by rewrite
  cec8867b, restored e3056501; revert c59cb953 whose reason sits in a later commit).
- The WHY exists but is scattered: commit bodies, `CHANGELOG.md`, 1,079 per-change checklists in
  `skills/<skill>/.skillwriter/` (1 to 69 per skill), and machine-local untracked files
  (`EXECUTION-USER-REVIEW.md`, `USER-DECISIONS.jsonl`, the contribution queue's closed file).
- Nothing is keyed by rule and nothing makes an editor read it: `meta-skill-writer` has no
  "read prior decisions" step, and `skill_review_failures` (repo-gate.py:1184) checks only that a
  fully ticked `.skillwriter/*.md` is co-changed.
- The A/B tool has no verdict step yet and writes nothing into the tested skill's dir.
- `.skillwriter/` already ships to every install unfiltered (1,079 files in the 10.17.0 cache)
  and is already ignored by the mirror gate (`MIRROR_IGNORED_DIRS`, repo-gate.py:1439), the audit
  rooms and the A/B tree hash. A file placed there travels with the skill and breaks no twin.
- Code differs from prose: all 101 hook modules and 38 toolbox jigs have a module docstring
  (66 and 31 with a stated reason) and 144 / 42 test files pin their behaviour.

### User decisions (2026-11-05, this session, quoted from the chosen options)

1. Record shape: "Decision ledger (Recommended)" - "One append-only decisions.jsonl per skill
   inside its existing .skillwriter/ dir ..., written through a small CLI. Each entry: decision,
   why, evidence, reopen-if condition, and a short text anchor quoted from the skill." Confirmed a
   second time after I corrected a wrong figure.
2. Code scope: "Docstring rule for code (Recommended)" - "Skills get the ledger. Hooks, jigs and
   scripts keep their WHY where it already is: a 'Decisions' block in the module docstring
   (decision, reason, evidence, reopen-if) plus a regression test that goes red when the decision
   is reverted. ... no new file and no new gate for code."
3. Backfill: "Seed, then baseline on first touch (Recommended)" - "Now: import the 80 declined
   proposals by script (each passed first through the gate's existing credential and private-name
   scan ... and a durability filter, and tagged as imported), and hand-write entries for the 4
   known flips and the inline 'do not re-add' notes. Later: each skill gets anchored entries for
   its load-bearing rules the first time it is A/B tested or substantially rewritten, as a step in
   the skill-writer procedure."

Two corrections to what decision 3 quotes, both measured after you answered: the declined set is
76 entries with `outcome: rejected` plus 4 with no outcome at all (not a clean 80), and of the "4
known flips" two are skill text (ledger entries) and two are code (docstring blocks).

### Decisions I made that you can overrule (my reading, not yours)

- D1 The record is named for what it holds: `decisions.jsonl`, CLI `skill_decisions.py`. Narrative
  history stays in git and `CHANGELOG.md`.
- D2 It ships with the install (it sits in `.skillwriter/`, which already ships). Consumer on an
  install: an agent about to queue a fix against `skill:<name>` reads the declined list first.
- D3 A ledger-only change (an A/B verdict that changes no skill text) still takes a patch bump and
  a CHANGELOG line, like every change under `plugins/bitranox/`. No gate exemption.
- D4 The ledger holds real decisions only. A SKILL.md change states what it decided in its
  already-mandatory checklist, on one line the gate can check: `Decisions: <id>, <id>` (ids that
  exist in the ledger) or `Decisions: none - <reason>`. No "nothing decided" entries in the ledger.
- D5 The edit guard refuses a SKILL.md edit ONCE, with the skill's rejected and removed decisions
  in the refusal, only when that list is non-empty AND the editing agent's own transcript shows no
  `skill_decisions.py show <skill>` call. An agent that followed the procedure is never refused.
  Same refuse-once pattern you chose for EnterWorktree and the question-premise hook (2026-10-12).
- D6 Entry text is public (the repo is public): no private hosts, paths or repo names; "user
  decision <date>" is allowed, as hook docstrings already do.

## Global Constraints

- Work in a dedicated git worktree created from `origin/master` after a fetch
  (`bitranox:git-worktrees`); the main checkout is shared with live peer sessions.
- `.github/` is template-managed: never edit it.
- History is append-only: no force-push, no rewrite. Each shipped change bumps
  `plugin.json` + `pyproject.toml` + `CHANGELOG.md` together via
  `uv run plugins/bitranox/hooks/bump_version.py --part <part> --changelog notes.md`, starting from
  origin's version, asserting the expected current value.
- Every shipped `.py` has sibling tests written in the same change, run with CI's dependency set:
  `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/ -q`
- Scripts are cross-platform: LF, explicit `encoding="utf-8"`, launched via `run-python.sh`,
  standard library only.
- Every SKILL.md edit goes through `bitranox:meta-skill-writer` (receipt, RED/GREEN, checklist).
- Self-authored text never passes through the shell: commit messages via `git commit -F <file>`,
  ledger entries via `--from-file`.
- No Claude/AI attribution in commits, PRs or files. ASCII punctuation only.
- Peak memory must not grow with ledger size: entries are processed one line at a time.
- A gate judges what the commit SHIPS (the index on commit, HEAD on push), never the working tree,
  and only the skills the change touches; a peer's half-done edit must never block an unrelated
  commit.
- Finish = commit + bump + push + watch CI by head sha and workflow (`ci_wait.py --ref HEAD`),
  without asking; message known peer sessions before pushing behind the pre-push gate.

---

## HIGH plan

Milestones, each a shippable release, with one decision checkpoint:

- **M0 Probe (no shipped code).** Replay real history to measure whether agent-picked text anchors
  catch the two known skill cases and how often they fire on a rewording that changed no meaning.
  **CHECKPOINT 1** decides whether the anchor gate refuses, warns, or is dropped. M1+ below are at
  MID altitude and get step-level tasks once it is decided.
- **M1 Ledger core.** `skill_decisions.py` (library + CLI: add, show, check) with tests.
- **M2 Enforcement and procedure.** Gate checks, edit-guard briefing, `meta-skill-writer` text.
  M1 and M2 ship as ONE release: a ledger nothing reads is not a feature.
- **M3 Seed, code rule, other readers.** Import the declined proposals, record the known cases,
  add the docstring `Decisions` rule to `meta-claude-hooks` and `compuse-toolbox`, give audit rooms
  and the contribution step the declined list.
- **M4 A/B wiring.** `seal` lists the prior decisions a variant reverses; a verdict becomes ledger
  entries. Starts only when the A/B tool's judge/report milestone exists; owned jointly with the
  A/B session.

Cut (YAGNI): a ledger for hooks/jigs; full backfill of 83 skills; a narrative history file; a
semantic "is this a re-add" judge; "must not reappear" anchors (a skill that warns against a
rejected alternative quotes it, as `devops-bmk/SKILL.md:75` does, so the check cannot work); a
separate re-anchor verb; an exemption from the version bump.

Risks, ranked:

1. Anchors fire on rewordings that change nothing, turning the gate into ceremony. M0 measures it.
2. The gate blocks unrelated work. Addressed by design (ships-only, touched skills only,
   merge-base) and by fixing the existing changed-path defect first (Task M2.1).
3. Imported entries are weak. They carry `origin: imported`, tier `inherited`, no anchors.
4. Peer sessions meet the new gate mid-work. Announce at release; the skill text ships with it.
5. Private names leaking into a public file. `check_secrets` scans every tracked file; the CLI
   refuses typographic tells; the skill text states rule D6.

## MID plan

### The ledger file

`plugins/bitranox/skills/<skill>/.skillwriter/decisions.jsonl`: UTF-8, LF, one JSON object per
line, append-only. The skill name is the directory, never a field, so a rename carries the ledger.
Ids are unique within one ledger only.

Entry (schema `v: 1`):

```json
{"v": 1, "id": "d-20261105-3fa9c1d2", "date": "2026-11-05", "kind": "rule",
 "topic": "env-model", "decision": "bmk installs alone as a shared uv tool; project tests run in the project venv.",
 "why": "The earlier per-project env was the inverse of what bmk 3.8.0+ does.",
 "evidence": {"tier": "measured", "text": "bmk 3.8.0 release behaviour, checked against the installed tool"},
 "reopen_if": "bmk changes its env model again (check its CHANGELOG first).",
 "anchors": ["bmk alone, shared across projects"],
 "supersedes": [], "refs": ["checklist-20260715-env-model.md"], "origin": "authored"}
```

- `kind`: `rule` (the text states this; at least one anchor), `removed` (a rule deliberately taken
  out), `rejected` (an alternative, proposal, declined gap or losing A/B variant NOT adopted),
  `void` (withdraws an entry written in error; names it in `supersedes`).
- `why` and `reopen_if` are mandatory and non-empty for every kind except `void` (`why` only).
- `evidence.tier`: `measured`, `user`, `argued`, `inherited`.
- `anchors` (rule entries only): phrases that must occur in the skill's shipped Markdown.
  Normalising before the match: per line strip leading blockquote markers and one list marker,
  then collapse every whitespace run to one space; case-sensitive. A table re-pad, a line re-wrap
  and a blockquote re-wrap therefore never fire. Length 20 to 200 characters after normalising.
  At `add` time an anchor must occur EXACTLY once in the corpus, so a copy elsewhere cannot keep
  a deleted rule's anchor alive.
- Corpus: the skill dir's tracked `*.md` files except `.skillwriter/` and `tests/`.
- `supersedes`: ids this entry replaces. An entry is LIVE when no later entry supersedes it.
  Reworded with the same meaning, split in two, merged: new `rule` entries that supersede the old.
- `id`: `d-<yyyymmdd>-<first 8 hex of sha256 over the entry's canonical JSON>`, so two worktrees
  appending at once never collide and a same-day rewording gets its own id; `.gitattributes` gains
  `plugins/bitranox/skills/*/.skillwriter/decisions.jsonl text eol=lf merge=union`.
- `origin`: `authored`, `imported`, `baseline`, `ab`.
- A skill deleted or folded into another: its ledger goes with it; the absorbing skill records a
  `removed` or `rule` entry whose `refs` name `<old-skill>:<id>`.

### `plugins/bitranox/hooks/skill_decisions.py` (new; tests `hooks/tests/test_skill_decisions.py`)

Lives in `hooks/` because `repo-gate.py` and `skill-edit-guard.py` import it. Library functions
(names fixed here, later tasks rely on them):

- `normalise(text) -> str`, `anchor_occurs(anchor, text) -> bool` (moved unchanged from M0)
- `ledger_path(skill_dir) -> Path`
- `parse_entries(lines) -> Iterator[dict]` (generator over any iterable of lines, so the gate can
  feed it a staged blob; raises `LedgerError(line_no, reason)`)
- `live_entries(lines_factory) -> Iterator[dict]` (two passes: the first keeps superseded ids only)
- `validate_entry(entry) -> list[str]` (one `<field>: <reason>` line each)
- `append_entries(skill_dir, entries) -> list[str]` (assigns id/date/v, validates, checks anchors
  against the corpus, refuses a duplicate id and typographic tells via `tell_chars`, appends)
- `check_ledger(lines_factory, corpus_text) -> list[Finding]` (`Finding`: entry id, topic, the
  vanished anchor, the entry's why and reopen_if)
- `render_brief(lines_factory, budget_chars=6000) -> str` (live rejected and removed entries in
  full until the budget is spent, then a count of what is left and the `show` command)

CLI (`--json` envelope `{ok, command, data, skipped}` on every verb; exit 0 yes, 1 findings,
2 could not run; diagnostics on stderr; no tracebacks):

- `add --from-file entries.json` (one object or a list; each names its `skill`)
- `show <skill> [--skill-dir DIR] [--kind K[,K]] [--topic T] [--id ID] [--all] [--full]`
  (default: live entries, one line each; `--skill-dir` reads a ledger elsewhere, for example the
  marketplace ledger while editing a tool-repo twin)
- `check [<skill> ...] [--skills-dir DIR] [--text-root DIR]` (no skill = every ledger; reads the
  working tree, for use by hand and by CI)

Held in memory: the current line, the set of superseded ids (about 20 bytes each), and for a
check the normalised Markdown of ONE skill. A test measures peak memory at 1,000 and 20,000
entries.

### Gate (`plugins/bitranox/hooks/repo-gate.py`, tests in `hooks/tests/`)

- **M2.1, first and in its own commit:** `_changed_vs_origin` (line 1039) diffs against the TIP of
  `origin/master`, so a checkout that is behind lists a peer's pushed paths as its own changes.
  The checklist rule survives that only because reading the peer's missing file raises `OSError`
  and hits `continue` (line 1210). Change the base to `git merge-base HEAD origin/master`, with a
  test that builds a repo whose origin moved ahead and asserts the peer's path is not listed.
- `check_skill_decisions(root, stage)` in hook and pre-push mode: for each skill the change
  touches, read the ledger and the corpus from what the commit ships (`_checked_out_bytes` /
  `shipped_files` at `stage`, the mirror check's own readers) and run `check_ledger`. Also refuse
  a ledger line that was present at the merge-base and is gone (append-only), except when that
  skill's `SKILL.md` is deleted in the same change. Refusal text prints the entry's decision, why
  and reopen_if and names the way out: `add` a superseding entry with its reason.
- The same function in `--ci` mode sweeps EVERY ledger on disk (CI has a clean checkout).
- `skill_review_failures` gains the D4 line: among the co-changed `.skillwriter/*.md` files of a
  changed SKILL.md, one must hold `Decisions: ...` naming ids present in the shipped ledger, or
  `Decisions: none - <reason>`.
- Each refusal appends one line to `~/.claude/self-improve-audit/skill-decision-gate.jsonl`
  (time, skill, entry id), so the 30-day review can count them.
- `_LF_SUFFIXES` (line 219) gains `.jsonl`.
- **M2b, mirrored skills:** when a TOOL repo commit touches a twin, the mirror check also runs the
  marketplace ledger against the twin's shipped text, so a rule is not dropped at its source
  (`devops-bmk`, one of the two known flips, is mirrored). Anchors must avoid the three
  by-convention divergences (name, H1 suffix, self-install blockquote).

### Edit guard (`plugins/bitranox/hooks/skill-edit-guard.py`)

After the existing receipt and skill-load checks pass, in this order: no session id -> allow;
`render_brief` empty or the ledger unreadable -> allow (the gate owns integrity); the agent's own
transcript (already resolved by `_agent_transcript`) holds a Bash call running
`skill_decisions.py show` for this skill -> allow; the refused-once flag for (agent, skill) is
stored -> allow; otherwise store the flag with `self_improve_signals.session_state_path` (the
`enter-worktree-first-refusal.py` pattern: a flag that cannot be stored lets the call through) and
refuse with the brief plus "re-send the edit, revised or unchanged; the re-send is not refused".
The module docstring records the decision, its pricing and its reopen condition in the new
`Decisions` block form. Pricing task before it ships: replay real transcripts
(`guard_replay.py`) and count first SKILL.md edits per agent that would have been refused.

### Skill and doc text (each through meta-skill-writer, each with its own ledger entries)

- `meta-skill-writer/SKILL.md`: a "read the decisions" step right after Step 0
  (`show <skill> --kind rejected,removed --full`, then the one-line index; for a tool-repo twin
  pass the marketplace `--skill-dir`); the baseline pass rule (no `rule` entries yet AND the edit
  is a rewrite or an A/B test: first record the skill's load-bearing rules as `origin: baseline`
  entries, in their own commit); an "append entries" step in REFACTOR (every decision the edit
  makes; a gap declined for a reason that will still hold next time becomes a `rejected` entry);
  the `Decisions:` checklist line; how to pick an anchor (the guidance M0 tests); the carve-out
  in "Keep out of both" (lines 627-657): the ledger holds decision, reason, evidence and
  reopen-if, still no session narrative; rule D6.
- `CONTRIBUTING.md` (lines 238-241), repo `CLAUDE.md` (a short maintainer section).
- M3: `meta-claude-hooks/SKILL.md` + `references/authoring.md` and `compuse-toolbox/SKILL.md`
  ("Building or enhancing a jig"): the docstring `Decisions` block (decision, why, evidence,
  reopen if; a rejected alternative the same way) and "pin it with a test that fails when the
  decision is reverted, and name the test in the block".
- M3: `meta-self-improve/SKILL.md` step 2: before queueing a fix against `skill:<name>`, read
  that skill's rejected and removed entries; a skill-targeted contribution dropped at integration
  gets its reason added to the ledger in the source repo.
- M3: `meta-skill-audit/scripts/audit_skills.py` (lines 768, 897 strip `.skillwriter`): write the
  rendered brief into each audit room, so reviewers stop re-proposing declined items.
- M3: `meta-adopting-external-skills/SKILL.md`: adoption writes the first entry.

### Seed (M3, throwaway scripts in the scratchpad, never shipped)

- Select closed contribution entries with `target` starting `skill:` and `outcome == "rejected"`
  (76 today), strip a `bitranox:` prefix from the target, drop targets that are test fixtures
  (`a`, `b`, `c`, `foo`) or live outside this repo, and list what was skipped and why. The 4
  entries with no outcome are read separately and included only if they state a decision.
- Read every candidate in session; keep those that state a durable decision (not "already
  shipped", not "duplicate", not task-local); record kept and dropped counts per reason.
- Rewrite each kept reason to rule D6; tag `origin: imported`, tier `inherited`, no anchors.
- Known cases: anchored `rule` entries for the `devops-bmk` env model and the `meta-dream-tree`
  tier note; `Decisions` docstring blocks for `hooks/secret_patterns.py` and the memory-ownership
  revert where the docstring does not already say it.
- Inline "do not re-add" notes: examine each grep hit in SKILL.md files and hook sources; record
  those that are decisions about the skill, and report the ones that are not (an early reading
  says the two SKILL.md hits are queue procedure; verify before skipping).
- Publish only after `repo-gate.py --ci` and the toolbox `pushcheck` pass on the unpushed range.

### A/B wiring (M4, interface fixed now, built later)

- `abtest.py seal`: runs `check_ledger` with the control skill's ledger against the FROZEN skill
  dir with the variant overlay applied (a variant dir holds only the files it overrides, so
  checking the bare variant dir would report every untouched reference as dropped), writes
  `sealed/prior-decisions.json`, and refuses to seal unless `PREREG.md` has a
  `## Prior decisions` section naming every reversed entry id (`none` when there are none, `all`
  for a variant that removes the skill) and a `## Reopen if` section.
- After the report: `skill_decisions.py add --from-file` with entries drafted from the verdict
  (HARMFUL or NEUTRAL variant -> `rejected` with the numbers and run id; adopted variant ->
  `rule`, `origin: ab`; TRADE-OFF -> entry only after a recorded user decision).

### Verification per milestone

- M1: the test module passes with CI's dependency set; mutation check on the normaliser, the
  anchor matcher and the live-entry filter (`mutation_arm`); a failing CLI call prints one line
  and exits 2; `add` then `show` on a scratch copy of a real skill.
- M2: in a scratch worktree, delete an anchored sentence and attempt a commit: refused, naming the
  entry and its reason; add a superseding entry: passes. Controls: an unrelated commit made while
  another skill's working copy is mid-edit passes; a commit made on a checkout behind origin
  passes; `git commit -- SKILL.md` with the ledger line unstaged is refused. Guard: a fresh
  session that skips `show` is refused once with the brief and the re-send passes; a session that
  ran `show` is not refused; a skill with an empty ledger is never refused. `repo-gate.py --ci`
  green. RED/GREEN probes of the changed `meta-skill-writer` passages with
  `bitranox:baseline-probe` agents.
- M3: `check` over every ledger exits 0; `repo-gate.py --mirrors` verdicts unchanged.
- M4: a variant that removes an anchored rule cannot be sealed until PREREG names the entry.

### Review after 30 days (pre-registered, outcome per branch)

Count: lines in `skill-decision-gate.jsonl`, superseding entries written after a refusal, A/B
seals that listed a prior decision, and the share of co-changed checklists saying
`Decisions: none`.

- If at least one refusal or seal hit named a real earlier decision: keep everything as built.
- If none did AND more than half of the refusals were answered by an entry whose `why` says the
  text was only reworded: bring you the numbers and the option to demote the gate to a warning.
- If there were no refusals at all: keep, and review again 30 days later.

---

## DETAILED plan, milestone M0: the anchor replay probe

Later milestones get their step-level tasks once Checkpoint 1 is decided.

### Task M0.1: Workspace and records

**Files:**
- Create: `docs/plans/2026-11-05-skill-decision-ledger.md` (this plan, in the worktree)
- Modify: `OPEN-WORK.md` (one new item via the `backlog_add` tool)
- Modify: `EXECUTION-USER-REVIEW.md` (git-ignored, main checkout)

- [ ] **Step 1:** `ListAgents`; message live peer sessions that a worktree `skill-decisions` is
      being created and that nothing in the main checkout is edited except the two record files.
- [ ] **Step 2:** Fetch, create the worktree from `origin/master` (`bitranox:git-worktrees`).
- [ ] **Step 3:** Copy this plan to `docs/plans/2026-11-05-skill-decision-ledger.md`; add the
      backlog item; append D1 to D6 and the three user decisions to `EXECUTION-USER-REVIEW.md`,
      quoting the chosen options from `USER-DECISIONS.jsonl` verbatim.
- [ ] **Step 4:** Capture the two parked learnings (last section) via `bitranox:meta-self-improve`.
- [ ] **Step 5:** `git commit -F <msgfile> -- docs/plans/2026-11-05-skill-decision-ledger.md OPEN-WORK.md`.

### Task M0.2: Pre-register the probe

**Files:**
- Create: `docs/plans/2026-11-05-skill-decision-ledger-prereg.md`

- [ ] **Step 1:** Write the PREREG before any replay output exists, with exactly this content:

  - Question: do anchors picked by an agent under the planned guidance catch real rule changes,
    and how often do they vanish at a commit that changed no meaning?
  - Skills: `devops-bmk`, `compuse-toolbox`, `meta-skill-writer`. Histories are read with
    `git log --follow`. The trial window of each skill is the second half of its SKILL.md
    commits and must hold at least 20 commits; a skill with fewer is replaced by the next skill
    in the churn ranking, and the replacement is recorded.
  - Anchor picking: one opus subagent per skill receives ONLY the SKILL.md text at the window's
    first commit and the guidance paragraph ("quote 20 to 200 characters that are the stable core
    of one rule, unique in the file, not inside a table row, not a heading"), and returns 20
    anchors with the rule each stands for. It is not told what the probe measures.
  - Fire: a window commit after which an anchor no longer occurs in the normalised SKILL.md.
  - Labelling: a second opus subagent, shown only the before and after text around each fired
    anchor and the rule it stood for, labels the event MEANING-CHANGED (rule altered, removed or
    moved out of the file) or REWORDED (same rule, different words). It does not see the anchor
    picker's output beyond that pair and is not told the thresholds.
  - Positive control 1 (must fire): an anchor taken from the "Tier of the promotion decision"
    bullet as added in b13255aa is present before cec8867b and absent after it.
  - Positive control 2 (must fire): an anchor taken from the env-model sentence as written in
    f0367056 is absent after d3a7a0d5, and one from the sentence d3a7a0d5 wrote is absent after
    48e94f13.
  - Negative controls (must not fire), synthesised from one recorded commit of each skill: a
    paragraph re-wrapped at 60 columns, a blockquote re-wrapped, a table re-padded, an ordered
    list renumbered.
  - Metric: REWORDED fires per 10 window commits, per skill; and MEANING-CHANGED fires in total.
  - Outcome A (build the refusing gate as designed): both positive controls fire, no negative
    control fires, and the median over the three skills is at most 1 REWORDED fire per 10 commits.
  - Outcome B (stop and redesign with you): a positive control does not fire or a negative
    control fires. The matcher is wrong for its purpose.
  - Outcome C (bring you the numbers and two options): controls behave but the median is above
    1 per 10. Option 1 demotes the anchor check to a warning in the skill-writer step; option 2
    keeps the refusal. The brief, the `Decisions:` line and the A/B wiring are unaffected.
  - Falsifiers: zero fires of either label across all three skills, or every fire carrying the
    same label, means the instrument is broken; read ten events by hand before any conclusion.

- [ ] **Step 2:** Commit the PREREG alone, before Task M0.3 runs.

### Task M0.3: Build the replay harness (scratchpad, not shipped)

**Files:**
- Create: `<scratchpad>/anchor_replay.py`, `<scratchpad>/test_anchor_replay.py`

**Interfaces:**
- Produces: `normalise(text) -> str` and `anchor_occurs(anchor, text) -> bool`; M1 moves both
  unchanged into `skill_decisions.py`.

**STOP conditions:** a control sha does not resolve; `git log --follow` cannot carry
`meta-dream-tree` back through `meta-dream-project`; a window holds fewer than 20 commits and no
replacement skill qualifies; the script would write outside the scratchpad.

- [ ] **Step 1:** Write the failing tests first:

```python
from anchor_replay import anchor_occurs, normalise

LINE_SEPARATOR = chr(0x2028)  # built with chr(): a typed escape would land as the raw character


def test_rewrap_and_repad_do_not_break_an_anchor():
    anchor = "Do **not** add `--with .` to the install line"
    rewrapped = "Do **not** add\n   `--with .`   to the\ninstall line"
    assert anchor_occurs(anchor, rewrapped)


def test_a_blockquote_rewrap_does_not_break_an_anchor():
    anchor = "never restore the per-project env"
    assert anchor_occurs(anchor, "> never restore the\n> per-project env")


def test_a_renumbered_list_item_keeps_its_anchor():
    anchor = "run the gate before the push"
    assert anchor_occurs(anchor, "3. run the gate before the push")
    assert anchor_occurs(anchor, "- run the gate\n  before the push")


def test_a_reworded_sentence_breaks_the_anchor():
    anchor = "bmk installs as a persistent uv tool"
    assert not anchor_occurs(anchor, "bmk installs into a per-project .venv-bmk")


def test_unusual_line_separators_count_as_whitespace():
    anchor = "first half second half"
    assert anchor_occurs(anchor, "first half" + LINE_SEPARATOR + "second half")
```

- [ ] **Step 2:** Run `uv run --with pytest python -m pytest <scratchpad>/test_anchor_replay.py -q`.
      Expected: FAIL, `ModuleNotFoundError: anchor_replay`.
- [ ] **Step 3:** Implement:

```python
import re

_QUOTE_MARKERS = re.compile(r"^(?:>[ \t]?)+")
_LIST_MARKER = re.compile(r"^(?:[-*+]|[0-9]+[.)])[ \t]+")


def normalise(text):
    """One-space-separated words of `text`, without blockquote and list markers at line starts."""
    words = []
    for line in text.splitlines():
        line = _LIST_MARKER.sub("", _QUOTE_MARKERS.sub("", line.strip()))
        words.extend(line.split())
    return " ".join(words)


def anchor_occurs(anchor, text):
    return normalise(anchor) in normalise(text)
```

  plus the replay: per skill list `(sha, path-at-that-commit)` with
  `git -C <repo> log --follow --name-only --format=%H --reverse -- <path>`, read each version
  with `git show <sha>:<path>`, hold only the previous and the current text, and append one JSON
  line per (commit, fired anchor) to `<scratchpad>/replay.jsonl` with the 400 characters around
  the anchor's old position before and after.
- [ ] **Step 4:** Run the tests. Expected: 5 passed.

### Task M0.4: Run the probe

- [ ] **Step 1:** Run the four negative controls and the two positive controls first, by sha,
      and record their results in the PREREG file BEFORE any window replay.
- [ ] **Step 2:** Dispatch the three anchor-picking subagents (opus), each with its own
      `mktemp -d` scratch dir named in the prompt; verify every returned anchor occurs exactly
      once in its window-start text and drop-and-replace none silently (record any that fail).
- [ ] **Step 3:** Run the replay over the three windows; the script writes its own exit status
      to `<scratchpad>/replay.rc`. Require the commits examined per skill to equal the window
      size computed in Task M0.2.
- [ ] **Step 4:** Dispatch the labelling subagent (opus, effort medium) over `replay.jsonl`;
      spot-check ten labels against `git show` by hand.
- [ ] **Step 5:** Compute the metric; write counts, the outcome letter and the artifact paths
      (copied to `.plan/skill-decisions/`) into the PREREG under `## Result`, tagged MEASURED.

### CHECKPOINT 1

Report to the user: the controls, REWORDED fires per 10 commits for each skill, the outcome
letter, and for Outcome A the step-level tasks for M1 and M2 appended to the plan file. Outcome B
stops; Outcome C asks one question.

## Critical files

- `plugins/bitranox/hooks/repo-gate.py` (219 `_LF_SUFFIXES`, 1039-1049 `_changed_vs_origin`,
  1184-1222 review gate, 1439 mirror ignore, 1470 `_checked_out_bytes`, 1601 `shipped_files`,
  2687-2746 `run_checks`)
- `plugins/bitranox/hooks/skill-edit-guard.py`, `enter-worktree-first-refusal.py` (refuse-once
  pattern), `self_improve_signals.py:201` (`session_state_path`), `tell_chars.py`
- `plugins/bitranox/hooks/tests/conftest.py` (`_HOOK_MODULES` for hyphenated modules)
- `plugins/bitranox/skills/meta-skill-writer/SKILL.md` (627-686, 1084-1125, 1348-1472, 1519-1635)
- `plugins/bitranox/skills/meta-skill-ab-test/scripts/abtest.py`, `abarm.py` (186-265 overlay and
  frozen skill dir); `docs/plans/2026-11-03-ab-test-skill-design.md` (labels, lines 88-99)
- `plugins/bitranox/skills/meta-skill-audit/scripts/audit_skills.py` (768, 897)
- `plugins/bitranox/skills/meta-claude-hooks/SKILL.md`, `compuse-toolbox/SKILL.md` (lines 421-425)
- `.gitattributes`, `CONTRIBUTING.md`, `CLAUDE.md`, `CHANGELOG.md`

## Found on the way (queue at Task M0.1, not part of this plan)

- `_changed_vs_origin` diffs against origin's tip (verified by reading it); fixed here as M2.1
  because the new checks stand on it.
- The real closed-contribution file holds 6 entries targeting `skill:a`, `skill:b`, `skill:c`,
  `skill:foo`: a test or probe wrote into the live audit store (reviewer's count, not re-counted).
- `meta-memory-settings` still triggers on "forget less/more" although the `forgetting` setting
  was dropped in b79e6db8 (reported by the history scan, unverified).
- The explorers' counts of checklists with a "Gaps declined" section disagreed (122 and 98); a
  heading-anchored grep gives 16 files in 15 skills.

## Learnings to capture once plan mode ends (Task M0.1, via bitranox:meta-self-improve)

- `~/.claude/self-improve-audit/*.contrib-rejected.jsonl` holds every CLOSED contribution, shipped
  ones included (607 skill-targeted: 527 shipped, 76 rejected, 4 without an outcome); the file
  name says "rejected". I quoted its line count to the user as "629 declined" and had to retract
  it. Candidate: a recurrence of "audit what a number counts before quoting it", plus a
  contribution against `contrib_queue.py` to name the file for what it holds.
- A subagent dispatched in the same message as the Write of the file it was told to read started
  while that Write was refused by a hook, so its input did not exist yet. Candidate: a recurrence
  of "never send a dependent call as a parallel sibling of the step that produces its input".
