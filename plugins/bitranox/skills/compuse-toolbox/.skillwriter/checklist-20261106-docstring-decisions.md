# skill-writer checklist - compuse-toolbox (2026-11-06, a jig decision lives in the module docstring)

"Building or enhancing a jig" gains the `Decisions:` block form for a jig's module docstring, the
rule that each entry is pinned by a test that fails when the decision is reverted
(`Pinned by: none - <why>` otherwise), that code gets no ledger file, and that the block and its
tests are read before a jig's matcher, rule or threshold changes. A reversal is made only when the
editor can say what met the entry's `Reopen if:`; the replaced form stays as the entry's
`Rejected:` line, and a decision recorded only in a commit is recovered from that commit into the
`Rejected:` line first. Nothing else changed; description unchanged.

Decisions: d-20261106-8590cd34, d-20261106-a18893ae

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`); Step 0b `show compuse-toolbox`
      (both forms) printed nothing: no ledger before this change.
- [x] Not mirrored: `repo-gate.py --mirrors` lists 12 pairs, compuse-toolbox not among them.
- [x] Skill type: technique; test is application - where a reason for re-tightening a jig's
      matcher is recorded and what is read first.
- [x] Inherited-coverage check: `redcheck --corpus-cascade` hit one document on the ordinary words
      "matcher, months, search, tightening"; the cascade states nothing about a docstring decision
      block (grep: no match), so the behavioural RED stands.
- [x] RED (opus x2, pre-edit skill loaded from the installed copy, byte-identical to HEAD).
      Scenario: "You are tightening a hook's matcher (here: the pattern a jig uses to decide which
      commands it matches). A git log search shows the same matcher was loosened four months ago.
      Where do you record why you are tightening it, and what do you check first?" Neither put
      the reason in the module docstring: both chose test docstrings, an inline comment at the
      pattern, the commit message ("This is where the history and the measurement belong") and a
      CHANGELOG line. Neither looked at the module docstring first; both read the loosening commit
      and reported "Nothing on consulting history" and "No place to record a reason" as gaps.
- [x] GREEN target text executed: none to run - the edit adds a docstring template, no command.
- [x] GREEN (opus x2 with the pasted edited section, haiku x1 with the section only). All three:
      first check quoted "Read the block, and the tests it names, before you change a jig's
      matcher, rule or threshold."; then the entry's `Reopen if:`; wrote a `Decisions:` entry with
      `Why:`, `Evidence:`, `Reopen if:` and `Pinned by:` naming a no-longer-matches test and a
      still-matches test, plus a `Rejected:` line; commit message demoted to a pointer, quoting "a
      commit message alone is no record".
- [x] RED-to-GREEN diff, both directions: the opus GREEN arms kept the RED checks (guard_replay
      over real history, RED test first, `mutation_arm --revert` to prove the pin); the inline
      comment at the pattern moved into the docstring entry, which now holds that reason. The
      haiku arm saw only the section, so the tool steps it did not list are outside what it was
      shown, not a loss.
- [x] Gaps from GREEN, decided:
  - CLOSED (all three arms): what to do when the decision being reversed has no entry, and what
    becomes of the replaced form - the sentences "The form you replaced stays in the block as
    that entry's `Rejected:` line" and "recover its reason from that commit and the tests it
    added, write it into the `Rejected:` line naming the commit as its source".
  - DECLINED: reversing an entry with `Evidence: user` without the user - not ruled on for code;
    the text stays silent.
  - DECLINED: how to measure a matcher change and how to prove a pin fails on revert - the Tools
    table already routes both (`guard_replay` row, SKILL.md:92; `mutation_arm --revert`,
    SKILL.md:90).
  - DECLINED: several tests in one `Pinned by:`, a gate jig's match direction - judgement per
    jig; the block form stays verbatim across the repo.
- [x] Re-probe on the final text (haiku, scenario with no `Decisions:` block yet): quoted "recover
      its reason from that commit and the tests it added, write it into the `Rejected:` line
      naming the commit as its source" and "The form you replaced stays in the block as that
      entry's `Rejected:` line"; read the docstring, then the commit and its tests, then decided
      whether the reason still holds; wrote both lines with two pinning tests. New gaps, all
      DECLINED: backfilling an entry for the current behaviour (the new entry is that entry), how
      to measure (Tools table), "git's job" beside naming the commit (the commit is the source of a
      recovered reason, not a history narrative). No new undecided gap.
- [x] Width and fence check over the added lines printed nothing (one 174-column line found and
      rewrapped before the re-probe); the section is the file's last, so no paragraph follows the
      insertion. ASCII only; history finder: one hit, "no longer holds" about a reason, not
      version history.
- [x] Anchor "Pin each decision with a test that fails when the decision is reverted" occurs once
      in the skill's Markdown (whitespace-normalised count: 1); `skill_decisions.py check
      compuse-toolbox` exits 0.
- [x] Tiers: RED opus x2; GREEN opus x2 + haiku x1; final re-probe haiku x1.
