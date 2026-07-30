# skill-writer checklist - web-frontend-pagespeed (2026-07-30, new skill seeded from one session)

New skill. Fills the `web-frontend-pagespeed` slot that both `sec-appsec-web-baseline` and
`web-frontend-responsive-ux` already hand performance work off to, so two dangling cross-references
now resolve. Seeded with caching and compression only; the SKILL.md says so in a STATUS block.

RED evidence came from a live debugging session rather than dispatched pressure scenarios. Both
failure modes were observed and measured on a real server, not hypothesised:

- A reverse-proxied asset location set no `add_header`, so it inherited the server-level
  `Cache-Control: no-cache`, and a 271 KB vendored bundle was refetched on every page view. Nothing
  errored. The header was confirmed live before and after the fix.
- `gzip_types` listed `application/javascript` while the server sent `text/javascript`, so no JS was
  compressed while `text/css` beside it was. Confirmed by wire byte count: 277226 uncompressed,
  81190 after listing the correct type.
- My own first compression check used `curl -I`, which returned no `Content-Encoding` because HEAD
  has no body. That false negative is in the skill as its own section, because I made the mistake
  before writing the rule.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: both defects observed live on a real server and confirmed by measurement (headers before
      and after, wire byte counts), not from documentation or assumption
- [x] GREEN: each observed failure has a corresponding section and a row in Common mistakes; the
      HEAD-versus-GET false negative is documented because it actually fired
- [x] Verified against ground truth before writing (live curl output, not recalled behaviour)
- [x] CSO description: trigger-first "Use when", no workflow summary, third person, keyword tail
      (Cache-Control, max-age, immutable, gzip, Content-Encoding, gzip_types, add_header)
- [x] Skill type identified: technique/reference. Self-contained SKILL.md, no bundled scripts, so
      no `tests/` is owed
- [x] Cross-references use skill names with no `@` links; no bare package-local doc paths
- [x] Security scan: generic prose only. No secrets, hostnames, IPs, internal paths, or private
      project names; host names in examples are the placeholder `https://host/`
- [x] No measured operational figures from the originating environment in the skill body
- [x] Docs describe current state: no legacy or migration narrative
- [x] Incompleteness declared in the body so a reader is not misled about coverage

NOT done, deliberately, and named in the STATUS block as the completion path: subagent baseline and
pressure scenarios per the skill-writer Iron Law, and the remaining pagespeed dimensions (Core Web
Vitals, LCP, render-blocking, image strategy, preload hints, Lighthouse workflow, an audit script
with its `tests/`). This skill ships as an honest partial, not as a finished skill.
