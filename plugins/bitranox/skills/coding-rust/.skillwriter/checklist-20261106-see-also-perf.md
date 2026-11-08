# skill-writer checklist - coding-rust (2026-11-06, See also: performance skill)

One bullet added under `## See also`, pointing at the new `bitranox:coding-rust-performance-review`
("performance: clippy's perf lints, criterion, profilers, release-profile settings and a Rust
hot-path checklist"). No other line changed.

Decisions: none - a cross-reference to the new skill; no rule changed

- [x] Receipt fresh. Step 0b: `skill_decisions.py show coding-rust --kind rejected,removed --full`
      and `show coding-rust` printed nothing (no ledger for this skill).
- [x] Not mirrored: ships only from this marketplace.
- [x] Skill type: reference; test is retrieval. Question: "You are reviewing a Rust crate and the
      user asks you to find why a hot loop is slow and to benchmark a fix. According to the skill
      text above ONLY, which other skill (if any) should you load for Rust performance work? Answer
      with a DIRECT QUOTE of the line in the text that names it, or the single word NONE."
      Headless `claude -p`, text only, no tools; first assistant text block read from the
      stream-json output.
- [x] RED (pre-edit text from `git show HEAD:`), opus (effort medium) and haiku: both `NONE`.
      Opus: "The skill text points to three other skills: `bitranox:compuse-git`,
      `bitranox:process-review-verification-before-completion` and
      `bitranox:coding-input-sanitization`. None of them is about performance". Haiku: "The skill
      text names no skill for Rust performance work."
- [x] GREEN (edited text), opus and haiku: both quoted "`bitranox:coding-rust-performance-review`
      - performance: clippy's perf lints, criterion, profilers, release-profile settings and a Rust
      hot-path checklist." 4 cells, 2 tiers.
- [x] Skill gaps: none reported that concern the edit. The opus GREEN arm noted the named skill is
      not in its installed listing; expected, the skill ships in the same release as this bullet.
- [x] Added lines: none over 100 columns, no fence, ASCII only. The paragraph before the bullet is
      unchanged and holds no back-reference that now binds to it.
