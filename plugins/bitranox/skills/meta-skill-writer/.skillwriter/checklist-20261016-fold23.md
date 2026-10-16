# skill-writer checklist - meta-skill-writer (2026-10-16, fold23)

- [x] Change: Deployment checklist, "Place skill in the correct directory" now splits on what the
      skill teaches: USING a tool (the tool repo as a single-plugin marketplace plus a mirror,
      never `<repo>/.claude/skills/`), DEVELOPING one repo (`.claude/skills/`), a generic procedure
      across projects (`~/.claude/skills/` plus a project extension skill for bindings).
- [x] Change: "5. Cross-Referencing Other Skills" gains a rule that a skill shipping in its own
      plugin copies the content it needs into its own files instead of a `REQUIRED SUB-SKILL`
      crossing a plugin boundary.
- [x] Change (contradiction): testing-skills-with-subagents.md no longer calls a redcheck hit
      "demonstrably" in context next to the term-overlap caveat; the two sentences are merged into
      one that calls a hit the strong direction and a term-overlap match to adjudicate. Ground
      truth: `scripts/redcheck.py` in process-test-driven-development counts a hit on
      `if len(shared) >= min_shared:` (shared rare distinctive terms), not on the claim.
- [x] Change (contradiction): the capture paragraph names route 1 as "the coverage check against
      the skill file, run on the text as it stood BEFORE your edit", and route 1 says to run it on
      the pre-edit text. Ground truth: compuse-toolbox `scripts/claim_check.py` reads the paths it
      is given and reports `PRESENT 0 the pattern matched`, so on the edited file it is PRESENT by
      construction.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded
      the skill through the Skill tool before its first SKILL.md edit
- [x] RED (text check of the artifact): before this edit SKILL.md (`git show HEAD:`) had no text
      for either rule: "single-plugin marketplace" 0 hits, "another plugin" 0 hits. Verifier gaps:
      "The Deployment checklist offers only two placements ... It never gives the third case" and
      "Nothing says that a skill shipping in its own plugin must not point at another plugin's
      skill". Behavioural RED replaced on purpose because the rules are in the always-loaded
      memory index of the authoring machine (inherited coverage).
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): tool-usage skill
      placement -> SKILL.md:1329 "**USING a tool or library** (install, configure, operate): make
      the tool's own repo a single-plugin marketplace" and :1332-1334 "Never
      `<repo>/.claude/skills/`: that loads only while editing that one repo"; own-plugin skill
      cross-reference -> SKILL.md:427 "**A skill that ships in its own plugin must not point at
      another plugin's skill.**" and :429-430 "Copy the content the skill needs into its own files
      ... instead of a `REQUIRED SUB-SKILL` that crosses a plugin boundary"; contradictions:
      hit-strength vs term-overlap -> resolved, testing-skills-with-subagents.md:132-137 "A hit is
      the STRONG direction ... It is still a term-overlap match ... open the named document and
      check it states the lesson's CLAIM" ("demonstrably" no longer present); capture fallback vs
      route 1 -> resolved, testing-skills-with-subagents.md:114-116 "route 1 below (the coverage
      check against the skill file, run on the text as it stood BEFORE your edit)" agreeing with
      :148-151 "Run it on the pre-edit text ... A PRESENT verdict on the pre-edit text ends the job"
- [x] Gaps closed or declined: SKILL.md's redcheck summary ("Read a hit as strong evidence") lacked
      the reference file's open-the-document step; closed: it now reads "Read a hit as strong
      evidence once you have opened the named document and seen it state the claim (a hit is a term
      overlap, not a reading)". The same overclaim in redcheck.py's own docstring and printed note
      is a script change with tests, filed separately.
- [x] Description measured: unchanged
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
