# skill-writer checklist - coding-python-send-mail (2026-10-24, latest-release inline images)

- [x] Change: the inline-images section opened "Since btx_lib_mail 4.5.0, the `send()` keyword
      `inline_images` ..."; it now opens "The `send()` keyword `inline_images` ...". Nothing else
      in the paragraph moved.
- [x] Rule: meta-skill-writer "Describe the latest release only" forbids "Since X.Y.Z" openers in
      a skill whose readers install the latest release (`uvx`, a fresh install).
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED: the rule's own finder (both passes, line and whitespace-joined) over the skill dir
      reported one hit, `SKILL.md:296: Since btx_lib_mail 4.5.0, the send() keyword inline_images`,
      and the same hit at line 301 of the btx_lib_mail twin.
- [x] GREEN: the same finder over both skill dirs reports zero hits.
- [x] Behavioural arm declined: the edit deletes a version qualifier and adds no instruction, so
      there is no reader behaviour for a subagent probe to get wrong; the finder output is the
      evidence. No probe ran, so no tier claim is made.
- [x] Claim checked: `inline_images` is a keyword of `send()` in the released library (CHANGELOG
      4.5.0 "Added - `send(inline_images=...)`"; PyPI serves 4.5.0), so the present-tense
      sentence is true for every reader on the latest release.
- [x] Description measured: unchanged.
- [x] Mirror: the same one-line edit in btx_lib_mail's `skills/python-send-mail/SKILL.md`;
      `repo-gate.py --mirror-of libs/btx_lib_mail` reports `in sync`.
- [x] Security scan: prose only; no secrets, hostnames or addresses.
