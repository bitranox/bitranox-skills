# skill-writer checklist - meta-prune-plugin-cache (2026-08-22, new skill)

Change: a new technique skill for reclaiming disk from `~/.claude/plugins/cache` without breaking
a running session, plus the tool it uses. The load-bearing question - which versions a live
session still holds - is answered from the cache's own `.in_use/<pid>` locks, each carrying
`{"pid":N,"procStart":"<start time>"}`, with `procStart` cross-checked so a reused pid cannot pass
for the original holder. `scripts/pluginprune.py` classifies every version directory and every
`temp_*` leftover in one pass, dry run by default, `--apply` acting only on the printed plan.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique, tool-bearing. Test approach: application scenarios, two arms - a
      disk-pressure cleanup and a post-publish tidy - each run without the skill and then with it.
- [x] Scope: self-contained SKILL.md plus `scripts/` and `tests/`. No supporting reference files,
      so no routing table applies.
- [x] Name carries the `meta` category prefix from `skill-taxonomy.json` (harness authoring), and
      uses letters and hyphens only.

## RED

- [x] INHERITED COVERAGE MEASURED FIRST, not assumed: `redcheck.py --corpus-cascade` over the
      authoring machine reads 769 documents and reports STRONG inherited coverage from two of them
      for this exact lesson. So a behavioural RED on it cannot fail honestly here.
- [x] Route declared and taken: the behavioural arms still ran, and are reported below as
      CONTAMINATED evidence about instrument choice only; the load-bearing RED is a code
      red-green cycle plus a mutation sweep, which no inherited context can forge.
- [x] Behavioural RED, both arms, each ending in a `Skill gaps` section. Both quote the inherited
      document verbatim, which is the contamination showing itself - and both still fail on the
      question the skill exists to answer:
      - arm 1 reaches for `lsof -p <PID> | grep plugins/cache` to find the session's version,
        an instrument that cannot work here;
      - arm 2 reports "I have no confirmed file or command that reports the plugin version this
        specific live session currently has loaded" and works around it by asking a person to
        run a slash command;
      - arm 1 calls treating `temp_git_*` like `temp_subdir_*.clone` "my judgment call, not a
        confirmed rule";
      - arm 2 looks for the temp leftovers inside the marketplace directory, one level below
        where they are;
      - both write `rm -rf` loops with no plan, no per-directory reason and no refusals.
- [x] The `lsof` premise is verified against the real machine rather than inherited: with four
      live sessions provably holding locks, `lsof +D` over the whole cache returns 0 lines, and
      `/proc/<pid>/fd` and `/proc/<pid>/maps` for two of those sessions contain 0 references to
      the cache. The prohibition in the skill is measured, not repeated.
- [x] Code RED observed before the tool existed: the whole suite fails at import
      (`No module named 'pluginprune'`), then each test in turn against the real fixture trees.

## GREEN

- [x] Frontmatter is `name` + `description` only; description is 317 characters, third person,
      "Use when ...", triggers only, and summarises no workflow.
- [x] Keywords a searcher would use are present: disk filling, plugin cache, published version,
      `temp_subdir_*.clone`, `temp_git_*`, marketplace add/update.
- [x] 25 tests pass against real directory trees, no monkeypatching. The liveness detector is
      exercised with this pytest process as the known positive and a genuinely reaped subprocess
      as the known negative, and separately with a live pid whose recorded start time disagrees.
- [x] Bundled script imports in a bare environment: standard library only, no PEP 723
      dependencies to provision.
- [x] The tool is run against a real 1.4 GB cache, not only fixtures. It identifies four live
      sessions across their locks, keeps every version they hold, keeps the `installPath` version
      of a plugin whose `.in_use` directory is empty, and plans 602.7 MB.
- [x] Behavioural GREEN, both arms, same scenarios, each ending in a `Skill gaps` section. Both
      close every RED gap: `.in_use` locks cross-checked on pid AND start time, `lsof`/`pgrep`
      explicitly declined with the reason, the temp leftovers placed at the cache root, the tool
      run dry first, and hand-written `rm -rf` refused. Arm 2 also declines the newest-version
      heuristic unprompted.

## REFACTOR

- [x] Every gap both GREEN arms reported is closed or declined with a reason:
      - CLOSED - "the tool covers version dirs, do I still hand-delete the temp ones": the tool
        section now states it does both in ONE pass.
      - CLOSED - a manual mtime check run before the tool: the text now says the tool reads each
        leftover's own mtime, so no separate age check is needed.
      - CLOSED - "a marketplace you only consume is not prunable" read as a per-marketplace rule:
        it is now stated as a per-plugin test, with mixed marketplaces named.
      - CLOSED, in the TOOL - a second session claiming a version between the plan and the apply.
        `apply_plan` re-checks each version directory's lock and refusal immediately before
        removing it, so the listed set can shrink but never grow.
      - DECLINED - the script's absolute path. Both arms resolved it with `find`, which is
        correct; a real invocation announces the base directory, and hard-coding an install path
        would be wrong on any other machine.
      - DECLINED - guidance on uninstalling unused plugins for the space they hold. That is a
        different action with different consequences, and it is a person's decision.
      - DECLINED - converging the version by asking for `/plugin marketplace update` and
        `/reload-plugins`. That mutates state to simplify a read, and the locks answer the
        question directly.
- [x] GREEN diffed against RED in BOTH directions. Everything GREEN dropped is a proxy the skill
      deliberately supersedes (`lsof`, `pgrep`, transcript mtimes, "keep the two newest") or an
      out-of-scope action declined above. No baseline finding of value is missing from GREEN.
- [x] Each fix verified by quote-back against the shipped text, not by paraphrase.
- [x] VACUITY CHECK: 7 mutations applied to a copy of the tool, each reintroducing the exact
      defect one test claims to guard - the `procStart` comparison dropped, the only-version rule
      dropped, `pid_alive` always true, the symlink refusal dropped, the temp age check dropped,
      apply re-scanning instead of using the plan, and the apply-time lock re-check dropped. 7 of
      7 detected, 0 absorbed. A first, badly aimed liveness mutation left the suite green and was
      re-aimed rather than recorded as a pass.

## Quality

- [x] Quick reference table of common mistakes, each row naming what happens rather than a verdict.
- [x] No flowchart: the decision is a list of keep reasons, which a table carries better.
- [x] No narrative and no private provenance in the skill or in this artifact.
- [x] Every path, value and identifier in the skill is generic; no address, hostname, user or
      machine path appears (`grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/'` is empty).
- [x] No external doc reference: the body is self-sufficient and sends the reader to `--help`,
      which is install-local and cannot rot.
- [x] Body is 735 words, above the 500-word target for a technique skill. Kept: the `.in_use`
      mechanism and its staleness rule are the whole contribution, and the mistakes table is
      built from measured baseline failures. Trimmed twice for wording, not for content.
- [x] Security review of the change: no credentials, no private hosts or addresses, no `eval`,
      no `shell=True`, no untrusted input. The only destructive call is `shutil.rmtree`, reached
      only for a path that passed the symlink, filesystem-root, cache-root and containment
      refusals and carries no live lock.
- [x] Derived artifacts regenerated: `docs/skills.md`, `hooks/skill_triggers.json`, and the two
      skill counts in `README.md`. `repo-gate.py --ci` passes.
