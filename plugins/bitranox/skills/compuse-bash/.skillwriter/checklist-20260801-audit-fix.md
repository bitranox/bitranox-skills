# skill-writer checklist - compuse-bash (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit` - one reviewer per skill, in
a copy of the plugin outside the knowledge tree with recall walled. Ships with plugin 5.126.0.

- [x] WRONG, and reproduced: the documented mtime-sort alternative
      `find DIR -printf '%T@ %p\n' | sort -zrn` does not sort at all. `-z` splits records on NUL
      while `-printf '\n'` emits newlines, so with no NUL present sort sees ONE record and passes
      the input through untouched. Verified on three files with known mtimes: the documented form
      returned them in directory order, `sort -rn` returned newest-first.
- [x] The damage is exactly what the surrounding rule exists to prevent - the row teaches "sort by
      MTIME, never lexical order" for keep-newest pruning, so a reader following its own command
      keeps whatever came first and deletes a newer file.
- [x] Fixed by making the record separator match (`%T@ %p\0` with `sort -zrn`) and naming the
      mixing failure inline, since the wrong form fails silently rather than erroring.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file before acting; every executable claim re-run rather
      than taken from the report.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
