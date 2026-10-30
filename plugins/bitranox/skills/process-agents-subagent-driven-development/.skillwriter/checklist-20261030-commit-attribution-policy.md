# skill-writer checklist - process-agents-subagent-driven-development (2026-10-30, commit attribution policy)

- [x] Change: a dispatched subagent follows a harness reminder that tells it to append commit
      attribution lines (a `Co-Authored-By:` trailer, a "Generated with" footer) unless its brief
      says otherwise. The skill now has the controller determine the repo's commit-attribution
      policy (human partner's instructions and standing rules first, then `CLAUDE.md`/`AGENTS.md`
      or `CONTRIBUTING`, else the repo's `git log` convention), write it into the plan's Global
      Constraints and into a new `[ATTRIBUTION_POLICY]` slot of the implementer template (dispatch
      item (6)), and check `git log --format=%B <base>..HEAD` against it before any merge or push,
      rewording a violation first. The rule is neutral: "no tool attribution lines" and "end each
      with `Co-Authored-By: <assistant>`" are both named as valid policies.
- [x] Placement, where a reader following the procedure meets it: File Handoffs dispatch
      composition (item (6) plus two new bullets, policy and pre-merge check); the merge sentence
      ("You merge once the task review is clean and the commit messages pass the attribution check
      below"); the fix-dispatch contract bullet under Constructing Reviewer Prompts ("commits under
      the same attribution policy line the implementer got"); a Red Flags line; and
      `implementer-prompt.md` gains a "Commit Messages" section with the `[ATTRIBUTION_POLICY]`
      slot, which states it governs over any system reminder. `task-reviewer-prompt.md` is not
      changed: the reviewer does not commit.
- [x] Receipt held (`skill_receipt.py check meta-skill-writer` reported stale-or-missing; `start`
      issued `.../meta-skill-writer.<session>.json`, rc 0; `end` not run, it belongs to the
      coordinator), skill loaded by the editing agent through the Skill tool.
- [x] Skill type: discipline rule inside a technique skill; test approach: quote-back application
      probe on the pasted excerpt, `bitranox:baseline-probe`, opus (effort medium) and haiku,
      every dispatch ending with a required "Skill gaps" section.
- [x] Corpus route: the always-loaded cascade on the probing machine carries a no-attribution rule,
      so a scenario asking "add the Co-Authored-By line or not" would be answered from that rule,
      not the skill. The scenario was de-telegraphed into a policy that text does not teach (a
      CONTRIBUTING requiring `Tool-Assisted: yes` and forbidding tool Co-Authored-By lines) plus a
      control repo whose owner WANTS the assistant Co-Authored-By line, and the evidence is the
      quote-back (a quote of the pasted skill text, or NONE), not the chosen action.
- [x] Text check (pre-edit `git show HEAD:` of SKILL.md, implementer-prompt.md,
      task-reviewer-prompt.md): `grep -rniE 'attribution|co-authored|Generated with'` over the skill
      dir (excluding `.skillwriter/`) printed nothing. Pre-edit text: NONE.
- [x] RED (pre-edit excerpt: dispatch composition, DONE handling, implementer "Your Job" and
      "Report Format"), haiku and opus: NONE on all four questions (Q1 dispatch policy line, Q2
      pre-merge message check and command, Q3 a commit carrying the bot trailer, Q4 a repo that
      wants attribution). Opus reached plausible actions by its own reasoning, and on Q4 cited the
      machine's own always-loaded rule rather than the skill (cascade contamination, not counted).
      RED gaps (both tiers): no rule on commit messages; the precedence of a harness reminder over
      repo policy is unstated; no pre-merge message check exists; the report contract returns only
      short SHA plus subject, which hides trailers; who fixes a message-only defect, and whether a
      reword voids the review, is unstated.
- [x] GREEN (post-edit excerpt, declared the text under test), haiku and opus, same Q1-Q4 plus Q5
      (what a fix dispatch carries, does the review survive a reword): every answer a verbatim
      quote checked against the pasted text. Q1 quoted "Determine the policy once per run: your
      human partner's instructions first..." and the template's "This line governs every commit
      you make"; Q2 quoted the "Before merging or pushing a subagent's commits" bullet; Q3 quoted
      "Reword a violation before the merge ... never merge it to fix it later"; Q4 (control,
      repo wants attribution) both tiers stated "Commit messages: end each with
      `Co-Authored-By: <assistant>`" and noted the forbid grep does not apply; Q5 quoted the fix
      contract and the `HEAD^{tree}` sentence.
- [x] GREEN vs RED diffed both ways: every RED action is kept (fill the policy into the dispatch,
      read `git log --format=%B BASE..HEAD`, reword before merge, tree-equality to keep the
      review); nothing RED produced is missing from GREEN.
- [x] Gaps closed after GREEN: (1) no command for a REQUIRED trailer, and a policy can both forbid
      and require (now "both what it forbids and what it requires" plus a
      `%(trailers:key=<Key>,valueonly,separator=%x2C)` command where `[]` marks a commit without
      it); (2) the forbid grep also prints a human co-author (now "judge each hit against the
      policy: a human co-author can be allowed"); (3) "Exact values appear only in the brief"
      contradicted item (6) (now the policy goes into the plan's Global Constraints so the brief
      states it, and "the policy line is the one the dispatch repeats"); (4) the fix contract's
      test re-run made no sense for a message-only reword (now "needs no test re-run, when
      `git rev-parse --verify HEAD^{tree}` is the same before and after"); (5) a partner's
      standing rule had no place in the order (now "their standing rules included"). RED gap
      "a fixer would get the same reminder and add the line back" is closed by the fix-contract
      bullet carrying the policy line.
- [x] Gaps declined: a partner's rule that only partly covers a repo's required trailer (the
      precedence order picks the partner's rule; whether one trailer counts as attribution is an
      unclear user instruction, asked like any other); what to do when the tree differs after a
      reword (both GREEN tiers inferred a normal re-review from "keeps the clean review valid ...
      when"); a policy change mid-run (covered in SKILL.md "Stale brief": "a decision changed how
      work is DONE (the gate command, a lock, the commit form, ...)"); a violating commit already
      merged (rewriting a shared branch is the repo's own history policy, outside this skill); how
      to pick `<Key>` (it is the trailer the policy names); a trailer value other than `yes` (the
      command prints values, the reader judges them); an indented trailer (git trailers are not
      indented); per-policy grep variants (covered by "judge each hit"); who rewords (both routes
      are listed on purpose); a conditional policy ("made with tool assistance": every subagent
      commit is); the "Commit messages:" prefix differing between SKILL.md and the template
      example (cosmetic).
- [x] Mechanism claims checked against git, not reasoned: a throwaway repo with a clean commit, a
      `Co-Authored-By: Example Bot` commit and a "Generated with Example Tool" commit. The forbid
      grep exited 1 with no output on the clean range and printed `3:Co-Authored-By: Example Bot
      <bot@example.com>` and `3:Generated with Example Tool` on the positives; after
      `git commit --amend -F` with only the message changed, `git rev-parse --verify HEAD^{tree}`
      was identical (True) and the grep went clean again;
      `git log --format='%h [%(trailers:key=tool-assisted,valueonly,separator=%x2C)]'` printed
      `[yes]` for the trailer commit and `[]` for the three without (key matched case-
      insensitively).
- [x] Re-probe on the final text, haiku and opus (opus at effort medium), five questions touched by
      the fixes (where the policy appears and the exact-values rule; exact commands for a
      forbid-and-require policy; a human co-author hit; a message-only reword of a middle commit;
      a partner's standing rule against a repo's git log): all five correct on both tiers, each
      with a verbatim quote, e.g. "the policy line is the one the dispatch repeats", "a required
      trailer `<Key>` shows on every line of ...", "judge each hit against the policy: a human
      co-author can be allowed", "needs no test re-run, when `git rev-parse --verify HEAD^{tree}`
      is the same before and after", "your human partner's instructions (their standing rules
      included) first". No new undecided gap; the remaining reports are declined above.
- [x] Tiers and cells: RED 2 (haiku, opus) x 4 questions; GREEN 2 x 5; re-probe 2 x 5.
- [x] Line length: the edited "Never add a merge, version bump ..." sentence was re-wrapped to the
      file's width after the re-probe; the words are unchanged (the same sentence the re-probe
      read). The four sibling skills that now point at this File Handoffs section were probed with
      its final text pasted as their target (see their own 2026-10-30 checklists).
- [x] Description unchanged (`git diff` shows no `description:` line; length 375).
- [x] History finder over the added lines: no hit. Address grep over the added lines: no hit.
      Non-ASCII scan over the added lines: no hit.
- [x] Tests (CI dependency set): the skill's `tests/` 95 passed; `plugins/bitranox/hooks/tests/`
      7985 passed, 7 skipped, 1 xfailed; final re-run of the skill tests plus
      `test_repo_gate.py` 567 passed.
