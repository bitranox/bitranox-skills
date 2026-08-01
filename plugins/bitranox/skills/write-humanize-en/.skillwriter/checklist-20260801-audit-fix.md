# skill-writer checklist - write-humanize-en (2026-08-01, isolated-audit fix)

Source: the clean-room sweep run by `bitranox:meta-skill-audit`. These five skills reported after
four batches had already shipped, so their findings were triaged last. Ships with plugin 5.131.0.

- [x] WRONG, and demonstrated: the skill said tell examples are kept in code spans so the exact
      character "survives both the hook and an accidental strip". Ran
      `strip_typographic_tells.py` over a probe holding an em dash in an inline span AND in a
      fenced block - it rewrote BOTH. Code-span placement protects from the tell-sweep HOOK, which
      skips code; it does not protect from the script, which does not.
- [x] Corrected to say so, and to name the do-not-run-it-here warning as the real protection.
- [x] Noted, not fixed: the hook and the script DISAGREE about code spans, so a file can pass the
      hook and be mangled by the script. Making the script skip code would align them, but that is
      a behaviour change to a shared script with its own blast radius - raised rather than decided.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Every claim re-measured against the real tool or file rather than taken from the report.
- [x] No session narrative or private provenance added; no machine paths added.
