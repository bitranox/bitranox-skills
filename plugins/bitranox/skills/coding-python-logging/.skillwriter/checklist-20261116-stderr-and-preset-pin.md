# skill-writer checklist - coding-python-logging (2026-11-16, STDERR stream and preset pin)

Entries: queued contribution 08a0317e525edff0. Fixes the false 'STDERR binds the stream at init' and adds the LOG_CONSOLE_FORMAT_PRESET=short_loc pin for suites filtering CLI stderr.

Decisions: d-20261116-30e42b5c

- [x] Step 0b `skill_decisions.py show <skill> --kind rejected,removed --full` read before the first edit (no entries).
- [x] RED, quote-back probe (opus, text only) on the pre-edit text: answered 'binds at init' and found no preset pin.
- [x] GREEN, quote-back probes (opus, then haiku after closing the gaps opus named) answered from the new text.
- [x] Added lines checked: ASCII only, no history wording, description unchanged.
- [x] Deployment: the marketplace copy and the tool repo twin carry the same text (repo-gate --mirrors: in sync) and both versions are bumped.
- [x] Claims checked in source: rich_console.py _build_console (Console(stderr=True), no file), _default_preset (SHORT_LOC_ICON on win32), resolvers.py (preset read when init builds settings), shutdown drains the queue.
