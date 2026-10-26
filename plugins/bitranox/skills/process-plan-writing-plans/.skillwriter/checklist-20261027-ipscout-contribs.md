# skill-writer checklist - process-plan-writing-plans (2026-10-27, ipscout-contribs)

- [x] Change: Self-Review gains check 4, "Absence checks". A step that verifies a rename or
      removal with "`grep X` must print nothing" must not match what the plan leaves behind: a
      substring pattern matches the new name (`grep '_reason'` hits `failure_reason`), so the step
      can never pass and a literal executor stops or "fixes" correct code. Match whole identifiers
      (`grep -nw`, or `\b` with `grep -E`) and dry-run each check against the intended after-state
      (a scratch file with the code the plan's steps write): nothing printed there, the line
      printed when each old name in turn is planted back. Placed in Self-Review, the pass the plan
      writer runs over every command the plan contains.
- [x] Item still open: the pre-change SKILL.md has no text on absence checks, word boundaries or
      dry-running a verification command (grep for `grep -nw`, `intended after-state`,
      `planted back`, `word bound`, `substring` found nothing relevant).
- [x] Claims verified by running them in a scratch repo: `grep -n '_within\|_reason'` matches
      `def failure_reason():` (rc 0) after the rename; `grep -nw '_within\|_reason'` and
      `grep -nE '\b(_within|_reason)\b'` print nothing on the after-state (rc 1); `grep -nw`
      prints a planted `y = _reason()` and an `obj._reason` attribute access (rc 0). Grepping only
      the `def _reason` form misses call sites, so the text does not offer it.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route: a text check of the artifact. The installed plugin still carries the pre-change
      text, so a no-skill behavioural arm would measure the old version. redcheck
      --corpus-cascade reported a term overlap with the always-loaded memory index; the named
      lines were read and none states this claim (the overlap is on ordinary words). Text check:
      `grep -nw`, `intended after-state`, `planted back` count 0 in the pre-change file and 1 in
      the new one. Quote-back on the pre-change passage: NONE on both questions, both tiers.
- [x] GREEN quote-back, opus (effort medium) and haiku, two questions on this passage (what is
      wrong with `grep '_reason'` after the rename; what pattern to use and what to do with the
      check). Both tiers answered both with direct quotes of the new text and NONE for the old
      text. 2 tiers x 2 questions x 2 arms (old/new).
- [x] Gaps closed after GREEN (opus): the after-state does not exist at plan time (now "a scratch
      file holding the code the plan's own steps write"); which name to plant for a two-name check
      (now "each old name in turn").
- [x] Re-probe on the final text, haiku, two questions on the touched sentences (what to dry-run
      against; how many plant-backs for two names). Both answered with quotes of the final text;
      no new undecided gap.
- [x] Gaps declined: how to build the scratch file, by hand or by running steps (judgement left to
      the plan writer); whether the dry-run is a "re-review" the closing line waives (it is part of
      check 4 itself); BRE `\|` with `-w` beside `\b` with `-E` (each named with its own grep mode,
      both verified); the exact plant-back command (the plan writer composes it).
- [x] Quotes checked with quotecheck against the SKILL.md: the final-text quote OK, a planted
      false quote MISMATCH (rc 1), so the check can fail.
- [x] GREEN diffed against RED both ways: only check 4 is added; checks 1-3 and the closing
      paragraph are unchanged, nothing the old text taught is lost.
- [x] Frontmatter description unchanged; no trigger map rebuild needed.
- [x] ASCII only (no non-ASCII byte in SKILL.md); no addresses, hostnames, user names or home
      paths added; no version-history wording in the added text; the file has no tables.
- [x] Repo hook tests that read skills pass (`-k "skill or description or trigger or tell"`:
      948 passed). The skill has no tests/ dir.
