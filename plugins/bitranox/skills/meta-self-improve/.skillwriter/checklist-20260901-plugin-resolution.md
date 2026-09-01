# skill-writer checklist - meta-self-improve (how to resolve the <plugin> placeholder)

Change: one paragraph before step 4's engine invocation. `<plugin>` appears in six commands in
this skill and was defined nowhere in it, so none of them could be turned into a runnable command
by a reader who did not already know the answer. The paragraph states what the placeholder is, how
it resolves in a hook and in an ordinary session, and why a version directory must not be pasted.

## PLAN

- [x] Skill type: technique (a procedure whose body carries executable commands).
- [x] Test approach: application scenario. The gap is executable - either the reader produces a
      runnable path or does not - so an agent asked for the exact command is the test.
- [x] Scope: one paragraph. The same placeholder convention is used by sibling skills; this change
      defines it where the invocation lives rather than restating it everywhere.

## RED

- [x] Two probe agents were given the invocation block WITHOUT the paragraph and asked for the
      exact command with no placeholders left. Neither produced a runnable path.
- [x] Arm one left `<plugin>` literal and said so: it could not resolve the installed cache
      directory from the supplied text, and declined to guess a version.
- [x] Arm two resolved it to `$CLAUDE_PLUGIN_ROOT`, reasoning it is "the standard Claude Code
      plugin-hook env var". That is true of a HOOK and false of an ordinary session: the variable
      is unset there, verified directly, so the command would have expanded to `/hooks/...` and
      failed. A confident wrong answer is the worse of the two failures.
- [x] Both arms ran on tool-less probe agents, so each answer came from the supplied text rather
      than from exploring the filesystem.

## GREEN

- [x] A probe agent given the paragraph plus the base-directory announcement produced an absolute
      path with no placeholder, deriving it as instructed: the announced base directory with the
      trailing `/skills/meta-self-improve` dropped.
- [x] It quoted the rule it applied rather than paraphrasing, so the text is what produced the
      answer.
- [x] No trigger keyword moved: the change adds a body paragraph and does not touch the frontmatter.

## REFACTOR - gaps from the GREEN dispatch

- [x] Every dispatch, RED and GREEN, was asked for a `Skill gaps` section and each returned one.
- [x] "Silent on what to do if the resolved `<plugin>` cannot be verified to exist." DECLINED: the
      next line of the procedure already requires the engine's success line before a capture counts,
      so a wrong path fails loudly at the call rather than silently.
- [x] The body-file path was unknown to the arm. DECLINED: an artifact of the test scenario, which
      named the file abstractly; no skill text is implicated.
- [x] Both GREEN arms independently flagged a near-duplicate stored fact before acting. Not a gap:
      that is the dedup step in this same skill working as written.
- [x] GREEN diffed against RED in both directions. Nothing the baseline produced is missing.
- [x] Undecided gap list is empty.

## Quality

- [x] Present tense, no session narrative, no operator instructions, no scratch paths.
- [x] Paths named in the paragraph are the placeholder itself and the source-repo location, not a
      machine-specific value.
- [x] Frontmatter untouched: no `name` or `description` change.
