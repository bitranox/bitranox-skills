# skill-writer checklist - meta-self-improve (2026-11-06, ledger paths and the rejected entry's wording)

Three wording fixes to the ledger text in steps 2, 3b and 4:

- Step 3b: a dropped skill-targeted entry's `decision` is "the proposal, stated plainly" instead of
  "the proposal prefixed `Rejected:`", so one convention holds (`show` already prints `kind`).
- Step 2 and step 3b: `<plugin>` for the ledger commands is `<checkout>/plugins/bitranox`, with
  `<checkout>` defined as the marketplace checkout's root; step 3b's `add` command names that
  absolute path and says to run it with the checkout as the working directory (`add` finds the
  skills from the working directory's repo). Step 4's "Resolving `<plugin>`" says step 2's `show`
  and step 3b's `add` read the checkout when the session has one.
- Step 3b: the no-checkout sentence moves after "... duplicates another entry records nothing."

Decisions: none - wording fixes that make the existing entries d-20261106-f1d066f6 and d-20261106-0231555d say one thing; no rule added, removed or rejected

- [x] Receipt fresh; Step 0b `show meta-self-improve --kind rejected,removed --full` printed one
      live entry (d-20261106-4cb9268c); untouched. Both anchored sentences unchanged:
      `skill_decisions.py check` reports 0 findings.
- [x] Not mirrored (`repo-gate.py --mirrors`).
- [x] Each finding verified against the file first: the `Rejected:` prefix requirement was at
      step 3b; `<plugin>` was `plugins/bitranox` (relative) at step 2 and "the installed plugin
      directory" at step 4; the no-checkout sentence sat between the command and the field list.
- [x] Commands executed, placeholders substituted as the text defines them, in a throwaway
      detached worktree as `<checkout>` and a separate empty dir as the user project cwd:
  - step 2 `python3 <checkout>/plugins/bitranox/hooks/skill_decisions.py show compuse-toolbox
    --skill-dir <checkout>/plugins/bitranox/skills/compuse-toolbox --kind rejected,removed --full`
    from the user-project cwd: rc 0, three entries printed.
  - control, the old relative form `python3 plugins/bitranox/hooks/skill_decisions.py show
    compuse-git` from the user-project cwd: rc 2, "can't open file".
  - step 3b `add --from-file <file>` by absolute path with the checkout as cwd, a `rejected` entry
    whose `decision` is the plain proposal: rc 0, id printed, line appended in the throwaway
    worktree (removed afterwards).
- [x] Re-probe on the final text, haiku x1 (user project cwd elsewhere, checkout and installed
      copy at distinct paths, dropping a declined compuse-git proposal): substituted `<checkout>`
      in both commands, ran `add` with the checkout as cwd, wrote `"decision": "Tell agents to
      rebase instead of merge."`, and without a checkout wrote no entry and named it in the
      report. Gaps: `drop` syntax (covered in the same paragraph, `drop --match ... --reason ...`,
      outside the excerpt shown); whether a checkout elsewhere on disk counts (judgement left
      open); topic and tier choice (defined in meta-skill-writer Step 0b). No new undecided gap.
- [x] Width and fence check over the added lines printed nothing after rewrapping the step 4
      paragraph; ASCII only; history-phrase finder: no hit.
