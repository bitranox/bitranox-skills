# skill-writer checklist - infra-swap-tuning (memory rules folded in)

- [x] Rule: The agent should replace the device rather than reset it or restart the setup service.
      After swapoff it should run hot_remove then hot_add under /sys/class/zram-control to get a
      fresh uninitialised device, and start dev-zram0.swap. It should know that zramctl --reset
      can delete the node, and that a half-run leaves an initialised device that returns EBUSY on
      comp_algorithm. It should recover a stuck device with reset-failed, mkswap and swapon
      --priority --discard, and verify on the host with zramctl and swapon --show, never the
      deploy summary.
      Where: SKILL.md, ## Automating it idempotently: lead line changed to 'Three traps, each of which
      produces a green run and a broken host:' and a third bullet appended after the 'Skip on the
      DESIRED STATE' bullet
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts.
- [x] GREEN quote-back on haiku and opus against the edited files (5 questions), again after the
      review fixes for every question, and a third time for the 2 questions the fix-delta fixes
      touched: every answer quoted the edited text, no NONE. Quotes were substring-checked against
      the files; the pre-edit snapshots fail the same check.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed or
      declined with evidence by the fixer, and the fix delta re-reviewed.
- [x] Each GREEN Skill gaps list triaged: 4 closed in the text, 8 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
