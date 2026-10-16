# skill-writer checklist - coding-python-send-mail (2026-10-16, inline CID images)

The marketplace copy is brought level with its twin, `libs/btx_lib_mail/skills/python-send-mail`,
which documents `send(inline_images=...)` and `--inline-image` of btx_lib_mail 4.5.0: images the
HTML body shows as `cid:<Content-ID>`, sent inside the message.

## PLAN
- [x] Skill type: reference. Test approach: retrieval questions answered from the text alone, each
      answer a direct quote or the word NONE, by a probe agent restricted to reading the two texts.
- [x] Ordering: the new section was drafted before the probe; RED ran against the published 9.1.1
      text, so it measures the old behaviour.

## Contamination
- [x] The probe was told to read only the two staged texts and to answer each from one file alone.
      `redcheck --corpus-cascade` was NOT run; the old text contains no `inline_images`, `cid:` or
      Content-ID at all (grep count 0), so a NONE on it cannot come from the text.

## RED
- [x] Pre-change text, four questions (embed a logo without remote images; logo under /root/.local;
      missing logo with raise_on_missing_attachments=False; the CLI flag): NONE to all four.

## GREEN
- [x] New text, same questions: each answered by a direct quote of the "Inline images" section or
      the table row.
- [x] Gaps reported by GREEN, each decided:
      - remedy for the /root refusal, size limit, minimum version, `send()` keyword vs `ConfMail`
        field, `INLINE_IMAGE_TYPES` in the export list, CLI without `--html-body`, unreferenced
        image or unknown cid: CLOSED; each answer was executed against the 4.5.0 tree first
        (`attachment_blocked_directories=frozenset()` accepts a /var path, a 100-byte size cap
        refuses as SIZE, no `ConfMail` field, an unreferenced image is sent, the CLI exits 22).
      - asserting on the image part with RecordingTransport: DECLINED - the testing section already
        shows reading the raw message with `message_from_bytes`; walking its parts is plain stdlib.

## Execution
- [x] The section's example was run against the 4.5.0 tree with a recording transport: the parsed
      tree is multipart/alternative > text/plain + multipart/related > text/html + image/png with
      `Content-ID: <logo>`; an image under /var/tmp is refused as DIRECTORY.

## Mirror check
- [x] This copy is generated from the twin by the three permitted divergences (name field and the
      self-install blockquote); the same transform applied to the twin's 4.4.0 text reproduces the
      previous copy byte for byte.

## Quality
- [x] Present tense; describes only current behaviour; ASCII punctuation (strip_typographic_tells
      --check passes).
- [x] No addresses beyond `example.com` documentation values.
