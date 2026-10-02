# Skill-writer checklist: Jev shadow on the polarity cap and call-site resolution (2026-10-02)

Scope: two steps of the interface-shape census. "Cap it when the sites are many" gains one
sentence saying the agent reads every site and quotes and counts from its own verdicts, and a
bullet for the Jev shadow site `quality-polarity`. The "Gather the call-site evidence by PARSER"
bullet gains one sentence saying the agent resolves every hit and keeps and counts from its own
verdicts, and a nested bullet for the site `quality-param-hit`. Both bullets: gated on
`jev_shadow.py status`, agent-built `items.jsonl` with exactly the site's state fields, the
agent's verdict for every item written to `verdicts.jsonl` before `jev_shadow.py run`, the step's
outcome taken from those verdicts. Both steps need a verdict on every item (the cap counts every
site, every hit is resolved), and both bullets say so. The procedure detail stays in
`meta-self-improve/references/jev-shadow.md`, cited with its home and launch shim. Technique edit;
no name, description, trigger or table row changed.

## PLAN

- [x] Skill type: technique steps inside a review skill. Test approach: application scenario on
      the least inferential tier (haiku), inert probe type `bitranox:baseline-probe`, step text
      and the cited reference supplied in the prompt.
- [x] Scenario per site, both with `classifier_backend = jev`, `classifier_skills = shadow` and a
      Jev key present, asking for files written (with example lines), commands run, review
      output, what decides it, then the actual output:
      - `quality-polarity`: 20 `[boolean, string]` check-function sites, convention `true` =
        passed, three planted inversions (`degradedModeCheck` `[true, "...degraded mode"]`,
        `redundancyCheck` `[true, "PSU redundancy lost"]`, `linkCheck` `[false, "link up at 10G"]`).
      - `quality-param-hit`: 20 `key=` grep hits for a `Store.get`/`Store.put` parameter, 8 real
        `Store` calls and 12 builtin/stdlib sort keys (`sorted`, `max`, `min`, `list.sort`,
        `heapq.nlargest`, `itertools.groupby`, `bisect.insort`).

## RED (current text)

- [x] Inherited coverage checked: `redcheck.py --corpus-cascade` over the worktree read 1324
      documents and flagged both scenarios, but every shared term was fixture vocabulary
      (`clock`, `drift`, `billing`, `bisect`, `census`, `controller`). A search of the cascade
      CLAUDE files and the memory fact bodies for the lesson's own terms (`jev_shadow`,
      `verdicts.jsonl`, `quality-polarity`, `quality-param-hit`, `classifier_skills`) found
      nothing. The behavioural arms were kept.
- [x] `quality-polarity`, one haiku arm on the old text. No verdicts file, no `jev_shadow.py`
      run. It offered an invented Jev classification as optional: `jev-judge classify --prompt
      "Does this return pair ..." < sites-for-sentiment.jsonl > sentiment-verdicts.jsonl`. Its
      own reading found the three inversions and wrote "quoted 3 of 20; the other 17 read ...".
- [x] RED `Skill gaps` (polarity): "Classification method not specified ... manual analysis vs.
      automated classifier ... a formal classifier like Jev could be called"; sentiment boundary
      undefined; skip-count wording for a mixed remainder; whether to persist analysis files.
- [x] `quality-param-hit`, one haiku arm on the old text. No verdicts file, no `jev_shadow.py`
      run, no Jev at all: it described a filter script and kept the 8 `Store` calls (hits 2, 4, 6,
      8, 10, 14, 17, 18). It added "Next step (per skill): Investigate WHO SUPPLIES A NON-DEFAULT
      VALUE". It returned no `Skill gaps` section although asked.
- [x] RED outcome as predicted: on the current text, with the knob on, neither site produces a
      verdicts file or a shadow run, and the polarity arm reaches for an invented Jev call.

## GREEN (new text, plus the reference's procedure section it cites)

- [x] `quality-polarity` arm 1: wrote `items.jsonl` (`{"id": "src/checks/battery.ts:12", "state":
      {"function": "chargeCheck", "source_line": ..., "convention": "true = check passed
      (healthy)"}}`), all 20 verdicts "(I judge each before running Jev)" with `agrees: false` on
      exactly the three inversions, then `run --site quality-polarity --items items.jsonl
      --verdicts verdicts.jsonl`. Output: "My verdicts (not Jev's output) show: 3 sites ...",
      quote block of the three, "Quoted 3 of 20 sites".
- [x] `quality-polarity` arm 2: `jev_shadow.py status` first, same items and verdict shapes, then
      `run`; "What decides the quotes and counts: My own reading of all 20 sites", quoting
      "YOU read every site; the quotes and counts come from your verdicts." Same three quoted,
      "quoted 3 of 20 sites; the other 17 read ...".
- [x] `quality-param-hit` arm 1: 20 items, 20 verdicts (true on hits 2, 4, 6, 8, 10, 14, 17,
      18), then `run --site quality-param-hit ...`; kept the 8 and "Final count: 8 call sites".
      Its items carried `"parameter": "key (sorted builtin)"` on a sort-key hit: the resolved
      callee, which is the answer, in the state Jev is asked about.
- [x] `quality-param-hit` arm 2: verdicts "(all 20 verdicts, written FIRST)" with a `note` per
      dropped hit, then `run`; "What Decides Which Hits to Keep: My own verdicts in
      verdicts.jsonl", quoting "Keep or drop each hit by your own verdict, whatever `run` printed
      or exited with." Kept 8. Its items carried `"parameter": "key"` with no declaration.
- [x] GREEN `Skill gaps`: `<plugin>` resolution (all four); `context` depth (param arms 1 and 2);
      sentiment boundary for "link up at 10G" (polarity arms 1 and 2); what to do with Jev's
      counts or a Jev disagreement (polarity arm 1, param arm 1); working-file location and
      cleanup (polarity arm 1); whether `agrees` is a boolean (polarity arm 2); `parameter`
      qualification (param arm 2: "The skill does not ask for full parameter qualification").
- [x] The documented shapes executed against the shipped tool: one item and one verdict per site
      in exactly the documented shape, read back by `jev_shadow.read_items` and
      `jev_shadow.read_verdicts` (`Verdict(answers={'agrees': False})`,
      `Verdict(answers={'is_parameter': False})`); `jev_shadow.py run --site quality-polarity`
      with no verdicts file exits 2, "write your own verdicts BEFORE asking Jev"; `status`,
      `run --help` and `status --help` list the flags the text names. Nothing that costs money
      was run.

## REFACTOR

- [x] GREEN diffed against RED both ways. Gained, all four arms: the items file with the site's
      fields, verdicts for every item before `run`, the `run` command with the right site, and
      the step's output from own verdicts; the invented `jev-judge classify` is gone. Kept: the
      polarity arms quote the same three inversions with the same "3 of 20" as RED, and the
      param arms keep the same 8 hits. Lost: RED param's closing "Next step: investigate WHO
      SUPPLIES A NON-DEFAULT VALUE", absent in GREEN param arms 1 to 3 (checked for
      reproduction in Fix round 1).
- [x] CLOSED, `parameter` field content: arm 1 put the resolved callee in it, arm 2 left out the
      declaration, both because "<name, where declared>" did not say it is the parameter under
      review and constant. The bullet now reads `"<the name under review and where it is
      declared>"` and "`parameter` the same on every hit (never what the hit resolved to: that is
      the answer)". Re-tested with GREEN param arm 3 on the final text (below).
- [x] DECLINED, `<plugin>` resolution: the bullets give the home and the shim, as every script
      reference in the plugin does.
- [x] DECLINED, `context` depth: "code around it" is the reviewer's judgement per language; the
      fixture supplied one line per hit, which is the probe's limit, not the text's.
- [x] DECLINED, sentiment boundary ("link up at 10G"): judging sentiment is the step's existing
      judgement, unchanged by this edit; both GREEN arms and RED judged it the same way.
- [x] DECLINED, Jev's counts and disagreements in the review output: the reference owns this
      (step 4 reports a non-zero exit in one line; disagreements are read afterwards with
      `report`), and the bullets say the outcome is the agent's whatever `run` printed.
- [x] DECLINED, working-file location, `agrees` type, `note` use: the reference states the noul
      answer is `true` or `false` and marks `note` optional; file location is the agent's
      working directory choice and changes no outcome.
- [x] DECLINED, polarity arm 1 skipping `status`: the scenario states both knobs on and a key
      present, and `run` itself prints `shadow: off (<reason>)` and exits 0 when shadow is off.

## Fix round 1

- [x] GREEN param arm 3 on the final text, asked for one kept and one dropped example line of
      each file. Both items carried the same `"parameter": "Store.get(self, key, default=None)
      at app/store.py:10"`, so the dropped sort-key hit no longer carries its answer. Verdicts for
      all 20 written before `run --site quality-param-hit ...`; kept 8, "my own verdict count (8)
      stands". `Skill gaps`: `<plugin>` and `context` content (declined above); whether to run or
      describe the command (a probe artifact); what Jev disagreements do (declined above).
- [x] The lost RED item checked for reproduction: a second RED param arm on the old text, same
      prompt, did not put the WHO-SUPPLIES next step in its output either; it named it only in
      `Skill gaps` as "beyond this section". Present in 1 of 2 RED arms and asked for by neither
      scenario, so it is run variance, not a result the edit displaced. That arm also wrote no
      verdicts file and ran no `jev_shadow.py`, confirming the RED.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, credential, hostname, address or real user path; the
      only path is `<plugin>/skills/meta-self-improve/`. The shadow step sends nothing unless the
      user turned both knobs on, and the tool redacts secrets before sending.
- [x] Added lines ASCII only and within 100 columns.
- [x] No session narrative or scratch path in the skill text or this artifact.

## Final-review fixes (2026-10-02)

Scope: the shadow bullets put `items.jsonl` and `verdicts.jsonl` in a fresh
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
