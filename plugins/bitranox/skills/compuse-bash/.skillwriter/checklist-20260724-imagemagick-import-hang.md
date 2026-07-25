# skill-writer checklist - compuse-bash (2026-07-24, imagemagick-import-hang)

Change: add a Quick-reference row warning that running a Python file as `bash script.py` makes bash
execute the file's `import os` line as ImageMagick's `import` (an X11 screen-grab on PATH), which
blocks forever at 0% CPU (state S) and drops a stray screenshot file - run Python via `python3` or
the tool's launcher, never `bash`. Shipped in plugin 5.98.4. (Retroactive artifact: the change
committed without its dated checklist because this clone has no pre-commit gate installed and CI
only checks that a checklist exists.)

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the skill covered pgrep/kill and backgrounding traps but had no entry for the
      `bash script.py` -> ImageMagick `import` hang, which cost a ~6-minute silent 0-CPU hang this
      session when a helper `.py` was launched via bash instead of the run-python.sh shim.
- [x] GREEN: a Quick-reference row now names the symptom (0-CPU state-S "slow" script), the cause
      (no `import` builtin; the shebang is a bash comment), the fix (`python3`/launcher), and the
      diagnosis (`pgrep -x import`, kill by PID).
- [x] Scope: shared/general - any user launching a Python file via bash on a machine with
      ImageMagick installed; no machine-specific content.
- [x] Security scan: prose-only table row, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: unchanged (body/table addition, frontmatter untouched).
- [x] Token budget: one table row added to a reference skill.
