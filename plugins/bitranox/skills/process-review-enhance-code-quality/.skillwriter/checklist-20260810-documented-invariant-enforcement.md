# checklist - a documented invariant needs a test that fails without it

Fifth always-on check: walk the must/never rules stated in the project instructions file and the
design docs, report the walk as invariant / owning test / covered paths / verdict, take the
evidence from a mutation rather than a reading, and report code-vs-doc drift in either direction.

## RED

- [x] First baseline DISCARDED as contaminated, not banked. Run inside a workspace, the probe
      inherits a memory index whose text states this very rule and quotes the fixture's own
      invariant wording verbatim; its reply cited a project the prompt never named. A probe that
      can read the answer measures recall, not the skill.
- [x] Baseline re-run headless from a room outside the knowledge tree, so no `CLAUDE.md` cascade
      loads. Same model, same fixture: three stated invariants, one honoured on the tested path
      and broken on an untested sibling, one holding, one unimplemented with no test at all.
- [x] RED result: both violations were reported, but only behind an explicit guess. From its gaps
      list: "neither is a literal instance of the four enumerated checks ... Nothing in the prompt
      says whether CLAUDE.md's rules are independently reportable findings or only a
      severity-grading lens for the four checks ... I treated them as independently reportable -
      but this was a guess, not something the text stated."
- [x] RED produced no invariant-to-test mapping, and reached "untested" by reading the suite
      rather than by breaking anything. On a fixture small enough to read end to end that lands
      the same answer; on a repository that cannot be read whole, the reading is what fails.

## GREEN

- [x] Same fixture, same model, same room; only the always-on checks changed.
- [x] The walk is a table now: four rows, the third rule splitting into atomicity and owner-only,
      each row carrying its owning test, the paths it covers and a verdict.
- [x] The mutation rule fires and is EXECUTED, not described: "Mutating `now_hours > prev_hours`
      to `now_hours != prev_hours` and rerunning the given tests: all 3 assertions still pass."
      The surviving mutant is filed as a finding. RED produced no mutation at all.
- [x] The reportable-in-its-own-right rule fires: a correct-but-unenforced invariant (the atomic
      write) is filed as MEDIUM on its own evidence, which RED did not report.
- [x] The path-enumeration rule fires by name: "the tested `achievable_sata` made the neighboring,
      untested `achievable_pcie` look covered by proximity."
- [x] RED's guess no longer appears in GREEN's gaps list.

## REFACTOR

- [x] Every RED and GREEN dispatch asked for a `Skill gaps` section; both lists recorded.
- [x] GREEN diffed against RED in both directions. GREEN loses RED's MINOR docstring nit; it is
      subsumed by GREEN's SEVERE on the same function and the same asymmetry, and it is not a
      correctness result. Accounted for; nothing restructured on one run.
- [x] GREEN reports a defect in the FIXTURE rather than the skill - the scenario claims five
      passing tests while showing three. Real, and identical in both arms, so it does not confound
      the comparison. Declined as a scenario fix, not a skill change.
- [x] GREEN's remaining gaps are absence-of-input by construction: no shipped skill in the
      fixture, and no reader for the state file. Declined - a reviewer with the repository has
      what the fixture withholds.
- [x] The check states where it does NOT apply, so it does not collide with Step 4: Step 4 asks
      whether a deliberate decision still holds, this asks whether a stated rule is true of the
      code at all.
- [x] No session narrative, no scratch paths, no machine-derived addresses or hostnames in the
      skill text or in this artifact.
