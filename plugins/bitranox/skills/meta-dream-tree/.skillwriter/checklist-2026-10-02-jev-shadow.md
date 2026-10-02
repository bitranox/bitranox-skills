# Skill-writer checklist: Jev shadow on placement, firing and prune (2026-10-02)

Scope: three steps of the dream gain one nested bullet each for a store-based Jev shadow site:
step 5 `dream-placement`, step 6 `dream-firing`, step 7 `dream-prune`. Each bullet: gated on
`jev_shadow.py status`, items built with `jev_shadow.py items --site <site> --anchor <anchor>`,
the agent's own verdicts written to `verdicts.jsonl` before `jev_shadow.py run`, the step's
outcome taken from those verdicts. Step 11's report line gains `jev shadow:` with the counts
`run` printed per site; the family verification contract in `references/dream-core.md` names the
same line so the two stay consistent. The procedure detail stays in
`meta-self-improve/references/jev-shadow.md`, cited with its home and launch shim in step 5 and
by reference from steps 6 and 7. Technique edit; no name, description, trigger or table row
changed, so the derived docs and triggers do not move.

## Volume per site (measured, `items` is read-only and free)

- [x] `jev_shadow.py items` against one real tree anchor: `dream-firing` 1313 items and
      `dream-prune` 1313 items (one per fact); `dream-placement` 46209 items (1313 facts times
      every level on each fact's chain, 3 to 109 pairs per fact, 109 levels).
- [x] `run` sends EVERY line of `items.jsonl` to Jev, whatever the verdicts file holds
      (`jev_shadow.py` `_ask_and_log` builds the request from all items; verdicts only decide
      pairing). Logged cost so far is about $0.000044 per item, so firing or prune over the whole
      store is a few cents, and placement over every pair is about $2 per dream plus a jev-judge
      run over 46k rows.
- [x] Decision, firing and prune: a verdict for EVERY fact, none left out, because both steps
      already cover the whole store (step 6 sweeps the whole store, step 7 asks both questions of
      every entry). The bullet maps the step's own output onto the verdict: `false` for each hook
      the agent queues, `true` for the rest; `true` for each prune question a fact trips.
- [x] Decision, placement: a stated subset. The agent cannot judge 46k pairs and its routing
      produces one chosen level per fact, not a score per pair. The bullet keeps each fact's line
      for its current level and for the level the agent routed it to (one line when it stays),
      at most two per fact (about 2600 on the measured tree), and cuts `items.jsonl` to those lines
      BEFORE `run` so Jev is asked only about paired items. Lines are kept unchanged: the agent
      selects lines, never edits a state field, so no field can carry the answer.

## PLAN

- [x] Skill type: technique steps inside a process skill. Test approach: application scenario on
      the least inferential tier (haiku), inert probe type `bitranox:baseline-probe`, step text
      (and in GREEN the reference's procedure section) supplied in the prompt.
- [x] One fixture for all three sites: a four-level tree (`.`, `projects`, `projects/webshop`,
      `projects/reportgen`) with scope descriptors and 20 facts. Planted: four misplaced facts
      (two down, two up) and one cross-boundary fact (`gh-exit-4`); three hooks failing the firing
      check (`rsync-progress` trigger-less, `pytest-notes` a title, `stripe-test-cards` naming the
      wrong situation); two undated negative claims (`weasyprint-svg`, `pdf-merge-forms`) and two
      unlabelled unsolved sessions (`celery-beat-drift`, `pdf-merge-forms`). Settings in every arm:
      `classifier_backend = jev`, `classifier_skills = shadow`, a Jev key present.

## RED (current text)

- [x] Inherited coverage: `redcheck.py --corpus-cascade` over the worktree read 1324 documents
      and flagged the scenario, every shared term being fixture vocabulary (`bcrypt`, `batchmode`,
      `burned`, `compose`). A search of every CLAUDE.md and CLAUDE.local.md on the chain and every
      memory fact body for the lesson's own terms (`jev_shadow`, `verdicts.jsonl`,
      `dream-placement`, `dream-firing`, `dream-prune`, `classifier_skills`) found 0. The
      behavioural arms were kept.
- [x] Placement: no verdicts file, no items, no `jev_shadow.py` command. Five moves by its own
      routing. `Skill gaps`: "Jev not invoked ... does dreamer invoke classifier for PLACEMENT, or
      only on LOW/UNSURE?"
- [x] Firing: no verdicts file, no `jev_shadow.py`. Queued `rsync-progress`, `pytest-notes`,
      `stripe-test-cards`.
- [x] Prune, two arms: neither wrote a verdicts file or ran `jev_shadow.py`. Both relabelled
      `celery-beat-drift` and `pdf-merge-forms` unsolved; neither flagged `weasyprint-svg` under
      question 1 (arm 2: "no facts are pure negations"). Both deleted `stripe-test-cards` as
      "corrupted" or an "unusable stub"; arm 1 also deleted `webshop-stripe-webhook-secret` as
      task state.
- [x] RED outcome as predicted: with the knob on, no site produces a verdicts file or a shadow
      run on the current text.

## GREEN (new text, plus the reference's procedure section)

- [x] Placement arm 1: cut `items.jsonl` from 71 lines, wrote verdicts (`ssh-batchmode|.` 2,
      `ssh-batchmode|projects/reportgen` 1, a moved fact's old level 0), then `run`, then the same
      five moves "by own routing". It listed no `items` command and counted 28 kept lines where
      25 is right.
- [x] Placement arm 2: wrote verdicts, ran `run`, and only THEN cut `items.jsonl` ("Edit
      items.jsonl: delete 46 lines" as command 3, after `run`), so Jev would have been asked
      about every pair. No `items` command; reported `jev shadow: off` although status was on.
- [x] Firing arm 1: `items`, 20 verdicts with `false` on `rsync-progress`, `pytest-notes`,
      `stripe-test-cards`, then `run`; queued those three; "Jev agreement counts are reported but
      do not affect queuing - I act on my own verdicts."
- [x] Firing arm 2: `items`, 20 verdicts, `run`; queued `pytest-notes` and `stripe-test-cards`,
      not `rsync-progress` (see REFACTOR).
- [x] Prune arm 1: `items`, 20 verdicts, `run`; re-test `weasyprint-svg`, relabel
      `celery-beat-drift` and `pdf-merge-forms`. It also answered `untestable_negative` true for
      `celery-beat-drift`, which makes no tool claim.
- [x] Prune arm 2: `items`, verdicts (`weasyprint-svg` q1, `celery-beat-drift` q2,
      `pdf-merge-forms` both), then `run`; actions "Based on my own verdicts (not Jev's agreement
      scores)": re-test both negatives, relabel both unsolved.
- [x] GREEN `Skill gaps`: unsolved-label format (prune 1, 2, 3); removal policy file not in the
      prompt (prune 1, 2); engine invocation and success-line text (placement 1); `<plugin>` and
      anchor resolution (placement 1); what Jev disagreement changes (placement 1, 3, prune 1);
      UNSURE has no slot in the 0-2 score (placement 3); score for the level a fact leaves, 0 or 1
      (placement 1, 4); whether `note` is wanted (firing 2); trigger-less versus vague triggers as
      separate problems (firing 1).
- [x] The documented shapes executed against the shipped tool: one real item per site and one
      verdict in exactly the documented shape, read back by `jev_shadow.read_items` and
      `read_verdicts` (`Verdict(answers={'fits_level': 2})`, `{'trigger_fires': False}`,
      `{'untestable_negative': False, 'unlabelled_unsolved': True}`); `run` with no verdicts file
      exits 2 for all three sites; `status`, `items --help` and `run --help` list every flag the
      text names. Nothing that costs money was run.

## REFACTOR

- [x] GREEN diffed against RED both ways. Gained, all arms: the items, verdicts before `run`, the
      `run` command with the right site, and the step's outcome from own verdicts. Prune also
      gained question 1: both GREEN arms flagged `weasyprint-svg`, both RED arms missed it. Kept:
      placement makes the same five moves as RED; firing queues the same three hooks in 2 of 3
      arms; prune relabels the same two facts.
- [x] Lost, firing: `rsync-progress` missing in GREEN firing arm 2. Re-run with the same prompt
      (firing arm 3): it queued all three with `rsync-progress` "Missing trigger entirely". Present
      in 2 of 3 GREEN arms and the bullet names a missing trigger as `false`, so it is run
      variance, not a result the edit displaced.
- [x] Lost, prune: the RED deletions of `stripe-test-cards` and `webshop-stripe-webhook-secret`
      do not appear in GREEN. Both were wrong (`stripe-test-cards` has a bad hook, which is step
      6's rewrite, not a prune; the webhook fact is a reusable fix). To check the archive
      judgement itself survives, prune arm 3 added a planted task-state entry
      (`refund-button-wip`, "in progress on branch feat/refund, Lena reviews Thursday"): it was
      archived as task state beside the two shadow questions, so the bullet does not displace the
      removal policy.
- [x] CLOSED, placement order: arm 2 cut `items.jsonl` after `run`, and arms 1 and 2 omitted the
      `items` command. The bullet now numbers the sequence, (1) `items`, (2) route, (3) cut
      `items.jsonl`, "BEFORE `run`, which asks Jev about every line in the file", (4) verdicts,
      (5) `run`. Re-tested with placement arms 3 and 4 on the final text: both ran `items`, cut to
      25 lines (the correct count), wrote verdicts, then `run`, then moved by own routing.
- [x] CLOSED, report line: placement arm 2 reported `jev shadow: off` with status on. Step 11 now
      says `off (<reason>)` is for when `status` was not 0. Arms 3 and 4 reported the counts line.
- [x] DECLINED, unsolved-label format and the removal policy: owned by step 7 and
      `references/dream-passes.md`, unchanged by this edit; RED arms raised the same gaps.
- [x] DECLINED, engine invocation, success-line text, `<plugin>` and anchor: the engine command
      table lives in `meta-self-improve` `references/memory-backend.md`, required background for
      the dream; the bullets give the shadow tool's home and shim as every script reference does.
- [x] DECLINED, what Jev disagreement changes: nothing, and every bullet says so ("whatever `run`
      printed or exited with"); disagreements are read afterwards with `report`, per the
      reference.
- [x] DECLINED, UNSURE and the 0-or-1 score for a level a fact leaves: the three criteria are the
      score's definition; an UNSURE fact stays and its current-level line is scored as the agent
      judges it. Placement arms 1 and 4 chose 0 or 1 for a departing level by those criteria.
- [x] DECLINED, `note` and trigger-less versus vague: `note` is optional per the reference, and
      the firing bullet names a missing trigger and a misnamed one as the same `false`.
- [x] DECLINED, `celery-beat-drift` answered `untestable_negative` in prune arm 1: a judgement
      error on the existing question, not an instruction gap; prune arms 2 and 3 answered it
      correctly.
- [x] Noted, outside this edit: placement arms in RED and GREEN alike moved `ssh-batchmode` and
      `gh-exit-4` to the tree top although `should-promote` printed `hold`, the corroboration gate
      in the existing step 5 text. Same in RED, so not caused by this edit.

## Fix round 1 (review findings)

- [x] `meta-self-improve/references/jev-shadow.md` procedure step 2 said items may be left out
      ("nothing is paired for them") without saying that `run` asks Jev about, and pays for, every
      line of `items.jsonl` whatever the verdicts hold (`cmd_run` and `_ask_and_log` build the
      request from all parsed items; verdicts only feed the log). Step 2 now adds: "A missing
      verdict loses only the pairing: `run` still asks Jev about, and pays for, EVERY line in
      `items.jsonl`. To keep an item from being asked, delete its line from `items.jsonl`
      (unchanged otherwise) BEFORE `run`." The placement bullet's step (3) already says the same
      ("BEFORE `run`, which asks Jev about every line in the file"), so it reads consistently and
      is unchanged.
- [x] Step 11's "`jev shadow:` the counts line `run` printed per site" could produce
      `jev shadow: shadow: N items, ...`. It now reads: `jev shadow:` followed by `<site> <counts>`
      per site, joined by `; `, the counts being what `run` printed after its own `shadow:`
      prefix, `<site> off (<reason>)` when `status` was not 0, `<site> error <message>` on a
      non-zero `run`, with an example line. The verification contract in `references/dream-core.md`
      says the same: one `jev shadow:` line naming each shadow site with the counts `run` printed
      after its own `shadow:` prefix, or `off (<reason>)`.
- [x] Quote-back, one haiku `bitranox:baseline-probe` arm given the final procedure section and
      the final step 11 rule, 500 items of which 40 judged. Q1 (are the 460 unjudged asked and
      paid for?): quoted "`run` still asks Jev about, and pays for, EVERY line in `items.jsonl`."
      - yes. Q2 (how to avoid it?): quoted "delete its line from `items.jsonl` (unchanged
      otherwise) BEFORE `run`." Q3 (may the kept lines be tidied?): "No ... 'unchanged otherwise'
      forbids it." Q4 wrote `jev shadow: dream-prune 40 items, 40 paired, 31 of 40 answers agreed,
      0 without a Jev answer, ~$0.001760; dream-firing off (no key)`, no doubled prefix.
      `Skill gaps`: the site table and the other report categories were not in the excerpt it was
      given, both probe-scope artifacts; declined.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, credential, hostname, address or real user path; the
      only path is `<plugin>/skills/meta-self-improve/`. The shadow steps send nothing unless the
      user turned both knobs on, and the tool redacts secrets before sending.
- [x] Added lines ASCII only and within 100 columns.
- [x] No session narrative or scratch path in the skill text or this artifact.
