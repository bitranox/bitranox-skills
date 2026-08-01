---
name: meta-skill-audit
description: Use when auditing or reviewing a whole catalogue of already-shipped skills for defects - stale claims, references that no longer resolve, instructions a reader cannot follow - rather than authoring or editing one skill. Also use before a release that touches many skills, when a skill's tool has moved on and the skill may not have, or on "audit the skills", "review the skill catalogue", "check the shipped skills".
---

# meta-skill-audit

Reviewing a catalogue of shipped skills is not the same job as writing one. There is no RED to
watch fail: the skill already exists, readers already have it, and what you are looking for is the
claim that has quietly stopped being true. For authoring and editing, use
`bitranox:meta-skill-writer` - this skill starts where that one ends.

**REQUIRED BACKGROUND:** `bitranox:meta-skill-writer`, whose "Watch for baseline contamination"
section explains the isolation this skill depends on.

## The two things that make an audit wrong

**Isolate from MEMORY, not from the plugin.** A reviewer running anywhere on a machine that holds a
curated memory store gets matching entries injected by the recall hook, which fires in every
directory and scans `discovery_roots` (the configured list UNION `$HOME`) regardless of cwd. It
then reports the skill as complete because IT knew the answer. Wall recall for the run and put the
room outside the knowledge tree, so the tree's `CLAUDE.md` cascade does not load either.

**The install unit is the PLUGIN, not the skill directory.** A skill legitimately points at sibling
skills and at the plugin's own hooks, and all of that ships together. Hand a reviewer one skill
directory and it reports every sibling reference as dangling. Measured: 5 of the first 6 findings
in a run framed that way were this one false positive.

## Procedure

1. **Wall recall and record the old value.** `cross_tree_search: false` via `save_config` in
   `self_improve_signals` (home: `<plugin>/hooks/`). Write the original value to a file first - a
   sweep is long and the restore is easy to lose.
2. **Run the sweep.** `scripts/audit_skills.py --plugin <plugin dir> --room <dir outside the tree>`
   (home: `skills/meta-skill-audit/`, launch via `hooks/run-python.sh`). It copies the plugin into
   the room, runs one reviewer per skill at `--jobs` at a time, and writes
   `<room>/reports/<skill>.audit.txt`. Reviewers are slow because they verify - budget minutes per
   skill, not seconds.
3. **Restore the setting and VERIFY the restored value**, before you start editing anything. Do not
   leave it until the end of the triage.
4. **Verify every finding against the real files before acting on one.** A reviewer's quote is a
   claim, not evidence: `grep -F` the quote in the file it names. An unfindable quote means the
   finding is fabricated, whatever else is right about it.
5. **Fix, then mirror.** A skill that also ships from its own tool repo has a twin, and a fix
   applied to one copy leaves the other wrong. Regenerate the stale side, re-apply the by-convention
   divergences, and bump BOTH plugin versions.

## Triage: what a finding is worth

| Class            | Act on it when                                                                        | Usual false positive                                                        |
|------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| **WRONG**        | The quote verifies AND you can reproduce the wrongness (run the command, check help). | The reviewer's own environment differs from the skill's stated target.      |
| **DANGLING**     | The path really is absent from the plugin. Check it yourself with `ls`.               | A sibling skill or plugin hook, reachable from the install, called missing. |
| **UNEXECUTABLE** | A required value, path, order or precondition is genuinely absent.                    | A placeholder the skill tells the reader to fill in, read as an omission.   |
| **STALE**        | The claim is version-bound and carries no version, date, or way to check it.          | A deliberately generic example.                                             |

Rank by what a reader DOES with the defect. A wrong command outranks every missing cross-reference,
because the reader runs the one and merely fails to follow the other.

## Common mistakes

- **Trusting a passing sweep.** A clean report from a contaminated room says nothing. If you could
  not isolate, record that instead of counting it as a pass.
- **Acting on the count.** One reviewer per skill, one run each, is a sample. A skill that reports
  clean once is not verified clean - it is unmeasured, and the next run may differ.
- **Fixing the marketplace copy and stopping.** The twin ships to real installs too.
- **Editing a skill during its own sweep.** The room holds a copy; edits to the live tree mid-run
  are not what was reviewed, and the report's line references drift.
