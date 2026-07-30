---
name: web-frontend-pagespeed
description: Use when a web asset is served with the wrong caching or compression - a fixed-URL file stuck stale behind a long max-age, a bundle refetched on every page view, an asset silently inheriting no-cache, JavaScript or CSS going out uncompressed, gzip that appears not to work, or an unexplained bandwidth bill from repeat downloads. Keywords - Cache-Control, max-age, immutable, ETag, gzip, brotli, Content-Encoding, gzip_types, nginx add_header inheritance, cache busting.
---

# Pagespeed: caching and compression

> **STATUS: SEEDED, NOT COMPLETE.** This skill currently covers only caching and
> compression, seeded from one debugging session. Still missing: Core Web Vitals and LCP,
> render-blocking resources, image format and sizing strategy, preload and priority hints,
> a Lighthouse workflow, and any bundled audit script. Treat what is here as reliable and
> the absence of a topic as "not written yet", not "not applicable".

## Overview

Two defects cause most avoidable transfer, and both are invisible to a casual check: an asset
that is never cached, and an asset that is never compressed. Neither shows up as an error.

## Cache-Control by resource class

| Resource                                 | Value                                 | Why                                        |
|------------------------------------------|---------------------------------------|--------------------------------------------|
| HTML                                     | `no-cache`                            | Always revalidated; unchanged pages 304    |
| Fixed-URL assets (favicons, unhashed js) | `public, max-age=86400`               | A regenerated file propagates within a day |
| URL-versioned or content-hashed assets   | `public, max-age=31536000, immutable` | New content always means a new URL         |
| Content that is overwritten in place     | short `max-age`, never `immutable`    | Same URL, new bytes                        |

**The rule everything follows from: `immutable` is valid only when the URL changes as the
content changes.** A fixed URL plus `immutable` means stale until expiry with no way to push a
fix. If you want the long cache, version the URL first (`?v=N` or a hashed filename) and bump it
on every change.

## nginx add_header inheritance cuts both ways

A `location` with its **own** `add_header` drops **all** inherited ones. A `location` with
**none** inherits the server-level set, including `Cache-Control`.

That second direction is the one that bites: a proxied asset location that sets no header of its
own silently inherits a server-level `Cache-Control: no-cache`, and every asset behind it is
refetched on every page view. Nothing errors; the bytes just leave again.

`bitranox:sec-appsec-web-baseline` documents the same trap from the security-header side. Check
both whenever you add an `add_header` to a location.

## Compression: `gzip_types` matches Content-Type literally

Modern servers send JavaScript as `text/javascript` (current IANA and WHATWG guidance), not
`application/javascript`. A `gzip_types` list naming only the latter compresses **nothing**,
while `text/css` and `text/html` next to it compress fine, so the config looks like it works.

List both. The same literal-match trap applies to any type you assume is covered.

## Verify with GET, never HEAD

`curl -I` sends HEAD. There is no body, so there is no `Content-Encoding`, and an uncompressed
response is indistinguishable from a compressed one. Compare bytes on the wire:

```bash
curl -s -o /dev/null -D - -H 'Accept-Encoding: gzip' https://host/app.js | grep -i content-encoding
curl -s -H 'Accept-Encoding: gzip' https://host/app.js | wc -c    # vs the uncompressed size
```

Check headers at the edge the visitor actually reaches. A reverse proxy or CDN in front can add,
strip, or override both caching and compression, so an origin-side check can grade the wrong hop.

## Common mistakes

| Mistake                                             | Reality                                                               |
|-----------------------------------------------------|-----------------------------------------------------------------------|
| `immutable` on a fixed URL                          | Stale until expiry, unfixable; version the URL first                  |
| Assuming a proxied location has no cache policy     | With no `add_header` it inherits the server-level one, often no-cache |
| Adding one `add_header` to a location               | Silently drops every inherited header there; re-add what you need     |
| `curl -I` to check compression                      | HEAD has no body, so no `Content-Encoding`; use GET and compare bytes |
| Listing only `application/javascript` in gzip_types | Servers send `text/javascript`; nothing gets compressed               |
| Grading the origin for a site behind a proxy        | The edge can add or strip both; measure where visitors land           |

## Scope boundary

| Concern                                    | Skill                                 |
|--------------------------------------------|---------------------------------------|
| Security headers, CSP, HSTS, cookie flags  | `bitranox:sec-appsec-web-baseline`    |
| Layout, viewport, tap targets, RTL         | `bitranox:web-frontend-responsive-ux` |
| robots.txt, crawl budget, indexing control | `bitranox:web-seo-crawl-indexing`     |
