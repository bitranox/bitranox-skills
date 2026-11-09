---
name: coding-rust-data-architecture
description: Use when Rust newtype, TryFrom, FromStr, serde Deserialize, deny_unknown_fields, untagged enum, zerocopy, bitfield, num_enum, thiserror or anyhow code needs a data-architecture review - untrusted input parsed at a boundary, open versus closed enums, wire or register structs, builders, or the clippy lints that enforce these. Loads alongside bitranox:coding-data-architecture.
---

# Rust data architecture

Rust mechanisms for the strict data-architecture discipline. The principles (typed models at
every boundary, no untyped maps inside, enums for fixed categories, one parse in and one dump
out, no compatibility shims) and the analyse-refactor-verify workflow live in
`bitranox:coding-data-architecture`: load it alongside this skill. This skill ships no scripts:
the type checker and clippy already do the mechanical part, once the lints below are on.

Every lint name here was checked against clippy 0.1.95 (rustc and cargo 1.95.0): each one is
accepted without an `unknown lint` warning, and the group named after it is the one
`cargo clippy -- -W help` lists. Groups and defaults shift between toolchains; re-check on yours
with that command. Every code example compiles and its claims ran as tests on that toolchain with
serde 1.0.229, serde_json 1.0.154, thiserror 2.0.21, zerocopy 0.8.63, num_enum 0.7.4 and
bitflags 2.13.2; "measured" marks a behaviour seen in such a run. Version numbers, dates and
lint thresholds come from the documentation and crates.io; UNVERIFIED marks a behaviour claim
taken from documentation that was not run.

## Parse at the boundary

- **Return a type that carries the proof, never a `bool`.** A validator returning `bool`
  discards what it learned, so every later caller re-checks or trusts blindly. Parse once into a
  type that cannot hold an invalid value. WHAT a value must satisfy (no CR or LF in a mail
  address, no private address as a connect target, a sane retry count) is
  `bitranox:coding-input-sanitization`'s question; check it in the same constructor.
- **A newtype with an invariant has a private field and one checked constructor.** Read access
  through `as_str()`, `get()` or `AsRef`; no `pub` field, no `DerefMut`. (The `@` test below
  only shows the shape; real address validation is a separate question.)

  ```rust
  pub struct Email(String);
  impl TryFrom<String> for Email {
      type Error = EmailError;
      fn try_from(s: String) -> Result<Self, Self::Error> {
          if s.contains('@') { Ok(Self(s)) } else { Err(EmailError::MissingAt) }
      }
  }
  ```
- **Newtypes for static distinctions** (units, ids, indices) even without an invariant:
  `#[repr(transparent)] pub struct UserId(u64)` stops a `u32` of the wrong kind at compile
  time. Once a value has an invariant, apply the private-field rule.
- **Fallible conversion is `TryFrom` or `FromStr`, infallible is `From`.** Implement `From`, never
  `Into` (`from_over_into`, style); a `From` that can panic is a `TryFrom`
  (`fallible_impl_from`, nursery); a `TryFrom` that cannot fail is a `From`
  (`infallible_try_from`, suspicious). An unchecked fast path is a separate `new_unchecked`.
- **Absence is `Option`, never a sentinel** (`0`, `-1`, `""`). `Option<NonZeroU32>` (or the
  generic `NonZero<T>`) costs nothing extra. `Option<Option<T>>` means two kinds of absence: name
  them in an enum instead (`option_option`, pedantic). serde cannot even fill it: a missing field
  and JSON `null` both decode to the outer `None` (measured), so `Some(None)` never arrives
  without a custom `deserialize_with`. `&Option<T>` in a signature is
  `Option<&T>` (`ref_option`, pedantic; `ref_option_ref`, pedantic, for `&Option<&T>`).
- **Derive helpers can bypass the constructor.** A derived `From`, `Constructor` (derive_more) or
  `Deserialize` on an invariant-bearing newtype builds it without the check; route
  deserialization through `#[serde(try_from = "String")]`.

## Enums: closed inside, open at the wire

- **Your own categories are closed enums**, never a `String` or an integer with a comment
  listing the values. Parse with `FromStr` or `TryFrom` at the boundary; for serde a fieldless
  enum can derive `Deserialize` itself (`#[serde(rename_all = "kebab-case")]`), and `"Fast"` then
  fails with "unknown variant `Fast`, expected one of `fast`, `safe`, `dry-run`" (measured).
- **Inside your own crate, never match your enum with `_`.** List every variant so a new one is
  a compile error at each site, not a silent fall-through (`wildcard_enum_match_arm`,
  restriction; `match_wildcard_for_single_variants`, pedantic). rustc's
  `non_exhaustive_omitted_patterns` is unstable: on stable rustc 1.95 naming it draws rustc's own
  `unknown_lints` warning ("the `non_exhaustive_omitted_patterns` lint is unstable").
- **An enum's `Debug` is its Rust name, never its wire form.** `format!("{:?}", Mode::DryRun)`
  gives `DryRun` while serde writes `dry-run`, and an enum has no `Display` until you write one,
  so `{:?}` never goes into a wire string, key or file name. Implement `Display` to print the wire
  form, or derive strum's `Display`, `AsRefStr` and `EnumString` with
  `#[strum(serialize_all = "kebab-case")]` beside the same serde `rename_all` (measured with strum
  0.28.0: `Display`, `as_ref()` and serde all give `dry-run`), and pin that equality with a test.
- **`#[non_exhaustive]` only at a library's public edge.** Outside the defining crate it forbids
  struct literals and forces `..` and `_`; inside the crate it does nothing. An application's
  internal enums stay exhaustive. `manual_non_exhaustive` (style) flags the hand-rolled hidden
  variant; `exhaustive_enums` and `exhaustive_structs` (restriction) flag public types without it.
- **A value defined by someone else (a protocol, hardware, a peer's JSON) must survive an unknown
  code.** Two shapes, a choice to make per type:
  - **Open newtype with named constants** (what a large Rust VMM does for every guest and hardware
    value). Any `u8` is representable and round-trips; a `match` needs a fallback arm, which
    returns a typed error or forwards the raw value. Use it when unknown values must be stored,
    forwarded or written back unchanged.

    ```rust
    #[derive(Clone, Copy, PartialEq, Eq, Debug)]
    #[repr(transparent)]
    pub struct Op(pub u8);
    impl Op { pub const READ: Op = Op(1); pub const WRITE: Op = Op(2); }
    // match op { Op::READ => .., Op::WRITE => .., _ => Err(ParseError::UnknownOpcode(op.0)) }
    ```
  - **Enum with an explicit unknown variant** that keeps the raw value: `Unknown(u8)` from a
    hand-written `From<u8>`, or num_enum's `FromPrimitive` with `#[num_enum(catch_all)]
    Other(u8)`. Matches on the known variants stay exhaustive. Use it when the code mostly acts on
    known values and only logs or rejects the rest.
  - **Rejecting is also a choice:** num_enum's `TryFromPrimitive` returns an error for an unknown
    code. Fine for a value that drives an action; wrong for a field you must write back.
  - Then convert the wire value into a closed internal enum at the parse step and decide on
    that; the open value travels past it only as a field kept to be forwarded or written back.
- **Never `transmute` an integer into an enum, or cast a pointer to one in `unsafe` code.** An
  enum holding an undefined discriminant is undefined behaviour the moment it exists. `as` goes
  only the other way, enum to integer (`Mode::Fast as u8`, which `as_conversions` still flags);
  `x as Mode` does not compile (E0605).
- **Flag sets are `bitflags`**, not a `u8` and a list of masks, and unknown bits take the same
  choice as unknown codes: `from_bits` refuses them (flags that drive an action), while
  `const _ = !0;` in the flag list keeps them (flags you must write back; with it,
  `from_bits(0x80)` returns `Some`).

## Invalid states unrepresentable

- **Variants carry their data.** A `kind` field plus optional fields that are valid only for some
  kinds is an enum whose variants hold exactly those fields.
- **Fields that are only valid together go in one struct behind one `Option`** (both or neither,
  enforced by the type); see `bitranox:coding-rust`, "Type design".
- **Enums or config structs instead of `bool` arguments.** `submit(body, true, false, true)` is
  unreadable at the call site and admits combinations nobody meant (`fn_params_excessive_bools`
  and `struct_excessive_bools`, pedantic, fire at more than 3).
- **Typestate when the order of operations is the invariant.** Each state is its own type and a
  transition consumes `self`, so calling `send` on a sent mail does not compile. The cost is
  rebinding at every step; use it for protocols and builders, not for every struct.

  ```rust
  pub struct Draft; pub struct Sent;
  pub struct Mail<S> { body: String, state: PhantomData<S> }
  impl Mail<Draft> {
      #[must_use]
      pub fn send(self) -> Mail<Sent> { Mail { body: self.body, state: PhantomData } }
  }
  ```

## serde at the boundary

- **Separate the wire DTO from the domain type.** `Deserialize` goes on a DTO of plain fields;
  the domain type is built by `TryFrom<Dto>` and can be decoded directly with
  `#[serde(try_from = "Dto")]`. The domain type never derives `Deserialize` field by field.
  `#[serde(try_from)]` turns the conversion error into a serde error message (measured: the
  `JobError` arrives as the text "invalid mode"); when a caller must `match` on it, decode the DTO
  and call `Job::try_from(dto)` yourself.

  ```rust
  #[derive(Deserialize)]
  #[serde(deny_unknown_fields)]
  struct JobDto { mode: String, email: String }
  #[derive(Deserialize)]
  #[serde(try_from = "JobDto")]
  pub struct Job { mode: Mode, email: Email }
  // impl TryFrom<JobDto> for Job: Ok(Self { mode: d.mode.parse()?, email: d.email.try_into()? })
  ```
- **Version the wire, not the domain.** A format the system must still read (a peer's, files
  already persisted) gets a tagged enum of versioned DTOs that converts once into one domain type:
  a boundary, not a shim (the generic skill's Core Principle 7 states the rule). `#[serde(alias)]`,
  `#[serde(default)]` and old fields go only on such a wire DTO, never on the domain type, which
  gets no `Option` fields kept for old payloads; a field an old version lacks is filled there or in
  that DTO's `TryFrom`. An old format nothing reads any more is deleted, DTO and all. (Synthesis
  from the DTO rule, UNVERIFIED as published practice.)
- **`#[serde(deny_unknown_fields)]` where a typo must fail** (config files, requests to an API
  whose format you define, whoever sends them).
  Unknown fields then fail with "unknown field". It is documented as not supported together with
  `#[serde(flatten)]`; measured, a flattened catch-all map then never receives a field, the
  outer struct rejects it. For input from newer peers, ignore unknown fields instead and observe
  them with `serde_ignored`.
- **Avoid `#[serde(untagged)]`** except for small shapes that cannot be confused. The first
  variant that fits wins, and a failure says only "data did not match any variant of untagged
  enum T" at line 0, column 0 (measured), so the reader learns nothing about which field was
  wrong. Prefer a tag (serde's default external tag where you own the format, else an internal
  `#[serde(tag = "type")]` or adjacent one): with
  `#[serde(tag = "kind", deny_unknown_fields)]` on the enum, an extra key fails as "unknown field
  `zz`, expected `name`" and a bad value names its type (measured).
- **`#[serde(default)]` turns a missing required field into a default silently.** Use it only
  where the default is a real answer, and for an older format only on its versioned wire DTO
  (above), never on the domain type.
- **Bound the input before parsing it.** Cap the bytes first (`Read::take`, a body limit, a
  maximum frame size), then deserialize; serde itself has no total-size limit. serde_json stops
  nesting at 128 levels by default (measured: 129 levels fail with "recursion limit exceeded");
  turning that off needs the `unbounded_depth` feature and a stack guard of your own
  (`serde_stacker`).

  ```rust
  #[expect(clippy::disallowed_methods, reason = "the one parse, after the byte cap")]
  pub fn read_job(reader: impl Read) -> Result<Job, BodyError> {
      let mut buf = Vec::new();
      reader.take(MAX_BODY + 1).read_to_end(&mut buf).map_err(BodyError::Read)?;
      if u64::try_from(buf.len()).map_or(true, |n| n > MAX_BODY) {
          return Err(BodyError::TooLarge);
      }
      serde_json::from_slice(&buf).map_err(BodyError::Parse)
  }
  ```
- **Report where it failed:** `serde_path_to_error::deserialize` names the field path
  (`target.port`) in the error. (Read from its docs, not run.)
- **Borrow only when profiling asks for it.** `&str` and `Cow` with `#[serde(borrow)]` tie the
  value to the input buffer; `DeserializeOwned` for anything that outlives it.
- **A library exposes serde support behind a feature named `serde`**, not as a hard dependency.
- **Never pass `serde_json::Value` or `HashMap<String, Value>` inward.** It is the Rust spelling
  of the raw dict the generic skill forbids: parse into a type at the boundary.

## Binary and protocol data

- **Fixed-layout headers are zerocopy structs, never `transmute` or pointer casts.** Derive
  `FromBytes, KnownLayout, Immutable, Unaligned` on a `#[repr(C)]` struct; use `TryFromBytes`
  when some bit patterns are invalid (an enum field, a `bool`).
- **Put the byte order in the field type:** `zerocopy::little_endian::U32` (or `big_endian`,
  `network_endian`), read with `.get()`. A plain `u32` field reads in host order. In a crate that
  reads every wire value through such field types, `big_endian_bytes`, `little_endian_bytes` and
  `host_endian_bytes` (restriction) find the stray conversions: they fire on every
  `from_*_bytes` call (measured), so leave them off where hand-written parsing calls
  `from_le_bytes` (below) on purpose.

  ```rust
  #[derive(FromBytes, KnownLayout, Immutable, Unaligned)]
  #[repr(C)]
  struct RawHeader { opcode: u8, flags: u8, reserved: [u8; 2], len: U32, offset: U64 }
  let Ok((raw, rest)) = RawHeader::read_from_prefix(buf) else {
      return Err(ParseError::Short { expected: size_of::<RawHeader>() });
  };
  ```

  `read_from_prefix` copies and returns an error on a short buffer (measured: 15 bytes for a
  16-byte header fail, 17 bytes return the header and a 1-byte rest). A copy is also the
  snapshot to parse when the source memory can change under you. The raw struct stays private
  to the parsing module and is converted into the domain header there. The zerocopy derives
  compile under `#![deny(unsafe_code)]` (measured), so a parsing crate can keep that lint.
- **Memory the other side can still write is copied once, then parsed.** A `&[u8]` over memory a
  guest or peer writes concurrently is a data race, and reading a field twice lets a checked
  value change before it is used. Copy the header out through the memory layer's own copy
  routine (volatile or atomic reads), then parse only the copy. How that layer reads is outside
  this skill.
- **Decide every reserved field:** reject a non-zero value where the format says must-be-zero,
  keep it and write it back where the format says preserve. A reserved field read and ignored
  can never be given a meaning later.
- **Hand-written byte parsing uses the panic-free slice APIs**, never `buf[a..b]`:
  `split_first`, `first_chunk`, `split_first_chunk::<N>()` (each returns `Option`),
  `split_at_checked`, then `u32::from_le_bytes(*chunk)`. Indexing panics on short input
  (`indexing_slicing`, `string_slice`, restriction).

  ```rust
  let (op, rest) = buf.split_first().ok_or(ParseError::Short { expected: 5 })?;
  let (len, _rest) = rest.split_first_chunk::<4>().ok_or(ParseError::Short { expected: 5 })?;
  let len = u32::from_le_bytes(*len);
  ```
- **Casts at a boundary are conversions:** `u64::from`, `usize::try_from`, never `as`
  (`as_conversions`, restriction; `cast_possible_truncation`, `cast_sign_loss`,
  `cast_possible_wrap`, `cast_lossless`, pedantic).
- **Arithmetic on wire values is checked:** `offset.checked_add(u64::from(len))` before the range
  is used (`arithmetic_side_effects`, restriction).
- **Registers are typed bitfield structs** (`bitfield-struct` 0.13; alternatives
  `modular-bitfield`, `bitfield`, and `deku` or `binrw` for whole formats), with reserved bits
  named so a write cannot set them by accident.
- **Integer wire codes become enums through `num_enum`** (`TryFromPrimitive` to reject,
  `FromPrimitive` with `catch_all` to keep), or a hand-written `match`.
- **bytemuck** suits plain-old-data casts; for untrusted bytes that need validity checks use
  zerocopy `TryFromBytes` or bytemuck's `CheckedBitPattern`.

## Errors

- **`thiserror` in libraries and library-like layers, `anyhow` (or `eyre`) with `.context()` at
  the application edge.** A library caller must be able to `match` on what went wrong.
- **One error type per unit of fallibility, variants named by the step that failed**
  (`ReadBody`, `ParseBody`), not by the inner type (`Io`). No blanket `#[from] io::Error`: two
  different reads become one indistinguishable variant.

  ```rust
  #[derive(Debug, thiserror::Error)]
  pub enum BodyError {
      #[error("reading the request body")] Read(#[source] std::io::Error),
      #[error("request body over {MAX_BODY} bytes")] TooLarge,
      #[error("parsing the request body")] Parse(#[source] serde_json::Error),
  }
  ```
- **Well-behaved errors:** `Error + Send + Sync + Debug + 'static`; `Display` lowercase without
  trailing punctuation; the cause through `source()`, not pasted into the message; never `()` or
  `Box<dyn Error>` in a library signature; never a synthetic `std::io::Error` for a non-IO
  condition (see `bitranox:coding-rust`). Lints: `error_impl_error`, `map_err_ignore`
  (restriction), `result_large_err` (perf, fires over 128 bytes), `missing_errors_doc`
  (pedantic).
- **A published library does not leak a dependency's error type in a public variant:** wrap it
  in a private enum and expose it with `#[error(transparent)]`, so the dependency can change
  without a breaking release. An application's own error enum may hold it as a `#[source]`.
- **No `unwrap`, `expect` or `panic!` on a path that untrusted data reaches.** Tests and proven
  internal invariants may still assert. Lints: `unwrap_used`, `expect_used`, `unwrap_in_result`,
  `panic`, `todo`, `unimplemented`, `get_unwrap` (restriction), `missing_panics_doc` (pedantic);
  `allow-unwrap-in-tests = true` in `clippy.toml` keeps tests readable. The lints keep the known
  patterns out; a fuzz target over the parse function (`cargo fuzz`, asserting it returns and
  never panics) finds the rest. (Fuzzing not run for this skill.)

## Construction and visibility

- **More than a few parameters: a config struct or a builder.** `too_many_arguments`
  (complexity) fires at more than 7 by default; set `too-many-arguments-threshold` lower in
  `clippy.toml` to match a stricter house rule. Where a signature mirrors an external interface
  (a hardware command, a C API), keep the arguments and opt that one function out with
  `#[expect(clippy::too_many_arguments, reason = "...")]`, per the generic skill's "never
  suppress or exclude the checker". A lint allowed workspace-wide (the VMM below) is that
  project's recorded choice with its reason, not a default to copy.
- **Prefer compile-time-checked builders:** `bon` reports a missing required field as a compile
  error; `derive_builder` checks at run time and returns a `Result` from `build()`. (Builder
  crate details UNVERIFIED, read from their docs; `typed-builder` is another compile-time option.)
- **`Default` only when a meaningful default exists**, and pair `new()` with it
  (`new_without_default`, style). Never derive `Default` on a type whose all-zero value is
  invalid.
- **`#[must_use]` on pure constructors, builders and value-returning functions**
  (`must_use_candidate`, `return_self_not_must_use`, pedantic; `let_underscore_must_use`,
  restriction; `double_must_use`, `must_use_unit`, style).
- **Visibility:** fields private by default, no struct mixing public and private fields
  (`partial_pub_fields`, restriction), no `pub(crate)` on single fields as a workaround
  (`field_scoped_visibility_modifiers`, restriction), no `pub _name` fields
  (`pub_underscore_fields`, pedantic); seal traits callers must not implement; rustc's
  `unreachable_pub` finds `pub` items that nothing outside can reach.
- **Minimal conversions:** take what you need (`&str`, `&[T]`), return what you built, and do not
  convert back and forth (`useless_conversion`, complexity; `unnecessary_to_owned`, perf;
  `redundant_clone`, nursery; `implicit_clone`, `needless_pass_by_value`,
  `trivially_copy_pass_by_ref`, `large_types_passed_by_value`, `unnecessary_wraps`, pedantic;
  `str_to_string`, restriction). Name conversions `as_` (cheap borrow), `to_` (costly),
  `into_` (consumes).

## Lint setup

Put the lints in the workspace root and opt every crate in, so the rules cannot drift per crate:

```toml
[workspace.lints.rust]
unsafe_code = "deny"

[workspace.lints.clippy]
pedantic = { level = "warn", priority = -1 }
wildcard_enum_match_arm = "warn"
indexing_slicing = "warn"
unwrap_used = "warn"
expect_used = "warn"
panic = "warn"
as_conversions = "warn"
arithmetic_side_effects = "warn"
allow_attributes = "warn"
allow_attributes_without_reason = "warn"
```

- The levels are `warn`; CI fails on them with `cargo clippy --all-targets -- -D warnings`, as
  `bitranox:coding-rust` prescribes.
- Each member crate says `[lints] workspace = true` (Cargo 1.74 or newer). It cannot add its own
  entries beside that: Cargo refuses the manifest with "cannot override `workspace.lints` in
  `lints`" (measured). For lints only one crate needs, put `#![warn(clippy::indexing_slicing)]`
  at that crate's root.
- **Groups get a lower priority than single lints.** A group and a lint at the same priority is
  refused: `lint_groups_priority` is deny by default and errors with "lint group `pedantic` has
  the same priority (0) as a lint" (measured), because Cargo ignores the order inside the table.
- **Exempt with `#[expect(lint, reason = "...")]`, never `#[allow]`** (stable since Rust 1.81).
  An expectation that no longer fires is reported by `unfulfilled_lint_expectations` (warn), so
  stale exemptions surface; `allow_attributes` and `allow_attributes_without_reason`
  (restriction) make `#[allow]` itself a finding.
- **Restriction lints are opt-in one by one**, never the whole group
  (`blanket_clippy_restriction_lints`, suspicious, warns on that). Turn on the ones above for
  crates that read untrusted input.
- **Enforce the boundary itself from `clippy.toml`.** No lint looks at `#[serde(untagged)]`,
  `#[serde(flatten)]` or a missing `deny_unknown_fields`; pin those with tests. What clippy can
  do is ban the escape hatches, so `disallowed_types` and `disallowed_methods` (style, warn by
  default) fire everywhere except the one boundary function or module, which carries an
  `#[expect]` (for a DTO field of a banned type, on its module: on the struct or the field,
  `derive(Deserialize)` still fires, measured):

  ```toml
  disallowed-types = [{ path = "serde_json::Value", reason = "parse into a typed model" }]
  disallowed-methods = [{ path = "serde_json::from_slice", reason = "use read_job (caps bytes)" }]
  max-fn-params-bools = 1
  allow-unwrap-in-tests = true
  allow-expect-in-tests = true
  ```

  All five keys are accepted (measured). Both bans fired on the named type and method,
  `max-fn-params-bools = 1` makes `fn_params_excessive_bools` fire at two bools (default 3), and
  with `allow-unwrap-in-tests` a `cargo clippy --all-targets -W clippy::unwrap_used` run flags
  the library `unwrap` and none in tests.
- Useful rustc lints: `unsafe_op_in_unsafe_fn` (warn by default in edition 2024, allow in 2021
  and older; measured), and `unsafe_code`, `missing_docs`, `missing_debug_implementations`,
  `unreachable_pub` (allow by default).
  Unsafe code that remains needs `undocumented_unsafe_blocks` (restriction).
- Related: `large_enum_variant` (perf, 200 bytes), `enum_glob_use`, `wildcard_imports`
  (pedantic), `iter_over_hash_type` (restriction, for output that must be deterministic).

## Inputs for the generic workflow

What each step of the Workflow in `bitranox:coding-data-architecture` runs on a Rust project:

- **INITIALIZATION step 2:** the workspace `Cargo.toml` (`[workspace.lints]`, `edition`,
  members) and each member's `[lints]`; `clippy.toml` or `.clippy.toml`; `rust-toolchain.toml`
  (or `rust-toolchain`); `.cargo/config.toml`, whose `target-dir` matters for STEP C item 5.
- **STEP A, the CANDIDATE SWEEP** (it matched 8 planted cases and not a plain signature,
  measured); STEP D reuses it and adds the second line, for module-level tables:

  ```bash
  grep -rnE --include='*.rs' -- '-> \(|(Hash|BTree)Map<String|serde_json::Value|: bool\b|[!=]= "|\.get\("|"[A-Za-z_-]+" *=>|(status|mode|kind|state): String' <dirs>
  grep -rnE --include='*.rs' -- '^(pub(\([a-z]+\))? )?(static|const) [A-Z0-9_]+: .*(Map<|\(&str)' <dirs>
  ```
- **STEP A, the analysis subagent's Rust patterns** (in place of `{the language skill's
  patterns}`):

  ```
  - HashMap<String, _>, BTreeMap<String, _> or serde_json::Value parameters, returns or
    fields carrying structured data, and `.get("key")` on them
  - a String or integer for a closed category; literals compared or matched for a status or
    mode (`== "active"`, `"fast" =>`); `{:?}` written into a wire string
  - fixed-shape records returned as bare tuples (`-> (String, Option<u16>)`)
  - two or more bool parameters; Option<Option<T>>; a sentinel (0, -1, "") for absence
  - a domain type deriving Deserialize field by field, or carrying serde alias/default
  - `buf[a..b]` or `as` casts on wire values
  NOT violations:
  - an open newtype with named constants for a value someone else defines
    (`pub struct Op(pub u8)`, `const READ: Op`), matched with a fallback arm and converted
    into a closed enum at the parse step
  - a wire DTO deriving Deserialize plus its TryFrom<Dto> into the domain type: the pair is
    the one parse, and the DTO's String fields are parsed there
  - versioned wire DTOs with serde alias/default for a format still read (Core Principle 7)
  - a serde_json::Value field for a free-form external envelope, inside the boundary only
  - a `_` arm on another crate's #[non_exhaustive] type or on an open newtype
  - literal arms inside the FromStr or TryFrom impl that parses the wire string
  ```

- **STEP B, the type checker** is the compiler: `cargo test` does not build while a call site
  still passes the old type, so report the gate's clippy run (below) beside it.
- **STEP C, the gate:** a Makefile `test` target first, else `cargo fmt --all --check`, then
  `cargo clippy --workspace --all-targets -- -D warnings`, then `cargo test --workspace`.
- **STEP C item 5, the error surface:** what moves is the error type and variant, its `Display`
  text (with `#[serde(try_from)]` the conversion error becomes serde's message) and the exit
  code; the error contract also sits in `# Errors` doc sections, so the doc grep covers `src/`
  too. Extract each baseline with `git archive <ref> | tar -x -C <tmpdir>`, build it with its
  OWN target dir (`CARGO_TARGET_DIR=<tmpdir>/target`) and run the binary by that path. A shared
  target dir runs the wrong code: measured, a `git archive` baseline (its files carry the
  commit's older mtime) built into the working tree's target dir reported `Fresh` and printed the
  working tree's output. The per-arm `CARGO_TARGET_DIR` also overrides an exported one and a
  `target-dir` in `.cargo/config.toml` (measured); a `path =` dependency leaving `<tmpdir>`
  still builds the working tree's crate, so grep the extracted manifests for it. Two binary
  paths and hashes show the arms built apart, not that each ran its own code: the liveness
  control is the proof.
- **Serializer bytes (Core Principle 2):** serde_json writes struct fields in declaration order
  and a `HashMap` in its iteration order, which changes between runs (std docs); byte-compare
  through a `BTreeMap` or a struct. **Revalidation:** no setting; an updated value goes through
  its checked constructor or `TryFrom` again.

## Crates and maintenance flags

Versions as listed on crates.io on 2026-11-09, not all run:

- Validation: `nutype` 0.8 (sanitise plus validate, also on deserialization; pre-1.0), `garde`
  0.23 (a `Valid<T>` wrapper), `validator` 0.21 (validates after construction, so an invalid
  value exists first: weaker than a checked constructor).
- Enums and flags: `num_enum` 0.7, `strum` 0.28, `bitflags` 2.13. serde helpers: `serde_with`
  3.24 (detail UNVERIFIED), `serde_path_to_error` 0.1, `serde_ignored` 0.1.
- Binary: `zerocopy` 0.8, `bytemuck` 1.25, `bitfield-struct` 0.13; parsers `winnow` 1.0,
  `nom` 8.
- Errors: `thiserror` 2.0, `anyhow` 1.0, `snafu` 0.9; `miette` 7.6 has had no release since
  2025-04.
- Builders: `bon` 3.10 (MSRV 1.88).
- **Flags:** `bincode` is unmaintained (RUSTSEC-2025-0141; alternatives `postcard`, `bitcode`,
  `rkyv`, `wincode`); `derive_builder` has had no release since 2024-10; `byteorder` none since
  2023-10 (std `from_be_bytes` and zerocopy's endian types cover it).

## What a large Rust VMM does

Patterns observed in one large open-source Rust virtual machine monitor (Rust 2024), a useful
reference for code that parses hostile bytes:

- Never panic, `unwrap` or `expect` on guest-controlled input; `assert!` (not `debug_assert!`)
  for internal invariants, so a broken invariant stops the process in release builds too.
- Wire structs are `#[repr(C)]` zerocopy types in separate spec or protocol crates; device code
  reads one, matches its open opcode constant with a fallback arm that returns a typed error,
  and builds a closed internal enum.
- An open-enum macro (a `#[repr(transparent)]` newtype with named constants) for every protocol
  and hardware value; registers as `bitfield-struct` types with named reserved bits; about a
  hundred primitive newtypes.
- `thiserror` enums at library and protocol boundaries, `anyhow` with `.context()` in
  application plumbing; trace events a guest can trigger repeatedly are rate-limited.
- Saved state is its own versioned type (Protobuf), never the runtime struct; save and restore
  destructure both structs exhaustively, so a new field fails to compile until it is handled.
  serde only for external JSON and file formats.
- `#[expect(lint)]` with a justification, never `#[allow]` (`allow_attributes` warns);
  `[workspace.lints]` with groups at a lower priority; `too_many_arguments`,
  `new_without_default` and `type_complexity` allowed workspace-wide, that project's recorded
  choice (a new project opts out per site, see "Construction and visibility"); `clippy.toml`
  disallows `std::sync` locks in favour of another crate's.

It differs from the web practice in one place worth knowing: open newtypes with a fallback arm
for wire values, where much published Rust code uses an enum with an `Unknown(raw)` variant.
Both keep the unknown value; pick per type as described under "Enums".

## See also

- `bitranox:coding-data-architecture` - the language-neutral principles and workflow.
- `bitranox:coding-rust` - error, secret and dependency idioms for Rust.
- `bitranox:coding-input-sanitization` - what to validate and escape at an untrusted boundary.
- `bitranox:coding-rust-performance-review` - clippy's perf lints and benchmarking.
