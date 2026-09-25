# skill-writer checklist - process-agents-subagent-driven-development (2026-09-25, audit behaviour sync)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every changed line states what a script now does after the
      skill-script audit fixes, so the RED is a ground-truth check of the old text against the
      code, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft. The artifact checks are immune.
- [x] RED, ground truth: the old text named the brief `task-N-brief.md`; `task_brief.py` now
      writes `task-<ID>-<plan8>-brief.md` (its docstring and `default_outfile`), so a report named
      from the old pattern would not sit beside its brief. Pinned by
      `tests/test_sdd_scripts.py::test_task_brief_default_outfile_in_workspace`.
- [x] The old line carried a typographic arrow; it is now ASCII `->`.
- [x] GREEN: a haiku probe given only the new text answered eleven retrieval questions across
      the changed rows and paragraphs (procsig, pushcheck, mutation_arm, fleet_ssh, adjudicate,
      claim_check, ci_wait, transcript_index, git_state, the SDD report name, the session-review
      part loop) all correctly, each with a direct quote of the governing sentence.
- [x] Skill gaps from GREEN decided: (a) the claim_check unreadable-path sentence needed chaining
      to the BROKEN sentence before it - CLOSED, it now names BROKEN itself; (b) no full command
      line shown for a three-path `--scp` - DECLINED, the flag syntax states the arity.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added; ASCII only.
- [x] Present tense, no session narrative, no private provenance.
