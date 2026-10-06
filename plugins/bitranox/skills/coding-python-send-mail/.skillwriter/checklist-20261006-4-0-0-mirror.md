# skill-writer checklist - coding-python-send-mail (2026-10-06, btx_lib_mail 4.0.0 mirror)

The marketplace copy is brought level with its twin, `libs/btx_lib_mail/skills/python-send-mail`,
which describes btx_lib_mail 4.0.0: `send()` returns `True` or raises, warn-and-skip for a missing
attachment or an invalid recipient, the fallback rules of the `send()` overrides, a generator of
attachment paths, a NUL in the credentials, STARTTLS off for a relay without TLS, the environment
variable behind each CLI option, what `skipped` and `data.recipients` report under `--json`, an
unreadable attachment reported as `AttachmentNotFoundError`, and a bidirectional formatting
character in an attachment name refused as `FILENAME`.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: 10 retrieval and application questions answered from
      the text alone, each answer backed by a direct quote or marked NOT IN TEXT / GUESS; every
      quote checked to occur verbatim in the file that arm was given.

## RED
- [x] The previously shipped text, 10 questions (`if not send(...)`; skipping one invalid
      recipient; `credentials=""`; a `Path.glob` generator; a relay on port 25 without TLS; the
      `--json` field for a partial delivery; an unreadable attachment; the variable behind
      `--timeout`; a U+202E file name; where `--json` goes): 3 answered correctly from the text.
      Silent on 5 (`credentials=""`, the generator, the `--timeout` variable, the U+202E name, and
      no skip mechanism for a recipient); a GUESS on the TLS-less relay; and one WRONG answer
      quoted from the text itself: an unreadable attachment "propagates unchanged" as
      `PermissionError`, where the library raises `AttachmentNotFoundError`.
- [x] Inherited-context check: every arm answered by direct quote, and each quote was matched
      against the file that arm was given (all RED quotes occur in the old text, all GREEN quotes
      in the new), so an answer drawn from inherited context could not pass as a text answer.

## GREEN
- [x] The new text, same 10 questions: 10 of 10 answered with direct quotes, each confirmed in the
      file.
- [x] Skill gaps reported by GREEN, each decided:
      - the `credentials` and `smtphosts` fallback rules shared one sentence, so `credentials=""`
        read as falling back when it raises: CLOSED (one sentence per parameter).
- [x] GREEN diffed against RED in both directions: every question RED answered correctly
      (`send()` never returns `False`, `skipped`, `--json` before the subcommand) is still
      answered in GREEN.
- [x] Quote-back on the closed gap: `credentials=""`, `smtphosts=""` and `credentials=()` each
      answered by a direct quote of the rewritten sentences.

## Execution
- [x] Every changed claim executed against the installed library: `credentials=()` falls back and
      `credentials=""` / `0` raise `InvalidInputError`; `smtphosts=[]`, `()` and `""` fall back
      and `0` / `False` raise; a NUL in the password is refused; a `Path.glob` generator is
      accepted; an unreadable attachment raises `AttachmentNotFoundError` (`can not be read
      (EACCES)`) and is skipped with `raise_on_missing_attachments=False`; an invalid recipient
      is skipped with `raise_on_invalid_recipient=False`; a U+202E name is refused with
      `violation_type` `AttachmentViolation.FILENAME`; `--timeout` reads `BTX_MAIL_SMTP_TIMEOUT`.

## Mirror check
- [x] This copy and the twin are identical apart from the name field, the H1 echo and the
      self-install blockquote (`repo-gate.py --mirrors`: in sync).

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added (examples use `example.com`).
- [x] Description measured: under the 1024-character cap.
