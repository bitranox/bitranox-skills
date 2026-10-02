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

## Final-review fixes (2026-10-02)

Scope: the shadow bullet put `items.jsonl` and `verdicts.jsonl` in a fresh
`D=$(mktemp -d)` outside any repo, and end the command sequence with `rm -rf "$D"` after `run`,
because both files hold unredacted text and redaction happens only inside `run`. Every path in
the bullet reads `$D/...`, and the counts sentence names `run` ("`run` prints counts only") so it
cannot be read as the `rm`. The shared detail (why, one dir per site and per tree, delete after
the counts are taken) lives once in meta-self-improve's `references/jev-shadow.md`, procedure
step 0.

- [x] RED (meta-dream-tree step 6 bullet, the representative one, haiku, inert probe): on the
      text before this change the arm wrote `--out /work/acme-app/items.jsonl` and
      `/work/acme-app/verdicts.jsonl` into the project checkout and reported "Both .jsonl files
      remain in /work/acme-app/". Its own gap list: "Post-step file cleanup policy not stated;
      files left in working directory."
- [x] GREEN 1 (same scenario, a first draft with the `rm` in the bullet's opening parenthetical,
      plus procedure step 0): ran `D=$(mktemp -d)`, wrote `/tmp/tmp.Qx7/items.jsonl` and
      `/tmp/tmp.Qx7/verdicts.jsonl`, ran `run` on those paths, then `rm -rf /tmp/tmp.Qx7`.
- [x] REFACTOR: a data-arch-dict arm on that same draft, given the bullet alone, used the temp
      dir but kept it ("Both retained for audit trail"): a cleanup stated up front in a
      parenthetical is skipped by a reader acting step by step. The `rm` moved to the end of the
      sequence, after `run`, in every bullet.
- [x] GREEN 2 (final text, the step 6 bullet ALONE, without procedure step 0): `D=$(mktemp -d)`,
      both files under `/tmp/tmp.Qx7`, `run` on them, then `rm -rf /tmp/tmp.Qx7`; "The
      directory and all its contents no longer exist when step 6 completes." The data-arch-dict
      arm on the final text likewise ended with `rm -rf /tmp/tmp.K2p`.
- [x] Remaining gaps (where to read a hook's text, whether to inspect items.jsonl, how much
      `context` is enough) are pre-existing judgement in the steps, untouched here: DECLINED.
- [x] Every bullet in this skill checked by grep: no `--out items.jsonl`, `--items items.jsonl`
      or bare `verdicts.jsonl` left.
- [x] Diff reviewed: prose only, ASCII, no secret, address, hostname or real user path.
