# skill-writer checklist - meta-skill-writer (2026-07-31, present tense, documentation values)

Change: two authoring rules and two checklist boxes. A skill and its review artifact are written in
the present tense - not as a session log - and every address, MAC, hostname and path an author adds
is a reserved documentation value rather than one from the machine they worked on. Ships with
plugin 5.118.0.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, and it did NOT fail. Two subagents were given the pre-change skill and a scenario whose
      notes deliberately offered session narrative to copy - an operator instruction that changed
      mid-run, a scratch path, a development host. Both declined all of it and wrote clean
      artifacts unprompted; one used documentation-range addresses on its own initiative, and one
      spontaneously flagged a marketplace copy that carried real ones. Reported rather than
      massaged into a failure: the second run dropped the "this repo is public" phrasing to test
      whether that hint was doing the work, and the result held without it.
- [x] The failure the rules answer is a real one, observed on this skill's own output rather than
      in a scenario: an artifact shipped in this repo containing an operator instruction, a scratch
      path, and a paragraph of agent transcript, and a sibling skill's examples shipped a real MAC
      and two link-local addresses derived from a real machine. A rule that a fresh agent does not
      need can still be the rule that holds under a long session, which is when the lapse happened.
      Both were corrected in the same change.
- [x] GREEN: a subagent given the updated skill and an equally tempting scenario produced an
      artifact with no operator instruction, no scratch path, no host and no LAN address, and
      ticked the two new boxes explicitly - "every host, path, and pattern in the new text is a
      placeholder, not a value from any real machine".
- [x] The rules carry their own test, so a reader can apply them without judgement: a reserved-range
      table (RFC 5737, 3849, 7042, 2606) and a grep the checklist names, plus a read-it-back
      question - what does a reader DO differently knowing this line?
- [x] Vendored upstream documentation is exempted explicitly. A skill that mirrors another
      project's docs keeps their examples; rewriting them would make the copy disagree with its
      source, and an audit of this marketplace found exactly that case.
- [x] Scope: universal authoring rule, so it belongs here rather than in the repo's CONTRIBUTING -
      it holds for a standalone skill on one machine as much as for a published one.
- [x] Security scan: the Bad example contains an address and a path by construction, both
      documentation-range and both labelled as what not to write. ASCII only.
- [x] CSO description unchanged; the rules are body content, not a new triggering condition.
- [x] Token budget: hub skill, already over the process-skill guidance by design; the addition is
      one table and two short sections.
