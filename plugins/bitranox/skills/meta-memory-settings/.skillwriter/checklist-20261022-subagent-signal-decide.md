# skill-writer checklist - meta-memory-settings (2026-10-22, classifier_subagent_signal decide)

The `classifier_subagent_signal` row gains `decide` in its allowed values and a sentence on what
it does, for the new decide path in `hooks/subagent-capture.py`. Only that row's line changed; the
table formatter re-padded nothing else. `docs/reference.md` carries the same change in its row.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - can a reader find that `decide` exists, what
      decides, the threshold, the wait, and what happens when Jev gives no answer.
- [x] Inherited coverage: every arm was given the row as pasted text and answered only from it, so
      RED and GREEN are text checks of the skill file's own row, which context the probe inherits
      cannot supply.
- [x] RED (haiku, `bitranox:baseline-probe`, the pre-edit row): asked whether Jev can decide, what
      happens to a broad-only match Jev rejects, to a message on a Jev timeout, at what score, and
      how long the stop waits. It answered NONE to the first, fourth and fifth, quoting "There is no
      `decide`.", and said the patterns' verdict stands on the other two.
- [x] GREEN (haiku and opus, the edited row, plus a sixth question: a strict match Jev scores
      low): both answered the five by direct quotes of the new `decide` clause.
- [x] Diffed both ways: RED's answers were the absence of the mode; nothing it gave is lost.
- [x] GREEN gaps, each decided:
      - a strict match Jev scores low (both tiers, answered only by inference) - CLOSED: "neither is
        a strict match it scores below 0.8 on both".
      - one score or both (opus) - CLOSED: "either a self-admitted mistake or a realization at 0.8
        or more".
      - one deadline or one per request, and a late answer (opus) - CLOSED: "1.5 s at most for all
        of them; a later answer counts as none".
      - whether the buffer still blocks in decide (opus) - CLOSED: "A non-empty buffer still blocks
        the main session's Stop."
      - the shadow failure list lacks "malformed answer" (opus) - DECLINED: in shadow nothing acts
        on any answer, so which failures exist does not change the outcome.
      - nothing is sent under `off` (opus) - DECLINED: the `classifier_backend` row states that
        nothing is sent unless it is `jev`, and every site row is read under it.
      - what the score is, per question or combined (haiku) - CLOSED by the "either ... or" clause.
- [x] Every closed gap verified by quote-back on the final text (haiku): five questions, five
      answers by direct quote, all matching the code. Its remaining gaps ("strict" and "broad"
      undefined, what the 12 counts) are excerpt artifacts: the full row defines both before the
      `decide` clause.
- [x] Every claim checked against the code and its tests: Jev decides answered messages
      (`subagent-capture._decide`, `test_decide_drops_a_broad_only_hit_jev_leaves_quiet`,
      `test_decide_lets_jev_overrule_a_strict_hit_it_answers_quiet`); either question at the site
      threshold 0.8 (`_jev_families`, `classifier.SITE_THRESHOLDS`,
      `test_decide_threshold_is_the_site_threshold`); parallel asks under one deadline
      (`ask_in_hook` with `workers` = request count, `classifier.DEFAULT_DEADLINE` = 1.5,
      `test_decide_asks_the_messages_in_parallel`, the fallback test bounding the whole stop);
      strict-only fallback for unanswered and capped messages
      (`test_decide_falls_back_to_the_strict_patterns_when_jev_does_not_answer`,
      `test_decide_falls_back_to_strict_for_messages_the_cap_left_out`); one logged row naming the
      path and each decision (`test_decide_logs_one_row_naming_each_message_decision`); the
      threshold named in the row (`test_a_decide_row_states_the_threshold_the_site_acts_at`).
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
