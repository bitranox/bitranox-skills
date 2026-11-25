---
name: coding-python-consistency
description: Use when Python code is reviewed or written for consistency - duplicated logic whose copies may differ, such as statistics.quantiles with and without method="inclusive", round() beside int() or Decimal ROUND_HALF_UP, floor division beside int(a / b), lower() beside casefold(), a substring test beside a word-boundary regex, an argparse default beside a function default - or when an attribute is assigned but never read, a docstring or notes file names a use that does not exist, or a public def, class or __all__ entry changed beyond what the plan lists. Loads alongside bitranox:coding-consistency.
---

# Consistency in Python

Python mechanisms for the consistency lens: the standard-library calls that make two computations
of "the same" value differ, the shapes that leave only one computation to write, and the searches
for the review.

## Load bitranox:coding-consistency alongside this skill

The language-neutral text lives there, once: the seven pairings, the four things a pair is
compared on (set, rule, window, unit), the rules for writing a change, and the pair table a
review returns. Every "pairing", "source N" and "pair table" in this skill names that skill's
text. This skill ships no scripts.

Every code example and every "measured" value below ran on CPython 3.14.4 with the standard
library only. Other Python versions were not run: re-run a row on the interpreter of the project
under review before quoting its numbers in a finding.

---

## Same value, two results

Each row is a pair that reads as equivalent and returns different results. When a change holds
both spellings for one quantity, that is a `DISAGREE` row in the pair table (rule or unit cell),
and the finding's concrete input is in the last column, whose two results stand in the order of
the two code columns.

| One path writes                      | The other writes                                         | They differ on (measured)                                       |
|--------------------------------------|----------------------------------------------------------|-----------------------------------------------------------------|
| `statistics.quantiles(xs, n=20)[18]` | `statistics.quantiles(xs, n=20, method="inclusive")[18]` | `xs = 1.0 .. 40.0`: 38.95 and 38.05                             |
| either of those                      | `sorted(xs)[len(xs) * 95 // 100]`                        | the same `xs`: 39.0                                             |
| `statistics.median(xs)`              | `sorted(xs)[len(xs) // 2]`                               | `[1, 2, 3, 4]`: 2.5 and 3                                       |
| `round(x)`                           | `Decimal(...).quantize(Decimal("1"), ROUND_HALF_UP)`     | `2.5`: 2 and 3 (`round` rounds half to even; `round(0.5)` is 0) |
| `int(x * 100)`                       | `round(x * 100)`                                         | `x = 0.29`: 28 and 29 (`0.29 * 100` is `28.999999999999996`)    |
| `a // b`                             | `int(a / b)`                                             | `-7, 2`: -4 and -3                                              |
| `ms // 1000`                         | `ms / 1000`                                              | `1999`: 1 and 1.999                                             |
| `"outage" in s`                      | `"outage" in s.casefold()`                               | `"Outage"`: False and True                                      |
| `s.lower() == t.lower()`             | `s.casefold() == t.casefold()`                           | `"STRASSE"` and `"straße"`: False and True                      |
| `"outage" in s.casefold()`           | `re.search(r"\boutage\b", s, re.IGNORECASE)`             | `"Outages in hall 2"`: True and no match                        |
| `"strasse" in s.casefold()`          | `re.search("strasse", s, re.IGNORECASE)`                 | `"STRAßE"`: True and no match                                   |

The default `method` of `statistics.quantiles` is `"exclusive"`. A percentile written without
`method=` in one module and with `method="inclusive"` in another is two rules for one figure, and
neither call looks wrong by itself.

## Shapes that leave one place to write

The examples show the SHAPE. The rule inside each one (a substring test, a 20 % share, half-up
rounding) is the example's own: where your spec fixes the rule, the spec's rule goes in its place.

**One rule function, every entry point calls it.** The doctest pins the rule; the parametrized
check below walks every tier and a set of subjects through both entry points, so a second body,
if someone writes one, fails on the input where it differs.

```python
from __future__ import annotations

import argparse
import inspect
import itertools
import statistics
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import IntEnum

WINDOW_TICKETS = 200


class Tier(IntEnum):
    BRONZE = 0
    SILVER = 1
    GOLD = 2


def is_urgent(subject: str, tier: Tier) -> bool:
    """The one urgency rule; both entry points call it.

    >>> is_urgent("Outage in hall 2", Tier.BRONZE)
    True
    >>> is_urgent("printer jam", Tier.SILVER)
    False
    """
    return "outage" in subject.casefold() or tier >= Tier.GOLD


def urgent_from_form(form: dict[str, str]) -> bool:
    return is_urgent(form["subject"], Tier[form["tier"]])


def urgent_from_mail(subject: str, tier_header: str) -> bool:
    return is_urgent(subject, Tier[tier_header])


def check_entry_points_agree() -> None:
    subjects = ["printer jam", "Outage in hall 2", "OUTAGE", "outages again", ""]
    for subject, tier in itertools.product(subjects, Tier):
        by_form = urgent_from_form({"subject": subject, "tier": tier.name})
        by_mail = urgent_from_mail(subject, tier.name)
        assert by_form == by_mail, f"paths disagree on {subject!r} / {tier.name}"
```

Iterating the enum itself (`itertools.product(subjects, Tier)`) keeps the check complete when a
member is added; a hand-written list of tiers would not.

**One population, one window type.** The figures and the rule judged beside them are methods of
one frozen `Window`, built in one place from the counted items, so they cannot rest on different
samples.

```python
@dataclass(frozen=True, slots=True)
class Ticket:
    spam: bool
    breached: bool
    response_secs: float


@dataclass(frozen=True, slots=True)
class Window:
    """One population; every figure and every rule over it is a method here."""

    tickets: tuple[Ticket, ...]

    @classmethod
    def last(cls, tickets: list[Ticket], n: int = WINDOW_TICKETS) -> Window:
        counted = [t for t in tickets if not t.spam]
        return cls(tuple(counted[-n:]))

    def breached_share(self) -> float | None:
        if not self.tickets:
            return None
        return sum(t.breached for t in self.tickets) / len(self.tickets)

    def at_risk(self) -> bool:
        share = self.breached_share()
        return share is not None and share > 0.20

    def p95_secs(self) -> float | None:
        secs = [t.response_secs for t in self.tickets]
        if len(secs) < 2:
            return None
        return statistics.quantiles(secs, n=20, method="inclusive")[18]
```

A module-level function that takes the raw ticket list and computes a figure beside these is the
shape to refuse in review: it can only rebuild the population itself.

**One conversion per unit.** A value shown in two places (a screen and an export, a log line and
a metric) is converted by one function, so two rounding rules cannot split it:

```python
def cost_cents(agent_minutes: float, hourly_rate: float) -> int:
    """Agent minutes times the hourly rate, in cents, rounded half up."""
    cents = Decimal(str(agent_minutes)) * Decimal(str(hourly_rate)) / 60 * 100
    return int(cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
```

Measured: `cost_cents(0.3, 5.0)` is 3, while `round(0.3 * 5.0 / 60 * 100)` is 2.

**One default.** A default that a function and a command-line option both carry is written once
and referred to; two literals are a pair waiting to differ.

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="board")
    parser.add_argument("--last", type=int, default=WINDOW_TICKETS)
    return parser


def check_one_default() -> None:
    cli_default = build_parser().parse_args([]).last
    assert cli_default == inspect.signature(Window.last).parameters["n"].default
```

## What Python checks, and what it does not

- **Nothing reports an attribute that is assigned and never read.** `self._digest = ...` with no
  reader raises nothing at run time, and pyright 1.1.414 in its default mode reports 0 errors and
  0 warnings for it (measured). State kept "for" a use that does not exist is found only by
  listing its readers (below).
- **A doctest is a test of the claim; the sentence around it is not.** An example in a docstring
  runs under `python -m doctest module.py` or `pytest --doctest-modules`, so a claim about a
  result that is written as an example cannot drift. Prose in the same docstring can.
- **A keyword-only parameter without a default breaks every existing call.** Adding
  `*, currency: str` to a public function raises `TypeError` at each caller that was not edited;
  the callers outside the repository are the ones no test runs.

## Inputs for the generic review

What the review steps of `bitranox:coding-consistency` run on a Python change. A hit is a lead to
a row in the pair table, not a finding.

- **Sources 1 to 4, candidate lines** (it listed every planted pair of a test package, measured):

  ```bash
  grep -rnE 'quantiles\(|median|\bround\(|\bint\(|//|ROUND_|\.lower\(\)|\.casefold\(\)|re\.(search|match|compile)\(|default=' --include='*.py' src/
  ```

  Group the hits by the quantity they compute, not by file: two hits for one quantity with
  different spellings are a pair. Then list the module-level constants and check each literal
  in a formula against them and against the configuration.
- **Source 6, a stored value and its readers.** For an attribute the prose says is kept for a
  use, list every occurrence and separate writes from reads by eye:

  ```bash
  grep -rnE '\b_digest\b' --include='*.py' src/
  ```

- **Source 7, public names the diff touches** (`BASE` is the commit the change starts from):

  ```bash
  git diff -U0 BASE -- '*.py' | grep -E '^[-+](__all__|(async )?def [a-z]|class [A-Z])'
  ```

  Every `-`/`+` pair of one name is a signature change; a `+` alone is an addition. This reads
  line by line and only module-level names: a signature wrapped over several lines shows only
  its first line, and a public method of a class is indented and not listed, so open the class
  when its body is in the diff. Compare what it lists with the interfaces the plan or spec names.

## See also

- `bitranox:coding-consistency` - the pairings, the writing rules and the pair table.
- `bitranox:coding-python-data-architecture` - enums and typed models, which remove whole rows
  (a status that is an enum member cannot be spelled two ways).
- `bitranox:process-test-design` - a consistency test enumerates every entry, including the ones
  the change did not touch.
