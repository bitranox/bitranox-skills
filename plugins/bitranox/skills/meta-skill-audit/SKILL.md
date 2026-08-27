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

## Run the deterministic checks first

Anything a script can decide, decide with a script: it covers the whole catalogue in seconds, it
cannot hallucinate a quote, and it costs nothing to re-run after every fix. Spend the reviewers on
what is left - claims that need judgement or a live tool to check.

```bash
# every shipped example must at least parse
python3 - <<'EOF'
import ast, pathlib
for p in pathlib.Path("skills").rglob("*.py"):
    if "__pycache__" in str(p): continue
    try: ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e: print("%s:%s %s" % (p, e.lineno, e.msg))
EOF
```

Worth the same treatment: JSON/YAML files that must parse, `CSS_PATH`-style asset references that
must resolve, relative links that must land on a shipped file, and the plugin's own mirror gate.
A real sweep found a shipped example with unescaped nested quotes that had never been executed -
one second of `ast.parse` over the catalogue, against several minutes of reviewer time per skill.

## Procedure

1. **Wall recall and record the old value.** Use the shipped front door - `settings.py` (home:
   `skills/meta-memory-settings/`, launch via `hooks/run-python.sh`), which validates the value and
   refuses an unknown one. `self_improve_signals.save_config` is a library function with no CLI, so
   it is not something you can run.

   ```bash
   settings.py view > <room>/cross_tree_search.before   # a sweep is long; the restore is easy to lose
   settings.py set cross_tree_search false
   ```
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
4b. **Do NOT reuse that quote match to ask which findings are still OPEN.** A triage outlives
   several fix-and-ship rounds, so you will come back to the list against a changed tree - and
   step 4's rule inverts into a plausible wrong one: "quote gone, so it was fixed". Measured
   over one round, that is wrong in BOTH directions. Quote GONE and still open: an unrelated
   edit requoted the line, and the recorded quote had been normalized so it never matched the
   file verbatim anyway. Quote PRESENT and fixed: the repair made the documented command WORK,
   so the example text correctly survives. Re-read the CLAIM against the file instead, and keep
   an explicit list of what you fixed - the work you did is the record, not a state query over
   the tree.
5. **Fix, then mirror.** A skill that also ships from its own tool repo has a twin, and a fix
   applied to one copy leaves the other wrong. Regenerate the stale side, re-apply the by-convention
   divergences, and bump BOTH plugin versions.

## Auditing the shipped SCRIPTS, not the skills

The same harness reviews a plugin's shipped Python and JavaScript - hooks, skill scripts, the shim -
with `--scripts`. It is a different job from the skill sweep and its defaults say so: one reviewer
per FILE rather than per skill, `opus` rather than `sonnet`, because judging a script needs a
concrete failing input and a decision about whether a fail-open path is house style or a defect.

```bash
scripts/audit_skills.py --plugin <plugin dir> --room <dir outside the tree> --scripts \
    --kind hook --skip-existing
```

Run `--help` for the full flag list; these are the three choices it cannot make for you.

- **`--kind` is how a 134-target run becomes survivable.** Slice by `hook`, `hook-lib`, `shim`,
  `skill-script` or `js` and triage each slice before spending the next. `--list` prints the corpus
  and exits without spending a reviewer, which is what to run first.
- **`--skip-existing` is the resume switch**, and it pairs with `--reuse-room`: a target whose
  report already exists and is non-empty is skipped. Without both, an interrupted run restarts from
  zero against a freshly-copied room.
- **`--include-vendored` is off, and should usually stay off.** Upstream sample code (`demos/`,
  `examples/`) ships as a copy of someone else's repository, so fixing a defect there diverges our
  copy from its source and the next sync silently reverts it. Those files still get `ast.parse` from
  the pre-pass - the one property we own whatever upstream says.

### The pre-pass runs first, and its two kinds of hit are not the same

`script_prepass.py` (home: `skills/meta-skill-audit/scripts/`, launch via `hooks/run-python.sh`)
scans the whole corpus deterministically before any reviewer starts, and `--scripts` runs it for you
- it is not a separate step. Run it alone with `--room <plugin dir>` to see the corpus summary, or
`--json` for the per-file map.

What it finds splits in two, and a reviewer is told the OPPOSITE thing about each:

| Kind             | Example                                                  | The reviewer is told                      |
|------------------|----------------------------------------------------------|-------------------------------------------|
| **Settled fact** | `text=True` with no `encoding=`; a hook carrying PEP 723 | already known, do not re-report           |
| **Lead**         | `shlex` on a path; no test module names this stem        | not settled, judge it and say which it is |

Keep that split. A settled fact is wrong wherever it appears and one line names the fix, so 133
reviewers re-deriving it is pure noise. A lead is only a defect depending on what the code does with
the result - which is the judgement the reviewer exists to make, and suppressing it silences the one
reader who can answer, in the files most likely to hold a real defect.

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
- **Assuming the clean room isolates the MACHINE.** It isolates context, not the filesystem. A
  reviewer told to verify a claim will install what it needs to verify it: one sweep pip-installed
  a package into the ambient environment, which flipped a skill's tests from skipping to running
  and turned a green gate red mid-session. Expect the host to change under you, and never point a
  sweep at a machine where an install would matter.
- **Trusting any gate run that OVERLAPS the sweep.** It is unreliable in both directions: the same
  run reported two failures that neither the isolated nor the ambient interpreter could reproduce
  once the sweep's concurrent installs had settled. Gate before the sweep or after it, never
  during, and re-run rather than debugging a result from the overlap.
