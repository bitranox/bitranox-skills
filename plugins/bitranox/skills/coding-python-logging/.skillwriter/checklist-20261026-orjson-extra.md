# skill-writer checklist - python-logging (2026-10-26, orjson extra)

Change: the Install block gains one line naming the `lib_log_rich[orjson]` extra that lib_log_rich
7.2.0 introduces (orjson is optional from Python 3.15, a core dependency below it, and a
free-threaded build encodes with stdlib json). Twin sync of the tool repo's skills/python-logging.
No rule, trigger, description or other instruction changes.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is retrieval: can a reader pick the right install command
      per interpreter from the text.
- [x] RED (text): the pre-edit SKILL.md has 0 lines naming `lib_log_rich[orjson]`, against 15
      lines naming `lib_log_rich` as the control that the grep read the file.
- [x] GREEN (text): the edited SKILL.md has 1 such line, the control 16.
- [x] GREEN (retrieval, quote-back): probes given the edited Install block answered CPython 3.12,
      normal 3.15 and free-threaded 3.15t. Both tiers (opus, haiku; 2 cells) gave `uv add
      lib_log_rich`, `uv add "lib_log_rich[orjson]"` and `uv add lib_log_rich` respectively, each
      with a direct quote of the governing clause ("below 3.15 it is a core dependency",
      "Python 3.15+ (GIL build) only: orjson", "a free-threaded build uses stdlib json").
- [x] Twin parity: `repo-gate.py --mirror-of` on the tool repo reports `in sync`.
- [x] Describes the latest release only: the history-line finder matches nothing in the added line.
- [x] No address, hostname or path added; no session narrative or private provenance here.
- [x] Skill gaps reported by the probes, each decided:
      - What the extra does on a build it does not apply to (both tiers): DECLINED - the line
        scopes it "(GIL build) only", which is the instruction a reader needs.
      - Whether lib_log_rich picks up orjson by itself (opus): DECLINED - there is nothing for the
        reader to configure; the encoder is chosen at import.
      - A project whose requires-python spans both sides of 3.15 (opus): DECLINED - choosing
        dependency markers is the consumer's packaging decision, owned by the uv skill.
      - Which encoder is fastest (both tiers): DECLINED - the skill does not rank encoders and the
        question does not change any command.
      - Free-threaded 3.13t / 3.14t, where "below 3.15 it is a core dependency" and "a
        free-threaded build uses stdlib json" both seem to apply (haiku): DECLINED here - the
        package declares free-threaded support for 3.15 only; the product question (install on
        3.13t/3.14t) is filed in the tool repo's backlog.
