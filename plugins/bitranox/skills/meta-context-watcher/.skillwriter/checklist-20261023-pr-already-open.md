# skill-writer checklist - meta-context-watcher (2026-10-23, a "waits for a push go" PR line is a snapshot)

One paragraph is added to "When you are the one READING a handover", after the
blocked-on-the-maintainer paragraph: a line saying a PR still waits for a push go, or has not been
opened yet, is checked against the PR itself and the target's default branch before any push or
"still wanted?" question reaches the user.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: discipline/reference; the test is retrieval plus application - what to check
      before relaying a "waiting for the push go" line, and what each finding turns the item into.
- [x] Inherited coverage: the memory index holds a rule for "blocked on the maintainer" PR lines
      (backlogcheck `--pr-repo`) but none for an unopened or unpushed PR, so the behavioural arms
      are valid; they still run as `bitranox:baseline-probe` arms with the pasted text and no tools.
- [x] RED (haiku and opus, the pre-change section): Q1 "check anything about this PR first?"
      answered NONE on both tiers; both would put the "still wanted?" question to the user
      directly. Both named the gap themselves: the stale-PR rule covers only a PR "blocked on the
      maintainer", not a drafted PR that may since have been opened or fixed upstream.
- [x] GREEN (haiku, and opus at effort medium; the edited section): every question answered by a
      direct quote of the new paragraph on both tiers - look for the PR first (`--head` or the
      author search), check the default branch, an open PR is a maintainer wait, an upstream fix
      closes the item.
- [x] Diffed both ways: no RED answer lost; the only changed answers are the intended ones.
- [x] GREEN gaps, each decided:
      - "an upstream fix of its own" had no test - CLOSED: "grep it for a symbol unique to the
        change, and judge a hit by its diff fixing the same defect, never by its title alone."
      - `--author @me` misses PRs opened by another account - CLOSED: "--author <the account that
        opens our PRs>".
      - a search miss read as "no PR" - CLOSED: "a search miss proves nothing until the words are
        widened."
      - a PR closed unmerged fit no branch - CLOSED: "a PR closed unmerged goes back to the user
        with its close reason".
      - the backlog line after the check - CLOSED: "rewrite the item's line to what you found
        before you report it."
      - "the paragraph above" was ambiguous - CLOSED: "the blocked-on-the-maintainer paragraph
        above applies".
      - `<owner>/<repo>` and the account are placeholders - DECLINED: they depend on the item's
        repo, which the line names.
      - what to ask the user after a PR closed unmerged - DECLINED: that is the user's decision; the
        text hands it over with the close reason.
      - how many search variants count as "widened" - DECLINED: judgement, no fixed count is right.
- [x] Each closed gap verified by a haiku re-probe on the final text (quote-back, five questions,
      all five answered by a direct quote). Its remaining gaps were the three DECLINED above, plus
      the reference file not being pasted, which ships as `references/stale-pr-verdict.md`.
- [x] Tiers: RED haiku + opus; GREEN haiku + opus (effort medium); re-probe haiku - 5 cells.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
