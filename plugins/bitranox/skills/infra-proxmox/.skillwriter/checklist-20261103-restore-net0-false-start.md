# skill-writer checklist - infra-proxmox (2026-11-03, restored CT: net0 and a false start error)

Change: the **Restored CT as a new machine** row, the (3) item of **Fresh PVE 9 node gaps**, and
`references/restored-guest-identity.md` now say that a `--net0` given to `pct restore` is ignored
whole, its `ip=` included (only `--unique` changes the MAC), and that the first `pct start` of a
restored copy can exit 1 with `unable to get PID for CT <id> (not running?)` while the CT runs.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference (a factual claim about pct plus one procedural step). Test approach:
      application scenario, RED on the pre-edit text, GREEN on the edited text, opus and haiku.
- [x] Ground truth, measured on pve-container 6.1.16 (PVE 9.2): `pct restore ... --unique 1
      --net0 ...,ip=<new>` left net0 with the fresh MAC and the source's static `ip=`; the first
      `pct start` printed `failed to connect to monitor socket: Connection refused` and
      `unable to get PID for CT <id> (not running?)`, exit 1, while `pct status` read running.
- [x] Order: the table-row text was first drafted through a Bash script before this procedure was
      entered; the RED arms were run on `git show HEAD:` text, so they saw none of the draft.

## RED
- [x] `redcheck --corpus-cascade` named term-overlap documents only; a grep of every CLAUDE.md and
      memory fact for the claims (`unable to get PID`, `--net0` ignored) found none. Behavioural
      RED kept.
- [x] Scenario: restore with `--unique 1 --net0 ...,ip=<new>`, then the start error. Arms got the
      pre-edit row and reference, declared complete.
- [x] RED opus: expected `ip=192.0.2.19/24` ("NOT STATED ... 'the one field' hints that the other
      `--net0` fields apply too"); on the start error read the journal and would run
      `pct start --debug`; never `pct status`.
- [x] RED haiku: "I expect `ip=192.0.2.19/24` and `gw=192.0.2.1` to show, since I passed them";
      start error NOT STATED, next command `pct start 119 --debug`.

## GREEN
- [x] GREEN opus and haiku both: expect the source's `ip=`, set the whole net0 with `pct set`
      before the first start, read it back; on the start error run `pct status 119` first, quoting
      "read `pct status <id>` before acting on that error".
- [x] No command added that needed executing beyond `pct config`/`pct set`/`pct status`, all of
      which ran on the real node in the measured case.

## REFACTOR
- [x] Every RED and GREEN dispatch asked for a `Skill gaps` section; all four lists read.
- [x] Closed: where the new MAC comes from (now "read the line it left", `hwaddr=<the MAC just
      read>`); which other fields to keep (now "copy every other field from that readback").
- [x] Declined: a CT that is already running on the source's address (the reference puts the net0
      fix before the first start, so following it prevents that state); the CT really stopped after
      the error (generic start debugging, out of scope for an identity checklist); behaviour on
      other pve-container versions (the measured version is named in the text); "hostname, two
      readings" (checklist item 4 covers the rootfs `/etc/hostname` check); whether an `hwaddr=`
      inside a restore `--net0` is ignored separately (not measured; the text claims only the whole
      `--net0`).
- [x] GREEN diffed against RED in both directions: every RED item (identity checklist steps,
      read-back) is still present in GREEN; nothing lost.
- [x] Quote-back on the final text, opus (effort medium) and haiku: "Does the restored CT get that
      ip?" quoted "a `--net0` given to it does not, and it fails silently" on both; "where does the
      hwaddr value come from" quoted "read the line it left" / "copy every other field from that
      readback unchanged" on both. No NONE.
- [x] Final re-probe found no new undecided gap (remaining items declined above).
- [x] Tiers: opus and haiku on RED, GREEN and quote-back; 6 cells.
- [x] Width and fence check over the added lines prints nothing; paragraph after each insertion
      read (the new "first start" section sits before "Verify from ground truth" and binds no
      back-reference).

## Quality
- [x] No session narrative or private paths; examples use `<id>`, `<new>`, `<gw>`.
- [x] History finder over the diff: no hit.
- [x] Address check over the added lines: no real address.
