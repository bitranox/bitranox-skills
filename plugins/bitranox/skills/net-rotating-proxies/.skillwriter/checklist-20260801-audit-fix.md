# skill-writer checklist - net-rotating-proxies (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.129.0.

- [x] WRONG: rule 1 promised `live.txt` is derived "freshly each run" and that yesterday's live
      proxy is never assumed to still work. The shipped `validate()` does the opposite - its work
      list is `pool - live - bad`, with the comment "only test ones we have not already cleared",
      so an entry already in `live.txt` is never re-tested and the file only accumulates.
- [x] Rewritten to the mechanism the tool actually implements, which is coherent once stated: dead
      proxies are banned to `bad.txt` at USE time and every reader computes `live - bad`, so a live
      entry is not-yet-disproven rather than proven-good. The doc was the only wrong part.
- [x] WRONG: the single `run` example omitted `--need` while the prose two paragraphs below
      describes `run` as holding "the `--need` fastest healthy proxies". `--need` defaults to None,
      so the documented invocation gets no right-sized working set. Example now passes it and the
      default is stated.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; behavioural claims checked against the code or the
      tool's own help rather than taken from the report.
- [x] No session narrative or private provenance added; no machine paths added.
