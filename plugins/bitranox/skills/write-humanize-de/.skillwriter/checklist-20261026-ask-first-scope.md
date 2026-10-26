# skill-writer checklist - write-humanize-de (2026-10-26, ask-first scope)

- [x] Change: the same rule as write-humanize-en (see its checklist-20261026-ask-first-scope.md),
      in German. "Immer zuerst den Benutzer fragen" becomes "Wann zuerst fragen": text the user
      wrote stays theirs (shown for an opinion or review: deliver, then ask "Soll ich diesen Text
      humanisieren?"; asked only to send it: send it unchanged); outgoing prose the agent wrote at
      the user's request, or a request for the humanizing itself, is humanized without asking; a
      standing humanize rule counts as that request for the agent's own text only. The scope list
      names PR-Beschreibungen und -Kommentare and Issue-Antworten.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: shared with the EN twin, whose guard said the same ("immer zuerst den Benutzer fragen");
      4 cells (opus + haiku), both tiers asked first for an agent-written PR comment.
- [x] GREEN on the German text, haiku, 3 situations, each with the deciding sentence quoted:
      agent-written German PR comment B ("NICHT fragen, wenn DU den ausgehenden Text geschrieben
      hast, ..."); user's own email "Schick das an Bob" C ("Bittet er nur darum, ihn zu senden,
      sende ihn unverändert."); user's blog intro for an opinion A ("Zeigt er ihn dir aus einem
      anderen Grund (Meinung, Review), liefere, worum er gebeten hat, frage dann ...").
- [x] Skill gaps recorded; the remaining ones (mixed requests such as "Was hältst du davon und
      schick es dann", "und verbessere ihn") are declined as judgement left to the agent, as in the
      EN checklist.
- [x] Opus behaviour for the same rule measured on the EN twin (identical structure, same clauses).
- [x] Frontmatter description unchanged (463 chars); trigger map needs no rebuild
- [x] No typographic tells in the added lines (German umlauts only); no history phrasing
- [x] Security scan: prose edit only, no secrets, hostnames, paths or PII
