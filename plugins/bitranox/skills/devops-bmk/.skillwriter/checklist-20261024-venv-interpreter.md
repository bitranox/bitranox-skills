# skill-writer checklist - devops-bmk (2026-10-24, bmk 3.25.1)

- [x] Change: the "project venv" section says which interpreter counts. The bold heading reads
      "on the patch uv builds it on" instead of "at its latest patch"; the toml comment names the
      condition ("latest patch under uv's default python-preference"); a paragraph states that bmk
      rebuilds only when the venv differs from what `uv venv --python X.Y` would use, which
      `uv python find --system --show-version X.Y` reports, so under `UV_PYTHON_PREFERENCE=system`
      the venv stays on the distro Python instead of rebuilding every run. Mirrored byte-identical
      in bmk's `skills/devops-bmk/SKILL.md` (`repo-gate.py --mirror-of` reports in sync).
- [x] Every claim checked against bmk source: `adapters/stagerunner/venv.py` `patch_uv_builds_on`
      runs `uv python find --system --no-python-downloads --show-version <minor>` and
      `_discard_venv_on_wrong_python` rebuilds only when the venv's interpreter version differs from
      that answer, and leaves the venv alone when uv gives none. Agreement of `find --system` with
      `uv venv --python 3.14` measured with uv 0.13.0 in six cells (python-preference unset, managed,
      system; an activated `VIRTUAL_ENV` present and absent): 6/6 the same patch, 3.14.8 for the
      first two preferences and 3.14.4 (the distro interpreter) for `system`.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`); this agent loaded the skill.
- [x] Inherited coverage: `redcheck --corpus-cascade` on the bmk repo reports STRONG inherited
      coverage (bmk's `CLAUDE.md` states the rule). Route taken: a text check against the skill file.
      Every probe ran as the tool-less `baseline-probe` type, was given the excerpt pasted in full,
      and had to answer with direct quotes or NONE; each quote was checked against the file.
- [x] RED (opus, pre-change excerpt), three questions: Q1 the system-preference case (which
      interpreter, rebuild every run?), Q2 a new patch under default settings, Q3 does bmk pick the
      target or defer to uv. Q1: NONE. Q3: quoted the heading "at its latest patch", i.e. bmk's own
      pick. Q2 answered by "A new patch costs you nothing".
- [x] GREEN (opus and haiku, edited excerpt), same three questions: both tiers answered Q1 and Q3
      by quoting the new paragraph; Q2 unchanged. 2 tiers x 3 questions.
- [x] GREEN gaps, each decided:
      - the heading promised "latest patch" next to "uv's choice" (opus) - CLOSED: heading and toml
        comment reworded, the paragraph says "latest patch" holds only under uv's default
        `python-preference`.
      - whether `uv python find --system` answers for the same interpreter `uv venv` uses (opus) -
        CLOSED: "which `uv python find --system --show-version X.Y` reports".
      - "Before those commands" points outside the excerpt - DECLINED, covered in the same section:
        "Before any command that touches the Python environment (`test`, `push`, `deps`, `build`,
        ...)".
      - what the distro patch number is, and what happens to a venv built on uv's own patch when
        the preference switches, or when the distro ships a new patch - DECLINED: answered by the
        stated rule "bmk rebuilds only when the venv differs from what `uv venv --python X.Y` would
        use" (one rebuild onto uv's new choice, then stable); naming a distro's patch is not the
        skill's to state.
      - whether `uv python upgrade` migrates a venv built on a system interpreter, and other routes
        a patch arrives by - DECLINED: uv's behaviour, outside this skill.
      - how bmk compares the two values, and why `--system` - DECLINED: implementation detail a
        reader of the skill does not act on.
- [x] GREEN diffed against RED both ways: Q2's answer is the same quote in every arm; the removed
      text ("at its latest patch" unconditionally) was false under a system preference.
- [x] Re-probe on the final text (haiku, and opus quote-back at effort medium), five questions
      (Q1-Q3 plus Q4 "always on the latest installed patch?", Q5 "which command reports it"): every
      answer a direct quote of the final text; Q4 "so "latest patch" holds only under uv's default
      `python-preference`", Q5 "`uv python find --system --show-version X.Y`". The one new gap
      ("by default" in the toml comment readable as "normally") is CLOSED by naming the condition in
      the comment; Q4 re-run on haiku against the final comment quotes it ("latest patch under uv's default
      python-preference") with no contradiction reported; its remaining gaps restate ones declined above.
- [x] History-phrase finder over the skill directory: the changed lines match nothing; the single
      existing hit (line ~387, "behaviour the tool no longer has") describes tool behaviour, not
      skill history.
- [x] Frontmatter untouched: no routing keyword moved.
