# skill-writer checklist - coding-python-send-mail (2026-10-01, btx_lib_mail 3.0.0 host validation mirror)

Source: the tool repo's python-send-mail skill as changed for btx_lib_mail 3.0.0 (`ConfMail` checks
every `smtphosts` entry with `validate_smtp_host`). This mirror carries the same new paragraph; the
by-convention divergences (`name:`, the H1 echo, the repo-only self-install blockquote) are
untouched, nothing else differs.

- [x] The skill says that from 3.0.0 `ConfMail` checks each `smtphosts` entry at construction,
      validation and assignment, raising `pydantic.ValidationError` with `loc` `("smtphosts",)` and
      the host never repeated, and names the refused shapes: a port outside 1-65535 or not a number,
      an unclosed IPv6 bracket, an unbracketed IPv6 address, a port with no host name, two hosts in
      one entry.
- [x] It says a blank entry is dropped, that before 3.0.0 these surfaced only at delivery, and that
      only the CLI splits a comma-separated `--host` / `BTX_MAIL_SMTP_HOSTS`.
- [x] Inherited-context route: the edited tool repo's own CLAUDE.md states the new behaviour and a
      dispatched agent inherits it, so the behavioural arm was replaced by a quote-back text check
      of the skill file (answers must be a verbatim quote of the supplied file, or NONE).
- [x] RED (sonnet, previous text, Q1-Q5: construction-time refusal of a bad port, a blank entry,
      a comma string, unbracketed IPv6, the version): NONE on all five; its guesses disagreed
      (dropped vs refused, one malformed host vs error).
- [x] GREEN (sonnet, new text, Q1-Q6): Q1-Q5 each answered with a direct quote of the new
      paragraph.
- [x] GREEN `Skill gaps` worked: no literal multi-host `ConfMail(...)` line, and the comma case
      needed reading across the sentence - CLOSED (the text now shows the refused string and the
      list form). Exception type stated once for the whole enumeration - DECLINED (one sentence
      governs every listed case). RED results lost in GREEN: none.
- [x] Quote-back re-test of the touched questions (Q3, Q6): both answered with direct quotes.
- [x] Every claim executed against the library: six malformed shapes refused with `loc`
      `("smtphosts",)` and the host absent from `str()` and `json()`, assignment refused,
      `[fe80::1]:25` accepted, `""` read as no hosts, the two-host list accepted.
- [x] MIRRORED skill: `repo-gate.py --mirrors` reports 0 of 10 pairs drifted.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] No session narrative or private provenance added; addresses are `example.com` and
      documentation-range IPv6 only.
