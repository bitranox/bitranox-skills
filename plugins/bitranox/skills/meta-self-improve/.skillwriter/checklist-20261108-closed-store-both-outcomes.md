# skill-writer checklist - meta-self-improve (2026-11-08, the closed store holds both outcomes)

Step 3b's contribution paragraph gains, after "A delivered contribution recorded as rejected
tells every later reader the work was not done.": count closed entries with
`contrib_queue.py shipped` or `rejected`, never by the lines of `<hash>.contrib-rejected.jsonl`,
which holds every closed entry; `ship` writes outcome `shipped`, `drop` writes `rejected`, and
`rejected` lists every record whose outcome is not `shipped`. The same warning goes into
`references/upstream-propagation.md`, the `contrib_queue.py` module docstring and its `rejected`
help line, and the `rejected_file` docstring in `hooks/self_improve_signals.py` records why the
file is not renamed. Description unchanged.

Decisions: d-20261108-3dbc6b9f

- [x] Step 0b `show meta-self-improve --kind rejected,removed --full`: one entry
      (d-20261106-4cb9268c, name-based misplacement signal), unrelated.
- [x] RED, text check: before the edit no SKILL.md or reference file named
      `contrib-rejected` (grep over `plugins/**/*.md`: no hit), so nothing warned a reader that
      the file holds shipped records too. The queue entry records the miss it caused: a line
      count put into a user decision question as declined proposals, retracted.
- [x] Claims executed against the live queue `queue_key:b76cc15ac35f308a`: the file holds 193
      records, `outcome` 168 `shipped` and 25 `rejected`; `contrib_queue.py rejected` printed
      "25 dropped contribution(s)", `shipped` printed "168 shipped contribution(s)".
      `self_improve_signals.py`: `drop` closes with `REJECTED = "rejected"`, `read_rejected`
      keeps every record whose outcome is not `shipped`. `--help` shows the new `rejected` line.
- [x] Rename declined: every installed plugin version reads `rejected_file`'s path, so a session
      on an older version would find no closed set and let a dream re-queue closed entries. The
      reason sits in the `rejected_file` docstring and the ledger entry's why.
- [x] GREEN (opus x1, haiku x1, edited passage pasted; scenario B, counting OPEN entries, was the
      control). Both refused to put 193 into the question and ran `contrib_queue.py rejected`
      first; opus also cross-checked with `shipped`. Both said the passage does not cover open
      entries (the control stayed out of scope).
- [x] Gaps from GREEN, decided:
  - CLOSED: which outcome value `drop` writes (opus and haiku) - now "`ship` writes `shipped`,
    `drop` writes `rejected`".
  - DECLINED, covered elsewhere: the open-entry count (`contrib_queue.py list`, module docstring
    and step 3b's "Listing and closing stay CLI-only"), queue addressing (`queues` and
    `queue_key:<hash>`, upstream-propagation.md), the file's directory
    (`~/.claude/self-improve-audit/`, upstream-propagation.md); all were cut from the excerpt.
  - DECLINED, judgement: splitting disproven from stale drops for a revisit question - the
    `--reason` each `rejected` line prints carries it.
  - DECLINED, by design: the file keeps its misleading name (see the rename bullet).
- [x] Width check over the added lines: longest 99 columns; no non-ASCII.
