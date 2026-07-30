---
name: web-seo-crawl-indexing
description: Use before changing robots.txt or deciding what crawlers may fetch - pages that stay in search results after being blocked, crawler load you want to cut, an asset or image host you are tempted to block, a URL space multiplied by language or filter parameters, or a stale sitemap. Keywords - robots.txt, Disallow, Allow, noindex, deindex, crawl budget, crawl trap, Googlebot, image search, Merchant Center, sitemap.
---

# Crawl control and indexing

> **STATUS: SEEDED, NOT COMPLETE.** Covers robots.txt decisions, crawl-versus-index, crawl traps
> and sitemap shape. Missing: canonical and hreflang, structured data, pagination and faceted
> navigation, sitemap generation and submission, Search Console workflow. Absence of a topic here
> means "not written yet".

## Why this exists

Every rule below is reversible except by waiting. A wrong `Disallow` does not error, does not show
up in monitoring, and its damage (a frozen index entry, an image dropped from search, a
disapproved shopping listing) surfaces weeks later somewhere nobody connects to the change. So the
work is in the checks BEFORE the edit, not in the syntax.

## Before editing robots.txt, answer these from data

Never from the current file, and never from the shape of the proposal.

1. **Where is crawl budget actually going?** Classify the access log by URL class and by
   user-agent family. The answer routinely contradicts the intuition.
2. **What do real people land on from a search engine?** Same log, referrer from a search host,
   non-bot user agent. This is the list of paths that are NOT safe to block, and it is usually not
   the list you would have guessed.
3. **Is this actually a crawler-volume problem?** If the cost is repeat downloads by real
   visitors, robots.txt is the wrong tool entirely; see `bitranox:web-frontend-pagespeed`.

## The rule the whole topic turns on

**`Disallow` controls CRAWLING. `noindex` controls INDEXING. Applying both cancels the second.**

Blocking a URL does not remove it from the index. The crawler can no longer fetch the page, so it
can never read the `noindex` telling it to drop it. The entry freezes: still listed, now with no
title or snippet, and it can persist for as long as anything links to it.

```
Want it OUT of the index?      allow crawling, keep noindex, wait for it to drop, THEN block
Want to remove it permanently? 410 Gone is a stronger and faster signal than noindex
Want to save crawl budget?     block only paths that were never candidates to rank
```

## robots.txt is the wrong instrument for a bandwidth bill

It is advisory, and compliance is inversely correlated with how much you want the traffic gone.
The crawlers that obey are the ones sending you visitors; the scrapers driving the load ignore it.
So a broad block reliably costs you the good traffic and keeps the bad. Rate limiting, caching or
a WAF is the lever for volume.

## Never block asset paths to save bandwidth

An image or file ranks through the crawlable page that embeds it, so a host serving assets to
another site must keep those paths fetchable even when its own pages are deliberately `noindex`.
You cannot put a meta tag on a JPEG, so robots.txt is the only control, and blocking it is total.

What that costs: image search entirely, and product feeds fail validation because the crawler
cannot fetch the referenced image, which disapproves the listing rather than merely demoting it.

Block the noindex HTML surface and keep the assets, relying on longest-match precedence:

```
User-agent: *
Disallow: /
Allow: /assets/
```

## Crawl traps

A trap is a URL space that multiplies without adding rankable pages: language pickers, sort and
filter parameters, session or tracking parameters, calendars. Multiply by every item and it is
effectively unbounded. `noindex` does not fix a trap, because the pages are still fetched. Only
blocking the trap at its root recovers the budget.

## Sitemaps

- Directory URLs only work where the site actually serves directory listings.
- A stale sitemap is worse than none: it spends budget steering crawlers into dead ends.
- Removing the `Sitemap:` line does not retire one that was submitted through a search console.
  Retire it at the source or it keeps being fetched.
- List canonical URLs only; enumerating every size or format of one asset adds no indexing gain.

## Common mistakes

| Mistake                                     | Reality                                                          |
|---------------------------------------------|------------------------------------------------------------------|
| `Disallow` to remove a page from results    | Freezes the entry; the crawler can no longer see `noindex`       |
| `noindex` to save crawl budget              | Still fetched every time; only blocking saves budget             |
| Both at once on a page you want gone        | They cancel; allow crawling until it drops, then block           |
| `Disallow: /` on an asset or image host     | Kills image search and disapproves product-feed listings         |
| robots.txt to cut a bandwidth bill          | Obeyed by the crawlers you want, ignored by the ones costing you |
| Editing from the proposal's reasoning       | Measure budget and real search arrivals first                    |
| Blocking a path that receives search clicks | Check human arrivals, not just crawler hits                      |
| Dropping the `Sitemap:` line to retire one  | A submitted sitemap keeps being fetched                          |

## Scope boundary

| Concern                               | Skill                                 |
|---------------------------------------|---------------------------------------|
| Caching and compression of the assets | `bitranox:web-frontend-pagespeed`     |
| Security headers, CSP, HSTS           | `bitranox:sec-appsec-web-baseline`    |
| Layout, viewport, RTL, tap targets    | `bitranox:web-frontend-responsive-ux` |
