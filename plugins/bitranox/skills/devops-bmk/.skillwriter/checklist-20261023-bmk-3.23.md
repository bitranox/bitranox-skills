# skill-writer checklist - devops-bmk (2026-10-23, bmk 3.23.0)

- [x] Change: five additions and two corrections for bmk 3.23.0. Added: the `pyright` stage runs
      `pyright --pythonplatform` once per OS family in `[tool.ci].os` ("Proving a gate" section);
      `test-all` covers the Python-version axis only, each cell checking the host platform;
      `bmk install` writes `.bmk-cooldown.mk` beside the Makefile, commit both (section 1) and what
      the file holds (bmk's env section); an exact pin (`==X`, `===X`) is never moved and never
      fails the `deps` stage, with the requirement lists the floor update reads; how to read which
      bmk a repo runs. Corrected: section 1 said the Makefile manages bmk "per project" while the
      next subsection says the env is shared machine-wide; the `deps` bullet said any floor behind
      PyPI fails, now with the exact-pin exception.
- [x] Every claim checked against bmk source: `adapters/stagerunner/project.py`
      (`pyright_platforms`, `_RUNNER_FAMILIES` prefixes ubuntu/windows/macos); `helpers/_matrix.py`
      (per-version cells, no platform loop); `adapters/cli/commands/install_cmd.py`
      (`_deploy_makefile` writes the Makefile and `.bmk-cooldown.mk` together; `check_makefile_update`
      calls it only for an outdated Makefile); `helpers/_dependencies.py` (`_hold_exact_pin` reports
      an OUTDATED exact pin PINNED; `_check_fails` fails only on OUTDATED or a lock blocker; the
      `[==]` report marker; the five requirement lists `_extract_all_dependencies` reads).
      `$(uv tool dir --bin)/bmk --version` run: prints `bmk version 3.23.0`.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`); this agent loaded the skill.
- [x] Inherited coverage: the bmk repo's own `CLAUDE.md` describes `.bmk-cooldown.mk` and per-OS
      pyright, so a behavioural arm dispatched there could answer from it. Route taken: every probe
      answer must be a direct quote of a snapshot of the skill file, or NONE, and each quote was
      checked against that file (lines joined, since sentences wrap).
- [x] RED (opus, pre-change text), three questions: does a Linux `make test` catch a Windows-only
      pyright error with Windows in `[tool.ci].os`; commit, ignore or delete `.bmk-cooldown.mk`;
      what `make test` does to a deliberate `pwshpy==1.5.0` once 1.6.0 is on PyPI. NONE to all
      three. Its gaps also named the misleading "reproduce CI's matrix locally" for `test-all` and
      the per-project / shared contradiction.
- [x] GREEN (opus and haiku, edited text), same questions plus "would `test-all` catch it" and
      "does the `deps` stage fail on the pin": both tiers answered every question with direct
      quotes of the new text. 2 tiers x 3 questions.
- [x] GREEN gaps, each decided:
      - how to read the running bmk's version when a rule says "from bmk 3.23.0" - CLOSED: the
        "Which bmk you are running" point (`bmk --version`, the Makefile's first line names the bmk
        that wrote it).
      - the `deps` bullet reads as failing on any floor behind PyPI - CLOSED: "(an exact pin
        excepted, see the next point)".
      - where "reported pinned" shows - CLOSED: "`[==]` in the `bmk deps` report".
      - whether extras are covered - CLOSED: the five requirement lists are named.
      - what `uv lock` does with an exact pin - DECLINED: uv's resolution, outside this skill.
- [x] Re-probe on the final text (haiku), four questions on the touched sentences (which bmk runs,
      the Makefile first line; `deps` on an exact pin and where the pin shows; `test-all` versus
      `make test` for the OS axis; the cooldown file). All four answered by direct quotes. Its
      remaining gaps restate what the text answers (each `test-all` cell checks the host; the pair
      shares the Makefile's version) and are DECLINED as stated.
- [x] GREEN diffed against RED both ways: RED produced no answer to lose; the removed text ("per
      project", "writes the Makefile; installs nothing permanently" without the cooldown file,
      "reproduce CI's matrix") was false or incomplete against the code.
- [x] Frontmatter untouched: no routing keyword moved.
- [x] No address, MAC, hostname or private path added.
- [x] No session narrative or private provenance added.
- [x] Mirrors bmk's `skills/devops-bmk/SKILL.md`: `repo-gate.py --mirror-of` reports `in sync`.
