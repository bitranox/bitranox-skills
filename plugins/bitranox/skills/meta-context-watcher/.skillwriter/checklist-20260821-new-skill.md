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
      threshold is `min(pct of window, absolute cap)` rather than either alone. The 400k cap is one
      published finding read SECOND-HAND from a summary, and both the hook docstring and the knob
      documentation say so rather than presenting it as measured here.
- [x] Model windows taken from the bundled `claude-api` skill's table rather than inferred: Fable 5,
      Opus 5/4.8/4.7/4.6, Sonnet 5/4.6 offer a 1M variant; Haiku 4.5 is 200K with NO 1M variant, so
      the capability set is an allowlist and a `[1m]` suffix on haiku is refused.

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
- [x] Token budget: see the final figure under "Revisions" below - over the 500-word target, and
      recorded rather than gamed. The overage is the RED-derived rationalization table plus the
      sections this repo's conventions require of a hook-paired skill (`When it fires on its own`,
      `Not the same as its neighbours`).
- [x] No supporting files, so no routing table is required.

## The paired hook

- [x] Measures context from the transcript's last `message.usage` as
      `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. No hook event carries
      a token count, so this is the only exact source; transcript bytes were rejected as a proxy.
- [x] 55 tests, covering both sides of the threshold boundary, the cache-legs sum, last-record-wins,
      a compaction reading, a partial line from the tail seek, no-usage reading as unknown rather
      than zero, the model-window table, project detection and its non-matches, re-ask spacing at
      both window sizes, the family window table, the `nudges` off-switch, and yielding while a nap is owed.
- [x] The misconfigured-window case is reported rather than silent: measuring more context than the
      configured window means the threshold can never be crossed, which is indistinguishable from a
      working watcher. Tested with its control - the same reading against a correct window is an
      ordinary offer.
- [x] Verified against this session's real transcript at several points as it grew (563k, 661k,
      761k): `misconfigured` against a wrong 200k window, `offer` against the detected 1M one.
- [x] Registered in `hooks.json` on the existing `Stop` group and in `hooks/tests/conftest.py`
      `_HOOK_MODULES`; full suite green at 1825 tests.

## Revisions from the decision review (same change)

- [x] **Re-asks replace the single ask.** Once-per-session meant a decline at 40% silenced the hook
      through the stretch it exists for. The next ask now waits until context has grown another
      tenth of the WINDOW, so the spacing scales with window size; tested from both sides at 200k
      and 1M.
- [x] **The window is DETECTED, not configured.** `~/.claude.json` records per-project
      `lastModelUsage` keyed by the full model id, and that is the one place the `[1m]` suffix
      survives - the transcript stores the bare `claude-opus-5`. The largest window among a
      project's models is taken, because subagents contribute haiku and sonnet entries and the
      asymmetry favours over-estimating. `context_window` defaults to 0 (detect) and remains an
      override. Verified live: resolves `(1000000, "detected")` here with no knob set, turning what
      was a misconfiguration complaint into a real offer.
- [x] **Writing OVERWRITES any existing handover.** One file, one moment: a stale handover is
      superseded the instant a new one is written, so it is replaced wholesale rather than appended
      to or kept alongside. Two handovers, or one holding two moments, leaves the reader deciding
      which half is true.
- [x] **Window detection is a LADDER, and rung 3 was a shipped defect.** Taking the WIDEST window
      ever recorded for a project goes silently inert on a switch down: a 200K session assumed to be
      1M gets a 400K threshold it can never reach (it auto-compacts near 166K), and the
      misconfigured check cannot see it either because 166K is far under the assumed window. Fixed
      two ways - rung 2 reads the session's OWN model exactly, and rung 3 now picks the DOMINANT
      model by cache-read volume rather than the widest.
- [x] **The exact current model IS detectable**, contrary to what 5.217.0 and the first revision
      both claimed. An `Agent` dispatch carrying no `model` inherits the session's, and its result
      reports `resolvedModel` with the `[1m]` suffix that `message.model` drops. Verified on real
      data: unpinned resolves to `claude-opus-5[1m]`, pinned resolves to the pinned tier and is
      skipped. Absent when a session never dispatches unpinned, which is why it heads a ladder
      rather than standing alone. Ruled out first: the PID-keyed session file (no model key), the
      hook environment, and the transcript's own metadata records.
- [x] **The window is the model FAMILY, measured rather than inferred.** Three designs were tried
      and discarded before measuring: widest-window-ever (silently inert on a switch down),
      dominant-model-by-volume, and a family ceiling plus a peak-proves-the-variant rule. All of
      them existed to work around an assumed 200K/1M split that does not exist. Scanning 1485 local
      transcripts settled it: every non-haiku family has actually carried far more than a 200K
      window could hold - opus-5 999,946; opus-4-8 999,911; fable-5 997,450; sonnet-5 665,313 -
      while haiku peaked at 119,393, and the peaks stop just under 1,000,000, which is the boundary
      showing itself. Claude Code's `[1m]` suffix never appears in `message.model` and is redundant.
      The result is one table and one lookup; `model_from_dispatch`, `model_from_project`,
      `window_from_evidence` and the peak tracking were all deleted.
- [x] An unknown family falls back to 200K, and that direction is tested: too small asks early and
      costs a decline, too large sets a threshold the session can never reach and the hook goes
      silently inert.
- [x] **Reading a handover marks it STALE rather than deleting it.** Deleting loses the only record
      of where the work stood if the reading session then crashes; leaving it untouched lets the
      session after next read a passed moment as current. Amending is forbidden - a new handover
      replaces the file.
- [x] Skill re-checked after the additions: **811 words**, still over the 500 target and still
      recorded rather than gamed. Two trim passes removed the restated one-rule elaboration, a
      duplicated procedure step, and the long-form reading section.

## Deployment

- [x] `build_skill_docs.py` and `build_skill_triggers.py` re-run; the trigger map reports 80 skills.
- [x] README skill count 79 -> 80 in both spots.
- [x] `handover.md` added to `.gitignore` beside `EXECUTION-USER-REVIEW.md`, so the skill's own
      instruction holds in this repo; verified with `git check-ignore`.
- [x] Plugin version bumped to 5.217.0 (MINOR: a new skill plus a new hook).
- [x] Doc rows added to `docs/architecture.md` (hook pipeline) and `docs/reference.md` (three knobs,
      in the Default / what it controls / change it when style).
