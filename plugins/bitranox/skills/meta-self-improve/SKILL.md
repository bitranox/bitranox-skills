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
prune, like sleep - is `bitranox:meta-dream-project` (and `bitranox:meta-dream-global` across
trees). Capture here; consolidate there. If a project ships its own `*-self-improve` extension,
honor its extra rules on top of this one.

## Reference files

| Topic                                                                                                                                                                             | File                               |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------|
| Storage spec - trees/anchors, pointer-block grammar, mem: lines, trigger-first hooks, body frame, tiers + capture flow, delivery paths, engine command table + fail-loud contract | references/memory-backend.md       |
| Upstream PR loop - shared skill/hook changes to the source repo, scan, routing, version bump                                                                                      | references/upstream-propagation.md |

Use the Read tool to load a referenced file when its detail is needed (the backend spec BEFORE the
first engine call of a session).

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
"learning". When the gate missed a signal, fix the WHOLE family in `self_improve_signals.py`, not
just the one phrase.

### End-of-session miss audit (self-tuning loop)

The per-turn gate is precision-tuned, so a broader SessionEnd scan (`self-improve-audit.py`)
records candidate misses to a per-project audit file; SessionStart surfaces it ONCE next session.
Review the candidates: capture the genuine misses here, and for a real gap extend the gate's family
patterns in `self_improve_signals.py` (gate and audit share that module, so they never drift).
Premature signals ("wait...", "let me double-check") stay audit-only - the lesson is not formed
yet. Skill-coverage gaps are NOT this loop's job: a defect that slipped past a skill you followed
goes to the dream's skill-gap pass.

## Procedure

Create one todo per step.

### 1. Gather candidates

Reflect on the just-finished work. List the concrete, reusable things it surfaced, one sentence
each. Discard task state, anything the repo/git history already records, and anything that only
mattered to this conversation.

### 2. Classify each candidate

| Kind                                                                                            | Home                                                                                                                                 |
|-------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| User correction or working-style directive ("from now on...", "always/never...")                | a `feedback` memory AND, if it must bind future sessions, a CLAUDE.md guardrail line                                                 |
| Recurring process/tooling/environment mistake (wrong command, shell/SSH/OS quirk, stale output) | the project's recurring-error record if it has one (bump count + date), else a `feedback` memory phrased as the check that avoids it |
| Discovery or miss (a re-derived tool/path, a measured timing, a gotcha, a working procedure)    | the most relevant existing `project`/`reference` memory, or a new one                                                                |
| Architecture/topology/data-flow realization                                                     | the right altitude per step 3b; unsure -> ask the user                                                                               |
| A skill was wrong, missing, or mis-triggered                                                    | PROPOSE (step 5); never rewrite an existing skill inline (sole exception: this skill, see the meta-loop)                             |
| Nothing durable                                                                                 | drop it                                                                                                                              |

### 3. Dedup BEFORE writing (mandatory)

Grep the pointer blocks (`CLAUDE.local.md`), the anchor's `facts/` bodies, the native memory dir,
and the CLAUDE.md chain for each candidate's keywords. If a related entry exists, UPDATE it: rerun
the engine `add` with the same slug/title - it upserts (merges provenance, keeps the pin). New
entry only when nothing covers it.

### 3b. Choose the altitude - by SCOPE, placed concretely

- **Per-turn capture writes at the PROJECT level of the CURRENT tree only** (`--proj "<cwd>"`).
  Raising a fact to a higher altitude is the DREAM's job (engine `move`), never capture's - a
  routine capture never touches a parent level or another tree.
- Decide the eventual home by **scope of applicability, not abstractness**: the narrowest level
  that still covers everywhere the lesson applies. Concrete knowledge useful tree-wide belongs at
  the tree's top KEPT CONCRETE. The per-level scope descriptors (the `bitranox:self-learning`
  block) are the routing key; when genuinely unclear, ask the user.
- An intermediate must-hold rule for a whole subtree goes in that level's `CLAUDE.md`
  (propose-first; policy in `bitranox:meta-dream-project`).
- **Normalization, not duplication:** store a general rule ONCE at its altitude; a lower entry
  cites `[[general-slug]]` plus only its delta. References point UPWARD only.
- **Promotion to the tree's top is gated**: user-stated rules promote eagerly; a model-inferred
  generalization needs corroboration across >= 2 dreams (`promotion` config knob).
- **A universal rule can also belong in a SHIPPED skill** (the shared brain; the private store
  teaches only you). If it matches a shipped skill's domain (shell -> `bitranox:compuse-bash`, git
  -> `bitranox:compuse-git`, ...) or warrants a new one, raise the public-contribution option -
  propose-first, scrub private specifics, route via references/upstream-propagation.md. Never let a
  clearly-shippable rule stop silently at the private layer.

### 4. Write it (the engine, fail-loud)

Compose the entry per the specs in references/memory-backend.md:
- **Hook: trigger-first.** `When <situation>, <directive>.` - second person, 1-3 sentences, <= 350
  chars, self-sufficient (keep names/paths/flags/numbers in it). A trigger-less hook never fires
  during reasoning; the engine warns on one.
- **Body: framed prose with reasoning.** The fact, then `**Why:**` and `**How to apply:**` lines
  (the engine adds the frontmatter frame).

Then ONE engine call per fact, and REQUIRE its success line (the printed slug):

    bash <plugin>/hooks/run-python.sh <plugin>/hooks/memory_engine.py add \
      --proj "<cwd>" --type feedback|project|reference|user \
      --title "..." --hook "When ..., ..." --body-file <tmpfile> [--source <key>] [--pin] [--slug s]

Risk ladder: engine `add` at the project level is additive - auto-apply. Rewriting/deleting an
existing entry, restructuring or editing a version-controlled CLAUDE.md, pruning - propose-first
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
  `recurrence: N (last YYYY-MM-DD)` line.
- Count reaches 2: STOP re-wording - prose has failed. Escalate to a DETERMINISTIC guard (a
  PreToolUse/Stop hook via the `update-config` skill, a CI check, or a real code fix; user-gated,
  never auto-created). Guards follow the cross-platform script rules in
  `bitranox:meta-skill-writer`; a globally-useful guard belongs in the shared plugin's `hooks/` and
  MUST propagate upstream - local-only `~/.claude/hooks` is the classic loss.
Memory changes what the model is TOLD; a guard changes what it can DO. A must-hold rule ends in a
guard.

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

## Common mistakes

- Appending a new entry when an existing one should have been updated (bloats the always-loaded
  block).
- A trigger-less hook ("Fix X properly" instead of "When you hit Y, fix X") - it never fires
  mid-reasoning.
- A bare-prose body without **Why:** / **How to apply:** - the model discounts it as inauthentic.
- Hand-editing a pointer block or body (guard-denied; the engine is the only write path).
- Capturing at an ancestor level or another tree - capture is project-level; the dream re-levels.
- Recording session state ("the build is running") as a durable learning.
- Auto-applying a rewrite or delete - additive is auto, destructive is propose-first.
