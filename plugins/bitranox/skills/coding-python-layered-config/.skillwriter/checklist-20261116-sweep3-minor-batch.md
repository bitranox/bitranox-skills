# skill-writer checklist - python-layered-config (sweep-3 MINOR text batch)

- [x] Change: five facts the skill got wrong or left out, closing QUALITY-REVIEW R5-F2, R5-F3 and
      the sweep-3 skill omissions.
      (1) Per-OS paths: a layer's base file is always TOML; a `config.yaml`/`config.json` beside it
      is not read, YAML and JSON go in `config.d/`. The old "`.yaml`/`.json` also accepted" read as
      layer files (measured: config.json alone -> {}, config.yaml alone -> {}, config.d/10-x.yaml
      alone -> {'b': 2}).
      (2) Env overrides: the null/none-kept-as-text rule is decided by the variable's own lowercased
      name, so `..._DB__DBPASSWORD=null` makes a file's `dbPassword` None while `..._DB__DB_PASSWORD=null`
      keeps "null" (measured; is_sensitive("dbpassword") False, is_sensitive("dbPassword") True).
      (3) CLI: library warnings print on stderr as `warning: <event> key=value ...`, stdout and the
      --json envelope unchanged (measured: read-json --json with app a=1 under user [a] b=2 printed
      `warning: type_conflict key=a layer=user path=... old_type=scalar new_type=mapping`).
      (4) `Config.get_redacted(key, default=)` (measured: masked password, visible host, default 7).
      (5) `generate_examples` leaves existing files and does not list them unless force=True;
      `generate_examples_report` in `lib_layered_config.generate` returns `ExamplesReport`
      .created/.kept (measured: 5 created, then 0, report 0 created 5 kept, force 5).
      Plus one sentence from the GREEN round: a `config.d/` loads without a `config.toml` beside it.
- [x] Receipt held before the edit. The skill has no decision ledger (`skill_decisions.py show
      coding-python-layered-config` printed nothing), so no rejected or removed decision applies.
- [x] RED, haiku, pre-edit text, 5 questions: Q1 answered that a lone config.yaml loads (wrong,
      quoting "also accepted"), Q2 answered "null" (wrong, quoting the sensitive-key rule), Q3-Q5
      "no deciding sentence".
- [x] GREEN, haiku and opus, new text, same 5 questions: 2 tiers x 5 = 10 cells correct, each
      quoting the new sentence. Opus named one remaining reading (the `.d/` bullet implied a
      `config.d/` needs a `config.toml`), closed with the "Either can exist without the other"
      sentence and re-probed (haiku, final text): a lone `config.d/10-db.yaml` loads, and with
      both `config.toml` and `config.json` only the TOML is read - both correct, quoted. Declined:
      saying whether an ignored top-level `config.json` is warned about; the skill claims no
      warning and no reader question in this batch needed it.
- [x] Width and fence check: no fence touched, no non-ASCII added; the longer lines flagged by the
      width scan were over width before this change.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
- [x] Twin: this SKILL.md is the lib's skills/python-layered-config/SKILL.md with the name line
      changed (diff shows only line 2), parked with the [70] marketplace commit.
- [x] Decisions: none - factual corrections and additions describing the library's current
      behaviour, each measured above.
