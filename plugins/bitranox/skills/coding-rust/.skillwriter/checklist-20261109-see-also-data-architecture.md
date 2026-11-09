# skill-writer checklist - coding-rust (2026-11-09, See also: data-architecture skill)

One bullet added under `## See also`, pointing at the new `bitranox:coding-rust-data-architecture`
("data architecture: newtypes, open and closed enums, the serde boundary, zerocopy wire structs,
error types and the clippy lints that enforce them"). No other line changed.

Decisions: none - a cross-reference to the new skill; no rule changed

- [x] Receipt fresh. Step 0b: `skill_decisions.py show coding-rust --kind rejected,removed --full`
      printed nothing and exited 0 (no ledger for this skill).
- [x] Not mirrored: ships only from this marketplace.
- [x] Skill type: reference; test is retrieval. Question: "You are reviewing a Rust crate that
      deserializes untrusted JSON with serde and parses a binary wire header, and the user asks you
      to tighten its types (newtypes, enums for wire values, error types) and the clippy lints that
      enforce them. According to the skill text above ONLY, which other skill (if any) should you
      load for this? Answer with a DIRECT QUOTE of the line in the text that names it, or the
      single word NONE." Headless `claude -p --output-format stream-json`, file and shell tools
      disallowed, the skill text in the prompt; the answer is the first assistant text block.
- [x] RED (pre-edit text from `git show HEAD:`), opus and haiku: both quote the
      `bitranox:coding-input-sanitization` line ("the language-agnostic rules are in
      `bitranox:coding-input-sanitization`"), the nearest match the old text offers; neither names
      a data-architecture skill.
- [x] GREEN (edited text), opus and haiku: both quote "`bitranox:coding-rust-data-architecture` -
      data architecture: newtypes, open and closed enums, the serde boundary, zerocopy wire
      structs, error types and the clippy lints that enforce them." 4 cells, 2 tiers.
- [x] Skill gaps: the retrieval prompt asks for a quote or NONE only; no gap concerns the edit.
- [x] Added lines: none over 100 columns, no fence, ASCII only. The bullet follows the existing
      performance-review bullet and nothing after it refers back.
- [x] `hooks/tests/test_rust_skill_family_text.py` pins the reference
      (`test_the_data_architecture_skill_routes_to_the_generic_and_back`); a mutation removing
      the `bitranox:` prefix from the new bullet was KILLED by that test.
