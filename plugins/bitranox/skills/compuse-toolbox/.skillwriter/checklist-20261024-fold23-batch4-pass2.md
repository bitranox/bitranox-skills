# skill-writer checklist - compuse-toolbox (memory rules folded in)

- [x] Change: references/anchored-edits.md '## Multi-edit hygiene' (first bullet REPLACED by three
      bullets); SKILL.md routing list under 'Three traps no --help covers' -
      compuse-toolbox/references/anchored-edits.md (+ routing line in compuse-toolbox/SKILL.md). RED
      on the pre-edit snapshot: partial. Verified: anchor_edit batch is all-or-nothing: CONFIRMED
      (skill row 'every count (default 1) checked before ANY write'; skeptic cites
      anchor_edit.py:36). grep -c counts lines, not occurrences: CONFIRMED by a scratch probe - a
      file with 'old_key old_key\nold_key' gave grep -c 2, grep -oF|wc -l 3, str.count 3.
- [x] Dropped as stale or unverified: Corrected the skeptic's amended text: it prescribed `grep -c
      -F ANCHOR FILE` for counts, which undercounts two hits on one line (measured), so the text
      uses str.count in a dry pass or grep -o -F | wc -l and warns against grep -c. Reconciled the
      CONTRADICTING old bullet ('Write after each edit, or report which edits were applied on
      failure') by replacing it; its valid half (a run that applied nothing looks like 'did not
      run') is kept as the on-refusal bullet. Dropped private repo name, dates and recurrence count.
- [x] Change: ## Why a jig over a one-liner - new bullet directly before '**The others encode the
      trap.**' (the ci_wait table cell is the widest in its column, so a cell append would re-pad
      the whole table) - compuse-toolbox/SKILL.md. RED on the pre-edit snapshot: partial. Verified:
      Release template trigger is `on: push: tags: ['v*']` + workflow_dispatch, no release event:
      CONFIRMED (lsdsk/.github/workflows/default_release_public.yml lines 9-13, `name: Release` line
      1). --event is free text passed server-side, default excludes schedule: ci_wait.py --event
      help text (~line 928) and _EXCLUDED_BY_DEFAULT. no-runs summary names the event filter:
      ci_wait.py verdict() ~317. Exit-2 states timeout/no-runs/error/pending-approval/stuck-queued:
      _EXIT_CODES ci_wait.py:141; bad ref/flag also exit 2: docstring :82-84. Summary format
      `Workflow=state`: _named(). Last line `{state}: {summary}` to stderr on non-zero: ci_wait.py
      ~1083; --json data.state and data.runs: ~1071; databaseId in _FIELDS :107. --timeout default
      1500, --error-grace 300, --settle 20: argparse block 890-930. A green-first set before the
      release run registers follows from the settle mechanism (skill row: settle BOUNDS the window).
- [x] Dropped as stale or unverified: Dropped the body's claim that a transient 1 s gh timeout
      produces exit 2 (stale: --error-grace retries failing gh for 300 s, per skeptic and
      ci_wait.py:18-23). Dropped the repo-specific '25 minutes for a windows-latest cell' timing and
      the internal workflow file name; generalised to '--timeout default 1500 s'.
- [x] Review B nits fixed: the --timeout wording; the anchored-edits two-phase rule matches
      anchor_edit.py (plan_batch checks every file before commit_batch writes; an IO failure names
      the files already written); a multi-line anchor is counted with the text.count dry pass, since
      grep reads each pattern line as its own pattern.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      every scenario again after the first review's fixes, then the scenarios each later fix
      touched. Every answer was a quote from the new text on both tiers in every round; no NONE.
      Quotes were checked against the files (6-word windows; misses traced to line wraps,
      markup and line-number prefixes).
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps not listed
      here asked for detail the rule does not need (out of scope) or were answered elsewhere in
      the skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history finder clean on the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns except where the file keeps one line per paragraph or list item.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
