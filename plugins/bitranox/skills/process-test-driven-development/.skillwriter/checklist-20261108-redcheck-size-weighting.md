# skill-writer checklist - process-test-driven-development (2026-11-08, redcheck weighs a hit by document size)

`scripts/redcheck.py`: each shared rare term now carries the weight -ln P(a document of that
size holds it by chance), with P built from the term's document share scaled by the document's
size against the corpus median; a hit must clear the shared-term count AND `min_shared` terms at
the rarity cutoff in a median-size document. Each hit reports `evidence` and `evidence_needed`
(JSON) and "evidence X of Y needed" on its text line. The skill section on redcheck gains a
paragraph: an index is scored as one document, so it no longer matches every scenario and no
longer reports the pointer line that states a lesson; after every clean run, grep each
`CLAUDE.local.md` on the chain for the lesson's keywords. Description unchanged.

Decisions: d-20261108-99ea8784

- [x] Step 0b `show process-test-driven-development --kind rejected,removed --full`: nothing.
- [x] Skill half already shipped: the section already said to read a hit's shared terms and call
      ordinary words a false positive (commit 60e27ac2, 2026-10-26), so the change is the tool.
- [x] RED, reproduced on the real cascade (1844 documents): an ordinary-words plan-executor
      scenario hit three `CLAUDE.local.md` indexes (shared "asks, cargo, crate, dispatch,
      executing, ledger, subagent, workspace" and similar) and seven facts. The 5% cutoff is 92
      documents per term, and an index holds nearly every term.
- [x] Code RED: four new tests; the long-index test and the evidence-field test failed on the
      unchanged tool (the index was the first hit), the fixture guard and the positive control
      passed. `mutation_arm.py` with the gate replaced by `if False:` KILLED the long-index test.
- [x] GREEN: 70 redcheck tests pass, 654 meta-self-improve tests and the related hook tests pass.
      Real cascade: the same scenario now hits three cargo/crate/workspace facts only (a genuine
      topical overlap with a Rust scenario); a uutils mkdir-lock control still flags its fact,
      alone, at "evidence 24.2 of 12.0 needed". A SIGPIPE control sharing only 2 rare terms with
      its fact stays clean, as it did before (below the count; the paraphrase blind spot).
- [x] GREEN probes (opus x1, haiku x1, new paragraph pasted with the existing adjudication text;
      scenario C, a strong hit on subject vocabulary, was the control). Both: a clean run with a
      remembered index pointer is not safe, grep the index first; a thin hit on "asks, tasks,
      executing, workspace" is a false positive, run the RED; the strong hit is checked by
      opening the fact.
- [x] Gaps from GREEN, decided:
  - CLOSED: "the fact body ... is still caught" overclaimed (opus) - now "caught only when it
    shares enough of your scenario's rare terms".
  - CLOSED: the index grep was conditional on already suspecting an index line (opus) - now
    "after every clean run, grep each `CLAUDE.local.md` on the chain".
  - CLOSED: per-line or per-document scoring unclear (opus) - "An index is scored as ONE
    document".
  - DECLINED, covered elsewhere: what replaces a contaminated RED (the STRONG note: move the RED
    to another domain or replace the arm with a text check), exit codes (the script's docstring
    and `--help`), the shared-terms list and false-positive test (the paragraph above).
  - DECLINED, judgement: how to treat a hit barely over the bar - the adjudication step reads
    the terms whatever the margin.
  - DECLINED, outside this change: how to run an arm without a cascade file.
- [x] Re-probe on the final text (haiku, clean run, no remembered note): grepped both
      `CLAUDE.local.md` files for the lesson's keywords, read the body of each matching pointer,
      and dispatched only after that, quoting "after every clean run, grep each
      `CLAUDE.local.md` on the chain". New gaps were keyword choice (judgement) and the remedy for
      a contaminated RED (the STRONG note); no undecided gap.
- [x] Width check over the added lines: longest 98 columns; no non-ASCII.
