# skill-writer checklist - meta-context-watcher (2026-10-26, compact mode)

The skill gains a second mode beside the handover. A "Two modes" section says compact (the
default) writes a CHECKPOINT with steps 1-6 and returns to the task in flight (new step 7c), while
handover mode and any handover the user asks for keep steps 7-8. It defines "compact-mode
checkpoint" so the checkpoint exceptions (no commit, next action = the task in flight) never reach a
user-requested handover. The reader side gains "A checkpoint handed back after a compaction is your
own work in progress", which scopes the earlier-session reading rules away from it. "When it fires
on its own" describes the PostToolUse request, the save point, the harness reserve and the
`CLAUDE_CODE_AUTO_COMPACT_WINDOW` alignment. The intro drops the 83% figure for the auto-compact
window. Rank rule 4 says to work the highest-ranked unblocked item while a blocked one waits.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: discipline/technique; the test is application under a conflicting instruction -
      what a session does when the hook's compact-mode request arrives, and when the checkpoint is
      handed back after the compaction.
- [x] Inherited coverage: no memory fact or CLAUDE.md line describes compact mode (it is new in
      this change), so the RED arms could only answer from the skill text they were given. All
      arms were `general-purpose` agents restricted to reading the named files, with the hook
      message and the resume block generated from the real hook code.
- [x] RED (pre-edit text; opus and haiku; 2 scenarios = 4 cells):
      - save request: both tiers follow step 7 ("STOP. The handover is the LAST thing you do") and
        step 8's `/clear` nudge, and step 4's "Commit it along with `OPEN-WORK.md`"; opus overrides
        the skill on its own judgement and says "no line of file 1 permits this".
      - resume block: haiku reads `OPEN-WORK.md` first, classifies, and leaves the half-written
        in-flight task for backlog item [20] ("Recency is not a reason"); opus resumes but writes
        "File 1 never says this. It is my own inference."
- [x] GREEN (edited text; opus and haiku; 2 scenarios + a control = 6 cells): both tiers write the
      checkpoint, commit nothing ("A compact-mode checkpoint commits nothing just for itself"),
      return to the task (step 7c quoted), and on the resume take the checkpoint's next action
      without reading or re-ranking the backlog. Control (user asks for a handover in compact
      mode): both tiers run steps 1-8, commit, stop and send the `/clear` nudge, quoting "A handover
      the USER asks for ... runs steps 1-8 in either mode."
- [x] Diffed both ways: every RED action that belongs to the checkpoint (lessons, reconcile into
      `OPEN-WORK.md`, `.prev` copy, secret check, expiry line, re-read) is still in GREEN; what left
      is exactly the stop, the `/clear` nudge, the commit and the backlog re-ranking on resume.
- [x] Gaps, each decided:
      - "compact-mode checkpoint" ambiguous for a user-requested handover - CLOSED: the definition
        paragraph after "Two modes".
      - "Either way" read as "commit in both modes" - CLOSED: "Committed now or later, check ...".
      - step 1 justifies lessons by "the file is committed" - CLOSED: "the file sits in the repo,
        committed or not".
      - how current the checkpoint must be kept - CLOSED: "Do not keep it in step with every edit".
      - what "task in flight" covers - CLOSED: "the whole piece of work the checkpoint's 'In
        flight' names, every remaining step of it".
      - "the rules below" was a fuzzy positional scope - CLOSED: "The paragraphs after this one,
        from 'A gate result in the handover' on".
      - "read it FIRST" contradicted the resume rule for a skimming reader - CLOSED: the qualifier
        on that paragraph.
      - lessons in a resumed checkpoint - CLOSED: "The checkpoint's lessons need nothing from you".
      - a blocked top item beside a workable lower one (reported by RED and GREEN, so older than
        this edit) - CLOSED: rank rule 4, "While a blocked item waits for its answer, work the
        highest-ranked item that is not blocked."
      - which file to name in 7c - CLOSED: "naming its path".
      - whether the nap reads an uncommitted `handover.md` - DECLINED, covered elsewhere:
        `meta-dream-nap/SKILL.md` line 62 reads "every line under `## Lessons for the next nap` in
        the repo's `handover.md`", the file on disk.
      - commit before or after steps 5-6, a user's consent to the step-4 commit, the repo root in
        a linked worktree, no handover to reconcile, an empty lessons heading, the diff source when
        no `.prev` exists - DECLINED: older writer-side questions this change does not touch;
        out of scope for the mode split.
- [x] Re-probe on the final text by quote-back (opus at effort medium, plus haiku; 8 questions
      covering every fix): every answer a direct quote, no NONE, no contradiction found; the only
      new note was the nap question declined above.
- [x] Tiers: RED opus + haiku (4 cells), GREEN opus + haiku (6 cells including the control),
      re-probe opus + haiku (2 cells, 8 questions each).
- [x] Description measured with `len()`: 825 characters, under 1024; the new trigger is "when the
      context watcher asks for a checkpoint before auto-compaction or a compaction hands a saved
      checkpoint back". Derived artifacts regenerated (`skill_triggers.json`, `docs/skills.md`).
- [x] The harness facts in the text were measured, not assumed: scripted probes on Claude Code
      2.1.310 at windows of 100k and 200k (compaction about 33k below the window; the turn
      continues after an automatic compaction; a SessionStart `additionalContext` on source
      `compact` reaches the next request; an `env` block in settings.json reaches hooks).
- [x] No address, MAC, hostname or machine path added; ASCII only; present tense, no session
      narrative; the version-history finder reports no new hit.
