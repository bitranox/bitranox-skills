# skill-writer checklist - coding-python-layered-config (2026-10-02, lib_layered_config 7.0.0)

Four statements in the skill contradicted lib_layered_config 7.0.0 or never matched it: `.env`
scalars staying strings, a secret's `null`/`none` becoming None, Linux `/etc/<slug>/` as a
fallback, and nothing on non-string YAML keys. A fifth gap surfaced in GREEN: the skill never said
that a `.env` key carries no `<SLUG>___` prefix.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: retrieval scenarios answered only from the skill text, old text
      (RED) against new text (GREEN), same questions, inert text-only probe, model pinned to sonnet.
- [x] Scope: five bullets in three sections; frontmatter untouched, no routing keyword moved.
- [x] Every claim checked against the released library before it was written: unquoted `.env`
      `SERVICE__PORT=5432` reads as int 5432; a prefixed key in `.env` becomes a `my_app` section;
      with both `/etc/xdg/<slug>/config.toml` and `/etc/<slug>/config.toml` present, the key takes
      the `/etc/<slug>` value; a YAML `1:` key refuses the file with `LayerLoadError`.

## RED (old text)
- [x] Secret `MY_APP___EMAIL__SMTP_PASSWORD=null`: answered None (wrong; the library keeps "null").
- [x] Both `/etc` files set `timeout`: answered 10, reading "fall back" as consulted only when the
      XDG file is absent (wrong; 20).
- [x] Unquoted YAML `1:` key: NOT STATED.
- [x] `.env` `SERVICE__PORT=5432`: NOT STATED - read the line as an invalid, unprefixed override.

## GREEN (new text)
- [x] Secret: "null" as text, quoting the sensitive-key sentence.
- [x] Both `/etc` files: 20, quoting the "a key set in both takes the `/etc/<slug>` value" sentence.
- [x] YAML `1:`: the file is refused, quoting the new design bullet.
- [x] `.env` `SERVICE__PORT=5432`: still NOT STATED, same reason as RED - a gap the edit did not
      open but did not close either.

## REFACTOR
- [x] Every dispatch asked for a `Skill gaps` section; each reply's list is recorded here.
- [x] Gap closed: added "A `.env` key is the key path WITHOUT the prefix", including what a
      prefixed line in `.env` does. Re-test of the `.env` questions only: unquoted -> int 5432,
      prefixed -> separate `my_app` section, quoted -> str "5432", each by direct quote.
- [x] Gap declined: "what `config.get` returns for an unset key" - the probe excerpt omitted the
      "Load config" section, which shows `config.get(key, default=...)`; not a gap in the skill.
- [x] Gap declined: exact exception class for the YAML refusal - the skill teaches design, the
      class lives in the API reference it links.
- [x] RED vs GREEN diffed both ways: no answer RED got right was lost in GREEN.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Twin `libs/lib_layered_config/skills/python-layered-config/SKILL.md` carries the same edits;
      the two are identical after the mirror normalisation.
