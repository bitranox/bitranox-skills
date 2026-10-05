# Skill-writer checklist: the idempotency guard misses sections and config locations (2026-10-05)

Scope: the "Automating it idempotently" `zram-size` read in the `awk` one-liner. Before, it read
only `/etc/systemd/zram-generator.conf` with a bare `/^zram-size/` match (no section tracking, so
it also matches inside `[zram1]` or any other section) and ignored `.conf.d/` drop-ins and the
`/run` and `/usr/lib` (and `/usr/local/lib`) main files zram-generator also reads. After: the
match is scoped to the `[zram0]` section, and every location zram-generator reads is checked in
its documented precedence order, built with a loop so a missing optional location does not abort
the read.

## PLAN

- [x] Skill type: reference/technique (a copy-paste shell guard for a sysadmin task). Test
      approach: verify the corrected `awk`/shell pipeline actually runs and resolves correctly
      against a crafted multi-section, multi-location fixture - this is a shell snippet readers
      copy verbatim, so its correctness is checked by RUNNING it, not by review.
- [x] Re-checked the claim against the current text first: the `awk -F= '/^zram-size/ ...'`
      pattern has no section guard and reads only one file. Confirmed by constructing a config
      with `[zram1]` ahead of `[zram0]` and showing the bare pattern finds the `[zram1]` value.

## RED (current text, reproduced)

- [x] Built a two-section fixture (`[zram1]` then `[zram0]`, with `[zram0]`'s own `zram-size`
      LAST) and ran the original one-liner against it: it returned the `[zram1]` value, not
      `[zram0]`'s own - confirms the section-scoping defect reproduces.
- [x] zram-generator's own README (fetched) states precedence `/run` > `/etc` > `/usr/local/lib`
      > `/usr/lib`, with each location's own `.conf.d/` drop-in overriding that location's main
      file - none of which the original one-liner reads except the one `/etc` main file.

## GREEN (the fix)

- [x] Rewrote the `awk` program to track `in_zram0` from a `[section]` line match, so only keys
      inside `[zram0]` are read.
- [x] Built the file list in ascending precedence (`/usr/lib` main, its `.conf.d/*.conf`,
      `/usr/local/lib` main, its `.conf.d/*.conf`, `/etc` main, its `.conf.d/*.conf`, `/run`
      main, its `.conf.d/*.conf`) and kept the LAST match with `tail -1`, so the
      highest-precedence location that sets the key wins.
- [x] Discovered mid-fix that `awk` treats a MISSING input file as FATAL, aborting the whole run
      rather than skipping it - unlike a shell glob that happens to match nothing (which expands
      to its own literal, non-existent pattern string and would ALSO abort `awk` the same way).
      Since most hosts have none of `/usr/local/lib`'s or `/run`'s locations, globbing them
      directly into the `awk` argument list would have made the guard fail HARDER than the
      original (worse than the defect being fixed). Replaced the direct glob with a `for` loop
      that tests `[ -f "$f" ]` before adding each candidate to an array, then passes only the
      files that exist.

## Verification

- [x] Ran the exact rewritten snippet (copied verbatim from the published file) against a
      scratch fixture: two "nope"/missing locations, a main file with `[zram1]` then `[zram0]`
      (8192), and a second, higher-precedence file overriding `[zram0]` to 16384. Result:
      `want_mb=16384` - correct winner, no fatal abort from the missing locations.
- [x] Confirmed the `case`/arithmetic guard immediately after is unchanged and still reads from
      the corrected `$want_mb`.

## Security and hygiene

- [x] No secret, real hostname, address or private path in the diff; all paths are standard
      `systemd`/`zram-generator` filesystem locations.
- [x] No frontmatter, `name`, or trigger text changed; no derived artifact needs regeneration.
- [x] Added lines ASCII only.
