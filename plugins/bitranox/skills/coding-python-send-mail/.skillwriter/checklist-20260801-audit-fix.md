# skill-writer checklist - coding-python-send-mail (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit` - one reviewer per skill, in
a copy of the plugin outside the knowledge tree with recall walled. Ships with plugin 5.126.0.

- [x] WRONG, and it breaks the skill's headline use case: both the example and the prose told the
      reader to pass `attachment_max_size_bytes=None` to lift the 25 MiB cap for a large
      attachment. Read against the installed library, `None` on the CALL is the sentinel for "no
      override" - `max_size = explicit if explicit is not None else conf.attachment_max_size_bytes`
      - so the 25 MiB default still applies and the send fails. `None` disables the check only on
      the CONFIG object, whose validator documents exactly that.
- [x] Fixed to pass a byte count larger than the file, and the prose now states the sentinel
      behaviour rather than repeating the wrong advice.
- [x] MIRRORED skill: the same fix applied to `libs/btx_lib_mail/skills/python-send-mail`, mirror
      gate re-run clean.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file before acting; every executable claim re-run rather
      than taken from the report.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
