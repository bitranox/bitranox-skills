# skill-writer checklist - git-worktrees (where a bare topic name looks for the worktree)

Change: `scripts/wtclean.py` resolves a bare topic against three project-local layouts as well as
the base convention, and reports the paths it tried when none match. Step 4 of `SKILL.md` documents
that search, states two consequences of it, corrects a refusal bullet that contradicted the
section's own example, and says when refusals are evaluated.

## PLAN

- [x] Skill type: reference/procedure section documenting a bundled tool. Test approach: retrieval
      scenario, one arm without the change and one with it, plus a quote-back pass.
- [x] Checked what the section ALREADY said: it documented the CACHE search convention in detail
      and said nothing about how the worktree itself is located.
- [x] Scope: extend Step 4 in place. The tool change carries its own tests in `scripts/tests/`.

## RED

- [x] Retrieval scenario, pre-change text: asked for the exact first command to remove a checkout at
      `.claude/worktrees/<topic>` and how the output would confirm it found the right one.
- [x] The baseline named the gap itself: "How the tool locates the checkout itself is never stated
      ... never explains how a bare topic like `auth-retry` resolves to an actual worktree path such
      as `.claude/worktrees/auth-retry`. I assumed the tool can make that connection ... This is the
      biggest gap - it's the crux of whether my chosen first command actually works."
- [x] It also reported, unprompted, a contradiction that predates this change: the refusal bullet
      said a path argument is refused while the third usage example passes one.
- [x] The code RED is independent of the prose one and was verified by mutation: setting
      `PROJECT_WORKTREE_DIRS = ()` fails exactly the 7 tests asserting the new search and none of
      the 4 asserting the unchanged directions (base-only default, base wins over project-local,
      absent-reports-base, explicit-base-does-not-reach-into-the-project).

## GREEN

- [x] Same scenario, post-change text: the answer states the search order, identifies
      `.claude/worktrees/<topic>` as covered, and reads a `nothing to remove` result as the
      documented failure mode rather than a safe answer. RED's crux gap is closed.
- [x] Both arms were asked for a `Skill gaps` section and both lists are worked below.

## REFACTOR

Diffed GREEN against RED in both directions. GREEN gained the resolution answer and LOST the
contradiction RED had found - it quoted the wrong bullet as its justification and then recommended
a path argument in the same reply, walking into the contradiction without noticing. A lost finding
is a requirement, so:

- [x] The refusal bullet now states the real rule, verified against the tool rather than reasoned
      from: a path with no parent reference is accepted and names the worktree, while `../../etc`
      is refused outright. Confirmed by running both shapes.
- [x] Two properties GREEN had to guess at are now stated as rules rather than implied by an
      anecdote: the project-local candidates are relative to the working directory, and the first
      candidate that exists wins, so a stale base-convention directory shadows a project-local one.
- [x] Both arms asked when refusals are evaluated; the section now says plan time, and distinguishes
      a plan-time `REFUSED` from an apply-time `FAILED` that only attempting the removal can find.
- [x] Two claims written during that pass were corrected before shipping because they overstated the
      code: the dry run lists the refusal RULES, not everything an apply can fail on, and it names
      the resolved path only when it found one.

Quote-back pass, four contested questions, answer required to be a verbatim quote or NONE. All four
returned a quote; none returned NONE. Its remaining gaps:

- [x] CLOSED: "the topic DERIVED from the argument" was ambiguous - the reader guessed it referred
      only to cache naming. The bullet now says the topic is the last path segment with the prefix
      stripped and that the cache candidates are built from it. Verified:
      `.worktrees/wt-my-feature` yields topic `my-feature` and candidate `wt-my-feature-target`.
- [x] CLOSED: a missing EXPLICIT path was told to "pass its path instead of the bare name", advice
      that does not fit what was given. The hint now branches on the argument shape, pinned by a
      test plus a control asserting the bare-name advice survives.
- [x] DECLINED: no signal beyond reading the resolved path when a topic is ambiguous. Accurate - the
      tool has no ambiguity flag, and inventing one is a tool change, not a doc fix.
- [x] DECLINED: no verbatim sample of the plan output. A pasted sample goes stale on the next format
      change, and the reader runs the dry run before acting anyway.

Undecided gaps remaining: none.

## Quality

- [x] ASCII only, present tense, no session narrative, no operator instructions, no scratch paths.
- [x] No real addresses, MACs, hostnames or machine paths added:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/' SKILL.md`
      returns nothing.
- [x] Frontmatter untouched; no routing keyword moved, so the derived trigger artifact is unchanged.
- [x] Hub-skill body stays an index over `scripts/`; the new text is 3 paragraphs and 2 bullets.

## Deliverables

- [x] `scripts/wtclean.py`: `worktree_dirs()`, `Plan.worktree_candidates`, candidate resolution in
      `build_plan`, the not-found warning, and the branching hint.
- [x] `tests/test_wtclean.py`: 13 new tests. Suite 75 passed; repo gate at CI parity green.
- [x] `SKILL.md` Step 4 and the tool's own module docstring and `--help` epilog carry the same
      description of the search, so a reader who never opens the skill still gets it.
