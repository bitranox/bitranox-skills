# skill-writer checklist - GREEN results and the refactor they forced

Follow-up to `checklist-20260731-interface-shape-and-machine-drivable-cli.md`, whose last box
("GREEN re-run") was still open when 5.112.0 was committed. This closes it, and records that
GREEN was a PARTIAL pass.

## GREEN - both fixtures replayed against the edited skill

Cast adversarially on purpose: each fixture went to the model that had failed hardest on it at
baseline, so a pass could not be explained by picking a favourable reviewer.

- [x] **CLI fixture (`spoolcheck`) on sonnet - PASS, clean.** Baseline: ten findings, ZERO about
      machine-readability. After: walked the row as "Machine-drivable (COUNTED)" and reported
      "0 of 3 subcommands offer a structured/--json mode; diagnostics confirmed on stdout not
      stderr; exit code confirmed 0 on a fully-unreachable report run" - verified by RUNNING the
      tool, not by reading it. Every baseline finding was retained; nothing was crowded out.
- [x] **No false positives.** On that same fixture the interface-shape census correctly found
      NOTHING and said so with numbers ("max params 2; 0 clumps; 0 anonymous tuple returns; 0
      tramps; 0 re-parses; 1 boolean flag - ordinary CLI toggle, not a smell"). The census can
      exonerate a codebase, which is the property that stops it manufacturing work.
- [x] **Shape fixture (`fleet-telemetry`) on haiku - PASS on counting.** Baseline: no finding at
      all about a shape repeated 26 times. After: walked "Interface shape", stated the counts
      (12 duplicated helpers, 8 identical 8-parameter signatures, 26 anonymous pair-returns) and
      filed two SEVERE findings it had entirely missed.
- [x] **REGRESSION, same run.** It LOST the planted inverted check, which it had found at
      baseline and ranked its top SEVERE finding. The census step ran; the judgement rule
      printed directly below the table did not. Finishing the count felt like finishing the row.

## Why that regression is not an acceptable trade

The inverted classifier reports a degraded controller as healthy. That single correctness bug
outranks every refactor the census produced, so the net effect of that one run was NEGATIVE even
though the section did exactly what it was designed to do. A step added to a procedure competes
with the existing steps for attention rather than adding to it.

Sample size is one run per condition, so this shows the mechanism is plausible, not that it is
stable. Acted on anyway: the cost of the rule being skipped is a shipped correctness bug, and the
cost of the fix is four lines.

## REFACTOR (this change, 5.113.0)

- [x] The meaning check is now a REQUIRED OUTPUT with a verbatim line to report ("read N of N
      sites of `<shape>`; consistent yes/no; inverted `<names>` or none"), not prose following a
      table. A row reporting counts without it is declared not walked.
- [x] The regression itself is written into the section as its justification, so a future editor
      cannot read the requirement as ceremony and trim it.
- [x] Checklist row rewritten: "COUNT ... THEN the meaning check on the dominant shape - both, or
      the row is not walked."
- [x] Added an explicit "counting nothing is a real result" rule, promoted from the observed
      green-cli behaviour, so a clean census is reported with numbers rather than nudging the
      reviewer toward inventing findings.
- [x] The machine-drivable section is UNCHANGED: green-cli shows it works as written, and it has
      no separate judgement step to skip - every one of its five rows is mechanical.
- [x] ASCII only (36 added lines verified); version 5.113.0; repo gate re-run.

## Not done

- [ ] Re-replay the shape fixture against 5.113.0 to confirm the meaning check now fires. The
      required-output line is a plausible fix, not a verified one. Left open deliberately rather
      than assumed - the same mistake this checklist exists to record.
