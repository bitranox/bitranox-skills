# checklist-20261011-fanout-fold

Change under test: step 1 (capture first) gains a fan-out clause. When the capture is dispatched
to subagents, each brief names `factedit.py apply` (home: `skills/meta-dream-tree/`) as the only
way to fold a delta into an existing fact, and assigns a fold target shared by two batches to ONE
batch (or folds it sequentially after a fresh `show`).

## PLAN

- [x] Skill type: technique (one procedure step gains a rule). Test approach: application - write
      the brief for three parallel capture agents that update overlapping facts.
- [x] Scope: one clause in step 1; no new file, no script. The subcommands and flags named in the
      clause were read from `factedit.py --help`, `apply --help` and `show --help` (`show --body`
      prints the body; `apply` takes `--slug`, `--body-file`, `--hook-file`, `--type`).

## RED

- [x] Pre-change text, sonnet and haiku baseline-probe: both briefs told each agent to write with
      `memory_engine.py add`; neither named `factedit.py`. Sonnet partitioned candidates by target
      fact, haiku by owning level, but neither brief required a re-read before a fold. Both
      reported "Skill gaps": the text is silent on partitioning for fan-out and on same-fact
      collisions between parallel agents.

## GREEN

- [x] Post-change text, sonnet and haiku baseline-probe: both briefs name `factedit.py apply` with
      the real flags, a `show --body` before each fold, and a shared target owned by one batch.
      Quote-back: both quoted rule (a) for the fold method and rule (b) for the shared target,
      neither answered NONE. Nothing the RED briefs did was lost (both still resolve the owning
      level from the pointer and use mktemp scratch dirs).

## REFACTOR - every gap closed or declined

- [x] GAP: how a new fact's level is chosen when no candidate names one. DECLINED: outside this
      change; owned by `meta-self-improve`.
- [x] GAP (GREEN): who detects the overlap and partitions. DECLINED: the dispatching agent does it
      before dispatch; rule (b) states the outcome, and both GREEN briefs placed it there.
- [x] GAP (GREEN): behaviour when `apply` refuses a slug. DECLINED: owned by `factedit.py`'s own
      error output, which the brief tells the agent to report.
- [x] GAP: who commits after a fan-out. DECLINED: owned by the nap's later steps and the core.

## Quality

- [x] Description unchanged. No narrative, scratch paths or addresses added.
