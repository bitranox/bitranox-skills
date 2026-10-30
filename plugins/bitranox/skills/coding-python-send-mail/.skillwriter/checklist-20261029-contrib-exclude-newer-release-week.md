# Review: the cooldown during a release week (contrib entry)

- [x] RED: the pre-edit Install section gave only `--exclude-newer "7 days"` forms;
      `grep -c exclude-newer-package SKILL.md` was 0.
- [x] Measured with uv 0.13.0 and an empty scratch cache, six days after a release: the unpinned
      `uvx --exclude-newer "7 days" btx-lib-mail --version` exits 0 and runs the PREVIOUS release;
      pinning the new version exits 1 with `No solution found` and a hint naming
      `exclude-newer-package`. The queued entry expected the unpinned line itself to fail; the
      measurement corrected that.
- [x] Both new command lines executed: `uvx ... --exclude-newer-package btx-lib-mail=false
      btx-lib-mail --version` and the `uv tool install` form (scratch UV_TOOL_DIR) run the new
      release; the tool receipt holds `exclude-newer-package = { btx-lib-mail = false }` beside
      the cooldown. The underscore spelling resolves the same.
- [x] GREEN: `grep -n "exclude-newer-package" SKILL.md` quotes the new paragraph.
- [x] Twin: the same block inserted at the same anchor; `diff -r -x .skillwriter -x __pycache__`
      shows only the `name:` line and the tool repo's self-install blockquote.
- [x] ASCII only; description untouched.
- [x] Declined, not run: subagent quote-back probes (this pass dispatched no subagents).
