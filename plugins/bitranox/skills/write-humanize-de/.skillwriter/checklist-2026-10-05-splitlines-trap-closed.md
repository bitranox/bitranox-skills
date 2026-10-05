# Skill-writer checklist: Zeilenumbruch-Codepoint-Falle als geschlossen beschrieben (2026-10-05)

Umfang: derselbe stale Hinweis wie im englischen Zwilling `write-humanize-en` - die deutsche
Fassung behauptete, ein Zeilenumbruch-Codepoint (U+2028, U+2029, U+0085) bleibe "fuer den Detektor
unsichtbar" und werde trotzdem vom Skript umgeschrieben, weil `str.splitlines()` dort trenne.
Gegen den aktuellen Code geprueft (`tell_chars.py`): `find_tell_lines` und
`transform_outside_code` teilen inzwischen dieselbe `split_lines()`, die genau diese drei
Codepoints NICHT als Zeilenende behandelt und laut eigenem Docstring die alte Uneinigkeit
zwischen beiden Laeufen geschlossen hat. Die Behauptung war veraltet; der beschriebene Fehler ist
geschlossen, nicht offen. Passage entsprechend umgeschrieben.

## Pruefung

- [x] Behauptung gegen den aktuellen Code geprueft: `tell_chars.split_lines`-Docstring und beide
      Aufrufstellen gelesen (`find_tell_lines` Zeile 251, `transform_outside_code` Zeile 134).
- [x] Reine Sachkorrektur einer Aussage ueber das Werkzeugverhalten, keine neue Regel und kein
      neuer Arbeitsschritt - die umgebende Anweisung (Beispiele in Backticks halten) bleibt
      unveraendert und aus eigenem Grund richtig, daher kein RED/GREEN-Drucktest noetig.
- [x] Frontmatter nicht beruehrt; `description` unveraendert.
- [x] Absatz nach der Bearbeitung erneut gelesen - schluessig, kein Widerspruch zu den
      Nachbarsaetzen ueber den Backtick-Schutz.

## Sicherheit und Hygiene

- [x] Diff geprueft: nur Prosa, kein Geheimnis, keine Adresse, kein Hostname, kein echter
      Maschinenpfad hinzugefuegt.
- [x] Neuer Text ist ASCII-sauber (keine Gedankenstriche oder typografischen Anfuehrungszeichen) -
      per grep ueber den Diff bestaetigt.
