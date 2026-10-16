# skill-writer checklist - compuse-toolbox (2026-10-16, rules folded into the skill)

- [x] Change, one line per item:
  - Unlinked files: SKILL.md now has a three-item list below the Tools table naming
    `references/anchored-edits.md`, `references/mutation-arms.md` and
    `references/transcript-corpus.md`, each with the situations that should send a reader there.
  - Contradiction (bare `uv run` hazard): `references/mutation-arms.md` now states the runner order
    from `resolve_runner` in `scripts/mutation_arm.py` (`--python`, else `--with` via uv, else
    `./.venv`'s python, else this interpreter) and scopes the hazard to a launch with no `.venv` in
    the current directory.
  - Contradiction (inert control reading KILLED): the reference now says an interpreter that cannot
    run the project reads INCONCLUSIVE, per `verdict_for()` ("an exit 1 without a FAILED/ERROR summary
    line is INCONCLUSIVE"), and that KILLED on an inert control means the test fails without a real
    change. The stale "a false one carries null" line is replaced: a KILLED always names its
    failure now.
  - Rules to add: none listed for this skill.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the
      skill through the Skill tool before its first edit
- [x] RED (text check of the artifact): before this edit none of the three reference files was
      linked from SKILL.md (verifier: "The only references/ mention in SKILL.md (line 313) points
      to jev-shadow.md in another skill"), and `references/mutation-arms.md` described the jig's
      pre-fix behaviour ("never a bare `uv run`, which runs the arm on an interpreter without the
      project's dependencies"; KILLED "usually an interpreter that cannot import the project").
      A behavioural RED was replaced on purpose: these rules are in the always-loaded memory index
      of the authoring machine (inherited coverage), so a behavioural arm answers from that context
      with or without this text.
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): rules to add: none.
      Contradictions: bare `uv run` hazard -> resolved, references/mutation-arms.md:13-16
      "`--python PATH`, else `--with DEP` through uv, else `./.venv`'s python under the current
      directory, else the interpreter running the tool ... a bare `uv run` with no `.venv` in the
      current directory runs the arm on uv's interpreter", matching scripts/mutation_arm.py
      resolve_runner (`if python:` -> `"--python"`; `if with_deps:` -> `"--with"`;
      `venv = Path(...) / VENV_PYTHON` -> `"cwd .venv"`; else `[sys.executable, ...], "this
      interpreter"`) and SKILL.md:86; inert control reading KILLED -> resolved,
      references/mutation-arms.md:8-10 "INCONCLUSIVE (exit 2) means the runner never ran the test
      ... a pytest exit 1 with no FAILED/ERROR summary line is scored INCONCLUSIVE, never KILLED",
      matching verdict_for (`if returncode == 1 and output is not None and failure_reason(output) is
      None: return "inconclusive"`) and exit_code_for (inconclusive -> 2); unlinked references ->
      resolved, SKILL.md:101 "`references/anchored-edits.md` - before an `anchor_edit` run",
      SKILL.md:104 "`references/mutation-arms.md` - before trusting a `mutation_arm` verdict",
      SKILL.md:107 "`references/transcript-corpus.md` - before hand-walking `~/.claude/projects`".
      Description re-measured: 1017 characters, unchanged against the main checkout.
- [x] Gaps closed or declined: none open. Step-4 scan of the added SKILL.md lines and the three
      references: no non-ASCII punctuation, no private host, IP or user home path; `session` and
      `~/.claude/projects` in transcript-corpus.md are the subject matter (Claude Code's own
      transcript layout), not a private reference.
- [x] Description measured: unchanged, 1017 characters
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
