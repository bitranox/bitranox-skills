# checklist-20260904-tooling-decisions-go-to-the-queue

Change under test: the review excludes decisions about the TOOLING (a bitranox hook, skill, guard
or the memory engine) from the walk and routes each to `contrib_queue.py add`; and the Stop hook
behind it now fires on a `/goal` or an opened PR only, never on a commit or a push.

The measurement behind both: over 21 days of transcripts, sessions outside the marketplace repo
spent 778 minutes in instrumentation episodes that began with this hook's block - the largest
single trigger, rising from 1% to 39% of weekly instrumentation minutes - and the episodes were
36% skills-repo edits, 32% memory-store work and 188 minutes of `AskUserQuestion` walks about
tooling; on one day they ended in 29 plugin releases pushed from four unrelated projects.

## PLAN

- [x] Skill type: discipline. The failure is a rule not followed - a tooling anecdote walked as a
      project decision - so the test approach is a pressure scenario, not retrieval.
- [x] Scope: `SKILL.md` plus the hook `decision-review-nudge.py` and a new `shell_text.opens_a_pr`
      predicate, each with its own RED test.

## RED

- [x] Scenario: a session in a Proxmox repo opens a PR, the Stop hook asks for the review; two
      unsettled things are in play - a per-host vs shared nftables table, and a memory-tool
      refusal the agent retyped around and suspects is a length-counting bug.
- [x] Inherited-coverage checked with `redcheck.py --corpus-cascade` on a work project: verdict
      INHERITED COVERAGE, adjudicated a false positive - the shared terms are function words
      (`along`, `chose`, `printed`, `request`, `settled`) and neither named fact body mentions a
      queue, a handover or tooling decisions. The queue-instead-of-walk rule is taught nowhere on
      this machine, so the arm can fail honestly.
- [x] RED on sonnet FAILS as predicted: the memory-tool refusal is item 2 of the list ("retyped
      rather than understood ... reproduce the refusal and read what actually triggered it"), and
      its own gaps section reports "The skill is silent on whether a tooling/environment anecdote
      (the memory-tool refusal) counts as one of the decisions you made ... I had to guess this
      still counts".
- [x] Hook RED: `test_a_commit_alone_does_not_conclude_the_work`,
      `test_a_push_alone_does_not_conclude_the_work`, `test_commits_and_pushes_never_raise_the_score`,
      `test_the_block_reason_sends_tooling_decisions_to_the_queue` and
      `test_a_session_that_only_committed_and_pushed_is_never_asked` - 5 failed, 47 passed against
      the pre-change hook; `test_opens_a_pr` 12 failed on the missing predicate.

## GREEN

- [x] Re-run on haiku, the least inferential tier, against the rewritten text, same scenario: the
      list holds the nftables decision only, the memory-tool issue is named in one sentence as
      queued, and the governing line is quoted verbatim ("a memory-engine call that refused you -
      none of that is this project's work").
- [x] Hook GREEN: 324 passed across `test_decision_review_nudge.py`, `test_shell_text.py` and
      `test_repo_gate.py`; `is_gated_command` unchanged, so the repo gate still blocks on a commit.
- [x] Both arms asked for a `Skill gaps` section; both lists recorded and worked below.

## REFACTOR - every gap closed or declined

- [x] GAP (RED sonnet): silent on tooling anecdotes. CLOSED - the new paragraph names four shapes
      (a hook that fired oddly, a doubted skill text, a guard worked around, a refusing engine
      call), the queue command with its home and launcher, and the one-sentence mention.
- [x] GAP (GREEN haiku): "does not show the exact contrib_queue command invocation". DECLINED -
      the paragraph carries `contrib_queue.py add --what ... --target <hook|skill> --why ...` with
      its home; the probe had no Bash to run it, which is a property of the probe, not the text.
- [x] GAP (both arms): no criterion for which option to mark recommended, and no rule for a point
      with exactly one alternative. DECLINED - pre-existing, owned by the walk section, and a
      judgement the skill leaves to the reviewer by design.
- [x] GREEN diffed against RED in both directions: GREEN lost the memory-tool item from the walk,
      which is the intended change, and kept every other RED result (the count-and-exit line, the
      hardest-to-reverse ordering, upside and downside per option).
- [x] Quote-back: "which line says a tooling decision is not walked?" answered from the text with
      a verbatim quote on haiku.

## Quality

- [x] Description unchanged in meaning; measured `len()` 364, under the 1024 cap and the 500 target.
- [x] No narrative, no scratch paths, no addresses added; the measurement is stated as a result.
- [x] `wc -w` 1366 - a discipline skill above the 500 target, as before this change; the addition
      is one paragraph and one sentence.
- [x] Cross-references by skill name; the script reference states its home and launcher.

## Deployment

- [x] Hook tests green with CI's dependency set; `repo-gate.py --ci` before the push.
- [x] Version bumped in `plugin.json` and `pyproject.toml`; CHANGELOG entry carries the numbers.
