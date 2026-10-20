# skill-writer checklist - meta-dream-tree (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: dream-core.md 'Verification contract', right after the --check-tree requirement;
      SKILL.md step 8 'Re-dedup, then verify', after 'Size warnings are advisory.'. Verified against
      ground truth: resolve_anchor returns the TOPMOST ancestor with CLAUDE.md AND .claude-memory ->
      hooks/self_improve_signals.py resolve_anchor docstring (~1281-1291). Walk-up recipe stops at
      first ancestor with a store -> hooks/uuid_store.py:120-121 RECIPE_LINE ('walk UP ... to the
      first ancestor that contains a `.claude-memory/`'). --check-tree reports decoy as a problem
      with this wording -> skills/meta-self-improve/reconcile_memory_index.py:545
      find_decoy_anchors, :981-983 '! decoy anchor ... problems += 1'; backup dirs `<store>-*` and
      stores inside them pruned -> :552-556 and the dirs[:] filter (d.startswith(STORE_DIRNAME)).
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Change: Procedure step 0b (scope-descriptor synthesis), before the 'Only synthesize levels
      whose descriptor is EMPTY' sentence; plus step 0a (heal) one clause. Verified against ground
      truth: heal scaffolds every dir from proj up to the anchor -> hooks/memory_engine.py heal
      (~1117-1140) iterates sig.altitude_chain(proj); altitude_chain
      (hooks/self_improve_signals.py:1445-1452) includes 'each ancestor directory up to and
      INCLUDING the tree's anchor (gap levels between are included so they can be filled)';
      _heal_level (memory_engine.py ~1100-1114) runs _ensure_claude_md + ensure_level +
      pointer-block render. SessionStart heals the cwd every session -> hooks/session-start.py:77-78
      _proj = event cwd, :552-557 _self_heal calls memory_engine.heal(proj), :635 _self_heal(proj).
      Scope block marker spelling -> hooks/memory_engine.py:41-42 '<!-- bitranox:self-learning -->'.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Change: dream-core.md 'Dedup semantics', after the CANDIDATE paragraph; SKILL.md step 3b
      'De-double the tiers' and step 4 'Dedup / merge ACROSS THE TREE'. Verified against ground
      truth: Step 3b drops on title/hook match -> SKILL.md:162 pre-edit 'already curated (by
      title/hook match) -> drop the native duplicate' (the destructive path the skeptic flagged; now
      gated). Extends, does not contradict, dream-core.md:192-199 CANDIDATE paragraph. Archive
      mechanics already covered elsewhere -> dream-passes.md removal policy /
      reconcile_memory_index.py --archive (not restated). Lexical scanner limitation consistent with
      SKILL.md step 4 'A clean scan is a clean LEXICAL scan'. 18/27, 2-to-1 and 5-of-5 merge figures
      -> fact body (kept as undated measurements).
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
- [x] Gaps closed or declined: closed - a drained decoy goes to the backup root and is never deleted
      (heading now says move it out); removing a scaffold-noise level is named under Boundaries as a
      proposed structural move and the Deliverables box excepts it; step 0a's `<cwd>` is defined as
      the project root (all re-tested by quote-back on haiku and opus, all quoted); declined - a
      definition of project root (the term is used throughout the skill family), how many skeptics
      (one per lens is stated), where the proposed-removal list goes (the dream's report).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
