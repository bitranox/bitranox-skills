---
name: coding-input-sanitization
description: Use when handling untrusted or external input at an application or facing-API boundary - an HTTP/REST endpoint, web form, file upload, webhook, CLI taking user data, queue/broker message, or data from a third-party or legacy system - or when emitting into SQL, HTML, a shell, a file path, or another sink. Keywords - SQL injection, XSS, command injection, path traversal, deserialization, SSRF, unbounded-input DoS. For boundary-parsing architecture see coding-python-clean-architecture and coding-python-enforce-data-architecture-strict.
---

# coding-input-sanitization

## Overview

Untrusted input is sanitized at the TRUST BOUNDARY - the edge of an application or a public/facing
API - in two directions: validate-and-bound on the way IN, escape-for-the-sink on the way OUT.

**Core principle: sanitize at the boundary, not in the libraries between boundaries.** A library
called by your own trusted code assumes its inputs were already validated at the edge; re-sanitizing
on every internal call is waste and false confidence. Two distinct defenses, both required: input
validation does NOT make output safe, and output escaping does NOT replace input validation.

## Where this applies (and where it does NOT)

APPLIES - an untrusted boundary, data from outside your control:
- HTTP request body / query params / headers / cookies; web form fields; multipart file uploads
- webhook payloads; queue / broker / pub-sub messages
- CLI arguments and stdin carrying user data
- responses from a third-party API; scraped data; rows from a foreign / legacy system

DOES NOT APPLY - internal seams between trusted code:
- a domain/application function called by your own validated code
- a library/package boundary between your own modules
- These rely on the TYPE CONTRACT (the edge already validated). At most assert/typecheck; do not
  re-run input sanitization. Sanitizing everywhere is the anti-pattern this skill prevents.

## On the way IN - validate at the edge

- **Parse into a typed model, never inspect a raw dict.** A boundary parser (Pydantic in Python)
  validates type and shape, coerces, and REJECTS what does not fit. Never pass a raw dict / JSON /
  ORM row inward; convert to a typed domain object immediately.
- **Bound length and size.** Max string length, collection size, numeric range, request-body size.
  Unbounded input is a DoS vector; stream or paginate large data, never materialize unbounded.
- **Handle arbitrary bytes/chars.** non-ASCII, emoji, CJK, control chars, NUL, binary: reject,
  normalize (e.g. Unicode NFC), or escape - never trust raw. Decide the allowed charset explicitly.

## On the way OUT - escape at the SINK, for that sink's context

The same value is safe for one sink and dangerous for another, so escaping belongs at the sink, not
once at the edge.

| Sink                  | Rule                                                                                                                                           | Never                                                          |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| SQL                   | parametrized query / bound parameters (driver placeholders or the ORM query API)                                                               | string-concat or f-string external data into SQL               |
| HTML / templates      | autoescape ON (`select_autoescape(default=True, default_for_string=True)`); a trusted rich-text field opts out per-interpolation with `\|safe` | disable autoescape globally; mark untrusted data `\|safe`      |
| Shell / subprocess    | `subprocess.run([argv...])` no shell; `shlex.split` a user template into list elements                                                         | `shell=True` with untrusted input; f-string into a shell line  |
| File path             | confine to a base dir (`Path(base, name).resolve()` stays under `base.resolve()`); reject `..`, absolute, NUL                                  | join user input into a path unchecked (traversal)              |
| Deserialization       | a safe format (JSON) parsed into a typed model                                                                                                 | `pickle` / `yaml.load` / `eval` on untrusted data              |
| Outbound URL (SSRF)   | allowlist host + scheme; block internal/link-local ranges and redirects to them                                                                | fetch a user-supplied URL unrestricted                         |
| Log / response header | strip CR/LF + control chars before writing                                                                                                     | write user data into a header/log line raw (injection/forging) |

## Quick checklist

- [ ] Every external input parsed into a typed model at the edge; raw dict/JSON never flows inward
- [ ] Length / size / range bounded; large data streamed, not fully materialized
- [ ] SQL via bound parameters only; no string-built queries
- [ ] HTML autoescape ON; only trusted rich-text opts out, never a global disable
- [ ] Shell via argv, never `shell=True` on untrusted input
- [ ] File paths confined to a base dir; `..` / absolute rejected
- [ ] No `pickle` / `yaml.load` / `eval` on untrusted data
- [ ] Internal library calls NOT re-sanitized (type contract trusted)

## Common mistakes

- **Sanitizing everywhere.** Re-validating in internal libs between trusted callers. Validate once at
  the boundary; trust the typed value within.
- **"I validated the input, so output is safe."** No - a name validated as a string is still XSS in
  HTML and SQLi in a concatenated query. Escape at each sink.
- **Blocklist instead of allowlist.** Stripping `<script>` or quoting one metachar is bypassable.
  Validate what is ALLOWED (type, charset, range) and use the sink's real escaping primitive.
- **One global `sanitize()` that strips characters.** Context-free stripping corrupts valid data and
  still misses context-specific attacks. There is no universal sanitizer; escape per sink.

## Language notes

Examples are Python (the primary stack); the principle is language-agnostic. Rust:
`bitranox:coding-rust`. Bash: `bitranox:coding-bash-reference` (quoting, `shlex`, never eval untrusted
input). Boundary-parsing architecture (where the edge is, typed models flowing inward):
`bitranox:coding-python-clean-architecture`, `bitranox:coding-python-enforce-data-architecture-strict`.
