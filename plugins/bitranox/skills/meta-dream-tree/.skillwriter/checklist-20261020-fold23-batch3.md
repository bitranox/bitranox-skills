# skill-writer checklist - meta-dream-tree (2026-10-20, fold23 batch 3)

- [x] Change: SKILL.md promotion step - `saw-promotable` takes the ABSOLUTE path of the project the
      fact came from, and a `promote` resting on a project key that resolves to no real directory
      is a `hold`, pointing at dream-core.md.
- [x] Change: references/dream-core.md - new paragraph "A `promote` is only as good as the keys
      behind it" (keys are `sha1(os.path.abspath(project))[:16]`, a bare name resolves against the
      cwd, resolve every key with a positive control before acting); the earlier gate sentence now
      also says ABSOLUTE. Ground truth: `hooks/self_improve_signals.py:31-58` (`proj_key`:
      `hashlib.sha1(os.path.abspath(...)).hexdigest()[:16]`), `:1961-1973`
      (`note_promotion_candidate` adds `proj_key(proj)` with no existence check),
      `skills/meta-dream-tree/dream_state.py:353-360` (`saw-promotable` calls it).
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first SKILL.md edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): partial - "obey the
      word it prints" with no exception and no word on how keys are formed. Behavioural RED
      replaced on purpose: the rule is in the always-loaded memory index of the authoring machine.
- [x] GREEN quote-back on haiku and opus, quotes substring-checked: dream-core.md:230 "A `promote`
      is only as good as the keys behind it." and SKILL.md:224 "`dream_state.py saw-promotable
      <slug> <ABSOLUTE path of the project the fact came from>`".
- [x] GREEN diffed against RED both ways: the RED quote ("obey the word it prints") is still
      present, now with its exception; nothing lost.
- [x] Gaps closed or declined: closed - the earlier dream-core.md gate sentence did not say
      ABSOLUTE (fixed at :222, re-tested by quote-back on haiku and opus, both quoted the absolute
      rule); declined - a command for hashing candidate dirs (the paragraph gives the formula and
      the candidate set; a jig is a separate tooling change), a tree-wide heal (pre-existing, heal
      is chain-scoped by design).
- [x] Description measured: unchanged
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII
