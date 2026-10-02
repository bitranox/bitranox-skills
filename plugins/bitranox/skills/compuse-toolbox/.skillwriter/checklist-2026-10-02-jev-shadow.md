# Skill-writer checklist: Jev shadow on the guard_replay classify-all step (2026-10-02)

Scope: the `guard_replay` sample bullet, which ends "classify the whole set when the answer is a
ratio or a residual". It gains one sentence saying the agent classifies and reports from its own
verdicts, and a nested bullet for the Jev shadow site `guard-firing`: gated on
`jev_shadow.py status`, items built from `guard_replay --firings`, the agent's verdicts written
before `jev_shadow.py run`, the ratio reported from those verdicts. The procedure detail stays in
`meta-self-improve/references/jev-shadow.md`, which the bullet cites with its home and launch
shim. Technique edit; no name, description, trigger or table row changed.

## PLAN

- [x] Skill type: technique step inside a reference/hub skill. Test approach: application
      scenario on the least inferential tier (haiku), inert probe type, text supplied in the
      prompt.
- [x] Scenario: a new guard, 20 firings written by `guard_replay --firings`, a precision ratio to
      report, `classifier_backend = jev` and `classifier_skills = shadow` set and a Jev key
      present. Asked: what is done with the firings, in what order, which files and commands, and
      what decides the reported figure.

## RED (current text)

- [x] Inherited coverage checked: `redcheck.py --corpus-cascade` over the worktree read 1324
      documents and flagged the scenario, but every shared term was topic vocabulary
      (`guard_replay`, `precision`, `firings`, `decide`). A search of the cascade and the memory
      fact bodies for the lesson's own terms (`jev_shadow`, `verdicts.jsonl`,
      `classifier_skills`) found one fact about shadow-versus-decide logging in general and no
      procedure for this step. The behavioural arm was kept.
- [x] Two haiku arms on the old text, same prompt. Neither wrote a verdicts file nor ran
      `jev_shadow.py`. Both handed the classification itself to Jev and took Jev's labels as the
      precision: arm 1 invented `jev-judge --items firings.jsonl --question ... --output
      precision-classified.jsonl` and counted `.judgment == true`; arm 2 invented
      `uvx jev-judge batch ... --judgment-type binary` and counted `"yes"` rows. Arm 2 named the
      reason: "I chose jev-judge because (a) user's config shows it ready, (b) 20 firings is a
      bounded judgment task it's designed for". The RED fails worse than expected: the knob being
      on reads as permission for Jev to DECIDE.
- [x] RED `Skill gaps` (both arms): jev-judge syntax and input/output format unknown, the
      firings schema unstated, whether classification is manual or tool-based not said, boundary
      cases of the hazard (`git -C <path>`) not defined.

## GREEN (new text, plus the reference's procedure section it cites)

- [x] One haiku arm, same scenario. Order it gave: `jev_shadow.py status` (expect exit 0), then
      `items --site guard-firing --firings firings.jsonl --hazard "..." --out items.jsonl`, then
      judge all 20 itself, then write `verdicts.jsonl` "(BEFORE running Jev)", then `run --site
      guard-firing --items items.jsonl --verdicts verdicts.jsonl`, then precision = true verdicts
      over 20. On what decides the figure it quoted the step: "Report the ratio from your own
      verdicts, whatever `run` printed or exited with." Every command went through
      `hooks/run-python.sh` with the full `<plugin>` path.
- [x] GREEN `Skill gaps`: items.jsonl fields beyond those named; judgment criteria for the
      hazard; whether partial verdicts are acceptable; report format; whether `note` is
      encouraged.
- [x] The documented commands executed against the shipped tool with a two-line firings file:
      `items` exit 0 wrote two items with the `hazard`, `command`, `error` state; `status` exit 0
      `shadow: on`; `run` with no verdicts file exit 2, "write your own verdicts BEFORE asking
      Jev". Nothing that costs money was run.

## REFACTOR

- [x] GREEN diffed against RED both ways. Gained: the status gate, the items command, verdicts
      before `run`, the agent's own verdicts as the figure; the invented jev-judge invocations and
      the Jev-decides precision are gone. Lost: nothing of value. RED arm 1's boundary-case
      remark (`git -C`) reappears in GREEN as its judgment-criteria gap; RED arm 2's
      rate-versus-precision paragraph restated the excerpt and carried no result.
- [x] CLOSED, partial verdicts: a quote-back on haiku answered "may some firings be left without
      a verdict?" with the reference's "You may leave items or questions out", which overrode the
      step's "every firing". Fixed in both places: the step now says "none left out, since the
      ratio counts every firing", and the reference's step 2 reads "Unless the step asks for a
      verdict on every item, you may leave items or questions out". Re-run quote-back answered
      with "write YOUR verdict for every firing to `verdicts.jsonl`".
- [x] DECLINED, items.jsonl fields: the reference's site table names the state fields, and the
      file is read, not authored, at this site.
- [x] DECLINED, hazard criteria: they belong to the guard under test, not to this skill.
- [x] DECLINED, report format and `note`: the step requires the ratio from own verdicts; format
      is the caller's, and the reference already marks `note` optional.

## Fix round 1

- [x] The `guard_replay` Tools-table row's Run column lists `--firings OUT.jsonl`, which the
      shadow bullet depends on. Row width kept (padding reduced by the inserted length).
- [x] Second independent GREEN arm on haiku, same scenario, final text (the step with "none left
      out", the reference step 2 with "Unless the step asks for a verdict on every item"). It ran
      `items --site guard-firing --firings firings.jsonl --hazard "..." --out items.jsonl`, wrote
      `verdicts.jsonl` with "exactly 20 JSON lines ... No items left out", then `run`, and computed
      precision from its own true verdicts over 20, quoting "Report the ratio from your own
      verdicts, whatever `run` printed or exited with". No Jev decision, verdicts before `run`.
- [x] Divergence from GREEN arm 1: arm 2 did not call `jev_shadow.py status` first. DECLINED as a
      text change: the scenario states both knobs on and a key present, and `run` itself prints
      `shadow: off (<reason>)`, exits 0 and writes nothing when shadow is off, so skipping the
      status check sends nothing and changes no outcome. The step already names the gate.
- [x] Arm 2 `Skill gaps`: it cannot judge without the firing data (expected, text-only probe);
      `<plugin>` resolution (the step and reference both give the home and shim); what to do with
      `items.jsonl` and `verdicts.jsonl` after `run`. DECLINED: they are working files of the
      step, and the durable record is the shadow log the reference names.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, credential, hostname, address or real user path; the
      only path is `<plugin>/skills/meta-self-improve/`. The shadow step sends nothing unless the
      user turned both knobs on, and the tool redacts secrets before sending.
- [x] The same change documents in the reference that a noul answer logs `probabilities` and
      `confidence` as null.
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
