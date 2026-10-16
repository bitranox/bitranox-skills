# skill-writer checklist - files-edit-toml (2026-10-16, fold23)

- [x] Change: new reference file `references/tomlkit-not-diff-minimal.md` - interleaved table
      families are regrouped on dump even with no edit (check `dumps(parse(src)) == src` first;
      if False, edit by exact text at an asserted unique anchor, re-parse with `tomllib`, check for
      duplicates, require zero removed lines, restore from a copy taken before the edit); a new
      `[tool.x]` lands after the first `[tool.*]`; `del` leaves the comment above the key.
- [x] Change: SKILL.md paragraph "tomlkit is not always diff-minimal" after the syntax-check line,
      with the equality check and a pointer saying when to read the reference file.
- [x] Every behaviour claim executed against tomlkit 0.15.2: the interleaved example in the
      reference file round-trips to a different text with `[rowsets.b]` moved above both
      `[[claim]]` entries; a new `[tool.uv]` landed directly after `[tool.ruff]`, above
      `[project.urls]`; `del` left `# about a` above `b = 2`.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded
      the skill
- [x] RED (text check of the artifact): before this edit the skill said only that tomlkit keeps
      "comments, key order, and whitespace" and always to edit via parse -> edit -> dumps; the
      verifier found no warning about regrouping, no equality check, no text-edit fallback and no
      note on new-table placement or orphaned comments. Behavioural RED replaced on purpose
      because the rule is in the always-loaded memory index of the authoring machine (inherited
      coverage)
- [x] GREEN quote-back (fresh-context verifier): SKILL.md "Before editing, check
      `tomlkit.dumps(tomlkit.parse(src)) == src`" and the pointer to
      references/tomlkit-not-diff-minimal.md; the reference example run with tomlkit 0.15.2:
      round-trip False, data unchanged, `[tool.uv]` lands after `[tool.ruff]`, `del` orphans the
      comment. "it is False" corrected to "it can be False" (a plain `[a.x]/[b]/[a.y]` round-trips
      equal).
- [x] Gaps closed or declined: the Common mistakes row and the duplicate-key step are left as they
      are (declined: the new paragraph names its own exception; tomllib already rejects duplicate
      keys).
- [x] Description measured: unchanged (387 characters)
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
