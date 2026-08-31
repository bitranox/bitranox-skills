# skill-writer checklist - process-agents-dispatching-parallel (2026-08-31)

Change: a subsection under "Review and Integrate" - structured output must be harvested from the
agent's transcript JSONL, not from the delivered message.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. The skill covered dispatching, prompt structure
      and verifying agents' claims, and said nothing about getting their output back intact; a grep
      for `transcript`, `escape` or `subagents/` returned nothing.
- [x] MEASURED while harvesting 38 restructured bodies from four agents: the agent-to-parent channel
      HTML-escapes `<`, `>` and `&`, so a dependency floor written as `>=3.11` arrives as
      `&gt;=3.11` and a control tag arrives neutralized.
- [x] The reason it needs saying is stated: the corruption survives every structural check. The
      delimiters still match and the block count is still right, so only the characters a version
      comparison or a shell cares about are wrong - nothing fails, and the corrupted text is
      written straight into whatever the parent produces.
- [x] Both practical traps recorded: a NAMED agent's transcript is not symlinked into the session's
      `tasks/` directory (only an unnamed one is) and lives under `subagents/`; and not every
      record's `message` is a dict, so an unguarded walk dies AFTER writing some blocks, which
      looks like truncation rather than failure.
- [x] Scoped so it does not overreach: prose you only read is fine to take from the delivered
      message. The rule is about text you PARSE.
- [x] Scope: shared - harness mechanics, nothing project-specific.
- [x] Security scan: prose only; no paths beyond the harness's own relative directory names.
- [x] CSO description: unchanged; this sits under existing dispatch/review triggers.
