# skill-writer checklist - meta-skill-writer (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: RED-GREEN-REFACTOR for Skills > REFACTOR: Close Loopholes, new paragraph right after
      the 'Where the loop stops' paragraph (after its 'A gap RED and GREEN both report'
      continuation, before 'Verify each fix by quote-back'); plus one REFACTOR Phase checklist line.
      Verified against ground truth: No code claim to verify; the mechanism (a probe stops at the
      first gap) is a measured observation and is stated as a mechanism with no measurement
      attached. Reconciled with existing SKILL.md text: 'Re-test only the questions your fix
      touched, not the whole skill' (kept; new text says re-run 'the questions your fix touched,
      asked in full', so it is not a full re-run), and 'the exit condition is an empty undecided
      list, never an empty list' (new stop rule is 'no new undecided gap', not the body's 'comes
      back clean'). Placed after the 'A gap RED and GREEN both report' continuation so that
      paragraph's 'reasons above' still refers back to Where-the-loop-stops.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Change: SKILL.md Structure > Frontmatter (YAML), two sub-bullets under the existing 'To see
      what a live session actually received' bullet. Verified against ground truth: skill_listing
      attachment, full record isInitial:true after startup and after every plugin reload, delta
      isInitial:false with only added skills -> hooks/skill_roster.py:8-10 docstring, :297
      att.get("type") == "skill_listing", :309-323 listing_from_transcript (latest full + merged
      deltas; delta alone returns None); entry shape '- <name>: <description>' and multi-line
      descriptions anchored on listed names -> hooks/skill_roster.py:50-79 (_opener, _really_opens),
      :90 names; subagent transcript path subagents/agent-<id>.jsonl ->
      hooks/transcript_siblings.py:15,42.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Change: SKILL.md Structure > Frontmatter (YAML), three sub-bullets under the existing 'A
      description under every cap can still be dropped WHOLE' bullet. Verified against ground truth:
      Budget formula, default 0.01, non-bundled entries drop to bare name, restore order usageCount
      * 0.5^(days_since_last_use / 7), never-invoked scores 0 -> hooks/skill-listing-budget.py:4-9;
      ceiling not reservation, only raised never lowered -> :11-13; user-level only, project
      .claude/settings.json or settings.local.json skipped -> :15-18; chars_per_token 4 for a known
      set, 3 otherwise -> :47-52; sized against 200k at the floor -> :50-53; hook registered under
      SessionStart -> hooks/hooks.json:3,17; bundled exempt from rationing ->
      skill-listing-budget.py:40-43; bare '- <name>' line for a trimmed entry ->
      hooks/skill_roster.py:15-16,53-66.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Change: RED-GREEN-REFACTOR for Skills > GREEN: Write Minimal Skill, new paragraph after the
      Skill gaps / 'Ask for the evidence' paragraphs (just before '### REFACTOR: Close Loopholes');
      plus one REFACTOR Phase checklist line. Verified against ground truth: Reconciled with
      SKILL.md pin rule ('it MUST pin a `model` tier per dispatch (`opus`, or `haiku` for purely
      mechanical work ...)'): framed as an added arm beside opus, the same exception the existing
      RED line makes ('**A baseline that PASSES is a result to investigate, not a verdict.** ...
      re-run pinned to a weak, literal tier'). Consistent with the existing 'Say Whose Verdict Is
      the Result' line 'Test the wording on the weakest tier (`haiku`)'. Behaviour claims are
      measured observations from the body, stated as mechanism without the measurement.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): partial for scenario 1;
      partial for scenario 2; partial for scenario 3; NONE for scenario 4. Behavioural RED replaced
      on purpose: each rule is in the always-loaded memory index of the authoring machine (inherited
      coverage), so the RED is a quote-back against the pre-edit file.
- [x] GREEN quote-back on haiku and opus against the edited files; every quote checked against the
      skill's files (a fragment check, then a grep of each inserted rule's lead sentence), all
      present.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus for every scenario; tiers haiku and
      opus, one cell per scenario per tier.
- [x] Gaps closed or declined: closed - the probe re-run now names the questions the first gap kept
      the probe from reaching (re-tested by quote-back on haiku and opus, both quoted it); declined
      - a cap on repeats (the exit rule is the empty undecided list), how to pick the session file
      (the reader knows its session), settings scopes beyond user and project (harness detail the
      repo does not pin), the vendored anthropic-best-practices.md line naming three tiers (upstream
      text keeps its own wording), how many haiku cells suffice (the artifact states the count).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
