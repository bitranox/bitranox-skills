# skill-writer checklist - net-rotating-proxies (2026-11-01, `fetch` for one large file)

New section `## One large file across proxies` documenting the `fetch` subcommand, plus one
description trigger ("or when one large file (an ISO, an archive) must be downloaded through
proxies and bans or dropped connections keep killing it mid-transfer").

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference for a tool. Test approach: retrieval. Scenario: one 4 GB ISO through
      free proxies, own IP banned, first try died at 1.3 GB. Questions answered with a direct
      quote or NONE, on both tiers (opus and haiku, `bitranox:baseline-probe`).
- [x] RED (pre-change text, abridged: the rules and Tool sections condensed to their rule lines,
      everything else as at HEAD): both tiers answered NONE for a single-file command, for
      keeping partial bytes, for an integrity check, and for Range support.
- [x] redcheck inherited-coverage hits read: term overlap (proxy, ban, retry), not this lesson.
- [x] GREEN round 1 (new section verbatim, same abridged rest): 8 of 8 answered by quote on both
      tiers, including the control (500 YouTube transcripts -> `run`, not `fetch`). Gaps both
      tiers named: whether `fetch` needs `discover` + `validate` first; whether it refreshes the
      pool; the defaults; what "the probe settled nothing" covers and what to do next.
- [x] Each gap checked against the code before writing: `_fetch` raises NoProxies with "run
      discover and validate first" when `live + good - bad` is empty; the `fetch` parser has no
      `--background-discovery`; defaults `--chunk-size 8M`, `--chunk-timeout 120`,
      `--max-attempts-per-chunk 20`; the exit-1 note reads "no proxy answered, or the answers
      disagreed". Added a pool/defaults paragraph and turned the exit codes into a list.
- [x] GREEN round 2 on the final section text (both tiers): pool prerequisite, no background
      refresh, defaults, disagreement exit code and next step, hash-mismatch exit code and
      `FILE.part`, exit 0 without `--sha256`. Haiku answered all six by quote (no refresh read
      correctly as NONE); its two wording points (unit of 120, "refuse" vs exit 1) fixed.
      Opus answered all six by quote too; its two consequential gaps were checked in
      `chunked_fetch.py` and written in: `_finish` removes the manifest and keeps the part on a
      mismatch, so a rerun starts over; `probe` decides at two agreeing voters even beside a
      dissenter, else the most votes win and a tie returns None (exit 1).
- [x] Documented example executed against the local stand-ins (origin + three proxies, one
      cutting at 200000 bytes, `--chunk-size 512K` so the 3 MB file spans chunks): rc 0, output
      byte-identical to the origin, no `.part` left.
- [x] Description measured with len(): 403 characters; frontmatter parses (keys `description`,
      `name`); file ASCII-only; no new line over 100 columns.
- [x] `skill_triggers.json` and `docs/skills.md` regenerated.
- [x] No address, MAC, hostname or machine path added; present tense, no private provenance.
