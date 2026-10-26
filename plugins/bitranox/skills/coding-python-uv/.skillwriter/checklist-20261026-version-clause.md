# skill-writer checklist - coding-python-uv (version clause out of the description)

Change: the frontmatter description ended "Baseline is uv 0.10.2 (2026-02-12); the Python-version
behaviours in 06-python-versions.md are measured on 0.11.x." while 05, 06, 07, 09, 10 and SKILL.md
carry gotchas stating "measured on uv 0.13.0". The version clause moves out of the description
into one body paragraph that says what each part follows; 06's "install does not upgrade" gotcha
is re-measured on uv 0.13.0.

- [x] Receipt held (skill_receipt.py start meta-skill-writer ran this session); the editing agent
      loaded the skill through the Skill tool before its first edit.
- [x] Scope: a factual-wording correction, so RED and GREEN are text checks against the files, not
      behavioural arms; no subagent was dispatched (tiers: none, cells: 0).
- [x] RED (text check, pre-edit): the description said 06 is "measured on 0.11.x"; 06 itself held
      three statements naming uv 0.13.0 ("uv 0.13.0 itself writes the minor", "All measured on uv
      0.13.0", "measured on Linux, uv 0.13.0"), so the description contradicted the file it named.
- [x] Re-measured on uv 0.13.0, offline (UV_OFFLINE=1), against a scratch interpreter store
      holding one concrete patch (3.12.12) copied from the local store, with a scratch bin dir:
      - behaviour 1 HELD: `uv python install 3.12` printed "Installed Python 3.12.12" and fetched
        nothing; `uv python upgrade 3.12` tried to download 3.12.15 (refused offline), and with
        3.12.15 present it repointed the minor alias; when current it printed "Python 3.12 is
        already on the latest supported patch release", rc 0, 0.03 s.
      - behaviour 2 HELD: a bare `uv venv` with only the concrete patch wrote
        `home = .../cpython-3.12.12-.../bin`; after the minor install `uv venv --python 3.12`
        wrote `home = .../cpython-3.12-.../bin`, and after the upgrade that venv ran 3.12.15.
      - behaviour 3 CHANGED: a venv on the minor alias records `version_info = 3.12` (the minor
        only), not the patch the example showed; a concrete request records the full patch, and
        `python -m venv` on the alias records `version = 3.12.15`. The rule (ask the interpreter,
        never pyvenv.cfg) still holds; the example and its lead-in are rewritten to the measured
        output.
      - not re-run: "seen on a whole fleet" (an observation, not a local measurement).
- [x] GREEN (text check, post-edit): no file in the skill dir, docs/ or README states "Baseline
      is uv" or "measured on 0.11.x" outside dated .skillwriter artifacts; the new body paragraph's
      "most on 0.13.0, a few on 0.11.x" matches a count of 15 "uv 0.13.0" against 2 "uv 0.11.x"
      statements across the skill files (excluding the new paragraph).
- [x] Description measured with len() on the parsed field: 397 characters, starts "Use when",
      third person, triggers only.
- [x] Router: build_skill_triggers.py regenerated; the only tokens lost are "0.10.2",
      "2026-02-12", "06-python-versions.md" and "0.11.x" (no prompt routes on them);
      "python-version" is kept by naming .python-version pins in the description.
      build_skill_docs.py regenerated docs/skills.md.
- [x] Skill gaps: none recorded, no probe was dispatched.
- [x] ASCII only in the edited files, present tense, no history lines, no private addresses or
      paths in the skill text.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
