# skill-writer checklist - git-worktrees (20261116, isolation worktree of the wrong repository)

- [x] Decisions: d-20261116-583eedae

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing for this skill; the live
      rules were read; no entry touched.
- [x] Premise check: Step 1a covered the BASE an isolation worktree takes, never which
      REPOSITORY it belongs to. The Agent tool used for this edit has no `cwd` parameter, which
      the existing text ("where the tool offers that parameter (not every build does)") already
      allows for, so the new paragraph keeps that hedge. This skill is the rule's one home;
      bitranox:process-agents-dispatching-parallel points here.
- [x] RED: text-only probe (`bitranox:baseline-probe`, `opus`) over the pre-edit Step 1a asked
      which repository `isolation: "worktree"` gives a subagent sent to work in a sibling repo, and
      what to do instead. Answer: NONE for the repository ("That implies the session's own
      repository, but the text never says so").
- [x] GREEN: same question over the new text, `opus` and `haiku`, 2 cells. Both quoted "never of
      the repository the task is about" and the omit-isolation remedy.
- [x] Neighbouring text made consistent: Step 1a's "the one case where `git worktree add` beside
      a native tool is right" and the Red Flags line "The one exception" now name both cases.
- [x] Gaps from GREEN, decided: which ref the other repo's worktree branches from (declined:
      covered by the base-branch text earlier in Step 1a); who removes it afterwards (declined:
      covered by Steps 4 and 5); which of the two remedies to prefer (declined: `cwd` exists only
      in some builds, so the choice follows the tool in hand).
- [x] The pointer from bitranox:process-agents-dispatching-parallel quotes this paragraph's bold
      lead; a `haiku` re-probe found it from the pointer.
- [x] Width and fence check over the added lines printed nothing; ASCII only; no description
      change.
