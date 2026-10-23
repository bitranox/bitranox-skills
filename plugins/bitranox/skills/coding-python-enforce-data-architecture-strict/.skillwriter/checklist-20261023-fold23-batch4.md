# skill-writer checklist - coding-python-enforce-data-architecture-strict (fold of memory rules into the skill)

- [x] Change: Instructions: step 3 'Refactor the Code' (new last bullet) + step 1 DoD 'Input/Output
      Boundaries' (two new checkboxes). Verified against ground truth: Fix landed and example
      accurate -> bmk/src/bmk/adapters/stagerunner/venv.py:138-156 (_UvPythonEntry declares version,
      version_parts, implementation: str; docstring :145-149 states several implementations per X.Y,
      uv venv --python <minor> provisions CPython, PyPy higher patch would never match and rebuild
      every run); :219 `if entry.implementation == "cpython" and ...` in _highest_installed_patch;
      rebuild path :656-677 _discard_venv_on_wrong_python rmtrees venv when venv_version !=
      latest_installed_patch. Build-variant discriminator -> venv.py:157-164 variant/key +
      is_default_build property, used at :613-615 (`entry.implementation == "cpython" and
      entry.is_default_build`).
- [x] Claims the source contradicts were dropped or corrected; machine-local figures, private names
      and incident history were not carried over.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against the pre-edit snapshot (partial for scenario
      1). Only a verbatim quote from the snapshot counts, so context inherited from this machine
      cannot satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files, in four rounds: after the edit,
      after the first review's fixes, after the delta review's fixes, and a final round on the
      questions the last fixes touched. Every scenario was answered with a quote from the new text
      on both tiers in every round; no NONE.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or recorded below.
- [x] Gaps closed or declined: declined - the exact uv JSON key for the build variant (the rule
      names the discriminator kind; the review confirmed uv reports it), whether the venv side
      compares implementation too (the rule governs the consumer's own decision fields).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, repo file paths or reserved examples.
