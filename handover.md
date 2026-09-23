# Handover - written 2026-09-23, nothing in flight

## In flight

Nothing. Five versions shipped and CI-green on their own shas: 7.6.0, 7.7.0, 7.8.0, 7.8.1, 7.9.0
(`5444cb6`). The worktree is clean and level with `origin/master`.

## Committed, or not

- Everything is on `origin/master`. Work was done in `.claude/worktrees/jev-classifier`; it can be
  removed (`wtclean.py jev-classifier`) and the main checkout pulled.
- `TODO-JEV.md` at the MAIN checkout root stays untracked on purpose (user's choice); its Progress
  section was NOT updated - the state is in the `OPEN-WORK.md` rank-12 line.
- Machine config unchanged: `classifier_backend = jev`, all three sites `shadow`. Key:
  `~/.credentials/typesafe.key`. No site has left shadow, and nothing decided here changes what a
  live session sees.

## Decided, and why - do not reopen

- **A path contributes only its file TYPE to a keyword matcher.** Dropping paths whole cost one
  genuine match in 3,483 typed prompts (a `defaultconfig.toml` request losing `files-edit-toml`);
  keeping the basename recovered it and admitted two false firings. The extension recovered it and
  admitted nothing.
- **`endorsement` is logged but never counted as a Stop-gate firing.** 12 of 12 firings across two
  windows were plain approvals ("yes", "go", "lets try 1-4").
- **Each classifier site is judged at its own threshold** (stop_signal 0.7, skill_router 0.7,
  recall_rerank 0.8). One number for three sites was always a placeholder.
- **A heredoc body gets the `_ANY_TOOL_RULES` pass, and the command reading keeps precedence.** Do
  not instead un-blank bodies for the command rules: blanking exists so a document naming a chore
  cannot trip the guard watching for it.
- **`jig_probe` asks one question per call, not a gate plus a choice.** The router's gate shape did
  not transfer.

## Decided against, and why

- **Reading a task notification's output FILE** into the classifier state. Its path comes from the
  turn's own text, so a forged envelope could name any file on the machine and have it sent to the
  API. The summary already says whether the task failed.
- **A live Jev jig-suggestion site, for now.** The offline probe answers the same question for no
  session tokens, and it had to be built first anyway to know whether such a site would have
  anything to say.
- **Tuning the probe's judge until it matched my hand labels.** It disagreed on 2 of 9, both
  defensible readings; fitting it to my expectations would have measured me rather than it.

## Still open, untouched

Twenty-one items in `OPEN-WORK.md`. Ranks 5 and 112 were closed here; 115 and 117 are new.

## Lessons for the next nap

- When you change the ARM a comparison is measured against, give it its own view tag, or old and new rows pool silently under an unchanged one.
- When you copy a gate question to another site, check the gate's own exclusion does not describe that site's subject - "ordinary use of a normal program" described `pgrep` exactly, and scored the control 0.12.
- When you measure a hook's regex arm offline, drive it through the hook's own pure seams, never its private rule lists - raw matching is a more trigger-happy matcher than the one that ships.
- When a test asserts concurrency with a wall-clock bound, assert the server's observed overlap instead; a clock bound races the machine's load and says nothing about concurrency.
- When a backlog line prescribes a fix, verify its premise before implementing it - "add a rule" was impossible, because the hook blanks heredoc bodies by design.
- When a path is the SUBJECT of a request rather than incidental to it, stripping it is a loss; the file type is the part that carries the subject.
- tooling: a version bump here touches two files (`plugin.json` and `pyproject.toml`) and has no command; three per-version scripts got written before one was parameterised.

## The exact next action

`OPEN-WORK.md` rank 10, the top-ranked open item: the user's "review all skills and scripts one by
one, each in its own subagent and ask when smth is to change". Its blocker comes first - `TRIAGE.md`
is the only record of the 17 unadjudicated guard-slice claims and the 5 coverage gaps, and it
survives ONLY in two hand-made ZFS snapshots
(`/media/srv-main-softdev/.zfs/snapshot/pre-bose-zonemaster-move-2026-09-11/projects/public/KI/scriptwave-2026-08-28/TRIAGE.md`).
Put it somewhere durable, then ask which bucket goes next.

## Files that matter

- `plugins/bitranox/hooks/prompt_text.py` - `typed_by_a_person`, `prose`, `scorable_prose`, `notification_fields`.
- `plugins/bitranox/hooks/shell_text.py` - `_split_heredocs`, `heredoc_bodies`, `strip_heredoc_bodies`.
- `plugins/bitranox/hooks/toolbox-nudge.py` - `match_authored`, `_ANY_TOOL_RULES`, the second reading in `main`.
- `plugins/bitranox/hooks/skill-router.py` - `match`, `_turn_fields`, `MATCHER_VIEW`.
- `plugins/bitranox/hooks/classifier.py` - `_ROUTER_TURNS`, `skill_router_questions(turn=)`, `NOTIFY_VIEW`.
- `plugins/bitranox/skills/meta-self-improve/jig_probe.py` and `classifier_eval.py` - `SITE_THRESHOLDS`, `NON_FIRING_FAMILIES`.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py report
```

`repo-gate: all checks passed` with 4994 passed. The report names the threshold each site was
judged at, and router rows logged from 7.7.0 on carry `matcher_view: prose-v1`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
