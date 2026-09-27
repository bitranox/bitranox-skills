# skill-writer checklist - meta-memory-settings (2026-09-27, router decide mode)

Two cells changed. The `classifier_skill_router` row gains the value `decide` and a statement of
what it does: the same request asked while the prompt waits (1.5 s at most), Jev's one pick or no
nudge at all, the keyword match only when Jev does not answer, one logged row per prompt, and no
other site having the value. The `classifier_backend` row stopped saying that every site knob can
only be `shadow`. The table was re-aligned by `reformat_tables.py`, so every row's padding moved;
no other cell's text changed.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is a retrieval scenario of five questions: whether Jev can
      choose the router's nudge and under which value, what happens on a timeout or error, what
      happens when Jev picks no skill, whether and how long the prompt waits, and whether the Stop
      gate's knob takes the same value.
- [x] Arms pinned to the least inferential tier (haiku), the three classifier rows pasted, tools
      and Skill invocation forbidden, answers required as a direct quote or NONE.
- [x] RED (pre-change rows): 1-4 NONE; 5 quoted the value column `off` [default], `shadow`. Its
      gaps section: "No decision-authority mode exists in the documentation", and the rows are
      "silent on API timeouts, error recovery behavior, blocking behavior, and latency bounds".
- [x] GREEN (new rows): every answer a direct quote - (1) "Jev's answer chooses the nudge - its
      one pick, or NO nudge when it picks nothing (the keyword match is not consulted then)",
      (2) "Only when Jev does not answer (timeout, HTTP error, no key, malformed answer) does the
      keyword match nudge, exactly as with `off`", (3) "its one pick, or NO nudge when it picks
      nothing", (4) "the same request is asked while the prompt WAITS (1.5 s at most)",
      (5) "No other site has `decide`".
- [x] Both dispatches asked for a `Skill gaps` section. GREEN reported none; every RED gap is
      closed by a quoted line above. RED produced no finding that GREEN lost.
- [x] The statement matches the code: `classifier.site_mode` (off unless the backend is `jev`),
      `settings.ENUM_CHOICES` (`decide` for `classifier_skill_router` only),
      `skill-router._decide` and `_ask_jev` (`classifier.ask_in_hook` under `DEFAULT_DEADLINE`
      1.5 s, `classifier.choice_pick` at `SITE_THRESHOLDS["skill_router"]` with `CHOICE_BYPASS`,
      keyword fallback on any unanswered request), and the row fields `mode`, `decide_path`,
      `nudged` pinned by `hooks/tests/test_skill_router_decide.py`.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
