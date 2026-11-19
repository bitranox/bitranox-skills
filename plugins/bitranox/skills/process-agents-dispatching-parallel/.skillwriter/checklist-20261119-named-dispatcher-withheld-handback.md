# checklist - a named dispatcher's withheld hand-backs

The "Waited-for probes" bullet now says that waiting does not save an agent dispatched with
`name`: every hand-back of its own dispatches is refused while it waits. It names where the
report still is (the `message` input of the probe's last `SubagentHandback` call in
`<session>/subagents/agent-<agentId>.jsonl`), says the new `withheld-report-nudge` hook quotes it
beside the Agent result, and says not to re-dispatch or SendMessage for it.

Decisions: d-20261119-50e91fcc, d-20261119-ebd21207

## RED

- [x] Skill decisions read first: no rejected or removed entries; the live rule
      d-20261116-76d1bd25 (nested-dispatch-wait) keeps its anchor and still holds for its own case.
- [x] Measurement first (the queue entry asked for a replay before any nudge): SubagentHandback
      results across the transcript corpus, split by the dispatcher in each agent's meta file.
      First hand-back refused for 116 of 116 agents dispatched by a named agent (all foreground),
      0 of 4,319 dispatched by the main session or an unnamed subagent. The proposed PreToolUse
      nudge (probe or meta-skill-writer brief with no wait line) would fire on 341 of 5,032 Agent
      dispatches and prevents none of the measured failures: the dispatchers were waiting.
- [x] Text probe on the pre-edit bullet (opus and haiku), scenario: a named agent waited for a
      foreground probe, the result says the report was withheld, a SendMessage failed again.
      Q1 (why, given the wait) NONE on both; Q3 (re-dispatch?) NONE on both; Q2 was pieced
      together from the harvest section and mixed up `tasks/` and `subagents/`.

## GREEN

- [x] Hook: 16 tests in test_withheld_report_nudge.py; a 6-arm mutation battery all KILLED with a
      green baseline before and after (two survivors of the first battery closed: a test for the
      `handback` field alone, and a redundant tail-fragment skip removed).
- [x] Hook run on a real withheld result from this session's own transcript: it quoted the
      probe's last SubagentHandback message (3,261 characters of context) and exited 0, also when
      launched through run-python.sh --hook.
- [x] Text probe on the edited bullet (opus and haiku): all three questions answered with quotes
      of the new lines ("Waiting does not save an agent dispatched with `name`", "Read it there;
      do not re-dispatch the probe for it.").

## REFACTOR

- [x] Closed (opus, haiku): no quote beside the result - the text now says to read the file
      yourself when the plugin predates the hook.
- [x] Closed (opus, haiku): whose `<session>` - the main session's transcript path without
      `.jsonl`, also for a probe a subagent dispatched (checked: this session's probes sit under
      the main session's `subagents/`), named probe or not.
- [x] Re-probe of the final text (haiku): path, report field and the no-quote case all quoted.
- [x] Declined (opus): replacement brief wording for a named dispatcher - none exists; the remedy
      is reading the transcript, which the hook automates.
- [x] Declined (opus, haiku): version scope and retries - the figures carry their build; the
      hook takes the last message, the agent's final word.
- [x] Declined (haiku): the JSONL record format - the harvest section below already says how to
      read a tool_use input.
- [x] Declined: a description change - it would route readers to a rule that does not prevent
      the failure (recorded as a rejected decision).
