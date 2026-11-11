# meta-dream-tree: what `set-scope` keeps of a descriptor it replaces

Scope: one clause in `SKILL.md` (the verify step after the descriptor fan-out) and the same clause
in `references/dream-core.md` ("Verify every parallel WRITE fan-out"). Both said `set-scope`
overwrites unconditionally. The engine keeps a stored `TOPICS:` line when the new text has none,
so both now say it replaces a level's descriptor text without asking and keeps only a stored
`TOPICS:` line. The instruction that follows (verify the fan-out from ground truth, keep each
agent's returned text) is unchanged.

## Step 0b

- [x] `skill_decisions.py show meta-dream-tree --kind rejected,removed --full`: one rejected entry
      (d-20261106-7121104c, re-running ref_map after a dropped move). Unrelated.
- [x] `skill_decisions.py show meta-dream-tree`: seven live rules; none anchors on the changed
      clause, and `skill_decisions.py check` reports 0 findings after the edit.
- Decisions: none - corrects one factual clause about the engine, adds and removes no rule

## Accuracy against the engine (run, not assumed)

- [x] `memory_engine.py` `scope_keeping_topics`: with a stored `TOPICS:` line and a new text
      without one, the stored line is carried over. Run on a scratch tree: a level tagged
      `TOPICS: python, uv`, then `set-scope` with a two-line text without the line, printed
      `scope updated:` and the block read `WHAT: ...`, `STACK: ...`, `TOPICS: python, uv`.
- [x] The hazard the sentence warns about still holds: `set-scope` asks nothing and checks no
      level identity, so a wrong `--proj` replaces a sibling's `WHAT`/`STACK`/`CHILDREN`/`PLACE-*`
      lines.

## RED / GREEN

Question: "A level's descriptor holds several lines, one of them `TOPICS: python`. A subagent runs
`set-scope` on that level with a new descriptor text that has no TOPICS line. According to this
text, what is left of the old descriptor afterwards? Quote the governing words verbatim, or
answer NONE." Text-only probes (no file or shell tools), the paragraph pasted in.

- [x] RED (`opus`, pre-edit paragraph): quoted "`set-scope` overwrites unconditionally" and
      answered that nothing of the old descriptor is left, with NONE for whether the `TOPICS:`
      line survives. The pre-edit text leads to the wrong belief.
- [x] GREEN (`opus` and `haiku`, new paragraph, 2 cells): both answered that only the `TOPICS:`
      line survives and quoted "`set-scope` replaces a level's descriptor text without asking (it
      keeps only a stored `TOPICS:` line)". Control question (does the text still tell you to
      verify the fan-out against what each agent returned): both quoted "diff each level's
      on-disk descriptor against what its own agent RETURNED".
- [x] GREEN against RED in both directions: nothing the RED answer held is missing from GREEN;
      the verify instruction is quoted by both GREEN cells.

## Skill gaps the probes reported

- What happens when the new text carries its own `TOPICS:` line: DECLINED, covered elsewhere.
  `meta-self-improve/references/memory-backend.md`, "Store format": "It refuses a text that
  carries a different `TOPICS:` line or adds one to a level that has none". The dream step writes
  descriptors from a fixed template that has no such line.
- Where the kept line goes, what "stored" means, where the backup lives, how to restore, what the
  freshness check is, what "ground truth" names: DECLINED, the probe saw one paragraph. The
  freshness gate is the step the paragraph belongs to (`SKILL.md` step 0b, "Scope-descriptor
  synthesis (freshness-gated, parallel opus subagents)"), the backup is step 2 ("Back up +
  manifest", `store_manifest.py backup`), and the verify rule is `references/dream-core.md`,
  "Verify every parallel WRITE fan-out from ground truth". None is touched by this change.

## Checks a probe cannot see

- [x] Width and fence check over the added lines of both files: nothing reported after the
      `dream-core.md` paragraph was reflowed.
- [x] The sentence after each insertion point still refers to the same thing (the wrong `--proj`
      clobber).
- [x] ASCII only; no host, path or project name added.

## Follow-up 2026-11-12: neutral names in the fan-out example

- [x] `references/dream-core.md`, "Verify every parallel WRITE fan-out": the observed clobber
      named two directories of a private tree; it now names `projects/` and `infra/`. The meaning
      is unchanged (one agent wrote a level's descriptor into a sibling level).
- [x] Width check over the reflowed lines (none over 100 columns); ASCII only; the sentence after
      it still continues "After ANY such fan-out".
- Decisions: none - replaces two example names, changes no rule
