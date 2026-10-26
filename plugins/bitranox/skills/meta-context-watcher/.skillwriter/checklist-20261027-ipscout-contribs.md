# skill-writer checklist - meta-context-watcher (2026-10-27, select a backlog line by its rank prefix)

One paragraph after the closing-rule paragraph ("That closing rule is the default ...") says to
select an `OPEN-WORK.md` line by the rank in its own open-item prefix (dash, empty box, date, then the rank in brackets), never by a bare
`[N]` anywhere in the line, because items cite each other by rank in their text. It states what
`backlog_close` matches on, gives the anchored extended regex for a script of one's own, says plain
`sed` (BRE) deletes nothing with that pattern, and requires exactly one hit before writing.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`), and this skill loaded through
      the Skill tool before the first edit.
- [x] Item: contrib item 15 (bare ` [N] ` match deletes lines that cite the rank).
- [x] Skill type: technique; the test is application - which pattern to match, why a bare
      substring is unsafe, what the tool refuses, what the script checks before writing.
- [x] RED by text check against the pre-change file (`git show HEAD:<path>`): no line mentions a
      substring match, an anchored match, an extended regex or an exactly-one-hit check (0 hits
      for `substring|anchor|sed -E|grep -E|exactly one line`). `backlog_close` was already named
      for closing, without what it matches on.
- [x] `redcheck --corpus-cascade` run on the scenario: it names the tree-top memory index on 4
      shared terms (backlog, cite, open-work, rank). Adjudicated against the named lines: they
      cover deleting solved lines, positional indexes and bulk target lists, none states the
      prefix-anchored rank match. The RED is the text check against the skill file above, which
      inherited context cannot contaminate.
- [x] Claims verified by running them, not from the request text:
      - `backlog_close` (`open_work.close_item`) matches the rank with `_ITEM_RX.match` on the
        stripped line, `-\s*\[([ xX])\]\s*\(([^)]*)\)\s*\[(\d+)\]`, only on open lines, skips
        fenced code (`iter_items`), and raises `AmbiguousRank` for a rank two open lines share;
        on a probe file with two lines citing `[60]` in their text it deleted only the rank-60
        item, and a second close raised `UnknownRank`. It works on an untracked file.
      - `grep -v ' \[60\] '` on the same file dropped the rank-60 item AND both citing lines.
      - `grep -vE` / `sed -E` with `^- \[[ xX]\] \([^)]*\) \[60\] ` removed only the item; plain
        `sed` with the same pattern removed nothing (the rank line survived).
- [x] GREEN by quote-back on the first text (opus at effort medium, plus haiku; 4 questions each):
      every answer a direct quote, no NONE. Quotes checked with `quotecheck text` against the
      skill dir, with a planted false quote as control: 5 OK, the control MISMATCH.
- [x] Gaps, each decided:
      - "anchors its match the same way" read as open-only while the regex has `[ xX]` (both
        tiers) - CLOSED: "on that prefix", plus "`[ xX]` also reaches a closed line in a file
        that keeps them".
      - regex dialect for sed (opus) - CLOSED: extended regex named, plain `sed` behaviour stated
        (measured above).
      - what to do on zero or several hits (both tiers), and haiku attributing "It checks" to
        `backlog_close` - CLOSED: "The script counts its hits and writes nothing unless there is
        exactly one; on zero or several, read the lines it hit and fix the rank or the pattern
        first."
      - how to invoke `backlog_close` - DECLINED, covered elsewhere: SKILL.md "the `backlog_close`
        tool deletes it the same way and returns the line and reason for that message".
      - a script's handling of code fences - DECLINED: a fenced example line holding the same
        rank is a second hit, which the exactly-one check refuses.
      - a backup before writing in an untracked backlog - DECLINED, covered elsewhere: the
        paragraph above it, "ask git whether the file is tracked ... first put any lasting reason
        somewhere durable".
      - a line without a date or without text after the rank - DECLINED: the line format requires
        both, and an undated item is written `(unknown)`, which `\([^)]*\)` matches.
      - open and closed lines sharing a rank make the script refuse where the tool would not -
        DECLINED, covered elsewhere: "A free rank is free over EVERY line of the file, closed
        `[x]` lines included."
- [x] Re-probes (opus at effort medium, plus haiku, each round): round 2 asked the 3 questions
      the first fixes touched (plain `sed`, zero or two hits, open-only); round 3 asked the
      hit-count question again on the final text after its last fix. Every answer a direct quote,
      no NONE; in round 3 both tiers attribute the hit count to the script. Remaining notes are the declines above. Final quotes
      re-checked with `quotecheck` (3 OK, planted control MISMATCH).
- [x] Tiers: GREEN opus + haiku, re-probe opus + haiku, final re-probe opus + haiku - 6 cells.
- [x] Description unchanged - no routing keyword moved. Tables canonical
      (`reformat_tables.py --check --strict` reports Unchanged).
- [x] ASCII only; no address, MAC, hostname or machine path added; present tense; the
      version-history finder reports no hit in the added lines.
- [x] Hook tests that read skills pass (`pytest plugins/bitranox/hooks/tests -k "skill or
      description or trigger or tell"`: 948 passed). The skill has no `tests/` dir.
