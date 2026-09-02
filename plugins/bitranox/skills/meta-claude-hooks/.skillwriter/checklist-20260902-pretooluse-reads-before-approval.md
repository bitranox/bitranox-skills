# skill-writer checklist - meta-claude-hooks (2026-09-02, a PreToolUse hook reads before approval)

Change: one section. A PreToolUse guard that resolves a path out of the pending command is reading
a file the call has not been approved to read, so it must report a hit by POSITION and CHARACTER
rather than by quoting the line back to the model.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. Pre-change, a grep for `before approval`,
      `not yet approved` and `quote the line` over SKILL.md returned 0 hits.
- [x] The check was shown capable of firing (control term on a sibling file returned 59).
- [x] The rule is stated as a contrast a reader can copy: the safe report line and the leaking one,
      side by side, so the difference is mechanical rather than a judgement about sensitivity.
- [x] The carve-out is stated too: quoting back IS safe for text the caller typed inline, which the
      user approved by typing it. Without that, the rule over-applies and readers will drop useful
      diagnostics.
- [x] Scope: shared - PreToolUse running before approval is a Claude Code property, not a setup detail.
- [x] Security scan: the example line is generic prose; no paths, hosts or credentials.
- [x] CSO description: unchanged; the section falls under the existing hook-authoring triggers.
- [x] Token budget: one section in a reference skill.
