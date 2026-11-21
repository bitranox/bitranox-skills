# skill-writer checklist - meta-skill-writer (fix the tool, never teach overriding it)

- [x] Change: REFACTOR gains "Never write text that tells the reader to override a tool the skill
      names; fix the tool", after the quote-back paragraph that already says to fix a tool's old
      advice in the same release.
- [x] Decisions: d-20261121-1029f85a
- [x] Mechanism claim checked against the source: the promotion check's `--source user` option is
      the commit "dream_state should-promote: take the candidate's source; skills obey its word".
- [x] Not applied, already covered: "a gap closed after the GREEN probes ran is untested; re-probe
      the final text before the checklist says so" is "A gap marked closed in the review artifact
      is a claim until the probe says so: after each fix, re-run the SAME probe ... on the final
      text, and repeat after each further fix" (REFACTOR) and the checklist line "After the last
      fix, the same probe re-run on the final text found no new undecided gap".
- [x] Step 0b: `skill_decisions.py show meta-skill-writer --kind rejected,removed --full` read; no
      declined entry is re-proposed and no live rule's anchor touched.
- [x] RED as a text check, opus and haiku, on the pre-edit quote-back paragraph: both quoted only
      the neighbouring "fix it in the same release" sentence and named the gap themselves (it is
      written for a tool giving old advice, not for one missing an input; silent on the tool's
      other callers); opus said the rest came from rules outside the excerpt.
- [x] GREEN quote-back, opus and haiku, on the edited text: both quoted the new paragraph for what
      to do instead and why the override is wrong; a checker found each quote in the edited text
      and none in the pre-edit text (5 of 5).
- [x] Gap from GREEN closed and re-probed on the final text (opus and haiku, quote from the new
      text): a tool another repo owns cannot ship in the same release (closed: ship its fix first
      and the text after).
- [x] Gaps declined: a temporary override under deadline pressure (the rule admits none; the tool
      fix is the work); the flag's default and the other callers passing it (covered by the next
      paragraph, "Before you ship, list every case the edit decides beyond the reported defect");
      readers on an older tool without the flag (owned by the tool's version floor, not this
      rule).
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion point ("Before you ship ...") holds no back-reference.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines (finder over the added lines: no hit), no private hosts,
      paths or personal data, ASCII only.
