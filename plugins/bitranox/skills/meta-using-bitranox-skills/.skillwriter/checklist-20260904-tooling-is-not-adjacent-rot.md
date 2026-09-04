# checklist-20260904-tooling-is-not-adjacent-rot

Change under test: the pathfinder paragraph gains one carve-out - a misbehaving bitranox hook,
skill or memory-engine call met while working on another project is queued in one line
(`contrib_queue.py add`) and left to the dream, unless the user asks for the fix in so many words.

The measurement behind it: over 21 days of transcripts, sessions outside the plugin repo spent
2,096 minutes fixing the plugin source in place - 93 episodes of three or more edit, commit or
test calls into it, a third of all instrumentation time in work sessions, growing from 4% to 11%
of work-session minutes across the four weeks - and 12% of ALL Edit calls made from work-project
sessions landed in the plugin source.

## PLAN

- [x] Skill type: discipline (this paragraph is the always-injected standing instruction). Test
      approach: a pressure scenario with the sunk cost of a two-hour task, a "go on" from the user,
      and the plugin repo one path away.
- [x] Scope: one sentence in this SKILL.md, the full rule in `meta-self-improve`'s Pathfinder
      section, the same rule as a tree-top memory fact, and the `tooling-detour-nudge` hook that
      says it once per session at the write.

## RED

- [x] Scenario: a data-pipeline session, two hours in, fixing a CSV reader; the notes helper the
      plugin ships refuses a note with a length message the agent believes wrong; the plugin repo's
      path is known and its tests take two minutes. First three actions, with the governing
      sentence for each.
- [x] Inherited coverage: the queue-instead-of-fix rule is taught nowhere on this machine before
      this change (checked by grepping every fact body for `contrib_queue`: 7 hits, all about
      draining the queue in a dream, none about a work session queueing a tool symptom).
- [x] RED on haiku FAILS as predicted, on the OLD paragraph: action 1 "run the helper script
      plugin's test suite", action 2 "create a git worktree in the helper plugin repo, diagnose
      the length-limit enforcement code, and apply the fix", action 3 "re-run the test suite in
      the worktree ... resume the CSV reader task with the helper plugin now corrected" - each
      quoting a sentence of the paragraph as its authority ("put an out-of-scope fix in its own
      worktree", "leave every file better than you found it").

## GREEN

- [x] Re-run on haiku against the new paragraph, same scenario: action 1 reads the helper's
      source to name the symptom precisely, action 2 queues it with `contrib_queue.py add`,
      quoting the new sentence verbatim, action 3 "Return to the CSV reader fix". Its gaps list
      states the assumption the rule needs: "the user's 'go on' does not count as asking me to
      fix the notes helper - only explicit requests ... override the queue-and-defer instruction".
- [x] Both arms asked for a `Skill gaps` section; both lists recorded and worked below.

## REFACTOR - every gap closed or declined

- [x] GAP (RED): the paragraph licenses the fix. CLOSED - the carve-out names the tool kinds, the
      queue command with its home, the dream as the fixer, and the one exception.
- [x] GAP (GREEN): the exact `contrib_queue.py add` arguments. DECLINED here - this paragraph is
      the always-injected standing text and stays short; the full invocation with `--what`,
      `--target` and `--why` is in `meta-self-improve`'s Pathfinder section, which this paragraph
      names as the full discipline, and in the nudge text at the moment of the write.
- [x] GAP (GREEN): "point mistakes out clearly" in tension with "queue and keep working".
      DECLINED - the arm resolved it the intended way (a precise one-line symptom IS pointing it
      out clearly); the Pathfinder section says "record the symptom in one line".
- [x] GAP (GREEN): whether to run the plugin's two-minute test suite before queueing. CLOSED in
      `meta-self-improve`: "'it is broken' is a symptom to queue" - the queue takes a symptom,
      not a diagnosis.
- [x] GREEN diffed against RED in both directions: GREEN lost the worktree-fix-resume sequence,
      which is the intended change, and kept the precise identification of the failure.
- [x] Quote-back: "which sentence says the tool is not yours to fix here?" answered on haiku with
      the new sentence verbatim.

## Quality

- [x] Description unchanged; the paragraph grows by two sentences.
- [x] No narrative, no scratch paths, no addresses added; the measurement is stated as a result.
- [x] Cross-references by skill name; the script reference states its home.

## Deployment

- [x] Hook suite green with CI's dependency set; `repo-gate.py --ci` before the push.
- [x] Version bumped in `plugin.json` and `pyproject.toml`; CHANGELOG entry carries the numbers.
