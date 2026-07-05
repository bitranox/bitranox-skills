---
name: coding-rust
description: Use when writing or reviewing Rust and deciding how to handle errors, secrets or credentials, dependency/crate choices, or type design - or when a review flags a synthetic std::io::Error used for a non-IO condition, a non-constant-time secret/token comparison, an inline --password, a heavyweight crate pulled in for one narrow job, or a struct whose invalid field combinations are constructible.
---

# coding-rust

Idioms and review checks for Rust, distilled from real review findings. Apply when writing or
reviewing Rust; each rule states the failure it prevents.

## Errors

- **Never use `std::io::Error::new(...)` / `std::io::Error::other(...)` for a non-IO condition.** A
  synthetic IO error erases the type, so callers cannot pattern-match on what went wrong. Add a
  dedicated variant to the crate's own error enum instead, with `thiserror`:
  ```rust
  #[derive(thiserror::Error, Debug)]
  pub enum Error {
      #[error("frobnicator {0} is out of range")]
      OutOfRange(u32),
      #[error(transparent)]
      Io(#[from] std::io::Error),   // real IO stays IO
  }
  ```
- **Preserve the error chain.** Wrap with context (`anyhow::Context::context`, or a `#[from]`/`#[source]`
  on a typed variant) rather than discarding the cause behind a fresh generic message. The source chain
  is what makes a failure debuggable.

## Secrets and credentials

- **Constant-time comparison for secrets** (passwords, tokens, HMAC/auth responses). A short-circuiting
  `iter.zip(other).all(|(a, b)| a == b)` leaks length/prefix timing. Use an XOR-fold (or a vetted
  constant-time crate such as `subtle`):
  ```rust
  let equal = expected.iter().zip(response)
      .fold(0u8, |acc, (a, b)| acc | (a ^ b)) == 0
      && expected.len() == response.len();
  ```
- **`--password-file PATH` is the primary CLI interface for a secret, `--password VALUE` only a
  convenience fallback.** An inline value is visible to every user in `ps aux` / `/proc/<pid>/cmdline`.

## Dependencies

- **Pick the minimal purpose-specific crate over the heavyweight general one** when you need one narrow
  thing (e.g. `jpeg-encoder` ~50 KB vs `image` ~2 MB for JPEG-only encoding). Smaller compile time,
  binary, and attack surface.
- **Feature-gate optional heavy deps** so a lightweight consumer can opt out (`[features]` + `#[cfg(feature
  = "...")]`), rather than pulling a web framework or rich-CLI crate into every build.

## Type design

- **Make invalid states unrepresentable.** When two (or more) fields are only valid together - e.g. two
  `Option`s that must be `Some` together or `None` together - bundle them into one struct behind a single
  outer `Option`, so the mismatched state cannot be constructed:
  ```rust
  // not: struct S { a: Option<X>, b: Option<Y> }   // a=Some,b=None is constructible but invalid
  struct Pair { a: X, b: Y }
  struct S { pair: Option<Pair> }                    // both or neither, enforced by the type
  ```

## Build / review discipline (Rust specifics; general git/verify rules live in bitranox:compuse-git and bitranox:process-review-verification-before-completion)

- Run `cargo fmt --all` and `cargo clippy --all-targets -- -D warnings` before committing; fix every
  warning, not just what CI would block.
- In a workspace/monorepo, a per-crate `cargo build -p foo` is not enough when you change a shared or
  public type - build/test the whole workspace before pushing, or downstream consumers break silently.
- Forking/extending an upstream crate: keep changes at the edges (new files, additive methods, existing
  extension points) rather than editing core types, to keep the merge-conflict surface small.

## See also

For untrusted input at a service/CLI boundary (validate at the edge, escape per sink - SQL/HTML/shell/
path), the language-agnostic rules are in `bitranox:coding-input-sanitization`. Sanitize at the
boundary, not in the libraries between.
