# Review checklist 2026-11-08: score reports subagent overlap, idea markers and the suite outcome (meta-skill-ab-test)

Change: a new script `scripts/abtrace.py` reads three things from an arm dir, and `score` adds
them to every arm (`subagents`, `idea_markers`, `floor_suite` in scores.json and the JSON
envelope; `subagents=`, `ideas=`, `suite=` on the text line, with the first marker line of each
idea printed below the arm). SKILL.md gains one paragraph after the run-dir paragraph that says
what each field means and when it shows `-`. Existing score keys (`floor_error`, `floor_steps`
and the rest) are unchanged. The description is untouched.

## Claims and their evidence

- [x] Description measured: `len()` of the YAML `description` is 481 (unchanged, under 1024); the
      frontmatter loads with `yaml.safe_load` and holds exactly `name` and `description`; SKILL.md,
      `abtrace.py`, its tests and both fixtures are ASCII only (non-ASCII byte count 0 each).
- [x] RED, before the code: the new score-level tests failed on the old source with
      `KeyError: 'subagents'`, `KeyError: 'floor_suite'`, a key-set mismatch and a text line
      lacking `subagents=`; `mutation_arm.py --revert scripts/abscore.py HEAD --revert
      scripts/abtest.py HEAD` on `tests/test_abscore.py` reports KILLED.
- [x] RED, text: an opus `baseline-probe` given the pre-edit paragraph answered NONE to all five
      questions (the difference between `ideas=-` and `ideas=none`, where the markers are, how
      `max N at once` is measured, the three `suite=` values, whether a marker quoted in a prompt
      counts) and listed "Output fields undefined" and "Marker source unknown" as gaps.
- [x] "`subagents=` ... the most whose first-to-last timestamp spans overlap": executed.
      `test_overlap_counts_agent_files_and_the_most_running_at_once` (3 agents, 2 at once, the main
      transcript and `.meta.json` not counted), `test_background_agents_launched_together_all_count_as_running_at_once`
      (4 at once), `test_an_agent_starting_when_another_ends_does_not_overlap_it` (a hand-over is 1).
- [x] "`ideas=` ... read from the writing tool calls in `stream.jsonl` and in the subagent
      transcripts ... a marker only quoted in a prompt, a brief or a read-back does not count":
      executed. `test_markers_written_by_bash_write_and_edit_are_collected`,
      `test_markers_in_prompts_reads_and_echoed_text_do_not_count` (user prompt, assistant prose,
      an Agent brief, a `grep` with `2>/dev/null`, a Read and its tool_result: 0 writes),
      `test_a_marker_a_subagent_wrote_is_read_from_its_transcript_once` (a call in both the stream
      and a subagent transcript counts once).
- [x] "`suite=` splits a failing acceptance suite ... `failed` ... `did_not_finish`": executed on
      two cargo fixtures that both exit 101: `does_not_compile` with
      `{"E0308": 1, "E0425": 1, "E0432": 2}` and missing `sbx::policy::Policy`, `run_sandboxed`,
      `sbx::mount::Bind`; `tests_failed` with 2 of 10. `test_the_suite_log_run_floor_writes_is_the_one_the_score_reads`
      runs the real `run_floor` and scores its log.
- [x] Mutation battery (`compuse-toolbox` `mutation_arm.py --battery`, baseline green first and
      last): KILLED peak capped at one, start sorted before end at the same instant, a non-writing
      Bash counted, a repeated tool_use not deduplicated, subagent transcripts not read, compile
      not split from run time, total counted as failed only. SURVIVED, equivalent: reading the main
      session transcript as well, which repeats the stream and is absorbed by the tool_use id dedup.
- [x] GREEN (opus x1, haiku x1, the same five questions with the new paragraph): both quoted the
      paragraph for Q2 to Q5 (markers come from the stream, not the branch; overlap from transcript
      timestamps; the three suite values; a prompt quote does not count).
- [x] Gaps from GREEN, decided:
  - CLOSED: which absent source gives `-` for which field (opus, haiku) - "Each field shows `-`
    when its own source is absent: `subagents=` when the arm has no `transcripts/` dir, `ideas=`
    when it has neither `stream.jsonl` nor a subagent transcript, `suite=` when the floor ran no
    suite step."
  - CLOSED in code and text: a marker a background subagent wrote may not reach the stream (opus) -
    the reader now also reads `agent-*.jsonl` under `transcripts/`, deduplicated by tool_use id.
  - CLOSED: the notation `1x2`, `E0432x2`, `2 of 10` (opus, haiku) - "`ideas=1x2,3x1` reads idea
    1 with 2 distinct marker lines", "`does_not_compile(<code>x<count>,...; missing <symbols>)`",
    "`tests_failed(<failed> of <total>)`".
  - CLOSED: "the first line of each" (opus) - "the first line of each idea".
  - CLOSED: other ways of writing (opus) - "a write by any other route (`sed -i`, a script) is not
    seen".
  - CLOSED: whether `max 1` means no overlap (haiku) - "`max 1` means no two spans overlapped".
  - CLOSED after the re-probe (haiku, final text, five questions: `-` vs `none`, a subagent's
    `echo >>` marker, a `sed -i` marker, the notation, `max 1`): every answer quoted the
    paragraph. Its remaining silences were closed in the text: MultiEdit and NotebookEdit named
    ("Write, Edit, MultiEdit, NotebookEdit, a Bash redirect or `tee`"), "a call found in both
    counted once", and "`<code>x<error lines>`".
  - Quote-back on those three fixes (haiku): each answer was a direct quote of the new wording.
    Its leftover silences are declined as implementation detail a reader does not act on: how a
    call in both sources is matched (the tool_use id, stated in `abtrace.idea_markers`'s
    docstring) and a MultiEdit (one `file_path` per call).
  - DECLINED, scenario artifact: the re-probe called `ideas=-` beside `subagents=4` a
    contradiction; that combination cannot occur (`idea_markers` reads the same transcripts), and
    the probe read the rule correctly.
  - DECLINED, judgement: what markers on the control arm mean, how a reader weighs `-` against
    `none`, and a subagent launched but not yet
    writing records being invisible to the span (a transcript has no record before its first one;
    the field informs and never voids).
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion point ("Do not judge a variant from transcripts") holds no back-reference that now
      binds to the new text. The version-history finder over SKILL.md found nothing.
- [x] Decisions: none - the paragraph documents behaviour this change's code and tests carry; the
      field names and their split were set by the task, not chosen in the text.
