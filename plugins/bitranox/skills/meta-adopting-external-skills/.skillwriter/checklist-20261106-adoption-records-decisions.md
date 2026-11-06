# skill-writer checklist - meta-adopting-external-skills (2026-11-06, an adoption records what it left out)

Step 4 gains a closing paragraph: before the adoption commit, record the adoption's decisions in
the new skill's ledger - a `rejected` entry for each upstream part Step 3 deliberately left out
and an anchored `rule` entry for each house rule Step 3 added that upstream does not have. From
the checkout root, `git add` the new skill directory, write the entries to a JSON file, run
`python3 plugins/bitranox/hooks/skill_decisions.py add --from-file <file>`, put the printed ids on
the Step 3 checklist's `Decisions:` line (`Decisions: none - <reason>` when nothing was decided),
then `git add` the ledger and the checklist for the adoption commit. It also names the fields an
entry carries and says what guards a later re-sync. Description unchanged.

Decisions: d-20261106-4e1cc697

- [x] Receipt fresh (`skill_receipt.py check meta-skill-writer`); Step 0b `show
      meta-adopting-external-skills --kind rejected,removed --full` and plain `show` printed
      nothing (no ledger before this change).
- [x] Not mirrored: `repo-gate.py --mirrors` lists 12 pairs, this skill not among them (the one
      DRIFT, `coding-python-layered-config`, is unrelated to this change).
- [x] Skill type: technique; test is application - what an adopter records at Step 4 so a later
      upstream sync does not undo the adoption.
- [x] Inherited-coverage check: `redcheck --corpus-cascade .` exit 1, one hit on the tree-top
      CLAUDE.local.md through ordinary words (adopted, deliberately, durable, house, marketplace,
      months); that file states nothing about recording an adoption's decisions, so a false
      positive. The repo CLAUDE.md describes the ledger in general but never ties it to an
      adoption. Behavioural RED kept, plus a text check: the pre-edit SKILL.md (`git show HEAD:`)
      mentions `skill_decisions`, `decisions.jsonl`, `reopen_if` and "ledger" zero times (its one
      "REJECTED" is the license gate's verdict). Installed copy byte-identical to HEAD.
- [x] RED, pre-edit text pasted, opus x2. Scenario: an upstream section on auto-committing was
      removed in Step 3; six months later upstream changes and the skill is re-synced - what
      stops the section coming back? Both: "Going by the excerpt, nothing does" / "Under the
      skill as written, nothing does." Neither named any ledger; both improvised a regression
      test and a `Modified:` / `Local changes:` notice field, quoting NONE for each. RED.
- [x] Commands the edit adds were executed in a throwaway detached worktree of the repo, with a
      demo skill directory: `add --from-file` with a rejected and an anchored rule entry before
      `git add` -> refused "anchors: must occur exactly once in the skill text, found 0 ...
      (untracked files are not read: git add them first)", rc 1; after `git add` of the skill
      directory -> "demo-adopted: d-..., d-...", rc 0; `git add` of the written
      `.skillwriter/decisions.jsonl` and the checklist -> rc 0, both staged; `check demo-adopted`
      -> "checked 1 ledger(s), 0 finding(s)", rc 0.
- [x] GREEN, edited text pasted, opus x2 + haiku x1 (three cells). Scenario A: adopt as
      `process-tidy-commits`, an auto-commit section removed, a pre-push sentence added. All three:
      `git add plugins/bitranox/skills/process-tidy-commits`, a JSON array with a `rejected` entry
      (anchors `[]`) and a `rule` entry anchored on the added sentence, every listed field present,
      then `python3 plugins/bitranox/hooks/skill_decisions.py add --from-file <file>`, ids onto the
      checklist line, the ledger staged. A2: the rejected entry is read under Step 0b; the commit
      gate refuses a dropped rule anchor. Control B (adoption that decided nothing): all three
      wrote no entries and ran no `add`, with a `Decisions: none - <reason>` line.
- [x] RED-to-GREEN diff, both directions: RED's improvised regression test and notice
      `Modified:` field were not taught by the old text and are not lost results; the Apache-2.0
      change notice they cite is already Step 1 ("record that you modified the files").
- [x] Gaps from GREEN, decided:
  - CLOSED: staging the ledger after `add` (all three inferred it) - now "then `git add` the
    ledger it wrote ... and the checklist".
  - CLOSED: the ids exist only after `add` (all three) - now "Put the ids `add` prints on the
    `Decisions:` line".
  - CLOSED: the zero-decision case (all three, the form came only from background) - now
    "(`Decisions: none - <reason>` when the adoption left nothing out and added no rule)".
  - DECLINED, covered elsewhere: JSON file shape - meta-skill-writer SKILL.md Step 0b, "the file
    holds one entry object or a list"; anchor shape and uniqueness - Step 0b "Picking an anchor:
    quote 20 to 200 characters ... unique in the skill's Markdown"; evidence tier and `reopen_if`
    meanings - Step 0b's tier list and field definitions, which the new text points at.
  - DECLINED, by design: a `rejected` entry is guarded by reading, not by a gate. The new text
    says exactly that ("Step 0b has its editor read the `rejected` entries first"); the edit
    guard also shows the list once (meta-skill-writer Step 0b, "The edit guard refuses an
    agent's first edit of a marketplace SKILL.md once, showing this list").
  - DECLINED, covered elsewhere: the ledger re-checked at commit - repo CLAUDE.md, "The commit
    and push gates refuse a change whose shipped text no longer contains a live `rule` entry's
    anchor"; `.skillwriter/` ships and is tracked - repo CLAUDE.md, "It ships with the skill,
    since `.skillwriter/` does".
  - DECLINED, outside this change: how a re-sync is performed. `adopt_skill.py` refuses an
    existing destination ("error: destination already exists", adopt_skill.py:1016-1017), so it
    cannot overwrite `.skillwriter/`; a re-sync procedure is not defined by this skill.
  - DECLINED, outside this change: a re-sync that keeps an anchor but adds contradicting text.
- [x] Gaps RED reported that predate this change, decided:
  - DECLINED, owned by the repo: the version bump touching `pyproject.toml` and the CHANGELOG
    heading, and regenerating derived artifacts - the repo CLAUDE.md governs both
    (`bump_version.py`, `check_version_sync`), and the gate Step 4 runs reports a stale artifact.
  - DECLINED, needs a user ruling: the Common mistakes line "Letting the helper or yourself
    commit, push, or uninstall anything" reads against "Adoption commits to that repo"; which
    commits the adopter may make is a policy decision this change does not take.
  - DECLINED, by design: Step 4 shipping the copy before Step 5 offers the change upstream is
    the skill's existing order; out of scope.
- [x] Re-probe on the final text (haiku, the questions the fixes touched): ids put on the
      `Decisions:` line, then `git add plugins/bitranox/skills/web-link-check/.skillwriter/
      decisions.jsonl plugins/bitranox/skills/web-link-check/.skillwriter/checklist-20261106.md`,
      quoting "Put the ids `add` prints on the `Decisions:` line"; the zero case writes
      `Decisions: none - ...` and runs no `add`; the dropped section is `rejected` with empty
      anchors. Its new gaps: JSON shape and tier definitions (declined above, Step 0b), commit
      command (owned by the repo), whether `add` runs on zero entries (it inferred "do not run",
      which is right: there are no entries to write), `git add` of the skill directory when no
      entry has an anchor (harmless, and the directory ships in the commit anyway). No new
      undecided gap.
- [x] Width and fence check over the added lines printed nothing (longest 100 columns); no
      non-ASCII in the file; history finder and private-path grep over the added lines: no hit.
      The text after the insertion is the Step 5 heading; no back-reference re-bound.
- [x] Ledger: one `rule` entry, tier `argued`, origin `authored`, anchored on "Record a
      `rejected` entry for each upstream part Step 3 deliberately left out";
      `skill_decisions.py check meta-adopting-external-skills`: "checked 1 ledger(s), 0
      finding(s)", rc 0.
