# meta-self-improve: state the two do-not-capture constraints where the author reads them

Scope: one new paragraph in step 1 "Gather candidates" (three sentences of lead-in plus two
bullets plus a closing sentence). The behaviour it documents - the write-time advisory - already
shipped in `hooks/capture_constraints.py` on this branch (a prior, separately-reviewed change);
nothing in `hooks/` changes here. This is prose only.

## What the tests showed

- [x] Pre-edit ABSENT confirmed with the files genuinely read, not assumed: `claim_check.py
      --pattern 'bare negative claim|unresolved failure written up as a procedure' --control
      'Discard task state' plugins/bitranox/skills/meta-self-improve/SKILL.md` -> ABSENT, control
      matched once (the file was read).
- [x] Post-edit PRESENT: same tool, same pattern -> PRESENT, 3 hits, all on the new paragraph.
- [x] Behavioural pressure-test not run: the source text to insert was already fixed by a
      human-reviewed task brief (with two corrections applied before writing), so this is a
      documentation-conformance change, not a new discipline rule whose phrasing needs
      pressure-testing against a subagent's rationalizations. The load-bearing check is that the
      inserted prose accurately describes the shipped hook, verified directly against
      `hooks/capture_constraints.py`'s source (see "Accuracy against the hook" below), not against
      a subagent's behaviour.

## Accuracy against the hook (read, not assumed)

- [x] `capture_constraints.py`'s own docstring states the mechanism is now advisory-only,
      version-independent: "Every hook whose NEGATIVE_RX matches gets the negative-claim advisory
      - whether a version or date sits nearby does not change that". The inserted clause "Record
      the WORKING alternative instead, or attach the version and date that make the claim
      re-testable for a later reader - that improves the fact's quality but does not suppress the
      write-time warning below, which fires on every bare negative claim regardless" matches this:
      it frames a version/date as a quality improvement for the READER, never as a way to avoid the
      warning.
- [x] The unresolved-failure bullet matches `UNRESOLVED_RX` + `_UNRESOLVED_ADVICE`'s intent (an
      unresolved failure written up as a procedure should be labelled unsolved, not presented as
      validated guidance) - no wording change needed there; only the negative-claim bullet carried
      the now-removed version/date exemption.
- [x] The closing sentence ("The engine warns on both at write time; the warning is advisory...")
      was left unchanged: it states only that the engine warns on both classes, which remains true,
      and does not itself claim an exemption.

## Scope declined

- [x] Did not touch `meta-using-bitranox-skills/SKILL.md` - explicitly out of scope per the task
      (always-loaded context; a capture-time rule there costs every session tokens).
- [x] Did not rewrite the whole passage - only the version/date clause was adjusted, per the
      correction's own instruction to change it minimally.

## Checks

- [x] Description frontmatter untouched, so the CSO lint and skill-router trigger map are
      unaffected.
- [x] No cross-skill or script references added.
- [x] No session narrative or private provenance in the skill text or this artifact.
- [x] No hostname, IP, credential, or machine-specific path introduced.
- [x] LF endings; ASCII only (scanned the changed file for codepoints above 126: zero hits).
- [x] Version bumped in `.claude-plugin/plugin.json`, 5.201.0 to 5.202.0 (MINOR: a new capability
      documented in an existing skill, matching the CHANGELOG preamble's rule), with a matching
      CHANGELOG entry. This bump and changelog entry are shared with the companion
      `meta-dream-tree` edit in the same commit; see that skill's checklist for the shared
      accounting.
- [x] `repo-gate.py --ci` passes on the full change set (see the paired commit's gate result).
