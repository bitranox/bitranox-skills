# checklist-20261104-fix-batches-add-no-behaviour

Change under test: Step 7 gains two paragraphs after "Every fix seeds the next sweep". A fix batch
holds the change each finding needs and its test, nothing else; an addition already merged is put
to the user. When the previous fix batch caused most of a sweep's gate-holding findings, that
batch's diff is reviewed before the next sweep, additions are settled before anything inside them
is fixed, and the full sweep that can end the loop comes after.

The case behind it: a multi-sweep review that did not converge for nine sweeps, most of each
sweep's gate-holding findings sitting in code the previous fix batch had written, including a
settings key and a second reader mode no finding asked for.

## PLAN

- [x] Skill type: technique. The test is application: given a sweep result, does the agent pick
      the next step, scope the fix batch and handle the additions.
- [x] Scope: Step 7 of `SKILL.md` only.

## RED

- [x] Scenario: sweep 9 with five gate-holding findings, four in sweep 8's code, sweep 8 having
      added a settings key and a second reader mode unasked; the user asks why it does not converge.
      Asked: next step, what the batch may contain, what to do with the additions; each answer with
      a governing quote or NONE.
- [x] Inherited coverage: `redcheck.py --corpus-cascade` matched on topic words only; a grep of
      the cascade found neither claim stated, so the arms can fail honestly.
- [x] RED on haiku and opus with the pre-edit Step 7: both went straight to another full sweep
      from Step 2 and quoted NONE for the additions; the scope ban was their own inference.

## GREEN

- [x] Same scenario on haiku and opus with the edited Step 7: both review sweep 8's batch first,
      quoting the new heading sentence; both scope the batch to findings plus tests and put the
      additions to the user, quoting the governing lines.
- [x] Both arms ended with `Skill gaps`; worked below.

## REFACTOR - every gap closed or declined

- [x] GAP (haiku): "the last batch" could mean sweep 8's or the one about to be written. CLOSED -
      heading says "the previous fix batch" and a sentence names it as the batch the finished sweep
      ran over.
- [x] GAP (opus): order of fixing findings inside an addition vs the user's decision. CLOSED -
      settle the additions before fixing anything inside them; a reverted addition takes its
      findings with it; findings outside need not wait.
- [x] GAP (opus): a standing user rule ("every behaviour switch gets a settings key") can make an
      addition look requested. CLOSED - one sentence: such a rule shapes the change a finding asks
      for and never makes an addition requested.
- [x] GAP (both): no method for tracing a finding to a hunk. DECLINED - the "caused by the last
      sweep's fixes" column already exists and its attribution is unchanged by this edit.
- [x] GAP (opus): "keep it as its own change" and "already merged" undefined. DECLINED - the user
      decides the form when asked; prescribing branch mechanics here would over-fit.
- [x] GAP (recheck): a revert can conflict with a standing rule (a hard-coded value returns).
      DECLINED - that is a downside of the revert option, which the question to the user carries
      per `process-review-uncertain-decisions`.
- [x] GAP (all): elided excerpt parts. DECLINED - artefact of the probe excerpt, not of the skill.
- [x] Quote-back re-check on haiku after the refactor: right batch, rule not a request, order
      after the decision, each with a direct quote of the new lines.

## Quality

- [x] Description unchanged.
- [x] Added lines ASCII and within width; the following "The last sweep" paragraph re-read: its
      "rule above" now names the cheap-or-accept rule, not the new paragraph.
- [x] No narrative, no scratch paths.

## Deployment

- [x] Version bumped in `plugin.json` and `pyproject.toml`; CHANGELOG entry; `repo-gate.py` before
      the push.
