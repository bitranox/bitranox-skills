# skill-writer checklist - web-frontend-pagespeed (2026-08-28, audit bucket E+F)

One unverifiable claim: an empirical statement resting on an anonymous sample of three.

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
- [x] "measured on three" names no servers, no date and no software versions, so a reader can
      neither reproduce it nor tell whether it still holds - they are asked to trust an anecdote.

## GREEN
- [x] The anecdote is gone. The row keeps the mechanism, which is what the reader acts on (a
      HEAD is unreliable in BOTH directions), and keeps the instruction to confirm with a GET.
      Nothing now rests on an unreproducible sample.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.

## Follow-up: re-measured instead of dropped (decision review)

- [x] The unreproducible "measured on three" is replaced by a dated, named measurement rather
      than removed: curl 8.18.0, 2026-08-28, six origins, each probed with a HEAD and a GET under
      `--compressed`.
- [x] Result: HEAD and GET AGREED on all six. Five negotiated compression and reported it
      identically (br or gzip); python.org reported none on either method, and an explicit
      `Accept-Encoding: gzip` plus a full `Content-Length` on both confirms it simply does not
      compress that response - so it is not a HEAD-vs-GET data point.
- [x] The original row asserted a HEAD is unreliable in BOTH directions. The disagreement
      direction was NOT produced by this sample, and the row now says so rather than implying it
      was observed. The confirm-with-a-GET instruction stays, which is what that residual risk
      calls for.
