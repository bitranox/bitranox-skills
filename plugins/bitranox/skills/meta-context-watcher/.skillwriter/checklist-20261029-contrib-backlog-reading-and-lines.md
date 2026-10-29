# skill-writer checklist - meta-context-watcher (2026-10-29, contributions: reading a backlog, writing and closing its lines)

Fifteen queued contributions folded into one coherent edit. Reading a backlog: the "classify EVERY
open line" step becomes a five-part list (list items only and match the SessionStart count, read
the last progress segment, staleness check, owning repo per line, forge state); a count a handover's
next action rests on is recounted; a resumed background agent's report is checked against the
deliverables the handover expected. Writing and closing lines: the header exception is inverted
(delete always, rewrite such a header); a line is read in full before it is closed and a partial
close re-tests the parts kept open; rank rule 2 records the user's own reason; the `open:` field
leads with the current state, states time gates as an absolute UTC instant, and cites commits by
subject or pushed sha; handover step 3 carries lines pointing into `handover.prev.md` before the
copy. To keep SKILL.md near its previous length, the peer-session and survivors-after-clear
paragraphs moved to `references/survivors-after-clear.md` and the hook mechanics to
`references/when-it-fires.md`, each behind a pointer saying when to read it.

- [x] Receipt armed (`skill_receipt.py check meta-skill-writer` reports it fresh) and the skill
      loaded through the Skill tool before the first edit.
- [x] Skill type: discipline/reference; the test is retrieval of the rule at the point a reader
      meets it.
- [x] Inherited coverage: several of these lessons are already in the tree-top memory store on this
      machine (the delete-solved-lines rule, the backlog staleness check, the owning-repo rule), so
      a behavioural arm would answer from it. Route taken: coverage check against the skill FILE,
      run on the pre-edit text (`git show HEAD:<path>`).
- [x] RED (pre-edit text, `grep -ci`): `recount` 0, `reason not given` 0, `own reason` 0,
      `LOST ITS BRIEF`/`deliverable` 0, `LAST progress`/`WHOLE entry` 0, `lead with` 0,
      `multi-part`/`parts left` 0, `sub-item`/`appended` 0, `git log -S` 0, `gh issue list`/
      `gh pr list --state open` 0, `UTC`/`by now` 0, `SessionStart.*count` 0. Hits that exist
      and are not the rule: `handover.prev.md` (3, the copy step, nothing about pointers into it),
      `sha` (5, HEAD's sha in "How to verify", not a sha cited by a backlog line), `EVERY line`
      (3, free rank and "classify", no owning-repo check per listed line), `YYYY` (1, the
      template itself). The old header text said "the header governs that file".
- [x] GREEN (edited text, quoted back with `grep -nF`):
      "recount it from the data file the handover cites";
      "rewrite that header rule to the delete rule in the same change";
      "quoted, or the words `reason not given`";
      "An agent resumed after the clear can have LOST ITS BRIEF";
      "take its state from its LAST progress segment";
      "When an item's state changes, rewrite `open:` to lead with the new state.";
      "lines that point INTO `handover.prev.md`";
      "Cite a commit by its subject, or by a sha from the PUSHED history.";
      "re-test the premise of each part you keep open";
      "re-home every follow-up the closing work did not address as its own line";
      "`git log --oneline --since=<raised date> -S '<a phrase or symbol unique to the item>'`";
      "`gh pr list --state open` and `gh issue list --state open`";
      "Check which repo each line's fix lands in, for EVERY line you list.";
      "A time-gated condition (a cooldown, an expiry, a release window) states an absolute instant.";
      "check your count equals the open-item count the SessionStart block printed".
- [x] Mechanism claims checked against the code and the repo:
      - the anchored listing `grep -nE '^- \[ \] \([^)]*\) \[[0-9]+\] '` returned 9 lines on this
        repo's `OPEN-WORK.md`, equal to `open_work.iter_items` open items (9); the bare
        `^- \[ \]` returned 10, the extra one the header's open-item template line.
        Positive and negative control in one run.
      - `iter_items` skips fenced blocks and `_ITEM_RX` needs a digit rank, so `backlog_list` and the
        SessionStart count both exclude the template (`hooks/open_work.py`).
      - SessionStart prints `%d OPEN-WORK ITEM(S)` (`hooks/session-start.py`), the count the text
        tells the reader to match.
      - the staleness command: `git log --oneline --since=2026-10-27 -S 'DirEntry.stat() leaves
        st_dev'` found the commit that added it; the same with a phrase that exists nowhere printed
        nothing.
- [x] Paragraph after each insertion point read: the closing-part paragraph is followed by "Select
      a line by the rank" (no back-reference); the `open:` bullets by "## What belongs in it"; the
      lost-brief sentences by the pointer paragraph. The moved survivors text said "the paragraph
      above checks a handover-named agent", which no longer resolves in the reference file;
      rewritten to name SKILL.md's handover-named-agent check.
- [x] Width and fence check over the added lines (the script in meta-skill-writer's REFACTOR
      section) prints nothing for SKILL.md; the moved reference text had one prose line over 100
      columns, rewrapped. Two pre-existing over-long lines next to the edits were rewrapped too.
- [x] Cases decided beyond the reported defects, listed: (1) a header that keeps closed lines is
      rewritten AND its existing `- [x]` lines are deleted in that change - the user's directive is
      "always delete solved lines", so a header-only rewrite would leave the noise it names;
      (2) the forge listing assigns a PR changing files another repo distributes to that repo,
      generalised from a CI template's workflows.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added; the UTC example uses an invented instant.
- [x] Present tense, no session narrative, no private provenance in the skill text.
- [x] Subagent arms: none run for this change (coverage check route above); 0 tier cells.
