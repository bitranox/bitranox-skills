# [29] Review dispatches run on opus at effort medium - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development (recommended) or bitranox:process-plan-executor to implement this plan task-by-task. Every SKILL.md / skill reference edit goes through REQUIRED SUB-SKILL bitranox:meta-skill-writer (its checklist, one task per phase; the skill-edit-guard hook refuses the edit otherwise). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Every judging-review subagent dispatch the bitranox plugin prescribes runs on `opus` at
effort `medium`, stated at the point of dispatch, with a warn-only hook that flags a review dispatch
missing either.

**Architecture:** One canonical rule ("Review dispatches") in
process-agents-subagent-driven-development replaces the effort table's inherit / xhigh-max rows for
reviews; every review dispatch site in 19 skills names `model: opus` + `effort: medium` and points at
that section; the two reviewer templates and `audit_skills.py` carry the field; the existing
`subagent-model-gate.py` gains a review nudge, replay-measured before shipping.

**Tech Stack:** Markdown skills, Python hooks (pytest, CI dependency set), compuse-toolbox jigs
(guard_replay.py, claim_check.py), memory_engine.py, Claude Code 2.1.306.

## Context

OPEN-WORK.md [29], USER, 2026-10-21, verbatim: "for reviewing tasks use opus 5.5 effort low !"

Superseded the same day by the user (2026-10-21, /goal), verbatim: "we want to use "medium"
effort, not "low" throughout, so change the plan first." Every review dispatch below
therefore runs at effort `medium`; `low` survives only where it already meant something else
(the haiku mechanical-scan row, quotes of existing text, probe-agent file names).

User decisions this session (2026-10-21, AskUserQuestion; quote them verbatim from
USER-DECISIONS.jsonl into EXECUTION-USER-REVIEW.md in Task 0):
1. Scope = "All judging review (Recommended)": task reviewer, final whole-branch review,
   code-review skills, skeptic/adversarial lenses, verify passes, adjudicators, quote-back checks,
   audit reviewers, judge panels. NOT implementers, fixers, scenario writers, or RED/GREEN probe
   subjects (they keep their haiku+opus tier pairs).
2. Enforcement = "Warn-only nudge (Recommended)": extend subagent-model-gate, never block,
   replay-measure the firing rate before shipping.

Why it is needed: the canonical tier reference says the opposite for part of that set
(`process-agents-subagent-driven-development/SKILL.md:152-161`: opus judging fan-out "inherit - do
not set", "Adversarial verify / judge panel / final synthesis | `xhigh` or `max`", and "Pinning
`low` broadly silently degrades"). `~/.claude/settings.json` sets `effortLevel: xhigh`
(`modelSettings.claude-opus-5-5.effortLevel: high`), so a review dispatch naming no effort
probably runs deep (unverified: Task 1 measures it). The Agent tool's `effort` field may be set
only when the user, CLAUDE.md or a skill asks, so each skill step must say it where it dispatches.

## Global Constraints

- Review dispatch = `model: "opus"` (alias, never a pinned id) + `effort: "medium"`. Workflow:
  `agent(..., {model: 'opus', effort: 'medium'})`. Headless: `claude -p --model opus --effort medium`.
- Out of scope, do NOT change tier or effort: implementers, fixers, scenario writers, RED/GREEN /
  baseline / pressure probes (`bitranox:baseline-probe`, meta-skill-writer probe arms,
  testing-skills-with-subagents RED/GREEN, process-test-driven-development scenario checks,
  meta-self-improve retrieval probe), haiku mechanical scans, final SYNTHESIS (keeps xhigh/max),
  non-Claude reviewers (docs-generate-schematics' Gemini review).
- Do not edit `~/.claude/settings.json` (the user's own default); the explicit field overrides it.
- No mirrored skill is touched (MIRRORED_SKILLS in hooks/repo-gate.py: none of the 19 below), so no
  twin release; still run `repo-gate.py --mirrors` before push.
- Work in a fresh worktree from `origin/master` after `git fetch` (marketplace rule); push
  `<branch>:master`; never force-push.
- ASCII punctuation only (tell-sweep); new table rows fit existing column widths.
- Bump `plugins/bitranox/.claude-plugin/plugin.json` MINOR (new hook capability): read the current
  value from `origin/master` and assert it before writing (expected 9.10.3 -> 9.11.0 unless a peer
  moved it).
- Tests run with CI's dependency set:
  `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/ -q`

## Inventory (measured 2026-10-21 by two Explore sweeps over 83 skills / 1006 files, hooks, agents, docs, ~/.claude, 13 twin dirs, memory facts)

Review dispatch sites to change (file paths under `plugins/bitranox/skills/`):

| Skill / file                                                       | Site                                                      | Today           |
|--------------------------------------------------------------------|-----------------------------------------------------------|-----------------|
| process-agents-subagent-driven-development/SKILL.md                | :116-117, :135-164 effort section + table, :176-181, :200 | opus, xhigh     |
| process-agents-subagent-driven-development/task-reviewer-prompt.md | :11-14 template (no effort field)                         | placeholder     |
| process-review-requesting-code-review/SKILL.md, code-reviewer.md   | SKILL :34-36, :89; template :8-12 (+ meta-review fan-out) | opus            |
| process-agents-dispatching-parallel/SKILL.md                       | :103-108, :126-128 read-only reviewer                     | opus            |
| process-review-verification-before-completion/SKILL.md             | :103-109 adversarial verifier                             | opus            |
| process-review-enhance-code-quality/SKILL.md                       | :82-87, :416, :539-545, :634                              | opus / none     |
| process-review-receiving-code-review/SKILL.md                      | :33-38 EVALUATE second opinion, :109-111 re-reviewer      | opus / none     |
| process-plan-executor/SKILL.md                                     | :24-30 review helper / verification agent                 | policy          |
| process-plan-writing-plans/SKILL.md                                | :185-194 two-stage review (points to SDD)                 | none            |
| coding-python-clean-architecture/SKILL.md                          | :33-38 REVIEW mode                                        | opus            |
| coding-bash-clean-architecture/SKILL.md                            | :28-33 REVIEW mode                                        | opus            |
| coding-python-performance-review/SKILL.md                          | :68-73 audit / claim validation                           | opus            |
| coding-python-enforce-data-architecture-strict/SKILL.md            | :270-272 audit fan-out, :440-450 analysis template        | opus / none     |
| infra-proxmox/SKILL.md                                             | :52-64 steelman / red-team                                | opus            |
| meta-consolidate-claude-md/SKILL.md                                | :80-83 claim verification per heading                     | opus            |
| meta-dream-tree/SKILL.md, references/dream-core.md                 | SKILL :174-176; dream-core :203-216 skeptic lenses        | none            |
| meta-self-improve/SKILL.md (+ judge_panel.py docs)                 | judge panel; :348/:399 are PROBES (out of scope)          | none            |
| meta-skill-writer/SKILL.md, testing-skills-with-subagents.md       | quote-back :1305-1308; testing :374-376                   | none            |
| meta-skill-audit/SKILL.md, scripts/audit_skills.py                 | SKILL :68-77, :108; audit_skills.py:812 reviewer_command  | opus, no effort |
| meta-audit-local-skills-and-hooks/SKILL.md                         | :90-96 (runs audit_skills.py)                             | inherited       |
| sec-appsec-web-baseline/SKILL.md                                   | :66-69 multi-page audit fan-out                           | none            |

Outside skills:
- `plugins/bitranox/hooks/subagent-model-gate.py:9-11, :56-61`: says effort "is not a per-dispatch
  field" - false (the Agent tool has `effort`; `claude --help` lists `--effort`). Fix wording.
- Memory fact `reference-subagent-effort-working-channels-and-the-a-b-proof` (body :12, :17; pointer
  `CLAUDE.local.md:27` at this repo's level): "xhigh/max for adversarial verify" - rewrite.
- Memory fact `reference-substrate-constraints-for-a-claude-agent-team` (body :15; pointer
  `projects/public/KI/CLAUDE.local.md`): says effort only via agent-definition frontmatter - add the
  per-dispatch field (adjacent rot).
- `docs/concepts.md` (1 effort hit) and `docs/architecture.md:89` (gate row): re-read, update if
  they restate the table or the gate's behaviour.
- Left alone, with reason: facts on haiku re-runs for probes (probe scope); `~/.claude/agents/
  probe-effort-{low,max}.md` (sonnet probe scaffolding, probe scope, user's own dir);
  `plugins/bitranox/agents/baseline-probe.md` (probe); synced third-party skills under
  `~/.claude/skills/synced/` (not ours).

Adjacent rot fixed on the way (model only, no effort): meta-skill-writer SKILL.md:1098 and :1205
dispatch examples carry no `model:` line, against the skill's own rule at :1142 - add
`model: "opus"`.

---

### Task 0: Worktree, decision log, backlog line

**Files:** Modify: `OPEN-WORK.md` ([29] line), `EXECUTION-USER-REVIEW.md` (gitignored, user-decision section)

- [ ] `cd /media/srv-main-softdev/projects/public/KI/bitranox-skills && git fetch origin && git worktree add .claude/worktrees/review-effort-29 -b review-effort-29 origin/master`
- [ ] In the MAIN checkout: append both decisions to EXECUTION-USER-REVIEW.md, labels and
      descriptions quoted verbatim from the last two AskUserQuestion entries of
      `USER-DECISIONS.jsonl`; any reading of my own marked "(my reading)".
- [ ] In the worktree's OPEN-WORK.md [29] line: replace `size: unknown...` with
      `size: ~50 review sites in 19 skills + 2 templates + audit_skills.py + gate hook + 2 facts`,
      `open:` adds "scope + warn-only nudge chosen 2026-10-21", `next:` "execute
      docs/plans/2026-10-21-review-dispatch-effort-plan.md from Task 1".

### Task 1: Probe that the effort field takes effect (iron rule: probe harness behaviour first)

Nothing is built until this proves the `effort` field overrides the settings.json default on both
channels the plan uses. `low` is the INSTRUMENT here, not the shipped value: it is the arm far
enough from the default to show the field reaches the model at all; `medium` is the value the plan
ships, measured beside it so its effect is on record.

- [ ] Agent tool: dispatch 9 `general-purpose` agents with `model: "opus"`, interleaved
      L,M,B,L,M,B,L,M,B (L = `effort: "low"`, M = `effort: "medium"`, B = no effort), identical
      prompt: a short multi-step puzzle answered in one line, no tools. Read each subagent
      transcript (`~/.claude/projects/<this dashkey>/<session>/subagents/agent-<id>.jsonl`, resolve
      via session id, rglob) and sum `usage.output_tokens` per agent.
      Pre-registered: if every L < every B by >= 3x, the field works -> continue; else STOP and
      report (the whole plan rests on it). M is recorded, not gating (the user chose medium): if
      the M median is not below the B median, say so in the final report as a finding for the user.
- [ ] Headless: same interleave with `claude -p --model opus --effort <low|medium> --settings '{"disableAllHooks":true}' "<puzzle>" --output-format json`
      vs no `--effort`; compare `usage.output_tokens` from the JSON. Same pre-registered rule.
- [ ] Record both results (numbers + commands) in the [29] OPEN-WORK line (`measured:`).

### Task 2: Canonical rule in process-agents-subagent-driven-development

**Files:** Modify `plugins/bitranox/skills/process-agents-subagent-driven-development/SKILL.md`
(:116-117, :135-164, :176-181, :200), `task-reviewer-prompt.md:11-14`; checklist
`.skillwriter/checklist-20261021-review-effort.md`.

**Out of scope:** the implementer template and implementer tiering (non-review); the haiku `low`
row and the "final synthesis xhigh/max" part (synthesis is not review).

- [ ] RED (meta-skill-writer): snapshot the pre-edit SKILL.md to `.plan/review-effort-29/pre/`;
      quote-back probe via `bitranox:baseline-probe` on `haiku` AND `opus` with the excerpt:
      "You are about to dispatch (a) the per-task reviewer, (b) a skeptic lens on a duplicate
      verdict, (c) an adversarial verifier. For each, which `model` and `effort` do you pass, and
      quote the line that says so." Expected RED: (a) opus/no effort, (c) xhigh or max.
- [ ] Edit: add a `### Review dispatches` subsection under Model Selection, before the effort
      paragraph:

```markdown
### Review dispatches: `opus` at effort `medium`

Every dispatch whose job is to JUDGE work already done runs on `model: "opus"` with
`effort: "medium"`: the per-task reviewer and its re-reviews, the final whole-branch review, code
review, skeptic and adversarial lenses, verify passes, adjudicators, quote-back checks, audit
reviewers and judge panels. User directive 2026-10-21; this paragraph is the explicit ask the
Agent tool's `effort` field requires, so pass the field on every such dispatch. On a Workflow
`agent()` call pass `{model: 'opus', effort: 'medium'}`; on a headless reviewer pass
`claude -p --model opus --effort medium`. Name the field even when it looks redundant: the user's
default effort is high, and an omitted field inherits it.

It does NOT cover implementers and fixers, scenario writers, or RED/GREEN and baseline probe
subjects: a probe is the thing under test, and its tier pairs stay as `bitranox:meta-skill-writer`
prescribes. `subagent-model-gate` warns on a review-shaped dispatch that is missing either value.
```

- [ ] Effort table (:157-161): replace the adversarial row and add a review row, widths kept:

```markdown
| Role                                                | Effort                                       |
|-----------------------------------------------------|----------------------------------------------|
| `haiku`-tier mechanical scan / transcribe / extract | `low` (the big saver on fleet-scale fan-out) |
| Any review (see "Review dispatches")                | `medium` on `opus` (user, 2026-10-21)        |
| `opus` fan-out / bounded judgment / deep reasoning  | inherit - do not set                         |
| Final synthesis                                     | `xhigh` or `max`                             |
```

- [ ] Reword :152-155 so the "extremes only / pinning low broadly degrades" warning names reviews
      as the user-directed exception; :163-164 add "a review dispatch is always asked (see
      'Review dispatches')". :176-181 and :200: append "at effort `medium`" to the reviewer mentions.
- [ ] task-reviewer-prompt.md: under `model:` add
      `  effort: medium   # review dispatch - see SKILL.md "Review dispatches"` and set the model line
      to `model: opus` (reviewer is always opus; the placeholder stays for nothing else).
- [ ] GREEN: same probe on post-edit text, haiku + opus; pass = all three answered opus/medium with a
      quoted line. Re-run on the final text after any fix (re-run-the-probe rule).
- [ ] Commit in worktree: `git -C <wt> add <paths> && git -C <wt> commit -F <msgfile>`.

### Task 3: Every other review site (19 skills)

**Files:** every row of the Inventory table except Task 2's, plus meta-skill-writer :1098/:1205
model lines. One `.skillwriter/checklist-20261021-review-effort.md` per edited skill
(generate with the precedent `.plan/fold-23/batch3/fold18/mkchecklists.py` pattern).

**Pattern** at each site (adapt the sentence, keep it one clause):
- dispatch named with opus already -> "a pinned `opus` subagent at effort `medium` (review dispatch,
  see bitranox:process-agents-subagent-driven-development \"Review dispatches\")";
- dispatch with no model -> add both values with the same pointer;
- template / code block -> add `model: "opus"` and `effort: "medium"` lines;
- workflow prose -> `{model: 'opus', effort: 'medium'}`.
Representative: `process-review-requesting-code-review/code-reviewer.md:8-12` gains
`effort: "medium"` beside `model: "opus"` and the meta-review sentence says "opus at effort medium";
`meta-dream-tree/references/dream-core.md:203-216` "Give each skeptic a distinct lens" gains
"(each an `opus` subagent at effort `medium`)".

**Out of scope:** meta-self-improve SKILL.md:348/:399, meta-skill-writer RED/GREEN arms (:1029,
:1129, :1157, :1243, :1296), testing-skills-with-subagents RED/GREEN table, TDD :225/:274,
write-humanize-*, process-debug-systematic, meta-collect-knowledge, dream fan-outs that classify
or write descriptors (all non-review), docs-generate-schematics (Gemini API).

**STOP if** a listed line no longer matches the inventory quote (re-grep; the tree moves).

- [ ] Before editing, re-run the inventory grep in the worktree and diff against the table:
      `grep -rnE -i 'review|skeptic|adversarial|verif|quote-back|audit|adjudicat|judge|red-team' plugins/bitranox/skills --include='*.md' | grep -v .skillwriter | grep -iE 'subagent|dispatch|agent\(|opus|Task tool'`
      Any hit not in the table: classify it (review / probe / non-review) and add or exclude with
      a reason in the commit message.
- [ ] RED: one quote-back question per skill on the pre-edit snapshot (Workflow fan-out, probe
      subjects on haiku + opus per meta-skill-writer, `bitranox:baseline-probe` with the excerpt in
      the prompt): "Your skill tells you to dispatch <the site's reviewer>. Which model and effort
      do you pass? Quote the line."
- [ ] Edit all sites per the pattern.
- [ ] GREEN: same questions on post-edit text; every answer opus/medium with an exact quote
      (substring-check the quotes against the files, `.plan/fold-23/batch3/fold18/qcheck.py`
      pattern). Fix and re-run until clean.
- [ ] Coverage check: re-run the inventory grep; every review hit's line or its paragraph now
      contains `effort` (script: for each hit, `effort` within +-3 lines, else list it). Zero
      unlisted review hits allowed.
- [ ] Commit.

### Task 4: audit_skills.py headless reviewers at effort medium

**Files:** Modify `plugins/bitranox/skills/meta-skill-audit/scripts/audit_skills.py:810-812` (and
the `--model` CLI block :1059, :1137-1143); Test `plugins/bitranox/skills/meta-skill-audit/tests/test_audit_reports.py:305`
neighbourhood; SKILL.md :68-77 mention.

- [ ] Failing test (drives the real function):

```python
def test_reviewer_command_runs_opus_at_effort_low():
    argv = A.reviewer_command("claude", "opus")
    assert argv[argv.index("--model") + 1] == "opus"
    assert argv[argv.index("--effort") + 1] == "medium"
    assert argv[-2:] == ["--settings", A.REVIEWER_SETTINGS]
```

- [ ] Run: `... python -m pytest plugins/bitranox/skills/meta-skill-audit/tests/test_audit_reports.py -q -k effort` -> FAIL (`--effort` not in list).
- [ ] Implement:

```python
# Reviewers judge finished work: the user's directive (2026-10-21) runs every review on opus at
# effort medium, and naming it here overrides the user's higher default effort from settings.json.
REVIEWER_EFFORT = "medium"


def reviewer_command(exe, model):
    """argv for one headless reviewer: print mode, the model, effort medium, every hook switched off."""
    return [exe, "-p", "--model", model, "--effort", REVIEWER_EFFORT, "--settings", REVIEWER_SETTINGS]
```

- [ ] Run the skill's whole tests dir -> PASS; meta-skill-audit SKILL.md line mentioning the
      `claude -p` command gains `--effort medium`.
- [ ] Commit.

### Task 5: subagent-model-gate review nudge + wording fix

**Files:** Modify `plugins/bitranox/hooks/subagent-model-gate.py`; Test
`plugins/bitranox/hooks/tests/test_subagent_model_gate.py`; docs `docs/architecture.md:89` row text.

**Interfaces:** `assess(tool_name, tool_input, plan_armed=False, definition_model=None) -> (action, message)` unchanged signature; new pure helper `review_shaped(tool_input) -> bool`.

- [ ] Failing tests:

```python
def test_review_dispatch_without_low_effort_warns():
    action, msg = G.assess("Agent", {"description": "Review Task 3 (spec + quality)",
                                     "model": "opus", "prompt": "x"})
    assert action == "warn" and "effort" in msg and "medium" in msg

def test_review_dispatch_on_opus_low_is_silent():
    assert G.assess("Agent", {"description": "skeptic lens on duplicate verdicts",
                              "model": "opus", "effort": "medium", "prompt": "x"}) == (None, "")

def test_review_dispatch_on_haiku_warns_for_the_model():
    action, msg = G.assess("Agent", {"description": "verify the fix", "model": "haiku",
                                     "effort": "medium", "prompt": "x"})
    assert action == "warn" and "opus" in msg

def test_probe_dispatch_is_not_a_review():
    for d in ("GREEN probe: verify the skill text", "RED baseline pressure test"):
        assert G.assess("Agent", {"description": d, "model": "haiku", "prompt": "x"}) == (None, "")
    assert G.assess("Agent", {"subagent_type": "bitranox:baseline-probe",
                              "description": "review quote-back", "prompt": "x"},
                    definition_model="opus") == (None, "")

def test_non_review_dispatch_unchanged():
    assert G.assess("Agent", {"description": "Implement Task 2", "model": "opus",
                              "prompt": "x"}) == (None, "")

def test_unpinned_review_while_armed_still_denies_and_names_effort():
    action, msg = G.assess("Agent", {"description": "Final whole-branch review", "prompt": "x"},
                           plan_armed=True)
    assert action == "deny" and "effort" in msg

def test_tier_message_no_longer_says_effort_cannot_go_on_the_dispatch():
    assert "not the dispatch" not in G._TIERS
```

- [ ] Run -> FAIL.
- [ ] Implement (module level, beside the other messages):

```python
# Judging-review vocabulary, matched on the description and agent type only: the prompt carries
# the reviewed text itself, which names these words for reasons of its own. Probe words win:
# a RED/GREEN probe subject is the thing under test and keeps its tier pair (user, 2026-10-21).
_REVIEW_RE = re.compile(
    r"\b(re-?review\w*|review\w*|skeptic\w*|adversarial|verif\w*|audit\w*|adjudicat\w*|"
    r"judge\w*|quote-back|red-team\w*|second opinion|cross-check\w*)\b", re.I)
_PROBE_RE = re.compile(r"\b(probe\w*|baseline|pressure|RED|GREEN)\b")
_PROBE_TYPES = ("baseline-probe", "probe-effort")

_REVIEW_MESSAGE = (
    "Review-shaped dispatch: every judging review (task/final/code review, skeptic or adversarial "
    "lens, verify, adjudication, quote-back, audit, judge panel) runs on `model: opus` with "
    "`effort: medium` - user directive 2026-10-21, see bitranox:process-agents-subagent-driven-"
    "development \"Review dispatches\". Pass both fields; an omitted effort inherits the user's "
    "higher default. Ignore this if the dispatch is not a review.")


def review_shaped(tool_input):
    """True when the dispatch's description or agent type reads as a judging review, not a probe."""
    agent_type = str(tool_input.get("subagent_type") or "").lower()
    if any(p in agent_type for p in _PROBE_TYPES):
        return False
    label = "%s %s" % (tool_input.get("description") or "", agent_type)
    return bool(_REVIEW_RE.search(label)) and not _PROBE_RE.search(label)
```

  In `assess`, compute the existing verdict first, then: if `review_shaped(tool_input)` and
  (effective model lacks "opus" or `str(tool_input.get("effort") or "").lower() != "medium"`),
  return `("deny", deny_msg + " " + _REVIEW_MESSAGE)` when the existing verdict was deny, else
  `("warn", (existing_msg + " " if existing_msg else "") + _REVIEW_MESSAGE)`. Effective model =
  dispatch model, else `definition_model`. Rewrite `_TIERS` and the module docstring :9-11:
  "Effort is set per dispatch with the Agent tool's `effort` field when a skill or the user asks
  (every review does), or by the agent type / a Workflow `agent()` call."
- [ ] Run tests -> PASS; whole hooks suite with CI deps -> PASS.
- [ ] Replay (feedback: measure a guard's firing rate on the real corpus): run
      `uv run plugins/bitranox/skills/compuse-toolbox/scripts/guard_replay.py --help`, then replay
      `assess` over every Agent/Task tool_use in `~/.claude/projects` (rglob, dedupe by tool_use
      id). Report: total dispatches, review-shaped count, warn count, and split by trigger word.
      Read 30 random firings and all firings of any word that is > 40 % of them; adjudicate each
      review / probe / other. Pre-registered: ship if >= 80 % of the sampled firings are real
      reviews; otherwise narrow `_REVIEW_RE` (drop the noisy word) and re-replay. Record the
      numbers in the commit message.
- [ ] Update `docs/architecture.md:89` row: "... DENY while a plan execution is armed; warn on a
      review dispatch not on opus at effort medium" (fit column width).
- [ ] Commit.

### Task 6: Memory facts and docs

**Files:** facts `reference-subagent-effort-working-channels-and-the-a-b-proof`,
`reference-substrate-constraints-for-a-claude-agent-team` (via the engine); `docs/concepts.md`.

- [ ] Read both bodies in full. Effort fact: rewrite body :17 to "low for mechanical fan-out; medium for
      every judging review (opus, user directive 2026-10-21); xhigh/max for final synthesis;
      inherit otherwise"; body :12 adds "a skill naming the level counts as the ask - the review
      rule in process-agents-subagent-driven-development is one". New hook (<= 250 chars):
      "When setting a subagent's effort: the Agent tool's effort field works once a skill/user asks;
      Workflow agent() opts.effort and claude -p --effort too. Reviews: opus at medium. Detail:
      bitranox:process-agents-subagent-driven-development."
- [ ] `memory_engine.py add --slug reference-subagent-effort-working-channels-and-the-a-b-proof --proj /media/srv-main-softdev/projects/public/KI/bitranox-skills --hook-file <f> --body-file <f>`
      (owning level = the CLAUDE.local.md that holds the pointer; confirm with find + grep first).
      Read the body back, confirm `metadata.type` kept.
- [ ] Substrate fact: body :15 add "per dispatch also via the Agent tool's `effort` field"; add at
      its owning level (`/media/srv-main-softdev/projects/public/KI`).
- [ ] `docs/concepts.md`: read the effort hit; if it restates the old table, point it at
      "Review dispatches" instead. Commit docs in the worktree; the store commits per its own
      workflow (shared store: stage only the two fact paths).

### Task 7: Ship

- [ ] CHANGELOG.md entry under a new 9.11.0 heading: "Review dispatches run on opus at effort medium:
      canonical rule in process-agents-subagent-driven-development, every review site in 19
      skills, reviewer templates, meta-skill-audit's headless reviewers (`--effort medium`); the
      subagent-model-gate hook warns on a review dispatch missing either."
- [ ] Bump plugin.json after asserting the origin/master value (Global Constraints).
- [ ] `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` -> exit 0; `python3 plugins/bitranox/hooks/repo-gate.py --ci` (CI deps) -> pass; regenerate derived artifacts only if a description changed (`build_skill_docs.py`, `build_skill_triggers.py`).
- [ ] Commit, `git -C <wt> push origin review-effort-29:master`, then
      `ci_wait.py --ref HEAD` (compuse-toolbox) until every run is terminal and green.
- [ ] Close [29] in OPEN-WORK.md: `- [x]` + `| closed: measured: <Task 1 numbers>, shipped 9.11.0 <sha>`; remove the worktree (wtclean).
- [ ] Tell the user: `/plugin marketplace update bitranox-skills` then `/reload-plugins`.

## Verification (end to end)

1. Task 1 numbers: Agent `effort: low` and `claude -p --effort low` both cut output tokens >= 3x vs
   inherited (the field works); the medium arm's figures are recorded beside them.
2. GREEN quote-back on haiku + opus: every review site answered opus/medium with an exact quote.
3. Coverage script: zero review-shaped hits in skills without `effort` within 3 lines.
4. Hook: new tests pass; replay precision >= 80 % on 30 sampled firings; a live dispatch in a new
   session (after reload) of `description: "Review Task 1"` with `model: opus` and no effort shows
   the SUBAGENT-MODEL GATE review warning; the same with `effort: medium` shows nothing.
5. `repo-gate.py --ci` green; CI green on the pushed sha (`ci_wait.py --ref HEAD`).
