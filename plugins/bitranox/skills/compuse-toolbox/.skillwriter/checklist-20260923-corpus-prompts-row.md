# compuse-toolbox: add the `corpus_prompts` row

Change under review: one row added to the tool index for a new jig that replays typed PROMPTS
through a predicate. Frontmatter untouched. Diff against origin/master is +1 line.

Skill type: REFERENCE (a routing table). Test approach: retrieval, per "Testing All Skill Types".

## PLAN

- [x] Skill type identified: reference. The change is a routing row, so the question is whether a
      reader can find the right tool from the table, not whether they comply with a rule.
- [x] Test approach chosen: retrieval scenario, one arm without the row and one with it.
- [x] Scope: the row only. No supporting file, no frontmatter change.
- [x] Risk named before testing: the new jig's nearest neighbour is `guard_replay`, which also
      walks the transcript corpus. The failure this test exists to catch is two rows that sound
      equally plausible for the same query.

## RED

- [x] Scenario run WITHOUT the row, against the table's real text for the nearest candidates
      (`jsonl_grep`, `claim_check`, `transcript_tail`, `transcript_index`, `diffbehave`,
      `guard_replay`). Verdict: **NONE**. Verbatim: "nothing in the index does 'replay a
      message-authorship classifier over the whole corpus, tally firing rate per version, and
      diff regressions between two versions' in one piece."
- [x] The baseline does not falsely pass. It reaches for a three-part hand-assembly
      (`transcript_tail` or `jsonl_grep` to extract, a hand-written loop to tally, `diffbehave`
      to diff), and states it would "queue this composition as a toolbox contribution afterward,
      since [this] is a recurring chore this session had to hand-assemble from parts" - it
      identifies the gap the row fills without being told of it.
- [x] Contamination ruled out by construction rather than by a corpus scan: the arm ran on an
      inert probe type with no Bash, Read or Write, and the subject is a jig that exists only in
      this change, so no cascade document or memory body can teach it. The arm confirms this
      itself: "I have no filesystem or shell access in this context."
- [x] Model tier pinned per dispatch (`sonnet`), not inherited.

## GREEN

- [x] Same scenario WITH the row. Verdict: `corpus_prompts`, first pick.
- [x] The differentiation risk is closed, and the arm gives the reason rather than the name:
      "there is no tool call, no cwd-scoped payload, and no gate-refusal notion to measure
      precision against, so guard_replay's whole calling convention and its precision column do
      not apply to this question."
- [x] Both dispatches required a `Skill gaps` section and both returned one.

## REFACTOR

Gaps reported, each closed or declined:

- [x] CLOSED - neither arm could tell what shape the predicate is called with. `guard_replay`
      states its convention prominently and this row did not, so both arms guessed by analogy.
      The row and the module docstring now state it: `f(text)`, the prompt text alone, with no
      record and no second argument, and why there is no cwd to forward.
- [x] DECLINED (owned by another row) - `diffbehave`'s description does not say whether it can be
      driven over a corpus-sized input list rather than a handful of cases. That is a gap in
      `diffbehave`'s own row, not this one, and widening this row to cover it would duplicate the
      judgement in two places.
- [x] DECLINED (correct as written) - neither tool offers built-in adjudication of whether a
      firing was right. The row says precision means nothing for prompts because there is no
      gate; the reader adjudicates by reading the diffed members. That is the honest position,
      not an omission.
- [x] DECLINED (out of scope) - `guard_replay`'s row does not enumerate every payload type it
      refuses. Pre-existing, and unchanged by this row.
- [x] GREEN diffed against RED in BOTH directions. RED produced one result GREEN does not: a
      concrete three-tool composition. That is the hand-rolling the row exists to prevent, so its
      loss is the intended effect rather than a regression.
- [x] Fix verified by quote-back: the governing text now reads "Your predicate is called as
      `f(text)` - the prompt TEXT alone, no record and no second argument".

## Quality

- [x] No flowchart added; the table is the reference surface.
- [x] No narrative, no provenance, no scratch paths in the row or in this artifact.
- [x] Every value in the row is generic: the only path is `~/.claude/projects`. Verified with the
      address, MAC and home-path grep from the checklist; no hits in the added row.
- [x] Routing accuracy check (table -> file): every term the row claims appears in the script -
      `firing SET`, `entrypoint`, `origin`, `RAW`, `claude/projects`, `count`.
- [x] Routing coverage check (file -> table): the script's capabilities are `collect_prompts`,
      `extract_prompts`, `diff_predicates` and a `--count` mode, and the row names the corpus
      walk, the typed-vs-harness filter, the firing-set diff and the count mode.
- [x] Differentiation check: the row names `guard_replay` explicitly and states why it cannot
      answer this question, which is what the RED/GREEN pair measured.
- [x] Frontmatter unchanged; `description` measured at 1009 characters, under the 1024 cap.
- [x] Token budget: this is a reference hub whose body is the index, so it exceeds 500 words by
      design. The row adds detail to the index rather than pushing the body toward prose.
- [x] External references: the row points only at the shipped script and at `--help`, both
      install-reachable.

## Scripts

- [x] `scripts/corpus_prompts.py` ships with `tests/test_corpus_prompts.py`, 12 tests, all
      passing. Every record shape asserted was taken from the real corpus rather than imagined.
- [x] The script imports in a bare environment: its one third-party import is guarded with a
      stdlib fallback, so a plain `pytest` collects it without provisioning PEP 723 deps.
- [x] Import-safe: all run-time work sits behind `if __name__ == "__main__":`.
- [x] Toolbox rule coverage satisfied with measured evidence rather than an assertion, since no
      command shape identifies this chore without shadowing an existing rule.
