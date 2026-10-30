# skill-writer checklist - process-agents-dispatching-parallel (2026-10-30, commit attribution policy)

- [x] Change: Step 2 ("Each agent gets") gains a bullet: every agent that may commit gets the
      repo's commit-attribution policy, stated as the line that governs over any harness reminder
      to add or omit attribution lines, with a pointer to
      bitranox:process-agents-subagent-driven-development, File Handoffs, for where the policy
      comes from and the checks. Verification item 7's commit-message sentence changes from "Grep
      ... for trailers the brief forbade (such as an attribution line)" to a check of
      `git log --format=%B <base>..HEAD` against the policy the brief stated, both what it forbids
      and what it requires, plus any other forbidden trailer, rewording a violation before pick,
      merge or push. The rule is neutral: the skill names no policy of its own.
- [x] Receipt held (`skill_receipt.py check meta-skill-writer`: fresh), skill loaded by the editing
      agent through the Skill tool.
- [x] Text check on the pre-edit file (`git show HEAD:`): one mention, the item 7 grep "for
      trailers the brief forbade (such as an attribution line)"; nothing tells the dispatcher to
      put a policy into the brief.
- [x] RED (pre-edit excerpt: the Step 2 list and item 7; one combined probe over four skills,
      haiku, scenario: CONTRIBUTING requires `Tool-Assisted: yes` and forbids tool Co-Authored-By
      lines, while every subagent's harness reminder adds `Co-Authored-By: Example Bot`): Q1 (what
      the brief says about the policy) NONE; Q2 quoted item 7's grep and flagged it: "this check
      only catches trailers the brief forbade. If the brief never forbade Co-Authored-By, the grep
      is clean even with the bot trailer present. Nothing checks for the required Tool-Assisted:
      yes trailer."
- [x] GREEN (post-edit excerpt plus the SDD File Handoffs bullets it points at, declared the text
      under test), haiku and opus (effort medium): Q1 both quoted "The repo's commit-attribution
      policy, for every agent that may commit, stated as the line that governs over any harness
      reminder ..." and wrote a brief line requiring `Tool-Assisted: yes` and forbidding tool
      Co-Authored-By lines; Q2 both quoted the new item 7 sentence and gave the forbid grep plus
      the `%(trailers:key=Tool-Assisted,...)` command from the SDD section. Every quote checked
      against the pasted text.
- [x] GREEN vs RED both ways: RED's forbid-trailer grep is kept inside the new sentence ("grep it
      for any other trailer the brief forbade"); nothing RED produced is missing.
- [x] Gaps declined: the required-trailer command prints the value and the reader judges it (the
      opus arm required `[yes]` on every line unprompted); a "generated with" hit in prose is
      covered in the SDD section ("judge each hit against the policy"); how to substitute the
      trailer key (it is the trailer the policy names); reword mechanics (owned by
      bitranox:compuse-git); a workspace standing rule conflicting with a repo policy (the SDD
      order puts the human partner's standing rules first, and the probe's citation of a
      machine-local rule is cascade context, not skill text).
- [x] Tiers and cells: RED 1 (haiku) x 2 questions; GREEN 2 (haiku, opus) x 2 questions.
- [x] Added lines: no history-finder hit, no address or home path, ASCII only; description
      unchanged.
- [x] Tests: this skill ships no scripts; the hooks suite and the touched skills' tests ran green
      (counts in the report).
