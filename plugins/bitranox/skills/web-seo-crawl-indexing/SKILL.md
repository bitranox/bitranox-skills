---
name: web-seo-crawl-indexing
description: Use when deciding what crawlers may fetch or index - writing or changing robots.txt, choosing between Disallow and noindex, a page that stays in search results after being blocked, crawlers burning budget on pages that cannot rank, a URL space multiplied by language or filter parameters, a stale or wrong sitemap, or images that are served but never appear in image search. Keywords - robots.txt, Disallow, noindex, crawl budget, crawl trap, sitemap, Googlebot, deindex, canonical.
---

# Crawl control and indexing

> **STATUS: SEEDED, NOT COMPLETE.** This skill currently covers robots.txt, the crawl-versus-index
> distinction, crawl traps, and sitemap shape, seeded from one debugging session. Still missing:
> canonical and hreflang, structured data, pagination and faceted navigation, sitemap generation
> and submission, and Search Console workflow. Treat what is here as reliable and the absence of a
> topic as "not written yet", not "not applicable".

## The distinction everything depends on

**`Disallow` controls CRAWLING. `noindex` controls INDEXING. They fight each other.**

Blocking a URL does not remove it from the index. The crawler can no longer fetch the page, so it
can no longer see the `noindex` telling it to drop it. The entry freezes: it stays listed, now
without a snippet, because nothing can read the page again.

```
Want it OUT of the index?   -> allow crawling, serve noindex, wait for it to drop, THEN block
Want to save crawl budget?  -> only Disallow paths that were never candidates to rank
Already noindex, never ranked? -> Disallow is free; there is no visibility to lose
```

## Measure before editing robots.txt

Do not reason from the current file. Classify the access log by URL class and by user-agent
family, and answer two questions with numbers: where is crawl budget actually going, and what do
real visitors arrive on from a search engine? Both routinely contradict the intuition, and the
second one is what tells you which paths are unsafe to block.

## Crawl traps

A crawl trap is a URL space that multiplies without adding rankable pages. The usual generators
are language pickers, sort and filter parameters, session or tracking parameters, and calendars.
Multiply those by every item and the crawlable space becomes effectively unbounded.

`noindex` alone does not fix a trap: the pages still get fetched, so the budget is still spent.
Blocking the trap at its root is what recovers it.

## An asset ranks through the page that embeds it

Image and file search index the asset via a crawlable HTML page that references it. A bare asset
URL with no host page essentially does not rank.

The practical consequence for a delivery host, CDN, or media subdomain: the asset paths must stay
crawlable so the crawler can fetch what it found on the embedding page, even when that host's own
pages are deliberately `noindex`. Blocking asset paths to save bandwidth silently removes them
from image search.

## Sitemaps

- A sitemap listing directory URLs only works where the site actually serves directory listings.
- A stale sitemap is worse than none: it spends budget steering crawlers into dead ends and away
  from what you want found.
- Removing the `Sitemap:` line does not retire a sitemap that was submitted through a search
  console. Retire it there too, or it keeps being fetched.
- List canonical URLs only. Enumerating every size or format variant of the same asset multiplies
  entries for no indexing gain.

## robots.txt is advisory

Major engines honour it. Plenty of scrapers ignore it entirely, and some large crawlers honour
only parts. Expect partial compliance, and re-measure after a change rather than assuming the
traffic went to zero.

## Common mistakes

| Mistake                                     | Reality                                                            |
|---------------------------------------------|--------------------------------------------------------------------|
| `Disallow` to remove a page from results    | Freezes the entry instead; the crawler can no longer see `noindex` |
| `noindex` to save crawl budget              | The page is still fetched every time; only blocking saves budget   |
| Both at once on a page you want gone        | They cancel out; allow crawling until it drops, then block         |
| Blocking asset paths to cut bandwidth       | Removes them from image search; assets rank via the embedding page |
| Editing robots.txt from intuition           | Measure the log by URL class and user agent first                  |
| Blocking a path that receives search clicks | Check real arrivals before blocking, not just crawler hits         |
| Assuming a `Disallow` drops traffic to zero | Advisory only; many crawlers ignore it. Re-measure                 |
| Dropping the `Sitemap:` line to retire one  | A submitted sitemap keeps being fetched; retire it at the source   |

## Scope boundary

| Concern                               | Skill                                 |
|---------------------------------------|---------------------------------------|
| Caching and compression of the assets | `bitranox:web-frontend-pagespeed`     |
| Security headers, CSP, HSTS           | `bitranox:sec-appsec-web-baseline`    |
| Layout, viewport, RTL, tap targets    | `bitranox:web-frontend-responsive-ux` |
