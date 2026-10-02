# Jev shadow for skill judgment sites (the shared procedure)

Several skill steps make one bounded judgment over many items: is this guard firing real, is this
memory note a stale negative claim, which level does this fact belong at. In shadow mode the agent
running the step still decides every item itself, exactly as the step says. Jev (TypeSafe's
classifier, reached through the published `jev-judge` CLI) answers the same questions about the same
items beside it, and both answers are logged per item. The log is the evidence for a later decision
on whether Jev could take a step over. Shadow never changes what the step does.

Each skill step that has a shadow site cites this file. The tool is
`<plugin>/skills/meta-self-improve/jev_shadow.py`, launched with `hooks/run-python.sh`:

```bash
bash <plugin>/hooks/run-python.sh <plugin>/skills/meta-self-improve/jev_shadow.py <command> ...
```

## When it runs

| Setting                                   | Default      | Effect when set                                               | Who changes it and when                    |
|-------------------------------------------|--------------|---------------------------------------------------------------|--------------------------------------------|
| `classifier_backend = jev`                | `off`        | Master switch for every Jev site, hooks and skills            | The user, through `meta-memory-settings`   |
| `classifier_skills = shadow`              | `off`        | The skill sites below run their shadow step                   | The user, through `meta-memory-settings`   |
| A Jev key (`jev-judge check-key` exits 0) | none         | Without one, shadow stays off and nothing is logged           | The user, per the `ai-llm-jev-judge` Setup |
| `classifier_model`                        | `jev-latest` | Passed to jev-judge as `--model`; empty lets jev-judge choose | The user, through `meta-memory-settings`   |

Shadow runs only with BOTH knobs on and a key present. Turning it on is the user's consent to send
these items (memory facts, commands, code lines) to TypeSafe; secrets are redacted before sending.
With either knob off, no `uvx` on PATH, or no key, `run` prints `shadow: off (<reason>)`, exits 0
and writes nothing. `status` answers the same question without running anything that costs money.

Shadow runs whatever the item count. The ~50-item floor in the `ai-llm-jev-judge` skill is for
letting Jev DECIDE; calibration data from a small batch is still data.

## The procedure, for every site

1. **Items.** For a store-based site, build them:
   `jev_shadow.py items --site <site> --anchor <tree anchor> --out items.jsonl`
   (`guard-firing` takes `--firings <guard_replay --firings output> --hazard "<what the guard
   warns about>"` instead of `--anchor`). For an agent-built site, write `items.jsonl` yourself:
   one `{"id": ..., "state": {...}}` per line, the state carrying EXACTLY the site's fields (table
   below), each a string; a null is sent and logged as an empty field. `run` refuses any other
   field set, and an empty items file asks nothing and exits 0.
2. **Judge every item yourself**, as the step says, and write `verdicts.jsonl`, one line per item
   you judged:
   `{"id": "<item id>", "verdict": {"<question id>": <answer>}, "note": "<one line why, optional>"}`.
   A noul answer is `true` or `false`, a choice answer is one of its keys, a score answer is the
   level's index (0 for the first level). Unless the step asks for a verdict on every item, you
   may leave items or questions out; nothing is paired for them, and an empty verdict `{}` counts
   as no verdict. A missing verdict loses only the pairing: `run` still asks Jev about, and pays
   for, EVERY line in `items.jsonl`. To keep an item from being asked, delete its line from
   `items.jsonl` (unchanged otherwise) BEFORE `run`.
3. **Then ask Jev:**
   `jev_shadow.py run --site <site> --items items.jsonl --verdicts verdicts.jsonl`.
   It prints counts only: items, paired, answers agreed, items without a Jev answer, cost.
4. **Carry on with the step on your own verdicts.** Whatever `run` printed or exited with, the
   step's outcome is yours. A non-zero exit is reported in the step's output in one line and
   changes nothing else.

The verdicts file must exist BEFORE `run`; without it `run` exits 2 and asks nothing. That and the
counts-only output keep the agent blind: knowing which items Jev disagreed on mid-task would pull
the agent's own judgments toward Jev's, and the comparison would measure nothing. Read the
disagreements afterwards, with `report`. With `--workdir`, jev-judge's `rows.jsonl` stays there:
do not open it until your own step is finished, for the same reason.

## Sites

| Site                  | Skill step                                         | Items                                               | State fields                                 | Questions (type)                                    |
|-----------------------|----------------------------------------------------|-----------------------------------------------------|----------------------------------------------|-----------------------------------------------------|
| `guard-firing`        | compuse-toolbox, guard_replay classify-all         | `items --firings F --hazard TEXT`; id = tool_use id | `hazard`, `command`, `error`                 | `real_hazard` (noul)                                |
| `quality-polarity`    | enhance-code-quality, "Cap it when sites are many" | agent-built; id = `file:line`                       | `function`, `source_line`, `convention`      | `agrees` (noul)                                     |
| `quality-param-hit`   | enhance-code-quality, "Resolve each hit"           | agent-built; id = `file:line`                       | `parameter`, `hit`, `context`                | `is_parameter` (noul)                               |
| `dream-prune`         | meta-dream-tree step 7                             | `items --anchor`; id = slug                         | `hook`, `body`                               | `untestable_negative`, `unlabelled_unsolved` (noul) |
| `dream-firing`        | meta-dream-tree step 6                             | `items --anchor`; id = slug                         | `hook`, `body`                               | `trigger_fires` (noul)                              |
| `crosstree-misplaced` | dream-crosstree 4b, dream-crosstree-deep 3b        | `items --anchor`; id = slug                         | `hook`, `body`, `level_scope`, `cited_paths` | `wrong_tree` (noul)                                 |
| `data-arch-dict`      | enforce-data-architecture-strict STEP D            | agent-built; id = `file:line`                       | `hit`, `context`                             | `real_violation` (noul)                             |
| `dream-placement`     | meta-dream-tree step 5                             | `items --anchor`; id = `slug\|level`                | `hook`, `body`, `level_scope`                | `fits_level` (score, 3 levels)                      |
| `consolidate-cause`   | meta-consolidate-claude-md step 1                  | agent-built; id = section group                     | `heading`, `copies`, `variants`              | `cause` (choice, 5 causes plus `none`)              |
| `collect-relevance`   | meta-collect-knowledge stage 2                     | agent-built; id = candidate path                    | `project`, `candidate`                       | `useful_here` (noul)                                |

The questions themselves are in `jev_sites/<site>.json` beside the tool: `{"site", "version",
"questions", "state_fields"}`, the questions in jev-judge's format. A question names a state field
only as a backticked name, and every backticked name is a state field (a test holds both
directions). Change a question by editing its file and bumping that file's `version`; each log
record carries the version and a hash of the questions (`questions_sha`), and `report` keeps
every sha apart, so records from different wordings never pool.

`dream-placement` pairs each fact with every curated level on its own chain: its level, the levels
above it up to the anchor, and the levels below it. The level id is the level's path relative to
the anchor (`.` for the anchor). Pick the best level per fact in code; Jev scores each pair alone.

## What is logged

One record per item in `~/.claude/self-improve-audit/jev-skill-shadow-YYYY-MM.jsonl`, appended
under the memory lock: `ts`, `run_id`, `site`, `site_version`, `questions_sha`, `plugin_version`,
`jev_judge_version`, `model`, `cwd`, `git_head` (of the cwd, or null), `item_id`, `state`,
`redactions`, `jev` (`{question id: {type, value, probabilities, confidence}}`, or null),
`jev_reason` (why there is no Jev answer), `agent` (the verdict, or null when there is none or
it is empty), `agent_note`, `agree`, `latency_ms`, `input_tokens`, `cost_usd` (this item's
share of the run). Each Jev answer keeps the `type` jev-judge reported, so `report` types an
older wording from it; records logged before answers carried a type are typed from their
answers' shape.

A noul answer carries its probability in `value` and logs `probabilities` and `confidence` as
null: those two belong to choice and score answers, so a null there is not missing data.

`state` is what was SENT: each field redacted (`classifier.prepare_state`) and capped. Keeping it
lets a later, better question be replayed over logged items without re-running the skill.

`agree` holds one entry per question: a noul compares the agent's bool with Jev's probability at
0.5, a choice compares keys, a score compares the agent's index with Jev's score rounded half up to
the nearest level. It is null when either side has no answer.

Retention: on every append, months whose last day is more than 400 days ago are deleted, then the
oldest months while the rest exceed 100 MB. The current month is never deleted. Skill sites fire
weekly at most, so the hook shadow's 30 days would throw the evidence away.

## Reading it back

```bash
jev_shadow.py report [--site S] [--since YYYY-MM-DD] [--disagreements OUT.jsonl] [--json]
```

Per site, per questions sha (`questions_sha`), per question: items, paired items, agreement among
the paired, the agent-by-Jev confusion counts, the share of Jev answers inside the uncertainty band
(a noul strictly between 0.2 and 0.8, a choice or score with confidence below 0.6), agreement with
the band excluded, and cost per site and per sha.

Every sha is reported separately, oldest first, marked `current` when it matches today's site
file. Only the current sha takes its question types and score levels from the site file; an
older sha takes them from its own logged answers, so a question whose type changed is reported
as what it was when it was asked. Compare a question across wordings by reading the shas side
by side, never by adding them up.

`FLAT` marks a question whose Jev answers barely vary: a standard deviation below 0.05 for a noul
or score, or one choice taking 95% or more, over at least 5 answers. A constant answer is a broken
instrument, not consensus; fix the question before reading its agreement.

`--disagreements` writes every paired item where any question disagrees, with its state, for
reading by hand. Either side can be the wrong one; deciding which is the point.

## Exit codes and output

| Command  | 0                                                  | 1                             | 2                                                                                     |
|----------|----------------------------------------------------|-------------------------------|---------------------------------------------------------------------------------------|
| `status` | a run would happen                                 | it would not (reason printed) | usage error                                                                           |
| `items`  | items written                                      | none built (empty file)       | unknown site, agent-built site, missing source                                        |
| `run`    | records logged, shadow off, or an empty items file | logged, but Jev answered none | missing verdicts file, malformed items or verdicts, unwritable log, workdir or output |
| `report` | records summarized                                 | no records match              | bad `--since`, unwritable `--disagreements`                                           |

`--json` prints `{ok, command, data, skipped}` on stdout; diagnostics go to stderr.
