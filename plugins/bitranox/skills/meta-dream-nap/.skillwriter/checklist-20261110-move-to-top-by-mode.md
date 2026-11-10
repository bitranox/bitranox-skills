# A move to the tree top follows the dream mode; the report carries verify's pointer-block lines

- [x] Step 0b: `show meta-dream-nap --kind rejected,removed --full` and `show meta-dream-nap` read.
      No entry says chain-internal placement includes moves to the anchor; nothing superseded.
- [x] The nap has no promotion step (no `promot` anywhere in SKILL.md), so every move it routes to
      the anchor is a misplacement re-home in dream-core.md's sense.
- [x] RED (opus, text-only agent type, pre-edit step 4 and step 6 pasted): five cases at
      /t/a/proj with chain /t/a/proj -> /t/a -> /t. G /t/a -> /t in propose and in auto: applied
      both times, deciding line "applying only moves whose from AND to levels are ON the chain (up
      or down)", mode NONE, cost NONE, `pointer blocks` lines in the report NONE. K /t/a/proj ->
      /t/a in propose and H /t -> /t/a in propose and auto: applied.
- [x] GREEN (opus, same cases plus G under `off` on a manual run, new text pasted): G stays at
      /t/a and is listed with its cost for approval in propose and under `off` ("in propose mode
      the nap lists the fact and its cost ... and does not apply it"); G applied at /t with its
      cost printed in auto; K and both H moves applied ("Every other chain move, a move down from
      the anchor included, is applied in every mode."); `pointer blocks` lines go into the report
      in every case ("its `pointer blocks` lines go into the report as printed").
- [x] Same GREEN prompt re-run on haiku: the same six verdicts, each with a direct quote.
      Tiers: opus RED, opus GREEN, haiku GREEN; 5 + 6 + 6 cells.
- [x] GREEN diffed against RED both ways: the only change is the mode-dependent outcome for G
      and the report lines; the down and intermediate moves and the pin rule are unchanged.
- [x] Skill gaps asked of every arm. Closed: RED read "the anchor (home: ...)" in step 6 as
      naming the anchor's location; the `home:` parenthetical now sits next to
      `reconcile_memory_index.py`. Declined, covered by the REQUIRED BACKGROUND core: how to
      compute the cost of a proposed or applied move (dream-core.md, Mode: "the UTF-8 length of
      its pointer line plus the newline"); where a proposed move sits in the report and what to
      print per level (dream-core.md, Verification contract: "listed beside them with its cost:
      as a proposal awaiting the user's approval in propose mode and under `off`"); what `off`
      still consolidates (dream-core.md, Mode: "a manual run consolidates PRIVATE memory only").
      Declined, not ruled by the user: reporting the bytes a move down from the top saves (the
      verify lines already show the shrink) and an explicit "no pointer blocks changed" line.
- [x] Contract test `test_dream_skill_contracts.py`: 19 passed.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion point read; the table reformatted with `reformat_tables.py`.
- [x] Finder for version-history wording and the address check over the added lines: no hit.
- [x] Decisions: d-20261110-f1fa0763
- [x] No private host, path or project name; ASCII only.
