# skill-writer checklist - meta-memory-settings (2026-10-06, recall decide)

The `classifier_recall_rerank` row gains `decide` in its allowed values and a description of what
decide does; its SENT list now names the assistant reply the request carries (300 characters at
most), which the hook sends and the row did not list. Two stale sentences go: the
`classifier_backend` row's "(or, for the skill router only, `decide`)" and the skill router row's
"No other site has `decide`.", both false since the Stop gate gained decide. The table was
re-aligned by `reformat_tables.py`; no other cell's text changed. `docs/reference.md` carries the
same change in its own row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Retrieval scenario, seven questions: Q1 can the knob be `decide`, Q2
      which notes are injected in decide, Q3 can a note the keywords did not pick be injected, Q4
      what is injected when Jev does not answer, Q5 every text sent, Q6 how long the prompt waits,
      Q7 which sites support `decide`.
- [x] Arms pinned to haiku on the inert `bitranox:baseline-probe` type, the three rows pasted,
      answers as a direct quote or NONE, each ending with a "Skill gaps" section.
- [x] RED (pre-change rows): Q1 "No" (only `off`, `shadow` listed); Q2, Q3, Q4, Q6 NONE; Q5 quoted
      "the prompt and up to 30 matching memory notes", which omits the reply the hook sends - a
      false answer; Q7 "`classifier_skill_router` only", quoting "No other site has `decide`" -
      false, the Stop gate has it too.
- [x] GREEN (new rows): Q1 yes; Q2 "the notes Jev scores at 0.8 or more, best first, up to 4"; Q3
      "whether or not the keyword ranking picked them"; Q4 "NOTHING is injected: the keyword
      ranking is not a fallback"; Q5 the prompt, the reply (300 at most), up to 30 notes; Q6
      "1.5 s at most"; Q7 the skill router and recall (the Stop gate row was not in the pasted
      set). Skill gaps: none.
- [x] GREEN against RED in both directions: every RED answer is still answered; Q1, Q5 and Q7
      change from wrong to right, Q2-Q4 and Q6 from NONE to a quote, as intended. Nothing lost.
- [x] The statement matches the code: `recall-memory._decide_recall` builds the same requests as
      shadow (`_rerank_request`: `with_previous`, `PREVIOUS_CAP` 300, `SHADOW_NOTE` 600, up to
      `SHADOW_SHORTLIST` 30), asks via `classifier.ask_in_hook` (deadline `DEFAULT_DEADLINE` 1.5 s)
      with `workers` = the request count, keeps scores >= `SITE_THRESHOLDS["recall_rerank"]` (0.8)
      best first, and `main` caps the injection at `MAX_HITS` 4; no answer gives path
      `fallback-<reason>` and no picks. Pinned by `tests/test_recall_memory_decide.py` (6 tests;
      the all-at-once test fails when `workers` is put back to 8).
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
