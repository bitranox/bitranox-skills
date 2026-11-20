# Review checklist - the project itself is exempt from its own cooldown (2026-11-20)

Change: the "The floor update also writes the project's `[tool.uv]` cooldown block" bullet in
section 3 gains two sentences: the project itself gets an `exclude-newer-package` entry when its
own name is in `[bmk.supply_chain] own_packages`, because `uv pip install <project>` run inside the
repository (the CI Quickstart notebook installs the published release that way) obeys the
project's `[tool.uv]`, and with only its libraries exempt it installs a release older than the
cooldown against the newest libraries. The rest of the bullet is reflowed to 100 columns, its
words unchanged. Frontmatter unchanged.

## PLAN
- [x] Skill type: reference. Test: a text coverage check of the pre-edit file (RED) and a
      retrieval probe with quote-back on the edited bullet (GREEN), text-only baseline-probe
      agents on opus and haiku.
- [x] Ledger read (`skill_decisions.py show devops-bmk`, also `--kind rejected,removed --full`):
      no rejected or removed entry covers the exemption list.
- Decisions: d-20261120-da723142

## RED
- [x] Route: a behavioural RED is contaminated. The machine's memory store already records that a
      package must exempt itself from its own uv cooldown, and the installed devops-bmk is the
      pre-edit text. The evidence is a coverage check of the pre-edit file instead.
- [x] Coverage check of `git show HEAD:<path>`: `grep -n -i -E 'project itself|own name|uv pip
      install <project>'` 0 hits; the only `exclude-newer-package` hit is the bullet that names
      only "every package named in `[bmk.supply_chain] own_packages` that the project reaches".
      Control: `grep -c 'that the project reaches'` 1 (the instrument reads the file).

## GREEN
- [x] Claim checked against the code before the probe: `own_project_exemption` in bmk
      `src/bmk/adapters/stagerunner/helpers/_supply_chain.py` returns the normalized project
      name when it is in `own_packages`; `_dependencies.py` unions it with `own_closure`. bmk's
      `test_an_own_project_is_exempt_from_its_own_cooldown` (own-project and foreign-project
      cases) passes; bmk's own gate wrote `bmk = false` into its `pyproject.toml`.
- [x] Probe on the edited bullet, opus and haiku (2 cells), three scenarios: own name in the list
      (both answered lib-log-rich and demo-tool), own name not in the list (both answered
      lib-log-rich only), why the notebook cares (both answered correctly). Both quoted "The
      project itself gets an entry too when its own name is in that list" and the `uv pip install
      <project>` sentence verbatim.

## REFACTOR
- [x] GREEN against RED in both directions: nothing in the bullet was removed; the reflow keeps
      the word sequence (asserted by the reflow script).
- [x] Width and fence check over the added lines: no output.
- [x] Skill gaps reported, each decided:
  - Whether a `false` entry stays after its name leaves the list (opus): declined, covered by the
    bullet's "any other entry is left alone"; `_supply_chain.py` lines 798-799 keep every entry
    that is not a floor pin.
  - Whether `make test` runs the floor update (opus, haiku): declined, covered in section 1
    ("`make test`'s first stage, `update_deps` (it runs the `deps_update` pipeline)").
  - Name normalization between list and project name (opus, haiku): declined, the code normalizes
    both sides (`own_project_exemption`: `normalize(project)` against normalized list entries);
    the reader needs no action for it.
  - Whether "when" also means "only when" (opus, haiku): declined, both tiers read it correctly
    and "it REPLACES the default" in the same bullet settles the absent case.
  - What "reaches" covers for extras, an empty list, PyPI not answering (opus, haiku): declined,
    pre-existing text this change does not touch; the bullet already covers PyPI not answering.
- [x] Tiers: opus and haiku, 2 cells, both pass.
- [x] Mirror: the same bullet in bmk `skills/devops-bmk/SKILL.md`; `repo-gate.py --mirrors`
      reports devops-bmk in sync.
