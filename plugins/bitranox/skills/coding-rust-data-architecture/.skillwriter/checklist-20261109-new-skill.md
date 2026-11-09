# skill-writer checklist - coding-rust-data-architecture (2026-11-09, new skill)

A new Rust data-architecture skill: parse at the boundary (newtypes, `TryFrom`/`FromStr`,
`Option` and `NonZero`), closed enums inside a crate and open ones at the wire (stated as a
per-type choice), invalid states unrepresentable and typestate, the serde boundary, binary and
protocol data (zerocopy, endian field types, panic-free slicing, bitfields, num_enum), errors,
construction and visibility, the lint setup (`[workspace.lints]`, priorities, `#[expect]`,
`clippy.toml`), crates with maintenance flags, and a note on what a large Rust VMM does. No
scripts. The principles and workflow stay in `bitranox:coding-data-architecture`, which the skill
tells the reader to load alongside.

Decisions: d-20261109-94ef3c56, d-20261109-c1afc908

- [x] Receipt fresh (armed for the session, skill loaded in this agent). Step 0b before the first
      edit: `show coding-rust-data-architecture --kind rejected,removed --full` exited 2 ("no
      skill"), the skill did not exist. After the ledger was written, `skill_decisions.py check
      coding-rust-data-architecture` reports 0 findings.
- [x] Not mirrored: the skill is new and ships only from this marketplace.
- [x] Skill type: technique plus reference (checklist and tool recipes); test is application,
      two review scenarios, each ending with a request for a "Skill gaps" section:
      - R1: a JSON job request from untrusted HTTP clients: `#[serde(untagged)]` target,
        `mode: String`, `Option<Option<u32>>`, `email: String` checked with `contains('@')`, a
        flattened `HashMap<String, serde_json::Value>`, `from_slice(..).unwrap()`, three bool
        parameters and a `_` match arm. "Review ... which lints (clippy or rustc, by exact
        name) ... give the fixed type definitions."
      - R2: a guest-written 16-byte header: `transmute::<u8, Opcode>`, `buf[4..8]` with
        `try_into().unwrap()`, `Box<dyn Error>` and `io::Error::other`. "Review ... how unknown
        values are handled ... lints and crates ... give the fixed code."
- [x] Probe set-up. RED: `bitranox:baseline-probe` subagents (no file or shell tools), opus and
      haiku, prompt "Text only: do not use any tools, and do not load any skill". GREEN and the
      final-text re-run: headless `claude -p --output-format stream-json`, opus and haiku, file,
      shell, web, Agent and Skill tools disallowed, the full SKILL.md in the prompt marked as the
      skill under test; the answer is the FIRST assistant text block (a later block can be a
      Stop-hook reply). The skill is not installed anywhere, so no arm could load another copy.
- [x] Inherited-coverage check: the cascade and memory index loaded into every probe hold
      `bitranox:coding-rust`'s one data rule (bundle always-paired Options) and no Rust serde,
      zerocopy or lint-setup rule; the RED arms each said they did not load `coding-rust`. The
      coverage evidence is the RED/GREEN diff below, not a no-context claim.

## Commands executed (scratch crates, rustc, cargo 1.95.0, clippy 0.1.95, edition 2024)

- [x] Every lint name in the skill, one `cargo clippy -- -W clippy::<name>` run each on an empty
      library crate: all accepted, none printed `unknown lint`. Control: `-W
      clippy::redundant_clones_typo` prints `warning[E0602]: unknown lint`. Names verified:
      fn_params_excessive_bools struct_excessive_bools option_option ref_option ref_option_ref
      from_over_into fallible_impl_from infallible_try_from manual_non_exhaustive
      exhaustive_enums exhaustive_structs wildcard_enum_match_arm
      match_wildcard_for_single_variants error_impl_error result_large_err map_err_ignore
      missing_errors_doc unwrap_used expect_used unwrap_in_result panic todo unimplemented
      indexing_slicing string_slice get_unwrap missing_panics_doc big_endian_bytes
      little_endian_bytes host_endian_bytes cast_possible_truncation cast_sign_loss
      cast_possible_wrap cast_lossless as_conversions too_many_arguments new_without_default
      must_use_candidate return_self_not_must_use double_must_use must_use_unit
      let_underscore_must_use partial_pub_fields field_scoped_visibility_modifiers
      pub_underscore_fields useless_conversion unnecessary_to_owned redundant_clone
      implicit_clone needless_pass_by_value trivially_copy_pass_by_ref
      large_types_passed_by_value unnecessary_wraps str_to_string allow_attributes
      allow_attributes_without_reason large_enum_variant enum_glob_use wildcard_imports
      undocumented_unsafe_blocks iter_over_hash_type type_complexity arithmetic_side_effects
      blanket_clippy_restriction_lints disallowed_methods disallowed_types lint_groups_priority.
      rustc lints: unsafe_code unsafe_op_in_unsafe_fn missing_docs missing_debug_implementations
      unreachable_pub unfulfilled_lint_expectations accepted; `non_exhaustive_omitted_patterns`
      prints "unknown lint ... the `non_exhaustive_omitted_patterns` lint is unstable", and the
      skill says so.
- [x] Group and default level of every name read from `cargo clippy -- -W help` and matched
      against the text (for example `result_large_err` perf/warn, `redundant_clone` nursery/allow,
      `infallible_try_from` suspicious/warn, `lint_groups_priority` correctness/deny,
      `disallowed_types` style/warn). A script cross-check of every backticked lint-shaped token
      in the final SKILL.md against that list: 71 lint names, all known.
- [x] Every code example, in full form, in one scratch crate with serde 1.0.229, serde_json
      1.0.154, thiserror 2.0.21, zerocopy 0.8.63, num_enum 0.7.4, bitflags 2.13.2, and
      `#![deny(unsafe_code)]`: `cargo test` passes. Asserted there: `Email::try_from("a")` is
      `Err`; `"dry-run".parse::<Mode>()` is `DryRun`; `WireOp::from(9)` is `Unknown(9)`; the
      open `Op(7)` hits the fallback arm; `deny_unknown_fields` on the DTO rejects `"extra"` with
      "unknown field"; `#[serde(try_from)]` reports a bad mode as the text "invalid mode"; a
      70000-byte body returns `TooLarge`, a valid one parses; `read_from_prefix` fails on 15 bytes
      and returns a 1-byte rest on 17; `split_first_chunk` fails on 2 bytes; `TryFromPrimitive`
      rejects 9, `FromPrimitive` with `catch_all` gives `Other(9)`; bitflags with `const _ = !0`
      gives `from_bits(0x80) == Some`.
- [x] serde behaviour measured: a flattened catch-all map under `deny_unknown_fields` still
      rejects `"zz"`; untagged failure text "data did not match any variant of untagged enum T"
      at line 0 column 0; internal tag plus `deny_unknown_fields` gives "unknown field `zz`,
      expected `name`" and "invalid value: integer `99999`, expected u16"; `Option<Option<u32>>`
      gives `None` for both absent and `null`; serde_json fails 129 nested arrays with "recursion
      limit exceeded at line 1 column 128" and accepts 127.
- [x] Lint behaviour measured: `wildcard_enum_match_arm` fires on a `_` arm over an own enum;
      an `#[expect(clippy::unwrap_used, reason = ..)]` with no unwrap gives "this lint
      expectation is unfulfilled"; `pedantic = "warn"` next to `must_use_candidate = "allow"` at
      the same priority errors with "lint group `pedantic` has the same priority (0) as a lint";
      `clippy.toml` `disallowed-types` / `disallowed-methods` fire on `serde_json::Value` and
      `serde_json::from_slice`, and an `#[expect(clippy::disallowed_methods, reason = ..)]` on
      the boundary function silences only that one; `max-fn-params-bools = 1` fires at two bools;
      `too-many-arguments-threshold = 3` fires at four; `allow-unwrap-in-tests` leaves test
      unwraps unflagged under `--all-targets` while a library unwrap is flagged;
      `allow-expect-in-tests` is accepted; the `let ... else` form of the zerocopy read passes
      `-W clippy::map_err_ignore` and the size check `u64::try_from(..).map_or(..)` passes
      `-W clippy::pedantic -W clippy::as_conversions`.
- [x] Cargo measured: a member with `[lints] workspace = true` plus its own `[lints.clippy]`
      entry is refused with "cannot override `workspace.lints` in `lints`"; a crate-root
      `#![warn(clippy::indexing_slicing)]` beside `workspace = true` adds the lint.
- [x] VMM claims read from that repository's own files: its `.github/copilot-instructions.md`
      trust-boundary section (never panic on untrusted input, thiserror at boundaries, anyhow
      with context, open_enum for round-tripping values, `assert!` over `debug_assert!`), its
      `[workspace.lints]` (groups at priority -2, `allow_attributes`, `option_option`,
      `fn_params_excessive_bools` warn; `too_many_arguments`, `new_without_default`,
      `type_complexity` allowed), the open_enum macro doc (a `#[repr(transparent)]` struct with
      consts) and a storage device's packet parser (fallback arm returning an
      `UnrecognizedOperation` error). The skill names no repository or path.
- [x] Not executed, marked in the text: `serde_path_to_error`, the builder crates
      (UNVERIFIED), `serde_with` (UNVERIFIED), the versioned-DTO practice (UNVERIFIED as
      published practice), fuzzing; crate versions are crates.io listings.

## RED (no skill), 4 cells

- [x] R1 opus: finds every planted defect (unwrap panic, `mode: String` as an enum, flatten plus
      `deny_unknown_fields`, untagged errors, `Option<Option>` "Some(None) can never come from a
      request", bool parameters, the `_` arm, a body cap, the 128 recursion limit); lints in a
      crate `[lints]` table with `pedantic` at priority -1; an `#[expect(clippy::disallowed_methods,
      reason = ..)]`; `clippy.toml` bans on `serde_json::Value` and `from_slice`. MISSING:
      `[workspace.lints]`; a DTO separate from the domain type (the fields stay `pub`, validated
      in place). Skill gaps: lint names and the `max-fn-params-bools` comparison "did not verify".
- [x] R1 haiku: the same defects; claims `Some(None)` "means `null`", which is false (measured:
      `null` gives the outer `None`); uses `#[allow(clippy::disallowed_methods)]`, not
      `#[expect]`. MISSING: `[workspace.lints]`, `#[expect]` with a reason, DTO separation.
      Skill gaps: "Several clippy group memberships ... are from memory".
- [x] R2 opus: transmute UB, a one-time snapshot of guest memory, indexing panics, `first_chunk`,
      bitflags `from_bits`, reserved bytes must be zero, `checked_add`, a `thiserror` enum,
      private fields; zerocopy with `little_endian::U32` "from memory"; open_enum "if I recall
      correctly". MISSING: `[workspace.lints]` and group priority; `#[expect]`; the open-versus-
      closed choice ("Unsettled ... whether the device needs unknown opcodes to stay
      representable" - it chose rejection). Skill gaps: "every lint name above" unverified.
- [x] R2 haiku: transmute UB, panics, `thiserror`, num_enum, zerocopy `TryFromBytes`, bitflags,
      fail closed, `arithmetic_side_effects`. MISSING: endian field types, the panic-free std
      slice APIs, the open-versus-closed choice, `#[expect]` (uses `#[allow(unsafe_code)]`),
      `[workspace.lints]` and groups. Quote: "The lint names come from memory and were not
      checked against a toolchain."
- [x] RED verdict: the defect findings are strong on both tiers; what fails is the Rust mechanism
      layer: no arm uses `[workspace.lints]`, the haiku arms exempt with `#[allow]`, no arm
      states the open-versus-closed wire choice, three of four arms put validation in the field
      types without a DTO, haiku R1 states a false serde fact, haiku R2 misses endian field
      types, and all four say their lint names are unverified.

## GREEN (this SKILL.md pasted), 4 cells

- [x] R1 opus: a private `JobDto` with `deny_unknown_fields` and a tagged `TargetDto`, built into
      the domain type by `TryFrom`; "A missing field and `null` both give the outer `None`";
      `[workspace.lints.clippy]` with `pedantic = { level = "warn", priority = -1 }`;
      `#[expect(clippy::disallowed_methods, reason = "the one decode site; the size cap runs
      first")]`. PASS.
- [x] R1 haiku: "The wire DTOs are private and carry no invariants. The domain types are built
      only through `TryFrom`"; "serde decodes both a missing field and `null` to the outer
      `None`"; `[workspace.lints.clippy]` with priority -1; `#[expect(clippy::disallowed_methods,
      reason = ..)]`; `max-fn-params-bools = 2`. PASS.
- [x] R2 opus: zerocopy `RawHeader` with `little_endian::{U32, U64}`, rejection of the
      action-driving opcode "with a typed error that keeps the raw byte" (the skill's choice
      applied), `[workspace.lints]` with priority, `little_endian_bytes` and the other endian
      lints. PASS.
- [x] R2 haiku: zerocopy with `little_endian::U32`, `[workspace.lints]` with priority -1,
      `allow_attributes` plus `#[expect]` for remaining unsafe, `clippy.toml` with
      `allow-unwrap-in-tests`. PASS.
- [x] Diff against RED, both directions. Gained: `[workspace.lints]` (0 of 4 RED, 4 of 4
      GREEN), `#[expect]` over `#[allow]` (1 of 4 RED, 4 of 4 GREEN), a separate DTO (0 of 2 RED
      R1, 2 of 2 GREEN R1), the correct `Option<Option>` fact (1 of 2 RED R1, 2 of 2), endian
      field types for haiku R2. Lost: the CR/LF mail-header injection point (2 of 2 RED R1, 0 of
      2 GREEN R1), SSRF (R1 haiku), fuzz or Miri testing (4 of 4 RED, 1 of 4 GREEN), and
      `checked_add` on `offset + len` (R2 haiku). Each was closed in REFACTOR below and
      re-probed.

## REFACTOR

- [x] CLOSED (lost results): a sentence in "Parse at the boundary" that what a value must
      satisfy (CR or LF in an address, a private connect target, a retry count) is
      `bitranox:coding-input-sanitization`'s question, checked in the same constructor; a bullet
      "Arithmetic on wire values is checked" with `arithmetic_side_effects`; a fuzz-target
      sentence in "Errors". Final re-run: R1 haiku names the CR/LF and private-address cases and
      a fuzz target, R2 haiku has `checked_add`.
- [x] CLOSED: the zerocopy example used `.map_err(|_| ...)`, which trips `map_err_ignore`, a lint
      the skill lists (GREEN R2 opus and haiku). Now `let Ok(..) = .. else { return Err(..) }`,
      measured clean under `-W clippy::map_err_ignore`.
- [x] CLOSED: `RawHeader` mixed `pub` and private fields, which `partial_pub_fields` forbids
      (GREEN R2 opus). All fields private; the text says the raw struct stays in the parsing
      module.
- [x] CLOSED: the body-size example used `buf.len() as u64`, against the skill's own
      `as_conversions` rule. Now `u64::try_from(buf.len()).map_or(true, |n| n > MAX_BODY)` and
      the boundary function carries the `#[expect(clippy::disallowed_methods, ..)]`, both measured.
- [x] CLOSED: copying memory the other side can still write (all four RED/GREEN R2 arms raised
      it): a bullet says copy once through the memory layer's routine, then parse the copy; HOW
      that layer reads is stated as outside the skill (DECLINED for the volatile/atomic detail,
      out of scope).
- [x] CLOSED: reserved fields (GREEN R2 opus and haiku): a bullet to reject must-be-zero values
      or preserve and write back, never ignore.
- [x] CLOSED: flag policy (GREEN R2 opus): the bitflags bullet now takes the same keep-or-reject
      choice as unknown codes.
- [x] CLOSED: per-crate restriction lints beside `workspace = true` (GREEN R2 opus): measured
      Cargo refusal plus the crate-root attribute route, in "Lint setup".
- [x] CLOSED: `#[serde(try_from)]` loses the typed error (GREEN R1 opus): measured ("invalid
      mode" arrives as text) and stated, with the two-step decode as the alternative.
- [x] CLOSED: the default external tag (GREEN R1 opus): the untagged bullet names it.
- [x] CLOSED: "do not leak a dependency's error" read as contradicting `BodyError::Parse` (GREEN
      R1 opus): the rule now says it is for a published library's public variants.
- [x] CLOSED: the sample lint table omitted `expect_used` and `panic` (GREEN R1 opus): added.
- [x] CLOSED: `deny_unknown_fields` on an internally tagged enum (GREEN R1 haiku, unsure):
      measured and stated.
- [x] CLOSED: `unsafe_code` versus zerocopy derives (GREEN R2 opus): measured, the derives compile
      under `#![deny(unsafe_code)]`, stated.
- [x] CLOSED: `allow-expect-in-tests` (GREEN R1 opus, from memory): accepted by clippy 0.1.95,
      added to the `clippy.toml` sample.
- [x] CLOSED: the `Email` example's `contains('@')` reads as an endorsement (GREEN R1 opus): the
      text says it only shows the shape.
- [x] DECLINED (judgement): a CI grep against `serde(untagged)` (GREEN R1 opus); the skill says
      to pin the serde attributes with tests, and a grep is a house choice.
- [x] DECLINED (not claimed): `option_option` with `avoid-breaking-exported-api`, and whether
      `disallowed-methods` resolves zerocopy trait-method paths; the skill states neither.
- [x] DECLINED (owned by the scenario): protocol values (`MAX`, flag meanings, the job-store
      semantics of `current_status`) that every arm had to guess; they are not in the snippet.
- [x] DECLINED (covered): "no rule for a guest-written opcode" (GREEN R2 haiku). The text says
      rejection is "Fine for a value that drives an action", and the arm's choice matches it.
- [x] Width and fence check over every added line: none over 100 columns outside the
      front-matter description, every fence closed, ASCII only. The paragraph after each
      insertion point re-read: the new bullets after the zerocopy note are followed by the
      slice-API bullet, which does not refer back.
- [x] Anchors of d-20261109-94ef3c56 and d-20261109-c1afc908 unchanged; `skill_decisions.py
      check` 0 findings after the REFACTOR edits.

## Re-run on the final text (same prompts), 4 cells, then a quote-back

- [x] R1 opus: private DTOs with `deny_unknown_fields`, `[workspace.lints]`, `#[expect]`, the
      CR/LF and private-address checks ("`bitranox:coding-input-sanitization`'s question") and a
      fuzz target back. PASS. New gaps: CI failing on `warn` levels (CLOSED: "The levels are
      `warn`; CI fails on them with `cargo clippy --all-targets -- -D warnings`"); whether a
      fieldless enum may derive `Deserialize` (CLOSED, measured); `deny_unknown_fields` for an
      own API called by untrusted clients (CLOSED: "requests to an API whose format you define,
      whoever sends them"). DECLINED (judgement): a test shape for the serde pins, the unit of
      "one error type per unit of fallibility", the `untagged` small-shape exception for string
      versus object. DECLINED (out of scope): a status used as an error channel and the
      check-then-act race on `current_status` (no data-architecture rule; the scenario's own
      bug). DECLINED (covered): `read_job` parsing straight into the domain type versus the
      two-step decode; the text states when each applies ("when a caller must `match` on it").
- [x] R1 haiku: DTOs, `[workspace.lints]`, `#[expect]`, CR/LF, private addresses and a fuzz
      target. PASS. Gaps are scenario values (limits, `current_status`, `dry`) and "nothing
      compiled"; none undecided about the text.
- [x] R2 opus: zerocopy with endian types, rejection of the action-driving opcode, reserved
      bytes, the one-time copy, `checked_add`. PASS. New gaps: the lint sample lacked a
      `[workspace.lints.rust]` table and `as_conversions` / `arithmetic_side_effects` (CLOSED:
      added, and the sample measured in a workspace: it parses and fires `indexing_slicing`,
      `unwrap_used` and pedantic lints); rate-limiting guest-triggered errors (CLOSED in the VMM
      note). DECLINED (not claimed): whether `cast_possible_truncation` fires on `u32 as usize`,
      and an enforcement for the synthetic `io::Error` rule (no lint exists; the rule is owned
      by `bitranox:coding-rust`). DECLINED (out of scope): the volatile or atomic copy primitive,
      device behaviour after a parse failure.
- [x] R2 haiku: endian types, `checked_add`, reserved bytes, the copy. PASS. Gaps are protocol
      values and "not compiled"; none undecided about the text.
- [x] Quote-back on every rule the last round touched (CI failing on `warn`, where `unsafe_code`
      goes, fieldless-enum `Deserialize`, `deny_unknown_fields` for an own API, must-be-zero
      reserved fields, the lint for `offset + len`), opus and haiku: 12 of 12 answered with a
      direct quote of the governing line, none NONE.
- [x] Tiers: opus and haiku on every probe; 22 behavioural cells in all (4 RED, 4 GREEN, 4 final,
      2 quote-back for this skill, plus the 4-cell retrieval probe in coding-rust's checklist).
      Discarded and re-run: a first GREEN round and a first retrieval round launched with the
      plain-text output format, which returns the LAST assistant text; in two cells that was a
      Stop-hook reply, not the answer, so every cell of both rounds was re-run with stream-json
      and its first text block.

## Other checks

- [x] Description: 376 characters (`len()` of the parsed field), starts "Use when", names the
      Rust triggers and that the skill loads alongside `bitranox:coding-data-architecture`; the
      front matter parses with a YAML loader to `['description', 'name']`.
- [x] Router replay with `skill-router.py`'s `match()` on the regenerated trigger map: "should
      this rust enum for wire opcodes be open or closed, and use num_enum or zerocopy?",
      "replace this rust newtype validation with TryFrom" and "thiserror or anyhow for my rust
      library errors?" nominate this skill; "my python function takes a dict parameter, make it
      a pydantic model" nominates only the Python data-architecture skill; "set up criterion
      benchmarks for my rust parser" only the Rust performance skill.
- [x] History-phrase finder (both passes) over the skill directory: one hit, "stable since Rust
      1.81 ... no longer fires", a version floor and a sentence about the tool's behaviour,
      judged not history. Address and private-name grep: no IP, MAC, home or temp path, and no
      repository or product name of the VMM.
- [x] Body 412 lines, a checklist plus tool recipes, no supporting files. Code blocks counted:
      eight Rust examples of 3 to 7 lines and the bounded-read example of 9 (its `#[expect]`
      line is part of the rule it shows); the two TOML samples are 14 and 5 lines.
- [x] Trigger map and catalogue regenerated (`build_skill_triggers.py --check`: "in sync (86
      skills)"; `build_skill_docs.py --check`: "docs/skills.md in sync"); README and
      docs/installation.md counts set to 86.
- [x] Text test `hooks/tests/test_rust_skill_family_text.py`: front matter and resolving
      `bitranox:` references for the three Rust skills, with `coding-data-architecture` held in
      `PENDING_SIBLINGS` and a test that fails once that skill exists. `mutation_arm.py
      --battery` with seven arms (a dangling reference, a renamed `name:`, a description not
      starting "Use when", a `: ` breaking the YAML, an empty pending set, a pending name that
      exists, the coding-rust bullet losing its `bitranox:` prefix): all KILLED, baseline green
      before and after.
