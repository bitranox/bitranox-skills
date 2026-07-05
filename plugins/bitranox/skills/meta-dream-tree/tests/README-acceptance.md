# Dream acceptance test (planted fixture)

Proves a real dream run works, end to end, against a deterministic fixture. Run it after any
substantive change to meta-dream-tree.

1. Build the fixture in a scratch dir (OUTSIDE any real tree):

       python3 fixture_builder.py /tmp/dream-acceptance

2. Run a REAL dream in the fixture: launch a fresh session (or dispatch a subagent) with cwd
   /tmp/dream-acceptance/tree1/dept-a/proj-1, dream mode auto (touch ~/.claude/.bitranox-dream-auto
   in the fixture HOME if isolating HOME), strict engine env, and the instruction "run
   bitranox:meta-dream-tree". The model must discover everything else itself.

3. Assert:

       python3 fixture_asserter.py /tmp/dream-acceptance

   HARD assertions (all must pass, every run): XTREE (control tree byte-identical), PIN (pinned
   entry untouched), VOICE-ID (reword kept the slug), RECONCILE (0 problems), NO-LOSS.
   JUDGMENT assertions: DUP, MIS-HIGH, MIS-LOW, OBS, TASK, SCOPE.

The BAR: all hard + >= 5/6 judgment on TWO CONSECUTIVE runs. On a RED, read the run's transcript
for the rationalization, close that loophole in SKILL.md, and re-run - budget 3-4 REFACTOR
iterations. The harness itself is unit-tested (test_fixture_harness.py); a harness change needs
its tests green first.
