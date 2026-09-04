# checklist-20260904-guard-replay-field

Change under test: `guard_replay.py` gains `--field`, which hands the predicate a named input
field instead of the tool's written payload - `--tool Edit --field file_path` prices a guard on
WHERE a write lands. The table row and the invoke cell say so.

## PLAN

- [x] Skill type: reference (a tool row). Test approach: retrieval - can a reader holding the row
      find the flag that prices a path guard?
- [x] Scope: one clause in the row, one form in the invoke cell, the script and its tests.

## RED

- [x] Text check against the pre-change row: it names `--tool Write` / `--tool Edit` and says
      Edit contributes the REPLACEMENT text; no form reaches `file_path`, so a path guard could
      only be priced by hand-rolling the walk.
- [x] Script RED: `test_a_field_override_replays_the_named_input_field` and
      `test_a_field_override_reaches_the_replay` - 2 failed on the old script (TypeError on the
      unknown keyword), then 42 passed.
- [x] The need was real before the flag existed: pricing `tooling-detour-nudge`, whose predicate
      keys on the path, had no jig route until this.

## GREEN

- [x] Text check against the changed row: `--field file_path` is named with the reason a content
      replay of a path guard measures the wrong question; the invoke cell carries the form.
- [x] The flag was used for its purpose in the same change: 3,495 Write and 5,765 Edit calls
      replayed through `notice_path` keyed on `file_path`, 142 and 695 firings, every sampled
      firing a write into the plugin source from another project.

## REFACTOR - every gap closed or declined

- [x] GAP: the default when `--field` is absent. CLOSED in the help text and the docstring: the
      tool's written payload, unchanged.
- [x] No other gap; the change is one optional flag.

## Quality

- [x] Description unchanged; the row grows by one clause.
- [x] No narrative, no scratch paths, no addresses added.
- [x] Tests ship beside the script and pass.

## Deployment

- [x] `repo-gate.py --ci` before the push.
- [x] Version bumped in `plugin.json` and `pyproject.toml`; CHANGELOG entry names the flag.
