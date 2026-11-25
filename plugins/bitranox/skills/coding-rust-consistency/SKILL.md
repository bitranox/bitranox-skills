---
name: coding-rust-consistency
description: Use when Rust code is reviewed or written for consistency - duplicated logic whose copies may differ, such as an as cast beside round(), Duration as_secs beside as_secs_f64, integer beside float division, contains beside to_lowercase or eq_ignore_ascii_case, a derived PartialOrd comparison beside ==, two match tables over one enum - or when a struct field is assigned but never read, a rustdoc comment names a use that does not exist, or a pub fn signature changed beyond what the plan lists. Loads alongside bitranox:coding-consistency.
---

# Rust consistency

Rust mechanisms for the consistency lens. The seven pairings, the rules for writing a change and
the pair table a review returns live in `bitranox:coding-consistency`: load it alongside this
skill. This skill adds the Rust constructs that make two computations of "the same" value differ,
the shapes that leave only one computation to write, what the toolchain reports by itself and
what it does not, and the searches for the review. It ships no scripts.

Every code example here compiles and its assertions ran as tests on rustc and cargo 1.95.0
(edition 2024) with clippy 0.1.95; "measured" marks a behaviour seen in such a run. Lint groups
and defaults shift between toolchains; re-check a lint on yours with `cargo clippy -- -W help`.

## Same value, two results

Each row is a pair that compiles, reads as equivalent and returns different results. When a
change holds both spellings for one quantity, that is a `DISAGREE` row in the pair table (rule or
unit cell), and the finding's concrete input is in the last column, whose two results stand in
the order of the two code columns.

| One path writes        | The other writes                      | They differ on (measured)                                               |
|------------------------|---------------------------------------|-------------------------------------------------------------------------|
| `(x * 100.0) as u64`   | `(x * 100.0).round() as u64`          | `x = 0.29`: 28 and 29 (`0.29 * 100.0` is `28.999999999999996`)          |
| `d.as_secs() as f64`   | `d.as_secs_f64()`                     | 1999 ms: `1.0` and `1.999`                                              |
| `d.as_millis() / 1000` | `d.as_secs_f64()`                     | 1999 ms: `1` and `1.999`                                                |
| `a / b` on integers    | `a as f64 / b as f64`                 | `7 / 2`: 3 and 3.5; `-7 / 2` is -3 while `(-7_i32).div_euclid(2)` is -4 |
| `n / 100 * 95`         | `n * 95 / 100`                        | `n = 40`: 0 and 38                                                      |
| `x.round()`            | `x.round_ties_even()`                 | `2.5`: 3.0 and 2.0                                                      |
| `v as u8`              | `u8::try_from(v)`                     | `300_u32`: 44 and `Err`                                                 |
| `s.contains("outage")` | `s.to_lowercase().contains("outage")` | `"Outages"`: false and true                                             |
| `tier == Tier::Gold`   | `tier >= Tier::Gold`                  | every variant declared after `Gold`                                     |

`#[derive(PartialOrd, Ord)]` on an enum orders the variants by DECLARATION, so `>=` on such an
enum turns the order of the lines in the type definition into behaviour: reordering or inserting
a variant changes every `>=` comparison and the compiler reports nothing (measured: with
`Bronze, Gold, Silver` declared in that order, `Tier::Silver > Tier::Gold` holds).

## Shapes that leave one place to write

The examples show the SHAPE. The rule inside each one (a substring test, a 20 % share, half-up
rounding) is the example's own: where your spec fixes the rule, the spec's rule goes in its place.

**One rule function, every entry point calls it.** The entry points keep their own signatures;
the rule has one body. The test walks every variant and a set of subjects through both entry
points, so a second body, if someone writes one, fails on the input where it differs.

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Tier {
    Bronze,
    Silver,
    Gold,
}

impl Tier {
    pub const ALL: [Tier; 3] = [Tier::Bronze, Tier::Silver, Tier::Gold];
}

/// The one urgency rule. Both entry points call it; neither restates it.
pub fn is_urgent(subject: &str, tier: Tier) -> bool {
    subject.to_lowercase().contains("outage") || tier >= Tier::Gold
}

pub struct FormTicket {
    pub subject: String,
    pub tier: Tier,
}

pub fn urgent_from_form(ticket: &FormTicket) -> bool {
    is_urgent(&ticket.subject, ticket.tier)
}

pub fn urgent_from_mail(subject: &str, tier: Tier) -> bool {
    is_urgent(subject, tier)
}

#[test]
fn both_entry_points_agree_on_every_input_class() {
    let subjects = ["printer jam", "Outage in hall 2", "OUTAGE", "outages again", ""];
    for tier in Tier::ALL {
        for subject in subjects {
            let form = FormTicket { subject: subject.to_owned(), tier };
            assert_eq!(
                urgent_from_form(&form),
                urgent_from_mail(subject, tier),
                "paths disagree on {subject:?} / {tier:?}"
            );
        }
    }
}
```

`Tier::ALL` is a hand-kept list: adding a variant without adding it there leaves the test green
and blind to the new variant. Keep the array next to the enum, and where the crate already
depends on an enum-iteration derive, use that instead.

**One population function, one window type.** Both halves of a ratio start from `counted`, and
the figures and the rule judged beside them are methods of one `Window`, so they cannot rest on
different samples.

```rust
pub struct Ticket {
    pub spam: bool,
    pub breached: bool,
    pub response_secs: f64,
}

/// The tickets that count in any figure. Every figure starts here, never from the raw slice.
pub fn counted(tickets: &[Ticket]) -> impl Iterator<Item = &Ticket> {
    tickets.iter().filter(|t| !t.spam)
}

pub fn breach_rate(tickets: &[Ticket]) -> Option<f64> {
    let total = counted(tickets).count();
    let breached = counted(tickets).filter(|t| t.breached).count();
    (total > 0).then(|| breached as f64 / total as f64)
}

pub struct Window<'a> {
    tickets: Vec<&'a Ticket>,
}

impl<'a> Window<'a> {
    pub fn last(tickets: &'a [Ticket], n: usize) -> Self {
        let all: Vec<&Ticket> = counted(tickets).collect();
        let start = all.len().saturating_sub(n);
        Self { tickets: all[start..].to_vec() }
    }

    pub fn len(&self) -> usize {
        self.tickets.len()
    }

    pub fn is_empty(&self) -> bool {
        self.tickets.is_empty()
    }

    pub fn breached_share(&self) -> Option<f64> {
        let breached = self.tickets.iter().filter(|t| t.breached).count();
        (!self.is_empty()).then(|| breached as f64 / self.len() as f64)
    }

    pub fn at_risk(&self) -> bool {
        self.breached_share().is_some_and(|share| share > 0.20)
    }
}
```

A free function that takes `&[Ticket]` and computes a figure beside these is the shape to
refuse in review: it can only rebuild the population itself.

**One conversion per unit.** A value that is shown in two places (a screen and an export, a log
line and a metric) is converted by one function, so truncation and rounding cannot split:

```rust
/// Agent minutes times the hourly rate, in cents, rounded half away from zero.
pub fn cost_cents(agent_minutes: f64, hourly_rate: f64) -> u64 {
    (agent_minutes * hourly_rate / 60.0 * 100.0).round() as u64
}
```

## What the toolchain reports, and what it does not

- **A field that is assigned but never read gets no warning.** Measured: a private field that is
  initialised and nowhere else touched draws `field ... is never read` (`dead_code`), but once
  any method assigns it (`self.last_digest = digest;`) the warning is gone although nothing reads
  it. State kept "for" a use that does not exist therefore compiles clean. Find it by searching
  the reads yourself (below).
- **rustdoc checks links, not sentences.** A doc comment that names its user as an intra-doc
  link, ``[`Cache::skip_unchanged`]``, draws `unresolved link` under `cargo doc` when that item
  does not exist (`rustdoc::broken_intra_doc_links`, warn by default, measured). The same claim in
  plain backticks or prose is never checked. Write the item a doc comment relies on as a link.
- **A doc example is a test.** A fenced example in a `///` comment runs under `cargo test`
  (measured: an example asserting a wrong result fails the run), so a claim about a result that
  is written as an example cannot drift. A sentence beside it can.
- **Casts and integer division have lints, off by default.** `clippy::cast_possible_truncation`,
  `clippy::cast_sign_loss`, `clippy::cast_precision_loss` (pedantic) and
  `clippy::integer_division` (restriction) are all allow by default and each fired on the lines of
  the table above when switched on (measured). They list every cast, not the pair that
  disagrees: use them as a second candidate list for the review, not as the finding.

## Inputs for the generic review

What the review steps of `bitranox:coding-consistency` run on a Rust change. A hit is a lead to a
row in the pair table, not a finding.

- **Sources 1 to 4, candidate lines** (it listed every planted pair of a test file, measured):

  ```bash
  grep -rnE ' as (u|i|f)(8|16|32|64|128|size)\b|\.round\(\)|\.round_ties_even\(\)|\.floor\(\)|\.ceil\(\)|\.trunc\(\)|as_secs\(\)|as_secs_f64\(\)|as_millis\(\)|to_lowercase\(\)|to_ascii_lowercase\(\)|eq_ignore_ascii_case|\.contains\("' --include='*.rs' src/
  ```

  Group the hits by the quantity they compute, not by file: two hits for one quantity with
  different spellings are a pair.
- **Source 6, a stored value and its readers.** For a field the prose says is kept for a use,
  list every occurrence and separate writes from reads by eye; rustc does not (see above):

  ```bash
  grep -rnE '\blast_digest\b' --include='*.rs' src/
  ```

- **Source 7, public names the diff touches** (`BASE` is the commit the change starts from):

  ```bash
  git diff -U0 BASE -- '*.rs' | grep -E '^[-+]' | grep -vE '^(\+\+\+|---)' | grep -E '\bpub\b'
  ```

  Every `-`/`+` pair of one item is a signature change; a `+` alone is an addition. This reads
  line by line, so a signature wrapped over several lines shows only its first line: open the
  item when a hit ends in `(`. It also lists `pub(crate)` items, which are not a contract outside
  the crate. Compare what it lists with the interfaces the plan or spec names.

## See also

- `bitranox:coding-consistency` - the pairings, the writing rules and the pair table.
- `bitranox:coding-rust-data-architecture` - newtypes and closed enums, which remove whole rows
  (a unit that is a type cannot be mixed up).
- `bitranox:coding-rust` - error, secret and dependency idioms for Rust.
