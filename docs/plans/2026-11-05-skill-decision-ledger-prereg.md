# PREREG: anchor replay probe for the skill decision ledger (M0)

Written 2026-11-05 before any replay output existed. Plan:
`docs/plans/2026-11-05-skill-decision-ledger.md`, milestone M0. This file is append-only after
its first commit: results go under `## Result`, deviations under `## Deviations`, never edits above.

## Question

Do anchors picked by an agent under the planned guidance catch real rule changes, and how often do
they vanish at a commit that changed no meaning?

## Instrument

- `normalise(text)`: per line, strip leading whitespace, leading blockquote markers (`>` runs) and
  one list marker (`-`, `*`, `+`, `N.` or `N)` followed by whitespace); then join all words with
  one space. `anchor_occurs(anchor, text)` is `normalise(anchor) in normalise(text)`,
  case-sensitive.
- Corpus per commit: that commit's SKILL.md only (the probe does not read references/).
- Fire: a window commit after which an anchor that occurred in the previous commit's SKILL.md no
  longer occurs. An anchor that has fired stays fired and is not counted again.

## Skills and windows

`devops-bmk`, `compuse-toolbox`, `meta-skill-writer`. Each history is `git log --follow` on the
skill's SKILL.md at origin/master 8141cb3a. The window is the second half of that history
(the newer ceil(n/2) commits); the window's first commit is the anchor-picking state. Measured
before any replay: devops-bmk 49 commits (window 25), compuse-toolbox 79 (window 40),
meta-skill-writer 52 (window 26); all meet the 20-commit floor, so no replacement is needed.

## Anchor picking

One opus subagent per skill receives ONLY the SKILL.md text at the window's first commit and this
guidance: "quote 20 to 200 characters that are the stable core of one rule, unique in the file,
not inside a table row, not a heading". It returns 20 anchors, each with the rule it stands for.
It is not told what the probe measures. An anchor that does not occur exactly once in that text is
recorded as a picking failure and not replaced.

## Labelling

A second opus subagent (effort medium), shown only, per fired anchor, the rule it stood for and the
400 characters around the anchor's old position before and after the commit, labels each fire
MEANING-CHANGED (rule altered, removed, or moved out of SKILL.md) or REWORDED (same rule, other
words). It is not told the thresholds or the outcome rules. Ten labels are then checked by hand
against `git show`.

## Controls (run first, by sha, before any window replay)

Anchors fixed now, quoted from the text at the named commit:

- PC1 (must fire): `Promoting to the global layer is high-blast (it loads in every session)` from
  `plugins/bitranox/skills/meta-dream-project/SKILL.md` at b13255aa (it spans a line wrap there).
  Must occur at `cec8867b^` and not at cec8867b.
- PC2a (must fire): ``bmk installs as a persistent `uv tool` together with the current project's
  dependencies`` from `plugins/bitranox/skills/devops-bmk/SKILL.md` at f0367056. Must occur at
  `d3a7a0d5^` and not at d3a7a0d5.
- PC2b (must fire): `machine-wide env cannot serve two projects` from the same file at d3a7a0d5.
  Must occur at `48e94f13^` and not at 48e94f13.
- NC1 to NC4 (must not fire), synthesised from each skill's window-start SKILL.md: (1) every
  paragraph outside fences and tables re-wrapped at 60 columns; (2) every blockquote re-wrapped at
  60 columns; (3) every table re-padded to different column widths; (4) every ordered list
  renumbered (1., 2., ... becomes 3., 4., ... and back). Each transform is applied to the original
  text, and all 20 picked anchors of that skill must still occur after it.

## Metric

Per skill: REWORDED fires per 10 window commits. Overall: the median of the three per-skill
figures, and the total of MEANING-CHANGED fires.

## Outcomes

- Outcome A, build the refusing gate as designed: PC1, PC2a and PC2b all fire, no negative
  control fires, and the median is at most 1 REWORDED fire per 10 commits.
- Outcome B, stop and redesign with the user: any positive control does not fire, or any negative
  control fires. The matcher is wrong for its purpose.
- Outcome C, bring the user the numbers and two options: controls behave, but the median is above
  1 per 10. Option 1 demotes the anchor check to a warning in the skill-writer step; option 2
  keeps the refusal. The edit-guard brief, the checklist `Decisions:` line and the A/B wiring are
  unaffected by C.

## Falsifiers

Zero fires of either label across all three skills, or every fire carrying the same label, means
the instrument is broken, not the answer: read ten fire events by hand before any conclusion.
A per-skill commit count examined by the replay that differs from the window size above voids the
run for that skill.

## Deviations (recorded before any control or replay ran)

- D-1, instrument: line-start marker stripping alone cannot keep an anchor quoted across two list
  items stable, because the anchor carries the inner "2." and a renumbering changes it (a harness
  test went red on it). `normalise` also drops, anywhere and on both the anchor and the text,
  every whitespace-separated token that is only a marker: `-`, `*`, `+`, a run of `>`, `N.` or
  `N)`. Both sides lose the same tokens, so a match stays sound; prose dashes and "step 2." become
  invisible to it.
- D-2, labelling context: a fixed after-excerpt "around the old position" cannot show the labeller
  a rule that was reworded and MOVED within SKILL.md. The labeller additionally gets the
  after-text region that best matches the vanished anchor by word-window similarity, with its
  similarity ratio.

## Result

### Controls (MEASURED 2026-11-05, recorded before the window replay)

- PC1, PC2a, PC2b: all three fired (present at the parent, absent at the named commit).
- Picking: 60 anchors returned (20 per skill), all 60 occur exactly once in their window-start
  text and are 20 to 200 characters after normalising; no picking failures.
- NC1 to NC4: no anchor lost under any transform, in any skill. NC1 and NC3 changed the text in
  all three skills. NC2 and NC4 changed nothing in devops-bmk and compuse-toolbox, whose
  window-start texts have 0 blockquote and 0 ordered-list lines outside fences (counted), so
  those two controls rest on meta-skill-writer alone (6 blockquote and 20 ordered-list lines).

### Window replay (MEASURED 2026-11-05)

Commits examined equal the window sizes: devops-bmk 25, compuse-toolbox 40, meta-skill-writer 26.
Five fires in total, labelled by the opus labeller (effort medium):

| Skill           | Commit   | Labeller        | Event                                                            |
|-----------------|----------|-----------------|------------------------------------------------------------------|
| devops-bmk      | 488e08cd | REWORDED        | "You no longer need a caller-side lock" became "You do not need" |
| devops-bmk      | dd60c7fc | REWORDED        | "at its latest patch" became "on the patch uv builds it on"      |
| devops-bmk      | 237b6aab | MEANING-CHANGED | `push` / `git add -A` passage reframed around the gate's order   |
| devops-bmk      | 862e6030 | MEANING-CHANGED | "release it directly" gained a condition                         |
| compuse-toolbox | b534fae2 | MEANING-CHANGED | the scan's "read none" exit code changed from 3 to 2             |

Hand check of all five events (fewer than the ten the PREREG names, because only five exist): I
agree on events 1, 4 and 5. On dd60c7fc I read a behaviour change (which patch is built), while
the labeller judged it against the rule as the picker stated it, which does not mention the patch;
on 237b6aab I could read either label. With my labels instead of the labeller's, devops-bmk has 1
or 2 REWORDED fires; the outcome below is the same either way.

- REWORDED fires per 10 window commits: devops-bmk 0.8, compuse-toolbox 0.0, meta-skill-writer
  0.0. Median 0.0 (threshold: at most 1).
- MEANING-CHANGED fires in total: 3 (one per about 30 window commits).
- Falsifiers: both labels occur, and fires are not zero, so the instrument is not flat.

**Outcome A**: all positive controls fired, no negative control fired, and the median is 0.0
REWORDED fires per 10 commits. Build the refusing gate as designed.

Limits, stated so the result is not read as more than it is: five fire events in 91 commits from
60 agent-picked anchors is a small sample; meta-skill-writer produced none; NC2 and NC4 rest on
one skill; the anchors were picked at each window's start, so rules added later in the window were
never anchored. Artifacts: the main checkout's `.plan/skill-decisions/` (gitignored).
