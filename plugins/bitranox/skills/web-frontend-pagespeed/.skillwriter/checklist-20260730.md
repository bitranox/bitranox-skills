# skill-writer checklist - web-frontend-pagespeed (2026-07-30, new skill, rescoped after a failed RED)

New skill. Fills the `web-frontend-pagespeed` slot that `sec-appsec-web-baseline` and
`web-frontend-responsive-ux` already hand performance work off to.

## RED round 1 - FAILED, and the skill was rewritten because of it

The first draft was a fact sheet (Cache-Control classes, gzip_types, HEAD vs GET). Two sealed
baseline subagents (sonnet, fictional `.test` hosts, no filesystem access, 0 tool calls each)
were given the caching and the compression scenario WITHOUT the skill. Both answered correctly
and unaided. One was better than the draft: it identified that `no-cache` yields a cheap 304 only
when the origin emits a validator, and that `proxy_pass` does not manufacture one, so a proxied
asset re-sends the full body on every revalidation. **The draft asserted the opposite.** It also
noted `^~` halts location selection so a later regex block never applies.

Conclusion drawn: the knowledge is already in the model, so a fact sheet earns nothing. What
failed in the originating session was not knowing but CHECKING - a `curl -I` returned a
clean-looking false negative. The skill was rewritten around the checks and a "what a false clean
looks like" table, and the wrong 304 claim was corrected from the baseline's finding.

## RED/GREEN round 2 - paired A/B on a non-leading scenario

Round 1's scenarios were leading (config excerpt with the smoking gun, the wrong answer framed as
suspicious). Round 2 gave a symptom only: egress 3.1x with flat request count, a frontend rewrite
8 days ago, no config shown. Same prompt to both arms.

- **Baseline (no skill, 0 tool calls): FELL INTO THE TRAP.** Its step 2 was
  `curl -sI -H "Accept-Encoding: gzip" ...` with "look for Content-Encoding" - a check incapable
  of ever showing compression, on any file. It used `curl -sI` again for cache headers, and never
  mentioned `add_header` inheritance.
- **With the skill (1 tool call, the Read): CORRECT.** Used GET, stated why HEAD cannot fail,
  compared wire bytes, derived the `text/javascript` gzip_types mismatch from the rewrite detail,
  checked `add_header` inheritance, and treated `no-cache` without validators as a full 200. It
  additionally proposed a deploy gate running the GET-based byte comparison.

Categorical difference on the skill's central claim, so not a marginal effect. Evidence is n=1
per arm; recorded as such rather than generalised.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED round 1 run sealed and FAILED (baseline passed unaided) - skill rewritten, not shipped as-is
- [x] A factual error found by the baseline (no-cache/304 without validators) corrected in the body
- [x] Baseline findings folded in: validator requirement, `^~` halting regex location selection
- [x] RED round 2 with a non-leading scenario reproduced the target failure (baseline used HEAD)
- [x] GREEN round 2 verified against the working-tree version, not an installed copy
- [x] CSO description: trigger-first "Use when", no workflow summary, third person, keyword tail
- [x] Skill type: technique/procedure. Self-contained, no bundled scripts, so no `tests/` is owed
- [x] Cross-references use skill names, no `@` links, no bare package-local doc paths
- [x] Security scan: generic prose only; no secrets, hostnames, IPs, internal paths, project names
- [x] No measured operational figures from the originating environment in the body
- [x] Docs describe current state: no legacy or migration narrative
- [x] Incompleteness declared in the body

NOT done, named in the STATUS block: the remaining pagespeed dimensions (Core Web Vitals, LCP,
render-blocking, image strategy, preload hints, Lighthouse workflow, an audit script with tests).
Testing is n=1 per arm on one scenario; more scenarios and repeats would strengthen it.
