# checklist-20260904-queue-the-tool-do-not-fix-it

Change under test: the Pathfinder discipline gains its one exception in full - a bitranox hook,
skill, guard or the memory engine misbehaving during another project's work is recorded with
`contrib_queue.py add --what ... --target <hook|skill> --why ...` and left to the dream, which
drains the queue from the plugin's repo with the tests and the bump a fix needs; the user asking
for the fix in so many words is the exception, and the `tooling-detour-nudge` hook says the rule
once per session at the write.

## PLAN

- [x] Skill type: discipline. Test approach: the pressure scenario is shared with the
      `meta-using-bitranox-skills` checklist of the same date, which tests the short form of the
      rule that every session sees; this section is the full form it names.
- [x] Scope: one paragraph in the Pathfinder section; the same rule captured as a tree-top memory
      fact (`feedback-queue-a-misbehaving-bitranox-tool-from-a-work-session-never-fix-it-in-place`).

## RED

- [x] Text check against the pre-change section: it says "fix the adjacent rot you touch and can
      verify" and "out-of-scope fixes go in their own worktree" and names no exception, so a tool
      fix reads as sanctioned. The behavioural arm is the paired RED on haiku: three actions, all
      three fixing the plugin in a worktree, each quoting the old text.
- [x] Inherited coverage: no fact body on this machine taught the rule before the capture (7
      `contrib_queue` hits, all about a dream draining the queue).

## GREEN

- [x] Text check against the changed section: the paragraph names the four tool kinds, the full
      queue invocation with its home and launcher, the dream as the fixer, the measurement, the
      exception, and the nudge.
- [x] The paired GREEN on haiku (short form) queues and returns to the work, and its one open
      question - run the two-minute test suite first? - is answered here: "it is broken" is a
      symptom to queue, "fix it" is a request to honour.

## REFACTOR - every gap closed or declined

- [x] GAP: does the rule bind when the user asked? CLOSED - the exception is stated, with the two
      phrasings that tell a symptom from a request.
- [x] GAP: where is the fix made when it IS requested? CLOSED - "in a worktree of the plugin's
      repo", which is the existing out-of-scope rule applied to the plugin.
- [x] The Rationalizations table gains no row: the excuse the RED produced ("leave every file
      better than you found it") is answered in the paragraph itself, where the reader meets it.

## Quality

- [x] Description unchanged; measured `len()` before and after identical.
- [x] No narrative, no scratch paths, no addresses added; the measurement is stated as a result.
- [x] The script reference states its home and launcher at the point of use.

## Deployment

- [x] Hook suite green with CI's dependency set; `repo-gate.py --ci` before the push.
- [x] Version bumped in `plugin.json` and `pyproject.toml`; CHANGELOG entry carries the numbers.
