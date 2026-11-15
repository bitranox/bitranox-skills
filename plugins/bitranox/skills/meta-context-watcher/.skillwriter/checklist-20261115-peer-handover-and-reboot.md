# A live peer's handover.md, and a checkpoint that survives a reboot

Two queued contributions, one remedy: where a watcher checkpoint goes when the checkout's
`handover.md` belongs to a session that is still working, and where state goes so a host reboot
that empties the scratchpad does not take it.

- [x] Step 0b: no rejected or removed decisions for this skill.
- [x] Premise check: `hooks/compact-resume.py` `candidates()` takes the cwd's repo root plus every
      touched path named `handover.md` (Write/Edit only; its docstring: a Bash write never reaches
      touched paths), so a scratchpad `handover.md` written with Write is handed back.
- [x] RED route: `redcheck --corpus-cascade` found the lesson in the machine's memory store, so the
      evidence is a text check of the pre-edit text (quote or NONE). RED on opus and haiku: the
      peer question quoted only "Write `handover.md` at the repo root, OVERWRITING whatever is
      there"; the reboot question found no sentence on reboot survival.
- [x] GREEN on opus and haiku with the edited text: peer case quoted "write a watcher checkpoint
      as `handover.md` in the session scratchpad instead, with the Write tool"; reboot case quoted
      "The scratchpad does not survive a host reboot, so it never holds the only copy". Control
      (an ended earlier session's file, no peer): both tiers write at the repo root and quote the
      stale-handover rule.
- [x] The step 4 lead now carries the exception, so it stays true read alone.
- [x] Gaps declined: a concrete test for "still working" (a judgement from the file's first lines,
      left open); a peer's lines in a shared `OPEN-WORK.md` (covered, SKILL.md "In a checkout other
      sessions share, the file can hold a peer's uncommitted lines beside yours"); whether the
      repo-root case also needs the backlog line for a reboot (the working tree is not under the
      scratchpad, so it survives one).
- [x] Decisions: d-20261115-0c9b527c, d-20261115-d1ff43f2
- [x] Tiers: opus and haiku, text-only agent type, pasted text; 2 RED + 2 GREEN cells.
- [x] Width and fence check over the added lines printed nothing; the step after the insertion
      read for a re-bound reference.
- [x] Finder for version-history wording over the added lines: no hit. ASCII only, no private
      host or path.
