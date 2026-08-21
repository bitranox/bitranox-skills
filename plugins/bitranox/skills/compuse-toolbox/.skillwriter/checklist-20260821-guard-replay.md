# skill-writer checklist - compuse-toolbox (`guard_replay`)

Change: a new jig, `guard_replay`, which replays every Bash command in a Claude Code transcript
corpus through a guard's own predicate function - with the cwd each command ran under - and reports
the firing RATE and the PRECISION separately. New script, new tests, one table row, one rationale
bullet.

## PLAN
- [x] Skill type: reference (a tool index with a per-tool rationale).
- [x] Trigger is measured, not hypothetical: the instrument was hand-rolled four times for one job,
      then three more times in the session that built this. It is what found three defects in one
      shipped hook, and it did not survive either session.
- [x] Checked the capability is not already shipped, in the tool AND its neighbours: `transcript_tail`
      mines ONE transcript and returns turns or tool calls, never a corpus; `jsonl_grep --count`
      tallies a dotted FIELD across a corpus but cannot run a predicate; `diffbehave` compares two
      programs on a prepared case file, which is a different shape; `claim_check` answers
      present/absent for a text pattern, not a program's verdict. No jig runs code over a corpus.
- [x] Scope: one script with six public functions, 20 tests, one table row, one rationale bullet,
      CHANGELOG, version bump.

## RED
- [x] Tests written first and run against a stub exposing only the names: 18 FAILED on
      `NotImplementedError`, which is the feature missing rather than a typo. The first run failed at
      COLLECTION (`ModuleNotFoundError`), which proves nothing about behaviour, so the stub was added
      to convert it into a behavioural RED before any implementation was written.
- [x] A second RED after the first GREEN: comparing the jig against the hand-rolled script it
      replaces showed a 54-command disagreement. `test_the_same_call_in_two_transcripts_counts_once`
      was written for it and failed `assert 3 == 2`. Cause: resuming a session copies the earlier
      transcript into a new file, so one real call sits in two files under one tool_use id, and
      counting it twice inflates the denominator silently.
      `test_calls_with_no_id_are_not_collapsed_into_one` passed throughout and pins the over-fix.
- [x] Retrieval RED on the table row, since the tests cover the script and not the doc. An inert
      probe (no filesystem tools), whole index visible, NONE stated as acceptable, asked in a user's
      words. It answered NONE and rejected each near row with a reason - of `diffbehave`: "Forcing
      this in means inventing a fake OLD (e.g. a no-op that never warns) just to get diff output,
      which is exactly the kind of stretch to avoid" - then described hand-rolling this tool.
- [x] Contamination checked before dispatch: `redcheck --corpus-cascade` read 699 documents and
      came back clean. Recorded as WEAK evidence per its own report, and the residual risk runs the
      SAFE way: the general rule "measure a guard on the real corpus" IS in the always-loaded
      memory index in other words, and inheriting it would push a probe TOWARD naming a tool. It
      answered NONE, so inheritance cannot explain the RED.

## GREEN
- [x] Same probe type, same model, same question, only the index changed. It named `guard_replay`,
      gave the invocation, reached for `--sample`, and flagged the exit codes unprompted: "1 means
      the guard never fired at all over the whole corpus ... 3 means the corpus couldn't be read -
      don't mistake either for 0% chatty, ship it."
- [x] Behaviour verified against ground truth, not only against tests: replayed both shipped guards
      and reproduced the hand-rolled measurement exactly at the same moment - 567 fires, 22
      gate-blocked, 3.88% precision from both instruments - and reproduced the second guard's
      documented 0.186% firing rate.
- [x] Both dispatches asked for a `Skill gaps` section.

## REFACTOR
- [x] GREEN reported four gaps; three were real silences in the row and are CLOSED in it: the corpus
      shape (Claude Code transcript JSONL, explicitly NOT shell history, which carries neither a cwd
      nor any record of what a gate did), the predicate contract (`f(command)` or `f(command, cwd)`,
      truthy fires), and the `--root` default. The fourth - that the path and function name in the
      example are placeholders - is DECLINED: they are the caller's own values.
- [x] GREEN diffed against RED in both directions. Nothing the RED produced is missing from GREEN:
      the RED's value was its per-row rejection analysis and a description of the tool to build, both
      superseded by a match. GREEN additionally surfaced the exit-code trap.
- [x] A limitation found by running the tool on two guards rather than one, and written into both
      the docstring and the rationale bullet: the precision figure asks "did a GATE refuse this
      call", which is the right question for a guard about commands that cannot succeed as written
      and the wrong one for a guard whose hazard is a plausible-but-wrong result. The second guard
      scores 0% while being useful, so a 0% is a prompt to look, not a verdict.

## Quality
- [x] Tests cover every public function, including the error paths: 20 tests, and the CLI's exit
      codes 0/1/2/3 exercised by hand as well.
- [x] The script imports in a BARE environment: verified in a fresh venv holding only pytest, with
      `orjson` confirmed absent, 20 passed. The stdlib fallback is what makes that work.
- [x] Machine values: `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/'` over the row and
      the script returns nothing. The corpus path in the row is `~/.claude/projects`, which is the
      reader's own.
- [x] No session narrative or private provenance in the row, the bullet or this artifact.
- [x] Reference/hub skill, so the body may exceed 500 words; detail stays in `--help` and the
      docstring rather than the row.

## Declined, with the reason
- [x] DECLINED (reported, not fixed): the skill's `description` is 2124 characters
      against a 1024 cap, and the injected skill listing truncates it - 597 characters never reach
      the router, taking the triggers for `wtclean` and `claudemd_variance` with them. So this jig's
      trigger was NOT added to the description: appending would land in the dead tail, and inserting
      it early would push another tool out. The field needs a rewrite, which is its own change.
