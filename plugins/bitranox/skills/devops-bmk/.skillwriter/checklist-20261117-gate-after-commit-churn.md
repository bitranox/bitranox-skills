# Review checklist - a gate run after the commit it gates leaves its rewrites unpushed (2026-11-17)

Change: the "`make test` mutates the tree" bullet in section 3 gains three sentences. `ruff format`
runs over the whole tree and reformats the fenced Python code blocks in Markdown files; a gate run
after the commit it gates (`make test && git push`, or a gate jig with a `--then "git push"`
action) pushes that commit without the gate's rewrites, so `git status --porcelain` is read after
every gate run and bmk's changes committed; with the change already committed a separate chore
commit is as good as amending, and the only form after the push. The bullet's last sentence now
points at "the `push` point below" (it read "next point", but another bullet stands between).
Frontmatter unchanged.

## PLAN
- [x] Skill type: reference. Test: a retrieval and application probe on the pre-edit bullets
      (RED) and on the edited bullets (GREEN), text-only baseline-probe agents, plus a text
      coverage check of the pre-edit file.
- [x] Ledger read (`skill_decisions.py show devops-bmk`, also `--kind rejected,removed --full`):
      no rejected or removed entry covers a gate run over an already-made commit.
      d-20261106-dfc4967b (no exception to "commit the floor churn make test leaves") stands:
      the new text adds no exception, it says when and how that churn is committed.

## RED
- [x] Coverage check of the pre-edit file (`git show HEAD:<path>`): `grep -c -i markdown` 0,
      `grep -c -- '--then'` 0, `grep -c 'make test && git push'` 0.
- [x] Probe (opus, 1 cell) on the pre-edit "mutates the tree" and `push` bullets; scenario: three
      commits made, `make test && git push` both green, a Markdown plan with fenced python blocks
      in the repo, about to report everything pushed. It chose the right action (read
      `git status --porcelain`, commit the churn) but called it "my inference; no sentence in the
      excerpt says it about this sequence". Can the gate have changed the Markdown plan: NONE.
      Amend or separate commit: NONE. Gaps it listed: the text never mentions
      `make test && git push`, and the bold line "bmk's own churn ships with your change" is false
      on that path; silent on Markdown; silent on amend versus follow-up commit once pushed.
- [x] The arms tie on the action; the finding is the RED arm's reason (inference, three NONE).

## GREEN
- [x] Claims executed before the probe. `ruff --version` in bmk 3.33.3's tool env: `ruff 0.17.4`.
      A scratch project with a `.md` holding a fenced python block `x = {  "a":1 }`:
      `ruff format --isolated .` printed `1 file reformatted` and the block read `x = {"a": 1}`.
      bmk's format stage command is `["ruff", "format", "."]` (bmk `adapters/stagerunner/tools.py`
      line 52). The gate jig documents `--then "git push origin HEAD"`
      (`skills/compuse-toolbox/scripts/gate.py` line 95).
- [x] Same probe on the edited bullets, opus and haiku (2 cells): both read
      `git status --porcelain` first and committed the churn as a chore commit; both quoted
      "pushes that commit WITHOUT the rewrites the gate just made", the Markdown sentence, and
      "a separate chore commit for the churn is as good as amending it in". Control (nothing
      committed yet): both quoted "commit them with your change, a docs-only change included", so
      the addition does not pull churn out of an uncommitted change.

## REFACTOR
- [x] GREEN against RED in both directions: every RED action is in GREEN; nothing lost.
- [x] Skill gaps reported, each decided:
  - "as good as amending" treats the two as equal though amending a pushed commit needs a
    force-push (opus GREEN): closed, the sentence now ends "after the push it is the only form,
    since amending a pushed commit needs a force-push".
  - "(next point)" does not lead to the restore step (RED, both GREEN): closed, it now reads
    "(the `push` point below)", where `git checkout -- <file>` is stated.
  - Order numbers 20 and 30 named for ruff and again for `build`/`test` and `clean` (RED):
    declined, the two bullets name different pipelines in their own words ("Its first stages" of
    `make test`; "`push` commits AFTER its gate: `update_deps` (order 10), `build` and `test`
    (20)").
  - Whether to gate again on the chore commit, and CI on the commits already pushed (opus GREEN):
    declined, owned by other text of the skill and outside this addition; the bullet above
    already has churn from a `make test` committed and pushed with CI awaited before a release.
  - "section 4" and "an exact pin excepted, below" not in the excerpt: declined, both resolve in
    the full SKILL.md (the excerpt cut them off).
  - How to word a floor bump in the commit message: declined, judgement the skill leaves open.
- [x] Quote-back on the final text, questions the fixes touched (haiku, 1 cell; opus at effort
      medium, 1 cell): see the last section.
- [x] Width and fence check over the added lines (451-458): nothing reported. The sentence after
      the insertion ("Files your TEST SUITE rewrites are different") still contrasts with bmk's
      churn, which the inserted sentences are also about.
- [x] ASCII only; no address, hostname or private path added; no history wording added.
- [x] Reconciled with the bullet's "commit them with your change": that stays the rule for an
      uncommitted change; the separate commit is offered only "With your change already
      committed".
- [x] Decisions: d-20261117-43ef1ecf

## Quote-back on the final text
- [x] haiku. Amend after the push: "after the push it is the only form, since amending a pushed
      commit needs a force-push." Not pushed yet: "With your change already committed, a separate
      chore commit for the churn is as good as amending it in". A snapshot a test rewrote: "read
      the diff of each file the tests rewrote and `git checkout -- <file>` it (or make the test
      write to `tmp_path`)". Nothing committed yet: "commit them with your change, a docs-only
      change included". No new undecided gap: its list repeats the declined cross-references and
      notes the text states the force-push cost, not a bare prohibition (left as written: the
      sentence already names the separate commit as the only form).
- [x] opus (effort medium): the same four quotes, one per question. Gaps it listed, each
      decided: no tie-breaker between amend and chore commit before the push (declined,
      judgement the skill leaves open: the text says either is fine); a snapshot regenerated on
      purpose, a file both a test and ruff rewrote, and how to know a repo's tests rewrite
      tracked files (declined, they concern the `push` bullet's restore rule, which this change
      does not edit, and that bullet has the reader "read the diff of each file the tests
      rewrote" before restoring); CI on the commit pushed without the rewrites (declined above).
      No new undecided gap from either tier.
