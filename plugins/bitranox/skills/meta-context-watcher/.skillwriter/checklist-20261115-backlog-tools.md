# checklist - backlog tools: header close steps, the returned path, create_new

Three additions to "Read and edit it through the backlog tools" and the closing paragraph:
read the backlog header before `backlog_close` (it deletes without reading it); read the returned
`path` first and repair a write that landed in the wrong copy; on the "would split the backlog"
refusal, decide `create_new` by which project owns the work.

Decisions: d-20261115-d3ee5b9b

## RED

- [x] Skill decisions read first: the skill has no rejected or removed entries.
- [x] Mechanisms checked in code, not assumed: `hooks/mod_bridge.py` `_backlog_close` calls
      `ow.close_item(path, rank, reason)` with no header read; every tool resolves
      `ow.backlog_path(cwd)` from `Path(os.getcwd())` at call time (`mod_bridge.py:197`);
      `_refuse_a_second_backlog` refuses whenever `ow.enclosing_backlog(path.parent)` finds a file,
      with no repository check.
- [x] Queued premise partly wrong: "compare git top levels, refuse only inside the same
      repository" cannot discriminate, because an ancestor OPEN-WORK.md above the cwd's git top
      level is always in another (enclosing) repository. The text therefore decides by ownership
      of the work, not by a repository test.
- [x] Coverage probe on the pre-edit text, text-only, opus and haiku: the header close step,
      the wrong-copy path and the create_new case answered NOT STATED on both tiers.

## GREEN

- [x] Same questions on the edited text, opus and haiku: both tiers quoted the new sentences and
      answered archive-then-close, restore-then-hand-edit, and create_new for the nested project.
- [x] Quote-back: each quote is verbatim from the edited text.

## REFACTOR

- [x] Declined (opus): "create_new is missing from backlog_add's parameter list" - the refusal
      sentence that names it follows directly after that list, and the refusal message itself
      names it (`mod_bridge.py:75`).
- [x] Declined (opus, haiku): "where the line to archive comes from before the close" -
      `backlog_list` in the same paragraph returns the lines, and the file can be read directly.
- [x] Declined (haiku): "restoring when the main checkout's tree is a peer's" - the sentence
      already says to put back only that line and leave every other line alone.
- [x] Width and fence check over the added lines printed nothing.
