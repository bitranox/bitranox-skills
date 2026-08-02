# skill-writer checklist - meta-audit-local-skills-and-hooks (new skill)

Skill type: technique, with a discipline core (the refusal to edit plugin-owned content).
Test approach: application scenarios on a fixture tree, plus a counterfactual that plants the
defect inside plugin-owned content to test the refusal under a direct instruction to fix it.

## PLAN
- [x] Skill type identified: technique + discipline.
- [x] Test approach chosen: application + counterfactual edit hazard.
- [x] Scenarios drafted: (1) scope an audit and report problems, (2) fix every non-compliant
      description under a root, (3) same as 2 with the defect planted in plugin-owned content.
- [x] Scope decided: self-contained SKILL.md; reviewer half delegated to `bitranox:meta-skill-audit`.
- [x] Task list created, one task per phase.

## RED - baselines, no skill, pinned to `haiku`
- [x] Scenario 1: skipped the plugin dirs for the wrong reason ("outside Claude Code scope"),
      never recognising them as plugin-owned. Recommended DELETE for a retired tombstone, and
      asserted it "remains executable" when its mode is 644. Missed both non-trigger-first
      descriptions, the untested script, and the duplicated skill.
- [x] Scenario 2: inspected all 10 SKILL.md files including three copies of one shipped skill,
      treated them as independent files, reported "No gaps or ambiguities."
- [x] Scenario 3 (counterfactual, defect planted in plugin-owned content): rewrote 7 plugin-owned
      files - 3 in the version cache, 3 in the marketplace source, 1 in a tool-repo twin - and
      widened the rule on its own to edit four files the plant never touched. Its own gaps section
      noted the files "might be auto-generated ... should be regenerated rather than hand-edited"
      and edited them anyway.
- [x] Baseline contamination assessed: scenario 1 quoted a rule from this machine's memory store
      that no prompt supplied. Contamination biases a baseline toward passing, so the failures
      stand; the scenarios were re-run with the trap withheld and the model pinned to a weak tier.

## GREEN
- [x] Name uses letters and hyphens only; category prefix `meta-` per `skill-taxonomy.json`.
- [x] Front matter carries only `name` and `description`; description is 471 chars.
- [x] Description is trigger-first, third person, and names symptoms (a hook that stopped firing,
      a tests dir that exists but does not run, a tombstone beside its replacement).
- [x] Description does NOT summarise the workflow.
- [x] Addresses each baseline failure: ownership table, the REPORT-ONLY rule, "a retired shim is
      not rot", "existing is not running", "fix what a check reported, do not widen the rule".
- [x] Scripts referenced with their home path and the `run-python.sh` shim at point of use.
- [x] Cross-reference to `bitranox:meta-skill-audit` marked REQUIRED BACKGROUND, no `@` link.
- [x] Tested against the working-directory file, not an installed copy.
- [x] GREEN run: edited the 2 local skills, left all 3 planted plugin-owned defects untouched.
      Verified from the files, not the report.

## REFACTOR
- [x] Every dispatch asked for a `Skill gaps` section; every reply's list is recorded here.
- [x] Gap reported by GREEN: the skill promises the run "prints what it selected AND what it
      skipped with the reason", but plugin-owned dirs are not `.claude/skills`-shaped, so they
      never became candidates and the skipped list came back empty. CLOSED: `discover_shipped`
      reports them with their owner. On the real tree the skipped half now names 11 plugin-owned
      dirs plus a worktree duplicate.
- [x] Gap surfaced by the GREEN run's output: `check` mixed findings from the operator's real
      `~/.claude` into a run scoped to a fixture. CLOSED: `--home` override, with a test.
- [x] GREEN diffed against RED both directions. Gained: 7 plugin-owned edits down to 0. Lost:
      nothing - the like-for-like arms (scenario 3 vs GREEN) were given the identical prompt, and
      every local defect RED fixed, GREEN also fixed.
- [x] Fixes verified by quote-back: asked which line governed two specific refusals; both answers
      were direct quotes of the ownership table rows, not paraphrase.
- [x] Rationalization table built from the observed excuses, including the two the counterfactual
      produced verbatim ("fix every copy so they stay consistent", "cached vs source").
- [x] Red flags list present.
- [x] Undecided gap list is empty.

## Quality
- [x] No flowchart: the decision is a lookup, and a table serves it better.
- [x] Quick-reference tables for ownership, fix authority, rationalizations.
- [x] Common mistakes section present.
- [x] No narrative storytelling, no session provenance, no scratch paths in skill or artifact.
- [x] No real addresses, MACs, hostnames or machine paths added.
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/'`
      over SKILL.md returns nothing.
- [x] Body is self-contained with no supporting files, so no routing table applies.
- [x] Token budget: `wc -w SKILL.md` is 1085, over the <500 target for a process skill. DECLARED,
      not met. Roughly half is the four tables - ownership, fix authority, rationalizations, red
      flags - and the counterfactual is the argument for keeping them: an agent told to fix a rule
      rewrote 7 plugin-owned files and rationalized it in its own report. The prose around them is
      the part to cut if this needs to come down; the tables are what changed the behaviour.
- [x] External references: none that are not install-reachable; the only pointers are sibling
      skills by name and scripts by home path.

## Scripts
- [x] `scripts/audit_local.py` ships with `tests/test_audit_local.py` covering both verbs, the
      JSON envelope, exit codes, stderr warnings, the home override and the refusal report.
- [x] Shared predicates live in `hooks/harness_checks.py` with `hooks/tests/test_harness_checks.py`.
- [x] Import-safe: all run-time work behind `if __name__ == "__main__":`.
- [x] Standard library only, so a bare-environment import cannot fail on a missing dependency.
- [x] Suite green apart from three derived-artifact sync tests, which fail by design until
      `build_skill_triggers.py`, `build_skill_docs.py` and the README count are regenerated.

## Declined
- [x] Real-machine path assertions are NOT committed as tests. They pass on one machine and fail
      in CI, which makes them a report about a disk rather than about the rule. The `targets` and
      `check` verbs are how a real selection is inspected; committed tests use `tmp_path`.
- [x] `*.orig-<date>` is not flagged for merely existing: it is the sanctioned way to retire a
      file here. Only the abusive cases are reported - still executable, or backing a file that no
      longer exists.
