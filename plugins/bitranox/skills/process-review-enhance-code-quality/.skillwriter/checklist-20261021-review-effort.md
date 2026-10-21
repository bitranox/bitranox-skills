# skill-writer checklist - process-review-enhance-code-quality (2026-10-21, review effort)

- [x] Change: Step 3: each per-rubric-dimension subagent runs on `opus` at effort `medium` (review
      dispatch, see bitranox:process-agents-subagent-driven-development "Review dispatches"); the
      synthesis pass is named final synthesis whose effort is the "Final synthesis" row of the
      effort table in bitranox:process-agents-subagent-driven-development, never `medium`. Step 5's
      respect-or-reconsider dispatch pins `opus` at effort `medium`; the Common Mistakes row says
      the same at the same column width (row length unchanged).
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded bitranox:meta-skill-writer through the Skill tool before its first edit.
- [x] Skill type: dispatch-parameter rule; test approach: quote-back application probe on the
      excerpt, both tiers (text check of the artifact, so inherited context cannot supply the
      values).
- [x] RED (pre-edit HEAD excerpt, bitranox:baseline-probe, text only, Skill gaps requested), haiku
      and opus, question "Your skill tells you to dispatch <the site's reviewer>. Which model and
      effort do you pass? Quote the line." (site D): opus quoted, effort NONE for both dispatches
      (both tiers).
- [x] GREEN (post-edit excerpt, same question), haiku and opus: opus and effort medium, each with an
      exact quote; every quote substring-checked against the skill's files (whitespace and
      blockquote markers normalised), 0 missing.
- [x] GREEN diffed against RED both ways: every RED model answer is still given in GREEN; nothing
      the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus; tiers haiku and opus, one cell per
      question per tier.
- [x] Gaps closed or declined: closed - GREEN reported the synthesis pass's effort unstated; the
      text now points at the "Final synthesis" row and rules out `medium` (re-probed on haiku and
      opus, both quoted the pointer); declined - restating that row's value here (the effort table
      is single-sourced in its owning skill); declined - what "known-capable" means for inline
      re-assessment (pre-existing wording, not about dispatch values).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; ASCII only; no
      provenance or dates in the skill text.
