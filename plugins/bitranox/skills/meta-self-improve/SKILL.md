---
name: meta-self-improve
description: Use at the end of a turn that produced a learning, such as a correction from the user, a rule or preference stated ("remember this", "from now on", "always/never"), a process or tooling mistake (wrong command, a quirk of the shell/SSH/environment, a misread of stale output, over-waiting, a tool or file you missed and re-derived), a wasted build or test cycle, or any reusable discovery (a procedure, a timing, a gotcha, a flag combination, a path). A gated Stop hook nudges this automatically; also run on "self-improve", "/self-improve", "improve the harness", or "capture what we learned".
---

# self-improve

Turn what this session taught into a durable improvement, so the same lesson is not re-learned next
time. The unit of value is ONE small, reusable fact recorded via the memory engine at the project
level of the current knowledge tree - or, when a rule must bind future sessions, a CLAUDE.md
guardrail (step 3b).

**Core constraint: memory is finite. Default to updating an existing entry, never to appending
blindly.** A self-improver that bloats memory makes the harness worse, not better.

This skill is the per-turn CAPTURE. The periodic BATCH consolidation - dedup / merge / re-level /
prune, like sleep - is `bitranox:meta-dream-tree` (and `bitranox:meta-dream-crosstree` across
trees). Capture here; consolidate there. If a project ships its own `*-self-improve` extension,
honor its extra rules on top of this one.

## Reference files

| Topic                                                                                                                                                                             | File                               |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------|
| Storage spec - trees/anchors, pointer-block grammar, mem: lines, trigger-first hooks, body frame, tiers + capture flow, delivery paths, engine command table + fail-loud contract | references/memory-backend.md       |
| Upstream PR loop - shared skill/hook changes to the source repo, scan, routing, version bump                                                                                      | references/upstream-propagation.md |

Use the Read tool to load a referenced file when its detail is needed. **REQUIRED BACKGROUND:**
references/memory-backend.md is the storage spec - Read it BEFORE the first engine call of a
session.

## Before moving a fact: map its refs in BOTH directions

`move` guards only INBOUND refs. It refuses a down-move that would dangle one, and never looks at
the refs the fact itself MAKES, so lifting a fact to a common ancestor silently strands every
outbound ref to a fact left below. Ask for both halves first:

```bash
bash <plugin>/hooks/run-python.sh <plugin>/skills/meta-self-improve/ref_map.py \
  --root <anchor> <slug> [<slug> ...] [--json]
```

Read it as: a non-empty **inbound** list is what a down-move will be refused for (re-point those
refs first, or leave the fact); an **outbound** target sitting BELOW the level you are lifting to
is what will be stranded (lift the shared targets too, or demote the irreducibly-local ones to
plain prose). `DANGLING` means the target exists nowhere. Underscores and dashes are the same slug,
matching the engine, so `[[a_b]]` against a fact named `a-b` is a match and not a defect.

## When to run

Any turn with a learning signal. Signal families (the gated Stop hook fires on all of them): a user
**correction**; an explicit **"remember"**; an **endorsement of a good idea from either side**
("good idea", "good call" - when YOU judge the user's suggestion good, adopt and record it; when
the user endorses yours, it is a confirmed approach); an assistant **self-admitted miss** ("you're
right", "my mistake", "I should have...", "in hindsight..."); an assistant **commitment going
forward** ("from now on I'll..."); a **realization or discovery** ("now I understand the real
topology...", "found it - the root cause was..."). A realization about infrastructure,
architecture, or data-flow is a durable discovery - capture it before the turn ends. A bare
acknowledgement ("understood") is not itself the signal - trigger on the rule it acknowledges.

If you reflect and find nothing durable, say so in one line and stop. Never manufacture a
"learning". When the gate missed a signal, fix the WHOLE family in `self_improve_signals.py`
(home: `<plugin>/hooks/`, launch via `hooks/run-python.sh`), not just the one phrase.

### End-of-session miss audit (self-tuning loop)

The per-turn gate is precision-tuned, so a broader SessionEnd scan (`self-improve-audit.py`, home:
`<plugin>/hooks/`) records candidate misses to a per-project audit file; SessionStart surfaces it
ONCE next session. Review the candidates: capture the genuine misses here, and for a real gap
extend the gate's family patterns in `self_improve_signals.py` (same `<plugin>/hooks/` home; gate
and audit share that module, so they never drift).

The audit scans THREE sources, because a learning does not always reach prose:

- **Prose** (user + assistant text) via the broad patterns.
- **Tool blocks** (`tool_use` commands, `tool_result` output) via the TOOL signal set. A tooling
  gap often announces itself only here - `error: unrecognized arguments: --rehome-to` is the whole
  discovery, with no sentence anywhere. The gate never reads tool blocks, so every tool signal is
  by definition a miss.
- **The skill tally** - which skills actually ran. If a candidate miss is a bug that shipped
  DESPITE a skill that ran, that is that SKILL's coverage gap, not just a memory: flag it and fix
  the skill (see `flag-a-skill-when-a-real-bug-slips-past-it`). This is real invocation data read
  from the transcript, not recall - in a long session the early invocations have scrolled out.
Premature signals ("wait...", "let me double-check") stay audit-only - the lesson is not formed
yet. Skill-coverage gaps are NOT this loop's job: a defect that slipped past a skill you followed
goes to the dream's skill-gap pass.

## Procedure

Create one todo per step.

### 1. Gather candidates

Reflect on the just-finished work. List the concrete, reusable things it surfaced, one sentence
each. Discard task state, anything the repo/git history already records, and anything that only
mattered to this conversation.

Also refuse two classes outright, whatever else recommends them:

- **A bare negative claim about a tool** ("X is broken", "that flag is
  unsupported"). These harden into refusals the agent cites against itself long
  after the thing was fixed, and the store has no mechanism to notice the fix.
  Record the WORKING alternative instead, or attach the version and date that
  make the claim re-testable for a later reader - that improves the fact's
  quality but does not suppress the write-time warning below, which fires on
  every bare negative claim regardless.
- **An unresolved failure.** If the session never found a working method,
  capture the dead ends AS dead ends, explicitly labelled unsolved - an
  unlabelled write-up presents untested attempts as validated guidance a
  later session will trust and repeat.

The engine warns on both at write time; the warning is advisory, and this is the
judgement it is prompting for.

### 2. Classify each candidate

| Kind                                                                                            | Home                                                                                                                                           |
|-------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| User correction or working-style directive ("from now on...", "always/never...")                | a `feedback` memory AND, if it must bind future sessions, a CLAUDE.md guardrail line                                                           |
| Recurring process/tooling/environment mistake (wrong command, shell/SSH/OS quirk, stale output) | the project's recurring-error record if it has one (bump count + date), else a `feedback` memory phrased as the check that avoids it           |
| Discovery or miss (a re-derived tool/path, a measured timing, a gotcha, a working procedure)    | the most relevant existing `project`/`reference` memory, or a new one                                                                          |
| Architecture/topology/data-flow realization                                                     | the right altitude per step 3b; unsure -> ask the user                                                                                         |
| A skill was wrong, missing, or mis-triggered                                                    | PROPOSE (step 5); never rewrite an existing skill inline (sole exception: this skill, see the meta-loop)                                       |
| A multi-step manual chore re-done from scratch a 2nd time (or a local tool that came up short)  | PROPOSE a LOCAL tool in `toolbox` (step 6); build/enhance it TDD only after user OK - never auto-author, never hand-roll around a fixable tool |
| Nothing durable                                                                                 | drop it                                                                                                                                        |

### 3. Dedup BEFORE writing (mandatory)

Grep the pointer blocks (`CLAUDE.local.md`), the anchor's `facts/` bodies, the native memory dir,
and the CLAUDE.md chain for each candidate's keywords. If a related entry exists, UPDATE it: rerun
the engine `add` against the level that OWNS its pointer, passing `--slug <the stored slug>` - it
then upserts (merges provenance, keeps the pin). New entry only when nothing covers it.

**Both halves of that sentence are load-bearing, and each fails silently in its own direction.**

- **The level.** The upsert branch searches only the entries at `--proj`. Aim it anywhere else and
  the engine refuses with `SlugCollision`, which names the slug but not the level, so it reads as
  "this fact already exists" - and its suggestion, `<slug>-2`, would create the duplicate you were
  trying to avoid. A fact an earlier dream promoted can no longer be updated from the project it
  came from. Find the owner first, and use `find`, because a session `grep -r` skips those files
  as gitignored:

      find <anchor> -name CLAUDE.local.md -not -path "*/.claude-memory/*" -exec grep -l "mem:<slug>" {} \;

- **The slug.** Passing the current TITLE and no `--slug` derives a slug from that title, which is
  NOT the stored one whenever the fact has been retitled since capture. There is no collision to
  refuse - the derived slug is free - so `add` mints a SECOND fact, pointer and body, and says
  nothing. Read the slug off the pointer line and pass it.

### 3b. Choose the altitude - by SCOPE, placed concretely

- **Per-turn capture writes at ONE PROJECT level - the level of the fact's SUBJECT, which is
  USUALLY but not always the cwd.** Raising a fact to a higher ALTITUDE is the DREAM's job (engine
  `move`), never capture's - a routine capture never touches a parent level.
- **Route `--proj` by SUBJECT, not blindly by cwd.** You often work FROM one repo while fixing
  another (a sibling project, or a repo in a different tree). The learning belongs to the repo it is
  ABOUT. The Stop-gate nudge carries ROUTING EVIDENCE - the other levels this turn actually edited
  (from the `touched-paths` recorder) - so use it:
  - the learning is about a repo you EDITED -> `--proj "<that level>"`;
  - the learning is about the cwd's own workflow/tooling (even though you edited elsewhere) -> cwd;
  - genuinely both or unclear -> ask the user.
  This matters most CROSS-TREE: a fact misfiled into another tree can NEVER be re-homed by a dream
  (`move` refuses to cross trees) - it is wrong until a human finds it. Same-tree misfiling is
  recoverable (the tree dream re-levels), but still capture it right.
- Decide the eventual home by **scope of applicability, not abstractness**: the narrowest level
  that still covers everywhere the lesson applies. Concrete knowledge useful tree-wide belongs at
  the tree's top KEPT CONCRETE. The per-level scope descriptors (the `bitranox:self-learning`
  block) are the routing key; when genuinely unclear, ask the user.
- **SUBAGENT learnings are yours to capture.** A subagent's discovery lives only in ITS transcript -
  it is not in yours, and a named/background agent's report is not returned to you at all. The
  `SubagentStop` hook detects those signals and the Stop-gate nudge surfaces them to you verbatim
  (labelled SUBAGENT LEARNINGS); you are the only one who can route + write them. Judge each: capture
  the durable ones (routing `--proj` by SUBJECT, same rule), drop the task-local noise. They are
  surfaced ONCE - if you skip them they are gone.
- An intermediate must-hold rule for a whole subtree goes in that level's `CLAUDE.md` (propose-first
  at CAPTURE time; the case model + guards live in `bitranox:meta-dream-tree` ->
  references/dream-passes.md "CLAUDE.md reconciliation").
- **Normalization, not duplication:** store a general rule ONCE at its altitude; a lower entry
  cites `[[general-slug]]` plus only its delta. References point UPWARD only.
- **Promotion to the tree's top is gated**: user-stated rules promote eagerly; a model-inferred
  generalization needs corroboration across >= 2 dreams (`promotion` config knob).
- **A universal rule can also belong in a SHIPPED skill** (the shared brain; the private store
  teaches only you). If it matches a shipped skill's domain (shell -> `bitranox:compuse-bash`, git
  -> `bitranox:compuse-git`, ...) or warrants a new one, raise the public-contribution option -
  propose-first, scrub private specifics, route via references/upstream-propagation.md. Never let a
  clearly-shippable rule stop silently at the private layer.
  **QUEUE IT THE MOMENT YOU JUDGE IT SHIPPABLE**, before doing the work - the intent is what gets
  lost, not the fact: `contrib_queue.py add --what ... --target skill:<name> --why ... "<cwd>"`
  (home: `<plugin>/skills/meta-self-improve/`, launch via `hooks/run-python.sh`). The queue is
  durable and SessionStart surfaces it every session WITHOUT consuming it, so the intent survives a
  session end. Close an entry only once it actually shipped, and by the right outcome: `ship --match
  <unique text> --note <where it landed>` for delivered, `drop --match ... --reason ...` for
  disproven or stale. Select by `--match`, never `--index`: an index shifts under the previous
  close, so two closes from one listing destroy the wrong entry. A delivered contribution recorded
  as rejected tells every later reader the work was not done.

### 4. Write it (the engine, fail-loud)

Compose the entry per the specs in references/memory-backend.md:
- **Hook: trigger-first.** `When <situation>, <directive>.` - second person, 1-3 sentences,
  self-sufficient (keep names/paths/flags/numbers in it). A trigger-less hook never fires during
  reasoning; the engine warns on one. Aim under the 350-char SOFT cap, but a complete trigger-first
  hook may run up to the 500-char HARD cap - never drop load-bearing detail just to silence the
  advisory soft-cap warning. Past 500 the engine REFUSES the add (exit 1, nothing written): rewrite
  the hook to the one directive that fires, and let the body carry the rest.
- **Body: framed prose with reasoning.** The fact, then `**Why:**` and `**How to apply:**` lines
  (the engine adds the frontmatter frame).

Then ONE engine call per fact, and REQUIRE its success line (the printed slug):

    bash <plugin>/hooks/run-python.sh <plugin>/hooks/memory_engine.py add \
      --proj "<cwd>" --type feedback|project|reference|user \
      --title "..." --hook "When ..., ..." --body-file <tmpfile> [--source <key>] [--pin] [--slug s]

Risk ladder: engine `add` at the project level is additive - auto-apply. Rewriting/deleting an
existing entry, restructuring or editing any CLAUDE.md, pruning - propose-first
with a diff. Shared/published artifacts - never auto-edit; respect push gates.

### 5. New-skill gaps: propose first

If a missing or broken skill is the real fix, write a one-paragraph proposal (trigger, behavior,
shared vs project-specific) and STOP at the proposal. On explicit permission, build it with
`bitranox:meta-skill-writer` (never hand-rolled), place it by scope, and propagate a shared one per
references/upstream-propagation.md.

### 6. Escalate repeats: count, then enforce

Soft rules are advisory - the model can and will skip them. Track recurrence and climb the ladder;
do not just write the note louder:
- First miss: write the rule (memory and/or CLAUDE.md guardrail).
- Recurs once: strengthen it (mark MUST, add the failing example) and bump its
  `recurrence: N (last YYYY-MM-DD)` line. The engine reads that count back: an `add` whose BODY
  records a repeat of 2 or more prints a `~ warning:` naming BOTH endpoints below, so the signal
  reaches you at the moment you write it rather than depending on you re-reading this section at
  the end of a long turn.
- Count reaches 2: STOP re-wording - prose has failed. Escalate to a DETERMINISTIC guard (a
  PreToolUse/Stop hook via Claude Code's built-in `update-config` skill - a HOST skill, not one this
  plugin ships - or a CI check, or a real code fix; user-gated,
  never auto-created). Guards follow the cross-platform script rules in
  `bitranox:meta-skill-writer`; a globally-useful guard belongs in the shared plugin's `hooks/` and
  MUST propagate upstream - local-only `~/.claude/hooks` is the classic loss.
- **Lifting a local hook into the plugin is a TWO-STEP retirement, and half of it is worse than
  neither.** After the plugin's copy is registered, remove the local hook's `settings.json` entry
  (via the host `update-config` skill) AND retire the file. Both copies otherwise fire and the one
  that blocks FIRST wins, so a stale local hook silently overrides the newer plugin version while
  the plugin looks installed and current - the failure never announces itself. Dropping only the
  file leaves a registered hook erroring on every matching call; dropping only the entry leaves an
  armed file for the next stale runbook line. Retire it as a non-executable shim that exits
  non-zero naming its replacement, keeping the original as `.orig-<date>`.
  **Prove coverage before removing, never assume the newer one is a superset:** feed BOTH copies
  the same synthetic hook events and compare verdicts across the real cases AND the ones that must
  NOT fire. Measured on this pattern: a stale local guard blocked text that merely MENTIONED the
  footgun it guards, so it blocked writing the documentation for its own rule.
Memory changes what the model is TOLD; a guard changes what it can DO. A must-hold rule ends in a
guard.

**A guard is not the end when the SAFE form is still hand-rolled - cross to the chore ladder.** A
blocking guard stops the WRONG action; it does not PROVIDE the right one. So when a footgun's guard
lands but you STILL hand-write the safe replacement every time (block `pkill -f` self-match, then
hand-roll the readlink-over-`/proc` loop; block `sed` on structured files, then hand-roll the
parse), the CHORE ladder below ALSO fires: propose a jig that DOES the safe thing, and once it
exists add a nudge signature so the guard's own victims are pointed at it. The two ladders are not
exclusive - a footgun that both keeps recurring AND leaves a hand-rolled safe form earns BOTH a
guard and a jig; guard-installed is not "handled". (A guard that instead FALSE-fires on legitimate
text - a footgun keyword quoted inside a commit message - is the same signal from the other side:
refine the guard or supply the jig, do not just route around it.)

**A recurring manual CHORE ends in a TOOL** (the fourth endpoint; a craftsman builds his own jigs).
Distinct from a rule violation: this is re-doing the same multi-step WORK by hand (parse/scan/extract/
reformat a thing you have hand-rolled before), not skipping a rule. Same ladder, one step over:
- First time: just do it by hand.
- Second time (re-doing the same chore from scratch): PROPOSE a tool - "this recurring chore is worth
  a tool" - and wait for the user's OK. Never auto-author (a fuzzy "did I re-run a similar script"
  detector would re-create the gate false-positive class; this is a model judgement in THIS reflection).
- On OK, build it in the **LOCAL `toolbox`** (a personal `~/.claude/skills/toolbox/` skill),
  TDD (RED core-function test first), best library + PEP 723 deps run via `uv run` (its SKILL.md
  carries the contract). Tools stay LOCAL by default.
- **REGISTERING it needs a passing RETRIEVAL test, not just file + test + index row.** A green unit
  test says nothing about whether the row is FINDABLE, and a jig nobody finds gets hand-rolled
  again - the exact chore it was built to end. RED first, before rewriting any row: ask a subagent
  the question a USER would ask, in their words, with the whole index visible and NONE stated as
  acceptable ("if nothing fits and you would just use a shell command, say so"). ONE question per
  agent - a batch primes a 1:1 mapping and lets the agent disambiguate by comparing rows, and
  without the NONE sentence it picks the nearest row, so the test can never fail. Write the row
  with the user's NOUN, not the mechanism ("Stalled or hung?" retrieves, "multi-signal verdict"
  does not), both jobs of a two-job tool, and a real value in the usage column (it gets copied).
  Measured: a row reading "capped resumable fetch" lost its own download case - asked to cap a
  5 GB download to 8 Mbit/s, an isolated agent answered NONE and reached for curl, having read
  "capped" as retries.
- ENHANCE, do not work around: a toolbox tool that is buggy/insufficient in use gets a RED regression
  test + a fix (propose-first), never a hand-rolled bypass - the tool analogue of
  `flag-a-skill-when-a-real-bug-slips-past-it`.
- CONTRIBUTE upstream only when a local tool proves BROADLY useful to other users: propose it via the
  `contrib_queue` + upstream loop (references/upstream-propagation.md), landing it in a relevant
  existing skill - exactly the local-stays-local / share-when-broad split skills already use.
  Never automatic.
- **A contribution ENDS by RETIRING the local original - landing it upstream is only half.** Same
  two-step shape as lifting a hook, and half of it is worse than neither. WHEN depends on whether
  you can land it yourself: with COMMIT RIGHTS, delete the local copy and its tests in the same
  change that pushes the shipped one, because there is no window to forget in. Via a PR, the twin
  appears in a LATER session with nobody standing at the contribution, so retire it when it lands -
  and do not rely on remembering: `bitranox:meta-audit-local-skills-and-hooks` reports every local
  hook or skill script the marketplace also ships (`duplicate-of-shipped`), and the deep dream runs
  that audit, so the pass catches what the moment could not. Either way the end state is ONE source
  of truth. Two copies do not
  stay in sync by good intentions - measured on this machine, EIGHT local tools had been contributed
  and left in place, and all eight had drifted from their shipped twin (code-identical with
  docstrings stripped, but the shipped prose had been scrubbed of private references and had gained
  usage detail the local copy never got). Before deleting, GREP THE OLD PATH and repoint every hit,
  including THE MEMORY STORE - fix a fact's HOOK as well as its body, since the hook is what the
  model follows at the moment the rule fires. Sweep the facts, the CLAUDE.md cascade, hooks, nudges
  and docs (`grep -rl '<old/path>'`, via find - Claude Code's grep skips gitignored files, and both
  the facts and the pointer blocks are gitignored), and require zero hits before you delete.
  Retiring the FILES while leaving the REFERENCES is
  the half that bites: measured on this machine, `gate.py` was correctly retired once it shipped in
  `bitranox:compuse-toolbox`, and the one reference nobody swept was the memory rule prescribing it
  - the remedy for the tree's most-recurring shell error became a command that could not run, whose
  documented fallback is hand-rolling, which is exactly how that error recurs. Name the replacement
  by SKILL rather than by path where you can, since a path under a versioned plugin dir rots on the
  next bump. Keep the local copy only when it genuinely diverges on purpose, and then say so in its
  docstring.

### 7. Report

End with a short summary: what was auto-applied (file + one line each) and what awaits a go. No
filler.

## Improving this skill (meta-loop)

The one exception to "propose, do not author" is this skill and its gate (`self-improve-gate.py`).
Treat a change as highest-risk: propose-first, re-verify with a baseline subagent test after any
substantive change, and land it in the SOURCE repo per references/upstream-propagation.md. Enter
the meta-loop when the improver itself fails: the user rejects a capture, the gate fires on noise
or misses corrections, the same learning recurs across sessions, or a ledgered rule keeps being
violated. Diagnose the stage (classify/dedup -> sharpen wording; bloat -> tighten edit-over-new;
gate noise -> adjust its patterns; rule still violated -> run step 6 to its END). **Circle-breaker
(mandatory):** if two passes on the same issue have not resolved it, writing the same lesson a
third time IS the circle - switch to enforcement or hand the decision to the user.

## Asking for a decision

Ask ONE question at a time, never a batch. For each: state what is being decided, give the
realistic upsides and downsides of every option, and ALWAYS end with a recommendation plus its
reason. Wait for the answer before the next question.

## Writing style

Notes are read by a future agent. Plain and short: the fact and the why, no promotional adjectives,
ASCII only - no em-dashes or typographic/invisible tells (the tell-sweep hooks enforce this on
files and commit messages; sweep anything else yourself).

## Pathfinder discipline (leave it better)

Fix the adjacent rot you touch and can verify; surface mistakes clearly, never wave them off;
out-of-scope fixes go in their own worktree (`bitranox:git-worktrees`); remove temporary
scaffolding when the goal is met.

## Deliverables (a completed capture run has ALL of these)

- [ ] Dedup grep ran over the pointer blocks + `facts/` bodies + native tier BEFORE any write.
- [ ] ONE engine `add` per fact; its printed slug captured (fail-loud - no silent results).
- [ ] Every hook trigger-first ("When <situation>, <directive>.") and self-sufficient. The 350-char
      soft-cap warning is advisory - acceptable; the 500-char HARD cap is a refusal, so an add that
      exits 1 needs the hook rewritten (surplus detail into the body), not the fact abandoned. Never
      trim a complete hook just to silence the soft-cap warning.
- [ ] Every body carries the fact plus **Why:** and **How to apply:**.
- [ ] Everything written at ONE PROJECT level - the level of the fact's SUBJECT (the cwd unless the
      routing evidence says the learning is about a repo you edited elsewhere); never an ancestor,
      never only CLAUDE.md.
- [ ] The report: auto-applied items (file + one line each) vs proposals awaiting a go.

An ended run missing any box is not done - finish it or say plainly what was skipped and why.

## Rationalizations (pressure-tested; these do not fly)

| Excuse                                                             | Reality                                                                                                                  |
|--------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| "It's arguably a different fact" (my drafted entry feels distinct) | Sunk cost in a draft is not a scope argument. A covering entry exists -> same slug, fold the delta, discard the draft.   |
| "It's obviously universal - capture at the tree top directly"      | Your certainty IS the inference the promotion gate exists to check. Project level now; the dream moves it, corroborated. |
| "Writing it in both places is safer"                               | Duplication is the failure mode, not a safety net. One home; the lower cites `[[general]]` + delta.                      |
| "The user is waiting - a bare one-liner is enough"                 | A trigger-less hook never fires and a bare body gets discounted; the trigger + Why/How cost seconds and are the value.   |
| "CLAUDE.md already mentions it, so it's captured"                  | A CLAUDE.md line loads only in that repo; it is not the store. Capture properly, then flag the overlap for the dream.    |

## Common mistakes

- Appending a new entry when an existing one should have been updated (bloats the always-loaded
  block).
- A trigger-less hook ("Fix X properly" instead of "When you hit Y, fix X") - it never fires
  mid-reasoning.
- A bare-prose body without **Why:** / **How to apply:** - the model discounts it as inauthentic.
- Hand-editing a pointer block or body (guard-denied; the engine is the only write path).
- Capturing at an ANCESTOR level - capture is project-level; the dream re-levels the altitude.
- Blindly capturing at the cwd when the turn's routing evidence shows the learning is ABOUT a repo
  you edited elsewhere - route `--proj` by SUBJECT (step 3b). Cross-tree that misfile is permanent:
  no dream can move a fact between trees.
- Recording session state ("the build is running") as a durable learning.
- Auto-applying a rewrite or delete - additive is auto, destructive is propose-first.
