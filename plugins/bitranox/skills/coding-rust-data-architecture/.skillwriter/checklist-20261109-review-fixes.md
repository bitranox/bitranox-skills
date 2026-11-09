# skill-writer checklist - coding-rust-data-architecture (2026-11-09, review fixes)

Fixes from an independent review of the skill: a new section "Inputs for the generic workflow"
(initialization config, candidate-sweep and STEP D greps, the analyser's Rust patterns and
NOT-violations, STEP B, the gate, the baseline arms of the error-surface diff, serializer bytes),
serde alias/default placed only on a versioned wire DTO with the rule held by the generic skill,
the enum `Debug` versus wire form, and corrected lint and cast facts.

Decisions: d-20261109-07af5b4b

- [x] Receipt fresh and `bitranox:meta-skill-writer` loaded in this agent before the first edit.
      Ledger read first (`show coding-rust-data-architecture --kind rejected,removed --full`:
      none). After the edit `skill_decisions.py check coding-rust-data-architecture` reports 0
      findings, so the anchors of d-20261109-94ef3c56 and d-20261109-c1afc908 still occur once.
- [x] Not mirrored: the skill ships only from this marketplace.
- [x] Every finding verified against the text before editing; none was wrong.

## Commands executed (rustc, cargo 1.95.0, clippy 0.1.95, scratch crates)

- [x] `#![warn(non_exhaustive_omitted_patterns)]` on stable: "warning: unknown lint ... the
      `non_exhaustive_omitted_patterns` lint is unstable ... `#[warn(unknown_lints)]` on by
      default" - the warning is rustc's `unknown_lints`.
- [x] `pub fn from_int(x: u8) -> E { x as E }`: error[E0605] non-primitive cast. `e as u8`
      compiles, and `-W clippy::as_conversions` flags it.
- [x] `unsafe fn f(p: *const u8) -> u8 { *p }`: edition 2024 warns E0133 (unsafe_op_in_unsafe_fn),
      edition 2021 prints nothing; `rustc -W help` lists the other four lints as allow.
- [x] `-W clippy::little_endian_bytes -W clippy::big_endian_bytes -W clippy::host_endian_bytes`
      flag `u32::from_le_bytes`, `from_be_bytes` and `from_ne_bytes` each.
- [x] strum 0.28.0 with serde, `#[strum(serialize_all = "kebab-case")]` beside
      `#[serde(rename_all = "kebab-case")]`: `debug=DryRun display=dry-run asref=dry-run
      serde="dry-run" parse=Ok(DryRun) bad=Err(VariantNotFound)`.
- [x] Candidate-sweep grep copied out of the SKILL.md and run on a planted file: lines 2-9 (map of
      Value, tuple return, bool params, `== "active"`, `.get("name")`, `status: String`,
      `BTreeMap<String`, `"fast" =>`) matched, `pub fn ok(x: u32) -> u32` did not; the table
      grep matched `pub static MODES: &[(&str, u8)]`, `pub(crate) const LIMITS: phf::Map<..>` and
      `pub static T2_MAP: ..`, not `const N: usize`.
- [x] Gate commands `cargo fmt --all --check`, `cargo clippy --workspace --all-targets -- -D
      warnings`, `cargo test --workspace` each exit 0 on a fresh crate.
- [x] Baseline arms: a committed crate, its working tree edited and built into a target dir, then
      `git archive HEAD | tar -x` and `cargo run` with the same `CARGO_TARGET_DIR`: printed the
      working tree's output, cargo reported Fresh (the extracted files carry the commit's mtime).
      With `CARGO_TARGET_DIR=<arm>/target` it printed the baseline's. `CARGO_TARGET_DIR` beat a
      configured `build.target-dir` (only the env dir was created).
- [x] `disallowed-types` banning `serde_json::Value`: `#[expect]` on a `derive(Deserialize)`
      struct or on its field still leaves two warnings at the field; on the enclosing module the
      field is silent and an unrelated use outside still fires.

## Probes (opus, `general-purpose`, told to read only the two skill files)

- [x] RED arms read the pre-edit SKILL.md of both skills (`git show HEAD:`); GREEN and final arms
      read the edited copies. Neither skill is in the installed plugin, so no arm could load
      another copy. Tier: opus only, one cell per changed rule, as the task scoped; no haiku arm
      was run.
- [x] Item 1 (workflow inputs). RED: gate partial (clippy only, "no test command"), sweep NONE,
      config partial, analyser block NONE, baseline arm NONE. GREEN: all five quoted from the new
      section. Final re-run (also asked for the `#[expect]` placement): all six quoted.
- [x] Item 2 (versioned DTO), shared with the generic skill's checklist. RED quoted "This is where
      `#[serde(alias)]`, `#[serde(default)]` and old fields live" against "never to make an old
      payload parse" and Principle 7, and answered retirement NONE. GREEN: no contradiction, both
      attributes on the wire DTO, "An old format nothing reads any more is deleted, DTO and all."
- [x] Item 3 (NOT-violations). RED reached the right verdicts but reported that generic
      Principles 4 and 5 read alone support the analyser and nothing gives precedence. GREEN and
      the final re-run (F3 added: literal arms in `FromStr`) quoted the new NOT-violations and
      Principles 4 and 5; all three findings permitted.
- [x] Every dispatch asked for a "Skill gaps" section; each reply's list was read.

## Gaps closed

- [x] sha256 is weak proof: the text now says the liveness control is the proof.
- [x] Env versus config target dir, and what to do with a `path =` dependency: stated.
- [x] Value envelope versus the `disallowed-types` ban: the `#[expect]` goes on the module.
- [x] Table names with digits: grep uses `[A-Z0-9_]+`.
- [x] Literal arms inside the parsing `FromStr`: added to the NOT-violations.
- [x] Open value kept for forwarding versus "never travels past": now "only as a field kept to be
      forwarded or written back".
- [x] `as` enum-to-integer versus `as_conversions`: noted that the lint still flags it.
- [x] Error-contract grep misses Rust `# Errors` doc sections: noted for `src/`.
- [x] STEP B clippy spelling: points at the gate's clippy run.

## Gaps declined

- [x] Untagged on-disk formats, migrate-versus-reader, proving no v1 file remains, a typed error
      for an unknown version: format-design questions outside the consistency fix; the untagged
      guidance stays under "serde at the boundary".
- [x] Lint-setup line `cargo clippy --all-targets -- -D warnings` without `--workspace`: it
      quotes `bitranox:coding-rust`'s CI rule; the STEP C line is the gate.
- [x] Inner versus outer module attribute: only the outer form on an inline module was run.
- [x] Multi-binary or library-only arms, which cargo profile, `<dirs>` scope, sweep noise on
      every `: bool`, Rust form of the enum-keyed table, a Rust call-site sweep pattern: generic
      workflow judgement, and the generic skill says a sweep hit is a lead.

## Checks

- [x] Width and fence check over the added lines printed nothing after every fix round; the
      paragraph after each insertion read for re-bound references.
- [x] ASCII only (no byte above 0x7f); history finder hits are pre-existing behaviour sentences.
- [x] Description unchanged; trigger map and docs regenerated with no diff.
- [x] 492 lines: over the 460 target by the new required section; no existing reviewed content
      was cut to make room.
- [x] Security: no secrets, hosts or private paths added.
