# skill-writer checklist - meta-context-watcher (2026-10-26, a stand-in before "blocked")

One paragraph is added after "classify EVERY open line": a recorded "no X available" is re-tested
against disposable stand-ins (container, throwaway VM, network namespace or router container,
size-capped tmpfs, a CI runner of the platform) before a line goes into blocked; a stand-in that
needs a user-only thing leaves the line blocked on that named thing; only hardware no reachable
machine has stays blocked as recorded.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: discipline/reference; the test is application - classify five backlog lines
      whose `open:` fields each say "no X available", three of them emulable from the machine
      facts, one needing a user-only input, one real hardware.
- [x] Inherited coverage: `redcheck --corpus-cascade` reported STRONG by term overlap. Opening the
      named documents, none states the lesson; one memory pointer at a project level covers only
      network probes ("rather than calling the item blocked"), so the scenario uses a different
      domain (database version, packet loss, OS release, disk full, CPU architecture) and the
      packet-loss line is read as possibly contaminated. Text check of the skill file: no
      sentence about emulating or standing in for a blocker (zero hits for
      emulat/throwaway/disposable/stand in).
- [x] RED (haiku and opus, `bitranox:baseline-probe`, pre-change paragraphs pasted): both found
      container stand-ins for the database and disk lines on their own judgement, and both still
      classed the OS-release line "BLOCKED on the user" while naming a VM on the cluster as the
      route. opus named the gap: "It never says to test each recorded blocker against the current
      machine... Read literally, all five lines say 'blocked'."
- [x] GREEN (haiku, and opus at effort medium; edited paragraph pasted): every class decided by a
      direct quote. Database, packet-loss and disk lines workable with a named stand-in and what
      it does not reproduce; the OS-release line blocked on a named ISO, licence or go-ahead,
      quoting "leaves the line blocked on THAT thing"; the hardware line blocked as recorded,
      quoting the hardware sentence (the over-trigger control held on both tiers).
- [x] Diffed both ways: no RED result lost; the only changed class is the intended one.
- [x] GREEN gaps, each decided:
      - check whether the user-only thing already exists before asking - CLOSED: "look first for
        whether it already exists (an ISO in the cluster's ISO store, a free evaluation build)".
      - does a public image that still has to be pulled count - CLOSED: "a public image or
        download included".
      - does a stand-in run close the line - CLOSED: "A stand-in run closes only what it
        reproduces: keep a narrower line for the part it did not."
      - CI runners and emulation - CLOSED: "real hardware someone else runs, such as a CI runner
        of that platform" and "emulating it is not a stand-in".
      - the hardware sentence contradicted the CI-runner clause - CLOSED: "Only physical hardware
        under test that no reachable machine has".
      - probe a stand-in's preconditions before classifying - DECLINED: covered by "When a
        stand-in fails (a kernel module refused, an image missing), write what was tried into
        `open:`".
      - what counts as shared infrastructure; whether to try a second stand-in after a failure -
        DECLINED: judgement the text should leave open.
      - rank direction, ORIGIN, the four classes, the `open:` field - DECLINED: covered elsewhere
        in SKILL.md (the line format and "How rank is decided"); the probes saw an excerpt.
      - several user-only things in one question - DECLINED: owned by the one-decision-per-turn
        rule in the CLAUDE.md cascade.
- [x] Each closed gap verified by a haiku quote-back re-probe on the edited text (five questions,
      five direct quotes); the contradiction it reported was fixed and re-probed by a second haiku
      quote-back: emulation not a stand-in, a CI runner of the platform workable, a device only
      the user owns blocked, each by a direct quote, and "no" to any contradiction. Its one new
      gap (a device the user could hand over) is DECLINED: covered by rank rule 4, "Being blocked
      on the user is a reason to go and ask".
- [x] Tiers: RED haiku + opus; GREEN haiku + opus (effort medium); re-probes haiku x2 - 6 cells.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added; no version-history wording.
- [x] Present tense, no session narrative, no private provenance.
