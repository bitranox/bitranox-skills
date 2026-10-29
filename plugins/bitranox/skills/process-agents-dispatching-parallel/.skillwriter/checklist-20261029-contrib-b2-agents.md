# Review: queued contributions folded into process-agents-dispatching-parallel

Text checks against SKILL.md: RED = the text at HEAD lacks the rule (grep), GREEN = the edited
text states it (quoted). No behavioural probe arms were run for this batch.

- [x] Description unchanged: `git diff HEAD -- SKILL.md | grep -c '^[-+]description:'` prints 0.
- [x] Not mirrored to a tool repo: `repo-gate.py --mirrors` lists no `process-agents-*` pair.
- [x] Destructive git steps in a lane brief. RED: `destructive` matches nothing. GREEN: "**Keep
      destructive steps out of lane briefs.** ... makes the auto-mode permission classifier
      refuse the WHOLE dispatch (`[Git Destructive]`)".
- [x] Report path for a worktree-isolated lane. RED: `isolation` matches nothing. GREEN: "An agent
      dispatched with `isolation: worktree` cannot write to the MAIN checkout ... Name a path
      inside its own worktree or in the session scratchpad".
- [x] Usage-limit stop of the whole fan-out. RED: the existing paragraph said only to finish
      stopped items from git, because a resume "can be days away". GREEN: two branches, "Hours
      away ...: resume each stopped agent with SendMessage" and "Days away, or the work cannot
      wait: finish the item yourself from git", plus the brief item "A per-item progress record,
      when an agent works a list".
- [x] Analyser line numbers. RED: `line number` matches nothing. GREEN: "Locate every finding by
      the TEXT it quotes, never by its line number alone."
- [x] ASCII only in every added line; no table touched.
