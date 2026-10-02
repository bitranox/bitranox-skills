# Skill-writer checklist: Jev shadow on the exhaustive misplacement audit (2026-10-02)

Scope: step 3b (misplacement audit, every tree) gains one nested bullet that applies
`meta-dream-crosstree` step 4b's Jev shadow bullet (site `crosstree-misplaced`) on EVERY tree
swept, its own files per tree: gated on `jev_shadow.py status`, `items --site crosstree-misplaced
--anchor <anchor>`, the agent's `wrong_tree` verdict for every candidate in `verdicts.jsonl`
before `run`, relocate or reject by its own verdicts, the counts on crosstree's `jev shadow:`
report line (crosstree step 8, which this skill's step 5 runs). The full bullet lives once, in
crosstree 4b; this one names what differs here (every tree) and keeps the same order and the same
"your own verdicts" rule, so the two read consistently. Technique edit; no name, description,
trigger or table row changed.

## Volume (measured)

- [x] Same site and builder as crosstree 4b: on the real tree top `items` wrote 0 items and
      exited 1, matching `--check-misplaced`'s `TOTAL misplaced: 0`. Every candidate is judged
      by the step already, so every item gets a verdict and nothing is cut.

## PLAN

- [x] Skill type: technique step inside a process skill. Test approach: application scenario on
      haiku, inert probe type `bitranox:baseline-probe`, step 3b plus crosstree's 4b (and in
      GREEN crosstree's step 8 and the reference's procedure section) supplied in the prompt.
- [x] Fixture: the crosstree fixture (two trees, 20 candidates in `/work`, 6 genuine misfiles),
      plus `/lab` printing no candidates, so the `items` exit 1 path is exercised. Settings:
      `classifier_backend = jev`, `classifier_skills = shadow`, a Jev key present; mode `auto`.

## RED (current text)

- [x] Inherited coverage: the same `redcheck.py --corpus-cascade` result as the crosstree
      scenario (fixture and function vocabulary only); the lesson's own terms occur 0 times in
      the cascade and the fact bodies. The behavioural arm was kept.
- [x] One haiku arm on the old text: no items, no verdicts file, no `jev_shadow.py`. Six facts
      relocated, 14 retained; report: "/lab checked (0 candidates); /work checked (20
      candidates, 6 relocated, 14 retained)". It gave neither a file list nor exact commands, and
      no `Skill gaps` section, although all three were asked for.
- [x] RED outcome as predicted: with the knob on, no verdicts file and no shadow run.

## GREEN (new text, plus crosstree 4b and 8 and the reference's procedure section)

- [x] Arm 1: `items --site crosstree-misplaced --anchor /work` through the shim, `verdicts.jsonl`
      20 lines quoted in full (6 `true`, 14 `false`; 20 lines counted), `run`, six `relocate`
      commands, and "Skip /lab tree (no candidates; jev_shadow.py items would exit 1)". Report:
      `jev shadow: crosstree-misplaced /work 20 candidates, 6 relocated to /lab, 14 confirmed
      cross-tree refs; /lab no candidates` - its own counts on the shadow line.
- [x] Arm 2, after the step 8 fix, with `run`'s printed line in the fixture: `items`, 20
      verdicts (7 `true`), `run`, seven `relocate` commands. Report: `jev shadow:
      crosstree-misplaced /work 20 items, 20 paired, 17 of 20 answers agreed, 0 without a Jev
      answer, $0.0009`, then "Relocated: 7 items to /lab" and "Kept in /work: 13 items" on lines
      of their own. Quote-back of the governing sentence came from crosstree step 8 verbatim.
- [x] GREEN `Skill gaps`: the `relocate` syntax (arms 1 and 2); `status` not run explicitly (1,
      2); where the files live (1); what counts as a legitimate cross-tree reference (1); fact
      bodies absent from the fixture (2); which items Jev disagreed on (2).

## REFACTOR

- [x] GREEN diffed against RED both ways. Gained: items per tree, verdicts before `run`, `run`,
      the `items` exit 1 path taken for the empty tree, the shadow line. Kept: the six lab facts
      relocated, the rejected candidates reported beside the moved ones.
- [x] Lost: arm 2 relocated `webshop-tls-ca` ("Lab CA resource, not webshop-specific fact"),
      which RED and arm 1 kept. The hook is about webshop nginx, so arm 2 misjudged it; arm 1 and
      the crosstree GREEN arm kept it on the same text, so it is run variance on the existing
      question, not displaced by the edit.
- [x] CLOSED, report line (crosstree step 8, which this skill's step 5 runs): own counts on the
      shadow line in arm 1; fixed in crosstree step 8 and re-tested in arm 2, which put `run`'s
      counts on the line and its own counts on separate lines. It wrote the empty `/lab` tree on
      a separate line rather than as `crosstree-misplaced /lab no candidates`; the example in
      step 8 shows that form, and nothing is lost either way.
- [x] DECLINED, `relocate` syntax, `status`, and disagreements: as in the crosstree checklist -
      `--check-misplaced` prints the exact `relocate` command, `run` itself is a no-op with
      shadow off, and disagreements are read afterwards with `report`.
- [x] DECLINED, fact bodies and file locations: fixture and probe-scope artifacts.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, credential, hostname, address or real user path.
- [x] Added lines ASCII only and within 100 columns.
- [x] No session narrative or scratch path in the skill text or this artifact.
