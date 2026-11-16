# Subagent learnings bullet: only the final text can reach the main session

The "SUBAGENT learnings are yours to capture" bullet states what holds on every Claude Code
build: a mid-task discovery lives only in the subagent's transcript and only its final text can
reach the main session. The clause "a named/background agent's report is not returned to you at
all" is gone, because delivery of a named background agent's final text differs by build.

- [x] Step 0b: rejected and removed decisions read; the one rejected entry (name-based
      misplacement signal) is not touched.
- [x] Premise check: `hooks/hooks.json` registers `subagent-capture.py` on `SubagentStop`, and
      that script reads the subagent's own transcript (`agent_transcript_path`), so "scans that
      transcript" describes the code. The per-build delivery measurements are taken as reported
      and were not re-run here (evidence tier `inherited` in the ledger entry).
- [x] RED: text probe of the pre-edit bullet on haiku, text-only agent type, excerpt pasted.
      "Will a finished named background agent's final report arrive in the main session?" It
      quoted "a named/background agent's report is not returned to you at all." and answered
      "No. Its final text does not reach you." The RED is a text check of the pre-edit wording,
      so context the probe inherits from the machine cannot supply the answer.
- [x] GREEN on opus and haiku with the edited bullet pasted. "Does the excerpt say a named or
      background agent's report is never returned to you?": both NONE. The mid-task correction
      left out of the final text: both placed it in the subagent's transcript and named the
      `SubagentStop` hook plus the Stop-gate nudge as its route.
- [x] RED against GREEN in both directions: the bullet's point (the learning is in the
      subagent's transcript, the hook surfaces it once, the main session routes and writes it)
      is answered the same in both; the only answer that changed is the delivery claim.
- [x] Gap closed: both GREEN tiers reported a tension between "lives only in ITS transcript" and
      the hook surfacing the learning. The sentence now reads "The `SubagentStop` hook scans that
      transcript for such discoveries". Re-probe by quote-back on opus (effort medium) and haiku:
      both quoted that sentence for "what reads the place where the learning lives" and answered
      "no" to the contradiction question; the named/background question stayed NONE on both.
- [x] Gaps declined, each predating this edit and outside the bullet's job:
      what counts as a signal (owned by the hook: the `hooks/subagent-capture.py` docstring says
      it scans for "the same learning signals the main gate uses"); the "same rule" for `--proj`
      (the bullet directly above it in SKILL.md, "Decide the eventual home by **scope of
      applicability, not abstractness**", which the probe excerpt left out); a criterion for
      durable against task-local (judgement the skill leaves open); recovery after a skipped nudge (the text says they are gone, which is the
      nudge's behaviour); how a named or background agent's final text is delivered (differs by
      build, so the skill stays silent on it).
- [x] Cases the edit decides beyond the reported defect: none. The bullet no longer says
      anything about named or background agents.
- [x] Decisions: d-20261116-6cb057d2
- [x] Tiers: opus and haiku, text-only agent type, pasted text; 1 RED + 2 GREEN + 2 quote-back
      cells.
- [x] Added lines are at most 98 columns, hold balanced backticks and are ASCII; the next bullet
      ("An intermediate must-hold rule") holds no back-reference to this one, and the list has no
      introducing count.
- [x] No command or snippet added.
