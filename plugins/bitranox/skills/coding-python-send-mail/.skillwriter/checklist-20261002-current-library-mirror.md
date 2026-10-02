# skill-writer checklist - coding-python-send-mail (2026-10-02, current-library mirror)

The marketplace copy is brought level with its twin, `libs/btx_lib_mail/skills/python-send-mail`,
which describes btx_lib_mail 3.1.0. The text was authored and tested in the twin's repo; this
change is the mirror sync.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The content is the twin's, so the test that governs it is the twin's;
      here the check is that the two copies say the same thing.

## RED / GREEN (twin)
- [x] RED, the previously shipped text: 0 of 8 application questions answered from the text; it
      stated that a Linux sender sends `invoice.exe`.
- [x] GREEN, this text: 7 of 8 answered from direct quotes; the eighth (no host from any source)
      is closed by the added exit-code sentence. The test example executes.

## Mirror check (here)
- [x] This copy and the twin are identical after `repo-gate.normalise_mirror` (name field, H1
      echo and self-install blockquote are the only divergences).
- [x] The `checklist-20261002-ascii-port-mirror.md` change (non-ASCII-digit port) is part of the
      same text and carried in the same commit.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
