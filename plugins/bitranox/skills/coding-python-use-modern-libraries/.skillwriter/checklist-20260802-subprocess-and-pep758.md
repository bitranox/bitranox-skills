# skill-writer checklist - coding-python-use-modern-libraries (2026-08-02, two Python notes)

Change: two notes added - `subprocess` raising a different exception TYPE per OS for one condition,
and PEP 758 making `except A, B:` valid on 3.14+. Ships with plugin 5.139.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued for this batch).
- [x] Both are measured. The WinError 267 case was a real cross-platform exit-code divergence (126 vs
      127 for the same missing `cwd`), caught only by Windows CI while POSIX stayed green. The PEP 758
      case is a near-miss: an `except orjson.JSONDecodeError, ValueError:` in a repo pinned to
      `requires-python >=3.14` looked like broken Python-2 syntax and was almost "fixed" into a
      needless change; `py_compile` and an exec probe showed it catches both.
- [x] Both are framed as WHAT NOT TO CONCLUDE, because both mislead in the same direction: a green
      POSIX run reads as portable, and valid 3.14 syntax reads as a Py2 bug. Each names the check that
      settles it - pre-check the path yourself; read `requires-python` and probe with `python -c`.
- [x] Deliberately NOT added: the `shutil.which` rule this batch also queued for this skill.
      `coding-python-uv` lines 171-182 already carry it with working code, and a general rule belongs
      in one home rather than copied into every plausibly-related skill. Dropped with that reason
      recorded, not silently skipped.
- [x] Verified ABSENT before writing and PRESENT after, using control-gated `claim_check` against the
      whole skill tree rather than this file alone.
- [x] Placed in `## Notes`, matching the file's existing bullet voice and length; no new section
      invented for two bullets.
- [x] No session narrative, no private paths, no machine-specific detail in the shipped text.
- [x] Suites green and `repo-gate.py --ci` clean with the CI dependency set.
