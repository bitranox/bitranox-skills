# The nap's backup goes to the durable backup home

Step 2 names the `--out` directory for `store_manifest.py backup`: the core's durable backup home
under `~/.claude/self-improve-audit/backups/`, not the session scratchpad.

- [x] Step 0b: rejected and removed decisions read; the one rejected entry (reconcile verify
      step) is not touched.
- [x] Premise check: dream-core.md ("Backup + manifest") and meta-dream-tree step 2 name
      `~/.claude/self-improve-audit/backups/<key>-<ts>/`, and store_manifest.py's own refusal for
      an `--out` inside the tree points there; `--out` is required with no default
      (store_manifest.py, `bk.add_argument("--out", required=True, ...)`), so no script default
      had to change.
- [x] The step's command executed on a scratch tree with a scratch HOME:
      `store_manifest.py backup --from <tree>/proj --scope chain --out
      <home>/.claude/self-improve-audit/backups/nap-proj-<date +%Y%m%d-%H%M%S>` exited 0, printed
      `backed up 1 pointer(s) (chain scope)`, and wrote `manifest.json`, `levels/` and `store/`.
- [x] RED: text probe of the pre-edit step on haiku answered that the text names only "a new
      directory in the scratchpad", quoting it.
- [x] GREEN on opus and haiku with the edited step pasted: both answered
      `~/.claude/self-improve-audit/backups/nap-proj-<timestamp>`, quoting the new line; both
      reported the timestamp format as a guess.
- [x] Fix round: `<timestamp>` is defined as `date +%Y%m%d-%H%M%S`; re-probe on haiku answered
      `~/.claude/self-improve-audit/backups/nap-proj-20260102-030405` for 2026-01-02 03:04:05,
      quoting the definition.
- [x] Gaps declined: whether `~` expands (the tree dream's step 2 and dream-core.md write the
      same unquoted `~` path); what "the core" is (the nap's opening lines name
      `bitranox:meta-dream-tree` -> references/dream-core.md); whether `--out` must exist
      (store_manifest.py's usage text in its docstring: new, empty, or an earlier backup).
- [x] Decisions: d-20261119-4cfc609a
- [x] Tiers: opus and haiku, text-only agent type, pasted text; 1 RED + 2 GREEN + 1 re-probe cell.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion ("Only that command's backup counts") still reads against the same command.
