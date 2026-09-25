# Real tables copied verbatim from shipped skill docs

Source: write-humanize-en/SKILL.md

> | Metric                  | Figure            |
> |-------------------------|-------------------|
> | Market Valuation (2024) | ~USD 2.1 billion  |
> | Major Facilities        | NLDB, CBR Biobank |

Source: coding-bash-clean-architecture/SKILL.md

| Mistake                                          | Fix                                                                       |
|--------------------------------------------------|---------------------------------------------------------------------------|
| Calling `curl`/`grep`/`find` in domain functions | Domain is pure; wrap I/O commands in adapter functions                    |
| Using global variables for data flow             | Use stdout + capture, or namerefs (`declare -n`)                          |
| Logging to stdout                                | Stdout is for data; log to stderr (`>&2`)                                 |
| Hardcoding file paths in use cases               | Pass paths as parameters; set defaults in composition root                |
| Mixing argument parsing with business logic      | Parse in adapter/composition; pass validated values to use cases          |
| No `set -euo pipefail`                           | Always set at script top; handle expected failures with `\| true` or `if` |
| Random exit codes                                | Use structured exit code table; map in composition root                   |
| `trap` cleanup in random functions               | Single `trap` in composition root; adapters provide cleanup functions     |
| Sourcing everything at top level                 | Source only what each layer needs; domain sources nothing                 |
| `eval` for dynamic dispatch                      | Use `"$fn_name" args` (indirect call)  -  safe, no eval needed            |

Source: coding-bash-reference/redirections-and-execution.md

| Operator | Behavior                                                                                               |
|----------|--------------------------------------------------------------------------------------------------------|
| `>`      | Redirects output; **fails** if `noclobber` is set and the file exists as a regular file                |
| `>\|`    | Redirects output; **overrides `noclobber`** -- always attempts the redirection even if the file exists |

Source: coding-bash-clean-architecture/SKILL.md

| Code | Meaning                                |
|-----:|----------------------------------------|
| 0    | Success                                |
| 1    | General error                          |
| 2    | Invalid input / usage error            |
| 3    | Not found                              |
| 4    | Conflict / precondition fail           |
| 70   | Unexpected internal error              |
| 124  | Timeout                                |
| 126  | Permission denied                      |
| 127  | Command not found (dependency missing) |

Source: coding-python-clean-architecture/script-mode.md

| Code | Meaning                      |
|-----:|------------------------------|
| 0    | Success                      |
| 1    | Check ran, result negative   |
| 2    | Invalid input / usage error  |
| 3    | Not found                    |
| 4    | Conflict / precondition fail |
| 70   | Unexpected internal error    |
| 124  | Timeout / cancelled          |

Source: process-review-verification-before-completion/SKILL.md

| Excuse                                  | Reality                |
|-----------------------------------------|------------------------|
| "Should work now"                       | RUN the verification   |
| "I'm confident"                         | Confidence ≠ evidence  |
| "Just this once"                        | No exceptions          |
| "Linter passed"                         | Linter ≠ compiler      |
| "Agent said success"                    | Verify independently   |
| "I'm tired"                             | Exhaustion ≠ excuse    |
| "Partial check is enough"               | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter     |

Source: process-test-driven-development/SKILL.md

| Excuse                                 | Reality                                                                 |
|----------------------------------------|-------------------------------------------------------------------------|
| "Too simple to test"                   | Simple code breaks. Test takes 30 seconds.                              |
| "I'll test after"                      | Tests passing immediately prove nothing.                                |
| "Tests after achieve same goals"       | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested"              | Ad-hoc ≠ systematic. No record, can't re-run.                           |
| "Deleting X hours is wasteful"         | Sunk cost fallacy. Keeping unverified code is technical debt.           |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete.             |
| "Need to explore first"                | Fine. Throw away exploration, start with TDD.                           |
| "Test hard = design unclear"           | Listen to test. Hard to test = hard to use.                             |
| "TDD will slow me down"                | TDD faster than debugging. Pragmatic = test-first.                      |
| "Manual test faster"                   | Manual doesn't prove edge cases. You'll re-test every change.           |
| "Existing code has no tests"           | You're improving it. Add tests for existing code.                       |

Source: meta-claude-hooks/SKILL.md

| Verdict      | Exit | What you do                                                                                                                                               |
|--------------|------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `CURRENT`    | 0    | proceed; these files are authoritative                                                                                                                    |
| `COSMETIC`   | 0    | proceed; upstream prose changed but the API surface did not. Say which sections moved                                                                     |
| `STRUCTURAL` | 1    | **stop treating this skill as exhaustive.** Report the added/removed names, read those upstream sections, update the reference file, then `stamp --write` |
| `BROKEN`     | 2    | say "freshness unverified: <reason>". Do **not** say up to date, and do **not** say stale. Keep using the files, flagged as unverified                    |
