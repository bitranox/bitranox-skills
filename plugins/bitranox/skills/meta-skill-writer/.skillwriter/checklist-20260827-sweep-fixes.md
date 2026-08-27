# skill-writer checklist - meta-skill-writer (2026-08-27, sweep fixes)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect class is a FACTUAL claim, so the RED is a
      ground-truth check against the code or the upstream document, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft, and the arm cannot fail honestly.
      The artifact check is immune to that.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] RED: running `render-graphs.js` against this skill - exactly what the skill tells the reader
      to do - reported `syntax error in line 1 near 'step1'` and `Failed: graph_2`. Cause: the "NO
      Code in Flowcharts" illustration is fenced `dot`, and the extractor renders every `dot`
      block, but two bare node statements have no `digraph {}` wrapper.
- [x] GREEN: refenced as `text` with an inline note saying why. Re-run reports zero errors.
- [x] Swept for siblings rather than fixing the one instance: exactly one `dot` block in the whole
      catalogue is not a digraph, the one repaired here.
- [x] `anthropic-best-practices.md` is a bundled upstream copy carrying no source, contradicting
      this skill's own rule that a bundled copy be stamped with its source URL. Source confirmed by
      fetching it: title and description match the local copy byte for byte. Stamped with the
      canonical URL, the fetch date, and a note that upstream carries no version so the refresh test
      is a diff.
- [x] Side effect fixed too: `render-graphs.js` writes `diagrams/` into the skill dir, which was not
      gitignored, so following the documented instruction left an untracked artifact that a hook then
      auto-staged. Now ignored; verified by re-running and seeing a clean `git status`.
