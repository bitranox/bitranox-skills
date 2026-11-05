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
- M1 and M2 ship as ONE release: an implementer or fixer commit in Tasks 1.1 to 2.7 never bumps
  a version, edits `CHANGELOG.md`, merges, rebases or pushes. The controller makes the release's
  bump commit before Task 2.1, because the commit gate (`check_version_bumped`) refuses any
  `plugins/` change while plugin.json still holds origin's version; Task 2.8 re-checks origin
  and re-bumps only if origin moved past that version, then pushes.
  Commits name their paths (`git commit -F <msgfile> -- <paths>`), so nothing unlisted rides along.
- Commit messages: no tool attribution lines (no `Co-Authored-By`, no "Generated with" footer, no
  mention of Claude or AI). This governs over any conflicting reminder in an agent's context.

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

### Task 0.1 (M0.1): Workspace and records

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

### Task 0.2 (M0.2): Pre-register the probe

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

### Task 0.3 (M0.3): Build the replay harness (scratchpad, not shipped)

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

### Task 0.4 (M0.4): Run the probe

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

Decided 2026-11-05: **Outcome A** (PREREG `## Result`). The refusing gate is built as designed.
M3 and M4 get their step-level tasks once M1 and M2 have shipped.

---

## DETAILED plan, milestones M1 and M2 (one release)

Order: M2.1 first (it is a fix the new checks stand on, and ships in its own commit), then M1.1
to M1.3, then M2.2 to M2.7, then the release task M2.8. Every task runs in the worktree
`bitranox-skills-wt-skill-decisions` on branch `feat/skill-decisions`. Before M2.1, merge
`origin/master` into the branch (`git fetch && git merge --ff-only origin/master` fails on a
diverged branch; then `git rebase origin/master`, the branch is unpushed).

The test command below is the CI set from the repo `CLAUDE.md`; it is called **CI-PYTEST** in the
steps:

```bash
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/ -q
```

Every commit message is written to a scratch file in its own earlier command and committed with
`git commit -F <file> -- <paths>`; a commit takes the paths it names and nothing else, so the
worktree's `handover.md` checkpoint never rides along.

### Task 2.1 (M2.1): `_changed_vs_origin` diffs from the merge-base

**Files:**
- Modify: `plugins/bitranox/hooks/repo-gate.py:1039-1049` (`_changed_vs_origin`), plus a new
  `_merge_base(root)` beside it
- Test: `plugins/bitranox/hooks/tests/test_repo_gate.py` (append)

**Interfaces:**
- Produces: `_merge_base(root) -> str | None` (full sha of `git merge-base HEAD origin/master`,
  None when either ref is missing or git fails); `_changed_vs_origin(root)` keeps its signature
  and return type (`list[str] | None`).

**Out of scope:**
- `check_version_bumped` (repo-gate.py:415): it diffs `origin/master` directly and does not call
  `_changed_vs_origin`; its question ("is the version still origin's?") is about origin's tip on
  purpose.
- `_plugin_version_pair`: same reason.

**STOP conditions:**
- the function at line 1039 does not match the text quoted in Step 0;
- a caller other than `check_skill_review` (line 1219) and `check_cso` (line 1335) appears;
- an existing test turns red that relies on the tip comparison (read it before changing it: it
  may encode a case the merge-base view must also answer).

- [ ] **Step 0:** `grep -n "_changed_vs_origin" plugins/bitranox/hooks/*.py` lists exactly the
      definition and the two callers above.
- [ ] **Step 1: Write the failing test** (it drives the real function on a real repo):

```python
def test_changed_vs_origin_does_not_list_a_peer_s_pushed_path_as_ours(tmp_path):
    """A checkout BEHIND origin listed every path origin gained since as its own change.

    The checklist rule only survived that because reading the peer's missing file raised OSError
    and was skipped; the decision ledger check reads the shipped text and would refuse on it.
    """
    git_repo_with_origin(tmp_path, {"mine.md": "a\n", "theirs.md": "b\n"})
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True,
                          text=True, check=True).stdout.strip()
    (tmp_path / "theirs.md").write_text("b2\n", encoding="utf-8")
    subprocess.run(["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit",
                    "-qam", "peer", "--no-verify"], cwd=tmp_path, check=True)
    subprocess.run(["git", "update-ref", "refs/remotes/origin/master", "HEAD"], cwd=tmp_path, check=True)
    subprocess.run(["git", "reset", "-q", "--hard", base], cwd=tmp_path, check=True)
    (tmp_path / "mine.md").write_text("a2\n", encoding="utf-8")

    assert RG._changed_vs_origin(tmp_path) == ["mine.md"]


def test_merge_base_is_none_without_an_origin_ref(tmp_path):
    git_repo(tmp_path, {"x.md": "a\n"})
    assert RG._merge_base(tmp_path) is None
```

- [ ] **Step 2:** Run `CI-PYTEST -k "peer_s_pushed_path or merge_base_is_none"`.
      Expected: FAIL; the first lists `["mine.md", "theirs.md"]`, the second raises
      `AttributeError: ... '_merge_base'`.
- [ ] **Step 3: Implement:**

```python
def _merge_base(root):
    """The commit HEAD forked from origin/master, or None when either ref is missing."""
    rc, out, _ = _git(root, "merge-base", "HEAD", "origin/master")
    sha = out.strip()
    return sha if rc == 0 and sha else None


def _changed_vs_origin(root):
    """Worktree+index+untracked paths changed since HEAD forked from origin/master.

    The base is the merge-base, not origin's tip: diffed against the tip, a checkout that is
    behind lists every path origin gained since as its own change, and a check that reads those
    paths judges a peer's pushed work as this commit's.
    """
    base = _merge_base(root)
    if base is None:
        return None
    # `diff <base>` compares the WORKING TREE, so a staged change whose working copy was
    # reverted afterwards was missing - yet that staged text is exactly what the commit carries.
    _, changed = _git_paths(root, "diff", "--name-only", base)
    _, staged = _git_paths(root, "diff", "--cached", "--name-only", base)
    _, untracked = _git_paths(root, "ls-files", "--others", "--exclude-standard")
    return list(dict.fromkeys(changed + staged + untracked))
```

- [ ] **Step 4:** Run `CI-PYTEST`. Expected: all pass, the two new tests included.
- [ ] **Step 5: Mutation check:** put `"origin/master"` back as the diff base in a scratch copy
      (`mutation_arm` from compuse-toolbox, `--revert`), run the first test, require RED; restore.
- [ ] **Step 6: Commit** `repo-gate: changed-path checks diff from the merge-base, not origin's
      tip` with `-- plugins/bitranox/hooks/repo-gate.py plugins/bitranox/hooks/tests/test_repo_gate.py`.
      No version bump in this commit: the release task bumps once for the whole branch.

### Task 1.1 (M1.1): the ledger model and the matcher

**Files:**
- Create: `plugins/bitranox/hooks/skill_decisions.py`
- Create: `plugins/bitranox/hooks/tests/test_skill_decisions.py`

**Interfaces:**
- Produces (fixed names, M1.2 to M2.7 rely on them):
  - `LEDGER_REL = ".skillwriter/decisions.jsonl"`
  - `KINDS = ("rule", "removed", "rejected", "void")`, `TIERS = ("measured", "user", "argued",
    "inherited")`, `ORIGINS = ("authored", "imported", "baseline", "ab")`
  - `normalise(text: str) -> str`, `anchor_occurs(anchor: str, text: str) -> bool` (moved
    unchanged from the M0 harness, deviation D-1 included)
  - `ledger_path(skill_dir) -> Path`
  - `entry_id(entry: dict) -> str` (`d-<yyyymmdd>-<8 hex>`, sha256 over the canonical JSON of the
    entry without its `id`)
  - `validate_entry(entry: dict) -> list[str]` (one `<field>: <reason>` string per problem)
  - `class LedgerError(ValueError)` with `.line_no: int` and `.reason: str`

**Out of scope:**
- `.plan/skill-decisions/anchor_replay.py` (scratch harness, never shipped): copy its two
  functions, do not import it.
- `hooks/tell_chars.py`: used by M1.3, not changed.

**STOP conditions:**
- `hooks/skill_decisions.py` already exists;
- the conftest does not put `plugins/bitranox/hooks` on `sys.path` (conftest.py:14-17 today);
- a mutant of a normalise rule stays GREEN after Step 4.

- [ ] **Step 1: Write the failing tests:**

```python
"""Tests for skill_decisions: the per-skill decision ledger."""
import copy

import pytest

import skill_decisions as SD

LINE_SEPARATOR = chr(0x2028)  # built with chr(): a typed escape would land as the raw character


def _rule(**over):
    entry = {"v": 1, "date": "2026-11-05", "kind": "rule", "topic": "env-model",
             "decision": "bmk installs alone as a shared uv tool.",
             "why": "The per-project env was the inverse of what bmk 3.8.0 does.",
             "evidence": {"tier": "measured", "text": "bmk 3.8.0 release behaviour"},
             "reopen_if": "bmk changes its env model again.",
             "anchors": ["bmk alone, shared across projects"],
             "supersedes": [], "refs": [], "origin": "authored"}
    entry.update(over)
    entry["id"] = SD.entry_id(entry)
    return entry


# ---- matcher (the M0-measured rules) ----

def test_a_rewrap_and_a_repad_do_not_break_an_anchor():
    assert SD.anchor_occurs("Do **not** add `--with .` to the install line",
                            "Do **not** add\n   `--with .`   to the\ninstall line")


def test_a_blockquote_rewrap_does_not_break_an_anchor():
    assert SD.anchor_occurs("never restore the per-project env", "> never restore the\n> per-project env")
    assert SD.anchor_occurs("never restore the per-project env", ">never restore the\n>per-project env")


def test_an_anchor_spanning_two_list_items_survives_renumbering():
    anchor = "commit the plan. 2. push the plan"
    assert SD.anchor_occurs(anchor, "1. commit the plan.\n2. push the plan")
    assert SD.anchor_occurs(anchor, "3. commit the plan.\n4. push the plan")


def test_a_reworded_sentence_breaks_the_anchor():
    assert not SD.anchor_occurs("bmk installs as a persistent uv tool",
                                "bmk installs into a per-project .venv-bmk")


def test_unusual_line_separators_count_as_whitespace():
    assert SD.anchor_occurs("first half second half", "first half" + LINE_SEPARATOR + "second half")


def test_case_matters():
    assert not SD.anchor_occurs("Never push", "never push")


# ---- entry model ----

def test_a_complete_rule_entry_validates():
    assert SD.validate_entry(_rule()) == []


def test_the_id_is_the_date_plus_a_hash_of_the_whole_entry():
    a, b = _rule(), _rule(why="Another reason, same day.")
    assert a["id"].startswith("d-20261105-") and len(a["id"]) == len("d-20261105-") + 8
    assert a["id"] != b["id"]


def test_an_entry_edited_after_its_id_was_computed_is_refused():
    entry = _rule()
    entry["why"] = "rewritten in place"
    assert any(p.startswith("id:") for p in SD.validate_entry(entry))


@pytest.mark.parametrize("field", ["why", "reopen_if", "decision", "topic"])
def test_a_rule_without_a_mandatory_field_is_refused(field):
    entry = _rule(**{field: ""})
    assert any(p.startswith(field + ":") for p in SD.validate_entry(entry))


def test_a_void_entry_needs_why_and_a_target_but_no_reopen_if():
    void = _rule(kind="void", anchors=[], reopen_if="", supersedes=["d-20261101-0123abcd"])
    assert SD.validate_entry(void) == []
    no_target = _rule(kind="void", anchors=[], reopen_if="", supersedes=[])
    assert any(p.startswith("supersedes:") for p in SD.validate_entry(no_target))


def test_only_a_rule_carries_anchors_and_a_rule_needs_one():
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(anchors=[])))
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(kind="rejected")))


@pytest.mark.parametrize("anchor", ["too short to anchor", "x" * 201])
def test_an_anchor_outside_20_to_200_characters_is_refused(anchor):
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(anchors=[anchor])))


@pytest.mark.parametrize("control", [chr(0), chr(9), chr(0x7F)])
def test_an_anchor_holding_a_control_character_is_refused(control):
    anchor = "bmk alone," + control + " shared across projects"
    problems = SD.validate_entry(_rule(anchors=[anchor]))
    assert any(p.startswith("anchors: contains a control character") for p in problems)


def test_a_plain_anchor_raises_no_control_character_problem():
    assert not any("control" in p for p in SD.validate_entry(_rule()))


def test_the_length_is_measured_after_normalising():
    padded = "- - - - " + "a b c d e f g h i"    # long enough raw, too short once the markers go
    assert (len(padded), len(SD.normalise(padded))) == (25, 17)
    assert len(padded) >= SD.ANCHOR_MIN > len(SD.normalise(padded))
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(anchors=[padded])))


@pytest.mark.parametrize("field,value", [("kind", "note"), ("origin", "copied"),
                                         ("evidence", {"tier": "felt", "text": "x"}),
                                         ("evidence", {"tier": "argued", "text": ""}),
                                         ("topic", "Env Model")])
def test_a_value_outside_its_vocabulary_is_refused(field, value):
    assert any(p.startswith(field + ":") for p in SD.validate_entry(_rule(**{field: value})))


@pytest.mark.parametrize("date", ["2026-13-45", "2026-02-30"])
def test_a_date_that_is_not_on_the_calendar_is_refused(date):
    assert any(p.startswith("date:") for p in SD.validate_entry(_rule(date=date)))


def test_a_real_calendar_date_passes_the_date_check():
    assert not any(p.startswith("date:") for p in SD.validate_entry(_rule(date="2026-11-05")))


def test_an_unknown_field_is_refused_so_a_typo_cannot_hide_a_reason():
    entry = copy.deepcopy(_rule())
    entry["reopen-if"] = entry.pop("reopen_if")
    problems = SD.validate_entry(entry)
    assert any("reopen-if" in p for p in problems) and any(p.startswith("reopen_if:") for p in problems)
```

- [ ] **Step 2:** Run `CI-PYTEST -k skill_decisions`. Expected: collection ERROR,
      `ModuleNotFoundError: No module named 'skill_decisions'`.
- [ ] **Step 3: Implement** (module head; M1.2 and M1.3 extend the same file):

```python
#!/usr/bin/env python3
"""The per-skill decision ledger: what a skill decided, why, and what would reopen it.

Each skill keeps one append-only JSON Lines file at `<skill>/.skillwriter/decisions.jsonl`.
An entry records one decision about the skill's text: a `rule` the text states (bound to the
text by anchors, phrases that must keep occurring in the skill's Markdown), a `removed` rule, a
`rejected` alternative, or a `void` that withdraws an entry written in error. An entry is LIVE
while no later entry names it in `supersedes`.

The commit gate (`repo-gate.py`) refuses a change whose shipped text loses a live anchor, and
the SKILL.md edit guard hands an editing agent the skill's rejected and removed entries before
its first edit. Both read this module, so it is standard library only.

Decisions:
- Anchors are compared after `normalise`: per line, leading blockquote markers are stripped,
  every whitespace-separated marker-only token (a list marker, a stray ">") is dropped, and
  whitespace collapses.
  Why: measured 2026-11-05 on 91 window commits of three skills (the plan's PREREG): re-wrapping,
  re-padding and renumbering moved no anchor, and 3 meaning changes fired. Reopen if a refusal
  log shows rewordings outnumbering meaning changes over 30 days.
- The id hashes the whole entry, so two entries written the same day in two worktrees never
  collide, and an entry edited in place no longer matches its id.
"""
import datetime
import hashlib
import json
import re
from pathlib import Path

LEDGER_REL = ".skillwriter/decisions.jsonl"
KINDS = ("rule", "removed", "rejected", "void")
TIERS = ("measured", "user", "argued", "inherited")
ORIGINS = ("authored", "imported", "baseline", "ab")
FIELDS = ("v", "id", "date", "kind", "topic", "decision", "why", "evidence", "reopen_if",
          "anchors", "supersedes", "refs", "origin")
ANCHOR_MIN, ANCHOR_MAX = 20, 200

_ID = re.compile(r"d-[0-9]{8}-[0-9a-f]{8}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TOPIC = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
_QUOTE_MARKERS = re.compile(r"^(?:>[ \t]?)+")
# No separate line-start list-marker strip: a list marker is always followed by whitespace, so it
# is a whole token that _MARKER_TOKEN already drops, and a strip of it could never change the
# result.
_MARKER_TOKEN = re.compile(r"^(?:[-*+>]+|[0-9]+[.)])$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class LedgerError(ValueError):
    """A ledger line that is not a valid entry; `line_no` is 1-based."""

    def __init__(self, line_no, reason):
        super().__init__("line %d: %s" % (line_no, reason))
        self.line_no, self.reason = line_no, reason


def normalise(text):
    """One-space-separated words of `text`, without blockquote and list markers.

    Blockquote markers are stripped at line starts, where they may touch the first word
    (">word"); list markers and stray ">" are dropped as standalone tokens anywhere, on the anchor
    and the text alike: an anchor quoted across two list items carries the inner "2.", which only
    a token-level drop keeps stable under renumbering. Both sides lose the same tokens, so a match
    stays sound; prose dashes and "step 2." become invisible to it.
    """
    words = []
    for line in text.splitlines():
        line = _QUOTE_MARKERS.sub("", line.strip())
        words.extend(w for w in line.split() if not _MARKER_TOKEN.match(w))
    return " ".join(words)


def anchor_occurs(anchor, text):
    """True when `anchor` occurs in `text` after both are normalised (case-sensitive)."""
    return normalise(anchor) in normalise(text)


def ledger_path(skill_dir):
    return Path(skill_dir) / LEDGER_REL


def _canonical(entry):
    body = {k: v for k, v in entry.items() if k != "id"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def entry_id(entry):
    """`d-<yyyymmdd>-<first 8 hex of sha256 over the entry without its id>`."""
    digest = hashlib.sha256(_canonical(entry).encode("utf-8")).hexdigest()[:8]
    return "d-%s-%s" % (str(entry.get("date", "")).replace("-", ""), digest)


def _text(entry, field):
    value = entry.get(field)
    return value.strip() if isinstance(value, str) else ""


def _vocabulary_problems(entry):
    problems = []
    for field, allowed in (("kind", KINDS), ("origin", ORIGINS)):
        if entry.get(field) not in allowed:
            problems.append("%s: must be one of %s" % (field, ", ".join(allowed)))
    evidence = entry.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("tier") not in TIERS:
        problems.append("evidence: tier must be one of %s" % ", ".join(TIERS))
    elif not _text(evidence, "text"):
        problems.append("evidence: text is empty")
    if not _TOPIC.fullmatch(str(entry.get("topic", ""))):
        problems.append("topic: lowercase letters, digits and dashes, 1 to 40 characters")
    return problems


def _list_problems(entry):
    problems = []
    for field in ("anchors", "supersedes", "refs"):
        value = entry.get(field)
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            problems.append("%s: must be a list of strings" % field)
    supersedes = entry.get("supersedes") or []
    if any(not _ID.fullmatch(x) for x in supersedes if isinstance(x, str)):
        problems.append("supersedes: every item must be an entry id")
    if entry.get("kind") == "void" and not supersedes:
        problems.append("supersedes: a void entry names the entry it withdraws")
    return problems


def _anchor_problems(entry):
    anchors = entry.get("anchors") or []
    if entry.get("kind") != "rule":
        return ["anchors: only a rule entry carries anchors"] if anchors else []
    if not anchors:
        return ["anchors: a rule entry needs at least one"]
    texts = [a for a in anchors if isinstance(a, str)]
    problems = ["anchors: %d to %d characters after normalising: %r" % (ANCHOR_MIN, ANCHOR_MAX, a)
                for a in texts if not ANCHOR_MIN <= len(normalise(a)) <= ANCHOR_MAX]
    # A control character is no text a skill shows, and a NUL would let an anchor match across the
    # file separator corpus_text puts between two files.
    problems += ["anchors: contains a control character: %r" % a
                 for a in texts if _CONTROL.search(a)]
    return problems


def _date_problems(entry: dict) -> list[str]:
    date = str(entry.get("date", ""))
    if not _DATE.fullmatch(date):
        return ["date: YYYY-MM-DD"]
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        return ["date: not a calendar date"]
    return []


def validate_entry(entry):
    """Every problem with `entry`, one `<field>: <reason>` string each; [] when it is valid."""
    problems = ["%s: unknown field" % k for k in entry if k not in FIELDS]
    if entry.get("v") != 1:
        problems.append("v: must be 1")
    problems += _date_problems(entry)
    required = ("decision", "why") if entry.get("kind") == "void" else ("decision", "why", "reopen_if")
    problems += ["%s: empty" % f for f in required if not _text(entry, f)]
    problems += _vocabulary_problems(entry) + _list_problems(entry) + _anchor_problems(entry)
    if entry.get("id") != entry_id(entry):
        problems.append("id: does not match the entry (edited after it was written?)")
    return problems
```

- [ ] **Step 4:** Run `CI-PYTEST -k skill_decisions`. Expected: all pass.
- [ ] **Step 5: Mutation check:** with `mutation_arm --revert` (compuse-toolbox), remove in turn
      the `_QUOTE_MARKERS.sub`, the marker-token filter, the `entry_id` comparison, the
      `len(normalise(a))` length measure (as `len(a)`), and the `_CONTROL` anchor check; each must
      turn at least one test RED.
- [ ] **Step 6: Commit** `skill_decisions: the decision ledger model and anchor matcher` with
      `-- plugins/bitranox/hooks/skill_decisions.py plugins/bitranox/hooks/tests/test_skill_decisions.py`.

### Task 1.2 (M1.2): reading a ledger: parse, live entries, check, brief

**Files:**
- Modify: `plugins/bitranox/hooks/skill_decisions.py`
- Test: `plugins/bitranox/hooks/tests/test_skill_decisions.py` (append)

**Interfaces:**
- Consumes: M1.1.
- Produces:
  - `file_lines(path) -> Iterator[bytes]` (nothing for a missing file; bytes, so a line that is
    not UTF-8 is a `LedgerError` from `parse_entries`)
  - `parse_entries(lines: Iterable[str | bytes]) -> Iterator[dict]` (raises `LedgerError`)
  - `live_entries(lines_factory: Callable[[], Iterable]) -> Iterator[dict]` (two passes; `void`
    entries are never live)
  - `corpus_text(files: Mapping[str, bytes]) -> str` (the skill's `*.md` outside `.skillwriter/`
    and `tests/`, joined so no anchor can span two files)
  - `corpus_from_dir(skill_dir) -> str` (tracked files via `git ls-files -z`, every `GIT_*`
    variable stripped; the directory walk when git cannot answer)
  - `@dataclass(frozen=True) class Finding: entry_id, problem, anchor="", decision="", why="",
    reopen_if=""` with `render() -> str`
  - `check_ledger(lines_factory, corpus: str) -> list[Finding]`
  - `render_brief(lines_factory, *, skill: str, budget_chars: int = 6000) -> str` ("" when the
    skill has no live rejected or removed entry)

**Out of scope:** the CLI (M1.3); any writing.

**STOP conditions:**
- the peak-memory test in Step 1 cannot separate the two sizes (the per-entry text is held);
- `git ls-files -z` cannot be run from a skill dir with `cwd=` (then the gate must pass files in).

- [ ] **Step 1: Write the failing tests** (append):

```python
import json
import subprocess
import tracemalloc


def _lines(*entries):
    return [json.dumps(e) + "\n" for e in entries]


def _factory(*entries):
    data = _lines(*entries)
    return lambda: iter(data)


def _rejected(**over):
    return _rule(kind="rejected", anchors=[], topic="per-project-env",
                 decision="Install bmk per project.", **over)


def test_parse_reports_the_line_number_of_a_bad_line():
    with pytest.raises(SD.LedgerError) as err:
        list(SD.parse_entries(_lines(_rule()) + ["{not json\n"]))
    assert err.value.line_no == 2


def test_blank_lines_are_skipped():
    assert len(list(SD.parse_entries(["\n"] + _lines(_rule()) + ["  \n"]))) == 1


def test_a_ledger_file_that_is_not_utf8_is_a_ledger_error_naming_the_line(tmp_path):
    path = tmp_path / "decisions.jsonl"
    path.write_bytes(json.dumps(_rule()).encode("utf-8") + b"\n" + b"\xff\xfe\n")
    with pytest.raises(SD.LedgerError) as err:
        list(SD.parse_entries(SD.file_lines(path)))
    assert err.value.line_no == 2
    [finding] = SD.check_ledger(lambda: SD.file_lines(path), "bmk alone, shared across projects")
    assert finding.problem.startswith("line 2: ")


def test_a_raw_line_separator_inside_a_json_string_stays_one_ledger_line(tmp_path):
    entry = _rejected(why="first half" + LINE_SEPARATOR + "second half")
    path = tmp_path / "decisions.jsonl"
    path.write_bytes((json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8"))
    assert [e["id"] for e in SD.parse_entries(SD.file_lines(path))] == [entry["id"]]


def test_a_superseded_entry_and_a_void_are_not_live():
    old = _rule()
    new = _rule(decision="bmk installs alone, reworded.", supersedes=[old["id"]])
    void = _rule(kind="void", anchors=[], reopen_if="", supersedes=[new["id"]],
                 why="written against the wrong skill")
    assert [e["id"] for e in SD.live_entries(_factory(old, new))] == [new["id"]]
    assert list(SD.live_entries(_factory(old, new, void))) == []


def test_check_passes_while_every_live_anchor_occurs():
    corpus = "Intro.\n\nbmk alone,\nshared across projects.\n"
    assert SD.check_ledger(_factory(_rule()), corpus) == []


def test_check_names_the_entry_and_its_reason_when_an_anchor_is_gone():
    entry = _rule()
    [finding] = SD.check_ledger(_factory(entry), "bmk installs per project now.\n")
    assert (finding.entry_id, finding.anchor) == (entry["id"], "bmk alone, shared across projects")
    assert entry["why"] in finding.render() and entry["reopen_if"] in finding.render()


def test_a_superseded_rule_s_anchor_may_go():
    old = _rule()
    new = _rule(decision="per-project env again", anchors=["each project gets its own bmk env"],
                supersedes=[old["id"]])
    assert SD.check_ledger(_factory(old, new), "Now each project gets its own bmk env.\n") == []


def test_check_reports_a_duplicate_id_and_an_unknown_supersede_target():
    entry = _rule()
    stray = _rule(decision="x", supersedes=["d-20990101-deadbeef"])
    problems = [f.problem for f in SD.check_ledger(_factory(entry, entry, stray), "bmk alone, shared across projects")]
    assert any("duplicate" in p for p in problems) and any("unknown" in p for p in problems)


def test_check_turns_a_parse_error_into_one_finding():
    [finding] = SD.check_ledger(lambda: iter(["{broken\n"]), "")
    assert "line 1" in finding.problem


def test_the_corpus_is_the_markdown_outside_skillwriter_and_tests():
    files = {"SKILL.md": b"keep one", "references/x.md": b"keep two",
             ".skillwriter/checklist-1.md": b"drop one", "tests/fixture.md": b"drop two",
             "scripts/x.py": b"drop three"}
    text = SD.corpus_text(files)
    assert "keep one" in text and "keep two" in text and "drop" not in text


def test_an_anchor_cannot_span_two_files():
    files = {"SKILL.md": b"the end of one file", "references/x.md": b"start of another"}
    assert not SD.anchor_occurs("one file start of another", SD.corpus_text(files))


def test_corpus_from_dir_reads_tracked_markdown_only(tmp_path):
    (tmp_path / "SKILL.md").write_text("tracked text\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("untracked text\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "SKILL.md"], cwd=tmp_path, check=True)
    text = SD.corpus_from_dir(tmp_path)
    assert "tracked text" in text and "untracked text" not in text


def test_the_brief_lists_rejected_and_removed_in_full_and_counts_the_rest():
    entries = [_rejected(why="reason %d " % i + "x" * 300) for i in range(30)]
    brief = SD.render_brief(_factory(*entries), skill="devops-bmk", budget_chars=2000)
    assert "reason 0" in brief and len(brief) < 2600
    assert "more not shown" in brief and "skill_decisions.py show devops-bmk" in brief


def test_the_brief_stops_at_the_first_block_that_does_not_fit():
    a, b, c = _rejected(why="why A"), _rejected(why="why B " + "x" * 300), _rejected(why="why C")
    budget = 300
    # Precondition: A and C together fit, so only a strict oldest-first prefix leaves C out.
    assert len(SD._brief_block(a)) + len(SD._brief_block(c)) <= budget < len(SD._brief_block(b))
    brief = SD.render_brief(_factory(a, b, c), skill="devops-bmk", budget_chars=budget)
    assert "why A" in brief and "why B" not in brief and "why C" not in brief
    assert "2 more not shown" in brief


def test_a_first_block_over_the_budget_still_gives_a_brief():
    brief = SD.render_brief(_factory(_rejected()), skill="devops-bmk", budget_chars=10)
    assert brief.startswith("Decisions already taken for devops-bmk")
    assert "1 more not shown" in brief and "skill_decisions.py show devops-bmk" in brief


def test_the_brief_is_empty_when_nothing_was_rejected_or_removed():
    assert SD.render_brief(_factory(_rule()), skill="devops-bmk") == ""


def test_file_lines_of_a_missing_ledger_is_empty(tmp_path):
    assert list(SD.file_lines(tmp_path / "absent.jsonl")) == []


def _peak(tmp_path, n):
    path = tmp_path / ("ledger-%d.jsonl" % n)
    with path.open("w", encoding="utf-8") as fh:
        for i in range(n):
            fh.write(json.dumps(_rejected(why="r%d " % i + "w" * 1000)) + "\n")
    tracemalloc.start()
    SD.check_ledger(lambda: SD.file_lines(path), "corpus")
    SD.render_brief(lambda: SD.file_lines(path), skill="s")
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return peak


def test_peak_memory_does_not_hold_the_entries(tmp_path):
    """19,000 more entries of 1 KB each would add about 19 MB if their text were held; the id
    sets the check keeps add about 100 to 150 bytes per entry (about 3 MB), so 8 MB separates the
    two outcomes with room on both sides."""
    small, large = _peak(tmp_path, 1000), _peak(tmp_path, 20000)
    assert large - small < 8_000_000
```

- [ ] **Step 2:** Run `CI-PYTEST -k skill_decisions`. Expected: FAIL with
      `AttributeError: module 'skill_decisions' has no attribute 'parse_entries'` (and the others).
- [ ] **Step 3: Implement** (append to `skill_decisions.py`; add `import os`, `import subprocess`,
      `from dataclasses import dataclass` to the imports):

```python
_CORPUS_SEP = "\n\x00\n"   # a NUL token: no anchor can match across two files
_CORPUS_SKIP = (".skillwriter/", "tests/")


def file_lines(path):
    """The lines of `path` as bytes, read one at a time; nothing for a missing file.

    Bytes, so `parse_entries` decodes each line inside its per-line check: a line that is not
    UTF-8 becomes a `LedgerError` naming it, never a UnicodeDecodeError raised by the read.
    """
    path = Path(path)
    if not path.is_file():
        return
    # Iterating a binary file splits on b"\n" only; str.splitlines would also split a JSON string
    # holding a raw U+2028.
    with path.open("rb") as fh:
        yield from fh


def parse_entries(lines):
    """Yield each entry of `lines` (str or bytes), validated; blank lines are skipped.

    Raises:
        LedgerError: at the first line that is not UTF-8, not a JSON object, or not a valid entry.
    """
    for line_no, raw in enumerate(lines, 1):
        try:
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        except UnicodeDecodeError:
            raise LedgerError(line_no, "not UTF-8") from None
        if not text.strip():
            continue
        try:
            entry = json.loads(text)
        except ValueError as exc:
            raise LedgerError(line_no, "not JSON (%s)" % exc) from None
        if not isinstance(entry, dict):
            raise LedgerError(line_no, "not a JSON object")
        problems = validate_entry(entry)
        if problems:
            raise LedgerError(line_no, "; ".join(problems))
        yield entry


def live_entries(lines_factory):
    """Entries no later entry supersedes, voids excluded. Two passes over `lines_factory()`."""
    superseded = set()
    for entry in parse_entries(lines_factory()):
        superseded.update(entry["supersedes"])
    for entry in parse_entries(lines_factory()):
        if entry["id"] not in superseded and entry["kind"] != "void":
            yield entry


def corpus_text(files):
    """The skill's Markdown a rule anchor must occur in: `*.md` outside `.skillwriter/`, `tests/`."""
    parts = [data.decode("utf-8", errors="replace") for rel, data in sorted(files.items())
             if rel.endswith(".md") and not rel.startswith(_CORPUS_SKIP)]
    return _CORPUS_SEP.join(parts)


def _git_env():
    # A GIT_DIR or pathspec variable inherited from a hook would point git at another repo.
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def corpus_from_dir(skill_dir):
    """`corpus_text` of the files git tracks under `skill_dir`; every file there without git."""
    skill_dir = Path(skill_dir)
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--", "."], cwd=str(skill_dir),
                             capture_output=True, env=_git_env(), check=False)
        listed = out.stdout.decode("utf-8").split("\0") if out.returncode == 0 else None
    except OSError:
        listed = None
    if listed is None:
        listed = [p.relative_to(skill_dir).as_posix() for p in skill_dir.rglob("*") if p.is_file()]
    files = {}
    for rel in filter(None, listed):
        try:
            files[rel] = (skill_dir / rel).read_bytes()
        except OSError:
            continue        # listed but gone from disk: a deletion this corpus does not hold
    return corpus_text(files)


@dataclass(frozen=True)
class Finding:
    entry_id: str
    problem: str
    anchor: str = ""
    decision: str = ""
    why: str = ""
    reopen_if: str = ""

    def render(self):
        if not self.anchor:
            return "%s: %s" % (self.entry_id or "ledger", self.problem)
        return ("%s: %s %r\n  decision: %s\n  why: %s\n  reopen if: %s"
                % (self.entry_id, self.problem, self.anchor, self.decision, self.why, self.reopen_if))


def _integrity_findings(lines_factory):
    findings, seen = [], set()
    for entry in parse_entries(lines_factory()):
        if entry["id"] in seen:
            findings.append(Finding(entry["id"], "duplicate id"))
        unknown = [s for s in entry["supersedes"] if s not in seen]
        if unknown:
            findings.append(Finding(entry["id"], "supersedes unknown or later id %s" % ", ".join(unknown)))
        seen.add(entry["id"])
    return findings


def check_ledger(lines_factory, corpus):
    """Findings for a ledger against its skill's text: integrity first, then every live anchor."""
    try:
        findings = _integrity_findings(lines_factory)
        text = normalise(corpus)
        for entry in live_entries(lines_factory):
            for anchor in entry["anchors"]:
                # anchor_occurs, with the corpus normalised once: keep the two tests identical.
                if normalise(anchor) not in text:
                    findings.append(Finding(entry["id"], "anchor no longer in the skill text:", anchor,
                                            entry["decision"], entry["why"], entry["reopen_if"]))
    except LedgerError as exc:
        return [Finding("", str(exc))]
    return findings


def _brief_block(entry):
    return ("- [%s] %s (%s, %s)\n  why: %s\n  reopen if: %s"
            % (entry["kind"], entry["decision"], entry["id"], entry["evidence"]["tier"],
               entry["why"], entry["reopen_if"]))


def render_brief(lines_factory, *, skill, budget_chars=6000):
    """The live rejected and removed entries, in full until `budget_chars` is spent, then a count."""
    blocks, used, left = [], 0, 0
    for entry in live_entries(lines_factory):
        if entry["kind"] not in ("rejected", "removed"):
            continue
        block = None if left else _brief_block(entry)
        # A strict oldest-first prefix: once one block does not fit, every later entry is counted,
        # a shorter one too, so the brief never shows a newer decision while hiding an older one.
        if block is None or used + len(block) > budget_chars:
            left += 1
            continue
        blocks.append(block)
        used += len(block)
    if not blocks and not left:
        return ""
    text = "Decisions already taken for %s (rejected or removed, oldest first):\n" % skill + "\n".join(blocks)
    if left:
        text += ("\n%d more not shown: python3 <plugin>/hooks/skill_decisions.py show %s "
                 "--kind rejected,removed --full" % (left, skill))
    return text
```

- [ ] **Step 4:** Run `CI-PYTEST -k skill_decisions`. Expected: all pass.
- [ ] **Step 5: Mutation check** (`mutation_arm --revert`): drop the `supersedes` filter in
      `live_entries`; drop `_CORPUS_SKIP`; replace `_CORPUS_SEP` with `"\n"`; make
      `render_brief` ignore the budget; let `render_brief` keep scanning past the first block that
      does not fit; open the file in text mode in `file_lines`. Each must turn a test RED.
- [ ] **Step 6: Commit** `skill_decisions: read, check and brief a ledger` with the two paths.

### Task 1.3 (M1.3): writing entries, and the CLI

**Files:**
- Modify: `plugins/bitranox/hooks/skill_decisions.py`
- Modify: `.gitattributes` (one line)
- Test: `plugins/bitranox/hooks/tests/test_skill_decisions.py` (append)

**Interfaces:**
- Consumes: M1.1, M1.2, `tell_chars.find_tell_codepoints(text) -> list[str]`.
- Produces:
  - `class EntryRefused(ValueError)` with `.problems: list[str]`
  - `append_entries(skill_dir, entries: list[dict], *, today: str | None = None) -> list[str]`
    (assigns `v`, `date`, `id`; validates; refuses tells; requires each new anchor to occur
    EXACTLY once in `corpus_from_dir(skill_dir)`; refuses a duplicate id and a `supersedes`
    naming an id the ledger does not hold; writes all or nothing; returns the new ids). The CLI
    calls it once per skill, so a file naming two skills is all or nothing PER SKILL, and the
    `--json` envelope lists what was written before a refusal.
  - `main(argv: list[str] | None = None) -> int` with the verbs below

CLI contract (every verb; `--json` puts `{ok, command, data, skipped}` on stdout; diagnostics go
to stderr; exit 0 yes, 1 findings or refused, 2 could not run; no tracebacks):

```
skill_decisions.py add   --from-file ENTRIES.json [--skills-dir DIR] [--json]
skill_decisions.py show  SKILL [--skill-dir DIR] [--kind K[,K]] [--topic T] [--id ID] [--all] [--full] [--json]
skill_decisions.py check [SKILL ...] [--skills-dir DIR] [--json]
```

- `ENTRIES.json` holds one object or a list; each object names its `skill` (removed before the
  entry is stored). Without `--skills-dir`, `add` and `check` use
  `<git top of the cwd>/plugins/bitranox/skills` and exit 2 naming `--skills-dir` when there is
  none: a write must never land in an installed plugin copy.
- `show` without `--skill-dir` uses the same repo dir, else the skills dir of the plugin this
  script ships in (read-only, so an install can read its own declined list).

**Out of scope:** the gate and the guard (M2); `contrib_queue.py`; any seeding (M3).

**STOP conditions:**
- `tell_chars.find_tell_codepoints` does not exist or has another signature;
- `.gitattributes` already has a rule for `decisions.jsonl`.

- [ ] **Step 1: Write the failing tests** (append; `_skill` builds a real tracked skill dir):

```python
def _skill(tmp_path, text="Intro.\n\nbmk alone, shared across projects.\n"):
    repo = tmp_path / "repo"
    skill = repo / "plugins" / "bitranox" / "skills" / "devops-bmk"
    (skill / ".skillwriter").mkdir(parents=True)
    (skill / "SKILL.md").write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    return repo, skill


def _draft(**over):
    entry = {k: v for k, v in _rule().items() if k not in ("id", "date", "v")}
    entry.update(over)
    return entry


def test_append_assigns_id_and_date_and_writes_one_line(tmp_path):
    _repo, skill = _skill(tmp_path)
    [new_id] = SD.append_entries(skill, [_draft()], today="2026-11-06")
    [stored] = list(SD.parse_entries(SD.file_lines(SD.ledger_path(skill))))
    assert stored["id"] == new_id and new_id.startswith("d-20261106-")


def test_an_anchor_that_occurs_twice_is_refused(tmp_path):
    _repo, skill = _skill(tmp_path, "bmk alone, shared across projects.\n" * 2)
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft()], today="2026-11-06")
    assert any("exactly once" in p for p in err.value.problems)
    assert not SD.ledger_path(skill).exists()


def test_an_anchor_absent_from_the_text_is_refused(tmp_path):
    _repo, skill = _skill(tmp_path, "something else entirely\n")
    with pytest.raises(SD.EntryRefused):
        SD.append_entries(skill, [_draft()], today="2026-11-06")


def test_a_batch_is_all_or_nothing(tmp_path):
    _repo, skill = _skill(tmp_path)
    with pytest.raises(SD.EntryRefused):
        SD.append_entries(skill, [_draft(), _draft(why="")], today="2026-11-06")
    assert list(SD.file_lines(SD.ledger_path(skill))) == []


def test_a_typographic_tell_is_refused(tmp_path):
    _repo, skill = _skill(tmp_path)
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft(why="because" + chr(0x2014) + "it broke")], today="2026-11-06")
    assert any(p.startswith("entry 1: why:") for p in err.value.problems)


def test_supersedes_must_name_a_recorded_id(tmp_path):
    _repo, skill = _skill(tmp_path, "bmk alone, shared across projects. Then run make test first.\n")
    [first] = SD.append_entries(skill, [_draft()], today="2026-11-06")
    stray = _draft(decision="gate first", anchors=["Then run make test first."],
                   supersedes=["d-20990101-deadbeef"])
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [stray], today="2026-11-06")
    assert any(p.startswith("entry 1: supersedes:") for p in err.value.problems)
    stray["supersedes"] = [first]
    assert len(SD.append_entries(skill, [stray], today="2026-11-06")) == 1


def test_show_all_includes_superseded_entries(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path, "bmk alone, shared across projects. Then run make test first.\n")
    [first] = SD.append_entries(skill, [_draft()], today="2026-11-06")
    SD.append_entries(skill, [_draft(decision="gate first", anchors=["Then run make test first."],
                                     supersedes=[first])], today="2026-11-06")
    monkeypatch.chdir(repo)
    _rc, live, _ = _cli(capsys, "show", "devops-bmk", "--json")
    _rc, every, _ = _cli(capsys, "show", "devops-bmk", "--all", "--json")
    assert len(json.loads(live)["data"]["entries"]) == 1
    assert len(json.loads(every)["data"]["entries"]) == 2


def _cli(capsys, *argv):
    rc = SD.main(list(argv))
    out = capsys.readouterr()
    return rc, out.out, out.err


def test_cli_add_show_check_round_trip(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path)
    src = tmp_path / "entries.json"
    src.write_text(json.dumps([dict(_draft(), skill="devops-bmk")]), encoding="utf-8")
    monkeypatch.chdir(repo)
    rc, out, _ = _cli(capsys, "add", "--from-file", str(src), "--json")
    assert rc == 0 and json.loads(out)["ok"] is True
    rc, out, _ = _cli(capsys, "show", "devops-bmk")
    assert rc == 0 and "env-model" in out
    rc, _, _ = _cli(capsys, "check", "devops-bmk")
    assert rc == 0
    (skill / "SKILL.md").write_text("bmk installs per project now.\n", encoding="utf-8")
    rc, out, _ = _cli(capsys, "check", "devops-bmk", "--json")
    assert rc == 1 and json.loads(out)["data"]["findings"]


def test_cli_add_outside_a_repo_exits_2_naming_the_flag(tmp_path, capsys, monkeypatch):
    src = tmp_path / "entries.json"
    src.write_text(json.dumps(dict(_draft(), skill="devops-bmk")), encoding="utf-8")
    monkeypatch.chdir(tmp_path)        # pytest's tmp dir is in no repo holding plugins/bitranox/skills
    rc, out, err = _cli(capsys, "add", "--from-file", str(src))
    assert rc == 2 and "--skills-dir" in err and "Traceback" not in err


def test_cli_json_mode_still_prints_json_on_a_run_error(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc, out, _ = _cli(capsys, "add", "--from-file", str(tmp_path / "missing.json"), "--json")
    assert rc == 2 and json.loads(out)["ok"] is False
```

- [ ] **Step 2:** Run `CI-PYTEST -k skill_decisions`. Expected: FAIL on the missing
      `append_entries`, `EntryRefused` and `main`.
- [ ] **Step 3: Implement** (append; add `import argparse`, `import datetime`, `import sys`):

```python
class EntryRefused(ValueError):
    """`append_entries` wrote nothing; `problems` says why, one line each."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


def _tell_problems(entry):
    import tell_chars  # noqa: PLC0415 - sibling hook module; keeps the reading half importable alone
    problems = []
    for field in ("decision", "why", "reopen_if", "topic"):
        if tell_chars.find_tell_codepoints(_text(entry, field)):
            problems.append("%s: typographic tell (use ASCII punctuation)" % field)
    evidence = entry.get("evidence") or {}
    if isinstance(evidence, dict) and tell_chars.find_tell_codepoints(_text(evidence, "text")):
        problems.append("evidence: typographic tell (use ASCII punctuation)")
    return problems


def _anchor_count_problems(entry, normalised_corpus):
    problems = []
    for anchor in entry.get("anchors") or []:
        hits = normalised_corpus.count(normalise(anchor))
        if hits != 1:
            problems.append("anchors: must occur exactly once in the skill text, found %d: %r"
                            % (hits, anchor))
    return problems


def append_entries(skill_dir, entries, *, today=None):
    """Validate and append `entries` to the skill's ledger, all or nothing; return their ids."""
    today = today or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    path = ledger_path(skill_dir)
    known = {e["id"] for e in parse_entries(file_lines(path))}
    corpus = normalise(corpus_from_dir(skill_dir))
    problems, lines, ids = [], [], []
    for n, draft in enumerate(entries, 1):
        entry = dict(draft, v=1, date=draft.get("date") or today)
        entry["id"] = entry_id(entry)
        found = validate_entry(entry) + _tell_problems(entry) + _anchor_count_problems(entry, corpus)
        if entry["id"] in known:
            found.append("id: an identical entry is already in the ledger")
        found += ["supersedes: unknown id %s" % s for s in entry.get("supersedes") or []
                  if s not in known]
        problems += ["entry %d: %s" % (n, p) for p in found]
        known.add(entry["id"])
        ids.append(entry["id"])
        lines.append(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    if problems:
        raise EntryRefused(problems)
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = "\n" if _ends_without_newline(path) else ""
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write(prefix + "".join(lines))
    return ids


def _ends_without_newline(path):
    """True when a non-empty `path` lacks a final newline; reads one byte, not the ledger."""
    if not path.is_file() or path.stat().st_size == 0:
        return False
    with path.open("rb") as fh:
        fh.seek(-1, 2)
        return fh.read(1) != b"\n"
```

  CLI (the same file):

```python
def _repo_skills_dir():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             encoding="utf-8", errors="replace", env=_git_env(), check=False)
    except OSError:
        return None
    candidate = Path(out.stdout.strip()) / "plugins" / "bitranox" / "skills"
    return candidate if out.returncode == 0 and candidate.is_dir() else None


class _RunError(Exception):
    """The verb could not run (exit 2)."""


def _skills_dir(arg):
    found = Path(arg) if arg else _repo_skills_dir()
    if found is None or not found.is_dir():
        raise _RunError("no skills dir: run inside the marketplace repo or pass --skills-dir")
    return found


def _cmd_add(args):
    try:
        raw = json.loads(Path(args.from_file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _RunError("cannot read %s: %s" % (args.from_file, exc)) from None
    drafts = raw if isinstance(raw, list) else [raw]
    root, written = _skills_dir(args.skills_dir), {}
    by_skill = {}
    for draft in drafts:
        skill = draft.pop("skill", None) if isinstance(draft, dict) else None
        if not skill or not (root / skill).is_dir():
            raise _RunError("every entry names an existing skill in 'skill': %r" % skill)
        by_skill.setdefault(skill, []).append(draft)
    try:
        for skill, batch in by_skill.items():
            written[skill] = append_entries(root / skill, batch)
    except EntryRefused as exc:
        return 1, {"written": written, "refused": exc.problems}
    return 0, {"written": written}


def _show_dir(args):
    if args.skill_dir:
        return Path(args.skill_dir)
    root = _repo_skills_dir() or Path(__file__).resolve().parents[1] / "skills"
    return root / args.skill


def _cmd_show(args):
    skill_dir = _show_dir(args)
    path = ledger_path(skill_dir)
    # parse_entries takes an ITERABLE of lines, live_entries a FACTORY it calls once per pass.
    entries = parse_entries(file_lines(path)) if args.all else live_entries(lambda: file_lines(path))
    kinds = set(args.kind.split(",")) if args.kind else set(KINDS)
    shown = []
    for entry in entries:
        if entry["kind"] in kinds and (not args.topic or entry["topic"] == args.topic) \
                and (not args.id or entry["id"] == args.id):
            shown.append(entry if args.full else {k: entry[k] for k in ("id", "kind", "topic", "decision")})
    return 0, {"skill": skill_dir.name, "entries": shown}


def _cmd_check(args):
    root = _skills_dir(args.skills_dir)
    names = args.skills or sorted(p.parent.parent.name for p in root.glob("*/" + LEDGER_REL))
    findings = []
    for name in names:
        path = ledger_path(root / name)
        for f in check_ledger(lambda p=path: file_lines(p), corpus_from_dir(root / name)):
            findings.append({"skill": name, "text": f.render()})
    return (1 if findings else 0), {"checked": names, "findings": findings}


def _parser():
    parser = argparse.ArgumentParser(prog="skill_decisions.py", description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="print a JSON envelope")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="append entries from a JSON file")
    add.add_argument("--from-file", required=True)
    add.add_argument("--skills-dir")
    show = sub.add_parser("show", help="list a skill's decisions")
    show.add_argument("skill")
    show.add_argument("--skill-dir")
    show.add_argument("--kind")
    show.add_argument("--topic")
    show.add_argument("--id")
    show.add_argument("--all", action="store_true", help="include superseded and void entries")
    show.add_argument("--full", action="store_true", help="every field, not one line each")
    check = sub.add_parser("check", help="check ledgers against their skill text")
    check.add_argument("skills", nargs="*")
    check.add_argument("--skills-dir")
    for p in (add, show, check):
        p.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    return parser


def _print_text(command, data):
    if command == "show":
        for e in data["entries"]:
            print(json.dumps(e, ensure_ascii=False) if "why" in e else
                  "%s  %-8s %-24s %s" % (e["id"], e["kind"], e["topic"], e["decision"]))
    elif command == "check":
        for f in data["findings"]:
            print("%s: %s" % (f["skill"], f["text"]))
        print("checked %d ledger(s), %d finding(s)" % (len(data["checked"]), len(data["findings"])))
    else:
        for skill, ids in data.get("written", {}).items():
            print("%s: %s" % (skill, ", ".join(ids)))
        for problem in data.get("refused", []):
            print("refused: " + problem, file=sys.stderr)


def main(argv=None):
    args = _parser().parse_args(argv)
    verbs = {"add": _cmd_add, "show": _cmd_show, "check": _cmd_check}
    try:
        rc, data = verbs[args.command](args)
    except (_RunError, LedgerError, OSError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "command": args.command, "data": {"error": str(exc)},
                              "skipped": []}))
        print("skill_decisions.py %s: %s" % (args.command, exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"ok": rc == 0, "command": args.command, "data": data, "skipped": []},
                         ensure_ascii=False))
    else:
        _print_text(args.command, data)
    return rc


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4:** Add to `.gitattributes`, below the existing `*.jsonl` fixture rule:
      `plugins/bitranox/skills/*/.skillwriter/decisions.jsonl text eol=lf merge=union`
      (union: two branches appending to one ledger merge by keeping both sides' lines).
- [ ] **Step 5:** Run `CI-PYTEST`. Expected: all pass.
- [ ] **Step 6:** Run the CLI by hand on a scratch copy of a real skill:
      `cp -a plugins/bitranox/skills/devops-bmk <scratchpad>/m1/devops-bmk` inside a scratch git
      repo laid out as `plugins/bitranox/skills/`, then `add` one rule entry quoting a real
      sentence, `show`, `check`, delete that sentence, `check` again (exit 1, the entry's why and
      reopen_if printed). Paste the four outputs into the task's review notes.
- [ ] **Step 7: Commit** `skill_decisions: add/show/check CLI and union merge for ledgers` with
      `-- plugins/bitranox/hooks/skill_decisions.py plugins/bitranox/hooks/tests/test_skill_decisions.py .gitattributes`.

### Task 2.2 (M2.2): the commit and push gate checks ledgers

**Files:**
- Modify: `plugins/bitranox/hooks/repo-gate.py`: `_LF_SUFFIXES` (line 219), `shipped_files`
  (1601), `_selected_files` (1582), `_working_tree_files` (1451), `run_checks` (2687), new
  `check_skill_decisions` and `check_all_skill_decisions` placed after `check_skill_review`
- Test: `plugins/bitranox/hooks/tests/test_repo_gate.py` (append)

**Interfaces:**
- Consumes: `skill_decisions` (M1), `_merge_base` and `_changed_vs_origin` (M2.1),
  `_checked_out_bytes`, `STAGE_INDEX`, `STAGE_HEAD`, `CommitSelection`.
- Produces:
  - `shipped_files(skill_dir, stage, *, ignore=_mirror_ignored)` and the same keyword on
    `_selected_files` and `_working_tree_files`; every existing caller keeps its behaviour
  - `check_skill_decisions(root, stage=STAGE_INDEX, *, log=None) -> list[str]`
  - `check_all_skill_decisions(root) -> list[str]`
  - `log` receives one dict per refusal: `{"time", "skill", "entry_id", "problem"}`; the default
    appends it to `self_improve_signals._audit_dir() / "skill-decision-gate.jsonl"` and swallows
    any `OSError`

**Out of scope:**
- The mirror gate's own reading (`MIRROR_IGNORED_DIRS` stays as it is: the ledger must never
  count as drift between twins).
- `check_version_bumped`.

**STOP conditions:**
- an existing `shipped_files` caller passes a positional third argument;
- making `.jsonl` an LF-checked suffix turns a tracked file red (Step 0 lists them first);
- a deleted skill directory makes `shipped_files` raise rather than return `{}`.

- [ ] **Step 0:** `git ls-files '*.jsonl'` and `git ls-files --eol '*.jsonl'`: every listed
      file shows `i/lf`. If one does not, STOP.
- [ ] **Step 1: Write the failing tests.** They drive the gate on real repos built by a helper
      that commits a skill with a ledger and sets `origin/master` to that commit:

```python
import skill_decisions as SD

SKILL = "plugins/bitranox/skills/devops-bmk"
RULE_TEXT = "Intro.\n\nbmk alone, shared across projects.\n"


def _ledger_line(text_anchor="bmk alone, shared across projects", **over):
    entry = {"v": 1, "date": "2026-11-05", "kind": "rule", "topic": "env-model",
             "decision": "bmk installs alone.", "why": "Measured on bmk 3.8.0.",
             "evidence": {"tier": "measured", "text": "release notes"},
             "reopen_if": "bmk changes its env model.", "anchors": [text_anchor],
             "supersedes": [], "refs": [], "origin": "authored"}
    entry.update(over)
    entry["id"] = SD.entry_id(entry)
    return json.dumps(entry) + "\n", entry


def _ledger_repo(tmp_path, ledger_lines):
    files = {SKILL + "/SKILL.md": RULE_TEXT,
             SKILL + "/.skillwriter/decisions.jsonl": "".join(ledger_lines)}
    return git_repo_with_origin(tmp_path, files)


def _stage(root, rel, text):
    write(root / rel, text)
    subprocess.run(["git", "add", rel], cwd=root, check=True)


def test_a_staged_change_that_drops_a_live_anchor_is_refused_with_the_reason(tmp_path):
    line, entry = _ledger_line()
    root = _ledger_repo(tmp_path, [line])
    _stage(root, SKILL + "/SKILL.md", "Intro.\n\nbmk installs per project now.\n")
    logged = []
    fails = RG.check_skill_decisions(root, RG.STAGE_INDEX, log=logged.append)
    assert len(fails) == 1 and entry["id"] in fails[0] and entry["why"] in fails[0]
    assert "skill_decisions.py add" in fails[0]
    assert [r["entry_id"] for r in logged] == [entry["id"]]


def test_a_superseding_entry_staged_with_the_change_passes(tmp_path):
    line, entry = _ledger_line()
    root = _ledger_repo(tmp_path, [line])
    new_line, _ = _ledger_line("each project gets its own bmk env", decision="per project",
                               supersedes=[entry["id"]])
    _stage(root, SKILL + "/SKILL.md", "Intro.\n\nNow each project gets its own bmk env.\n")
    _stage(root, SKILL + "/.skillwriter/decisions.jsonl", line + new_line)
    assert RG.check_skill_decisions(root, RG.STAGE_INDEX, log=lambda r: None) == []


def test_an_unstaged_edit_does_not_block_a_commit(tmp_path):
    """The index is what the commit carries: a half-done working copy is not part of it."""
    line, _ = _ledger_line()
    root = _ledger_repo(tmp_path, [line])
    write(root / SKILL / "SKILL.md", "half-done rewrite\n")
    assert RG.check_skill_decisions(root, RG.STAGE_INDEX, log=lambda r: None) == []


def test_a_push_reads_head_not_the_index(tmp_path):
    line, _ = _ledger_line()
    root = _ledger_repo(tmp_path, [line])
    _stage(root, SKILL + "/SKILL.md", "dropped\n")
    assert RG.check_skill_decisions(root, RG.STAGE_HEAD, log=lambda r: None) == []


def test_a_removed_ledger_line_is_refused(tmp_path):
    line, _ = _ledger_line()
    second, _ = _ledger_line(topic="second")
    root = _ledger_repo(tmp_path, [line, second])
    _stage(root, SKILL + "/.skillwriter/decisions.jsonl", second)
    fails = RG.check_skill_decisions(root, RG.STAGE_INDEX, log=lambda r: None)
    assert any("append-only" in f for f in fails)


def test_deleting_the_whole_skill_takes_its_ledger_with_it(tmp_path):
    line, _ = _ledger_line()
    root = _ledger_repo(tmp_path, [line])
    subprocess.run(["git", "rm", "-rq", SKILL], cwd=root, check=True)
    assert RG.check_skill_decisions(root, RG.STAGE_INDEX, log=lambda r: None) == []


def test_another_skill_s_broken_ledger_does_not_block_an_unrelated_commit(tmp_path):
    line, _ = _ledger_line()
    root = _ledger_repo(tmp_path, [line])
    write(root / SKILL / "SKILL.md", "dropped, but not staged and not this commit\n")
    _stage(root, "plugins/bitranox/hooks/x.py", "x = 1\n")
    assert RG.check_skill_decisions(root, RG.STAGE_INDEX, log=lambda r: None) == []


def test_ci_sweeps_every_ledger_in_the_working_tree(tmp_path):
    line, entry = _ledger_line()
    root = _ledger_repo(tmp_path, [line])
    write(root / SKILL / "SKILL.md", "dropped\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    fails = RG.check_all_skill_decisions(root)
    assert len(fails) == 1 and entry["id"] in fails[0]


def test_jsonl_is_an_lf_checked_suffix():
    assert ".jsonl" in RG._LF_SUFFIXES
```

  The test named `another_skill_s_broken_ledger` stages nothing in the skill, so the skill is
  touched only in the working tree; it passes because the gate reads the INDEX of a touched skill,
  which still holds the anchor. Keep it: it is the "a peer's half-done edit never blocks" control.

- [ ] **Step 2:** Run `CI-PYTEST -k "ledger or anchor or skill_s or jsonl or append_only or
      superseding or push_reads"`. Expected: FAIL, `AttributeError: ... check_skill_decisions`.
- [ ] **Step 3: Implement.** Thread the keyword through the three readers (replace each
      `_mirror_ignored(rel)` call inside them with `ignore(rel)`, default `ignore=_mirror_ignored`,
      and pass it on from `shipped_files` to `_selected_files` and `_working_tree_files`). Then:

```python
import skill_decisions  # sibling module, standard library only

_LF_SUFFIXES = (".py", ".sh", ".json", ".jsonl")
_SKILL_PATH_RX = re.compile(r"^%s/([^/]+)/" % re.escape(_SKILLS_DIR))
#: What the decision check skips when it reads a skill: caches only. The mirror reader skips
#: `.skillwriter/` too, but the ledger lives there.
_DECISION_IGNORED = frozenset({"__pycache__", ".pytest_cache", ".git", ".ruff_cache"})


def _decision_ignored(rel):
    return bool(_DECISION_IGNORED & set(rel.split("/")))


def _log_decision_refusal(record):
    try:
        from self_improve_signals import _audit_dir  # noqa: PLC0415 - optional sink, never a gate input
        path = _audit_dir() / "skill-decision-gate.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:  # noqa: BLE001 - the log is for the 30-day review; it must never block
        pass


def _decision_message(name, finding):
    return ("skills/%s: %s\n  The rule's earlier decision is recorded with a reason. If the change "
            "is meant, record why: python3 plugins/bitranox/hooks/skill_decisions.py add --from-file "
            "<entries.json> with an entry whose supersedes names %s, staged with this change."
            % (name, finding.render(), finding.entry_id or "<id>"))


def _append_only_problem(root, name, shipped_ledger):
    base = _merge_base(root)
    if base is None:
        return None
    rel = "%s/%s/%s" % (_SKILLS_DIR, name, skill_decisions.LEDGER_REL)
    before = _checked_out_bytes(root, base, rel)
    if not before:
        return None
    old, new = before.splitlines(), shipped_ledger.splitlines()
    if new[:len(old)] != old:
        return ("skills/%s: %s is append-only; a line present at the fork point was changed or "
                "removed. Withdraw an entry with a new void entry instead." % (name, rel))
    return None


def _judge_skill(root, name, files, log):
    if "SKILL.md" not in files:
        return []                                   # the skill is deleted: its ledger goes with it
    ledger = files.get(skill_decisions.LEDGER_REL, b"")
    fails = []
    problem = _append_only_problem(root, name, ledger)
    if problem:
        fails.append(problem)
    lines = ledger.decode("utf-8", errors="replace").splitlines(keepends=True)
    for finding in skill_decisions.check_ledger(lambda: iter(lines), skill_decisions.corpus_text(files)):
        log({"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "skill": name,
             "entry_id": finding.entry_id, "problem": finding.problem})
        fails.append(_decision_message(name, finding))
    return fails


def check_skill_decisions(root, stage=STAGE_INDEX, *, log=None):
    """Refuse a commit or push whose SHIPPED text of a touched skill loses a live ledger anchor.

    Only the skills this change touches since the merge-base are read, and each at what the
    commit or push ships (`shipped_files` at `stage`), so another skill's half-done working copy
    never blocks an unrelated commit. The whole shipped skill dir is held at once, the ledger
    included: the same per-skill bound the mirror check already has.
    """
    changed = _changed_vs_origin(root)
    if changed is None:
        return []
    log = log or _log_decision_refusal
    names = sorted({m.group(1) for p in changed for m in [_SKILL_PATH_RX.match(p)] if m})
    fails = []
    for name in names:
        skill_dir = root / _SKILLS_DIR / name
        files = shipped_files(skill_dir, stage, ignore=_decision_ignored) if skill_dir.is_dir() else {}
        fails += _judge_skill(root, name, files, log)
    return fails


def check_all_skill_decisions(root):
    """The CI sweep: every ledger in the checkout against its skill's tracked text."""
    fails = []
    for path in sorted((root / _SKILLS_DIR).glob("*/" + skill_decisions.LEDGER_REL)):
        skill_dir = path.parent.parent
        for finding in skill_decisions.check_ledger(lambda p=path: skill_decisions.file_lines(p),
                                                    skill_decisions.corpus_from_dir(skill_dir)):
            fails.append(_decision_message(skill_dir.name, finding))
    return fails
```

  In `run_checks`, after `failures += check_version_sync(root)`:

```python
    # Both modes: CI sweeps every ledger (a clean checkout has nothing half-done), the hook and
    # the pre-push judge only the skills the change touches, at what it ships.
    if ci:
        failures += check_all_skill_decisions(root)
    else:
        failures += check_skill_decisions(root, stage=mirror_at)
```

  Check that `time` and `json` are already imported in repo-gate.py; add only what is missing.

- [ ] **Step 4:** Run `CI-PYTEST`. Expected: all pass, every pre-existing mirror test included
      (they prove the `ignore` default kept their behaviour).
- [ ] **Step 5:** `python3 plugins/bitranox/hooks/repo-gate.py --ci` from the worktree root.
      Expected: no ledger finding (no ledger exists yet) and the same verdict as before the task.
- [ ] **Step 6: Mutation check:** make `_judge_skill` read the working tree instead of `files`
      (call `skill_decisions.corpus_from_dir(skill_dir)`); `test_an_unstaged_edit_does_not_block`
      must go RED. Drop the `new[:len(old)] != old` check; `test_a_removed_ledger_line` must go RED.
- [ ] **Step 7: Commit** `repo-gate: refuse a change that drops a recorded skill decision` with
      `-- plugins/bitranox/hooks/repo-gate.py plugins/bitranox/hooks/tests/test_repo_gate.py`.

### Task 2.3 (M2.3): the checklist states what the change decided (D4)

**Files:**
- Modify: `plugins/bitranox/hooks/repo-gate.py:1184-1215` (`skill_review_failures`)
- Test: `plugins/bitranox/hooks/tests/test_repo_gate.py` (append)

**Interfaces:**
- Consumes: `skill_decisions.parse_entries`, `skill_decisions.file_lines`, `ledger_path`.
- Produces: `DECISIONS_LINE_RX` (module constant) and the new failure text.

The rule: among the co-changed `.skillwriter/*.md` files of a changed `SKILL.md` (the files the
function already reads), at least one holds a line matching

```python
DECISIONS_LINE_RX = re.compile(
    r"^Decisions:[ \t]+(?:none[ \t]+-[ \t]+\S.*|d-[0-9]{8}-[0-9a-f]{8}(?:,[ \t]*d-[0-9]{8}-[0-9a-f]{8})*)[ \t]*$",
    re.MULTILINE)
```

and every id it names is in that skill's ledger. The function already reads the checklists from
the working tree; the ledger is read the same way (`ledger_path(root / _SKILLS_DIR / name)`), so
the two sides of one rule use one lens.

**Out of scope:** the table re-pad waiver (a re-pad has no checklist and stays exempt);
`has_open_checkbox`.

**STOP conditions:** an existing `skill_review_failures` test builds a fully ticked checklist
for a changed SKILL.md and now fails: update that fixture by adding a `Decisions: none - fixture`
line, never by loosening the rule, and list every fixture changed in the commit message.

- [ ] **Step 1: Write the failing tests:**

```python
def _review(tmp_path, checklist, ledger=""):
    rel = "plugins/bitranox/skills/s1/"
    files = {rel + "SKILL.md": "x\n", rel + ".skillwriter/checklist-1.md": checklist}
    if ledger:
        files[rel + ".skillwriter/decisions.jsonl"] = ledger
    for path, text in files.items():
        write(tmp_path / path, text)
    return RG.skill_review_failures(tmp_path, list(files), read_original=lambda rel: None)


def test_a_checklist_without_a_decisions_line_is_refused(tmp_path):
    fails = _review(tmp_path, "- [x] RED\n- [x] GREEN\n")
    assert any("Decisions:" in f for f in fails)


def test_decisions_none_with_a_reason_passes(tmp_path):
    assert _review(tmp_path, "- [x] RED\nDecisions: none - wording only, no rule changed\n") == []


def test_decisions_none_without_a_reason_is_refused(tmp_path):
    assert _review(tmp_path, "- [x] RED\nDecisions: none\n")


def test_decisions_naming_an_id_the_ledger_lacks_is_refused(tmp_path):
    fails = _review(tmp_path, "- [x] RED\nDecisions: d-20261105-0123abcd\n")
    assert any("d-20261105-0123abcd" in f for f in fails)


def test_decisions_naming_a_ledger_id_passes(tmp_path):
    line, entry = _ledger_line()
    assert _review(tmp_path, "- [x] RED\nDecisions: %s\n" % entry["id"], ledger=line) == []
```

- [ ] **Step 2:** Run `CI-PYTEST -k decisions`. Expected: the first, third and fourth FAIL.
- [ ] **Step 3: Implement.** In `skill_review_failures`, after the open-checkbox loop for one
      skill (`for a in arts:`), add:

```python
        fails += _decisions_line_failures(root, name, arts)
```

  and beside the function:

```python
def _ledger_ids(root, name):
    path = skill_decisions.ledger_path(root / _SKILLS_DIR / name)
    try:
        return {e["id"] for e in skill_decisions.parse_entries(skill_decisions.file_lines(path))}
    except (skill_decisions.LedgerError, OSError):
        return set()                    # the ledger check reports a broken ledger itself


def _decisions_line_failures(root, name, arts):
    lines = []
    for a in arts:
        try:
            lines += DECISIONS_LINE_RX.findall((root / a).read_text(encoding="utf-8"))
        except OSError:
            continue
    if not lines:
        return ["skills/%s: the co-changed checklist has no 'Decisions:' line. Name the ledger ids "
                "this change added ('Decisions: d-YYYYMMDD-xxxxxxxx, ...') or say why it decided "
                "nothing ('Decisions: none - <reason>')." % name]
    named = set(re.findall(r"d-[0-9]{8}-[0-9a-f]{8}", "\n".join(lines)))
    missing = sorted(named - _ledger_ids(root, name))
    return (["skills/%s: 'Decisions:' names %s, not in the skill's ledger." % (name, ", ".join(missing))]
            if missing else [])
```

  `DECISIONS_LINE_RX.findall` returns the whole line only if the pattern has no group; the
  pattern above uses only non-capturing groups, so it does. Keep it that way.

- [ ] **Step 4:** Run `CI-PYTEST`. Expected: all pass (fixtures updated per the STOP rule).
- [ ] **Step 5: Mutation check:** remove the `missing` comparison; the id test must go RED.
- [ ] **Step 6: Commit** `repo-gate: a skill change's checklist names the decisions it recorded`.

### Task 2.4 (M2.4): the edit guard hands over the skill's declined decisions once

**Files:**
- Modify: `plugins/bitranox/hooks/skill-edit-guard.py` (`decide`, module docstring)
- Test: `plugins/bitranox/hooks/tests/test_skill_edit_guard.py` (append)
- Scratch, not shipped: `<scratchpad>/m2/price_brief_guard.py`

**Interfaces:**
- Consumes: `skill_decisions.render_brief`, `ledger_path`, `file_lines`;
  `self_improve_signals.session_state_path(session, suffix)`; `_agent_transcript(event)`.
- Produces: `ran_show(transcript: Path, skill: str) -> bool`; `decide` unchanged in signature.

**Out of scope:** `skill_receipt.py`; the receipt and load checks (the brief runs only AFTER
both pass, so an agent outside the procedure still gets the existing refusal first).

**STOP conditions:**
- the pricing replay (Step 1) cannot read the corpus or finds the transcript layout differs from
  `_agent_transcript`'s;
- the pricing shows more than one refusal per (agent, skill) is possible (the flag is broken).

- [ ] **Step 1: Price it before building it.** Write `price_brief_guard.py` (scratch) that walks
      `~/.claude/projects` with `rglob("*.jsonl")`, dedupes `tool_use` blocks by id, and for every
      `Edit`, `Write` or `MultiEdit` whose `file_path` matches the guard's `_SKILL_MD` counts the
      FIRST one per (transcript file, skill name); also counts how many of those transcripts held
      an earlier Bash command containing `skill_decisions.py show <skill>` (expected 0 today).
      Print: transcripts scanned, first-edits per (agent, skill), sessions with at least one, and
      the 30-day figure. Record the four numbers in the guard's docstring `Decisions` block
      (Step 4). This is the UPPER BOUND of refusals once every skill has a ledger; with M1/M2
      alone only skills holding a rejected or removed entry can refuse.
- [ ] **Step 2: Write the failing tests** (append; they reuse the module's `_session`,
      `_load_record`, `_CACHE` and `armed`):

```python
import skill_decisions as SD


def _skill_with_rejection(tmp_path, name="foo"):
    skill = tmp_path / "repo" / "skills" / name
    (skill / ".skillwriter").mkdir(parents=True)
    (skill / "SKILL.md").write_text("text\n", encoding="utf-8")
    entry = {"v": 1, "date": "2026-11-05", "kind": "rejected", "topic": "per-project-env",
             "decision": "Install per project.", "why": "Two projects cannot share it.",
             "evidence": {"tier": "measured", "text": "x"}, "reopen_if": "bmk changes.",
             "anchors": [], "supersedes": [], "refs": [], "origin": "authored"}
    entry["id"] = SD.entry_id(entry)
    SD.ledger_path(skill).write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return skill / "SKILL.md"


def _brief_edit(transcript, path):
    return {"session_id": "S", "transcript_path": str(transcript), "tool_name": "Edit",
            "tool_input": {"file_path": str(path)}}


def _show_record(skill):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_s", "name": "Bash",
         "input": {"command": "python3 /p/hooks/skill_decisions.py show %s --kind rejected,removed --full" % skill}}]}}


def test_the_first_edit_is_refused_once_with_the_declined_decisions(tmp_path, armed):
    path = _skill_with_rejection(tmp_path)
    main = _session(tmp_path, [_load_record(_CACHE + "meta-skill-writer")])
    reason = G.decide(_brief_edit(main, path), {})
    assert reason is not None and "Two projects cannot share it." in reason
    assert "re-send" in reason
    assert G.decide(_brief_edit(main, path), {}) is None


def test_an_agent_that_ran_show_is_not_refused(tmp_path, armed):
    path = _skill_with_rejection(tmp_path)
    main = _session(tmp_path, [_load_record(_CACHE + "meta-skill-writer"), _show_record("foo")])
    assert G.decide(_brief_edit(main, path), {}) is None


def test_show_for_another_skill_does_not_count(tmp_path, armed):
    path = _skill_with_rejection(tmp_path)
    main = _session(tmp_path, [_load_record(_CACHE + "meta-skill-writer"), _show_record("foo-bar")])
    assert G.decide(_brief_edit(main, path), {}) is not None


def test_a_skill_with_no_declined_decision_is_never_refused(tmp_path, armed):
    path = tmp_path / "repo" / "skills" / "plain" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("text\n", encoding="utf-8")
    main = _session(tmp_path, [_load_record(_CACHE + "meta-skill-writer")])
    assert G.decide(_brief_edit(main, path), {}) is None


def test_an_unreadable_ledger_lets_the_edit_through(tmp_path, armed):
    path = _skill_with_rejection(tmp_path)
    SD.ledger_path(path.parent).write_text("{broken\n", encoding="utf-8")
    main = _session(tmp_path, [_load_record(_CACHE + "meta-skill-writer")])
    assert G.decide(_brief_edit(main, path), {}) is None


def test_each_agent_is_refused_once_for_itself(tmp_path, armed):
    path = _skill_with_rejection(tmp_path)
    main = _session(tmp_path, [], agent="a1", agent_records=[_load_record(_CACHE + "meta-skill-writer")])
    event = dict(_brief_edit(main, path), agent_id="a1", agent_type="general-purpose")
    assert G.decide(event, {}) is not None and G.decide(event, {}) is None
```

- [ ] **Step 3:** Run `CI-PYTEST -k "declined or ran_show or show_for or no_declined or
      unreadable_ledger or refused_once"`. Expected: the first, third and last FAIL (the guard
      allows them today).
- [ ] **Step 4: Implement.** In `decide`, replace the allow line after the receipt and load
      checks:

```python
    if receipt and _loaded_by_editing_agent(event):
        return _brief_refusal(event, path)             # None unless the decisions brief is owed
```

  and add:

```python
_BRIEF_FLAG = ".skill-decisions-brief-"
_BRIEF = ("Before this first edit of skills/%s, read what was already decided for it. Each entry "
          "below was taken for the reason given; re-proposing one needs that reason answered, in a "
          "new ledger entry that supersedes it.\n\n%s\n\nThe full list: python3 <plugin>/hooks/"
          "skill_decisions.py show %s --kind rejected,removed --full. Now re-send the edit, revised "
          "or unchanged; the re-send is not refused.")


def _bash_commands(record):
    content = (record.get("message") or {}).get("content")
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Bash":
            yield str((block.get("input") or {}).get("command") or "")


def ran_show(transcript, skill):
    """True when `transcript` holds a Bash call of `skill_decisions.py show <skill>`."""
    wanted = re.compile(r"skill_decisions\.py\b.*\bshow\s+%s(?![\w-])" % re.escape(skill))
    with Path(transcript).open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "skill_decisions" not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if any(wanted.search(c) for c in _bash_commands(record)):
                return True
    return False


def _refuse_once(session, agent, skill):
    """True the first time for (session, agent, skill), recording it; False after, or if unstorable."""
    try:
        from self_improve_signals import session_state_path  # noqa: PLC0415 - optional state store
        key = hashlib.sha1(("%s/%s" % (agent, skill)).encode("utf-8")).hexdigest()[:16]
        flag = session_state_path(session, _BRIEF_FLAG + key)
        if flag.exists():
            return False
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("refused\n", encoding="utf-8")
        return True
    except Exception:  # noqa: BLE001 - a flag that cannot be stored lets the edit through
        return False


def _brief_refusal(event, path):
    session = event.get("session_id")
    if not isinstance(session, str) or not session.strip():
        return None
    skill_dir = Path(path).parent
    try:
        import skill_decisions  # noqa: PLC0415 - a missing module must not wedge the guard
        ledger = skill_decisions.ledger_path(skill_dir)
        brief = skill_decisions.render_brief(lambda: skill_decisions.file_lines(ledger),
                                             skill=skill_dir.name)
    except Exception:  # noqa: BLE001 - ledger integrity is the commit gate's job, not this guard's
        return None
    if not brief:
        return None
    transcript = _agent_transcript(event)
    try:
        if transcript is not None and ran_show(transcript, skill_dir.name):
            return None
    except OSError:
        pass                                           # unreadable: one refusal costs one re-send
    if not _refuse_once(session, event.get("agent_id") or "main", skill_dir.name):
        return None
    return _BRIEF % (skill_dir.name, brief, skill_dir.name)
```

  Add `import hashlib` to the imports. Extend the module docstring's decision list with:

```
  - AFTER both checks pass, once per (session, agent, skill): when the skill's ledger holds a
    live rejected or removed entry and the editing agent's transcript shows no
    `skill_decisions.py show <skill>` call, the first edit is refused with those entries
    (`render_brief`); the re-send passes. This direction fails OPEN: an unreadable ledger, a
    missing module or an unstorable flag lets the edit through, because the commit gate owns
    ledger integrity and this refusal only delivers reading.

Decisions:
- Refuse once, not every time, and never when the agent ran `show`: the user chose the
  refuse-once form for EnterWorktree and the question-premise hook (2026-10-12), and an agent
  that followed the procedure must never pay for it. Priced on <the date Step 1 ran> by
  replaying the transcript corpus: <the four numbers Step 1 printed>. Reopen if the refusal log
  shows agents
  re-sending unchanged edits without reading the brief.
```

- [ ] **Step 5:** Run `CI-PYTEST`. Expected: all pass, every existing guard test included.
- [ ] **Step 6: Mutation check:** make `_refuse_once` always return True; the "once" tests must
      go RED. Drop the `(?![\w-])` lookahead; `test_show_for_another_skill` must go RED.
- [ ] **Step 7: Commit** `skill-edit-guard: hand over a skill's declined decisions before its
      first edit` with the guard and its test.

### Task 2.5 (M2.5): the skill-writer procedure reads and writes the ledger

**REQUIRED SUB-SKILL:** `bitranox:meta-skill-writer` for every SKILL.md change below (receipt,
RED baseline with `bitranox:baseline-probe` agents, GREEN, REFACTOR, checklist). This task's own
checklist is the first one the M2.3 rule binds, so it carries a `Decisions:` line.

**Files:**
- Modify: `plugins/bitranox/skills/meta-skill-writer/SKILL.md` (sections named below; line numbers
  from the plan's Critical files, re-read before editing)
- Create: `plugins/bitranox/skills/meta-skill-writer/.skillwriter/decisions.jsonl` (through the
  CLI only) and the skill-writer checklist for this change
- Modify: `CONTRIBUTING.md` (lines 238-241), `CLAUDE.md` (a new short section)

What the text must say (the GREEN target; the RED baseline asks a probe agent, given the
current skill text and a scenario "you are about to re-add a rule that was removed last month",
what it does first, and must show it does NOT look for prior decisions):

1. **Step 0b, read the decisions** (right after the receipt step): run
   `python3 <plugin>/hooks/skill_decisions.py show <skill> --kind rejected,removed --full`, then
   the one-line index (`show <skill>`). For a tool-repo twin, pass `--skill-dir` naming the
   marketplace copy. An edit that reverses a listed decision needs a new entry answering its
   `reopen_if`, written before the edit.
2. **Baseline pass:** when the skill has no `rule` entries yet AND the edit is a rewrite or an
   A/B test, first record its load-bearing rules as `origin: baseline` entries, in their own
   commit, so the rewrite is checked against them.
3. **REFACTOR, append entries:** every decision the edit makes becomes an entry (`rule` with an
   anchor for a rule the text now states; `removed` for one taken out; `rejected` for an
   alternative or a declined gap whose reason will still hold next time). Entries go in through
   `add --from-file`, never by hand.
4. **Picking an anchor:** quote 20 to 200 characters that are the stable core of one rule,
   unique in the skill's Markdown, not a heading and not inside a table row; prefer the clause
   that would have to change if the rule changed. Avoid the three twin divergences (the `name:`
   field, a trailing `(<name>)` on the H1, the self-install blockquote).
5. **Checklist line:** `Decisions: <id>, <id>` or `Decisions: none - <reason>`.
6. **"Keep out of both" carve-out** (lines 627-657): the ledger holds decision, reason, evidence
   and reopen-if; it is still no place for session narrative. Entry text is public: no private
   hosts, paths or repo names; "user decision <date>" is fine.

**Ledger entries for this change** (dogfood; written with `add --from-file` after the GREEN
text exists, so each anchor quotes the shipped sentence):
- one `rule` per item 1 to 5 above, tier `user` for 1, 3 and 5 (the user's 2026-11-05 decision
  quoted in the plan's Context), tier `measured` for 4 (the M0 PREREG result);
- one `rejected` entry: "a narrative history file per skill", why: git and CHANGELOG already hold
  the narrative and a rewritten history file erodes (the context-watcher finding), reopen if: an
  editor needs history the ledger plus `git log` cannot answer.

`CONTRIBUTING.md` (at the existing skill-change section): two sentences naming the ledger, the
`Decisions:` line, and `skill_decisions.py show`. `CLAUDE.md`: a section "Skill decisions are
recorded per skill" stating where the ledger lives, that the commit gate refuses a dropped anchor
and how to answer it (a superseding entry), and that hooks and jigs use a docstring `Decisions`
block instead (M3 adds that rule to the hook and jig skills).

**STOP conditions:** the RED baseline already looks for prior decisions (then the text change
is not needed as drafted: report what the probe did); a probe agent's GREEN run still skips
`show`; `repo-gate.py --mirrors` reports meta-skill-writer as mirrored (then its twin needs the
same text: add that repo to this task before editing).

- [ ] **Step 1:** Run the meta-skill-writer procedure through RED (two baseline-probe agents),
      GREEN (the text above), REFACTOR (entries, checklist with its `Decisions:` line).
- [ ] **Step 2:** `python3 plugins/bitranox/hooks/skill_decisions.py check meta-skill-writer`
      exits 0; `python3 plugins/bitranox/hooks/repo-gate.py --ci` passes.
- [ ] **Step 3: Commit** `meta-skill-writer: read and record a skill's decisions` with the
      SKILL.md, its `.skillwriter/` files, `CONTRIBUTING.md` and `CLAUDE.md`.

### Task 2.6 (M2.6): end-to-end controls on a scratch worktree

No code; this proves the shipped behaviour the plan's M2 verification names, with the REAL hook
entry points (`repo-gate.py` reading a PreToolUse event on stdin, `skill-edit-guard.py` likewise),
never the functions.

- [ ] **Step 1:** `git worktree add <scratchpad>/m2/e2e HEAD` (detached). In it, record a rule
      entry for a real sentence of `devops-bmk/SKILL.md` via `add`, commit it with its checklist.
- [ ] **Step 2:** Delete that sentence, stage it, and pipe a `git commit` PreToolUse event into
      `repo-gate.py` (`git -C <e2e>` in the command so the hook judges that repo). Expected: exit
      2, the message names the entry id, its why and its reopen_if.
- [ ] **Step 3:** Add a superseding entry, stage it, replay the event. Expected: pass.
- [ ] **Step 4, controls:** (a) leave another skill's SKILL.md edited and unstaged, commit an
      unrelated file: passes. (b) Move `origin/master` of the scratch repo one commit ahead of
      HEAD (`update-ref`), commit an unrelated file: passes. (c) Drop the sentence AND write the
      superseding entry to the ledger on disk, then `git commit -F msg -- SKILL.md` naming only
      SKILL.md: refused (that selection takes SKILL.md from disk and the ledger from HEAD, where
      the superseding entry is absent).
- [ ] **Step 5, guard:** replay an Edit event for that skill with a transcript that loaded
      meta-skill-writer and holds a fresh receipt (`skill_receipt.py start` under an isolated
      HOME): refused once with the brief once a `rejected` entry exists; the re-send passes; a
      transcript holding a `show` call is not refused; a skill with an empty ledger is not.
- [ ] **Step 6:** Write the outputs of Steps 2 to 5 into the review notes; remove the scratch
      worktree with `wtclean.py --apply` after checking nothing runs in it.

### Task 2.7 (M2.7): mirrored skills (M2b)

**Files:**
- Modify: `plugins/bitranox/hooks/repo-gate.py` (the tool-repo path, `_tool_repo_touched` and
  the function that judges a tool-repo commit's twins)
- Test: `plugins/bitranox/hooks/tests/test_repo_gate.py` (append)

When a TOOL repo commit or push ships a change to a twin, also run the MARKETPLACE copy's ledger
(read at its published ref plus local commits, the way the mirror check already reads the
marketplace side) against the twin's shipped Markdown, after erasing the three by-convention
divergences with the mirror check's own normaliser. A finding refuses the tool-repo commit with
the same message as M2.2, naming the marketplace ledger as the place to add the superseding entry.

**STOP conditions:** the tool-repo path has no single function receiving both the twin's shipped
files and the marketplace skill dir (then report the call graph and split this task); the change
exceeds about 150 lines (report and ask whether to ship M2.7 in the next release).

- [ ] **Step 1:** Read the tool-repo commit path end to end (`_tool_repo_touched` at the line
      after `run_checks`, its callers, the mirror normaliser) and write its call graph into the
      review notes.
- [ ] **Step 2:** Failing test: a tool repo whose twin `SKILL.md` drops a sentence the
      marketplace ledger anchors is refused; the same drop with a superseding marketplace entry
      passes; a twin edit that touches no anchor passes.
- [ ] **Step 3:** Implement at the function Step 1 found; run `CI-PYTEST`; mutation check (skip
      the new call: the refusal test goes RED).
- [ ] **Step 4: Commit** `repo-gate: a tool repo's twin answers to the marketplace ledger`.

### Task 2.8 (M2.8): release

- [ ] **Step 1:** `git fetch`, `git rebase origin/master`; re-run `CI-PYTEST` and
      `python3 plugins/bitranox/hooks/repo-gate.py --ci` after the rebase.
- [ ] **Step 2:** The bump commit made before Task 2.1 raised origin's 10.17.1 to 10.18.0 with
      these notes: `### Added` - the per-skill decision ledger and its CLI; the commit gate
      refuses a change that drops a recorded decision; the skill-writer checklist names the
      decisions a change made; the edit guard hands over a skill's declined decisions before the
      first edit. `### Fixed` - changed-path checks diffed from origin's tip, so a checkout behind
      origin listed a peer's pushed paths as its own. Re-read origin's version now
      (`git show origin/master:plugins/bitranox/.claude-plugin/plugin.json`); edit the CHANGELOG
      section if a task changed what shipped.
- [ ] **Step 3:** If origin's version is no longer 10.17.1, renumber: `bump_version.py --rebase`
      when its `--help` says it handles this branch's shape, else a new commit with
      `--to <origin's minor + 1>.0` that moves the CHANGELOG section; assert the expected current
      value before writing either way.
- [ ] **Step 4:** `ListAgents`; message each live peer that a push is coming and that the gate
      gains the ledger checks (the release note text). Then `git push origin
      feat/skill-decisions:master` (the pre-push hook is the gate; do not also run it by hand).
- [ ] **Step 5:** `ci_wait.py --ref HEAD` (compuse-toolbox), every run terminal and green;
      `git fetch` and confirm `git log origin/master -1 --format=%s` is the bump commit.
- [ ] **Step 6:** Update OPEN-WORK [28] in the main checkout: `next:` becomes M3 (seed, code
      docstring rule, audit rooms, meta-self-improve), and the plan file gets the M3 tasks in a
      later session.

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
