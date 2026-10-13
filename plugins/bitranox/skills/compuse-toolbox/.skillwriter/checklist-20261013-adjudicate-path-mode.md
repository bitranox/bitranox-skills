# skill-writer checklist - compuse-toolbox (2026-10-13, adjudicate path mode)

The `adjudicate` row, its notes paragraph and the frontmatter description name a detector or scan
written during a review, and document the new path mode. The launch-rule sentence near the top and
the "fine under `uv run`" sentence in the `gate` notes are corrected; the `adjudicate` row's
`--probe`/`--control` placeholder now says what the value is.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - a review scenario whose answer depends on
      the changed text, answered only from the full SKILL.md pasted into the prompt, each answer
      with a direct quote or NONE, ending with a "Skill gaps" section.
- [x] Inherited-context route: every arm ran `claude -p --model haiku --tools ""
      --disable-slash-commands --setting-sources project` from a directory whose ancestor chain
      holds no CLAUDE.md or CLAUDE.local.md (checked by walking it), so the answer came from the
      pasted text, not from an installed copy or memory.

## RED (pre-change SKILL.md, haiku)
- [x] Q1 (a file-walking checker printed nothing; is there a tool for checking it): "probably
      `adjudicate`, though the reference describes it for guards and hooks, not file scanners",
      with a stdin command (`--probe STDIN --control STDIN`) that cannot pass a directory.
- [x] Q2 (passing `--root DIR --json`): NONE. Q3 (a probe directory that does not exist): NONE.
- [x] Q4 control (which flags carry a hook's two stdin payloads): `--probe` / `--control`.
- [x] Skill gaps: the tool reads as guard-only, no way to pass a directory, no word on a missing
      path, unclear how two `STDIN` values are fed.

## GREEN (changed SKILL.md, same model and questions)
- [x] Q1 `python3 scripts/adjudicate.py --subject find_noenc.py --probe-path <planted-tree>
      --control-path <clean-tree> -- --root {path} --json`, quoting the PATH MODE sentence and the
      notes sentence on a detector written during a review.
- [x] Q2 quoting "everything after a bare `--` is the subject's argv, `{path}` where each side's
      path goes". Q3 quoting "refuses a missing path or the same place on both sides before
      anything runs".
- [x] Q4 control unchanged (`--probe` / `--control`).
- [x] Diffed against RED both ways: Q4 kept; nothing RED answered was lost.

## REFACTOR
- [x] GREEN gaps closed: the refusal's exit code (now "(exit 2, a usage error)"); the `STDIN`
      placeholder (now `TEXT`, "each TEXT is fed on that side's own stdin" - RED hinted at it too,
      so it predates this edit); the top-of-file sentence calling `gate` the only plain-`python3`
      jig, which contradicted the `gate` notes (now lists the five jigs declaring
      `LAUNCH_WITH = "python3"`, checked by grep of `scripts/`).
- [x] Quote-back re-test on haiku of the three fixes: each answered with a direct quote. Its new
      gap, "every other jig is fine under `uv run`" against `mutation_arm`'s own row, is closed by
      pointing that sentence at `mutation_arm`.
- [x] Gaps declined, with reasons: how to seed a planted tree for a given defect (depends on what
      the detector hunts; the row says to seed it with "the thing it hunts"); whether the default
      `--fired-when output` suits a given detector (already covered by the banner sentence in the
      notes); whether `--probe` takes a path in hook mode (the row now says TEXT is fed on stdin).

## Quality and deployment
- [x] Description measured with `len()`: 1017 (cap 1024); the new trigger fits by tightening two
      clauses (`gitignored` to `ignored`, `turns or calls` to `turns/calls`), no keyword dropped.
- [x] No address, MAC, home or temp path added (grep over the added lines: no match).
- [x] Derived artifacts regenerated: `skill_triggers.json`, `docs/skills.md`.
- [x] `adjudicate.py` change test-first: of the first 14 new test cases 12 went RED on the missing
      feature; the 2 that passed were the stdin regression guard and a half-pair claim line the old
      parser already refused. A 9-arm mutation battery killed every arm once the refusal tests
      asserted their reason text (3 had survived on defense in depth before that).
