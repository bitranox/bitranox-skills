# skill-writer checklist - coding-resilience (2026-11-08, answers from untrusted peers)

Patterns gains a bullet after "Health-check, evict, replace": answers from untrusted peers can
choose a value, never stop, ban or discard. Rule 1, a first-contact value comes from two
independent paths that agree, and one no two agree on ends the run as a plain failure. Rule 2,
no permanent shared ban on an answer the origin could have produced; ban only a peer whose own
TCP connection was refused, failed or timed out. Rule 3, agreement never builds a hard stop or a
refusal of saved progress; a resumed job trusts its verified record, and "disagree" means
disagreeing with the record. Common mistakes gains one row. Description unchanged (it already
names pool eviction and proxies).

Decisions: d-20261108-b666e522, d-20261108-eed5ca64, d-20261108-6a36e556

- [x] Step 0b `show coding-resilience --kind rejected,removed --full`: nothing.
- [x] RED, text check: the pre-edit skill held no rule on peer agreement, ban lists or a resume
      record (grep for agree, ban, manifest, first reply: only the generic "Health-check, evict,
      replace" bullet). net-rotating-proxies states the fetch-specific forms; this is the general
      principle the queue entries ask for.
- [x] Measured figures carried from the entries' recorded runs (6 of 6 and 4 of 4 bans, 3 of 3
      stopped runs); rule 1 is argued (plan self-review) and its ledger entry says so.
- [x] GREEN (opus x1, haiku x1; Q4, a database pool member with timeouts, was the control). Both:
      kept the first HEAD reply provisional and asked a second path; banned only the
      TCP-refusing proxy and evicted the 404 one for the run; resumed on the manifest and evicted
      the outvoting proxies without banning; called the control out of scope.
- [x] Gaps from GREEN, decided:
  - CLOSED: first-contact answers that disagree with no record yet (opus, haiku) - "ask further
    paths; a value no two paths agree on is not chosen".
  - CLOSED: "disagree" on resume read against a majority (opus) - "disagreeing with the RECORD,
    however many peers outvote it".
  - CLOSED: "CONNECT refused with a status" against "connect refused" (opus) - "the TCP
    connection to the peer itself ... A peer that answers with a status, even one refusing
    CONNECT, did answer".
  - CLOSED: what detects a real change (opus) - "shows up in the trusted check (the hash no
    longer matches)".
  - CLOSED after re-probe: start-over advice against "never tell the user to delete saved
    progress" (haiku) - "right here because a trusted check failed, never because peers
    outvoted the record".
  - DECLINED, judgement: what makes two paths independent, how many further paths to ask.
  - DECLINED, owned by net-rotating-proxies: ban thresholds and expiry, bad.txt lifetime,
    eviction scope across concurrent jobs, the failure message's format.
- [x] Re-probe on the final text (haiku): sizes 100/200/300 chose nothing and named the answers;
      a CONNECT 403 was not banned, a TCP timeout was; four outvoting proxies were evicted on
      resume; a hash mismatch ended as a plain failure naming the grouped answers.
- [x] Width check over the added lines: prose at most 99 columns; the table row matches the
      existing row length (built with `zip(strict=True)`, one inserted line); no non-ASCII.
