# skill-writer checklist - meta-self-improve (2026-07-17, route capture by SUBJECT, not blindly by cwd)

Change: capture was hard-wired to `--proj "<cwd>"` ("never another tree"), so a learning about repo B
discovered while working in repo A landed in A - misplaced from birth, and CROSS-TREE unrecoverable
(`move_entry` refuses cross-tree moves, so no dream can ever re-home it; only a duplicating copy
exists). Step 3b now routes `--proj` by the fact's SUBJECT using the ROUTING EVIDENCE the Stop gate
carries (the levels the turn actually edited, from the new `touched-paths` PostToolUse recorder), with
cwd as the default when the learning is about the cwd's own workflow. The contradicting deliverable
("never another tree") and the contradicting common-mistake line were corrected in the same change.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the user reported the exact symptom ("when we work from a certain directory on a project in
      ANOTHER directory, the learnings seem to go into the wrong directory"), and a 4-agent code
      investigation confirmed it: capture is a pure function of cwd (SKILL.md:88-90 + engine
      `add_or_update_entry(proj)`), nothing inspects the subject, and `memory_engine.py:319-322`
      hard-refuses the cross-tree move that would fix it
- [x] GREEN (deterministic evidence, not prose alone): new `touched-paths.py` PostToolUse recorder +
      `self_improve_signals.subject_levels()` compute the OTHER levels a turn edited; the Stop gate
      appends them to its block reason naming the level and flagging the cross-tree (unrecoverable)
      case and telling it to pass `--proj <level>`. Unit-tested end to end
      (test_touched_paths.py, test_self_improve_signals.py::subject_levels,
      test_self_improve_gate.py::block_reason_names_other_repos_the_turn_edited)
- [x] Hybrid by user decision: the evidence is deterministic, the ROUTE stays model-judged (a learning
      can legitimately be about the cwd workflow even when another repo was edited) - the skill says so
      explicitly rather than mechanically overriding cwd
- [x] Probe-first (iron rule): the mechanism rests on PostToolUse carrying `tool_input.file_path` and a
      stable `session_id` - PROVED on the live harness by `.plan/probes/probe_hook_events.py` before
      any of it was built (the same probe corrected the SubagentStop transcript key for P1)
- [x] Contradictions swept in the same change: the deliverables checklist and the common-mistakes list
      both still said "never another tree" - both corrected, so the skill has one consistent rule
- [x] Scripts/tests: every new/changed .py has sibling tests; `touched-paths` registered in
      hooks/tests/conftest.py `_HOOK_MODULES`; run with the CI dep set
- [x] CSO description: unchanged (procedure edit only, no trigger change)
- [x] Security scan: paths only, no secrets/PII; the recorder writes a capped, session-keyed scratch
      file under ~/.claude and fails open (exit 0) so it can never wedge a turn
- [x] Docs describe current state: no legacy narrative
