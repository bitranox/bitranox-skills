# skill-writer checklist - coding-rust-consistency (2026-11-25, new skill)

A new Rust companion to `bitranox:coding-consistency`: a table of Rust spellings that compile,
read as equivalent and return different results, three shapes that leave one place to write
(one rule function, one population function and window type, one conversion per unit), what
rustc, rustdoc and clippy report and what they do not, and the searches that feed the generic
review. No scripts.

Decisions: d-20261125-fd4283d3, d-20261125-723a4973, d-20261125-aadbbaf9, d-20261125-862ff120

- [x] Receipt fresh (armed for the session, skill-writer loaded in this agent). Step 0b before
      the first edit: `skill_decisions.py show coding-rust-consistency` reports no skill, the
      skill did not exist. After the ledger was written, `skill_decisions.py check
      coding-rust-consistency` reports 0 findings.
- [x] Not mirrored: the family is new and ships only from this marketplace.
- [x] Skill type: reference plus technique; test is application together with the generic
      skill, on the scenarios and with the probe set-up recorded in `coding-consistency`'s
      checklist of the same date.

## Commands executed (scratch crates, rustc and cargo 1.95.0, edition 2024, clippy 0.1.95)

- [x] Every row of "Same value, two results" asserted in a test and passing: `0.29 * 100.0`
      as `u64` 28 and rounded 29; 1999 ms as `as_secs()` 1, `as_secs_f64()` 1.999,
      `as_millis() / 1000` 1; `7 / 2` 3, `-7 / 2` -3, `div_euclid` -4; `40 / 100 * 95` 0 and
      `40 * 95 / 100` 38; `round` 3.0 and `round_ties_even` 2.0 on 2.5; `300_u32 as u8` 44 and
      `u8::try_from` `Err`; `contains` false and lowercased `contains` true on "Outages".
- [x] Derived ordering by declaration: with `Bronze, Gold, Silver` declared in that order
      `Tier::Silver > Tier::Gold` holds.
- [x] The three code blocks extracted from the SKILL.md into one crate: `cargo test` passes (2
      tests), `cargo clippy` is clean.
- [x] A private field only initialised warns `field ... is never read`; once a method assigns
      it the warning is gone with no reader anywhere.
- [x] `cargo doc` on a doc comment with an intra-doc link to a missing item warns `unresolved
      link`; the same name in plain backticks draws nothing. A doc example asserting a wrong
      result fails `cargo test`.
- [x] `clippy::cast_possible_truncation`, `cast_sign_loss`, `cast_precision_loss` and
      `integer_division` each accepted by name, allow by default, and each fired on lines of
      the table when switched on.
- [x] The candidate grep run on a test file with planted pairs: every planted pair listed. The
      three-stage public-item diff line run on a scratch repository: it lists a removed and a
      re-added `pub fn`, including a line that starts `-pub fn`.
- [x] Not executed: other toolchains; the text says lint groups shift and how to re-check.

## RED and GREEN (with the generic skill)

- [x] RED reviewer, small Rust scenario (11 planted): opus 11 of 11, haiku 11 of 11. The
      baseline does not fail for a reviewer.
- [x] GREEN reviewer (both skill texts): opus 11 of 11, haiku 11 of 11 in 2 of 2 runs, each
      with the pair table and a concrete input per finding.
- [x] Diff against RED: nothing found in RED is missing in GREEN. The implementer behaviour
      (an unspecified condition) was probed on the Python scenario only; the rule that closes
      it is in the generic skill.

## REFACTOR

- [x] CLOSED: the order of the two results in the last table column is stated.
- [x] CLOSED: the shape note ("The examples show the SHAPE"), carried from the Python
      companion.
- [x] CLOSED: `Tier::ALL` is a hand-kept list; the text says what that leaves blind.
- [x] DECLINED (owned by the scenario): whether "contains the word" means a substring or a
      whole word when both sides agree; the generic skill sends a spec with two readings to
      its owner.
- [x] DECLINED (covered): an added fallback that shows a default value and does not suppress
      output; the generic text says "usually SUPPRESSES", and the row is `ADDED` either way.
- [x] DECLINED (probe artifact): "could not run cargo or the searches" in a text-only run.
- [x] Width and fence check: no line over 100 columns outside the front-matter description,
      tables and the fenced grep line; every fence closed; ASCII only.

## Re-run on the final text

- [x] Reviewer haiku on the Rust scenario: 11 of 11 with the pair table.
- [x] Quote-back, opus and haiku, on the family's rules: every question answered with a direct
      quote, none NONE (counts in the generic checklist).
- [x] Tiers: opus and haiku on every probe.

## Other checks

- [x] Description: 539 characters, starts "Use when", names triggers and that the skill loads
      alongside `bitranox:coding-consistency`; parses to `['description', 'name']`.
- [x] Router replay on the regenerated trigger map: "this rust change has an as cast beside
      round() and a Duration as_secs beside as_secs_f64, check consistency" nominates this
      skill first and the generic one second.
- [x] History-phrase finder and private-name grep over the skill directory: no hit.
- [x] Body 222 lines, no supporting files; three Rust blocks of 4 to 45 lines, compiled as one
      crate.
- [x] Trigger map and catalogue regenerated and in sync (90 skills).
- [x] Text test `hooks/tests/test_consistency_skill_family_text.py` covers this skill.
