# skill-writer checklist - process-review-enhance-code-quality (2026-07-29, test-design delegation)

Change: the Testing dimension - the heaviest at 20% - was specified as the four words "Coverage %,
test quality, edge cases, isolation", and the skill contained no reference to `process-test-design`,
so the criteria that define test quality were never loaded. Replaced with a "Testing is not the
coverage number" block (a five-row gap table with a cap-at-5 rule, an explicit delete-the-filler
instruction, and delegation to `bitranox:process-test-design`), plus a rewritten Tests row in the
aspect checklist and three Common Mistakes rows. Shipped in plugin 5.102.0.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED ran on a purpose-built fixture, not a hypothetical: a Python service whose suite
      monkeypatches its own `_post`/`_record` methods, has no test touching real HTTP or a real DB,
      and carries five filler tests (constructor-stores-its-argument, "is an Exception subclass",
      frozen-dataclass). The fixture's prompt never used the words mock, e2e, integration, flaky or
      low-value - the scenario withholds the answer the skill is supposed to supply.
- [x] The fixture hides a real defect behind the mocks, verified by running it: `_record` inserts
      into a table nothing ever creates, so `submit()` raises
      `sqlite3.OperationalError: no such table: orders` on the first real call. The suite is 10/10
      green over a broken contract. This is the "green units, broken contract" case made concrete.
- [x] RED on a weak/literal model (haiku) FAILED cleanly, which is the baseline that matters: it
      scored Testing 6/10 citing "10/10 tests passing, 78% coverage", never found the missing table,
      framed the mocked-out methods purely as a coverage percentage, and - worse than silence -
      recommended ADDING a `# pyright: ignore` suppression to preserve a filler test.
- [x] RED re-run on a capable model (sonnet) per the known false-pass mode: it routed around the gap
      via general competence, finding the missing table and naming the self-mocking. This is the
      documented "a capable model masks a rigid-rule gap" pattern, so it does not clear the skill.
- [x] One gap survived BOTH models and drove the delete-the-filler paragraph: neither run proposed
      removing a single worthless test. The skill only ever pointed at adding tests, so five
      deletable tests were invisible to both, and the weak model actively defended one.
- [x] Both halves of the fix are load-bearing: delegation alone would leave "test quality" to
      ad-hoc judgment, and the gap table alone would duplicate a sibling skill. The table names the
      five gaps and hands the criteria to `process-test-design` rather than restating them.
- [x] Guarded the opposite failure - a reviewer nagging about tests on a project that deliberately
      accepts thin coverage - by leaving Step 1/Step 4 accepted-item handling untouched; a
      documented "minimal test coverage by design" is still respected silently.
- [x] Scope: shared/general, no project-specific content; the gap table is language-neutral and the
      sibling skill it delegates to now carries the per-language mechanics.
- [x] Security scan: prose and tables, no secrets, hostnames, private paths or PII. The example
      names a fictional service and a table name only.
- [x] CSO description: frontmatter untouched (a body change; the triggering conditions are unchanged).
- [x] Token budget: a process skill that is a checklist by nature; net +38 lines, one new table,
      three mistake rows, one rubric cell repointed.
- [x] Derived artifacts regenerated (build_skill_triggers.py, build_skill_docs.py) and
      `repo-gate.py --ci` run with CI's full dependency set: all checks passed.
- [x] GREEN verified on the SAME weak model that failed RED, same fixture, same prompt: Testing went
      6/10 ("10/10 tests passing, 78% coverage") to 3/10 ("self-mocking prevents real validation;
      50% are low-value filler"). It raised the self-mocked seams and the absent integration proof
      as two SEVERE findings, and listed all five filler tests as individual deletions. No
      suppression was proposed this time - the previous run's `# pyright: ignore` recommendation is
      gone. The weak model still did not spot the missing table unaided, but it now demands the
      integration test that exposes it, which is the behaviour the skill is responsible for.
