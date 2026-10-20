# skill-writer checklist - compuse-toolbox (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: transcript-corpus.md: new bullet after 'Dedupe tool calls by tool_use id'; SKILL.md:
      the references/ routing list bullet. Verified against ground truth: Stubs are a real share ->
      ran read-only: `find ~/.claude/projects -name '*.jsonl' | wc -l` = 3929 and the inserted
      find|wc|awk command = 1117 files under 50 lines (~28%), so 'many' holds and the command itself
      works (awk excludes wc's 'total' rows). No existing two-denominator rule in the skill
      (transcript-corpus.md:19-22 'inflating the denominator' is about duplicate calls only).
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Change: ## Why a jig over a one-liner: new bullet after '`guard_replay` asks the second
      question too'; plus one sentence appended inside the guard_replay row of the ## Tools table
      (consumed trailing padding, row length unchanged at 4910 chars). Verified against ground
      truth: guard_replay runs only the given predicate and counts truthy as firing -> SKILL.md:90
      ('anything truthy counts as a firing') and guard_replay.py docstring lines 1-60. --firings
      writes every firing with the FULL command -> guard_replay.py:495-517 write_firings writes {id,
      transcript, cwd, command, error} with call.get('command') untruncated, and argparse :573-576.
      Exit 1 = never fired (docstring), consistent with the candidate-miss reading. The blocking
      guard for a pgrep -f pattern exists -> plugins/bitranox/hooks/block-pgrep-self-match.py.
      Heading 'Why a jig over a one-liner' exists at SKILL.md:113. 40x is a historical measurement
      (6,335 -> ~140), kept dated, not re-run.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): partial for scenario 1;
      partial for scenario 2. Behavioural RED replaced on purpose: each rule is in the always-loaded
      memory index of the authoring machine (inherited coverage), so the RED is a quote-back against
      the pre-edit file.
- [x] GREEN quote-back on haiku and opus against the edited files; every quote checked against the
      skill's files (a fragment check, then a grep of each inserted rule's lead sentence), all
      present.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus for every scenario; tiers haiku and
      opus, one cell per scenario per tier.
- [x] Gaps closed or declined: declined - a stated stub cut-off (eligibility is per detector; the
      command shows one example cut-off), a jig for grouping candidates by shape (none exists; the
      step is a read).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
