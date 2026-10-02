# skill-writer checklist - ai-llm-jev-judge (2026-10-02, new mirror of jev-judge 0.2.4)

Source: the `jev-judge` skill of `bitranox/btx-skill-jev-judge` (`skills/jev-judge/SKILL.md`, package
and skill 0.2.4). This copy differs from the twin only in the by-convention `name:` field; the H1
carries no parenthetical, so it stays `# jev-judge` as in the twin.

- [x] Skill type: technique (a procedure for delegating a repeated bounded judgment to a CLI).
- [x] Name `ai-llm-jev-judge`: category `ai`, sub `llm` ("LLM APIs" in `skill-taxonomy.json`); the
      registry's tie-break prefers the specific tech domain over the generic `compuse` bucket.
- [x] Inherited-context check: the `jev-judge` skill itself is installed on this machine as a
      separate plugin, so a behavioural RED here would answer from the installed text in both arms.
      Route taken: a text check of the artifact. The copy is byte-identical to the twin outside the
      `name:` line (`repo-gate.py --mirrors`: 0 of 11 pairs drifted), and the twin's own RED/GREEN
      record for this exact text is its `docs/skill-review.md`, section "Re-check for the summarize
      data (0.2.4)", with every command executed against the published package.
- [x] Description measured with `len()`: 425 characters, starts "Use when", third person, no
      workflow summary.
- [x] Router firing rate measured before shipping: replaying `skill-router.match` over 1,814 typed
      prompts from the transcript corpus, the new triggers reach MIN_HITS on 10 prompts and land in
      the nudged top two on 8 (other skills: median 3, maximum 17, 53 skills nudged at least once).
      All 10 are false positives on head words (`items`, `same`, `work`, `many`); none asks for a
      many-item judgment. DECLINED for now: the description is shared with the twin, so a reworded
      head is a twin release first, and 8 in 1,814 is inside the range the shipped skills already have.
- [x] No address, MAC, hostname or private path in the copy; the only URLs are the TypeSafe console
      and docs.
- [x] No bundled scripts (the skill calls the published CLI through `uvx`), so no `tests/` dir.
- [x] Derived artifacts regenerated: `docs/skills.md`, `hooks/skill_triggers.json`, README count 82.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] No session narrative or private provenance added.
