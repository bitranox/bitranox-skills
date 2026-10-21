# skill-writer checklist - process-review-receiving-code-review (2026-10-21, review effort)

- [x] Change: The EVALUATE delegate is a pinned `opus` subagent at effort `medium` (review dispatch,
      see bitranox:process-agents-subagent-driven-development "Review dispatches"); the re-reviewer
      of a fix brief is an `opus` subagent at effort `medium` with the same pointer.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded bitranox:meta-skill-writer through the Skill tool before its first edit.
- [x] Skill type: dispatch-parameter rule; test approach: quote-back application probe on the
      excerpt, both tiers (text check of the artifact, so inherited context cannot supply the
      values).
- [x] RED (pre-edit HEAD excerpt, bitranox:baseline-probe, text only, Skill gaps requested), haiku
      and opus, question "Your skill tells you to dispatch <the site's reviewer>. Which model and
      effort do you pass? Quote the line." (site E): EVALUATE delegate: opus, effort NONE;
      re-reviewer: model NONE, effort NONE (both tiers).
- [x] GREEN (post-edit excerpt, same question), haiku and opus: opus and effort medium, each with an
      exact quote; every quote substring-checked against the skill's files (whitespace and
      blockquote markers normalised), 0 missing.
- [x] GREEN diffed against RED both ways: every RED model answer is still given in GREEN; nothing
      the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus; tiers haiku and opus, one cell per
      question per tier.
- [x] Gaps closed or declined: declined - whether to dispatch at all when the session is already on
      opus (pre-existing conditional, not about dispatch values); declined - the parameter key names
      (the cited section gives the Agent-tool and Workflow spellings).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; ASCII only; no
      provenance or dates in the skill text.
