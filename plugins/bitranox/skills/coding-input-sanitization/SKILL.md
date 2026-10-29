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
- any value a security check vouches for before a DIFFERENT component parses it (a URL, path or
  header handed to a driver, an HTTP client or a service in another language), the app's own
  configuration included - see "When a different parser reads the value"

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
  Unbounded input is a DoS vector; stream or paginate large data, never materialize unbounded. A
  whole-document or request-body cap does NOT bound any single field inside it: one plain-string
  field can still carry megabytes into parsing, formatting or a per-character loop whose cost grows
  faster than its length. So give every text field on a boundary model its own `max_length` and
  every collection an item-count bound, at least where the field reaches parsing, formatting or
  allocation (a field only compared for equality needs none). For the wider self-healing/resource-guard patterns (bounding concurrency/memory, headroom checks), see
  `bitranox:coding-resilience`.
- **Handle arbitrary bytes/chars.** non-ASCII, emoji, CJK, control chars, NUL, binary: reject,
  normalize (e.g. Unicode NFC), or escape - never trust raw. Decide the allowed charset explicitly.

Test the edge with the adversarial input battery (UTF/emoji/CJK/binary/wrong-type/oversized) in
`bitranox:process-test-design`.

## When a different parser reads the value

**A check is only as strict as its agreement with the parser that CONSUMES the input.** When a
validator's verdict gates what a different component parses later (a password in a database URL
handed to a driver, a path, a header), two parsers routinely disagree on edge shapes, and the check
has holes exactly there. The usual cause is a refactor that centralises or "purifies" the predicate
onto a stdlib parser (`urllib.parse` in place of the driver library's own URL parser): its tests
stay green because they feed only shapes both parsers read alike, so nothing reports the loosening,
and a display masker built on the same predicate leaks the same inputs. So:

- keep a check on the consumer's own parse at the point of use, even when a shared predicate also
  runs earlier;
- make any shared predicate fail closed (refuse) on input it cannot parse;
- prove it with a differential table of adversarial shapes - fragments, a raw `@` in userinfo,
  unbalanced brackets, mixed-case and percent-encoded keys, repeated keys - fed to BOTH the
  predicate and the consumer's parser: every row the consumer reads as dangerous must be refused.
  Build the table first and run it against the pre-fix code for the RED.

**When the consumer is another language or a binary, fuzz against a replica of it.** It cannot be
imported into the test, so build the smallest program that runs its REAL routing and decoding code
from its source (the service repo, a vendored copy or a module cache): its router, path cleaning
and handler copied verbatim, driven with raw requests (Go: `http.ReadRequest`). Build it with the
toolchain the consumer declares (Go: the `go` / `toolchain` directive in `go.mod`, never whatever
Go is installed), since stdlib decoders change between releases. Generate a corpus from the edge
shapes (case, encodings, repeated keys, padding, path cleaning), run every row through both sides,
and classify it: agree; fail-closed (the validator refuses what the consumer accepts - allowed if
documented); or dangerous (the validator reads a value the consumer does not). Require zero
dangerous rows. Put the replica's path and the fuzz script in the fix brief so the fixer re-runs
it, and keep both out of the repo unless that toolchain runs in CI. Typical mismatches between a
Python validator and a Go consumer: `urllib.parse.parse_qs` drops a blank value unless
`keep_blank_values=True`, so `k=&k=x` reads `x` where Go's `Query().Get` returns the empty first
value; Go's `encoding/json` v1 decoder matches object keys case-insensitively (with Unicode case
folding, so U+017F and U+212A match `s` and `k`) and the last duplicate key wins; a handler that
tries each base64 alphabet in turn reads a mixed blob differently from Python code that normalises
it first. Review rounds that probe one input at a time find these one mismatch per round: when
successive rounds keep finding one more, stop probing by hand and build the replica.

## On the way OUT - escape at the SINK, for that sink's context

The same value is safe for one sink and dangerous for another, so escaping belongs at the sink, not
once at the edge.

| Sink                  | Rule                                                                                                                                            | Never                                                                                                                  |
|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| SQL                   | parametrized query / bound parameters (driver placeholders or the ORM query API)                                                                | string-concat or f-string external data into SQL                                                                       |
| HTML / templates      | autoescape ON (`select_autoescape(default=True, default_for_string=True)`); a trusted rich-text field opts out per-interpolation with `\|safe`  | disable autoescape globally; mark untrusted data `\|safe`                                                              |
| Shell / subprocess    | `subprocess.run([argv...])` no shell; `shlex.split` a user template into list elements                                                          | `shell=True` with untrusted input; f-string into a shell line                                                          |
| File path             | confine to a base dir by resolving THEN checking: `p = Path(base, name).resolve()`, keep only if `p.is_relative_to(base.resolve())`; reject NUL | trust the join to confine - `Path(base, "../../etc/passwd")` and `Path(base, "/etc/passwd")` both resolve OUTSIDE base |
| Deserialization       | a safe format (JSON) parsed into a typed model                                                                                                  | `pickle` / `yaml.load` / `eval` on untrusted data                                                                      |
| Outbound URL (SSRF)   | allowlist host + scheme; block internal/link-local ranges and redirects to them                                                                 | fetch a user-supplied URL unrestricted                                                                                 |
| Log / response header | strip CR/LF + control chars before writing                                                                                                      | write user data into a header/log line raw (injection/forging)                                                         |

**HTML built by hand: pick the escape mode per location.** Python's `html.escape(s)` defaults to
`quote=True`, which also turns `"` and `'` into `&quot;` and `&#x27;`. Inside a quoted attribute
value (`title="..."`, `alt="..."`) that is required, so keep the default there (an `href` from
input also needs a scheme allowlist: escaping does not stop `javascript:`); in element text (a
paragraph, a table cell) use `html.escape(s, quote=False)`, which still escapes `<`, `>` and `&`.
A test that looks for a sentence with quotes or apostrophes in the rendered HTML fails on the
default mode although the browser shows the text correctly: fix the escape mode, not the test.
Compare element text against `html.escape(s, quote=False)` (the raw text itself when it holds no
`<`, `>` or `&`) and an attribute value against `html.escape(s)`.

**Outbound URL: judge the host the client will read, not a string split.** `urlsplit(url).hostname`
passes numeric IPv4 spellings (`http://2130706433/`, `http://0x7f.1/`), IDNA spellings and a
trailing dot, which the HTTP client and resolver then treat as the host they really are. Parse into
the typed model first and run every host check (allowlist, no loopback/private/link-local, must
match the configured host) on its normalised host: pydantic's `HttpUrl` turns both numeric
spellings into `127.0.0.1`, applies IDNA (`xn--...`) and lower-cases, but KEEPS a trailing dot
(`LOCALHOST.` becomes `localhost.`), so strip one yourself before comparing names. Parsers also
disagree on where an authority ends: a WHATWG parser (pydantic) ends it at a backslash, an RFC 3986
one (`urllib`, libcurl) splits userinfo at the last `@`, so `http://192.0.2.10:8000\@evil.example/`
is `192.0.2.10` to pydantic and `evil.example` to `urllib`. Where a second parser may read the URL,
refuse it when the authority holds a backslash, `@`, `%`, whitespace, a control character or a
non-ASCII character, or when the two parsers' hosts differ. Store the canonical
`scheme://host[:port]` you judged (default port omitted), or require the stored text to equal it:
a reader of the raw text may see another origin (empty userinfo, dot segments, a backslash, a
leading-zero port, a one-number address). This holds for a URL in the app's own settings too. Test
numeric, IDNA, trailing-dot and backslash/userinfo spellings of a forbidden host, each refused.

## Quick checklist

- [ ] Every external input parsed into a typed model at the edge; raw dict/JSON never flows inward
- [ ] Length / size / range bounded; large data streamed, not fully materialized
- [ ] Allowed charset decided explicitly; arbitrary bytes/chars rejected, normalized (NFC), or escaped
- [ ] Whole-value regex uses `fullmatch` with `[0-9]` or `re.ASCII`; no `isdigit()` before `int()`
- [ ] SQL via bound parameters only; no string-built queries
- [ ] HTML autoescape ON; only trusted rich-text opts out, never a global disable
- [ ] Hand-built HTML: `html.escape(s, quote=False)` in element text, `html.escape(s)` in attributes
- [ ] Shell via argv, never `shell=True` on untrusted input
- [ ] File paths confined to a base dir; `..` / absolute rejected
- [ ] No `pickle` / `yaml.load` / `eval` on untrusted data
- [ ] Outbound URLs allowlisted (host + scheme); internal/link-local ranges and redirects to them blocked
- [ ] URL host checks run on the typed model's normalised host (one trailing dot stripped); a URL
      two parsers read differently is refused; the canonical origin you judged is what is stored
- [ ] A check gating what a different parser reads also runs on that parser's own parse, fails
      closed, and is proven by a differential table (by a replica for a consumer in another
      language)
- [ ] CR/LF + control chars stripped before writing user data to a log line or response header
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
- **"It takes an argv, so there is no shell to inject into."** Removing the shell removes ONE sink,
  not the need to validate. `chpasswd` reads `user:password` one entry PER LINE from stdin, so a
  newline inside a password smuggles in a second entry - run as root, that sets root's password, with
  no shell anywhere. Likewise a name beginning with `-` is parsed as an OPTION by `useradd`/`gpasswd`
  rather than as a name. Reject `\n` in a password at the boundary and allowlist account names to a
  POSIX pattern. The sink here is a line-oriented parser; treat it like any other sink.
- **A regex or `isdigit()` that reads as a complete check.** `re.match(r"...$", s)` accepts
  `"<valid>\n"`: `match` anchors only the start and `$` also matches just before a final newline,
  so `re.compile(r"(\d{4})-(\d{2})-(\d{2})$").match("2024-01-31\n")` passes and the caller then
  uses the original string, newline included - a "one entry per line" writer writes two lines.
  `\d` without `re.ASCII` also accepts non-ASCII digits such as U+0662, which `int()` converts.
  Validate a whole value with `pattern.fullmatch(s)` (no `$` needed) and `[0-9]` or `re.ASCII`.
  `str.isdigit()` is no `int()` guard either: `chr(0xB2).isdigit()` (superscript two) is `True`
  and `int(chr(0xB2))` raises `ValueError`, and so does an all-ASCII digit string past 4300
  characters (the `sys.set_int_max_str_digits` default); `isdecimal()` still accepts U+0662. An
  escaping `ValueError` can end a whole batch (a thread-pool map, a multi-host pass) with an exit
  code that reads as a normal result. Parse an untrusted integer with
  `re.fullmatch(r"[0-9]{1,N}", s)` (N sized to the field) and route a non-match to the
  malformed-input path. Test with `"<valid>\n"`, `chr(0x0662)`, `chr(0xB2)` and a 5000-digit
  string, and require each refused. To send a hostile header through an httpx mock transport, pass
  it as raw bytes (`headers=[(b"content-length", b"\xb2")]`): a `str` header with a non-ASCII
  character already fails while building the response (`UnicodeEncodeError`), which tests the
  fixture, not the parser.

## Language notes

Examples are Python (the primary stack); the principle is language-agnostic. Rust:
`bitranox:coding-rust`. Bash: `bitranox:coding-bash-reference` (quoting, never eval untrusted
input); `shlex` is Python's, for building an argv from a string - see the shell sink above. Boundary-parsing architecture (where the edge is, typed models flowing inward):
`bitranox:coding-python-clean-architecture`, `bitranox:coding-python-enforce-data-architecture-strict`.
