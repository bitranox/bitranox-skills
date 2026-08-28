# skill-writer checklist - process-debug-systematic (2026-08-28, audit bucket E+F)

Two unsourced statistics, one of them used to override the reader's own investigation.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect is a FACTUAL claim carrying no version or date,
      so the test is a ground-truth check against the installed package, the live catalogue or the
      running tool - not a pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is a ground-truth check, whose result is immune to inherited context.
- [x] "15-30 minutes vs 2-3 hours" and "95% vs 40%" carry no date, source or study, unlike the
      near-identical Real-World Impact sections in this skill's own supporting files, which anchor
      theirs to a dated session.
- [x] The second figure is load-bearing: it tells a reader who has finished a genuine
      investigation to distrust their conclusion, which can push them past a legitimately
      environmental or timing-dependent issue.

## GREEN
- [x] The figures are gone. The Real-World Impact section keeps the DIRECTION and says plainly
      that the sizes are unmeasured and must not be quoted as figures.
- [x] The override keeps its force without the number and gains an action: name the evidence that
      RULED OUT a code cause, since a cause not found is not a cause excluded.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.

## Follow-up: upstream provenance checked (decision review)

- [x] The upstream this skill is adapted from (`obra/superpowers`,
      `skills/systematic-debugging/`) was fetched and read. The `95%` line appears there VERBATIM
      and BARE, in the same position, with no citation; `CREATION-LOG.md` names no measurement,
      study or data.
- [x] The `Real-World Impact` block carrying "15-30 minutes", "2-3 hours" and "95% vs 40%" does
      NOT EXIST upstream at all - the string "Real-World Impact" is absent from the upstream
      SKILL.md. So neither figure has provenance to restore, and the deletion stands.
- [x] The first search for this was run against the local `superpowers-marketplace` clone and
      found nothing. That negative was void: the clone holds LICENSE and README only, zero
      SKILL.md files. The control (does this corpus contain any skill body at all?) is what
      exposed it, and the real check went to the plugin repo instead.
