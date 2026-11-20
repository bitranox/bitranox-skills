# checklist - kill only the tmux sessions you created

One queued contribution (a deep dream cut the source fact to a pointer, so the rule needed a home
here): name every session, end it with `kill-session -t <name>`, confirm with `has-session`,
never `kill-server` or another session's name, because one tmux server serves every process of
the user on the host.

Decisions: d-20261120-49078c56

## RED

- [x] Skill decisions read first: three rejected rows (grep shim, BSD grep, awk END), unrelated.
- [x] Text check of the pre-edit file: `kill-server` 0 hits, `kill-session` 0 hits; the tmux
      section started a named session but never said how to end it.

## GREEN

- [x] Quote-back probe (opus, haiku): T1 answered with the new paragraph's lines.

## REFACTOR

- [x] Closed (opus, haiku): no check that the session is gone; `has-session` added.
- [x] Declined (opus): private sockets (`-L`/`-S`, `TMUX_TMPDIR`) - the section uses the default
      socket throughout.
- [x] ARGUED, not measured here: one server per user via `/tmp/tmux-<uid>/default` is tmux's
      documented default.
- [x] Width, fence and ASCII checks on the added lines clean.
