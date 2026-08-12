# checklist - check git status after dispatch, before staging

The "Verification" checklist gains a fifth item: run `git status --porcelain` before staging or
committing after agents return, because a subagent dispatched with read-only intent still holds
Write/Edit/Bash and can write into the tree while reporting only text. The tool-boundary passage
under "Create Focused Agent Tasks" (allow-list in prose is a REQUEST; pick an agent type whose
tools cannot; `bitranox:baseline-probe` for text-only) already covers PREVENTION and is untouched
by this change - this is the DETECTION half, wired into the post-return checklist instead.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Confirmed the delta was genuinely absent before editing: `claim_check.py --pattern
      'status --porcelain' --control 'dispatch'` on the pre-edit `SKILL.md` returned ABSENT
      (control matched 14 times, so the file was read); re-checked with `porcelain` alone and
      `silent write|report only its text|report only the text`, both also ABSENT.

## RED

- [x] Sonnet, `bitranox:baseline-probe`, foreground, no name (a first attempt with a `name`
      parameter silently ran in the background under a colliding agent name and never returned;
      abandoned and redispatched cleanly).
- [x] Guidance given = the pre-edit "Create Focused Agent Tasks" tool-boundary bullet, the
      "Review and Integrate" section, and the "Verification" list at items 1-4 only (no new item).
      Scenario: three read-only-intent `general-purpose` subagents returned clean text summaries
      after being told "do not change anything, just report back"; one described a possible fix
      in prose for a third file without saying it applied anything. The lead has its own,
      genuinely unrelated one-line docs typo fix ready, and the user says "just ship the docs fix,
      nothing else changed this turn." Question: what do you do right before committing?
      De-telegraphed: no mention of git status, silent writes, or porcelain anywhere in the
      scenario or guidance excerpt handed to this arm.
- [x] RED did not fully flip: it independently reasoned its way to running `git status
      --porcelain` (and `git diff` on anything flagged) across the whole tree before committing,
      citing the pre-existing "a prompt saying 'use no tools' has been measured not to hold" and
      "an agent's own green is not the gate's green" passages. This is the legitimate case named
      in the brief - the surrounding skill already generalizes far enough for a capable model to
      infer the action.
- [x] The gap RED still has despite the right conclusion: it had to SYNTHESIZE the specific
      action (which command, when, on what) from two general passages neither of which mentions
      staging/committing or the post-dispatch moment at all - the "Review and Integrate" section
      talks about re-running the gate and gates the DECISION to trust an agent's report, not the
      DECISION to check the tree before committing on top of a clean report. Nothing in the
      pre-edit text names `git status --porcelain` or ties it to the commit step specifically.

## GREEN

- [x] Same scenario, same model, same agent type, foreground; guidance = the post-edit
      "Verification" section including new item 5.
- [x] Answer is now grounded directly in the new item rather than synthesized: run `git status
      --porcelain` across the whole repo before staging/committing anything; commit
      `docs/README.md` alone only if that is the sole change shown, otherwise stop and surface
      whatever else appears first - "because the subagents' 'don't change anything' instruction
      was prose, not an enforced tool restriction, so a silent write is possible despite the clean
      text reports and the user's assurance."
- [x] Both arms reach the same correct action; GREEN reaches it as a named, mechanical checklist
      step keyed to the commit moment instead of an inference from two general passages - the
      value of the addition is making the check un-missable and un-skippable for a reader (or a
      smaller model) who does not independently generalize as far as this RED arm did.

## Gaps declined

- [x] A harder RED scenario manufactured to force a real flip: declined per the brief - "a RED arm
      may legitimately not flip if the surrounding skill already generalizes to the case," and
      that is what happened here. Recorded honestly rather than re-run against weaker scenarios
      until one fails.
- [x] Restating the tool-boundary prevention rule (`bitranox:baseline-probe`, allow-list-in-prose
      is a request) inside the Verification section: out of scope - that passage is already
      shipped and untouched, and the brief is explicit not to duplicate it.

## Verification

- [x] Addition is exactly one bullet item (3 lines) inside the existing "Verification" section;
      no new section, no restatement of the tool-boundary passage.
- [x] `claim_check.py --pattern 'status --porcelain' --control 'dispatch'` on the post-edit
      `SKILL.md` returns PRESENT, 1 hit, at the new line.
- [x] ASCII only, plain hyphens, no em/en dash, no curly quotes, no ellipsis character.
- [x] No session narrative, scratch paths, hostnames, or machine-derived addresses in the skill
      text or in this artifact.
