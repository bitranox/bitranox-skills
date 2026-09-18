# Skill-writer checklist: write-humanize-de section 20 (2026-09-18)

Scope: section 20 and the one completion-checklist bullet. The skill told a German writer to
replace typographic quotation marks with straight ones, which after 6.14.0 means removing
punctuation the tell set permits and the repair script deliberately protects. The section's own
first sentence already conceded the characters are correct German, so it contradicted itself
before it contradicted the gate. Advice change, decided by the user; no frontmatter, name or
trigger changed.

## RED (baseline, pre-change text)

- [x] Text check again rather than a subagent, for the reason recorded in the 6.14.0 artifact:
      the machine's own cascade and memory facts teach the pre-change answer, so a behavioural
      arm would answer from them in both directions.
- [x] RED proven on the real text, naming both sites:
      `test_no_german_example_flattens_permitted_punctuation_away` failed quoting the section 20
      pair, and the checklist test failed quoting
      `- Gedankenstriche, Emojis, Fettschrift-Header und typographische Anfuehrungszeichen entfernt`.
- [x] The first version of the pair parser read fenced blocks only and matched 1 pair of 30 while
      still failing on the right one - a test that looked like it worked. The pair-count CONTROL
      caught it: 29 of the 30 examples are blockquotes and exactly one is fenced. The parser now
      reads both forms and the control requires it to find all but one of the declared markers.
- [x] A second control asserts every parsed example is non-empty, since a parser returning empty
      strings satisfies the flattening test vacuously.
- [x] Measured with the widened parser: section 20 was the ONLY example of the 30 that flattened
      German punctuation away. The defect was not systemic.

## GREEN (post-change text)

- [x] Section 20 is now about INCONSISTENCY, which is what the original problem statement
      described: the Vorher mixes low-9, straight and guillemet quoting in one passage, the
      Nachher unifies on one German style rather than flattening to ASCII.
- [x] The checklist bullet split in two: dashes/emoji/bold headers stay under "entfernt",
      quotation marks move to "vereinheitlicht".
- [x] Full hook suite green: 2891 passed, 1 skipped, 1 xfailed, exit code read from a file.

## REFACTOR

- [x] The checklist test was REWRITTEN after its RED, so the version that ships had never been
      seen to fail. Proven by mutation: reverting the bullet to the removal claim failed it by
      name, and the file was restored from a copy taken beforehand rather than with git checkout,
      which would have discarded the uncommitted section-20 rewrite in the same file.
- [x] It keys on the POSITIVE claim ("vereinheitlicht" present, "entfernt" absent), because a
      bare must-not-say-entfernt check also passes when the bullet disappears entirely.
- [x] The flattening check deliberately permits normalising one German style to another, since
      that is exactly what a consistency fix looks like. What it rejects is an "after" with no
      German punctuation left where the "before" had some.
- [x] DECLINED: the English section 18 is unchanged. English curly quotes are still tells, U+2019
      and U+201D still block, and its advice is correct as written.
- [x] Noted while reading the real bytes: the old Vorher opened with U+201E and closed with an
      ASCII quote, so the example was already half-typographic. The new Vorher keeps that as one
      of the three inconsistent spellings it demonstrates.

## Security and hygiene

- [x] Diff reviewed: German prose and one test, no secrets, no credentials, no host or path.
      The test module stays ASCII; the one German term it needs is built with `chr(0x00FC)`.
- [x] No session narrative, operator instruction or scratch path in the skill text or here.
