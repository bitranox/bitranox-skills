# skill-writer checklist - python-logging (2026-10-26, free-threaded 3.14t)

Change: the Install block's `lib_log_rich[orjson]` line moves the extra's cut from 3.15 to 3.14 (lib_log_rich
7.3.0: orjson is a core dependency below 3.14, the optional extra from 3.14), and two comment lines below it name
the supported free-threaded builds (3.14t, 3.15t), say never to add `[orjson]` on them, and say lib_log_rich does
not install on 3.13t. Twin sync of the tool repo's skills/python-logging. No rule, trigger, description or other
instruction changes.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is retrieval: can a reader pick the right install command per interpreter
      from the text.
- [x] RED (text): the pre-edit SKILL.md has 0 lines naming the 3.14 cut (`Python 3.14+ (GIL build)` or
      `normal (GIL) Python 3.14+`) and 1 naming the 3.15 cut, against 16 lines naming `lib_log_rich` as the control
      that the grep read the file.
- [x] GREEN (text): the edited SKILL.md names the 3.14 cut once and the 3.15 cut zero times.
- [x] GREEN (retrieval, quote-back), first text: both tiers (opus, haiku; 2 cells) answered CPython 3.12, normal
      3.14, 3.14t and 3.13t correctly (plain install, `[orjson]`, plain install, no install), each with a direct
      quote. Gaps both reported: "3.13t cannot install" had no clear subject (the library or the extra), it overlapped
      the "below 3.14" rule, nothing said a plain 3.14 install lacks orjson, and nothing said what `[orjson]` does
      on a free-threaded build. All four CLOSED in the final text.
- [x] GREEN (retrieval, quote-back), final text, same questions in full plus "`[orjson]` on 3.14t": both tiers
      (opus, haiku; 2 cells) answered all five correctly, quoting "normal (GIL) Python 3.14+: adds orjson, which a
      plain install there lacks", "below 3.14 orjson is a core dependency", "never add [orjson] on them (orjson
      refuses to build free-threaded)" and "lib_log_rich itself does not install on 3.13t." No new undecided gap.
- [x] Twin parity: `repo-gate.py --mirror-of` on the tool repo reports `in sync`.
- [x] Describes the latest release only: the history-line finder matches nothing in the changed lines.
- [x] No address, hostname or path added; no session narrative or private provenance here.
- [x] Skill gaps reported by the probes, each decided:
      - What "fastest" means, and how to check which encoder is active (opus): DECLINED - the extra's stated
        purpose is the instruction; the encoder choice is internal and needs no reader action.
      - Interpreter selection with `uv add`, and `uv pip install` with extras (opus): DECLINED - owned by the uv
        skill.
      - What `[orjson]` does on 3.12 (opus): DECLINED - "below 3.14 orjson is a core dependency" makes the extra
        redundant there; no reader action follows.
      - uv's exact error text and rollback behaviour when `[orjson]` is added on 3.14t (both tiers): DECLINED - the
        text says never to do it and why; the installer's output is not this skill's to document.
      - One project targeting both GIL 3.14 and 3.14t (opus): DECLINED - choosing dependency markers is the
        consumer's packaging decision, owned by the uv skill.
      - No alternative interpreter named for 3.13t (both tiers): DECLINED - the supported builds are listed on the
        line above it; picking one is the reader's decision.
