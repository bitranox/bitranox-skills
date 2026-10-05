# checklist-20261005-brief-constraints-and-red-mutation

Changes under test:

1. `SKILL.md`, File Handoffs, task brief: the brief opens with the plan's `Global Constraints`
   section verbatim (a constraint naming the tasks it binds lives there, so without it a task's
   Files list reads complete and is wrong); constraints filed under another heading are not
   carried and the controller reconciles them; exit 1 = no such task, exit 2 with `line N:`
   headings = a duplicated id, which goes to the human like any plan contradiction.
2. `implementer-prompt.md`: a new section on proving RED by mutating code - through
   compuse-toolbox's mutation_arm or a `mktemp -d` copy made in this run, never a `.orig` the
   agent did not make (sequential subagents share one scratchpad), and `git diff --quiet HEAD --
   <file>` after the restore.
3. `task-reviewer-prompt.md`: the read-only rule names a RED-proof mutation as a mutation; the
   reviewer names it in the report, or runs it only through mutation_arm and confirms
   `git diff --quiet HEAD` afterwards.

The script change behind (1) - `task_brief.py` carrying the section, refusing a duplicated id,
exit codes 0/1/2 - ships with its own tests in `tests/test_task_brief.py`.

## PLAN

- [x] Skill type: technique (controller and subagent procedure).
- [x] Scope: `SKILL.md` plus the two dispatch templates.

## RED

- [x] Inherited-coverage check: `redcheck.py --corpus-cascade` on the repo answered INHERITED
      COVERAGE for both lessons (memory facts on this machine record them). Route taken: a TEXT
      CHECK of the artifact, with a behavioural arm for gaps.
- [x] Text-check RED: the pre-change `SKILL.md` never connects the brief to `Global Constraints`
      (`grep -n -i "Global Constraints" | grep -i brief` returns nothing), and no file of the skill
      mentions `mutation_arm`, `mktemp` or `diff --quiet`.

## GREEN

- [x] Text-check GREEN: each rule is present once in its file.
- [x] Behavioural arm on haiku with the three excerpts pasted, four scenarios, each answered with
      a direct quote of the new text: constraints under "## Project rules" - reconcile and
      forward the one naming the task; exit 2 with two `line N:` headings - do not dispatch; a
      `.orig` already in the scratchpad - not used, mutation_arm or a `mktemp -d` copy instead;
      a reviewer doubting a test - names the mutation rather than making it.
- [x] The arm was asked for a `Skill gaps` section; its list is worked below.

## REFACTOR - every gap closed or declined

- [x] GAP: who renames a duplicated task id. CLOSED - the exit-2 sentence now says to ask the
      human which heading is meant, as for any plan contradiction, and re-run once the plan gives
      each its own id. Quote-back on haiku answered with that sentence.
- [x] GAP: whether dispatch waits when constraints sit under another heading. DECLINED - the
      remedy is to forward the constraint, which the sentence states; nothing needs to wait.
- [x] GAP: where `mktemp -d` puts the directory. DECLINED - any directory made fresh for this run
      is unique to it, which is the property the rule needs.
- [x] GAP: whether a reviewer may ever run a mutation. DECLINED - the text answers it: name it by
      default, and if one must run, only through mutation_arm with the clean-tree check after.
- [x] GREEN against the pre-change behaviour: brief composition, the report-file contract and the
      reviewer's read-only rule are unchanged apart from the added sentences.

## Quality

- [x] Description unchanged, so the trigger map needs no rebuild.
- [x] Script referenced from outside its skill names its home under `$CLAUDE_PLUGIN_ROOT`.
- [x] No narrative, no scratch paths, no addresses added.

## Deployment

- [x] No version bump or CHANGELOG entry in this branch: the integration owner bumps and writes
      the release notes for the whole batch.
