# checklist-20261009 - match the file's null style instead of always pinning `null`

## What the change is

The pattern installed a `None` representer unconditionally, so every null was written as
`key: null`. On a file with bare nulls - a GitHub workflow's `pull_request:` under `on:` - that is
the reflow the skill warns about, produced by the skill's own pattern. The representer was also
registered through `yaml.representer.add_representer`, which writes to the shared
`RoundTripRepresenter` class and so changes every `YAML()` in the process.

The pattern now pins no null spelling by default and proves its settings with an unedited round
trip before editing. A new "Match the file's null style" section counts explicit nulls, pins a
spelling only when the file writes one (on a subclass), and gives the mixed-file procedure: a
normalisation commit on its own, then the edit.

## RED

- [x] Mechanical proof of the defect, ruamel.yaml 0.19.1: the pattern's settings applied to
      `on: {push: ..., pull_request: <bare>}` dump `pull_request: null`; plain `YAML()` keeps it
      bare. With the representer, `x: null`, `y: ~` and a bare `z:` all come out `: null`.
- [x] Mechanical proof of the second defect: after `add_representer` on one `YAML()` instance, a
      NEW `YAML()` dumps a bare null as `a: null`.
- [x] Behavioural arms (sonnet, haiku) given the old text and the bare-null workflow: both reasoned
      around the pattern and dropped the representer, so the action did not flip. Both named the
      defect as a skill gap - "it never says to check whether the file uses bare or explicit
      nulls"; "the text never says which rule wins when the file's convention is bare keys". The
      evidence is the mechanical proof plus those gap reports.

## GREEN

- [x] Every code block in the new text executed against fixtures: bare-null workflow (one added
      line `workflow_dispatch:`, nothing else), `null`-only and `~`-only files with the matching
      spelling pinned (only the added router lines), a mixed file (the unedited-round-trip assert
      fails, as intended), and a bare-null file AFTER a pinned file in the same process (still
      bare - the subclass does not leak).
- [x] Mixed procedure executed: pinning `~` normalises only `local:` to `local: ~`; the pattern
      then passes its assert and the edit adds only `disk: ~`.
- [x] Behavioural arms (sonnet, haiku) given the new text: both pinned nothing for the workflow and
      predicted a one-line diff; both classified the `~`-plus-bare file as mixed and produced the
      two commits with the predicted lines, matching the executed result.

## REFACTOR

- [x] Gaps closed: the unedited-round-trip assert must be replaced by writing `buf.getvalue()` in
      the normalisation step; which spelling an added `None` gets; whether a bare null counts as a
      spelling (branch reworded to "one explicit spelling, and the unedited round trip with it
      pinned passes"); how to count bare nulls for the majority; `grep -c` exits 1 on a zero count;
      the mixed bullet named `key: null` where the pinned spelling may be `~`.
- [x] Each closed gap verified by quote-back: five questions, each answered with a direct quote.
- [x] Declined: a method for reading the file's indent (the unedited round trip catches a wrong
      guess, and it predates this change); YAML 1.1 `on` handling (not this change); how to show a
      single commit's diff (general git); whether normalising one's own file needs approval
      (judgement left to the reader).
- [x] No result lost against RED: the RED arms' one correct action (drop the representer for a
      bare-null file) is what the new text prescribes.

## Quality

- [x] Present tense; no session narrative, no scratch paths.
- [x] Values added are documentation names (`example.com`) and generic paths.
- [x] `name` and `description` unchanged; no routing keyword moved.
- [x] Also fixed in passing: the pattern's `path.open("w")` now passes `encoding="utf-8"`, and the
      Library bullet no longer says to pin "the two settings".
