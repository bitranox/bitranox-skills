# skill-writer checklist - write-humanize-de (2026-08-12, hooks/ path correction)

Change: the prose sentence right after the invocation examples said "Das Skript liegt im Ordner
`scripts/` dieses Skills" (the script lives in this skill's `scripts/` directory). No `scripts/`
directory exists here or in write-humanize-en; the script lives once at
`plugins/bitranox/hooks/strip_typographic_tells.py`. The three invocation lines above that
sentence already used the correct `<plugin>/hooks/` path (fixed in the 2026-08-02
shared-strip-script pass) - only the explanatory sentence right after them was missed and kept
naming a directory that has never existed.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Ground truth checked directly, not assumed: `ls plugins/bitranox/skills/write-humanize-de/`
      and `write-humanize-en/` show no `scripts/` entry in either; `find plugins/bitranox -name
      strip_typographic_tells.py` returns exactly one hit, `plugins/bitranox/hooks/`.
- [x] Fix is repo-relative to the plugin's own layout (`hooks/-Ordner des Plugins`), not a
      versioned cache path - it will not rot on the next version bump, and it matches the
      invocation lines already in this file.
- [x] Kept the fix in German, matching the surrounding file's voice; did not translate the
      correction to English.
- [x] Scope check: read the whole "Deterministischer Typografie-Durchlauf" section for other
      stale claims about the script (flags, behavior). The 5.185.0 change (spaced em dash now
      collapses straight to ` - ` with no doubled-space residue) is NOT documented anywhere in
      this file in either the old or a stale form - the file never claimed the old "von Hand
      nachziehen" behavior, so there was nothing to correct on that axis.
- [x] No RED/GREEN probe pair staged: this is a factual path correction (does the stated directory
      exist), not new judgment guidance a model could apply wrong under pressure. The `ls`/`find`
      output above IS the verification.
- [x] Sibling fixed in the same change (write-humanize-en), same defect, same root cause -
      documented in that skill's own checklist rather than skipped as "already covered here".
- [x] No session narrative or private provenance added; no machine paths added.
