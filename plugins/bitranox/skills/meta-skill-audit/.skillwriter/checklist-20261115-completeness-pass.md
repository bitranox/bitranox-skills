# checklist - a completeness pass for library and CLI skills

New section "Audit completeness, not only correctness": list the installed package's public
callables (`__all__`) and CLI subcommands, require each in the skill or a recorded exemption,
report the rest; with a runnable snippet that prints how many names it examined.

Decisions: d-20261115-10f53b8f

## RED

- [x] Skill decisions read first: the skill has no ledger entries.
- [x] Coverage probe on the pre-edit text, opus and haiku: asked whether a skill whose every
      statement checks out is done, both tiers listed only the correctness classes; opus named
      "CLI features the skill never documents" as NOT STATED.

## GREEN

- [x] Same question on the edited text, opus and haiku: both answered "not done", ran the
      completeness pass, and quoted the section verbatim, including the 0-names rule.
- [x] The snippet was RUN, not read: on three stdlib packages it printed "7 public names, 2
      missing", "211 public names, 207 missing" and "7 public names, 6 missing" against skills
      that do not document them, so it reports both the count and the names.
- [x] A first draft that piped `grep ... || echo MISSING` was refused by the plugin's own
      verdict-on-any-exit guard; the shipped form is Python and never mistakes an error for a miss.

## REFACTOR

- [x] Declined (opus): "the CLI half has no script" - `--help` is the command step 1 names, and
      subcommand listing differs per CLI framework.
- [x] Declined (opus, haiku): "where the exemption lives" - left to the audited skill, which may
      not have a decisions ledger; the text requires only that the next audit can read it.
- [x] Declined (opus): "submodule names" - the top-level `__all__` is the package's declared
      public surface; a name exported only from a submodule is not.
- [x] Open, reported rather than fixed here: the existing "every shipped example must at least
      parse" snippet only parses `.py` files, never fenced Python inside SKILL.md (found by the
      opus RED probe). It predates this change and needs its own decision.
- [x] Width and fence check over the added lines printed nothing outside code fences.
