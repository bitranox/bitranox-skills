# skill-writer checklist - process-agents-dispatching-parallel (20261116, nested dispatch wait)

- [x] Decisions: d-20261116-76d1bd25

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing for this skill; no entry
      touched.
- [x] Premise check: the brief list's FOREGROUND bullet covers a wait for CI or a gate only;
      nothing covered an agent that dispatches agents of its own. The new bullet sits next to it.
      The base bullet gains a one-line pointer to the wrong-repository rule, whose home is
      bitranox:git-worktrees Step 1a.
- [x] Related skill checked, report only: bitranox:meta-skill-writer says nothing contrary about
      probe dispatch (no foreground or background guidance for probes there).
- [x] RED: text-only probe (`bitranox:baseline-probe`, `opus`) over the pre-edit excerpts asked
      what a brief must say about probe agents a background subagent dispatches, and what happens
      to their reports if its turn ends first. Answer: NONE to both.
- [x] GREEN: same question over the new text, `opus` and `haiku`, 2 cells. Both quoted "wait for
      every agent you dispatch before you end your turn." and the hand-back consequence.
- [x] Gaps from GREEN, decided: whose name to forward to (closed: "to the agent that dispatched
      that probe, by the name you gave it"); the pointer cited a phrase that is not a heading
      (closed: it quotes the paragraph's bold lead); whether SendMessage wakes an agent that has
      ended its turn, and how long a failed hand-back is retried (declined: not measured, and the
      rule is to keep the turn open so neither arises).
- [x] Re-probe of the touched sentences on the final text, `haiku`: quoted the forward rule with
      "by the name you gave it" and found the pointer's quoted phrase as the bold lead of the
      target paragraph; no new undecided gap.
- [x] Width and fence check over the added lines printed nothing; ASCII only; no description
      change.
