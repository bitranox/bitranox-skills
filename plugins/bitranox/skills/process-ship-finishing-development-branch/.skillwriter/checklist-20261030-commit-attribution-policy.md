# skill-writer checklist - process-ship-finishing-development-branch (2026-10-30, commit attribution policy)

- [x] Change: Step 3 gains a paragraph run before a merge or a push (Options 1 and 2): read
      `git log --format=%B <merge-base>..HEAD` and check each message against the repo's
      commit-attribution policy, both what it forbids and what it requires; attribution lines are
      forbidden by some repos and required by others, and a harness reminder can add them whatever
      the repo says; the policy source and the forbid/require commands are pointed at
      (bitranox:process-agents-subagent-driven-development, File Handoffs); a violation is
      reworded before Step 5. This skill dispatches no agent, so it has no brief to carry the
      policy; its share of the rule is the finish-time check.
- [x] Receipt held (`skill_receipt.py check meta-skill-writer`: fresh), skill loaded by the editing
      agent through the Skill tool.
- [x] Text check on the pre-edit file (`git show HEAD:`): `grep -ciE
      'attribution|co-authored|generated with'` printed 0.
- [x] RED (pre-edit excerpt of Step 3 and the option list; one combined probe over four skills,
      haiku, scenario: CONTRIBUTING requires `Tool-Assisted: yes` and forbids tool Co-Authored-By
      lines, a harness reminder adds `Co-Authored-By: Example Bot`): Q2 (what is checked about
      commit messages before merge or push) NONE: "No step inspects commit messages before merge
      or push."
- [x] GREEN 1 (post-edit excerpt plus the SDD File Handoffs bullets, declared the text under test),
      haiku and opus (effort medium): both quoted the new paragraph and ran the forbid grep and the
      `Tool-Assisted` trailer command over `<merge-base>..HEAD`. Control Q3 (a repo whose owner
      REQUIRES `Co-Authored-By: <assistant>`): both said a commit carrying it is compliant. Opus
      reported a defect: the first wording put the attribution examples in parentheses after "what
      it forbids", which reads as the policy and pushes toward stripping a required line.
- [x] Fix: the examples moved out of the "forbids" clause into a neutral sentence, "Attribution
      lines (a `Co-Authored-By:` trailer, a "Generated with" footer) are forbidden by some repos and
      required by others".
- [x] Re-probe on the final text, haiku and opus (effort medium): Q1 (repo requires the
      assistant trailer, three commits carry it) both: no violation, strip nothing, quoting "are
      forbidden by some repos and required by others"; Q2 (a forbidden "Generated with" footer)
      both quoted "Reword a violation before Step 5; never merge or push it to fix later". No new
      undecided gap.
- [x] Gaps declined: the policy text and commands live in the SDD section the paragraph points at
      (a pointer by design, not a copy); Options 3 and 4 neither merge nor push, so no check
      applies; `<merge-base>` is the value Step 3 just computed; reword mechanics (owned by
      bitranox:compuse-git); the Step 3 main/master fallback order is pre-existing and Step 3
      already says to ask when unsure; a workspace standing rule against a repo's required trailer
      (the SDD order puts the human partner's standing rules first; the probe's citation of a
      machine-local rule is cascade context, not skill text).
- [x] Tiers and cells: RED 1 (haiku) x 2 questions; GREEN 2 (haiku, opus) x 3; re-probe 2 x 2.
- [x] Added lines: no history-finder hit, no address or home path, ASCII only; description
      unchanged.
- [x] Tests: this skill ships no scripts; the hooks suite and the touched skills' tests ran green
      (counts in the report).
