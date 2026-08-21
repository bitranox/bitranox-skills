# skill-writer checklist - meta-context-watcher (new skill), 2026-08-21

Change: a new technique skill for writing a session handover, plus the `Stop` hook
`context-watcher.py` that measures context and offers the handover once past a threshold, its
tests, three config knobs, and the doc rows.

## PLAN

- [x] Skill type: **technique**. The failure mode for a technique skill is a silent gap or a
      wrong-shaped artifact, not a violated rule, so the test is an application scenario -
      produce a real handover - rather than a pressure scenario.
- [x] Scope: self-contained `SKILL.md`, no reference files. The hook is a sibling artifact, not a
      bundled script, so it lives in `hooks/` with its tests in `hooks/tests/`.
- [x] Prior art surveyed. Nothing in the catalogue writes a session handover. `meta-dream-nap` and
      `meta-dream-tree` consolidate MEMORY and the nap explicitly prunes task state as noise;
      `meta-self-improve` captures durable facts. All three are cross-referenced and disambiguated
      rather than restated.
- [x] Threshold researched rather than guessed: Claude Code auto-compacts at about 83% of the
      window and that ceiling only lowers; measured context-rot onset is about 300-400k tokens on a
      1M window and about 50k on a 200k one. Those two disagree on a big window, which is why the
      threshold is `min(pct of window, absolute cap)` rather than either alone.

## RED

- [x] Contamination checked before running any arm. `redcheck.py --corpus-cascade` over the repo
      read 691 documents and reported `clean - no inherited coverage, no telegraphing found`.
      Recorded with its own caveat: clean means NOT CAUGHT, not absent.
- [x] Baseline run on `bitranox:baseline-probe` (no filesystem tools, so no arm could read the
      answer off disk), model pinned to `sonnet`, scenario deliberately un-telegraphed - it asked
      for "the file that makes that possible" and never named a section.
- [x] RED **FAILED**, and in the shape the skill now counters. The baseline spent the file on
      re-derivable material: a full "Conventions this repo enforces" section restating CLAUDE.md,
      a git-log dump, a "Recommended first steps" list of commands the reader could have run, and
      a provenance preamble headed "How this handover was produced". Task state was absent.
- [x] Its own gaps section named two of the counters verbatim: "I was unsure whether to include
      the full repo-wide memory index ... versus only the handful of rules that are operationally
      load-bearing", and "I do not know this project's convention for where a handover file like
      this should live, whether it should be committed or gitignored".

## GREEN

- [x] Same scenario, same model, skill pasted in full so the version under test was the working
      copy, not an installed one. Session facts supplied so task state was available to record.
- [x] GREEN **PASSED**: produced exactly the named sections, with no CLAUDE.md restatement, no git
      log dump and no provenance preamble. It told the user to type `/clear` and stated it could
      not run the command itself, and it flagged that the file must be gitignored.
- [x] Both dispatches asked for a `Skill gaps` section and both replied with one.
- [x] Diffed GREEN against RED in BOTH directions. Nothing of value was lost: RED's only section
      without a GREEN counterpart was "What is NOT known and must be reconstructed", which GREEN
      covers as "Not done this session (flagging, not doing)". Every other RED section that
      disappeared was re-derivable content the skill deliberately forbids.

## REFACTOR

- [x] GREEN reported five gaps; two were real defects in the skill text and are now closed:
      - it had to guess repo-relative paths from bare filenames -> "Files that matter" now requires
        PATHS, not filenames.
      - it observed that "commit status is silent ... uncommitted work needs different care than
        committed-but-unpushed" -> a "Committed, or not" item was added.
- [x] The other three are DECLINED with reasons: no filesystem access (a property of the probe
      type, not of the skill); unknown knob names and version number (absent from the supplied
      facts, and the reply correctly pointed at a diff instead of inventing them); step 1 not
      executable inside a single reply (the reply flagged the owed capture, which is the behaviour
      the step wants).
- [x] Both fixes verified by quote-back against the artifact: `Committed, or not` and
      `repo-relative PATHS` are present as governing text, not paraphrase.
- [x] No undecided gap remains.

## Quality

- [x] Frontmatter is `name` + `description` only; description is a single-line plain scalar,
      trigger-first, and names no workflow. `cso_failures` and `check_skill_naming` both return
      none.
- [x] Category prefix `meta-` is a registered taxonomy key. A bare `context-watcher` is blocked -
      `context` is not a category, and opening one for a single member was rejected.
- [x] No session narrative or private provenance in the skill or this artifact.
- [x] No machine-specific address, host or path: `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/'`
      over the SKILL.md is clean.
- [x] Token budget: **642 words, over the 500-word target and recorded rather than gamed.** The
      overage is the RED-derived rationalization table plus the two sections this repo's
      conventions require of a hook-paired skill (`When it fires on its own`, `Not the same as its
      neighbours`). One trim pass already removed the restated one-rule elaboration and the
      duplicated procedure step; further cutting would remove a RED counter.
- [x] No supporting files, so no routing table is required.

## The paired hook

- [x] Measures context from the transcript's last `message.usage` as
      `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. No hook event carries
      a token count, so this is the only exact source; transcript bytes were rejected as a proxy.
- [x] 31 tests, covering both sides of the threshold boundary, the cache-legs sum, last-record-wins,
      a compaction reading, a partial line from the tail seek, no-usage reading as unknown rather
      than zero, once-per-session, the `nudges` off-switch, and yielding while a nap is owed.
- [x] The misconfigured-window case is reported rather than silent: measuring more context than the
      configured window means the threshold can never be crossed, which is indistinguishable from a
      working watcher. Tested with its control - the same reading against a correct window is an
      ordinary offer.
- [x] Verified against this session's real transcript, both config states: 661,622 tokens read
      `misconfigured` against the 200k default and `offer` against a 1M window.
- [x] Registered in `hooks.json` on the existing `Stop` group and in `hooks/tests/conftest.py`
      `_HOOK_MODULES`; full suite green at 1801 tests.

## Deployment

- [x] `build_skill_docs.py` and `build_skill_triggers.py` re-run; the trigger map reports 80 skills.
- [x] README skill count 79 -> 80 in both spots.
- [x] `handover.md` added to `.gitignore` beside `EXECUTION-USER-REVIEW.md`, so the skill's own
      instruction holds in this repo; verified with `git check-ignore`.
- [x] Plugin version bumped to 5.217.0 (MINOR: a new skill plus a new hook).
- [x] Doc rows added to `docs/architecture.md` (hook pipeline) and `docs/reference.md` (three knobs,
      in the Default / what it controls / change it when style).
