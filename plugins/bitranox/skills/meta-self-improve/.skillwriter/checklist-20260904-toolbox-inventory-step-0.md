# skill-writer checklist - meta-self-improve (2026-09-04, tool inventory as step 0)

Change: the Procedure gains a step 0, "Read the tool inventory FIRST (before hand-rolling
anything)", and the Deliverables checklist gains the matching line. It names both halves - the
local `toolbox list` and the shipped `bitranox:compuse-toolbox` row table - and says to prefer a
tool the PreToolUse nudge names over the command it interrupted. No frontmatter change.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Skill type: PROCESS. The test that applies is whether the step is reachable at the moment it
      binds, which is a placement question, not a wording one.
- [x] The defect is placement, not absence, and that is what the change fixes. The chore ladder at
      step 6 already says to build or ENHANCE a tool rather than work around one, and the
      "ENHANCE, do not work around" line already sits there. Neither fires in time: a capture run
      hand-rolls its scripts DURING the capture, so by the time step 6 asks whether a recurring
      chore deserves a tool, the throwaway is already written. Step 0 is where the read binds.
- [x] Behavioural RED not run, and the reason is recorded rather than worked around:
      `redcheck --corpus-cascade` reports STRONG inherited coverage, naming this repo's own
      always-loaded files as documents that already teach it. An agent dispatched on such a machine
      answers from those, so the arm cannot fail honestly. The evidence taken instead is the
      accuracy check below plus a text check of the artifact.
- [x] ACCURACY: every claim the step makes is checked against the machine, not asserted.
      `toolbox.py list` runs and returns rows (exit 0); `bitranox:compuse-toolbox` ships a table of
      33 tool rows; `factedit.py` ships in `meta-dream-tree`; `anchor_edit.py` ships in
      `compuse-toolbox/scripts/`. Both named misses are real and both are covered by the two halves
      the step names, which is why it names two.
- [x] Both halves are load-bearing, and the step says why. The LOCAL list covers your own jigs; the
      SHIPPED table covers the ones contributed upstream, which no longer exist locally, so a
      reader who checks only the local list still re-implements those.
- [x] The step is enforceable, not advisory: it is a Deliverables line, which is the shape this
      skill uses for anything a completed run must have. A step with no deliverable is one a run can
      end without.
- [x] No frontmatter change: 0 frontmatter lines in the committed diff for this file, so no routing
      keyword moved.
- [x] Scripts unchanged by this entry; `repo-gate.py --ci` green at 4700 passed.
- [x] Present tense, no session narrative, no machine-specific address or path added. The one path
      the step names is `~/.claude/skills/toolbox/tools/toolbox.py`, the documented home of the
      local toolbox and the same path `meta-dream-tree` step 0c names, written with `~` and no user.
