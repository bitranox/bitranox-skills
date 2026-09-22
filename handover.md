# Handover - written 2026-09-22, nothing in flight

## In flight

Nothing. The Jev classifier's first wave shipped as 7.1.0 and the Stop-gate input fix as 7.1.1;
CI green on both (`d0be47d`, `8d45974`).

## Committed, or not

- `bitranox-skills`: `origin/master == 8d45974`, plugin `7.1.1`. The work was done in the linked
  worktree `.claude/worktrees/jev-classifier` (branch `worktree-jev-classifier`); everything in it
  is pushed except this handover commit, and it can then be removed (`wtclean.py jev-classifier`).
- `TODO-JEV.md` at the MAIN checkout root is UNTRACKED on purpose (the user asked for it there): it
  is the design, the TypeSafe docs review and the progress log for the experiment.
- The machine config `~/.claude/.bitranox-memory.json` now has `classifier_backend = jev` and all
  three first-wave sites on `shadow` (user's choice); the key is in `~/.credentials/typesafe.key`.
- The running plugin was 7.1.0 when this was written; 7.1.1 needs `/plugin marketplace update
  bitranox-skills` and `/reload-plugins` before the Stop gate reads its turns correctly.

## Decided, and why - do not reopen

- **Shadow only, off by default, nothing deleted.** User's framing: an option and experiment, not
  a replacement of working code. A site moves to deciding only after a replay shows a win.
- **Data egress:** prompts, the last reply, memory text, and tool output or file contents when a
  site needs them may go to TypeSafe; secrets are replaced with `[REDACTED]`, never a reason to
  skip the call (user, 2026-09-21).
- **Standard-library HTTP (urllib), not httpx2 or typesafe-sdk** (user, after first choosing
  httpx2): hooks run on a bare python3, so a dependency would mean an install step or a uv launch
  per hook.
- **One flat `off|shadow` knob per site** instead of a `classifier_sites` dict: the settings CLI
  validates flat enums. `decide` joins the enum when decide mode exists.
- **The Stop gate's input fix applies to the gate itself, not only the shadow** (user's choice):
  replay over 1,339 interactive turns, 7.7% -> 6.0% firing, +24 typed corrections, -47 matches on
  its own injected feedback.

## Decided against, and why

- A per-site dict config: see above.
- Counting `origin: null` / `entrypoint: sdk-*` prompts as human: the replay showed 244 of 268
  added firings were headless task briefs and teammate messages.

## Still open, untouched

Nineteen items in `OPEN-WORK.md`; the Jev experiment is new at rank 12.

## Lessons for the next nap

- When a Stop hook needs this turn's text, take the reply from the event's `last_assistant_message`
  and the prompt from the last `origin.kind == "human"` record; the last `type: user` record is a
  tool_result (already recorded as a fact at the bitranox-skills level).
- When a first fix to a gate's input widens what it sees, split the new firings by origin before
  shipping; a plain rate hid 244 non-typed prompts among 268.
- tooling: `redcheck --corpus-cascade` flagged a clean scenario on generic shared words
  ("classifier", "commands", "quote"); grep the named files for the lesson's own terms before
  abandoning a RED.
- tooling: in a worktree-isolated session, compound Bash (heredocs, `$VAR` arguments, `cd &&` with
  git) is refused by the worktree guard; put multi-step logic in a scratch script and call it with
  literal paths.

## The exact next action

`OPEN-WORK.md` item 10, the top-ranked USER item, per the ranking rule. Rank 12, the Jev
experiment, follows; its first step is small: confirm a `stop_signal` line appears in
`~/.claude/self-improve-audit/classifier-shadow.jsonl` once 7.1.1 is loaded.

## Files that matter

- `plugins/bitranox/hooks/classifier.py` - the port, shadow child, question sets.
- `plugins/bitranox/hooks/secret_patterns.py` - redaction, shared with repo-gate and recall.
- `plugins/bitranox/hooks/self-improve-gate.py` - `_human_text`, `_last_messages`, the shadow call.
- `plugins/bitranox/hooks/skill-router.py`, `plugins/bitranox/hooks/recall-memory.py` - the other
  two shadow sites.
- `plugins/bitranox/hooks/tests/test_classifier.py`, `test_classifier_sites.py`,
  `test_secret_patterns.py`, `test_self_improve_gate.py` - the fake API lives in `conftest.py`.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

`repo-gate: all checks passed`; 4877 passed at `8d45974`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
