# checklist - backgrounding a `cd DIR && CMD &` list over ssh

The "Backgrounding a remote command" row now says the session can also hang until the process
exits, and that the redirections must bind to what `&` backgrounds: in
`cd DIR && nohup CMD >log 2>&1 </dev/null &` the `&` backgrounds the whole list as a subshell that
keeps ssh's stdout open. It gives two fixes, a brace group and a redirected subshell.

Decisions: d-20261121-33806e7d

## Premise check (every command the row adds was executed)

- [x] Over ssh to a host whose login shell is bash, payload `sleep 4`, output to `/dev/null`:
      `cd /tmp && nohup sleep 4 ... & echo started` returned after 4153 ms (rc 0, a hang, not 255);
      `cd /tmp && { setsid sleep 4 ... & }; echo started` 134 ms;
      `(cd /tmp && exec sleep 4) ... & echo started` 135 ms; control `sleep 4 ... & echo started`
      139 ms. Locally through a pipe, bash held it 4 s and dash returned at once.
- [x] `redcheck --corpus-cascade`: one STRONG hit, opened and read: it is about harness
      `run_in_background` tasks and orphaned waiters, not an and-list holding ssh's stdout. False
      positive by term overlap; the behavioural RED stands.

## RED (pre-edit row, opus and haiku)

- [x] Both tiers reasoned the hang themselves (opus unsure whether bash exec-optimises the last
      command). Both listed the row as silent on the and-list shape, and opus flagged that the row
      names exit 255 where the shape hangs.

## GREEN (edited row, opus and haiku)

- [x] Both tiers answered "hangs until poll.sh exits", quoted the and-list sentence and wrote one of
      the two stated fixes adapted to the poller.

## REFACTOR

- [x] Table re-formatted with `reformat_tables.py`; only the edited row changed.
- [x] ASCII scan and history-phrase finder over the added text: no hits.
- [x] Gap declined: "`echo started` prints even when ssh hangs; how to confirm the job started" -
      covered by the row "Check/kill a remote process by name" (SKILL.md line 12).
