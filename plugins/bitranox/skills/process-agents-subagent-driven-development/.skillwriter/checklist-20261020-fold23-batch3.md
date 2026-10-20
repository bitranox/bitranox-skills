# skill-writer checklist - process-agents-subagent-driven-development (2026-10-20, fold23 batch 3)

- [x] Change (correction): the effort paragraph said "A dispatch has no per-call reasoning-effort
      field". It now names three channels - (1) the Agent tool's own `effort` field, settable only
      when the user, CLAUDE.md or a skill explicitly asks, ignored for a `fork`; (2) the agent-type
      definition; (3) a Workflow `agent()` `opts.effort` - and says the ask restriction binds
      channel (1) only. A line under the Role/Effort table says the same for a reader who skims
      to the table. Ground truth: the installed Claude Code 2.1.304 binary contains the Agent
      tool's field description verbatim ("Set this ONLY when the user, or instructions such as
      CLAUDE.md or a skill, explicitly ask ...", "Ignored for subagent_type"); the Workflow
      authoring reference documents `opts.effort` with no ask requirement.
- [x] Change: File Handoffs gains "Stale brief" - re-read later tasks and Global Constraints
      against the shipped code after a behaviour-changing review, a fix to code the plan pins
      verbatim, an accepted deviation (a Minor-rated one is corrected in later tasks, since Minors
      get no fix round), or a changed way of working (replace the retired mechanism in Global
      Constraints); amend the plan, then regenerate the brief.
- [x] Change (consistency): "Constructing Reviewer Prompts" now allows an earlier review finding
      restated as a short rule, matching the new bullet, so the two no longer disagree.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first SKILL.md edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): effort - partial and
      WRONG (the false "no per-call reasoning-effort field" sentence); stale brief - partial (the
      generic brief contents only). Behavioural RED replaced on purpose: the stale-brief rule is in
      the always-loaded memory index of the authoring machine.
- [x] GREEN quote-back on haiku and opus, quotes substring-checked: effort -> SKILL.md:135 "Three
      channels set a subagent's reasoning effort; only the Agent tool's own field needs an
      explicit ask."; stale brief -> :367 "Stale brief:".
- [x] GREEN diffed against RED both ways: the RED's correct parts (agent-type definition, Workflow
      `opts.effort`, set only at the extremes) are still present; the false sentence is gone
      (0 hits for "per-call reasoning-effort field").
- [x] Gaps closed or declined, each closure re-tested by quote-back: closed - the table's `low` row
      vs the Agent-field ask rule (the restriction is scoped to channel (1), plus the line under the
      table); the first lead "Effort is set per dispatch only when something explicitly asks for
      it" read as covering every channel and made haiku refuse the Workflow channel - reworded to
      "only the Agent tool's own field needs an explicit ask", after which two haiku runs answered
      both channel questions correctly; "fix the deviation now" vs "Minors never get a fix round"
      (Minor deviations go to later tasks); whether Global Constraints gets the NEW mechanism
      (replace it); declined - what counts as an explicit ask from a vague user request for speed
      (left to judgement), ledger-vs-plan order (no consequence).
- [x] Description measured: unchanged
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII
