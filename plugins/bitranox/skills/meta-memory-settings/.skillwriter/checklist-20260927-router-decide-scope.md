# skill-writer checklist - meta-memory-settings (2026-09-27, router decide scope)

One cell changed: the `classifier_skill_router` row's `decide` statement. Decide mode now acts on
typed prompts only (a background-task notification is handled as with `off`, Jev not asked), and a
pick from the project's cached skill list that is not this plugin's own skill is treated as no
answer, so the keyword match nudges. The table was re-aligned by `reformat_tables.py`; no other
cell's text changed.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Retrieval scenario of three questions under `decide`: a
      notification turn (is Jev asked, what is nudged), a confident pick of a skill found only in
      the cached list and no longer installed, and a pick of nothing.
- [x] Arms pinned to haiku, the row pasted, tools forbidden, answers as a direct quote or NONE.
- [x] RED (pre-change row): 1 NONE, 2 NONE, 3 quoted "NO nudge when it picks nothing (the keyword
      match is not consulted then)". Its gaps named both silences: whether notifications reach Jev
      at all, and what happens to a pick outside the installed set.
- [x] GREEN (new row): 1 quoted "A background-task notification is handled exactly as with
      `off`", 2 quoted "or picks a skill the session may no longer have (read from the project's
      cached skill list and not this plugin's own), does the keyword match nudge", 3 unchanged.
- [x] GREEN gaps: (a) the row did not say directly that Jev is not asked on a notification -
      CLOSED, the sentence now ends ": Jev is not asked."; (b) what `off` does is defined outside
      this row - DECLINED, `off` is the default whose behaviour the table's other rows and the
      router's own description give; (c) picking nothing versus failing takes two passages to read
      - DECLINED, both passages are in one cell and each is quoted above. RED's gap on what
      "installed in the session" means - DECLINED, a mechanism of `skill_roster.installed_skills`,
      not a settings consequence. Nothing RED produced is missing from GREEN.
- [x] The statement matches the code: `skill-router.main` sends a turn to `_decide` only when
      `prompt_text.notification_fields` is empty; `_ask_jev` returns "fallback-stale pick" when
      `skill_roster.is_live` is false (live = in the transcript listing, or this plugin's skill on
      disk); pinned by `test_decide_leaves_a_task_notification_exactly_as_off_does` and
      `test_decide_treats_a_cached_pick_the_session_may_not_have_as_no_answer`.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
