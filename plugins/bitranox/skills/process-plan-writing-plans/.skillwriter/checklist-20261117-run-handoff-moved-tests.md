# checklist - Self-Review: the run stays owed and may be handed off; imports of moved tests

Self-Review item 9 (run the plan's code) says it stays owed when a subagent drafted the tasks and
that its run is the one part of the review that may be handed off: a pinned `opus` agent, briefed
with the item's text and its three traps, in a scratch clone, ending with the full gate, returning
each defect and surviving battery arm with command and output. Judging and folding in stay with
the author. The Capability check and the Self-Review opener, which both said the review is not a
subagent dispatch, now name that one exception. Item 8 gains a rule for a task that moves tests
between repos: list each moved test's imports against the target repo before dispatch.

Decisions: d-20261117-7963c668, d-20261117-62222b50

## RED

- [x] Skill decisions read first (`skill_decisions.py show`, also `--kind rejected,removed
      --full`): one rejected entry (no fixed numbers in item 7), not touched by this edit. No
      entry records "the Self-Review is not delegable"; that sentence was unanchored text.
- [x] Coverage check on the pre-edit text (`git show HEAD:` excerpt: Capability check plus the
      whole Self-Review), quote-back probe, opus, five questions. "May any part be handed off":
      quoted "The Self-Review below is NOT delegable at any tier", so none. "Who folds in defects
      from a run someone else did": NONE. "Check before dispatching a task that moves tests":
      NONE. "Still owed when a subagent drafted the tasks": yes, but only by inference from the
      non-delegable sentence. Control (may item 1 be delegated): no.

## GREEN

- [x] The command the edit adds was executed: `git clone -q --no-local . <scratch dir>` from the
      repo, rc 0, the clone held the `plugins` directory; removed by exact path.
- [x] Same five questions on the edited text, opus and haiku (2 tiers, 10 cells): each quoted the
      new sentence for the owed run, the hand-off (model, scratch clone command, full gate), who
      folds in, and the moved-tests check; control unchanged on both tiers (item 1 stays with the
      author).
- [x] GREEN diffed against RED in both directions: no baseline answer lost; "is the run still
      owed" moved from an inference to a quoted sentence.

## REFACTOR

- [x] Every dispatch asked for a `Skill gaps` section; all lists recorded and decided below.
- [x] Closed: "does the delegated agent judge a surviving arm" - it returns each defect and each
      surviving battery arm; judging them stays with the author.
- [x] Closed: "what goes in the brief" - the item's text, the three traps included.
- [x] Closed: "is the review finished while the run is out" - not until its results are judged
      and folded in.
- [x] Closed: "one part you may hand off" read beside the decomposition hand-off as a limit on
      all delegation (haiku) - the sentence now says "one part of the Self-Review".
- [x] Declined: "may the scratch-copy runs of items 8 and 14 go with it" - out of scope; the
      measured incident covers item 9's run only, and the entry's reopen_if names this case.
- [x] Declined: "the stated reason (the plan YOU wrote) does not hold when a subagent drafted it"
      and "does a lesser-tier session still run the review itself" - reported by RED and GREEN
      alike; who owns the review after a delegated draft is a policy question for the maintainer,
      out of scope for this edit. The rule itself ("at any tier") is unambiguous.
- [x] Declined: "clone versus virtualenv" - covered in the same item: "A scratch copy run on the
      main checkout's virtualenv, where the package is installed editable, imports the MAIN
      checkout's source" with the `PYTHONPATH=<scratch>/src` remedy, and the brief carries it.
- [x] Declined: "run again after folding many defects" - the closing rule "No need to re-review,
      just fix and move on" governs; changing it is out of scope.
- [x] Declined: "how to pin a model" - covered elsewhere: the Capability check points at
      `bitranox:process-agents-subagent-driven-development`, whose SKILL.md has the section
      "Concrete tiers (canonical mapping - other skills reference this section)".
- [x] Declined: "which command is the full gate, which repo, where the scratch dir goes, which
      commit to clone" - the repo's own; judgement the skill leaves open.
- [x] Declined: "item 9 when the plan has no complete code" - the item's own condition ("When the
      plan carries complete code and tests") answers it.
- [x] Declined: "what if the delegated run never returns" - owned by
      `bitranox:process-agents-dispatching-parallel` and the dispatch skills.
- [x] Re-probe of the touched questions after each fix round, opus (effort medium) and haiku:
      five questions after round one, two after the wording fix. Final run, both tiers: "one
      part" quoted as "The one part of the Self-Review you may hand off is the run of the plan's
      code", decomposition still delegable, item 1 not; no new undecided gap.
- [x] Width, fence and non-ASCII check over the added lines printed nothing after each round; the
      paragraphs after each insertion point read (item 9 after the item 8 addition, item 10 after
      the item 9 addition), no back-reference re-bound; "Three ways" still matches its three
      bullets.
- [x] Cases the edit decides beyond the proposal, for the maintainer: the brief contents, the
      full gate at the end of the run, and "the review is not finished until that is done".
