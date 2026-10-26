# skill-writer checklist - docs-md-table-formatting (2026-10-27, a scripted cell edit replaces only the match)

One paragraph at the end of "Editing tables via JSON (tablekit.py)" says a script that rewrites
part of one cell replaces only the matched text, never from the match to the next `|`; that the
column count is unchanged so the reformat pass and `--strict` stay silent; how to replace safely
(exact string occurring once, or `tablekit.py`); and to read the row back with
`git diff --word-diff`, where every deletion in the row must be intended.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`), and this skill loaded through
      the Skill tool before the first edit.
- [x] Item: contrib item 17 (a slice to the next pipe dropped half a cell; the re-padded table
      still looked well-formed).
- [x] Skill type: technique; the test is application - is the slice allowed, does a clean
      `--strict` prove the cell intact, how to check the row, what a safe replacement does.
- [x] RED by text check against the pre-change file (`git show HEAD:<path>`): no line covers a
      scripted partial-cell edit (0 hits for `word-diff`, "next `|`", `matched text`, `slice`).
- [x] `redcheck --corpus-cascade` run on the scenario: it names the tree-top memory index on 4
      shared terms (markdown, pipe, reformat, rewrites). Adjudicated against the named lines: the
      nearest is "A pipe inside a table code span drops the rest of the row", a different defect
      (GFM cell splitting); none states the slice-to-next-pipe rule. The RED is the text check
      against the skill file above.
- [x] Claims verified by running them in a scratch git repo:
      - replacing from the match to the next `|` dropped the rest of the cell
        (", ping socket via ping_group_range");
      - `reformat_tables.py --strict` on the damaged file exited 0 with "Reformatted", no ragged
        warning, and the table looked aligned;
      - plain `git diff --stat` counted all 4 table rows changed after the re-pad;
      - `git diff --word-diff=plain` showed `[-needed, ping socket via ping_group_range-]` on the
        damaged row, and only `{+or CAP_NET_RAW+}` (no deletion) for the exact-string replacement.
- [x] GREEN by quote-back on the first text (opus at effort medium, plus haiku; 4 questions each):
      every answer a direct quote, no NONE. Quotes checked with `quotecheck text` against the
      skill dir, with a planted false quote as control: 5 OK, the control MISMATCH.
- [x] Gaps, each decided:
      - "check it occurs once": once where, and what if not (opus) - CLOSED: "check it occurs
        exactly once in the file, and narrow it until it does".
      - no pass/fail reading of the word diff (both tiers) - CLOSED: "every `[-...-]` in that row
        must be text you meant to replace".
      - what to do on a bad word diff (both re-probe tiers) - CLOSED: "any other is text the edit
        cut, so restore the file and redo the edit".
      - how to call `tablekit.py` - DECLINED, covered elsewhere: the same section's commands
        (`tablekit.py read FILE.md --index 0 ... | python3 tablekit.py replace FILE.md --index 0`).
      - what `--strict` checks - DECLINED, covered elsewhere: "`--strict` turns that into a
        non-zero exit for CI" in the ragged-row paragraph.
      - escaped `\|` inside a cell - DECLINED: replacing only the matched text never consults a
        pipe; the escape is already covered in "A pipe inside backticks still splits the cell".
      - a file not in git, or restoring alongside other uncommitted edits - DECLINED: an edge the
        reader resolves (`git diff --no-index`, restore only their own edit); out of scope for a
        one-paragraph rule.
      - applying the rule to sed or an editor, and when to prefer `tablekit.py` - DECLINED:
        judgement the skill leaves open; the rule names scripts, and either method satisfies it.
- [x] Re-probes (opus at effort medium, plus haiku, each round): round 2 asked the 2 questions
      the first fixes touched (three occurrences, a stray `[-...-]`); round 3 asked the stray
      deletion question again on the final text after its last fix. Every answer a direct quote,
      no NONE. Remaining notes are the declines above. Final quotes re-checked with
      `quotecheck` (3 OK, planted control MISMATCH).
- [x] Tiers: GREEN opus + haiku, re-probe opus + haiku, final re-probe opus + haiku - 6 cells.
- [x] Description unchanged - no routing keyword moved. Tables canonical
      (`reformat_tables.py --check --strict` reports Unchanged).
- [x] ASCII only; no address, MAC, hostname or machine path added; present tense; the
      version-history finder reports no hit in the added lines.
- [x] The skill's own tests pass (`pytest plugins/bitranox/skills/docs-md-table-formatting/tests`:
      146 passed), and the hook tests that read skills pass (948 passed).
