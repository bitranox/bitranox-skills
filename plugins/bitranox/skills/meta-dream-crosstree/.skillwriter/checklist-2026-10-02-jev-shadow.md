# Skill-writer checklist: Jev shadow on the misplacement audit (2026-10-02)

Scope: step 4b (misplacement audit) gains one nested bullet for the store-based Jev shadow site
`crosstree-misplaced`: gated on `jev_shadow.py status`, items built per tree with
`jev_shadow.py items --site crosstree-misplaced --anchor <anchor>` (one line per
`--check-misplaced` candidate, `items` exit 1 meaning no candidates and no `run`), the agent's
`wrong_tree` verdict for every candidate written to `verdicts.jsonl` before `jev_shadow.py run`,
relocate or reject taken from those verdicts. Step 8 (report) gains the `jev shadow:` line the
family verification contract in `meta-dream-tree/references/dream-core.md` already requires for
the crosstree variants: `crosstree-misplaced <anchor> <counts>` per tree, plus the `off`,
`no candidates` and `error` forms. `meta-dream-crosstree-deep` step 3b cites this bullet (its own
checklist). The procedure detail stays in `meta-self-improve/references/jev-shadow.md`, cited with
its home and launch shim. Technique edit; no name, description, trigger or table row changed, so
the derived docs and triggers do not move.

## Volume (measured, `items` is read-only and free)

- [x] `jev_shadow.py items --site crosstree-misplaced --anchor <the real tree top>` wrote 0 items
      and exited 1; `reconcile_memory_index.py --check-misplaced` on the same anchor printed
      `TOTAL misplaced: 0`, so the two agree. Shadow costs nothing on a clean tree and a few
      items when facts are misfiled.
- [x] Decision: a verdict for EVERY candidate, none left out, because the step already judges
      every candidate ("JUDGE each candidate against its body before acting"). No cut of
      `items.jsonl` is needed: every line is judged.

## PLAN

- [x] Skill type: technique step inside a process skill. Test approach: application scenario on
      the least inferential tier (haiku), inert probe type `bitranox:baseline-probe`, step text
      (and in GREEN the reference's procedure section) supplied in the prompt.
- [x] Fixture: two trees (`/work` with three levels, `/lab` with one) and 20 `--check-misplaced`
      candidates filed in `/work` whose cited paths are all under `/lab`: 6 genuinely about the
      lab (`proxmox-zfs-arc-cap`, `lab-dns-override`, `pbs-prune-schedule`, `lab-vlan-trunk`,
      `lab-grafana-dashboards`, `lab-ups-shutdown`), 14 about a work project that only uses a lab
      resource. Settings in every arm: `classifier_backend = jev`, `classifier_skills = shadow`,
      a Jev key present; mode `auto`.

## RED (current text)

- [x] Inherited coverage: `redcheck.py --corpus-cascade` over the worktree flagged the scenario,
      every shared term being fixture or function vocabulary (`backup`, `cloning`, `firewall`,
      `assume`, `modprobe`). A search of every CLAUDE.md and CLAUDE.local.md on the chain and
      every memory fact body for the lesson's own terms (`jev_shadow`, `verdicts.jsonl`,
      `crosstree-misplaced`, `classifier_skills`) found 0, against a control term found 30
      times. The behavioural arm was kept.
- [x] One haiku arm on the old text (step 4b and step 8): no items, no verdicts file, no
      `jev_shadow.py` command. Seven `relocate` commands (the six lab facts plus `work-ci-cache`),
      13 rejected, decided by its own reading. Report: "Misplacement audit (step 4b): 20
      cross-tree candidates scanned ... 7 facts relocated ... 13 rejected". `Skill gaps`: the
      `relocate` syntax is not in the step text.
- [x] RED outcome as predicted: with the knob on, no verdicts file and no shadow run.

## GREEN (new text, plus step 8 and the reference's procedure section)

- [x] Arm 1: `jev_shadow.py items --site crosstree-misplaced --anchor /work --out items.jsonl`,
      `verdicts.jsonl` 20 lines (6 `true`, 14 `false`, a `note` each), then `jev_shadow.py run
      --site crosstree-misplaced --items items.jsonl --verdicts verdicts.jsonl`, then six
      `relocate` commands for the six lab facts. "Facts are filed by their triggering event's
      tree, not by the location of the resource they reference." Report line: `jev shadow:
      crosstree-misplaced /work items=20, paired=20, agreed=14, jev_absent=0, cost=$X; 6
      relocated, 14 kept` - counts it could not have seen, and its own relocate counts on the
      shadow line (see REFACTOR).
- [x] GREEN `Skill gaps` (arm 1): `status` not run explicitly ("assumed it exits 0"); what to do
      on a disagreement; the shape of `run`'s output.
- [x] Step 8 after the fix, verified through the deep skill's arm 2 (which is given this step 4b
      and step 8 verbatim, with `run`'s printed line in the fixture): `jev shadow:
      crosstree-misplaced /work 20 items, 20 paired, 17 of 20 answers agreed, 0 without a Jev
      answer, $0.0009`, the relocated and kept counts on lines of their own; quote-back of the
      governing sentence: "and `jev shadow:` followed by `crosstree-misplaced <anchor> <counts>`
      per tree, joined by `; `: the counts are what `run` printed after its own `shadow:`
      prefix". It wrote the `/lab` tree's "no candidates" on a separate line rather than as a
      second entry on the shadow line.
- [x] The documented shapes executed against the shipped tool: one item and one verdict in
      exactly the documented shape, read back by `jev_shadow.read_items` and
      `jev_shadow.read_verdicts` (`{'wrong_tree': True}`); `run` with no verdicts file exits 2
      and asks nothing; `items` on an anchor with no candidates exits 1. Nothing that costs money
      was run.

## REFACTOR

- [x] GREEN diffed against RED both ways. Gained: items, verdicts before `run`, the `run` command
      with the right site, the shadow line in the report. Kept: the six lab facts relocated in
      RED and in every GREEN arm.
- [x] Lost: RED also relocated `work-ci-cache`, GREEN did not. Not a loss: that fact is about a
      work repo's CI ("When a work repo's CI runs out of disk") and only uses a lab cache path,
      the planted not-a-misfile shape; the deep RED arm on the same fixture kept it too.
- [x] CLOSED, report line: arm 1 put its own relocate counts on the shadow line. Step 8 now says
      "Your own relocated and rejected counts go on a line of their own, never on this one" and
      gives an example with two trees. Re-tested (deep arm 2, above): run's counts on the line,
      relocate counts on their own lines.
- [x] DECLINED, `status` not run explicitly: the bullet gates on it; with shadow off `run` itself
      prints `shadow: off (<reason>)`, exits 0 and writes nothing, so a skipped `status` costs at
      most an `items` call.
- [x] DECLINED, disagreement handling: nothing changes on a disagreement and the bullet says so
      ("whatever `run` printed or exited with"); disagreements are read afterwards with
      `report`, per the reference.
- [x] DECLINED, the `relocate` syntax (RED and GREEN): `--check-misplaced` prints the exact
      `relocate` command per candidate, as step 4b already says; the probe saw candidates only.
- [x] Noted, run variance: the deep skill's arm 2 also judged `webshop-tls-ca` a misfile, which
      four other arms on either text kept; a judgement on the existing question, not an
      instruction gap.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, credential, hostname, address or real user path; the
      example anchors are the fixture's `/work` and `/lab`. Shadow sends nothing unless the user
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

Also: step 8's `jev shadow:` report line uses the four shared forms; `no candidates` is now
`no items`, the form every site uses, and the definition lives once in `references/jev-shadow.md`
"The report line".

- [x] Quote-back (haiku) on step 8 plus "The report line": `crosstree-misplaced /work error ...`
      for a `run` exit 2 and `crosstree-misplaced /lab no items` for an `items` exit 1, each with
      its governing row quoted.

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
