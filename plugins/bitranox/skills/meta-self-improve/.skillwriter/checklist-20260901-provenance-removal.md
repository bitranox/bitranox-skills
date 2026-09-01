# skill-writer checklist - meta-self-improve (the add invocation no longer takes --source)

Change: step 4's engine invocation and step 3's upsert sentence. Provenance was removed from the
memory store, and with it the `--source` flag on `add` and `amend-pinned`. The documented
command now names a flag the engine rejects, so the text is corrected to match. No behaviour is
added; a removed option is removed from the procedure that told readers to pass it.

## PLAN

- [x] Skill type: technique (a procedure whose body carries an executable command).
- [x] Test approach: application scenario. The defect is executable, so an agent following the old
      text produces a command that fails, and that is the test.
- [x] Scope: the invocation block in step 4 plus one clause in step 3. The sibling sentences in
      three other skills get their own checklists.

## RED

- [x] A subagent given the PRE-CHANGE invocation block, and a fact to capture carrying a session
      label, wrote the flag: `--source session-gate-2026-09-01`. Its stated reason: "I used
      `--source ...` because the given session label matches the `--source <key>` pattern".
- [x] That command is not merely stylistically wrong, it fails. Run against the shipped engine:
      `memory_engine.py: error: unrecognized arguments: --source session-gate-2026-09-01`, exit 2.
      Nothing is written.
- [x] The arm ran on a tool-less probe agent, so the command came from the supplied text rather
      than from exploring the filesystem.

## GREEN

- [x] A subagent given the POST-CHANGE block wrote the same capture with no `--source`, ending at
      `--body-file`. The equivalent command against the shipped engine prints the slug and exits 0.
- [x] The correction is a REMOVAL from a bracketed-optional list, so no trigger keyword moved and
      the router is unaffected.

## REFACTOR - gaps from the GREEN dispatch

- [x] Both dispatches were asked for a `Skill gaps` section and both returned one.
- [x] `<plugin>` cannot be resolved from context alone. DECLINED: pre-existing, and the placeholder
      is the convention across this skill family; the GREEN arm resolved it to `$CLAUDE_PLUGIN_ROOT`
      unaided, which is the intended answer.
- [x] `--slug` guidance absent from the invocation block. DECLINED: step 3 already states when to
      pass a stored slug; the template marks it optional and the arm treated it correctly.
- [x] Two further gaps were artifacts of the test scenario, not the skill (a placeholder project
      path and a body-file location supplied by the prompt). DECLINED, no skill text implicated.
- [x] GREEN diffed against RED in BOTH directions. Nothing the baseline produced is missing from
      GREEN; GREEN additionally identified a near-duplicate stored fact and said so before acting,
      which is the dedup step working rather than a regression.
- [x] Undecided gap list is empty.

## Quality

- [x] Present tense, no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added by this change.
- [x] Frontmatter untouched: no `name` or `description` change, so no routing keyword moved.

