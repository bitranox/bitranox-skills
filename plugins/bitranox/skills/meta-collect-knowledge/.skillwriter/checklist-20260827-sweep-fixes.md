# skill-writer checklist - meta-collect-knowledge (2026-08-27, sweep fixes)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect class is a FACTUAL claim, so the RED is a
      ground-truth check against the code or the upstream document, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft, and the arm cannot fail honestly.
      The artifact check is immune to that.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] Native-tier label: `gather_scan.py` prints `native-tier (machine-local)` as one label; the
      skill named only the parenthetical, so a reader grepping for it finds nothing. Full string now
      given, with the instruction to grep for the whole thing.
- [x] Debounce step was UNEXECUTABLE - it named no file, format or tool, and none exists (no
      debounce store anywhere in the plugin; `gather_scan.py --help` offers no `--mark`). The step
      now names a concrete path and record format, and says plainly that nothing ships to enforce
      it. Kept out-of-store deliberately, so it cannot become a fact the next dream tidies.
- [x] REJECTED as a false positive, recorded here so it is not re-filed: the sweep claimed the scope
      descriptor no longer lives in a `bitranox:self-learning` block in `CLAUDE.local.md`. It does -
      the marker wraps the WHAT/STACK/CHILDREN block, and `self_improve_signals` reads it from
      `claude_local_md_path`. The skill's sentence is correct and is unchanged.
- [x] REVISED after the decision review: the first fix documented a hand-maintained TSV that no
      shipped code wrote or read, which is a spec that becomes fiction. `gather_scan.py` now owns
      it - `--mark` records a pair, `--seen` answers from the record (exit 0 gathered, 1 not) and
      walks nothing. Step 5 names those instead of a convention.
- [x] Six store tests and five CLI tests, each watched fail first. The ones that matter are the
      negatives: a mark on one project must not silence another project or another topic; a tab in
      free text must not forge a second TSV column; an unreadable store must read as "not gathered"
      rather than raise, because debounce is an optimisation and losing it costs only a re-grep.
- [x] Deliberate non-behaviour, with its own test: neither flag GATES a scan. A marked topic still
      scans when a scan is asked for - `--seen` is advice to the caller, not a lock - so the tool
      cannot silently do less than it was told to.
