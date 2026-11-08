---
name: coding-rust-performance-review
description: Use when Rust is slow or its performance needs a benchmark - criterion, flamegraph, samply, perf, heaptrack, DHAT, clones, with_capacity, spawn_blocking, an .await with a std Mutex guard held across it, blocking calls in async code, Regex::new or format! inside a loop, needless allocations, a Vec or String grown without capacity, unbuffered I/O, clippy perf lints, cargo bench, release-profile settings (lto, codegen-units, debug symbols), or timing a change between two Rust builds.
---

# Rust performance review

Rust-specific checks and tools. The measurement method (profile first, reproduce the before
figure, interleave the arms, pin the core, prove the change took effect) and the language-neutral
checklist live in `bitranox:coding-performance-review`: load it alongside this skill. This skill
ships no scripts, because clippy and criterion already do the mechanical part.

## Measure the build you ship

- **Never time a debug build.** `cargo run` and `cargo test` without `--release` build the dev
  profile, which is unoptimised, so its timings say nothing about the release binary and an
  optimisation can vanish or invert there. Time the `cargo build --release` binary, or use
  `cargo bench` (the bench profile inherits from release).
- **Keep symbols without changing code generation:** `debug = "line-tables-only"` under
  `[profile.release]`, or `CARGO_PROFILE_RELEASE_DEBUG=line-tables-only cargo build --release`
  for one build. Debug info does not change the optimisation level.
- **Profile settings are A/B arms, not defaults:** `lto = "thin"` or `"fat"`,
  `codegen-units = 1`, `panic = "abort"` (a behaviour change as well: a panic no longer unwinds,
  so `Drop` does not run and `catch_unwind` catches nothing), and
  `RUSTFLAGS="-C target-cpu=native"` (that binary may not run on an older CPU). Record which ones
  each arm used.

## Lint first: clippy

```bash
cargo clippy --all-targets -- -D clippy::perf \
  -W clippy::redundant_clone -W clippy::needless_collect -W clippy::inefficient_to_string \
  -W clippy::large_types_passed_by_value -W clippy::trivially_copy_pass_by_ref \
  -W clippy::format_collect -W clippy::rc_buffer -W clippy::large_stack_arrays
```

The `perf` group warns by default (36 lints in clippy 0.1.95, among them
`regex_creation_in_loops`, `manual_memcpy`, `large_enum_variant`); `-D` makes them errors. The
`-W` lints are off by default because they have false positives: treat each hit as a candidate
to measure, not a verdict.

## Benchmarks: criterion

Add criterion as a dev-dependency (`cargo add --dev criterion`) and a bench target with the
default harness turned off:

```toml
[[bench]]
name = "hot_path"
harness = false
```

```rust
use criterion::{criterion_group, criterion_main, Criterion};
use std::hint::black_box;

fn bench(c: &mut Criterion) {
    let input = load_input();
    c.bench_function("parse", |b| b.iter(|| parse(black_box(&input))));
}

criterion_group!(benches, bench);
criterion_main!(benches);
```

Before and after: on the old code `cargo bench --bench hot_path -- --save-baseline before`, then
on the new code `cargo bench --bench hot_path -- --baseline before`. Criterion reports the change
with a confidence interval; "No change in performance detected" or "Change within noise
threshold" is not a win. The two runs happen one after the other, so one pair is all-A-then-all-B:
alternate old and new at least three times each, saving each run under its own name
(`--save-baseline old1`, then `new1`, `old2`, ...), and compare saved runs without re-sampling
(`--load-baseline new1 --baseline old1`) before calling a change real. `black_box` keeps the
compiler from deleting the work being timed. A criterion run is a micro-benchmark: confirm a win
on the real workload too.

For whole programs, `hyperfine --warmup 3 ./old ./new` compares two binaries, but it runs all of
one command's runs before the other's, which is not the interleaving the generic method asks
for: alternate `./old` and `./new` in a loop of your own for the verdict, and treat a hyperfine
run (repeated with the order swapped) as a cross-check only.

## Profilers and allocations

The flamegraph, samply, perf and heaptrack recipes are unverified: none of those tools has been
run for this skill. The `dhat` crate snippet is verified: it writes `dhat-heap.json`.
- `cargo flamegraph --bin app -- <args>` (`cargo install flamegraph`; builds release by default,
  uses perf on Linux and dtrace on macOS).
- `samply record ./target/release/app <args>` (`cargo install samply`), viewed in the Firefox
  Profiler.
- `perf record --call-graph dwarf ./target/release/app <args>`, then `perf report`. Inside a
  container perf can be refused by `kernel.perf_event_paranoid` or a missing capability; profile
  on the host or in a VM then.
- Allocations: `heaptrack ./target/release/app <args>`, or the `dhat` crate:
  `#[global_allocator] static ALLOC: dhat::Alloc = dhat::Alloc;` and
  `let _profiler = dhat::Profiler::new_heap();` at the top of `main`, which writes
  `dhat-heap.json` for the DHAT viewer.

## What to flag in Rust code

| Pattern                                                                             | Fix                                                                                                       |
|-------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `.clone()`, `.to_string()`, `.to_vec()` in a loop to please the borrow checker      | Borrow, use `Cow`, or restructure; `redundant_clone` finds some                                           |
| `Vec::new()` or `String::new()` then a push per iteration of known length           | `with_capacity(n)`, or `collect()` from an iterator with a size hint                                      |
| `format!` into a temporary on every iteration (`out = out + &format!(..)`)          | `write!` into one `String`; `String + &str` alone already appends in place                                |
| `collect()` into a `Vec` only to iterate once or take `len()`                       | Keep the iterator (`needless_collect`)                                                                    |
| `Regex::new`, a parser or a client built inside a loop or per call                  | Build once: a `LazyLock` static (Rust 1.80+, see below), or pass it in                                    |
| `dyn Trait` or `Box<dyn Fn>` called per element on a hot path                       | Generics for static dispatch; measure the speed against the code-size cost                                |
| Default-hashed `HashMap` with integer keys on a profiled hot path                   | `rustc-hash` or `ahash`, only if the keys are not attacker-controlled (SipHash resists HashDoS)           |
| A `std::sync::Mutex` or `RwLock` guard alive across `.await`                        | End the guard's scope before the await, or `tokio::sync::Mutex` if it must be held (`await_holding_lock`) |
| Blocking calls in async code (`std::fs`, `std::thread::sleep`, heavy CPU)           | `tokio::fs`, `spawn_blocking`, or a thread pool such as rayon                                             |
| Small reads or writes on a `File`; `println!` in a hot loop                         | `BufReader`/`BufWriter`; lock stdout once (`let mut out = std::io::stdout().lock();`)                     |
| `read_to_string`/`read_to_end` on a large input; `collect()` of an unbounded stream | Stream with `BufRead::lines` or fixed-size chunks (generic checklist: unbounded memory)                   |
| `Arc<Mutex<_>>` updated from every task of a parallel loop                          | Per-thread accumulation, merged once at the end                                                           |
| A large value moved by value; one enum variant far larger than the rest             | Pass a reference; box the large variant (`large_enum_variant`)                                            |

Two of these fixes can break or change the code. `std::sync::LazyLock` needs Rust 1.80 or newer:
check the crate's `rust-version` (and its CI toolchain) before suggesting it; on an older one use
`std::sync::OnceLock` (1.70 or newer) or build the value once in the caller and pass it in.
Rewriting a regex while moving it (`\d` to `[0-9]`, say) is not a free speedup: `\d` in the
`regex` crate matches every Unicode decimal digit, so the swap changes results on non-ASCII digits
and needs a test, not just a benchmark.
