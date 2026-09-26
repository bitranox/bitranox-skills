# skill-writer checklist - compuse-toolbox (2026-09-26, doc sync for the 7.25.6 script fixes)

Rows and notes for claim_check, conflict_scan, transcript_index, jsonl_grep, adjudicate, newest, mdwrap, fleet_ssh and diffbehave now state the behaviour the 7.25.6 scripts have.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed behaviour, answered ONLY from pasted passages, with a direct quote or NONE.
- [x] Scope: the passages that describe the changed behaviour; no frontmatter change.
- [x] Inherited-context route: the arms are pasted text on an inert probe type told not to invoke
      a skill, so the answer is a text check of the passages, not of the installed skill.

## RED
- [x] Old passages (built from the porcelain word diff, not retyped), haiku, inert probe type:
      Q4 claim_check: one hit plus one unreadable path: BROKEN (wrong).
      Q5 newest --name-timestamp: unzoned stamp read as: NONE.
      Q6 diffbehave: one side exits 127; one side times out: NONE.
      Q7 adjudicate launcher: uv run (wrong).
      Q8 fleet_ssh re-runs after dropping a key?: "retries only when ssh itself refused" (misleading).
      Q9 jsonl_grep `<(cmd)`: NONE.
      Q10 transcript_index punctuation-only query: NONE.
      Q11 conflict_scan symlinked dir inside a walked tree: "skipped with a stderr note" (the dangling-link rule, wrong).
- [x] Skill gaps asked for: the RED reply listed every question above as unaddressed or
      only partly covered.

## GREEN
- [x] New passages, same model and questions:
      Q4 claim_check: one hit plus one unreadable path: "A hit in the files it DID read is still PRESENT (exit 0), with the unread paths listed on stderr as `skipped:`".
      Q5 newest --name-timestamp: unzoned stamp read as: "read as UTC, `Z` or not, so a local-time stamp reports an age off by the UTC offset".
      Q6 diffbehave: one side exits 127; one side times out: "A case where EITHER side did not run ... is ERROR ... one side timing out while the other answers is DIFFER".
      Q7 adjudicate launcher: "`python3 scripts/adjudicate.py` ... NOT `uv run`, whose env lacks a hook's optional deps".
      Q8 fleet_ssh re-runs after dropping a key?: "it never re-runs the command".
      Q9 jsonl_grep `<(cmd)`: "any existing path is read, so `<(cmd)` works".
      Q10 transcript_index punctuation-only query: "exit 2 = query error or a query with no letter or digit".
      Q11 conflict_scan symlinked dir inside a walked tree: "a symlinked directory met inside a walked tree is not followed and is named on stderr".
- [x] GREEN diffed against RED in both directions: every RED answer that was right stayed right;
      nothing a baseline answered was lost.
- [x] Skill gaps asked for again. One reported: what the license gate does after reading a
      `SEE LICENSE IN` file - declined, the full sentence in the file continues "and one copyleft
      id rejects" and lists an unrecognised license text as a stop; the probe saw a cropped
      excerpt.
- [x] Every stated behaviour checked against the script it describes, and each script change is
      pinned by tests that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] Tables re-padded by the formatter where a row changed (`reformat_tables.py --check` clean).
