# skill-writer checklist - process-test-design (2026-10-19)

Change: a fifth bullet under "mechanics worth stating because they silently defeat a test that
looks right": a standard-library wrapper can hold its own copy of the function a test patches, on
some interpreter versions only (Python 3.10 `Path.cwd` against a patched `os.getcwd`). The lead-in
count goes from four to five. Skill type: technique (application test).

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] The claim was measured before it was written: a probe replacing `os.getcwd` and calling
      `Path.cwd()` printed the real directory on 3.10 and the patched value on 3.11, 3.12, 3.13 and
      3.14.
- [x] Inherited context checked with `redcheck --corpus-cascade` from this checkout: clean (WEAK
      evidence), 1587 documents read.
- [x] RED (haiku, `bitranox:baseline-probe`, the four existing bullets, NONE allowed): a test
      replaces `os.getcwd`, the code calls `Path.cwd()`, green on 3.12 and 3.14, red on 3.10 where
      it read a real config file. Answer: NONE; it named the from-import bullet as nearest and
      "quoting it as governing would be a stretch", and listed as gaps that the text never says how
      to produce a failing cwd or that the test should prove the patch was reached.
- [x] GREEN (same tier, same situation, the edited list): quoted "Python 3.10's
      `pathlib.Path.cwd()` calls `os.getcwd` through an accessor that bound it at import, so
      `monkeypatch.setattr(os, "getcwd", fake)` never reaches it there, while 3.11 and later read
      `os.getcwd` at call time and the same test is right." It then chose patching `Path.cwd` or a
      removed cwd, proving it on 3.10, and a sandbox config file a missed patch would read.
- [x] GREEN diffed against RED both ways: RED's injection advice survives (the bullet keeps "the
      real lookup" route as the better one); nothing RED produced is missing.
- [x] Skill gaps from GREEN, each decided: how to prove the patch reaches it - CLOSED, the bullet
      now says to undo the fix and require the test RED on the oldest interpreter; the
      chdir-and-remove route being POSIX-only - declined, the bullet says POSIX and Windows refuses
      to remove a directory in use; which route to prefer - declined, "better" already ranks them;
      injecting a cwd source - declined, the first bullet and the skill's opening rule cover
      injection.
- [x] Phrased as the general mechanism, with the 3.10 accessor as its supporting instance.
- [x] Table canonical per `reformat_tables --check` (no table touched).
- [x] Security scan: prose only; no addresses, hosts or paths added.
