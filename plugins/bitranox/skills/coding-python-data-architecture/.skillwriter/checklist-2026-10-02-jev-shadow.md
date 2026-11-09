# Skill-writer checklist: Jev shadow on STEP D final verification (2026-10-02)

Scope: STEP D - FINAL VERIFICATION gains one bullet, inserted between the grep-candidates bullet
and the "If a real violation is found" branch. It is gated on `jev_shadow.py status`, builds
`items.jsonl` itself (agent-built site, one `{"id": "<file:line>", "state": {"hit", "context"}}`
per grep hit), writes a verdict for every hit to `verdicts.jsonl` BEFORE `jev_shadow.py run --site
data-arch-dict`, and takes the step's outcome from those verdicts regardless of what `run` printed
or exited with. The procedure detail stays in `meta-self-improve/references/jev-shadow.md`, cited
with its home and launch shim. Technique edit; no name, description, trigger or table row changed.

## PLAN

- [x] Skill type: technique step inside a verification loop. Test approach: application scenario
      on the least inferential tier (haiku), inert probe type `bitranox:baseline-probe`, step text
      and the cited reference procedure supplied in the prompt.
- [x] Scenario: STEP D with 20 `: dict`/`-> dict` grep hits, `classifier_backend = jev` and
      `classifier_skills = shadow` both on, a Jev key present. Asked for files written (with
      example lines), commands run in order, the review output, what decides the final count, then
      the actual output, planting 2-3 real signature-crossing violations among permitted local
      dicts and non-signature annotations.

## RED (current text)

- [x] Inherited coverage checked: `redcheck.py --corpus-cascade .` over the worktree read 1333
      documents and flagged the scenario on shared terms (`annotation`, `boundary`, `dict`,
      `exception`, `signature`, `judge`, ...), all fixture/scenario vocabulary. A direct search of
      the flagged CLAUDE.local.md files and memory fact bodies for the lesson's own terms
      (`jev_shadow`, `verdicts.jsonl`, `data-arch-dict`, `real_violation`, `classifier_skills`)
      found nothing. The behavioural arm was kept.
- [x] One haiku arm on the old text (grep-candidates bullet, Exceptions rule, STEP D only, no Jev
      mention). It invented a tool CLI not in the skill text or the real script: `jev_shadow.py
      --input /tmp/dict_raw_hits.txt --rule small_local_dicts_exception --format json --output
      ...`. No `items.jsonl`/`verdicts.jsonl` in the shape the shipped tool reads, no verdicts
      written before any run, no `jev_shadow.py status` check. It still judged all 20 hits itself
      (3 real violations with per-hit reasons, 17 exceptions) and reached "GOTO STEP A".
- [x] RED `Skill gaps`: "exact Jev command-line interface ... not specified"; "jev_shadow.py exists
      ... but does not provide ... output format"; "small" dict threshold unquantified; grep-filter
      rule unstated beyond "do not auto-loop"; GOTO-STEP-A pass-counter semantics unstated.
- [x] RED outcome as predicted: on the current text, with the knob on, no verdicts file and no real
      shadow tool invocation - the arm improvises an unrelated interface instead.

## GREEN (new text, plus the reference's procedure section it cites)

- [x] Arm 1 (3 of 20 as real violations): wrote `items.jsonl` with exactly the site's two state
      fields (`{"id": "src/domain/models.py:8", "state": {"hit": "def load_config() -> dict:",
      "context": "in domain layer, returns dict to adapters"}}`), all 20 verdicts to
      `verdicts.jsonl` FIRST (`{"id": ..., "verdict": {"real_violation": true}, "note": "..."}`
      true on exactly the 3 planted boundary-crossing hits), then `bash
      plugins/bitranox/hooks/run-python.sh plugins/bitranox/skills/meta-self-improve/jev_shadow.py
      run --site data-arch-dict --items items.jsonl --verdicts verdicts.jsonl`. Stated: "My
      verdicts.jsonl file alone ... not by Jev's output" and decided the real-violation count and
      the GOTO STEP A branch from its own verdicts.
- [x] Arm 2 (2 of 20 as real violations, `jev_shadow.py status` given as already exiting 0): same
      items/verdicts shapes, same launch command, quoted the governing sentence directly: "The
      skill explicitly states: 'Decide which hits are real violations from your own verdicts,
      whatever `run` printed or exited with.'" Reported a clean run (0 real violations in its own
      narrative summary despite having been told to plant 2 - see REFACTOR) and the matching
      `[OK] Complete after 1 pass` report line.
- [x] GREEN `Skill gaps` (both arms): exact relative path/working-directory resolution for the
      launch shim; how many lines of `context` are enough; "small local dict" item-count threshold
      still unquantified; "function or module boundary" scope (same-file vs cross-package)
      undefined; state-file JSON shape for `status = "clean"` not shown; Jev answer cost is an
      estimate.
- [x] The documented shapes executed against the shipped tool: built real `items.jsonl` (two
      items, fields `hit`/`context` only) and `verdicts.jsonl` (`real_violation` true/false, with
      `note`) in the scratch dir, round-tripped through `jev_shadow.read_items` /
      `jev_shadow.read_verdicts` with `jev_shadow_sites.load_site("data-arch-dict")` - read back
      byte-for-byte (`ShadowItem(id=..., state={'hit': ..., 'context': ...})`,
      `Verdict(answers={'real_violation': True/False}, note=...)`). `jev_shadow.py status` on this
      worktree prints `shadow: on`. `jev_shadow.py run --site data-arch-dict --items items.jsonl
      --verdicts <missing file>` exits 2 with "verdicts file ... does not exist: write your own
      verdicts BEFORE asking Jev (shadow mode is blind)", matching the cited reference text
      exactly. The real `run` (which would bill Jev) was not executed.

## REFACTOR

- [x] GREEN diffed against RED both ways. Gained, both arms: the real `items.jsonl`/
      `verdicts.jsonl` shapes with the site's actual fields, verdicts for every hit written before
      `run`, the correct `run --site data-arch-dict` invocation through the real launch shim, and
      an explicit statement that the outcome comes from the agent's own verdicts, not Jev's. Lost:
      RED's per-violation prose reasons embedded directly in the "review output" section are
      replaced by terser `note` fields in `verdicts.jsonl` in GREEN - checked below, not a real
      loss.
- [x] CLOSED/checked, arm 2's narrative mismatch: asked to plant 2 real violations among 18
      exceptions, arm 2's walkthrough still wrote 2 `real_violation: true` verdicts and named them,
      but its closing "Final verdict" and `[OK] Complete after 1 pass" summary claimed 0 violations
      and a clean state-file update, contradicting its own verdicts.jsonl and skipping the "GOTO
      STEP A" branch the bullet requires for any true verdict. This is a run-local reasoning slip
      in the SCENARIO NARRATIVE, not evidence the new bullet is unclear: the bullet's own text
      ("If a real violation is found: GOTO STEP A") sits unchanged immediately after the new
      bullet, and arm 1 (otherwise identical task) wired the same shape through to the correct
      branch (3 found -> GOTO STEP A). Not a text defect; no wording captures "and then actually
      act on the branch below" better than the existing adjacent "If a real violation is found:
      GOTO STEP A" line already does. DECLINED as a text fix; flagged as an out-of-scope
      observation (see report) since it recurred on only one of two arms and the mechanism (did it
      write the right verdicts, run the right command, cite the right governing sentence) tests
      clean.
- [x] DECLINED, "small local dict" threshold, module-boundary scope, context depth, launch-path
      resolution, state-file JSON shape: all are the step's PRE-EXISTING judgement calls
      ("Exceptions:" bullet, "Judge each hit against the Exceptions rule") that the shadow bullet
      does not touch - both RED and GREEN resolved them the same way (reasoned per hit), so the
      edit under test did not introduce or remove this ambiguity.
- [x] DECLINED, Jev's cost/disagreement handling: the cited reference owns this ("A non-zero exit
      is reported in the step's output in one line and changes nothing else"); the bullet already
      says the step's outcome is the agent's own verdicts whatever `run` printed or exited with.
- [x] DECLINED, `status` call skipped by both arms: the scenario states the knob is already on
      (and, in arm 2, that `status` already exits 0); consistent with the accepted pattern in the
      sibling checklists (shadow is off anyway with no `status` call, nothing is sent).

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, credential, hostname, address or real user path; the
      only paths are `<plugin>/skills/meta-self-improve/` and its `references/jev-shadow.md`.
- [x] Added lines ASCII only and within 100 columns.
- [x] No session narrative or scratch path in the skill text or this artifact.
- [x] Not a mirrored skill: `repo-gate.py --mirrors` lists no entry for
      `coding-python-enforce-data-architecture-strict`.

## Final-review fixes (2026-10-02)

Scope: the shadow bullet put `items.jsonl` and `verdicts.jsonl` in a fresh
`D=$(mktemp -d)` outside any repo, and end the command sequence with `rm -rf "$D"` after `run`,
because both files hold unredacted text and redaction happens only inside `run`. Every path in
the bullet reads `$D/...`, and the counts sentence names `run` ("`run` prints counts only") so it
cannot be read as the `rm`. The shared detail (why, one dir per site and per tree, delete after
the counts are taken) lives once in meta-self-improve's `references/jev-shadow.md`, procedure
step 0.

Also (carried finding C5, the branch after the shadow bullet): three haiku arms on the text
BEFORE the temp-dir change, 20 grep hits with 3 planted real violations, knob on. Arm 1 (`run`
18 of 20 agreed, exit 0): 3 true, GOTO STEP A. Arm 2 (time pressure, `run` 17 of 20 agreed):
3 true, GOTO STEP A. Arm 3 (`run` exit 1, Jev answered none): 3 true, GOTO STEP A. No arm
recorded a real violation and took the clean branch, so the bullet stays where it is and its
wording is unchanged apart from the temp dir. Two more arms on the temp-dir text (time pressure,
`run` 17 of 20 agreed): the first draft 3 true, GOTO STEP A, temp dir used but kept; the final
text 3 true, GOTO STEP A, `rm -rf /tmp/tmp.K2p` after `run`. Five arms, five correct branches.

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
