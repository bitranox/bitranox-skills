# skill-writer checklist - coding-python-rpyc (2026-08-01, vendored-doc audit fixes)

Source: the clean-room sweep run by `bitranox:meta-skill-audit`. Operator decision: fix EVERY
finding in the vendored copies rather than leaving them upstream's problem. Ships with 5.130.0.

- [x] WRONG x8, each checked against the INSTALLED rpyc 6.0.2 rather than against the report:
      - `--host` default was documented twice as `0.0.0.0`. `rpyc_classic.py --help` says
        `localhost`. Worth noting the reviewer reached the right conclusion from wrong evidence -
        it cited a tutorial log line that shows an ACCEPTED PEER address, not a bind address - so
        the claim was re-derived from the tool before changing anything.
      - `-m/--mode` listed three modes; the tool offers four (`oneshot` was missing).
      - `propagate_KeyboardInterrupt_locally` was documented `False`; `DEFAULT_CONFIG` says `True`.
      - `conn.builtin.range(7)` (singular) in one sample against `conn.builtins` everywhere else.
      - `telnetlib.socket = rpyc.modules.socket` - the rpyc PACKAGE has no `.modules`
        (`hasattr(rpyc,'modules')` is False); the CONNECTION does, so it is `machine_c.modules`.
      - the boilerplate ReadMe promised server output "after 30s"; the shipped client sleeps 10.
      - SKILL.md said CPython 3.7+ and install.md said 2.7-3.7; the installed distribution declares
        `Requires-Python >=3.8`. All three reconciled on the measured value.
- [x] UNEXECUTABLE: the "Per-module API" row sent readers to `api/*.md` for detail those files do
      not contain - all 11 are ~121-byte stubs reading "See source code". The row now says so and
      points at `help()` on the installed package, which does have the signatures.
- [x] DANGLING x5, all now resolving: `changelog.md` (3 links) and `license.md` redirected to the
      upstream repo, and three `_static` logo paths that were never vendored.
- [x] The gtk demo snippet is marked illustrative rather than presented as a transcript of the
      shipped demo, which is not vendored here and could not be checked.
- [x] Verified after: 0 unresolved local links anywhere in the skill.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Divergence from upstream is now deliberate and recorded here, so a future re-vendor is a
      MERGE rather than a copy - re-apply this list, or re-run the audit after refreshing.
- [x] No session narrative or private provenance added; no machine paths added.
