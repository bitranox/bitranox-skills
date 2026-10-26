# skill-writer checklist - python-network-probe (2026-10-26, MAC fallback to the cache)

Change: document `lookup_mac(ip, active=True, fallback_to_cache=True)`, `MacMethod` /
`MacLookup.method`, `get_mac_address`'s matching flag and the CLI `--fallback-to-cache`. A new
quick-reference row; the "They never silently degrade" rule gains the opt-in fallback, which errors
fall back, which raise, what separates a miss from a failed send, the Windows SendARP table caveat
and the accepted zone spellings; the address-borrowing advice says a cache miss does not prove an
address free. The description is unchanged ("find a MAC address" already routes here).

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: retrieval and application scenarios, plus an over-trigger
      control.
- [x] Inherited-context check: `redcheck --corpus-cascade` named the tree-top CLAUDE.local.md and
      five facts, all on generic shared terms (active, address, fallback, method); a grep of the
      cascade and the fact store for `fallback_to_cache`, `MacMethod` and `--fallback-to-cache`
      found nothing. Not inherited. Because this is an EDIT, the primary RED is a text check.
- [x] RED (text): the pre-edit SKILL.md has 0 matches for
      `fallback_to_cache|MacMethod|fallback-to-cache`, against 5 for `lookup_mac` as the control.
- [x] RED (behaviour), opus + haiku, pre-edit MAC text pasted: both hand-rolled
      `try: lookup_mac(ip, active=True) except <unnamed>: lookup_mac(ip)`, both answered NONE for
      how the code learns which method answered, and both could not say what an unanswered active
      ask returns. Opus noted the branch's commit subject in its environment and did not rely on it.
- [x] GREEN, opus + haiku, edited text pasted, five questions: both chose
      `lookup_mac(ip, active=True, fallback_to_cache=True)` and `r.method`, both quoted "a `CACHE`
      answer with no MAC only says this host has not talked to that address, not that it is free",
      both kept an unanswered root ask as `ACTIVE` with no cache substitution, both raised on the
      typo'd zone and rejected the hand-rolled `except IPScoutError`. Over-trigger control (an
      active-only tool that must fail loudly): both chose `lookup_mac(ip, active=True)` without the
      fallback. Cells: 2 tiers x 5 questions GREEN, 2 x 1 RED.
- [x] GREEN gaps closed: which exception each trigger raises; an interface that cannot carry the
      request (falls back) against a zone naming no interface (raises); the fallback flag does not
      change the zone and host-name refusals; what a service does on a cache miss (do not borrow);
      `get_mac_address` takes the flag and its `None` cannot tell an active miss from a cache miss;
      a timeout is the miss, any other OS error the failed send, and on Windows
      `ERROR_BAD_NET_NAME` is the only status read as no reply; Windows IPv4 `SendARP` answers from
      Windows' own ARP table when it holds the address (Microsoft's SendARP remarks); an index and
      both Windows interface names are accepted as a zone.
- [x] Gaps declined, with reason:
      - Import path: every example in the skill uses `ipscout.<name>` and the quick reference lists
        the calls; the probes saw an excerpt.
      - The exception hierarchy: the error-contract section states "`except IPScoutError` catches
        every one of them".
      - CLI exit codes and output: the machine-consumers section states the exit codes; `--help` is
        the flag reference.
      - Cache freshness and a cache read that itself fails: owned by the OS cache and by
        `neighbours()`'s own contract, not this flag.
      - Example spellings of Windows interface names, case rules: decided by Windows'
        `if_nametoindex` and the adapter's own name; the text says which two namespaces count.
      - The borrowing paragraph read mid-sentence: an excerpt artifact; the full text opens it.
- [x] Quote-back after each fix round, opus (effort medium) + haiku: three rounds, every touched
      question answered with a verbatim quote of the final text. The last round asked whether a
      Windows no-reply status falls back (both: it stays an `ACTIVE` miss) and which two Windows
      names a zone accepts (both: the friendly name `local_interfaces()` reports and the
      `if_nametoindex` name). Both also asked whether `ERROR_BAD_NET_NAME` is the whole list; the
      text now says it is the only status read as no reply, which is what the code does. No
      undecided gap remains.
- [x] Every claim checked by running it: the fallback on an unprivileged host and on loopback, the
      typo'd zone, a host name, the refused combination, the routed cache fallback, a numeric zone
      resolved to its name, the send failure under root, and on a Windows VM the active answers,
      the no-route refusal, the friendly-name zone and the SendARP status values. Each new test was
      mutation-checked on the platform that runs it.
- [x] Description: unchanged, 1015 characters (cap 1024). Version-history finder over the skill
      dir: no hits.
- [x] Values added are documentation values (`192.0.2.7`, `fe80::1`); no host's own addresses.
- [x] No secrets, hosts, private paths or PII in the change.
- [x] Kept identical to the copy mirrored into the bitranox-skills marketplace, apart from that
      copy's name prefix.
