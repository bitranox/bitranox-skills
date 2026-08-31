# compuse-toolbox: add the `anchor_edit` jig

Change: a new jig `scripts/anchor_edit.py` with `tests/test_anchor_edit.py`, and one row for it
in the Tools table. Skill type: REFERENCE (a catalogue row), so the test is a retrieval scenario -
given the table, does an agent facing the chore find and name the right tool?

## PLAN

- [x] Skill type identified: reference. Test approach: retrieval, not pressure.
- [x] Scope: no new file in the skill body; one table row plus a script and its tests.

## RED

- [x] Scenario checked for the two leaks with `redcheck.py --corpus-cascade` against this repo.
      First form reported INHERITED COVERAGE at 26 percent, on the terms `action`, `anywhere`,
      `approach`, `concrete`, `guess`, `limits`, `paragraph`, `reply`, `turn` - all boilerplate
      from the "Skill gaps" instruction block, none of them subject vocabulary. Re-run with that
      block removed: `clean - no inherited coverage, no telegraphing found`, 953 documents read.
      Recorded as a false positive of the documented function-word shape, not a sealed fixture.
- [x] RED arm, sonnet, with the installed skill version that has no `anchor_edit` row.
      It did NOT hand-roll a broken edit: it grepped `^## Limits$` for uniqueness, used an exact
      `old_string`/`new_string` pair, and verified zero deletions. Its own gaps section names why:
      "No shipped skill covers exact-anchor prose insertion into a Markdown *body* ...; I fell back
      to the general Edit tool plus the memory-derived ... discipline rather than a dedicated tool."
      So the baseline knows the PRINCIPLE from this machine's memory cascade and lacks the TOOL.
- [x] Consequence recorded rather than argued away: for a SINGLE INTERACTIVE edit the Edit tool
      already refuses a non-unique anchor, so the jig's value is the SCRIPTED and bulk path. The
      row says so, and the claim for the tool is narrowed to match.

## GREEN

- [x] GREEN arm, sonnet, same scenario with the new table. Selected
      `anchor_edit.py insert --before`, passed the prose via `--new-file` rather than the shell,
      ran `--dry-run` first, then applied, then verified with `git diff`. It cited the mechanism:
      "`require_unique` ... raises (exit 1, nothing written) unless the anchor occurs exactly once,
      and `assert_no_removals` guarantees every character of the original file is still present".
- [x] GREEN diffed against RED in BOTH directions. Nothing RED produced is missing from GREEN;
      both converge on widening the anchor when it is not unique.
- [x] Every dispatch asked for a `Skill gaps` section and every reply's list is recorded below.

- [x] Confirming arm on haiku, the least inferential tier, on the SCRIPTED case the row now
      claims. Zero tool uses, so it answered from the table alone rather than from this checkout.
      Selected `anchor_edit.py insert ... --before`, guarded the script with `set -e` so a refusal
      stops it, and stated "spliced verbatim. The trailing newline is included in the string to
      preserve spacing" - which is the gap closed above, holding on the weakest tier.

## Gaps reported, each closed or declined

- CLOSED: "I guessed the correct blank-line shape ... this is inference from reading the source,
  not something the `--help` output or the skill excerpt states explicitly." The tool splices
  verbatim and adds no newline. Now stated in the module docstring and on `--new-text`'s help.
- DECLINED: "cannot rule out `## Limits` appearing as a substring elsewhere." That is the designed
  refusal - `require_unique` stops rather than guesses, and the answer is a wider anchor.
- DECLINED: markdown blank-line conventions around a heading. Owned by the caller's document, not
  by an editing tool.
- RE-OPENED, and DECLINED as out of scope for this change with the reason recorded: locating the
  scripts directory from a COMMITTED script. Two of three arms stalled here independently, one
  writing a `$SKILL_SCRIPTS` placeholder it could not fill. The row now points at the scripted
  path, and the installed plugin path is VERSION-STAMPED, so a release script that hard-codes it
  breaks on the next plugin update - and resolving it with a glob plus `tail -1` sorts
  lexicographically, where 5.294.10 lands before 5.294.9.

  Left unfixed here because it is PRE-EXISTING and skill-wide: every one of the jigs is invoked
  the same way, so the answer belongs in the table preamble (or a documented vendoring step, the
  script being a single stdlib-only file) and needs its own RED/GREEN rather than a sentence
  bolted onto one row.
- CLOSED: which insert side is the default. The haiku arm called `--before` the default; the
  default is `--after`, and the help stated neither. Both now say so.

## Verification

- [x] RED-verified: `assert_no_removals` was written line-level first and the insertion test
      FAILED against it, because a mid-line insertion changes a line while removing nothing. The
      check now compares characters, which is what its name claims.
- [x] Live control on real files: the same `insert` command that succeeds on a file containing the
      anchor exits 1 on a file without it, leaving that file byte-identical. A wrong-file edit is
      refused by construction, not by care.
- [x] 18 tests pass, and pass in a fresh venv holding ONLY pytest - the script imports stdlib only,
      so the contribution gate cannot hit a `ModuleNotFoundError` it does not provision for.
- [x] Whole-repo gate green: `repo-gate.py --ci` reports all checks passed.
- [x] Description unchanged and measured at 1009 characters, under the 1024 cap. No trigger was
      added to it, so the derived trigger map is unaffected.
- [x] No address, MAC, hostname or machine path added: the grep over both new files is clean, and
      the scenarios use `/path/to/project`.
- [x] No `shell=True`, `eval` or `exec` in the new script; it runs `git` through an argv list.
- [x] `compuse-toolbox` has no mirrored twin, so no second copy needs this change.
