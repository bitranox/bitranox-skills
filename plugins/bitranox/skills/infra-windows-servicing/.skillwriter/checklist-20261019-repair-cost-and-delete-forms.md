# skill-writer checklist - infra-windows-servicing (2026-10-19, repair vs upgrade, delete command forms)

Change: "Batch tools abandon the whole walk" gains the exact `takeown`/`icacls`/`attrib` forms with
which part is locale-dependent, per-top-level-entry deletion, and the no-second-enumeration rule;
"Choosing the remedy" gains why a successful repair is the weaker end state, the upgrade's costs,
the image-build rule, and the caveat that a peer's WinSxS may have been pruned.

- [x] Skill type: reference - tested by quote-back (verbatim quote, or NONE).
- [x] RED (sections as they stood, opus): Q8 cost and Q9 NONE; Q6, Q7, Q10, Q11 PARTIAL; RED also
      reported a contradiction: a peer "carries the actual revisions" beside "WU covers payloads no
      local source has". The peer caveat resolves it.
- [x] GREEN (new text, opus and haiku): all six questions answered by a direct quote.
- [x] REFACTOR, from the opus GREEN gaps: "locale-safe" was wrong for `takeown /d` (the letter is
      localised) - relabelled, only the `icacls` SID form is locale-independent; `attrib /S /D` is
      itself a batch walk - added the fall-back to the per-entry loop; "never enumerate" scoped to a
      SECOND enumeration started to check progress. Haiku re-test quoted each fix.
- [x] Cost figures checked against the skill's own measurements: "about an hour" from the source
      note contradicted the "Durations" section (1 h to 5h18m), so the text says "hours" and points
      there; the Windows.old size cites the measured 7-20 GB reclaims, not an unmeasured range.
- [x] Skill gaps, declined: slipstream steps and the loop's `record` placeholder are outside these
      sections; whether one recursive enumeration is itself safe on a big tree is unmeasured, and
      the recorded hangs were second enumerations started during a running delete.
- [x] Lost-result diff: every RED quote survives in GREEN; nothing missing.
- [x] Description unchanged; tables untouched (`reformat_tables.py --check` unchanged).
- [x] Security: placeholders only; the SID is the documented well-known Administrators SID.
