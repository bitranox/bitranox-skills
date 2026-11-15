# meta-skill-ab-test: login pause, sealed max_tokens, CLAUDE*.md drift between arms

Rules added under "Before and during a live run": a login pause is answered with `/login` and the
same `run` command (a cheap `claude -p` call does not renew it); `max_tokens` is sealed, so an arm
that hit `token_cap` reruns in a new run dir with `--only <arm name>`, and an old arm that ended
`finished` may still be judged beside it; keep the memory store quiet, since `run` now records each
arm's `CLAUDE.md`/`CLAUDE.local.md` hashes (`context_files`) and `score` flags an arm whose files
differ from the first arm's. Code: `abarm.context_files`, `abtest._add_context_drift` and
`_context_flag`, and the pause message naming `/login` (tests
`test_context_files_hashes_every_claude_md_of_the_worktree_and_its_ancestors`,
`test_context_files_marks_an_unreadable_file_instead_of_skipping_it`,
`test_score_flags_an_arm_that_started_on_other_claude_md_text_than_the_first`,
`test_an_ancestor_claude_local_md_edited_between_arms_flags_the_later_arm`, and the `/login`
assertion in `test_an_arm_is_not_started_on_a_login_that_lapses_before_its_deadline`; each failed
before the code change).

Declined:
- A per-arm host-file override by a hand-added `--ro-bind` in `abarm.sandbox_argv`: outside the
  sealed inputs and unrecorded per arm (ledger `rejected` entry).
- An arm that ended `deadline` judged beside a new run's arms (both GREEN tiers answered NONE): a
  judgement the text leaves to the operator; only `finished` is stated as unaffected by the cap.
- A fact body under `.claude-memory/facts/` changed between arms is not hashed: bodies are read on
  demand during the session, not loaded at its start, and the store guard already records a change
  inside an arm.
- A change made before the first arm starts: every arm then sees the same text, so there is no
  drift between arms to flag.
- Where and in what form "say so beside it" goes, and how to bring an old run's diffs to the judges:
  the judging section owns the report's form.

- [x] Step 0b: `skill_decisions.py show` run before the first edit; no rejected or removed entry
      exists, and the edited `deadline_s` bullet keeps its rule anchor.
- [x] RED: the pre-edit text has zero hits for `max_tokens`, `/login`, `context_files`,
      `CLAUDE.local` and `ancestor`. Text-only probes (`opus`, `haiku`) given the pre-edit excerpt
      answered NONE or guessed on all three questions: no cap rule, no `/login`, no way to find the
      affected arms. The login lesson is in this machine's memory index, so the text check is the
      evidence for that question.
- [x] GREEN: the same questions with the edited text on `opus` (effort medium) and `haiku`: both
      quoted the new sentences and answered all three; every dispatch ended in a `Skill gaps`
      section.
- [x] Gaps closed: resume by rerunning `run`; `PREREG.md` added to the copy list; `--only` takes the
      arm's name (both tiers had written `--only r1-V2`); "copy in every variant". The re-probe of
      the touched question on the final text found no new undecided gap.
- [x] Every mechanism claim was checked against the code: `max_tokens` is refused after the seal
      (test_abtest committed max_tokens case), `--only` takes "C or a variant name" (abtest.py
      run parser), the flag text and `null` drift come from `_context_flag`/`_add_context_drift`.
- [x] Width, backtick and non-ASCII checks over the added lines printed nothing; the paragraph after
      each insertion point was read.
- [x] No session narrative, private path or history line was added.

- [x] Decisions: d-20261115-d0fc4b38, d-20261115-32651f6f, d-20261115-07827fe8, d-20261115-a89fc980
