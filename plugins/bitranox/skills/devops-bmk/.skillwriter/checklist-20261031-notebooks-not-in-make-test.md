# Review checklist 2026-10-31: `make test` never executes a notebook

Change: two paragraphs in "Proving a gate actually ENFORCES". `make test` runs no notebook while
the CI template's "Execute notebooks" job runs `notebooks/Quickstart.ipynb` under nbclient with
`allow_errors=False`; a command that runs it the way that job does; and a warning that a notebook
whose install cell always installs `git+https://...` tests what is already pushed, not the change.

## Claims and their evidence

- [x] No bmk stage executes a notebook: `grep -rniE 'nbclient|nbconvert|ipynb|notebook'` over
      bmk's `src/` (`.py`, `.toml`) returns nothing.
- [x] CI runs it with nbclient, `allow_errors=False`, `kernel_name='python3'`, no `resources`
      path, after installing only `nbclient nbformat ipykernel jupyter_client`: read from the
      template workflow's `notebooks` job.
- [x] The shipped command, extracted verbatim from SKILL.md and run from the repo root of a
      `git archive` export: exit 0 and `NOTEBOOK OK` for two projects' notebooks.
- [x] Negative control: the same command on a copy with a `raise RuntimeError("planted")` cell
      appended: exit 1, a `CellExecutionError` naming that cell, no `NOTEBOOK OK`.
- [x] The command does not rewrite the notebook: it calls `execute()` and never `nbformat.write`.
- [x] Install cells differ: one notebook installs from the checkout when its `pyproject.toml` is
      in the working directory or a parent, another always installs `git+https://github.com/...`
      (both read from the notebooks' source). That a git+https install tests the pushed code is
      argued from that line, not measured.

## Probes (text only, haiku, passage pasted, quote-back required)

- [x] RED (pre-edit section): NOT COVERED on "does a green `make test` mean the notebook runs"
      and on "which command checks it the way CI does".
- [x] GREEN: answered both by quoting the new paragraph and the command. Gaps it reported: no
      explicit "do not push on exit 1", the hardcoded `3.14` against "the version CI names", and
      how the project reaches the kernel. All three closed in the text.
- [x] Final probe on the final text: quoted "exit 1 is the CI failure you would push, so fix it
      first", the `--python` sentence, and both install-cell sentences correctly (4 of 4).
      Its one actionable gap, how to point the install at the checkout, was closed with the
      scratch-copy clause.

## Gaps declined

- How to build a failing arm for the notebook: the section's own "Prove it" paragraph states the
  rule; the planted-cell control above is evidence, not text a reader needs in the skill.
- Exit codes beyond 0 and 1 (kernel death, timeout): nbclient raises an exception for both, which
  the `python -c` process turns into a non-zero exit like any other failing cell.
- The notebook path is hardcoded: the CI job reads the same fixed `notebooks/Quickstart.ipynb`.
- Which kernel `python3` resolves to: the measured runs show it resolves to the uv environment's
  ipykernel; the reader needs no choice there.
