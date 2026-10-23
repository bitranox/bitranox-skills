# skill-writer checklist - meta-context-watcher (2026-10-23, a solved backlog line is deleted)

The default closing rule changes from "`- [x]` plus `| closed: <reason>`; the line stays" to "a
solved item's line is deleted, the reason in the commit message", matching `open_work.close_item`
and the `backlog_close` tool, which now delete the line. Four passages change: the closing rule
and its header-governs paragraph, the moved-item clause, the free-rank paragraph, and reconcile
step 2.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: discipline/reference; the test is retrieval - what happens to a solved line,
      where its reason goes, a moved item, a reconcile, a file whose header keeps closed lines, an
      untracked backlog, rank reuse.
- [x] Inherited coverage: the tree-top memory store now holds a fact stating the same rule
      (`feedback-delete-solved-open-work-lines-everywhere`), so a behavioural arm here would answer
      from it. The coverage check is therefore a text check of the passages, pasted into
      `bitranox:baseline-probe` arms with no tools, every answer a direct quote or NONE.
- [x] RED (haiku, the pre-change passages): all five questions answered by quoting the old rule -
      "Closing an item is `- [x]` plus `| closed: <reason>`; the line stays.", the moved item's
      "keeps at most a closed line", reconcile's "gets `- [x]` and a reason". Its gaps also showed
      the old header example contradicted the default ("a solved item is DELETED" given as the
      exception).
- [x] GREEN (haiku, and opus at effort medium; the edited passages): seven questions, every answer
      a direct quote of the new text on both tiers (deleted line, reason in the commit message, the
      moved item's line deleted, reconcile deletes, header governs, untracked backlog first puts
      the reason somewhere durable, a deleted line holds no number).
- [x] Diffed both ways: no RED answer lost; every changed answer is the intended change.
- [x] GREEN gaps, each decided:
      - rank reuse would make "rank N" name two items in history - CLOSED: "prefer a fresh number
        to one just freed: old handovers and commit messages still name the deleted item by its
        rank."
      - "somewhere durable" unnamed - CLOSED: "a CHANGELOG entry, a tracked decision log, a commit
        message of the change itself".
      - an untracked backlog has no commit for the reconcile step's reason - CLOSED: step 2 points
        at the durable-place rule.
      - whether `backlog_close` commits or checks tracking - CLOSED: "it neither commits nor
        checks whether the file is tracked" (`close_item` only rewrites the file).
      - a header that keeps closed lines vs a tool that always deletes - CLOSED: "close its items
        by hand, since `backlog_close` always deletes".
      - whether a single closure gets a `measured:`/`argued:` tag - DECLINED: unchanged text, the
        tag exists for a multi-item pass.
      - whether a stub may stay for a moved item - DECLINED: the line is deleted and the commit
        message names where it moved; nothing else is meant to stay.
- [x] Each closed gap verified by a haiku re-probe on the final text (quote-back, five questions,
      all five quoted). Its remaining gaps, both DECLINED: which of the three durable places an
      untracked backlog uses (any of them; the text lists them as equals), and whether a freed rank
      counts as free (it does - "a deleted line holds no number" - and the text gives the
      preference for a fresh one).
- [x] Every claim checked against the code: `close_item` deletes exactly one line and returns
      `{rank, line, reason, deleted}` (`tests/test_open_work.py`), the new-file `HEADER` says a
      solved line is deleted, legacy `- [x]` lines still parse and hold their rank
      (`tests/test_session_start.py` fixtures), the bridge returns the same
      (`tests/test_mod_bridge.py`).
- [x] Tiers: RED haiku; GREEN haiku + opus (effort medium); re-probe haiku - 4 cells.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
