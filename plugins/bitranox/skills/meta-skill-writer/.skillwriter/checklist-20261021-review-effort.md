# skill-writer checklist - meta-skill-writer (2026-10-21, review effort)

- [x] Change: "Verify each fix by quote-back" adds: dispatch the quote-back as an `opus` subagent at
      effort `medium` (review dispatch, see bitranox:process-agents-subagent-driven-development
      "Review dispatches"); the `haiku` re-run under "A pass gets the same re-run as a failure" is a
      probe arm and passes no `effort` field. The two "Using Agent Teams" Task examples and the
      GREEN "How to dispatch a verification test" example gain `model="opus"` / `model: "opus"`
      (they carried no model, against the skill's own pin-a-tier rule); RED/GREEN probe arms take no
      effort field.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded bitranox:meta-skill-writer through the Skill tool before its first edit.
- [x] Skill type: dispatch-parameter rule; test approach: quote-back application probe on the
      excerpt, both tiers (text check of the artifact, so inherited context cannot supply the
      values).
- [x] RED (pre-edit HEAD excerpt, bitranox:baseline-probe, text only, Skill gaps requested), haiku
      and opus, question "Your skill tells you to dispatch <the site's reviewer>. Which model and
      effort do you pass? Quote the line." (site O): model NONE, effort NONE (both tiers); the RED
      reported the excerpt does not say a dispatch runs the check.
- [x] GREEN (post-edit excerpt, same question), haiku and opus: opus and effort medium, each with an
      exact quote; every quote substring-checked against the skill's files (whitespace and
      blockquote markers normalised), 0 missing.
- [x] GREEN diffed against RED both ways: every RED model answer is still given in GREEN; nothing
      the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus; tiers haiku and opus, one cell per
      question per tier.
- [x] Gaps closed or declined: closed - GREEN asked what effort the haiku probe arm passes; the text
      now says it passes no `effort` field (re-probed on haiku and opus, both quoted it); declined -
      restating the probe tier pairs (owned by the haiku re-run paragraph).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; ASCII only; no
      provenance or dates in the skill text.
