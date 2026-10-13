# skill-writer checklist - coding-python-send-mail (2026-10-13, btx_lib_mail 4.2.0 mirror)

The marketplace copy is brought level with its twin, `libs/btx_lib_mail/skills/python-send-mail`,
which describes btx_lib_mail 4.2.0: internationalised addresses over RFC 6531 SMTPUTF8 (what works,
the relay requirement, `SMTPUTF8NotSupportedError` and the host order, NFC), and installing with
uv / uvx and a 7-day `--exclude-newer` cooldown, with the supply-chain reason and the uv installer.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval questions answered from the text alone, each
      answer a direct quote or the word NONE; every quote checked to occur in the file that arm was
      given.

## RED
- [x] The previously shipped text, 5 questions (install the CLI and add the library with a cooldown;
      why a cooldown matters; send to `empfänger@müller.de` - relay requirement and a host without
      it; what a decomposed sender becomes on the wire; how to install uv): all 5 answered NONE. The
      only near text was the non-ASCII CREDENTIAL failover, which the arm correctly refused to apply
      to addresses.
- [x] Inherited-context check: every arm answered by direct quote and each quote was matched against
      the file that arm was given, so an answer drawn from inherited context could not pass as a
      text answer.

## GREEN
- [x] The new text, the same 5 questions plus two (a one-off cooldown run from an agent; ASCII mail
      through a relay without SMTPUTF8): 7 of 7 answered with direct quotes, each confirmed in the
      file.
- [x] Skill gaps reported by GREEN, each decided:
      - "fails over to the next host, which is not demoted for ASCII recipients" was ambiguous
        about which host, ASCII mail through such a relay was only implied, and a mixed recipient
        list was unstated: CLOSED (the refusal is about the message, so the relay is NOT moved to
        the back; each recipient is a separate message, so ASCII recipients still go through it).
      - merging into an existing `[tool.uv]` table, checking whether uv is already installed,
        choosing N, and the two command spellings `btx_lib_mail` / `btx-lib-mail` (both are
        registered): DECLINED - plain TOML, out of scope, an owner choice (7 days), and correct as
        written.
- [x] GREEN diffed against RED in both directions: RED answered nothing, so no baseline result can
      be lost.
- [x] Quote-back on the closed gaps: the mixed-recipient case, ASCII mail through a relay without
      SMTPUTF8, and whether the refusing host is moved to the back each answered by a direct quote.

## Execution
- [x] Every changed claim executed against the library or uv: `uvx --exclude-newer "7 days"
      btx-lib-mail --version` resolves the newest release older than 7 days; `uv tool install
      --exclude-newer "7 days" btx_lib_mail` stores `exclude-newer-span = "P7D"` in the tool
      receipt; `[tool.uv] exclude-newer = "7 days"` plus `uv lock` applies to a project, while
      `uv add --exclude-newer` writes nothing to `pyproject.toml`; `validate_email_address`
      accepts German and CJK addresses and reports non-ASCII lengths in UTF-8 octets;
      `SMTPUTF8NotSupportedError` subclasses `smtplib.SMTPNotSupportedError` and `BtxMailError`;
      the wire behaviour (DATA and BDAT, HELO fallback, failover, host order) is covered by the
      library's aiosmtpd tests.

## Mirror check
- [x] This copy and the twin are identical apart from the name field, the H1 echo and the
      self-install blockquote (`repo-gate.py --mirror-of`: in sync).

## Quality
- [x] Present tense; describes only current behaviour (no "from version" lines).
- [x] No address, MAC or machine path added. Hostnames are `example.com`, plus the IDN example
      `müller.de` from the design, which is not a reserved name; a reserved IDN form
      (`müller.example`) is the alternative if that matters.
- [x] Description measured with len(): 737 characters, under the 1024 cap; its zero-install
      example now carries the cooldown (`uvx --exclude-newer "7 days" btx-lib-mail send ...`), and
      the trigger map and skill catalog were rebuilt for it.
