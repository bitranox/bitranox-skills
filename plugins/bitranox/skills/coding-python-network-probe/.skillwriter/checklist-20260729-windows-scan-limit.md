# skill-writer checklist - coding-python-network-probe (2026-07-29, Windows scan limit)

Change: one bullet in "What it will not do, and why" recording that a connect scan cannot separate
CLOSED from FILTERED on Windows. Shipped in plugin 5.100.3.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the skill told readers to rely on the three-state result, and a "Common mistakes" entry
      said conflating CLOSED and FILTERED hides a firewall. On Windows the library itself cannot
      draw that line, so the advice was unachievable there and the skill did not say so.
- [x] Measured, not assumed: five Windows CI jobs reported a closed loopback port as FILTERED even
      after the refusal check was widened to errno and winerror as well as the exception class.
      Windows neither refuses nor resets it within the timeout. The assertion was made
      self-diagnosing first, so the runner log names the state rather than only that it differed.
- [x] GREEN: the bullet states which platforms draw the line, what a Windows FILTERED means, and
      that a SYN scan draws it wherever it can run - which is not Windows.
- [x] Kept consistent with the code: the same limit is documented in portscan.py's module
      docstring and encoded in the test, so the three cannot drift apart silently.
- [x] Scope: shared/general - no machine-specific content.
- [x] Security scan: one prose bullet, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: unchanged (body addition, frontmatter untouched).
- [x] Token budget: one bullet added to an existing section.
- [x] Mirrors the copy shipped in the ipscout repo.
