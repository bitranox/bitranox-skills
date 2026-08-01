# skill-writer checklist - coding-python-textual (2026-08-01, vendored-doc audit fixes)

Source: the clean-room sweep run by `bitranox:meta-skill-audit`. Operator decision: fix EVERY
finding in the vendored copies rather than leaving them upstream's problem. Ships with 5.130.0.

- [x] WRONG x4, all in shipped example code:
      - `border_title.py` did not parse - unescaped nested quotes - and `guide/styles.md` embedded
        the same broken line. Both fixed; `ast.parse` over the whole catalogue now reports 0 broken.
      - `styles/width.md` had an unterminated string literal; every python block in that file now
        parses.
      - `examples/how-to/layout.py` declares `CSS_PATH = "layout.tcss"`, which resolves relative to
        the app file, but the only copy lived in `examples/styles/`. A copy now sits beside the app
        that declares it, so the example runs as shipped.
- [x] DANGLING: `tutorial.md` linked `[Timer](textual.timer.Timer)` - a dotted Python path, which
      resolves to nothing in Markdown. Now the upstream API URL. Verified after: 0 unresolved local
      links anywhere in the skill.
- [x] STALE: "At the time of writing, the latest Textual is 0.47.1" replaced with how to CHECK the
      current release, since a dated claim in vendored text goes stale silently and the pin above
      it is an example rather than a recommendation.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Divergence from upstream is now deliberate and recorded here, so a future re-vendor is a
      MERGE rather than a copy - re-apply this list, or re-run the audit after refreshing.
- [x] No session narrative or private provenance added; no machine paths added.
