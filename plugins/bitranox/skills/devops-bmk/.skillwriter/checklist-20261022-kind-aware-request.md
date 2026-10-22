# skill-writer checklist - devops-bmk (2026-10-22, kind-aware-request)

- [x] Change: the hand resync for a project without a Python classifier asks for what the venv's
      interpreter reports: `pypy@X.Y` for PyPy (`X.Y` from the Python version line, example
      `pypy@3.11`), `X.Yt` for a free-threaded build (example `3.13t`, recognised by the
      `sysconfig.get_config_var('Py_GIL_DISABLED')` one-liner printing `1`), otherwise the bare
      minor. It says why: a bare minor for a PyPy or free-threaded venv lets a recreate fall back
      to uv's default CPython, and bmk never passes the interpreter's path, on any version.
- [x] Every claim checked against bmk source: `venv._python_request` (`pypy@X.Y`, `X.Yt`, else
      `X.Y`), `venv._INTERPRETER_PROBE` (implementation, `sys.version_info[:3]`,
      `Py_GIL_DISABLED`), `venv._sync_python_request` (declared minor first; the path only when
      the probe cannot answer). The PyPy fallback to CPython under a bare minor is measured by the
      real-uv test `test_a_pypy_venv_without_a_declared_minor_that_uv_sync_recreates_stays_pypy`
      (it fails with `assert 'cpython' == 'pypy'` when the PyPy branch is removed). PyPy's
      `--version` output was read on a PyPy 3.11 build: first line `Python 3.11.13 (...)`, second
      line `[PyPy 7.3.20 ...]`.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route: a text check of the artifact, four claims (`pypy@X.Y` for PyPy, `X.Yt` for a
      free-threaded build, the bare minor otherwise, why a bare minor is wrong for PyPy). On the
      pre-change SKILL.md all four FAIL (exit 1); on the final text all four PASS (exit 0).
- [x] GREEN quote-back, opus and haiku, three questions (PyPy 3.11 venv; free-threaded 3.13.5;
      ordinary CPython 3.12.4 and whether its path may be passed). Both tiers gave `pypy@3.11`,
      `3.13t` and `3.12` with direct quotes. 2 tiers x 3 questions.
- [x] Gaps closed after GREEN: whether the interpreter path is acceptable on CPython 3.11 and newer
      (both tiers; now "bmk never passes the interpreter's path, on any version"); which version
      line gives PyPy's `X.Y` (now the Python version on the first line, not PyPy's own); no
      filled-in examples for the special forms (now `pypy@3.11` and `3.13t`).
- [x] Re-probe on the final text, haiku, two questions (a PyPy 3.10 venv; the path on CPython
      3.12). Answers: `pypy@3.10` "taking 3.10 from the first line, not 7.3 from the PyPy line",
      and "No. Pass the bare minor `--python 3.12`", each with a direct quote. No new undecided
      gap: its remaining notes are declined below (another implementation, such as GraalPy, gets
      the bare minor in bmk too, so the text matches the code).
- [x] Gaps declined: classifiers on a PyPy or free-threaded venv (the classifier path builds
      CPython by design: classifiers name CPython versions, and the section's version paragraphs
      cover it); precedence between PyPy and free-threaded (PyPy has no free-threaded build); a
      Windows form of each command (the paragraph names the Windows interpreter path once,
      `.venv\Scripts\python.exe`, and the commands are the same with it); when uv recreates a venv (stated in the version paragraphs of the same section);
      no venv at all (nothing to resync; provisioning creates it).
- [x] GREEN diffed against RED both ways: the removed claim is "the bare minor, always", which is
      false for PyPy and free-threaded venvs against the code. Nothing else the old text taught is
      lost.
- [x] Mirrors the bmk repo's copy byte for byte.
