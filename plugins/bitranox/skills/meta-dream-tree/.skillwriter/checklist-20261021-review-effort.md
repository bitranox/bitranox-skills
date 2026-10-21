# skill-writer checklist - meta-dream-tree (2026-10-21, review effort)

- [x] Change: Step 3b names the loss-finding pass's skeptics as `opus` subagents at effort `medium`;
      references/dream-core.md "Give each skeptic" gains "(each an `opus` subagent at effort
      `medium`, review dispatch, see ...)"; that paragraph reflowed with mdwrap.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded bitranox:meta-skill-writer through the Skill tool before its first edit.
- [x] Skill type: dispatch-parameter rule; test approach: quote-back application probe on the
      excerpt, both tiers (text check of the artifact, so inherited context cannot supply the
      values).
- [x] RED (pre-edit HEAD excerpt, bitranox:baseline-probe, text only, Skill gaps requested), haiku
      and opus, question "Your skill tells you to dispatch <the site's reviewer>. Which model and
      effort do you pass? Quote the line." (site N): model NONE, effort NONE (both tiers).
- [x] GREEN (post-edit excerpt, same question), haiku and opus: opus and effort medium, each with an
      exact quote; every quote substring-checked against the skill's files (whitespace and
      blockquote markers normalised), 0 missing.
- [x] GREEN diffed against RED both ways: every RED model answer is still given in GREEN; nothing
      the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus; tiers haiku and opus, one cell per
      question per tier.
- [x] Gaps closed or declined: declined - none beyond the cited section not being in the excerpt.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; ASCII only; no
      provenance or dates in the skill text.

## Fix round (final whole-branch review)

- [x] Step 3b names the skeptics' tier with the pointer the other sites carry: "`opus` subagents at
      effort `medium`, review dispatches, see bitranox:process-agents-subagent-driven-development
      "Review dispatches"". Wording-only addition of a cross-reference; the value is unchanged, so
      the earlier probe results stand. ASCII only.
