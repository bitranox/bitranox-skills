# Review checklist: process-agents-dispatching-parallel, stopped agent's output dirs (2026-10-31)

## Change

1. New brief item "An output directory for whatever does not land in git": name the directory a
   host-measuring lane writes to (example `evidence/<item>-<date>/` on the test host), so a
   recovery has a place to look.
2. "An agent that stopped mid-task left no report" extended in place, not duplicated: the heading
   now says the places its brief told it to write are the record; the section covers every way
   an agent stops (limit, stopped by you, idle without a report); the branch choice names the
   idle case (resume now) and the drifting case (finish it yourself); the recovery block gains
   `ls -la <evidence-dir>`; the measurement paragraph opens with "Recover from EVERY place the
   brief told it to write" and names the cost of a re-run (hours, host state that cannot be
   recreated).

## Claims and evidence

- [x] The skill already had a stopped-agent section; it was extended rather than paralleled.
      Grep for `stopped|idle|recover|evidence` before the edit found the section ("its worktree
      is the record") and one measurement paragraph naming "the evidence directory its brief
      named", but no brief item telling the dispatcher to name that directory.
- [x] The heading text is referenced nowhere else in `plugins/` except an older checklist
      (grep `left no report|worktree is the record`), so renaming it re-binds no pointer.
- [x] `ls -la <evidence-dir>` run against a fake evidence dir with one file: listed the file,
      rc 0. The "via ssh on a host" hint is prose, not a literal command; no ssh invocation was
      added (ssh form is owned by bitranox:compuse-ssh).
- [x] Width and fence check over the added lines (22) printed nothing; no non-ASCII; table
      formatter `--strict` reports Unchanged; front matter parses with `yaml.safe_load`
      (`name`, `description`).
- [x] Paragraph after each insertion read: after the brief item, "Keep destructive steps out of
      lane briefs" (unrelated, no re-bound reference); after the recovery block, "Compare that
      state with the item's brief" now also covers the evidence dir.

## Probes (bitranox:baseline-probe, haiku, excerpt pasted)

- [x] RED (pre-edit text): Q2 "what goes in the brief about measurement output" - "NOT COVERED
      for an explicit instruction". Q3 idle agent - "No usage limit was hit here, so the section
      on stopped agents does not apply". Gap: "worktree-recovery commands ... are written for
      usage-limit stops only".
- [x] GREEN (edited text): Q2 quoted "gets that directory named in its brief (for example
      `evidence/<item>-<date>/` on the test host)". Q3 quoted "That holds however it stopped: ...
      you stopped it, or it went idle without a report." Q1 quoted "Recover from EVERY place the
      brief told it to write, not only its worktree and branch."
- [x] GREEN gap closed: the first wording sent an agent stopped for drifting back to "resume".
      Reworded; final probe Q1 quoted "one you stopped for drifting is finished by you, not
      resumed into the same drift", Q2 quoted "one that idled can be resumed now".

## Gaps declined

- Where the transcript lives / which script: covered in the same skill, "Structured output must
  be harvested from the TRANSCRIPT" (named vs unnamed agent locations, SKILL.md around line 335).
- How to tell idle from still running: covered by the brief item "A FOREGROUND wait" ("When one
  idles saying it is waiting, check the ground truth yourself").
- Read the evidence dir before RESUMING an idle agent: not needed; a resumed agent keeps its
  context, and the rule targets re-measuring or re-dispatching.
- `<base>` undefined, host-state restore before re-measuring, a gate for a measurement lane:
  predate this edit or are per-item judgement the skill leaves to the dispatcher.
- ssh invocation for a remote evidence dir: owned by bitranox:compuse-ssh.
