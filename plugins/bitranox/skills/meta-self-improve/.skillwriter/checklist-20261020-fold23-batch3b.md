# skill-writer checklist - meta-self-improve (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: SKILL.md '### 3b. Choose the altitude', new bullet right after the 'Route --proj by
      SUBJECT' bullet; memory-backend.md '## The engine (the ONLY write path) and its fail-loud
      contract', new paragraph before the command table. Verified against ground truth: body to
      anchor, pointer to proj -> hooks/memory_engine.py add uses us.body_path(anchor, slug)
      (uuid_store.py:229) and sig.claude_local_md_path(proj) = Path(proj)/'CLAUDE.local.md'
      (self_improve_signals.py:269-273); dangler line + advisory total, not counted in problems ->
      reconcile_memory_index.py:996-1001 (no problems += 1 for danglers; prints 'TOTAL dangling
      bodies: %d (advisory - run with --rehome ...)'); danglers skipped when unreadable ->
      reconcile_memory_index.py:638-643; unreadable run exits 2 -> :1003-1004; --rehome default tree
      top, --rehome-to LEVEL for a subtree -> argparse help :878-887; add adopts a dangling body
      unless another level on the chain owns it -> memory_engine.py:350-361 and
      _slug_owned_elsewhere :493 (chain-scoped); --check-misplaced judges by body paths -> help text
      :898-901; no engine guard against --proj under ~/.claude/plugins -> ExcludedLevel covers only
      home/tempdir/root (memory_engine.py:165-174).
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Change: New paragraph after 'Dropping is a JUDGEMENT ... test it and find out.' (which follows
      'Close every entry by its OUTCOME'), before 'Before writing a queued documentation
      contribution, check it is not already shipped elsewhere'. Verified against ground truth: `ship
      --match TEXT [--note WHERE]` -> contrib_queue.py:19 usage docstring; guard_replay and
      corpus_prompts exist and replay transcript calls / typed prompts ->
      skills/compuse-toolbox/SKILL.md:90-91; 'see below' resolves to the existing already-shipped
      paragraph in the same file (upstream-propagation.md, 'Before writing a queued documentation
      contribution, check it is not already shipped elsewhere'); no contradiction with 'A queue
      entry you merely doubt is not a drop - test it and find out' (line 46), the new text extends
      it.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Change: '### 3. Dedup BEFORE writing (mandatory)', new paragraph after the two 'The level.' /
      'The slug.' bullets (the find-the-owner command sits in the first of them). Verified against
      ground truth: the find above is tree-wide from <anchor> -> SKILL.md step 3 code line `find
      <anchor> -name CLAUDE.local.md -not -path "*/.claude-memory/*" -exec grep -l "mem:<slug>" {}
      \;`; --check-tree walks every curated level under the anchor and prints dangling bodies ->
      reconcile_memory_index.py argparse help :892-897 and print :997; ancestor-only cascade ->
      consistent with memory-backend.md 'Three delivery paths' item 1 ('ancestor CLAUDE.local.md
      blocks load as plain text every session'), Claude Code behaviour not pinned by the repo;
      'scope descriptor' is the term SKILL.md 3b already uses (line ~207), PLACE-HERE is the
      descriptor's line name used in meta-dream-tree.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): partial for scenario 1;
      partial for scenario 2; partial for scenario 3. Behavioural RED replaced on purpose: each rule
      is in the always-loaded memory index of the authoring machine (inherited coverage), so the RED
      is a quote-back against the pre-edit file.
- [x] GREEN quote-back on haiku and opus against the edited files; every quote checked against the
      skill's files (a fragment check, then a grep of each inserted rule's lead sentence), all
      present.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus for every scenario; tiers haiku and
      opus, one cell per scenario per tier.
- [x] Gaps closed or declined: closed - a note under the command table says the --check-tree success
      line counts problems only (re-tested by quote-back on haiku and opus, both quoted it);
      declined - how to find the source repo from an installed copy (installation-specific; the rule
      names what not to target), the ship/drop launch form (step 3b already shows the contrib_queue
      launch), an instrument for fixes that do not fire on a pattern (left to the item).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
