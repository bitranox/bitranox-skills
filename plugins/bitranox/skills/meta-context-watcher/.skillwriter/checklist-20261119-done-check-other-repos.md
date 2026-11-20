# checklist - the done check for an item whose fix lands in other repos

Point 3 of "Before naming the next item" ("Check the line is not already done") now says that this
repo's history shows only work that landed here, and that for an item whose fix lands in other
repos (a sweep across member repos, a trim a template distributes) the check runs in each target
repo against `origin/<default branch>`: the same `git log`, or a `git grep -c` for the state the
item produces, read as "gone" only when `git cat-file -e` finds the file. A no-hit in the
backlog's own repo is no answer for such an item.

Decisions: d-20261119-9531f9de

## RED

- [x] Skill decisions read first: no rejected or removed entries; the live rule
      d-20261108-9e91bd5b (backlog-recommend-done-check) keeps its anchor and is extended, not
      superseded.
- [x] Text probe on the pre-edit point 3 (opus and haiku), scenario: a member-repo trim with no
      hit in the backlog's repo. Both reasoned their way to the member repos on their own; opus
      quoted "Which repository and which ref the step-3 commands run in: NONE" and listed "No
      repository or ref for step 3" as a skill gap. Same action, unsupported by the text: RED.
- [x] Corpus cascade (redcheck --corpus-cascade): clean, so the RED is not contaminated by a
      memory fact that already states the rule (weak evidence).

## GREEN

- [x] Text probe on the edited text (opus and haiku): both quoted "`no hit` in this repo alone is
      no answer for it" and ran the check per member repo against `origin/<default branch>`.
- [x] Commands the text names were run: `git grep -c` on a present heading prints
      `origin/master:CLAUDE.md:1` with exit 0, on an absent heading nothing with exit 1;
      `git cat-file -e` exits 0 on a present file, 128 on an absent one; `git grep` on an absent
      file exits 1, the same as an absent heading.
- [x] Final-text quote-back (haiku) after the guard and the reflow: Q1 quoted "This repo's history
      shows only work that landed HERE." and the no-answer sentence; Q2 named fetch, the default
      branch and the `git cat-file -e` guard; Q3 quoted the result-beside-recommendation line.

## REFACTOR

- [x] Closed (opus GREEN gap): "no output, exit 1: it is gone" also held for an untracked or
      deleted CLAUDE.md. The text now requires `git cat-file -e origin/<default branch>:<file>`
      to exit 0 before reading exit 1 as "gone".
- [x] Declined (opus, haiku): how to find the default branch - standard git
      (`git symbolic-ref refs/remotes/origin/HEAD`), not this skill's job.
- [x] Declined (opus): a peer's unpushed trim is invisible - "done" here means it reached origin;
      an unpushed sweep is not done.
- [x] Declined (opus): point 3 versus point 4 classification of such an item - point 4 decides
      where it is filed; the done check is independent of that and runs either way.
- [x] Declined (haiku): heading spelling, member list and count, the raised date - scenario input,
      not procedure.
- [x] Declined (haiku): which of `git log -S` and `git grep` governs when they disagree - a hit in
      either means "read the commit / state before offering", as the paragraph already says.
- [x] Width check on the added lines: none over 100 columns, no code span split across lines.

## Follow-up: the bare --since date

Decisions: d-20261119-add305f0

- [x] RED: three of the four point-3 probes (opus RED, opus and haiku GREEN) named the template's
      bare `--since=<raised date>` as a gap; their reports reached the dispatcher only later,
      relayed by the main session.
- [x] Measured: `git rev-parse --since=2026-11-19` resolved to that day at the time the command
      ran (00:14:34), `--since='2026-11-19 00:00'` to midnight.
- [x] GREEN: both templates now read `--since='<raised date> 00:00'`, with the reason beside them;
      no other skill's template uses a bare `--since=<...>` (grep over skills/*/SKILL.md).
