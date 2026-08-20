# skill-writer checklist - meta-claude-hooks (new skill), 2026-08-20

Change: a new reference/hub skill for the Claude Code hook API, plus `scripts/hookdoc_stamp.py`,
which compares the shipped reference against the upstream docs and reports drift.

## PLAN

- [x] Skill type: **reference/hub**. Test approach is therefore retrieval plus application, not
      pressure scenarios: the failure mode for a reference is a silent gap, not a violated rule.
- [x] Scope: hub `SKILL.md` plus four reference files, a bundled script, and its tests.
- [x] Prior art surveyed. Nothing in the catalogue documents the hook API; the knowledge existed
      only implicitly across 44 hook scripts and one inventory table in `docs/architecture.md`.
      Adjacent skills own packaging, auditing and settings editing, and are cross-referenced
      rather than restated.

## RED

- [x] Three scenarios drafted and run against `bitranox:baseline-probe`, which has no filesystem
      tools, so no arm could read the answer off disk.
- [x] Contamination checked before believing any arm. `redcheck.py --corpus-cascade` reported
      INHERITED COVERAGE for all three at the default rarity and clean for all three at 0.01, so
      the term-overlap heuristic was inconclusive here. A direct control over the inherited
      cascade and memory fact bodies decided it: `FileChanged`, `Last-Modified` and `ETag` occur
      **zero** times, while `permissionDecision`, `additionalContext` and "fails open" occur in
      the cascade and in 2 to 8 fact bodies.
- [x] Scenario 2 (the deny/fail-open contract) is therefore recorded as **unable to fail
      honestly on this machine** and was not run as a behavioural arm. Its coverage is asserted by
      a text check of the artifact instead: `references/io-contract.md` states the exit-1, exit-0
      stderr and silence-is-not-approval rules, and `coverage` proves every stamped name is
      documented.
- [x] RED A (weak arm, file-watching): FAILED. Invented a `hooks.preTool` settings schema that
      does not exist, never reached `FileChanged`, and explicitly rejected the alternatives for
      plausible-sounding reasons. Its own gaps section conceded it guessed the entire config
      format.
- [x] RED B (capable arm, same scenario): FAILED, and more usefully. It stated "Claude Code has
      no passive filesystem-watch hook - every hook fires at a point in the conversation/tool
      loop, not asynchronously when a file mutates", then enumerated "the events available" as
      nine. `FileChanged` does exactly what it declared impossible. A confident false absence
      claim is the failure this skill exists to prevent.
- [x] RED C (drift-detection design): **PASSED - no gap.** A capable model produced content
      hashing, a structural/cosmetic split, four verdicts including unreachable, and both
      controls. Investigated per the falsely-passes rule: the cause is a **telegraphed scenario**
      (it asked for a check that does not alarm on copy-editing and for proof the check is not
      always saying "no change", which names the answers). Conclusion recorded: designing drift
      detection is not a skill gap, so the skill ships the working checker and the measured
      domain facts rather than teaching the design.

## GREEN

- [x] Both arms re-run with the skill text supplied, same scenario.
- [x] GREEN A (weak arm): reached `FileChanged`, cited the filesystem-watcher reason, and
      rejected `PostToolUse` because it only sees Claude's own tool calls. The core gap is closed.
- [x] GREEN B (capable arm): reached `FileChanged`, produced the correct nested settings JSON, and
      rejected `PostToolUse`, `InstructionsLoaded` and `ConfigChange` for the right reasons. It
      then reported two contradictions in the text, both of which turned out to be real defects,
      and are the highest-value findings of this change.
- [x] Every dispatch, RED and GREEN, required a `Skill gaps` section, and each reply's list is
      recorded here.

## REFACTOR

- [x] GREEN A gap "the complete JSON schema for the hooks array is not shown" is **closed**: the
      three-level config skeleton now sits in `SKILL.md` itself, because an agent routed straight
      to an event page otherwise has to invent the wrapper, and inventing it is exactly what both
      RED arms did.
- [x] GREEN A gap "not clear which directory the handler runs in" is **closed**: added
      "Handlers run in the current directory, with Claude Code's environment" to
      `references/configuration.md`, with the pointer to `${CLAUDE_PROJECT_DIR}`.
- [x] GREEN A gap "no documented limit on `additionalContext`" is **declined as already covered**:
      `references/io-contract.md` states the 10,000 character cap and the write-to-file fallback.
      The gap reflects the extract given to the arm, not the shipped file.
- [x] GREEN A gaps on handler invocation mechanism and on watching a file in a subdirectory are
      **declined as out of scope**: the first is marketplace packaging, owned by
      `bitranox:meta-skill-writer`; the second is answered by `watchPaths`, which
      `references/events.md` documents.
- [x] GREEN B finding 1, **a real defect, now fixed**: the text named two different ways to reach
      Claude's context and did not reconcile them for this event. Checked against upstream:
      `FileChanged` reads **only** `watchPaths` and `systemMessage`, `systemMessage` is a terminal
      notification **to the user**, and `FileChanged` never appears in the `additionalContext`
      placement table. A `FileChanged` hook therefore cannot put anything into Claude's context by
      itself. Both GREEN arms wrote a hook that looks correct, exits 0 and reaches nobody - one
      using `additionalContext`, one using `systemMessage` believing Claude reads it.
      `references/events.md` now states the limit and gives the two-hook pairing that does work.
- [x] GREEN B finding 2, **a real self-contradiction the edit itself introduced, now fixed**: the
      matcher paragraph said the value is unconditionally split into literal filenames, then said
      the narrow exact-match set pushes anything else onto the regex path, which reads as two
      different rules for one string. Reconciled explicitly: the watch list is always literal
      `|`-separated segments while filtering treats the same string as a regex, so a dot is
      harmless, which is why upstream's own example is `"matcher": "data.csv"`.
- [x] GREEN B finding 3 is **partly closed**: the bootstrapping sentence for a file outside the
      working directory now names the concrete route (`SessionStart` or `CwdChanged` `watchPaths`).
- [x] GREEN B findings 4 and 5 (handler type and stdin delivery; which settings file) are
      **declined as harness artifacts**: both are answered in `SKILL.md`, `references/io-contract.md`
      and the hook-locations table, none of which were in the extract the arm was given.
- [x] Diffed GREEN against RED in both directions. Nothing the baseline produced is missing from
      GREEN: both RED arms produced only the invented schema and the wrong event, and GREEN
      retains the correct rejection reasoning while adding the right event.
- [x] Coverage gate re-run after every edit; `complete`, 31 of 31 events, 20 of 20 required names.

## Verification of the shipped checker

- [x] The extractor was wrong twice before it was right, and each failure was measured against the
      live page rather than argued: column-0 fence anchoring yielded **17 of 31** events, plain
      toggling yielded **0 of 31**, and CommonMark fence matching with an arbitrary opener info
      string yields **31 of 31**, exactly the known set with no extras. The cause is that upstream
      writes fences as ```json theme={null}: a pattern accepting only a bare language word rejects
      the opener and then reads the bare closer as an opener, inverting state for the rest of the
      document. A fixture carries that exact shape so the regression stays locked.
- [x] `Last-Modified` was measured identical within one second across four unrelated doc pages, so
      it is the site build time and cannot signal a page change; there is no `ETag`. The design
      uses a content hash for that reason, and this is stated in the script's own docstring.
- [x] The known-negative `selftest` produces four **different** verdicts over four fixtures. A
      comparator stubbed to answer CURRENT to everything makes it fail, so the proof itself is
      shown capable of failing.
- [x] A truncated body yields BROKEN, not STRUCTURAL. Without that control a short read reports as
      "every event was removed", which is both false and maximally loud.
- [x] Every path that cannot reach the network yields BROKEN and never CURRENT: fetch failure,
      non-200, wrong content type, timeout. The timeout is a hard total wall on a daemon thread,
      because `urlopen(timeout=)` bounds each socket read rather than the call.
- [x] Mutable state lives in `~/.claude/bitranox-hookdoc/`, never in the skill dir, because the
      installed skill sits inside the marketplace git clone that `/plugin marketplace update`
      pulls. A test asserts a `check` run leaves the skill dir byte-identical.
- [x] `stamp --write` runs `coverage` first and refuses while a newly-appeared event is
      undocumented, so the stamp cannot move ahead of the documentation it certifies.
- [x] The coverage bar is split: events, env vars and handler types are blocking, while the 130
      example field names are advisory. Requiring all of them would fail forever on per-tool
      schema detail the skill delegates upstream, and a gate that can never go green is switched
      off.
- [x] The coverage check found three env vars missing from the first draft
      (`CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`,
      `CLAUDE_CODE_DISABLE_PERMISSION_PROMPT_NOTIFY_HOOKS`, `CLAUDE_CODE_USE_POWERSHELL_TOOL`);
      all three are now documented and the gate passes.

## Quality

- [x] Frontmatter carries only `name` and `description`; `name` is 18 chars, `description` 340.
- [x] Description is a single-line plain YAML scalar starting "Use when", and distils to 14
      router keywords, well past the 3-keyword floor.
- [x] Name `meta-claude-hooks` passes `check_skill_naming`: `meta` is a registered category
      documented as covering harness and hooks config. The bare `claude-hooks` the request named
      is not legal, since `claude` is not one of the 26 categories.
- [x] Hub routing table lists concrete symbols per file, and the body carries the required
      "Use the Read tool to load the file identified as relevant" instruction.
- [x] Routing table coverage checked file-to-table: all 31 event names appear in the events row,
      and each other row names the sections its file actually contains.
- [x] Routing table accuracy checked table-to-file: every term listed resolves in the named file.
- [x] External references are install-reachable: the two upstream URLs are default-branch links to
      raw markdown, and no reference points at a package-local path that does not ship.
- [x] Body is 1162 words. A reference/hub skill may exceed the 500-word target; the body stays an
      index and the detail sits in the four reference files.
- [x] No narrative, no operator instructions, no scratch paths, in the skill or in this artifact.
- [x] Every address, host and path is a reserved documentation value. Checked:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/'`
      over the shipped files returns **nothing**. Event input schemas are given as field tables
      rather than pasted JSON examples, so upstream's sample paths never entered the skill.
- [x] ASCII only, LF endings; a non-ASCII sweep over the skill returns nothing.
- [x] Security scan of the change: no credentials, tokens, keys or private hostnames. The script
      makes one GET to a fixed public docs URL, passes no shell string anywhere, and writes only
      inside its own cache dir and the stamp.

## Tests and deployment

- [x] 53 pytest tests beside the script, all passing under CI's dependency set
      (`pytest PyYAML lxml defusedxml ruamel.yaml httpx2`).
- [x] No test touches the network; every verdict is reachable through the `--body` seam or an
      injected fetcher. `check` is deliberately not a pytest test, so no test can pass by
      silently skipping a fetch.
- [x] `httpx2` is imported lazily inside `_fetch` with a stdlib fallback, and a test asserts the
      module has no third-party import at module scope, because the repo gate imports test modules
      bare and does not provision PEP 723 dependencies.
- [x] Script basename `hookdoc_stamp.py` verified globally unique across the repo.
- [x] Derived artifacts regenerated: `skill_triggers.json` (79 skills) and `docs/skills.md`.
      README count raised to 79 in both spots.
- [x] `plugins/bitranox/.claude-plugin/plugin.json` bumped 5.207.0 to 5.208.0 (a new skill is a
      MINOR change), with a matching CHANGELOG entry.
