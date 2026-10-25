# skill-writer checklist - coding-python-uv (memory rules folded in)

- [x] Change: 09-pip-interface.md > Locking requirements, directly after the 'Note by default the
      `uv pip compile` output is just displayed...' line; SKILL.md Cross-Reference table row after
      'Cache problems / disk space' - coding-python-uv/09-pip-interface.md (plus routing row in
      SKILL.md Cross-Reference by Scenario). RED on the pre-edit snapshot: NONE. Verified: -o -
      writes ./- with empty stdout and rc 0 -> scratch probe on uv 0.13.0 (`uv --version` = uv
      0.13.0): `uv pip compile -q -o - r.in > out.txt` gave rc=0, out.txt 0 bytes, file `-` 122
      bytes containing the pinned idna==3.20 output. Omitting -o pipes to stdout -> `uv pip compile
      -q r.in` printed the requirements. `-` as input reads stdin -> `echo idna | uv pip compile -q
      -` printed the requirements (also 09-pip-interface.md:380 example). git add -A sweep and
      empty-stream signature carried from the body (consequence, not tool behaviour). Table row
      fitted to existing widths; reformat_tables.py --check --strict: Unchanged.
- [x] Dropped as stale or unverified: Body's 126-byte figure (input-dependent; not carried). Hint's
      'references/' location (no references/ dir; file is at the skill root). Nothing contradicted.
- [x] Change: 05-resolution.md > Multi-Version Resolution, directly after the existing 'a package
      may be listed multiple times...' sentence (extends it, before --fork-strategy) -
      coding-python-uv/05-resolution.md (plus routing row in SKILL.md). RED on the pre-edit
      snapshot: partial. Verified: Packages repeat per fork -> 05-resolution.md:194 (upstream).
      tomllib probe on a real public forked lock (3 resolution-markers): 102 [[package]] entries,
      102 distinct (name, version) pairs, but a by-name dict has only 97 keys; duplicated names each
      carry two versions (e.g. filelock 4.1.0/4.2.1). So a name-keyed dict silently drops 5 entries
      with no error, confirming the undercount mechanism and the entries-vs-names check.
- [x] Dropped as stale or unverified: Body's example list of duplicated packages in a named lock
      (stale: the set now differs) and the project name; no numbers from that lock carried into the
      skill.
- [x] Change: 10-configuration.md > Caching > Dependency caching, after the escape-hatch list and
      the 'As a special case...' line; 08-building-and-publishing.md > Verifying Your Package, after
      the --refresh-package Tip - coding-python-uv/10-configuration.md (plus pointer in
      08-building-and-publishing.md and routing row in SKILL.md). RED on the pre-edit snapshot:
      NONE. Verified: Flags exist -> `uv pip install --help` on uv 0.13.0 lists `-n, --no-cache`
      ('Avoid reading from or writing to the cache, instead using a temporary directory'),
      `--refresh`, `--refresh-package`. Conflict with upstream advice reconciled explicitly:
      10-configuration.md escape-hatch list (--refresh) and :443 note ('In most cases, `--refresh`
      should be used instead of `--no-cache`') and 08:377 Tip (--refresh-package) are named as the
      advice that does not hold in this case. --refresh-failed / --no-cache-worked kept as observed
      behaviour with 'uv version not recorded' (body: 'uv version not noted'); propagation retry
      from the body's later observation. Could not re-check (needs a fresh publish).
- [x] Dropped as stale or unverified: Project name and dates from the body; urllib code snippet
      replaced by the plain URL + header; nothing contradicted.
- [x] Change: 10-configuration.md > Caching > Dependency caching, directly after the just-published
      paragraph (both follow the escape-hatch list and the mtime rule for local archives) -
      coding-python-uv/10-configuration.md (plus routing row in SKILL.md). RED on the pre-edit
      snapshot: NONE. Verified: Scratch probe on uv 0.13.0 with an isolated UV_CACHE_DIR and a
      uv_build wheel mylib-0.9.3: first run loaded VALUE='old' from
      cache/archive-v0/dhVO.../lib/python3.15/site-packages; after rebuilding at the same version
      (new content) `--reinstall --with` loaded 'new' from a NEW archive-v0 hash dir; rebuilding
      again with the old mtime restored via touch -d @<sec> (and again with near-equal size) also
      loaded the new value. So the staleness did NOT reproduce here, and the text states that
      measurement and keeps the stale-archive case only as observed behaviour, uv version
      unrecorded. Two unchanged runs reused the same archive-v0 hash (oSwdIGapZ0XUeWk0 twice) -> the
      hash diagnostic. `--no-cache` run imported from a temporary dir ( -> 'uses a temporary cache';
      help text confirms. Upstream mtime claim 10-configuration.md (For local dependencies...) is
      consistent with the probe; the inserted text reconciles with it rather than contradicting it.
- [x] Dropped as stale or unverified: Body's claim that uv keys the unpacked archive on name and
      version so ANY rebuild at the same version is served stale: not reproduced on uv 0.13.0
      (rebuilds were re-read), so it is not stated as the mechanism; it survives only as an
      observed, unversioned case. Host name, /root/.cache paths, project and probe names, date
      dropped. Skeptic's 'this contradicts the mtime-based caching' framing softened to 'the mtime
      rule predicts a fresh read, and it was re-read on 0.13.0'.
- [x] Review A fixed: the rebuilt-wheel paragraph now tells a test harness that re-runs a rebuilt
      same-version wheel to pass --no-cache on every run and not rely on the --reinstall or uv cache
      clean escape hatches (the vendored upstream list above it is left unchanged).
- [x] GREEN gap fixed: the uv.lock diff paragraph names per-name version sets as the way to count
      moves, downgrades included, and says newest-only comparison misses a move in a fork that does
      not hold the newest version.
- [x] Measured against the fact body: on uv 0.13.0 a rebuilt same-version wheel was re-read every
      time (new and restored mtime), so the stale-archive case is kept only as observed behaviour
      with the version not recorded, and the rule is to prove which build loaded.
- [x] Gaps declined: a code snippet for the lock diff (the rule and its sanity check suffice);
      behaviour of uv releases older than the measured one (not measured).
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      then the scenarios each review fix touched (9 after the first review, 1 after the second).
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
