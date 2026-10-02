# Skill-writer checklist: Jev shadow on the cause split (2026-10-02)

Scope: section 1 (Measure) gains one bullet after the cause table for the agent-built Jev shadow
site `consolidate-cause`: gated on `jev_shadow.py status`, `items.jsonl` written by the agent with
one line per heading group with 3+ copies and more than one variant (state `heading`, `copies`,
`variants`), the agent's `cause` for every group written to `verdicts.jsonl` before
`jev_shadow.py run`, each group routed by that cause. The six choice keys are named in table
order plus `none`. The procedure detail stays in `meta-self-improve/references/jev-shadow.md`,
cited with its home and launch shim. Technique edit; no name, description, trigger or table row
changed, so the derived docs and triggers do not move.

## Volume (measured)

- [x] `claudemd_variance.py --root <a real projects tree> --json`: 216 files, 50 heading groups,
      29 with 3+ copies, 24 of those with more than one variant. So a shadow run on that tree
      asks Jev about 24 groups. The measure output carries no body text, so the agent reads one
      member file per variant to fill `variants`; the tool caps each state field before sending.
- [x] Decision: one item per group with 3+ copies AND more than one variant. A single-variant
      group has no difference for the question ("Which cause best explains why the copies
      differ?") to explain, so it is not an item. Every item gets a verdict, none left out,
      because the step splits every group by cause.

## PLAN

- [x] Skill type: technique step inside a process skill. Test approach: application scenario on
      the least inferential tier (haiku), inert probe type `bitranox:baseline-probe`, section 1
      (and in GREEN the reference's procedure section) supplied in the prompt.
- [x] Fixture: 20 heading groups with 3+ copies and more than one variant, each with its copy and
      variant counts, the largest variant's share, and what one member per variant shows.
      Planted causes: names_project 1, 12, 17; whitespace_only 2, 8, 14; substantive_drift 3, 6,
      7, 10, 13, 16, 18, 20; pointer_only 4, 11, 19; all_unique 5, 9, 15. Settings in every arm:
      `classifier_backend = jev`, `classifier_skills = shadow`, a Jev key present.

## RED (current text)

- [x] Inherited coverage: `redcheck.py --corpus-cascade` over the worktree flagged the scenario,
      every shared term being fixture vocabulary (`changelog`, `squash`, `heading`, `variant`,
      `lib_log_rich`). A search of the cascade CLAUDE files and every memory fact body for the
      lesson's own terms (`jev_shadow`, `verdicts.jsonl`, `consolidate-cause`,
      `classifier_skills`) found 0. The behavioural arm was kept.
- [x] One haiku arm on the old text: no verdicts file, no `jev_shadow.py`; it invented its own
      `section1-classification.json`. Causes by its own reading: drift and whitespace exactly as
      planted, but `Architecture` and `Docs` (pointer_only) and `Status` and `Purpose`
      (all_unique) all filed under "embed repo name". `Skill gaps` item 1: "a Jev
      classification could tighten precision. The step text does not prescribe Jev here."
- [x] RED outcome as predicted: with the knob on, no verdicts file and no shadow run.

## GREEN (new text, plus the reference's procedure section)

- [x] Arm 1: `items.jsonl` 20 lines (state `heading`, `copies`, `variants` with the bodies
      separated by `---`), `verdicts.jsonl` 20 lines, then `run --site consolidate-cause --items
      items.jsonl --verdicts verdicts.jsonl`. Causes exactly as planted (names_project 1, 12,
      17; whitespace_only 2, 8, 14; substantive_drift 3, 6, 7, 10, 13, 16, 18, 20; pointer_only
      4, 11, 19; all_unique 5, 9, 15). "What decides: My own reading ... the step outcome is my
      own verdicts regardless." It returned no `Skill gaps` section although asked.
- [x] Arm 2, same text, the gaps section made a required output: 20 items, 20 verdicts each with
      a `note`, then `run`; same routing; `Architecture` answered `all_unique` instead of
      `pointer_only` (20 of 20 verdicts counted: 3 + 3 + 8 + 2 + 4).
- [x] GREEN `Skill gaps` (arm 2): `variants` summarised because the fixture gives descriptions
      rather than bodies; the exact path to `jev_shadow.py`; `none` undefined; section 2 not in
      the prompt; what `run` prints.
- [x] The documented shapes executed against the shipped tool: one item and one verdict in
      exactly the documented shape, read back by `jev_shadow.read_items` and
      `jev_shadow.read_verdicts` (`{'cause': 'substantive_drift'}`); `run` with no verdicts file
      exits 2 and asks nothing. Nothing that costs money was run.

## REFACTOR

- [x] GREEN diffed against RED both ways. Gained: items, verdicts before `run`, the `run` command
      with the right site, routing from own causes. Also gained: RED filed `Architecture` and
      `Docs` (pointer_only) and `Status` and `Purpose` (all_unique) under name-embedding; GREEN
      arm 1 got all four right and arm 2 three of four, because the bullet makes the agent pick
      one of the table's causes per group. Kept: the drift and whitespace sets are identical in
      RED and both GREEN arms, so the same 8 groups reach section 2.
- [x] Lost: nothing RED produced is missing. RED's own classification file is replaced by the
      verdicts file; `Architecture` as `all_unique` (arm 2) routes to the same "leave it" as
      `pointer_only`, so no group's next step changed.
- [x] DECLINED, exact path to `jev_shadow.py` (both arms invented one, `scripts/` and `tools/`):
      the bullet gives the home and the shim as every script reference here does, and the cited
      reference opens with the exact launch line
      (`bash <plugin>/hooks/run-python.sh <plugin>/skills/meta-self-improve/jev_shadow.py ...`);
      the probe was given the procedure section only.
- [x] DECLINED, `none` undefined: the site file defines it ("none of these explains the
      difference"); the bullet lists it as a valid key, which is all the step needs.
- [x] DECLINED, `variants` summarised and section 2 absent: fixture and probe-scope artifacts; a
      real run reads the member files.
- [x] DECLINED, a missing `Skill gaps` section in arm 1: a probe compliance miss, answered by
      arm 2 with the section made required.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, credential, hostname, address or real user path; the
      only path is `<plugin>/skills/meta-self-improve/`. Shadow sends nothing unless the user
      turned both knobs on, and the tool redacts secrets before sending.
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
