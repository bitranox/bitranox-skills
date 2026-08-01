---
name: web-frontend-pagespeed
description: Use when verifying or fixing how a site caches and compresses its assets - bandwidth or CDN cost up with flat request volume, a bundle refetched on every navigation, an asset that will not pick up a new deploy, compression that looks enabled but is not, or a header check that came back clean and you need to know whether to believe it. Keywords - Cache-Control, max-age, immutable, ETag, 304, revalidation, gzip, Content-Encoding, gzip_types, add_header inheritance.
---

# Pagespeed: verifying caching and compression

> **STATUS: SEEDED, NOT COMPLETE.** Covers only caching and compression verification.
> Missing: Core Web Vitals, LCP, render-blocking resources, image strategy, preload hints,
> Lighthouse workflow, bundled audit script. Absence of a topic here means "not written yet".

## Why this exists

The facts below are not obscure. The failure mode is not knowing them, it is **not running the
check**, and then **believing a clean result that was never capable of being dirty**. Both defects
here are silent: no error, no warning, just bytes leaving again.

## Run these checks

Check at the hop the visitor reaches (a CDN or reverse proxy can add, strip, or override both).

```bash
# 1. What headers does this asset ACTUALLY carry? GET, never HEAD - see below.
curl -s -o /dev/null -D - -H 'Accept-Encoding: gzip' https://host/path/app.js

# 2. Is it really compressed? Compare bytes on the wire, do not trust the header alone.
curl -s -H 'Accept-Encoding: gzip' https://host/path/app.js | wc -c
curl -s                            https://host/path/app.js | wc -c

# 3. Does revalidation actually cost nothing? A no-cache asset needs a validator,
#    or every "revalidation" is a full 200 with the whole body.
curl -s -o /dev/null -D - https://host/path/app.js | grep -iE 'etag|last-modified'
```

## What a false clean looks like

| Check                             | Why it can read clean while broken                                                                                                                                             |
|-----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `curl -I` for compression         | Plain `curl -I` sends no `Accept-Encoding`, so nothing is negotiated and `Content-Encoding` is absent whatever the server does. With `--compressed` most servers DO report it on a HEAD (measured on three), but a filter that only runs on a body will not - so a HEAD is unreliable in BOTH directions. Confirm with a GET |
| `Cache-Control: no-cache` present | `no-cache` means revalidate, not do-not-store. Cheap only if the origin emits `ETag`/`Last-Modified`; a proxied app that sends neither turns each revalidation into a full 200 |
| A location "has no cache policy"  | With no `add_header` of its own it INHERITS the server-level one, often `no-cache`. Absence of config is a policy                                                              |
| A later regex location for assets | A `^~` prefix match stops location selection; regex locations are never evaluated for that prefix                                                                              |
| `gzip_types` names the type       | Matching is literal against the response `Content-Type`. `application/javascript` does not match `text/javascript`, which is what modern servers send                          |

## Decision rules

**`immutable` requires a URL that changes with its content.** Hashed or versioned filename, or
no `immutable`. On a fixed URL it means stale until expiry with no way to push a fix. Until the
build fingerprints the filename, use a bounded `max-age`.

**`add_header` inheritance cuts both ways.** A location with its own `add_header` drops all
inherited ones. A location with none inherits the whole server-level set. Adding one header to a
location silently removes the rest there, which is also how security headers get lost; see
`bitranox:sec-appsec-web-baseline`.

**robots and bandwidth are different problems.** If the cost is crawler volume rather than repeat
downloads, caching will not fix it; see `bitranox:web-seo-crawl-indexing`.

## Common mistakes

| Mistake                                     | Reality                                                            |
|---------------------------------------------|--------------------------------------------------------------------|
| `curl -I` to test compression               | False negative on every file; use GET and compare wire bytes       |
| Reading `no-cache` as "not cached"          | It is revalidate-every-time; without validators that is a full 200 |
| `immutable` on an unhashed path             | Stale until expiry, unfixable                                      |
| Assuming a proxied location has no policy   | It inherits the server-level `Cache-Control`                       |
| Adding one `add_header` to a location       | Drops every inherited header there                                 |
| Only `application/javascript` in gzip_types | Servers send `text/javascript`; nothing compresses                 |
| Grading the origin behind a CDN             | Measure where visitors actually land                               |

## Scope boundary

| Concern                              | Skill                                 |
|--------------------------------------|---------------------------------------|
| Security headers, CSP, HSTS, cookies | `bitranox:sec-appsec-web-baseline`    |
| Layout, viewport, tap targets, RTL   | `bitranox:web-frontend-responsive-ux` |
| robots.txt, crawl budget, indexing   | `bitranox:web-seo-crawl-indexing`     |
