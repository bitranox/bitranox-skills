# Data architecture skills: generic, Python, Rust - design and plan

Date: 2026-11-09. Status: implemented in 11.0.0 (the rename was decided by the user; the independent review fixes shipped in the same release).

## Goal

Make the strict data-architecture discipline available for any language and add a Rust version,
in the same three-skill shape as the performance family (docs/plans/2026-11-06-performance-skills-design.md):
a generic skill with the language-neutral rules, the existing Python skill, and a new Rust skill.

## Measured starting point (2026-11-09, read from origin/master)

- `coding-python-enforce-data-architecture-strict/SKILL.md` is 1230 lines. The principles (typed
  models at every boundary, no raw dicts inside, enums for fixed categories, one parse in and one
  dump out, no compatibility shims, define the types instead of silencing the checker) and most of
  the workflow (analysis, partitioned refactor, subagent loop, final verify) are language neutral.
  The Pydantic, StrEnum, datetime, pyright and 3.10 detail (about 60 percent) is Python specific.
- `coding-rust/SKILL.md` (79 lines) holds one data rule (invalid states unrepresentable). Newtypes,
  closed enums, boundary parsing, serde and binary parsing are not covered anywhere.
- The performance family has no stated general rule; its three-skill shape is a user decision.
  Only `coding-performance-review` shares a script. No `coding-common-*` name exists: language
  neutral skills are plain `coding-<topic>`.
- Live references to the Python skill name: docs/skills.md, hooks/skill_triggers.json (generated),
  `coding-input-sanitization` (frontmatter description and body), `coding-python-clean-architecture`,
  `coding-python-use-modern-libraries`, `process-review-enhance-code-quality`. A rename is a major
  version bump and touches all of them.

## Evidence for the Rust rules

- Our openvmm fork (Rust 2024, 1.97): wire structs are `#[repr(C)]` zerocopy types in `_spec` or
  `_protocol` crates, parsed in device code into closed internal enums with typed errors; `open_enum!`
  for every guest or hardware value (344 uses); `bitfield-struct` for registers; about 101 primitive
  newtypes; thiserror in libraries and anyhow with context at the edges; saved state is its own
  versioned mesh Protobuf struct, never shared with runtime types, and save/restore destructure both
  structs exhaustively; serde only for external JSON and file formats; `#[expect]` with a reason, never
  `#[allow]`; never panic or unwrap on untrusted input. Sources: `.github/copilot-instructions.md`,
  `Guide/src/dev_guide/contrib/{code,save-state}.md`, `vm/vmcore/src/save_restore.rs`, `Cargo.toml`
  `[workspace.lints]`, `clippy.toml`.
- Online research (40 rules, each with a source and date, UNVERIFIED items marked): parse, don't
  validate; private-field newtypes with a checked constructor; enums or structs instead of bool
  arguments; typestate; TryFrom and FromStr at the boundary; closed enums inside the crate and no `_`
  match arm; `#[non_exhaustive]` only at library edges; explicit open variants for foreign wire
  values; DTO and domain separation with `serde(try_from)`; versioned DTO enums; `deny_unknown_fields`
  with its flatten limit; avoid `untagged`; byte and depth limits before parsing untrusted input;
  thiserror for libraries, anyhow at edges, error types per unit of fallibility, no leaked inner
  errors; zerocopy with endian field types; panic-free slice APIs; builders or config structs and
  `bon` for compile-time-checked builders; `[workspace.lints]` with groups at lower priority;
  `#[expect]` over `#[allow]`. Maintenance flags: bincode is unmaintained (RUSTSEC-2025-0141),
  derive_builder has had no release since 2024-10.
- Where the two agree, the rule is firm. Where they differ it is stated as a choice: openvmm uses
  `open_enum!` plus a match with a fallback arm for wire values, the web practice uses an explicit
  Unknown variant or `num_enum`; openvmm allows many-argument functions, the Python skill caps at 3.

## Decisions to take (one at a time)

1. Shape and names. DECIDED by the user 2026-11-09: rename the Python skill to
   `coding-python-data-architecture`, and add `coding-data-architecture` (generic) and
   `coding-rust-data-architecture` (Rust). Cost accepted: a major version bump and edits to the six
   live references, the generated files and the skill's own ledger path. The old name keeps no alias,
   so any user prompt or memory fact naming it must be re-pointed (sweep below).
2. Where the generic workflow lives. Recommended: the generic skill holds principles, the checklist
   and the analyse-refactor-verify workflow; language skills hold only mechanisms and examples.
3. Rust skill scope. Recommended: a checklist plus tool recipes with no scripts, like the Rust
   performance skill. Alternative: also a script that counts violations (raw `serde_json::Value`
   fields, `HashMap<String, _>` params, bool parameters); costs a script, tests and a Rust parser.

## Tasks (detail only to the first checkpoint, the generic skill, per the three-altitude rule)

Each task is one commit and goes through the repo gate; each SKILL.md change carries a checklist
with a `Decisions:` line and a ledger entry for the shape decision (`skill_decisions.py add`).

1. Generic skill `coding-data-architecture`. Move the language-neutral principles, anti-patterns,
   definition-of-done checklist, workflow and rationalizations out of the Python skill; add a
   "Route by language" table (Python, Rust; others use this alone). Description starts "Use when"
   and names the triggers (dict parameters, stringly-typed status, raw JSON values passed around,
   compatibility shims) and routes Python and Rust. Tests: a text check that the Python skill no
   longer holds the moved sections and cites the generic one; RED on the pre-edit text.
2. Rename and slim the Python skill: `git mv` the directory so its `.skillwriter` ledgers move with it
   (a renamed skill answers to its old name at the fork point), change `name:` and the H1, then slim it to its mechanisms (Pydantic, StrEnum and 3.10 forms, datetime, aliases,
   discriminated unions, pyright facades), with a first-section pointer to the generic skill. Check
   that no Python rule was lost (diff the heading list before and after) and that the 6 live
   references still resolve. Sweep every spelling of the old name with an uncapped grep over the repo, memory facts and hooks
   (SKILL.md files, docs/skills.md, skill_triggers.json, the four referencing skills, README, tests);
   historical files (CHANGELOG, docs/plans, old checklists) stay. Bump MAJOR for the rename.
3. Rust skill `coding-rust-data-architecture`, from the two evidence lists above. Sections: parse at
   the boundary (newtype, TryFrom, FromStr), enums (closed inside, open at the wire), Option and
   NonZero, typestate and builders, serde boundary (DTO vs domain, versioning, limits, error paths),
   binary data (zerocopy, endian types, panic-free slicing, bitfields), errors, lints, crates with
   maintenance flags, and a "what openvmm does" note kept generic (no private paths). Every
   rule names the clippy lint that checks it where one exists, verified by running `cargo clippy`
   on a scratch crate for the lint names; lints marked UNVERIFIED stay marked.
4. Cross-links and housekeeping: See-also lines in `coding-rust`, `coding-input-sanitization`
   (description change means a trigger rebuild and its own checklist), `process-review-enhance-code-quality`;
   `build_skill_triggers.py`, `build_skill_docs.py`, README count, `repo-gate.py --ci`, minor bump.
5. Review: one opus agent reads the Rust skill against the openvmm repo and the research list and
   lists contradictions; a second probes the generic and Rust descriptions for triggering with
   baseline-probe agents. Fix, then push and watch CI.

## Verification

- `python3 plugins/bitranox/hooks/repo-gate.py --ci` and the skill tests with CI's dependency set.
- Heading diff proves the Python skill kept every Python-specific section.
- Each Rust lint name checked against the installed clippy (`cargo clippy -- -W clippy::<name>` on a
  scratch crate); a lint that does not exist is removed from the skill.
- Triggering probe: a Rust boundary-parsing prompt loads the Rust skill and routes to the generic;
  a Python dict-parameter prompt still loads the Python skill.

## Out of scope

Go, TypeScript and other languages (they use the generic skill alone until a language skill is
worth its cost); a Rust violation-scanner script; renaming the Python skill unless decision 1 says so.
