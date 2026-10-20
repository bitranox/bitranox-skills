# skill-writer checklist - process-test-design (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: ## Run in a clean, project-correct environment (new closing paragraph after the 'Keep
      .venv out of git' bullet, before '## A permission-wall test on Windows'). Verified against
      ground truth: windows-latest is a real CI cell -> .github/workflows/ci.yml:37 'os:
      windows-latest'. sys.executable -c is the established throwaway-child idiom here -> 20 test
      files under hooks/tests and skills/*/tests use [sys.executable, "-c", ...] (e.g.
      hooks/tests/test_tmp_prune.py:98). Runner PATH contents (Git usr/bin) and the
      default-Git-install PATH are NOT pinned anywhere in the repo (grep of docs/ and hooks/ for
      windows-latest/Git for Windows finds only unrelated mentions), so stated as observed behaviour
      ('has been observed to carry'), with the shutil.which("true") -> None observation from the
      fact body.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): NONE for scenario 1.
      Behavioural RED replaced on purpose: each rule is in the always-loaded memory index of the
      authoring machine (inherited coverage), so the RED is a quote-back against the pre-edit file.
- [x] GREEN quote-back on haiku and opus against the edited files; every quote checked against the
      skill's files (a fragment check, then a grep of each inserted rule's lead sentence), all
      present.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus for every scenario; tiers haiku and
      opus, one cell per scenario per tier.
- [x] Gaps closed or declined: declined - a substitute for every coreutils child (the
      `sys.executable -c` form covers them).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
