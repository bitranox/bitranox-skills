# skill-writer checklist - meta-claude-hooks (2026-10-22, fold23 batch 3, reach-fails rows)

- [x] Change: new section '## Reading the transcript a hook is handed' > '### Which `user` records
      are the person' (shared with the last-user-record row); plus pointer sentence appended to the
      'Do not read the transcript...' note and the I/O contract routing row in SKILL.md. Verified
      against ground truth: marker anchored at start, case-insensitive after lstrip ->
      hooks/self_improve_signals.py:2705-2710 (`_SKILL_BODY_MARKER = "base directory for this
      skill:"`, `.lstrip().lower().startswith`); wired into self-improve-gate.py:357 and
      self-improve-audit.py:165; skill bodies and hook feedback are isMeta ->
      hooks/transcript_turns.py:25-26 and skill-edit-guard.py:19-20 ('a `type: user`, `isMeta: true`
      message whose text starts `Base directory for this skill: <dir>`'); `<\task-notification`,
      `<command-`, `<local-command` prefixes -> transcript_turns.py NOT_TYPED_PREFIXES;
      queued_command attachment -> transcript_turns.py human_text docstring and _queued_human_text.
- [x] Change: Traps worth knowing > 'A guard that scans the raw command string blocks its own
      documentation.' paragraph, appended after the existing 'slice values from the raw text at the
      same offsets.' sentence. Verified against ground truth: length-preserving mask and raw-offset
      slicing for -C comparison -> hooks/block-git-semicolon-chain.py:387-389 ('Every mask preserves
      length, so the same offsets cut the raw text into `raw_parts`, which is what a `-C` path is
      compared on') and :513-516 (the $PLAN/$PROX vs $PLANNING/$PROX example verbatim).
- [x] Change: Traps worth knowing, new paragraph after the raw-command-string trap. Verified against
      ground truth: Bash|PowerShell rule -> io-contract.md:66 'Match `Bash|PowerShell`, not `Bash`
      alone'; gap still live -> hooks/hooks.json registers skill-edit-guard.py only under PreToolUse
      matcher 'Edit|Write|MultiEdit|NotebookEdit' (python json dump); result-side second gate exists
      -> hooks/repo-gate.py:986-1003 (changed SKILL.md needs a co-changed
      .skillwriter/checklist-*.md).
- [x] Change: SKILL.md 'Before you escalate a nudge to a block, price it' new bullet; authoring.md
      raw-command-string trap, after 'options like `-C`?'. Verified against ground truth: launcher
      allowlist and keywords -> hooks/shell_text.py:299-316 (_COMMAND_PREFIXES nice, ionice,
      timeout, sudo, doas, env, stdbuf, nohup, setsid, chrt, taskset, time, command, exec;
      _STATEMENT_KEYWORDS if, while, until, do, then, else, elif, {, !, (); guard_replay has
      --firings writing {id, transcript, cwd, command, error} and no two-predicate mode ->
      skills/compuse-toolbox/scripts/guard_replay.py:560-577; diffbehave exists ->
      skills/compuse-toolbox/scripts/diffbehave.py and SKILL.md:78.
- [x] Change: Traps worth knowing, new paragraph after the write-guard trap. Verified against ground
      truth: bullet/label stripping, no length cap, loud cost pinned by a test ->
      hooks/subagent-probe-capability-gate.py:63-75; apostrophe normalisation via translate ->
      :101-102 (_APOSTROPHES U+2019, U+02BC, U+FF07) and :137 `.translate(_APOSTROPHES)`; named
      exception 'other than' -> :88 _EXCEPTION.
- [x] Change: '## Reading the transcript a hook is handed' > '### Which `user` records are the
      person' (bullet list shared with row 1, plus the walk-back rule below). Verified against
      ground truth: transcript_turns.py:93-128 human_text: entrypoint sdk -> '', type attachment ->
      _queued_human_text, isMeta/isCompactSummary -> '', `if "origin" in obj` then require kind ==
      human; docstring states origin null on claude -p/SDK prompts and teammate messages, sdk
      entrypoint when no origin key, fallback to injected shapes; TAIL_BYTES 65536 widened 4x
      (transcript_turns.py:17-18); last_assistant_message rule already at io-contract.md
      (Stop/SubagentStop note).
- [x] Change: Common input fields, new paragraph directly under the table (after the
      agent_id/agent_type rows). Verified against ground truth: parent session_id/transcript_path +
      agent_id, parent CLAUDE_CODE_SESSION_ID, probed 2.1.295 -> hooks/skill-edit-guard.py:22-29 and
      transcript_siblings.py:14-18; both layouts and 'event does not name the workflow' ->
      transcript_siblings.py:39-58 agent_transcript docstring; refusal of non-plain id (_AGENT_ID
      fullmatch) and of an id matching two workflows (len(found) > 1 -> None) ->
      transcript_siblings.py:35-58; skill load record in the loading agent's own file ->
      skill-edit-guard.py:18-22.
- [x] Change: 'Testing a hook without a live session', new paragraph after the 'A hook that never
      fires...' blockquote. Verified against ground truth: deny-before-dialog on interactive 2.1.296
      and additionalContext-with-answer on 2.1.289 -> hooks/missing-mechanism-nudge.py:28-30
      (comment block). claude -p offering no AskUserQuestion is NOT pinned in the repo: kept only as
      observed behaviour with the body's CLI version 2.1.296. The rendered
      'PreToolUse:AskUserQuestion hook error: <reason>' string comes from the body's 2.1.296
      observation.
- [x] Change: '## Reading the transcript a hook is handed' > '### Same-message sibling calls'.
      Verified against ground truth: hooks/transcript_siblings.py:3-21 docstring (probed 2.1.296:
      sequential sibling Bash calls, one record per tool_use carrying message.id, all on disk before
      the second call's hook, first call sees none; subagent lookup in its own file; every failure
      answers None = allow); earlier_siblings slices uses[:position] by tool_use_id and message_id
      (:71-82); tail read 256 KiB then 4 MiB (TAIL_BYTES).
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over; the coordinator re-checked in the source: human_text, agent_transcript
      and its refusals, guard_replay --firings and its id field, diffbehave,
      subagent-probe-capability-gate.py, the case-insensitive skill-body marker.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot, opus at effort medium):
      NONE for scenario 1; partial for scenario 2; NONE for scenario 3; partial for scenario 4;
      partial for scenario 5; partial for scenario 6; partial for scenario 7; NONE for scenario 8;
      partial for scenario 9. Behavioural RED replaced on purpose: each rule is in the always-loaded
      memory index of the authoring machine (inherited coverage), so the RED is a quote-back against
      the pre-edit file.
- [x] GREEN quote-back on haiku and on opus at effort medium against the edited files; every quote
      checked present by a fragment check, each weak fragment traced to a sentence revised after
      GREEN or to a quote splicing two files.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus for every scenario; tiers haiku and
      opus, one cell per scenario per tier. The questions later fixes touched were re-run on the
      final text, on both tiers, twice (the second after the per-record and count fixes): all
      quoted, no new undecided gap.
- [x] Gaps closed or declined: closed - the skill-body marker test is stated case-insensitive (as
      the reference code lowercases), PowerShell write targets (Set-Content, Add-Content, Out-File,
      a > redirect) are named beside the Bash forms, the launcher paragraph points at the firing-set
      diff in SKILL.md, the per-record use of the four person tests is stated, and the SKILL.md
      lead-in now counts the four bullets under it (the fold added the fourth); each re-tested by
      quote-back on haiku and opus at effort medium, all quoted. Declined - a numeric tail window
      (one tool output can exceed any fixed size, so the rule is to widen until found), case rules
      for the correction words themselves (the scanner's own vocabulary), MultiEdit and NotebookEdit
      coverage and receipt format (the rule names the class, a guard decides its own tool list),
      PowerShell aliases and positional -Path (a full parser recipe is out of scope), an acceptance
      threshold for a narrowing (reading every dropped row is the bar), how a queued_command
      attachment or an origin-less transcript passes each test (the named reference implementation
      human_text settles the record shape), fail-closed vs fail-open for a policy gate (already a
      deliberate per-guard decision in the I/O contract).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, field names, repo file paths or reserved examples (/path/to/scratch).
