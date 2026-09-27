# skill-writer checklist - meta-claude-hooks (2026-09-27, model-switch events and upstream resync)

Upstream added two hook events (PreModelSwitch, PostModelSwitch) and changed behaviour across much of
the hooks reference. The skill still claimed 31 events and that only SessionStart can see the model.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The defect is factual drift, so the RED is the skill's own drift
      instrument plus a retrieval probe, not a pressure scenario.
- [x] RED from the skill's OWN instrument: `hookdoc_stamp.py check --force` returned STRUCTURAL,
      rc 1, naming added events PreModelSwitch/PostModelSwitch, their H3/H4 headings, fields
      `from_model`/`to_model`/`requested_model`/`scratchpad_dir` and the resume cost fields, and env
      vars `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`/`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`.
- [x] `coverage` checks names only, so a re-stamp cannot certify behavioural notes. Every upstream
      section whose stored hash changed (60 of them) was listed from the stamp's per-section digests
      and read against the references by four parallel read-only auditors, each finding tied to a
      quoted upstream line. Every finding applied was re-verified against the upstream text before
      editing.
- [x] Behaviour corrected where the references were WRONG: Setup discards all output and ignores exit
      code and stderr, and never runs `mcp_tool` hooks; SessionStart `mcp_tool` hooks are skipped at
      launch, not errors; WorktreeRemove fails the removal on any non-zero exit; PermissionRequest does
      not run `agent` handlers; `stopReason` reaches Claude if the conversation continues; `once`
      removes a hook only after a successful run; stdout is JSON only when it starts with `{` AND ends
      with `}`, and a failed parse is an error from v2.1.248; PostToolUse `tool_response` has no
      `success` field; TaskCompleted ignores `continue: false` for TaskUpdate; `/hooks` has no
      "Built-in Hooks" source; `CLAUDE_ENV_FILE` reaches four events, not two.
- [x] Added what a hook author gets bitten by: the Stop 8-continuation cap and its env var, the
      credential scrub, `updatedToolOutput` silently dropped when mis-shaped, `@` references skipping
      PreToolUse, `defer` only under `-p` with one tool call, `/skill` bypassing PreToolUse, silent
      ConfigChange blocks, `mcp_server.source` for trust decisions, SubagentHandback reports not in
      `last_assistant_message`, and the version floors that moved.
- [x] Script defect found by the same run: `fingerprint` harvested any JSON `"type"` value as a
      handler type, so a Write result's `"type": "create"` (and a background task's `"shell"`) were
      stamped as handler types that `coverage` then demanded be documented. TDD: new test
      `test_fingerprint_takes_handler_types_only_from_a_fence_that_configures_hooks` failed first,
      passes after restricting harvesting to fences with a `"hooks"` key or under the handler-fields
      heading; mutating the rule back re-fails it. Selftest still separates all four fixtures.
- [x] Fixtures updated to carry 33 events (sample, cosmetic, structural) and `stamp-sample.json`
      regenerated with `build_source_record`, keeping its control block; the shipped-stamp test now
      pins 33 events and both new names (failed at 31 before the re-stamp).
- [x] Retrieval probe, haiku, both arms reading only their file set. RED (pre-change events.md and
      authoring.md): "Both requirements are impossible", quoting "Hooks cannot read or set the session
      model." GREEN (new files): PreModelSwitch with exit 2 to block, PostModelSwitch to log every
      change including fallbacks, quoting the new lines.
- [x] GREEN's gaps worked: it wrote a flat, un-nested config and did not re-check `to_model`. Closed
      by a correctly nested PreModelSwitch example in `events.md` that re-checks `to_model`; the
      example's JSON parses and its command, executed, exits 2 for `claude-opus-4-6` and 0 for
      `claude-opus-5`. GREEN's other gap (no hook can steer which model a fallback picks) is true of
      upstream and is declined as out of scope.
- [x] Re-stamped with `stamp --write` against a live fetch whose content hash equals the audited copy
      (093402aa4d3b hooks.md, 02d3377f472a guide); `check --force` now CURRENT, rc 0; `coverage`
      complete (33 events, 70 required names); baseline line rewritten by `baseline --write`.
- [x] Tables reformatted with `reformat_tables.py`; ASCII only; no address, hostname or machine path
      added.
- [x] Present tense, no session narrative. Description unchanged, so no routing keyword moved.
