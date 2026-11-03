# skill-writer checklist - coding-python-use-modern-libraries (2026-11-04, JSON array streaming row)

Change: one new quick-reference row, "Large JSON array read one element at a time (memory must not
grow with the record count)". orjson has no streaming API, so the row names stdlib
`json.JSONDecoder().raw_decode` as the element FINDER and `orjson.loads` on each slice as the
parser, or `ijson.items(..., use_float=True)` when a dependency is fine. Avoid: a whole-array
`orjson.loads` / `json.load`, and a hand-rolled byte or regex scanner.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session).
- [x] RED (pre-edit JSON row plus the stdlib note, scenario: orjson already a dependency, no new
      dependencies wanted, 1 GB array, memory must not grow with the record count):
      haiku designed a hand-rolled chunked byte scanner tracking depth, string and escape state,
      then orjson per slice, and listed in Skill gaps "The table names orjson for JSON but says
      nothing about streaming or incremental parsing ... the byte scanner is my own design".
      opus reached `raw_decode` from its own knowledge but reported the gap: "Followed literally,
      'JSON: use orjson' leads straight to the whole-file `loads` that breaks the memory rule",
      and that the stdlib note and the JSON row point opposite ways for this case.
- [x] Every API the row names was executed before the GREEN probe (Python 3.12, orjson 3.13.0,
      ijson 3.6.0 yajl2_c): `dir(orjson)` lists only `loads`/`dumps` as parsers; a
      `raw_decode` + `orjson.loads(slice)` loop read 40k / 160k records in 0.04 / 0.16 s and a
      16 MB single record of 8M `\\` escapes in 0.04 s with RSS growth about the file's size;
      `ijson.items(f, "item")` returned `Decimal('1.10')`, with `use_float=True` it returned `1.1`,
      as `orjson.loads` does; a string regex of the form `(?:\\.[^"\\]*)*` grew RSS 228 MB at 2M
      escapes and 456 MB at 4M, measured with `ru_maxrss` (tracemalloc reports none of it).
- [x] GREEN on haiku and opus with the edited row pasted in: see the GREEN section below.
- [x] Scope: shared/general - no machine-specific content; no addresses, hosts or paths.
- [x] CSO description: unchanged (it already names JSON; body table edit only).
- [x] Table realigned with reformat_tables.py; `--check` reports it canonical. The diff touches the
      whole table only through re-padding to the wider first column.
- [x] Present tense, no version-history wording in the added row.
- [x] Security scan: one prose table row, ASCII, no secrets/hosts/paths/PII.

## GREEN

- Round 1 (row only, Notes said "memory = the text plus one record"): both tiers chose
  raw_decode + orjson; opus reported that holding the whole text contradicts the row's own memory
  rule. Fixed: the Notes entry became a chunked recipe, executed first (chunked.py: 300 random
  arrays equal to orjson with chunks down to 1 byte; RSS growth 0 MB at 16 MB and 65 MB files).
- Round 2 (chunked recipe): both tiers built the chunked reader and quoted the recipe. Both
  reported that a MALFORMED element reads as "incomplete", so the buffer grows to end of file;
  opus added RecursionError on deep nesting and the per-element prefix copy. Measured: a 32 MB
  file whose first element is malformed grew RSS 25-26 MB uncapped, 0 MB with a 1 MiB cap;
  RecursionError at 100000 levels (5000 parse). Fixed: maximum element size, RecursionError
  refusal, prefix dropped only on the next read, JSON-only whitespace.
- Round 3: both tiers applied the cap, the RecursionError refusal and the RSS proof with a
  malformed-first-element file. Gaps checked: invalid UTF-8 raises UnicodeDecodeError (confirmed,
  added); "raw_decode refuses near 1000 levels while orjson takes 1024" REFUTED by measurement
  (1024 pass and 1025 refused on both; the text now says so); cap unit is characters (added).
  Left as reader's choice, named by the probes as guesses: default chunk and cap values, offsets
  in error messages.
- Round 4: both tiers GREEN. Clarified the ambiguities they reported: `final=True` on the last
  read (measured: without it a file cut inside a character ends silently; with it,
  UnicodeDecodeError), which layer refuses 1025 levels (orjson; stdlib parses them), and an Avoid
  cell narrowed to scanners that track strings, escapes and depth (three probes read the
  separator stepping as banned).
- Round 5: both tiers GREEN. opus said the depth figures may depend on the Python version.
  Measured with uv (CPython 3.10.22, 3.11.17, 3.12.15, 3.14.8): on 3.10 and 3.11 raw_decode stops
  at 997 levels at the default recursion limit of 1000, while 3.12+ parse 5000. Fixed: the row
  qualifies "exactly orjson's", and the Notes give both figures and say to pin the promised depth
  on every supported minor.
- Round 6: both tiers GREEN. haiku planned a version-gated depth test (997 everywhere, 1024 only
  on 3.12+). opus planned the same, asserting the 998-1024 band per minor. One real gap, applied
  after this round and not re-probed: the 997 figure counts from a shallow stack (a CLI's reader
  measured 995). The Notes now say to pin the depth through the production call path. Remaining
  gaps reported in all rounds are values left to the reader (chunk size, cap default, refusal
  wording) or the grammar of `[]` and trailing data, which "refuse anything else there" covers.
