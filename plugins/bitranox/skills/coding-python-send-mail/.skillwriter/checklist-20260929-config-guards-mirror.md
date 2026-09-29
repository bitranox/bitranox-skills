# skill-writer checklist - coding-python-send-mail (2026-09-29, btx_lib_mail config guards mirror)

Source: the tool repo's python-send-mail skill as changed for the btx_lib_mail release after
1.6.0 (empty blocked-set refusal, `credential_fields` check). This mirror is regenerated from that
twin; the two by-convention divergences (`name:` and the repo-only self-install blockquote) are
re-applied, nothing else differs.

- [x] The authenticated `send()` example loads the password at runtime
      (`os.environ["BTX_MAIL_SMTP_PASSWORD"]`) instead of the literal `("user", "pass")`.
- [x] The skill names `redact_validation_error` (for a plain pydantic model that cannot inherit
      `SecretSafeModel`, raised outside the `except` block), `AttachmentViolation` and
      `violation_type` (branch on the member, never the message text), and lists
      `AttachmentSecurityError`, `AttachmentViolation`, `SecretSafeModel` and
      `redact_validation_error` in the public API sentence.
- [x] The skill teaches that `ConfMail` refuses an empty blocked extension or directory set without
      an allowlist unless `attachment_allow_empty_blocklists=True` (one bool for both axes), that a
      config `[]` meaning "defaults" must be dropped before `ConfMail`, and that the `send()`
      keyword `frozenset()` stays allowed.
- [x] The skill teaches that `credential_fields` is checked at class definition (`TypeError` for a
      typo, an alias, a plain str, or an annotation without `ClassVar`), and the older sentence
      saying such an annotation is silently "ignored" is replaced.
- [x] RED route: the behavioural RED is contaminated here (redcheck `--corpus-cascade` reported
      STRONG inherited coverage for all three scenarios), so the RED/GREEN evidence is a text check
      of the artifact: 7 required facts, all FAIL on the previous text, all PASS on the new text.
- [x] RED behavioural run on the previous text (inert probe): an agent invented an
      `exc.violations` attribute for the attachment refusal, predicted a silent leak for a
      misspelled `credential_fields` name, and guessed the redaction and empty-list behaviour.
- [x] GREEN behavioural run on the new text: all six tasks answered from quoted lines, including
      dropping the `[]` keys, branching on `violation_type`, `redact_validation_error` outside the
      `except`, `TypeError` for the typo, and the opt-out for a deliberate empty set.
- [x] GREEN `Skill gaps` worked: "is the opt-out one flag for both axes" and "is the redacted
      error safe to log" CLOSED in the text; exact `TypeError` message text and version drift
      DECLINED (install-local `help()` answers both). RED results lost in GREEN: none.
- [x] Every new example executed against the installed library with output assertions.
- [x] MIRRORED skill: `repo-gate.py --mirrors` reports 0 of 10 pairs drifted.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
