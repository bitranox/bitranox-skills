# skill-writer checklist - web-seo-crawl-indexing (2026-07-30, new skill seeded from one session)

New skill under the existing `web` category (`web-seo-...`; sub-prefixes are free-form, top-level
`web` is in skill-taxonomy.json). Seeded with the crawl-versus-index distinction, crawl traps and
sitemap shape; the SKILL.md declares the gaps in a STATUS block.

RED evidence came from a live session rather than dispatched pressure scenarios. The central rule is
in the skill because getting it backwards was a live near-miss, not a hypothetical:

- An asset host was serving a URL space where the overwhelming majority of crawler fetches went to
  paths carrying `<meta name="robots" content="noindex">`, measured by classifying the access log by
  URL class and user agent. The indexable assets received a negligible share.
- My first draft of the robots.txt would have blocked a legacy path that measurement then showed was
  still receiving real human arrivals from a search engine. Blocking it would have frozen its index
  entries instead of letting the existing `noindex` retire them cleanly. The measurement, not the
  reasoning, caught it. That is why "measure before editing" and "check real arrivals, not just
  crawler hits" are both in the skill.
- A sitemap listing directory URLs was inherited from a predecessor site that served directory
  listings; on a host without them every entry resolved to a 404, steering crawlers away from the
  assets. Verified by requesting sampled URLs from it.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the crawl-budget split, the live search arrivals, and the dead sitemap URLs were each
      measured from access logs and HTTP status checks, not assumed
- [x] GREEN: every observed failure has a section and a Common-mistakes row, including the one my
      own first draft would have committed
- [x] Verified against ground truth before writing (log classification and sampled HTTP statuses)
- [x] CSO description: trigger-first "Use when", no workflow summary, third person, keyword tail
      (robots.txt, Disallow, noindex, crawl budget, crawl trap, sitemap, deindex)
- [x] Skill type identified: technique/reference. Self-contained SKILL.md, no bundled scripts, so
      no `tests/` is owed
- [x] Cross-references use skill names with no `@` links; no bare package-local doc paths
- [x] Security scan: generic prose only. No secrets, hostnames, IPs, internal paths, private project
      names, or real URLs from the originating environment
- [x] No measured operational figures from the originating environment in the skill body
- [x] Docs describe current state: no legacy or migration narrative
- [x] Incompleteness declared in the body so a reader is not misled about coverage

NOT done, deliberately, and named in the STATUS block as the completion path: subagent baseline and
pressure scenarios per the skill-writer Iron Law, and the remaining dimensions (canonical and
hreflang, structured data, pagination and faceted navigation, sitemap generation and submission,
Search Console workflow). `web-frontend-responsive-ux` still routes sitemap work to a
`web-frontend-sitemap` name; repointing that row edits its SKILL.md and so owes its own review
artifact, deferred to when these skills are completed.
