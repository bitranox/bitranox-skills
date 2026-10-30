# Driving `mutation_arm` so its verdict means something

Each of these has produced a verdict that looked right and meant nothing.

- **Run an inert control first.** Before trusting any KILLED, run a mutation that cannot change
  behaviour (a comment-only or docstring-only edit). It MUST come back SURVIVED. KILLED means the
  test fails without any real change (red or flaky at baseline, or the "inert" text is read by a
  doctest or `inspect`); INCONCLUSIVE (exit 2) means the runner never ran the test, usually an
  interpreter without pytest or the project - a pytest exit 1 with no FAILED/ERROR summary line is
  scored INCONCLUSIVE, never KILLED. Read the envelope's `failure` field and `caught_by`, not only
  the verdict word: a kill names the FAILED node id that caught it.
- **Know which interpreter runs the arm** (the report names it as `runner` / `runner_source`):
  `--python PATH`, else `--with DEP` through uv, else `./.venv`'s python under the current
  directory, else the interpreter running the tool. Launch it from the project root, or pass
  `--python PATH`: a bare `uv run` with no `.venv` in the current directory runs the arm on uv's
  interpreter, which has neither pytest nor the project, and every arm reads INCONCLUSIVE.
- **`--mutate` takes FILE PATHS** (`FILE OLD_FILE NEW_FILE`), not literal strings, and every
  `--mutate` in one call is ONE arm. A fix spanning two places is proved in one run, not as two arms
  that each survive.
- **Write each anchor file in its own EARLIER command, with an absolute path.** A `printf ... >
  old.txt` chained into the same command lands in the shell's current directory (often the repo
  root, where it can get staged), and the tool then refuses with "No such file or directory" naming
  the file rather than the directory.
- **A whole-suite arm must hand pytest the source tree too.** Under `--doctest-modules`, doctests are
  collected only from the paths pytest is given, so `tests` alone never runs them and an invariant
  held only by a doctest reads as SURVIVED. Name both as the arm's tests (`"tests": ["tests",
  "src"]` in a `--battery` spec; `--test` takes a single node id) and check the collected count
  includes the doctest items before reading a survivor as a gap.
- **A NON-pytest suite runs through `--cmd "<command>"`** (`cargo test -p crate`, `make check`),
  split without a shell. Its exit decides the arm: 0 survived, a failure killed, and a mutant that
  does not BUILD (or a command that cannot run) INCONCLUSIVE, because a compile error is not a test
  catching the change. The restore writes the original bytes with a FRESH mtime: an mtime-keyed
  build cache (cargo, make) would otherwise see the restored file as older than the mutant's build
  and keep running the mutant.

## When the tool is not in reach

A `.pyc` is validated against the source's mtime SECOND and SIZE, so a length-preserving mutation
in the same second as the last edit is invisible to the cache, in both directions (a stale mutant
served after the restore, or a pre-mutation cache served in place of the mutant, which reads
SURVIVED). Hand-rolled, set `PYTHONDONTWRITEBYTECODE=1` in the pytest environment (pytest has no
`-B` flag and exits with a usage error on it), remove every `__pycache__` under the tree before and
after the arm, restore from a copy taken first with a plain copy (never `cp -p` or `copy2`,
which bring the OLD mtime back for a build cache to trust; never `git checkout --`, which discards
uncommitted work), and prefer a length-CHANGING mutation, which invalidates the cache on size alone.
