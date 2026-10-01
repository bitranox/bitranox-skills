# skill-writer checklist - meta-claude-hooks (2026-10-01, upstream refresh)

`hookdoc_stamp.py check` reported STRUCTURAL: hooks.md added "How the tool's result is read", "When the
server is still connecting", "Events that fire before MCP servers are available" and "What a blocked
prompt leaves behind", the `suppressOriginalPrompt` field, and dropped a `SessionStart` JSON-example key
and a `Bash(cat *)` table key. The pre-launch `mcp_tool` skip was already documented. Two statements
were now false: a blocked `UserPromptSubmit` prompt "erases the prompt" (events.md, io-contract.md
exit-2 table), and an `mcp_tool` server "must already be connected" (configuration.md handler table and
field table). Both are rewritten from the upstream text; SKILL.md changes only its baseline line
(`baseline --write`).

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Retrieval scenario, three questions: Q1 after an exit-2 block with no
      JSON, can the prompt text still be found (block message, transcript); Q2 the exact JSON that
      keeps it out of the block message, where the field sits, and whether exit 2 honours it; Q3
      whether a `PreToolUse` `mcp_tool` hook waits for a connecting server, and whether
      `Notification` differs.
- [x] Arms pinned to haiku on the inert `bitranox:baseline-probe` type, the excerpt pasted, answers
      quoted or NONE, each ending with a "Skill gaps" section.
- [x] RED (pre-change text): Q1 "yes" for the block message by inference from the field, silent on
      the transcript; Q2 placed `suppressOriginalPrompt` at the TOP LEVEL beside `decision` (wrong),
      exit 2 unknown; Q3 "non-blocking error", wait behaviour unknown, Notification NONE.
- [x] GREEN (new text): Q1 quoted both the block-message and the transcript sentence; Q2 printed
      `hookSpecificOutput: {hookEventName, suppressOriginalPrompt: true}` and quoted that exit 2
      works; Q3 quoted the wait for `PreToolUse` and "no wait" for `Notification`.
- [x] GREEN gaps: (1) what happens when `MCP_TIMEOUT` runs out, (3) whether "no wait" still errors -
      CLOSED by one sentence: "If the server is not connected when the tool is called - the wait ran
      out, or the event never waited - the hook is a non-blocking error: the action proceeds and the
      transcript shows a hook error". (2) how a non-blocking error manifests - DECLINED here, defined
      in io-contract.md ("the action proceeds and the transcript shows `<hook name> hook error`").
- [x] Quote-back on the closed gap: timeout-expiry question answered "the action proceeds and the
      transcript shows a hook error"; Notification answered "On observational events (`Notification`,
      `SessionEnd`) there is no wait."
- [x] GREEN against RED in both directions: every RED answer is still answered; Q2 changes from a
      wrong placement to the right one; nothing RED found is missing.
- [x] `hookdoc_stamp.py stamp` (coverage gate) passed before `stamp --write`; `check` afterwards reads
      CURRENT for both sources.
- [x] No other file still says "already-connected" or "erases the prompt" (grep over the skill and
      docs/).
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
