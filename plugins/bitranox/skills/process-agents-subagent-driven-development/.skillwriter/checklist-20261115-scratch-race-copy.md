# skill-writer checklist - process-agents-subagent-driven-development (20261115, scratch output, race check, copy method)

Changes: implementer-prompt.md (scratch output in a `mktemp -d` dir outside the worktree; report
file written only after the gate's closing line, quoting it), task-reviewer-prompt.md (untracked
scratch output outside the worktree; `git diff HEAD` and `git status --porcelain` compared before
and after), SKILL.md (a brief names the scratch-copy method and forbids `cp -a`/`cp -r` of a whole
directory; the final whole-branch review runs a two-process concurrency check per writer pairing;
a fix dispatch copies the scratch-output paragraph too).

- [x] Decisions: d-20261115-909c6925, d-20261115-4f436f48, d-20261115-87bbbe15
- [x] Step 0b: `show --kind rejected,removed --full` read; the two rejected entries are about
      headless plan-text findings and are untouched. Live rule anchors still present.
- [x] RED: text-only quote-or-NONE probe over the pre-edit excerpts (`git show HEAD:` text) of
      both templates and the SKILL.md sections, `opus` and `haiku`, 5 questions, 2 cells. Both
      tiers answered NONE for scratch-output location, report timing and gate verdict, a race
      check, and the copy method; the reviewer question was answered only by the bare read-only
      rule. Route: coverage check against the skill file, since several of these lessons sit in
      the always-loaded memory index and a behavioural RED could not fail honestly.
- [x] GREEN: same 5 questions plus a control (a pure string formatter that writes nothing) on the
      edited text, `opus` and `haiku`, 2 cells. Every question answered with a direct quote of a
      new sentence on both tiers; the control did not trigger the race check on either tier.
- [x] Gaps closed after GREEN: one new writer against a pre-existing one (the check now names every
      pairing, existing writers included); no pass/fail rule for the race check (a state neither
      serial order gives, from the same starting state, is a DEFECT); scratch dir cleanup (removed
      by its exact path); the reviewer's `git diff --quiet HEAD` check could not work on an
      already-dirty checkout (now: `git diff HEAD` prints what it printed before).
- [x] Re-probe of the amended clauses on the final text, `opus` and `haiku`, 3 questions (one new
      writer plus an existing one; an already-dirty file; the pure-formatter control): both tiers
      quoted the governing sentences, named both pairings, chose the `git diff HEAD` comparison
      over the porcelain check for the dirty file, and did not trigger the race check for the
      control. No new undecided gap; remaining items declined below.
- [x] Gaps declined: the implementer/reviewer difference on restoring a mutation from a scratch
      copy predates this change and is deliberate (the reviewer is read-only; the implementer may
      copy into its own `mktemp -d` dir); how to force two writers to overlap and what a crashed
      agent leaves behind are judgement for the agent running it, as are a repeat count and how
      to compare stores holding timestamps or generated ids; readers of shared state and pairs of
      two unchanged writers are outside the rule, which is about writers the branch changed;
      saving the `git diff HEAD` output at the start is implied by "prints what it printed before
      you started", which both final re-probe tiers acted on.
- [x] Commands added (`mktemp -d`, `git status --porcelain`, `git diff HEAD`, `git clone
      --no-local`) are standard invocations with no placeholders to resolve.
- [x] Width and fence check over the added lines printed nothing; ASCII only; the latest-release
      finder hits nothing in the added lines.
