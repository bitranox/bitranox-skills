# skill-writer checklist - python-network-probe (2026-10-24, banner grab)

Change: document `grab_banners` / `agrab_banners` and the `banners` subcommand (ipscout 2.1.0).
New quick-reference row, async row, subcommand grid (twenty-two), a section "Identifying a device
by what it says: one connection per host", an error-contract line for the many-host calls, an exit
code line, and two common-mistakes entries. The description gains the banner trigger and was
rewritten rather than appended to stay under the cap.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: retrieval and application scenarios, plus an over-trigger
      control.
- [x] Inherited-context check: `redcheck --corpus-cascade` named seven documents, all on generic
      shared terms (hosts, library, send, server); the top two were read and neither mentions a
      banner grab or `grab_banners`. Not inherited. Because this is an EDIT, the primary RED is a
      text check of the pre-edit file.
- [x] RED (text): the pre-edit SKILL.md has 0 matches for `banner|greeting|grab`, against 25 for
      `ping` as the control that the grep read the file.
- [x] RED (behaviour), opus + haiku, pre-edit text pasted: both answered NONE and hand-rolled
      `socket.create_connection` / `asyncio.open_connection` loops. Both reported the environment
      leaked the feature name (worktree and git log), and both still answered from the text as
      instructed, so the arms stand.
- [x] GREEN, opus + haiku, edited text pasted, four questions: both chose `grab_banners` with
      verbatim quotes, both quoted "a name that does not resolve is `UNREACHABLE`, never a raise"
      and "A refusal is reported, not retried". Over-trigger control (port 443, server speaks
      second): both chose `scan_ports`, not `grab_banners`. Cells: 2 tiers x 4 questions.
- [x] GREEN gap that was a real defect: the example filtered `startswith("220")`, which matches
      every FTP server. Fixed in SKILL.md and docs/usage.md to match the device-naming part,
      with a sentence saying why.
- [x] GREEN gaps closed: the `state` attribute is named; decoding (UTF-8, U+FFFD); no privilege
      needed; host strings, not a network (with the `ipaddress` expansion in the example);
      farewell closes without waiting; which arguments raise `ValueError`; `PortState.OPEN`
      named (a gap both arms hit in the older common-mistakes text); `RuntimeError` named for the
      in-loop refusal; `error` and `line` are `None` outside their state; long line cut at the cap
      and still `GREETED`; repeated host strings collapse, keyed as given.
- [x] Gaps declined, with reason:
      - `scan_ports` timeout/concurrency/defaults not listed: the skill points at `--help` and
        `ipscout.__all__` and keeps flag lists out on purpose ("do not trust a flag list copied
        into any document").
      - Retry timing for a device's reconnect window: device-specific; the text says to retry
        yourself.
      - Whitespace-only greeting (`line == ""`): still `GREETED`, so the stated test equivalence
        holds; exotic.
      - A multi-byte character split at the byte cap: follows from "cut there" plus replacement
        decoding; exotic.
      - A CIDR string passed straight to `grab_banners`: the text says to expand it first.
      - "Twenty-two subcommands, one per capability above" while the quick reference omits some
        CLI-only rows: pre-existing wording, the grid itself is complete.
- [x] Quote-back after each fix round, opus (effort medium) + haiku: every touched question
      answered with a verbatim quote. The `None`-otherwise and keyed-as-given wording was added
      after a haiku arm answered `error` on REFUSED only by inference, and the dedup sentence was
      rewritten after both arms asked whether matching folds case and which position a repeat
      keeps.
- [x] Final run, haiku, final text: for `["printer.example", "192.0.2.7", "PRINTER.example",
      "printer.example"]` it answered "3 entries, in the order "printer.example", "192.0.2.7",
      "PRINTER.example" ... One connection goes to "printer.example"", quoting "Every distinct host
      STRING gets one entry, keyed exactly as given (case included, nothing resolved or folded), at
      the position of its first occurrence; a repeat is grabbed once." Its remaining gaps (whether
      two spellings reach one machine, an IP literal counting as a host string) follow from the
      no-folding wording and are declined; no undecided gap remains.
- [x] Every code block executed against the real library: the banner example ran verbatim
      (network and port swapped for a loopback greeter), found the greeter, sent `QUIT\r\n` on
      the same connection, and reported an unrouted host `UNREACHABLE`. `RuntimeError` for all
      three sync calls inside a loop, `PortState.OPEN` and the dict return of `scan_ports` were
      each checked by running them.
- [x] Description measured with `len()`: 988 (cap 1024). Rewritten, not appended; the only routing
      keyword the rewrite dropped ("permanent") was restored.
- [x] Version-history finder over the skill dir: no hits.
- [x] Values added are documentation values (`192.0.2.0/24`, `printer.example`); the remaining
      `192.168.1.x` lines predate this change.
- [x] No secrets, hosts, private paths or PII in the change.
- [x] Kept identical to the copy mirrored into the bitranox-skills marketplace, apart from that
      copy's name prefix.
