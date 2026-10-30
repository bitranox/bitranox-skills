# skill-writer checklist - compuse-toolbox (procsig --peer)

Entry covered: a `procsig` option that lists the local processes holding a TCP connection to a
peer, with the owning Claude session, instead of a hand-rolled `ss -tnp | grep` plus ppid walk.

- [x] Change: `scripts/procsig.py` gains `--peer HOST[:PORT]` (list only, `--kill` refused) and
      the jig table row for `procsig` names it, its output and its exit codes.
- [x] TDD: 23 new tests in `tests/test_procsig.py` failed first (`23 failed, 60 deselected`),
      then `83 passed`; one test opens a real loopback connection and finds its own pid through
      the live `/proc/net/tcp`, so the address decoding is checked against the kernel, not only a
      fixture.
- [x] Live run: `--peer 127.0.0.1` listed real holders (exit 0); `--peer 192.0.2.1:9` printed
      `no holder: ...` (exit 1); `--peer bad:port` exited 2 naming the bad port.
- [x] Whole skill test dir: 2687 passed, 19 skipped.
- [x] RED: the opus no-text arm hand-rolled `ss -tnpH` plus a ppid walk (the shape the option
      replaces); text check `--peer` HEAD 0 now 1.
- [x] GREEN (opus and haiku, row pasted): both ran `uv run scripts/procsig.py --peer
      192.0.2.52:9100` and quoted the row's exit-code clause.
- [x] Skill gaps decided: what exit 2 means and how to tell its causes apart (closed: the row
      says stderr names which and to run as root for another user's process; re-probed on haiku,
      quoted back); the relative `scripts/` path (declined: inside this skill the announced base
      directory resolves it, as for every other row of the same table).
- [x] Description unchanged (997 chars measured with len(), under the 1024 cap); table canonical;
      ASCII only in added lines; no private names.
