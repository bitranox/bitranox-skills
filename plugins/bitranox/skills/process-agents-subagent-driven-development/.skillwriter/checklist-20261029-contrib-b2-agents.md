# Review: queued contributions folded into process-agents-subagent-driven-development

Scope: SKILL.md, implementer-prompt.md, scripts/task_brief.py (with tests), and three new
reference files. Rule edits are text checks against the skill files (RED = the pre-edit text at
HEAD lacks the rule, GREEN = the edited text states it, quoted back below). No behavioural probe
arms were run for this batch; the evidence is the text check of the artifact.

## Frontmatter

- [x] Description unchanged: `git diff HEAD -- SKILL.md | grep -c '^[-+]description:'` prints 0.
- [x] Not mirrored to a tool repo: `repo-gate.py --mirrors` lists no `process-agents-*` pair.

## Script (task_brief.py)

- [x] RED: 5 new tests failed on the pre-fix script, e.g.
      `AssertionError: assert 'body two-one-b' in ''` (id 2.1b read as 2) and
      `assert ('### P1 - privacy scan' in '## Global Constraints\n\n* gc line\n\n### Task 2.1: ...')`.
- [x] GREEN: `tests/` 93 passed (task_brief, review_package, sdd_scripts).
- [x] Bites: restoring only the old id regex fails the two dotted-id tests; restoring only the
      old title rule fails `test_a_milestone_that_opens_a_plan_without_a_title_is_still_carried`.
- [x] Existing behaviour kept: every pre-existing test_task_brief.py test passes unchanged
      (template plans, flat plans, duplicate ids, plans without Global Constraints).

## Rules (RED by grep over HEAD, GREEN by quote)

- [x] Unfilled placeholder before dispatch. RED: `placeholder` matches only the reviewer's
      "**Placeholders:**" rubric. GREEN: "an unfilled placeholder token (`EXCERPT_PLACEHOLDER`,
      `[BRIEF_FILE]`, `<paste here>`) left from a template or an earlier dispatch".
- [x] Plan without Task headings. RED: no text on restructuring a plan; the script only said
      "no heading matching 'Task 1'". GREEN: "Restructure the PLAN first, content unchanged: the
      decisions, measured facts and design under `## Global Constraints`, one
      `### Task <id>: <name>` heading per task." The script's exit-1 message says the same.
- [x] Relayed or forwarded claims. RED: `relay|unmeasured` match nothing on this topic. GREEN:
      "check its premise with one direct read or probe. If you cannot, carry it labelled:
      \"unmeasured, from the Task 3 report\"."
- [x] Plan mode switched on mid-run. RED: the only plan-mode text covers dispatching before it
      ends. GREEN: "List them in the ledger, leave their checkouts untouched, and after approval
      resume each by SendMessage as Phase 0 of the new plan".
- [x] Merge/release kept out of implementer briefs. RED: no such rule (`merge|release` hits are
      about review packages and the final review). GREEN: "Never add a merge, version bump,
      release or build step to an implementer or fixer dispatch", plus a Red Flags line.
- [x] Restriction that names a file. RED: `names a file|file list|diff stat` match nothing.
      GREEN: "When the restriction NAMES A FILE and says what it holds ... read that file too".
- [x] New or tightened refusal. RED: `refusal|lenien` match nothing. GREEN: "**A task that ADDS
      or TIGHTENS a refusal** ... Name each one in the task's Files list".
- [x] Two remedies, one changing released behaviour (implementer-prompt.md). RED:
      `released|operator-visible` match nothing. GREEN: "report NEEDS_CONTEXT naming both
      remedies, and do not pick". mutation_arm was already named; the line now adds "rather than
      a mutation runner of your own".
- [x] Borrowed resource cleanup. RED: `borrowed|cleanup recipe` match nothing. GREEN: "write the
      cleanup recipe into the ledger BEFORE dispatch, and treat any non-success notice from that
      agent as \"take over the cleanup now\"".
- [x] Untracked CLAUDE.md in a worktree. RED: no `ls-files` text in this skill. GREEN: "check with
      `git ls-files --error-unmatch CLAUDE.md` and, when it is not tracked, give the main
      checkout's absolute path instead".
- [x] Usage-limit stop of a review. RED: `429|usage limit` match nothing in this skill. GREEN:
      "A review you do inline meanwhile is a logged deviation, never the gate".
- [x] Re-arm the model gate in a resumed session. RED: no text on the receipt being per session.
      GREEN: "a session that resumes a plan after a handover, `/clear` or restart, or a run past 8
      hours, runs `start` again before its next dispatch".
- [x] User decisions quoted verbatim. RED: `USER-DECISIONS` matches nothing. GREEN: "generate
      the brief with `task_brief.py PLAN_FILE N --decision "<text>"` (repeatable, one per
      decision)". Script: 9 new tests failed on the script without the flag (`assert 2 == 0`:
      the old parser refused the extra arguments), 93 passed after. Bites: accepting the first of several matches
      fails the ambiguity test; reading the log from the cwd instead of the main checkout root
      fails the linked-worktree test. The location comes from hooks/user-decision-log.py
      (`main_checkout_root`, `LOG_NAME`), loaded by path; tests read fixture files only.

## Mechanism claims checked against code

- [x] `skill_receipt.py check <name>` exits 0 fresh / 1 stale, TTL 8 h, keyed per session:
      hooks/skill_receipt.py docstring and `TTL_SECONDS = 8 * 3600`.
- [x] `USER-DECISIONS.jsonl` sits at the main checkout root: hooks/user-decision-log.py
      `log_path()`.
- [x] `mutation_arm --mutate` exists: `mutation_arm.py --help`.

## Structure

- [x] SKILL.md shrank from 720 to about 680 lines although 13 rules were added: the worked
      example and trade-offs moved to references/example-workflow.md, the effort-channel and
      session-model harness detail to references/model-tiers.md (both sections keep their
      headings, which other skills cite by name), and interruption procedures live in
      references/interrupted-runs.md behind a short "Interrupted Runs" section.
- [x] Routing table lists all three references, with "Use the Read tool" above it.
- [x] `test_model_tiers.py` passes (no new tier wording); tables reformatted with
      reformat_tables.py; ASCII only in every added line.
