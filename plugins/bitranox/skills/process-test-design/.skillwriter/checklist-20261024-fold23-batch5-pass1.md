# skill-writer checklist - process-test-design (memory rules folded in)

- [x] Change: references/silent-test-defeaters.md: new '## Leaked and held resources' > '### A
      lowest-free-descriptor check cannot see a leak behind a closed lower one'; SKILL.md 'Read
      references/silent-test-defeaters.md' routing paragraph gains 'asserts that no file descriptor
      leaked or that a file is held only through a memory map' -
      process-test-design/references/silent-test-defeaters.md (+ routing line in SKILL.md and the
      reference header). RED on the pre-edit snapshot: NONE. Verified: Mechanism -> probe script
      (open parent dir, open file, close dir): lowest-free before/after 3 3, leaked fd 4,
      os.fstat(4) succeeds, i.e. the lowest-free check stays green while a leak exists. EBADF on
      fstat of a closed fd is POSIX semantics. Placement: SKILL.md 'Six mechanics' list left
      untouched (count stays correct, per skeptic conflict) and routed via the existing references
      routing line instead.
- [x] Dropped as stale or unverified: Dropped the private provenance (named library, sweep/test
      identifiers) and the specific measured fd numbers 5,6,7,8 (unverified, replaced by the generic
      N/N+1 mechanism the probe confirmed).
- [x] Change: ## Adversarial inputs at the boundary - new paragraph after the axis table's 'Assert
      the SPECIFIC behavior' line, before 'How much is enough' - process-test-design/SKILL.md. RED
      on the pre-edit snapshot: NONE. Verified: ulimit -v units -> `bash -c 'help ulimit'`: 'Values
      are in 1024-byte increments, except for -t' (so KiB). Raising-generator, range(3),
      injectable-cap-plus-default-test technique taken from the current body. 36 GB / five minutes
      kept only as a measurement (unverifiable, not re-run).
- [x] Dropped as stale or unverified: Dropped private names (library, sweep number, the project with
      the 1,000,000 cap) and the date; dropped the /dev/zero env-file aside (an illustration of the
      same rule).
- [x] Change: ## Prefer real over mocked; mock only at the true edge - new bullet before the 'See
      bitranox:process-test-driven-development' bullet - process-test-design/SKILL.md. RED on the
      pre-edit snapshot: NONE. Verified: Textual tab = focus key -> installed textual/screen.py:270
      `Binding("tab", "app.focus_next", "Focus Next", show=False)`; priority bindings exist ->
      coding-python-textual/guide/input.md:286. 'Say why when bypassing' rule (skeptic's lost item)
      carried from the body. This also makes true the existing pointer in
      process-plan-writing-plans/SKILL.md:116-117 that cites process-test-design for this rule.
- [x] Dropped as stale or unverified: Dropped the private project name, the handler name
      show_attributes and the date; the concrete trap is generalised to the Textual mechanism.
- [x] Change: ## Adversarial inputs at the boundary - sentence-form paragraph directly under the
      axis table (not a table cell, per skeptic conflict) - process-test-design/SKILL.md. RED on the
      pre-edit snapshot: NONE. Verified: errno.EILSEQ exists in Python (`python3 -c 'import errno;
      print(errno.EILSEQ)'` -> 84 on Linux). APFS EILSEQ refusal itself UNVERIFIED here (no macOS);
      kept as stated in the body as observed CI behaviour.
- [x] Dropped as stale or unverified: Dropped the private project name and the 'one test skipped its
      siblings' guard' anecdote.
- [x] Change: references/silent-test-defeaters.md: '## Leaked and held resources' > '### A plain
      `mmap` keeps a descriptor, so it cannot prove a maps-only holder' -
      process-test-design/references/silent-test-defeaters.md (+ routing lines). RED on the pre-edit
      snapshot: NONE. Verified: Probe script: python3.12 plain mmap -> file still in /proc/self/fd
      (True); `trackfd=False` -> 3.12.15 TypeError "'trackfd' is an invalid keyword argument for
      this function"; python3.13 trackfd=False -> not in /proc/self/fd (False).
- [x] Dropped as stale or unverified: Dropped provenance (script name in this repo, date). Phrased
      the version requirement as 'needs Python 3.13 or later' to avoid version-history wording.
- [x] Change: ## Per-language mechanics - new paragraph right after the 'A marker only skips when
      something acts on it' paragraph, before 'Watch for two families' -
      process-test-design/SKILL.md. RED on the pre-edit snapshot: NONE. Verified: pyright narrowing
      -> `pyright --pythonplatform Windows` (1.1.407) on a two-test file: the `not hasattr(os,
      "geteuid") or os.geteuid() == 0` condition reports 'error: "geteuid" is not a known attribute
      of module "os" (reportAttributeAccessIssue)', the `sys.platform == "win32" or os.geteuid() ==
      0` condition reports nothing (1 error total). Import-time evaluation: skipif positional args
      are evaluated when the decorator expression runs at module import. os.geteuid is Unix-only.
- [x] Dropped as stale or unverified: Hint's 'build it from sys.platform/hasattr' dropped as
      CONTRADICTED by the current body and the pyright probe; hasattr is now explicitly warned
      against. Dropped memory cross-links and the CI-cell count.
- [x] Change: references/silent-test-defeaters.md: '### pytest names `tmp_path` after the test
      function' - new closing paragraph (same mechanism, per skeptic placement advice) -
      process-test-design/references/silent-test-defeaters.md (+ routing lines). RED on the pre-edit
      snapshot: NONE. Verified: Probe script on Linux: absolute bind under a 120-char dir ->
      'OSError: AF_UNIX path too long'; after chdir, `bind("s")` succeeds although the absolute path
      is 260 chars. 108 (Linux) / 104 (macOS) sun_path sizes from platform headers (macOS value not
      re-run here).
- [x] Dropped as stale or unverified: Dropped the private test-file name and date.
- [x] Review A fixed: the invalid-UTF-8 file name example no longer claims Windows creates it;
      Python decodes a bytes path there as UTF-8 with surrogatepass and raises UnicodeDecodeError
      before the filesystem (probe: b"bad\xff\xfe.txt".decode("utf-8", "surrogatepass") raises), so
      the test is POSIX-only with its own Windows skip.
- [x] Gaps declined: Pilot mechanics for driving a Textual row selection (owned by
      coding-python-textual, which the rule cross-references); the exact form of the
      default-equals-shipped-constant test (judgement the rule leaves open); the skip direction in a
      root-only test (the short-circuit pattern shown covers both directions).
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      then the scenarios each review fix touched (6 after the first review, 1 after the second).
      Every answer was a quote from the new text on both tiers in every round; no NONE. Quotes
      were checked against the files; misses traced to line wraps and the arm's own commentary.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff in three slices, then a review of each fix delta alone;
      every finding fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps
      not listed here asked for detail the rule does not need or were answered elsewhere in the
      skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history wording absent from the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
