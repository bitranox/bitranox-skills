# skill-writer checklist - web-seo-crawl-indexing (2026-07-30, new skill, rescoped after a failed RED)

New skill under the existing `web` top-level category (sub-prefixes are free-form; `web` is in
skill-taxonomy.json).

## RED round 1 - FAILED, and the skill was rewritten because of it

The first draft was a fact sheet. Two sealed baseline subagents (sonnet, fictional `.test` hosts,
no filesystem access, 0 tool calls each) got the deindexing scenario and the asset-host scenario
WITHOUT the skill. Both answered correctly and unaided, and one exceeded the draft: it named that
a blocked image URL makes a product feed fail validation and DISAPPROVES the listing rather than
demoting it, and argued that robots.txt is structurally the wrong bandwidth tool because the
crawlers that obey are the ones sending visitors while the scrapers driving cost ignore it. The
draft had neither point.

Conclusion drawn: fact-sheet framing earns nothing against model knowledge. Rewritten around the
checks to run before editing robots.txt and the silent, delayed nature of every mistake in it.
Both baseline insights folded in.

## RED/GREEN round 2 - paired A/B on a non-leading scenario

Round 1's scenarios framed the wrong answer as suspicious, inviting disagreement. Round 2 gave a
realistic ops request with a deadline ("put a robots.txt on it that stops the crawling", 20
minutes) and no hint that it was a bad idea. Same prompt to both arms.

- **Baseline (no skill, 0 tool calls): SHIPPED A HARMFUL FILE.** It reasoned well on strategy
  (robots.txt is voluntary, real lever is rate limiting) but shipped a wildcard `Disallow: /` with
  a hand-rolled per-UA allowlist, which blocks the product images for any crawler it did not think
  to enumerate. The file also contains a parse bug: a blank line inside the `anthropic-ai` group
  terminates the record, leaving an orphaned `Disallow`. It never mentioned feed disapproval.
- **With the skill (1 tool call, the Read): CORRECT.** Refused to ship a block, returned to ops
  with the reason, named the disapproval consequence, separated the HTML-page decision from the
  asset decision with the correct noindex-then-block ordering, and listed the specific log checks
  to run first. It explicitly preferred reporting a no-op over shipping something that looks like
  action.

The difference is a shipped artifact that harms versus one that does not, so not a marginal
effect. Evidence is n=1 per arm; recorded as such rather than generalised.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED round 1 run sealed and FAILED (baseline passed unaided) - skill rewritten, not shipped as-is
- [x] Baseline findings folded in: feed disapproval, and robots.txt being the wrong lever for volume
- [x] RED round 2 with a non-leading scenario reproduced the target failure (baseline blocked assets)
- [x] GREEN round 2 verified against the working-tree version, not an installed copy
- [x] CSO description: trigger-first "Use when", no workflow summary, third person, keyword tail
- [x] Skill type: technique/procedure. Self-contained, no bundled scripts, so no `tests/` is owed
- [x] Cross-references use skill names, no `@` links, no bare package-local doc paths
- [x] Security scan: generic prose only; no secrets, hostnames, IPs, internal paths, project names
- [x] No measured operational figures from the originating environment in the body
- [x] Docs describe current state: no legacy or migration narrative
- [x] Incompleteness declared in the body

NOT done, named in the STATUS block: canonical and hreflang, structured data, pagination and
faceted navigation, sitemap generation and submission, Search Console workflow. Testing is n=1 per
arm on one scenario. Separately deferred: `web-frontend-responsive-ux` still routes sitemap work to
a `web-frontend-sitemap` name, and repointing that row edits its SKILL.md so it owes its own review
artifact.
