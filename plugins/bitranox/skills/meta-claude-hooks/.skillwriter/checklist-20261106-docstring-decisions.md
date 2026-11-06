# skill-writer checklist - meta-claude-hooks (2026-11-06, a code decision lives in the module docstring)

`references/authoring.md` gains the section "Record a decision in the module docstring" (before
`## Security`): the `Decisions:` block form, the rule that each entry is pinned by a test that
fails when the decision is reverted (`Pinned by: none - <why>` otherwise), that code gets no
ledger file, and that the block and its tests are read before a matcher, rule or threshold
changes. A reversal is made only when the editor can say what met the entry's `Reopen if:`; the
replaced form stays as the entry's `Rejected:` line, and a decision recorded only in a commit is
recovered from that commit into the `Rejected:` line first. SKILL.md gains item 7 in "Before you
write a hook, answer these" pointing at that section, and the Authoring row of the routing table
names the block. Description unchanged.

Decisions: d-20261106-259b781f, d-20261106-a18893ae

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`); Step 0b `show meta-claude-hooks`
      (both forms) printed nothing: no ledger before this change.
- [x] Not mirrored: `repo-gate.py --mirrors` lists 12 pairs, neither skill among them (one DRIFT,
      `coding-python-layered-config`, unrelated to this change).
- [x] Skill type: technique; test is application - where a reason for re-tightening a matcher is
      recorded and what is read first.
- [x] Inherited-coverage check: `redcheck --corpus-cascade` over the scenario reported one hit
      (shared terms "matcher, months, search, tightening"); the named document states nothing
      about a docstring decision block (grep for `docstring.{0,40}decision|decisions:` over the
      cascade files: no match), so the hit is ordinary-word overlap and the behavioural RED stands.
- [x] RED (opus x2, pre-edit SKILL.md loaded from the installed copy, byte-identical to HEAD, plus
      the authoring.md headings and its dependency section). Scenario: "You are tightening a
      hook's matcher. A git log search shows the same matcher was loosened four months ago. Where
      do you record why you are tightening it, and what do you check first?" Both put measurement
      notes in the module docstring, following the existing line "Record the per-arm figures in
      the hook's docstring and its CHANGELOG entry", but in free form with no `Decisions:` heading,
      no `Reopen if:`, no `Pinned by:` test, and one wrote history into it ("History: loosened in
      <full sha> ... "). Neither read an existing decision record first; both read the loosening
      commit with `git show` and said "the skill has no line telling me to read a previous change
      to the same rule". Gaps both reported: no guidance on the history of a rule; where the record
      goes for a matcher in `hooks.json`, which takes no comments.
- [x] GREEN target text executed: none to run - the edit adds a docstring template, no command.
- [x] GREEN (opus x2 with the pasted edited text, haiku x1 with the excerpt only). All three: first
      check "read the `Decisions:` block in the module docstring and the tests it names"; then the
      loosening entry's `Reopen if:` ("is made only when you can say what met its `Reopen if:`");
      wrote a `Decisions:` entry with `Why:`, `Evidence:`, `Reopen if:` and `Pinned by:` naming a
      still-matches test and a no-longer-matches test, plus a `Rejected:` line for the loosened
      form; hooks.json case answered by quoting the new sentence.
- [x] RED-to-GREEN diff, both directions: the opus GREEN arms kept every RED check (Step 0
      freshness, exact-vs-regex matcher, control arm, firing-set diff, per-arm split); the commit
      message stays, now as a pointer. The haiku arm saw only the excerpt, so the replay steps it
      did not list are outside what it was shown, not a loss.
- [x] Gaps from GREEN, decided:
  - CLOSED (all three arms): what to do when the decision being reversed has no entry (only git
    records it), and what becomes of the replaced form. Added: "The form you replaced stays in the
    block as that entry's `Rejected:` line. When the decision you reverse has no entry (...),
    recover its reason from that commit and the tests it added, write it into the `Rejected:`
    line naming the commit as its source, and reverse it only when you can say why that reason no
    longer holds."
  - DECLINED: whether an entry with `Evidence: user` needs the user to reverse it - a case the
    user has not ruled on for code; the text stays silent and the existing reopen rule governs.
  - DECLINED: figures in both the docstring and the CHANGELOG versus "no number appears in both
    places" - that sentence (SKILL.md:269) compares the hook docstring with the skill section,
    and SKILL.md:192 asks for the per-arm figures in docstring and CHANGELOG; this edit only names
    `Evidence:` as their place in the docstring and changes neither line.
  - DECLINED: several tests in one `Pinned by:`, test path prefix, RED-first ordering, replay
    procedure - the block form stays verbatim across the repo; the replay method is the
    escalation section of SKILL.md, which the new text points at.
- [x] Re-probe on the final text (haiku, scenario with no `Decisions:` block yet): quoted "The form
      you replaced stays in the block as that entry's `Rejected:` line" and "write it into the
      `Rejected:` line naming the commit as its source"; read the docstring, then the loosening
      commit and its tests; wrote both lines with `Pinned by:` naming a rejects test and a
      still-matches test. New gaps, all DECLINED: the tier for a reason recovered from a commit
      (`inherited` is in the template's tier list), no separate source field on a `Rejected:` line
      (the commit is named in its `Why:` text), which test is "the behaviour you replaced" when no
      entry names tests (the loosening commit's tests, as the new sentence says), test command
      (repo CLAUDE.md owns it). No new undecided gap.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion point (`## Security`, "## The five that bite hardest") read for re-bound
      references: none. ASCII only; history finder: two hits, both "no longer holds" about a
      reason, not version history.
- [x] Anchor "Pin each decision with a test that fails when the decision is reverted" occurs once
      in the skill's Markdown (whitespace-normalised count: 1); `skill_decisions.py check
      meta-claude-hooks` exits 0.
- [x] Tiers: RED opus x2; GREEN opus x2 + haiku x1; final re-probe haiku x1.
