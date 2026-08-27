# skill-writer checklist - write-humanize-de (2026-08-27, audit bucket G)

Die deutsche Fassung wiederholt dieselbe falsche Zusicherung.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every defect here is a FACTUAL claim, so the test is a
      ground-truth check against the real file, the installed package or live tool output, not a
      pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is the one the skill names - a ground-truth check whose result is immune to
      inherited context.
- [x] Derselbe Befund wie in `write-humanize-en`, mit derselben Messung: U+2028 in einem
      Inline-Code-Span passiert den Sweep und wird vom Skript trotzdem umgeschrieben. Hook und
      Skript teilen sich keine gemeinsame Funktion, sondern sind zwei Laeufe ueber dieselben Regeln.

## GREEN
- [x] Der Absatz benennt jetzt beide Funktionen, sagt dass es Zwillinge sind, nennt die
      abweichende Zeichenklasse samt Ursache und ersetzt die Zusicherung durch den tatsaechlichen
      Schutz.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
