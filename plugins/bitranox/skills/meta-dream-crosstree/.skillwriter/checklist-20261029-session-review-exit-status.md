# skill-writer checklist - meta-dream-crosstree (session-review part loop on exit status)

- [x] Change: step 0's part loop repeats `session-review` and `session-reviewed` while
      `session-review` exits 0 (1 = nothing left, 2 = error) instead of until it prints
      `NOTHING NEW`, and points at dream-core "Capture-first" for why a grep over the output
      fails: its body is raw transcript. Matches the shipped `dream_state.py` exit status.
- [x] RED/GREEN: the governing text is dream-core.md, tested there (see
      `meta-dream-tree/.skillwriter/checklist-20261029-session-review-exit-status.md`: RED opus and
      haiku stopped on a marker search, GREEN opus and haiku stopped on the exit status). This
      line restates that rule in one sentence with a pointer, so it was checked as text: it
      names the same three statuses and the same reason.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, prose wrapped to the step's indentation.
- [x] Security scan: no secrets, hostnames, private paths or PII.
