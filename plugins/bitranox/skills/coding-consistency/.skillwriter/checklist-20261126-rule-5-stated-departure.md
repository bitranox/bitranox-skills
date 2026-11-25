# skill-writer checklist - coding-consistency (2026-11-26, rule 5 as a stated departure)

Writing rule 5 changes on a user decision: an author MAY add a condition the spec does not carry
when they judge it sensible, and states it as a deliberate departure in the commit message and
in the hand-over (what the condition is, why, what the user sees differently). A condition added
without that statement stays a defect. The review side follows: the `ADDED` verdict is written
`ADDED (stated)` or `ADDED (silent)`, a stated one is listed under "departures for the owner's
decision" and carries no rating, a silent one is a finding rated by what it holds back.

Decisions: d-20261125-8bd24c0f

- [x] Receipt fresh (armed for the session, skill-writer loaded in this agent). Step 0b before
      the edit: `skill_decisions.py show coding-consistency` read; the strict-rule entry
      d-20261125-408ba02e is the one this change supersedes. After the new entry,
      `skill_decisions.py check coding-consistency` reports 0 findings. The ledger tool stamps
      entries in UTC, so the entry made on 2026-11-26 local time carries the id date 20261125.
- [x] Not mirrored: the skill ships only from this marketplace.
- [x] What changed in the text: rule 5; the `ADDED` verdict line; the heading of review step 3
      ("neither `AGREE` nor `ADDED (stated)`"); the one-side exception (now `ADDED (silent)`);
      the "what is seen" bullet and the paragraph after it; the rating sentence; three rows of
      the rationalization table; the execution summary (a fourth returned part); one clause of
      the description. Rule 4 is unchanged and rule 5 says so ("a fixed point you would change
      stays under rule 4").
- [x] Companions: neither `coding-python-consistency` nor `coding-rust-consistency` restates
      rule 5 or the `ADDED` verdict (grep for ADDED, condition, departure: no hit); unchanged.
- [x] The measurement recorded for the strict rule (haiku implementer 2 of 2 runs with a silent
      gate without the skill, 0 of 3 with it) does not carry over to this wording; the ledger
      entry says so.

## GREEN on the new text (implementer scenario of the 2026-11-25 checklist, 2 cells)

- [x] Probe set-up as on 2026-11-25: headless, no tools, a fresh empty working directory, the
      first assistant text block; the prompt carries this SKILL.md and the Python companion.
- [x] haiku, 1 run: adds `ALERT_MIN_SAMPLE = 10` and states it in its hand-over under
      "Departure from the design (stated)" with all three parts: "What: no 'SLA at risk' line
      while the response window holds fewer than `ALERT_MIN_SAMPLE` (10) counted tickets",
      "Why: the product owner reports an alert that flapped", "What the user sees differently:
      on a board with fewer than 10 counted tickets in the store, the alert stays silent where
      5.1 would raise it". The gate is a STATED departure, not a silent one. It wrote no commit
      message: the task hands back files only.
- [x] opus, 1 run: no condition added ("I added no minimum sample size, sustain timer or
      cooldown to the alert"); the question goes to the owner with an offer to add it "as a
      stated departure".
- [x] Against the strict text: under it haiku added no gate (0 of 3); under this text it adds
      one and states it (1 of 1). That is the behaviour the decision asks for. One run per
      tier; no rate is claimed.

## REFACTOR

- [x] CLOSED (both arms): no commit exists when files are handed back. Rule 5 now says the
      statement then stands under its own heading at the top of the hand-over, and the verdict
      text says a change without a commit carries it in the hand-over alone.
- [x] DECLINED (recorded on 2026-11-25, unchanged by this edit): whether an author returns a
      pair table, moving reviewed code to a shared home, defaults for fields the first path
      does not have, the unit of a rounded threshold, running nothing in a text-only probe.
- [x] DECLINED (judgement): whether a stakeholder's note is part of the spec or a request
      against it; rule 4 names "a request from somewhere else" and the arm applied it.
- [x] Not re-probed after the no-commit sentence: it adds a channel rule for a case both arms
      named and changes no other line.
- [x] Width and fence check: no line over 100 columns outside the front-matter description,
      the tables and the fenced row format; every fence closed; ASCII only; the rationalization
      table's rows all 243 columns wide.

## Other checks

- [x] Description: 713 characters, starts "Use when", parses to `['description', 'name']`;
      the changed clause reads "adds a condition the spec never asked for without stating the
      departure".
- [x] Trigger map and catalogue regenerated and in sync (90 skills).
- [x] Text test `hooks/tests/test_consistency_skill_family_text.py` gains two tests: rule 5
      keeps the permission, both channels, the three statement parts, the suppression reason
      and the defect sentence; the review text keeps the stated/silent split.
- [x] CHANGELOG 11.24.0 does not describe rule 5 ("rules for whoever writes the change");
      unchanged. Version stays 11.24.0, which origin does not hold yet.
