# skill-writer checklist - coding-python-send-mail (2026-09-29, btx_lib_mail 1.6.0 mirror)

Source: the tool repo's python-send-mail skill as changed for btx_lib_mail 1.6.0 (secret safety).
This mirror is regenerated from that twin; the two by-convention divergences (`name:` and the
repo-only self-install blockquote) are re-applied, nothing else differs.

- [x] WRONG in the previous text: a LOGIN-only server refusing a non-ASCII credential does not
      surface as `smtplib.SMTPNotSupportedError` from `send()`. The per-host failure is caught and
      logged as a WARNING, and `send()` raises `RuntimeError` once every host has failed. The skill
      now says to catch `RuntimeError`.
- [x] WRONG in the previous text: "subclass `ConfMail`" did not protect a password field the
      subclass adds. The skill now requires extending the inherited `credential_fields` set as a
      `ClassVar`, with an example, and states that listing the name is what keeps a value out of
      validation errors whatever its type.
- [x] RED: an agent given the previous text wrote
      `credential_fields: frozenset[str] = frozenset({"smtp_password", "db_password"})`, which
      replaces the inherited set and is not a `ClassVar`; run against the installed library, that
      shape leaks an int-typed `db_password` into `errors()` and `json()`, while the documented
      shape does not (a discriminating scalar input, with a leaking control).
- [x] GREEN: an agent given the new text extended the set as a `ClassVar` for two unseen fields
      and caught `RuntimeError` around `send()`. Quote-back of the two contested rules returned the
      governing sentences.
- [x] The LOGIN-only rule is checked against the text rather than behaviourally: always-loaded
      context on the authoring machine already states that `send()` raises `RuntimeError`, so a
      behavioural RED could not fail honestly.
- [x] Every example executed against the installed library with output assertions.
- [x] MIRRORED skill: `repo-gate.py --mirrors` reports the pair in sync.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
