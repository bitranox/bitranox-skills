# skill-writer checklist - meta-consolidate-claude-md (new skill)

Skill type: technique with a discipline core (the refusal to lift before verifying).
Origin: extracted from a live consolidation across one 92-file tree on 2026-08-02, where every rule
below was learned by getting it wrong first.

## PLAN
- [x] Type identified: technique + discipline.
- [x] Scope: measure -> verify -> converge -> lift, plus the guards. Does NOT restate the
      reachability invariant (points at `meta-dream-tree` -> dream-passes.md, the single authority).
- [x] Called from `meta-dream-crosstree-deep` step 3, the CLAUDE.md reconciliation step, which
      previously said only "CONSOLIDATE ... UP to their common ancestor" with no procedure.

## Every rule traces to an observed failure, not to theory
- [x] "Measure before acting": the first pass assumed `rotek/apps` was the common ancestor; computing
      it from member paths showed several groups actually span `public/` and `rotek/`, so `projects/`
      was correct.
- [x] "Split variance by cause": sections embedding the package name can never be lifted. Without
      that split the candidate list is ~2600 lines; with it, far smaller and actually correct.
- [x] "Verify, do not run a popularity contest": user correction mid-run - "they might be different
      but not necessarily good or correct". Verification then found a `menu` target documented in 5
      variants and defined in 0 Makefiles, 4 files claiming `send-email`/`send-notification` fail
      when both are implemented, a deleted systemprompt file still referenced in 3 repos, a
      cyclomatic limit of 5 contradicting the source file's 10, and a `.env` mode 0600 claim against
      an actual 777 on this mount.
- [x] "Spot-check the agent's evidence": one report claimed a `hello` target existed nowhere; it
      exists in exactly one repo. Another flagged a dead wikilink that resolves fine because the
      engine folds `_` to `-`. Both would have shipped a wrong fix.
- [x] "No double heading": the mechanical version appended a second `## Test Fixtures` to a file that
      already had one from an earlier pass, because the guard only knew about homes claimed in that
      run. Fixed by seeding it with headings already present, then by making the test precise -
      collision only when a NON-MEMBER file under the target keeps the heading.
- [x] "Preserve repo-specific rows": the make-targets tables carried per-repo `run` and
      `testintegration` descriptions that a whole-section delete would have destroyed.
- [x] "Git never gates the trim": shipped as a fix to `meta-dream-crosstree-deep` in 5.145.1 after
      the old umbrella-repo rule stalled a correct consolidation. Restated here as a pointer.
- [x] "Test, not census": a banner was about to claim "verified <date>: these repos are not
      template-built"; the user pointed out those repos acquire `pyproject.toml` as they are built
      out, so the claim would rot while reading as checked.
- [x] "Walk, never the session grep": measured 73 files by walk vs 17 by grep on this tree; the
      shipped `grep_all` jig (5.146.0) exists for exactly this and is cited.
- [x] "Snapshot out of the tree": `git status --porcelain` is empty for a gitignored file and for a
      clean one alike, so a git-based revert would have restored 20 of 45 edited files.

## GREEN
- [x] Front matter: `name` + `description` only; `meta-` prefix per skill-taxonomy.json.
- [x] Description is trigger-first and names symptoms (a section repeated in 20 repos, a rule at
      three levels, a table that no longer matches its tool), not a workflow summary.
- [x] Rationalization table covers the six excuses actually encountered.
- [x] Cross-skill references name the owning skill (`compuse-toolbox` for `grep_all`,
      `meta-dream-tree` for the invariant); no rule restated from either.
- [x] ASCII only.

## Deliverables
- [x] SKILL.md; call site in `meta-dream-crosstree-deep` step 3.
- [x] `plugin.json` bumped; `skill_triggers.json`, `docs/skills.md` and the README count regenerated.
