# skill-writer checklist - coding-python-use-modern-libraries (2026-07-29, ipscout row)

Change: add one routing row for the ICMP ping / reachability / traceroute task, pointing at
`ipscout` and listing what to reach for instead of (`icmplib`, `scapy`, `subprocess` around
`ping`/`tracert`), with a cross-reference to `bitranox:coding-python-network-probe` for the detail.
Shipped in plugin 5.99.0.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the table had no row for this task at all, so an agent consulting it for a network-probe
      question got no steer and fell through to its own recall - which selected `icmplib` and
      claimed, wrongly, that `privileged=False` avoids admin on Windows.
- [x] GREEN: with the row present the task routes to ipscout, and the "instead of" column names
      icmplib explicitly with the reason (forces raw sockets on Windows, needs Administrator), so
      the wrong answer is refused by name rather than merely left unmentioned.
- [x] Claim verified from source before it was written down: icmplib `sockets.py` sets
      `self._privileged = privileged or PLATFORM_WINDOWS`, then opens `SOCK_RAW`.
- [x] Placement: inserted before the `Layered / cross-platform app config` row, keeping the table's
      existing grouping intact. No other row touched.
- [x] Scope: shared/general - no machine-specific content.
- [x] Security scan: one prose table row, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: unchanged (body table addition, frontmatter untouched).
- [x] Token budget: one row added to an existing routing table.

# skill-writer checklist - coding-python-use-modern-libraries (2026-07-29, lint + type-check rows)

Change: the `Type checking` row named `mypy` with an empty `Avoid` cell, and the table had no
lint/format row at all. Row swapped to `pyright` in strict mode (mypy, untyped code and blanket
`# type: ignore` move into `Avoid`), and a `Lint / format` row added for `ruff` (`ruff check` +
`ruff format`) replacing the flake8/black/isort/pylint/pyupgrade/autoflake stack. The frontmatter
description gains "linting and formatting" so the router sees the new task. Shipped in plugin
5.100.1.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, first attempt, FALSE PASS: a haiku agent pointed at the SKILL.md path with tools
      available browsed the surrounding repo, absorbed the bmk/CI conventions from sibling files,
      and answered ruff + pyright + bandit + pip-audit - an answer this reference does not contain.
      Discarded per the "a RED can falsely pass" rule; the ambient repo was the widening factor.
- [x] RED, isolated re-run (haiku, no tools, table excerpt pasted, answer withheld): the agent
      answered dev package `mypy`, and "not covered by the reference" for linting, formatting and
      the CI commands. That is the gap, reproduced cleanly.
- [x] GREEN (haiku, no tools, same scenario, edited excerpt): the agent answered `ruff` + `pyright`,
      commands `ruff check .`, `ruff format --check .`, `pyright` in strict mode. No mypy.
- [x] Verified against ground truth, not preference: of the 27 project dirs under `public/apps/`
      and `public/libs/`, 20 pyprojects reference `pyright` and 20 reference `ruff`; `mypy` appears
      in none. `bmk make test` runs ruff plus pyright; CI runs `uv run pyright`.
- [x] Cross-skill consistency: coding-python-clean-architecture, process-review-enhance-code-quality
      and coding-python-enforce-data-architecture-strict already prescribe pyright strict, so this
      table was the one dissenting voice. Now aligned.
- [x] The skill's own "Adding an entry" rules honoured: both rows carry a why (contested picks),
      name what they replace in `Avoid`, and stay on one line.
- [x] Table realigned by the reformat-md-tables hook on save; a `reformat_tables.py` re-run reports
      Unchanged.
- [x] Derived artifacts regenerated: build_skill_triggers.py (map already in sync, no diff) and
      build_skill_docs.py (docs/skills.md description line updated). The skill count is unchanged,
      so the README count needs no edit.
- [x] CSO description: still triggering conditions only - the added words are one more task keyword
      in the existing task list, no workflow summary.
- [x] Token budget: 1194 words, a reference skill whose body is a routing table plus short notes;
      no supporting files.
- [x] Security scan: two table rows of public tool names, ASCII only, no secrets, hosts, internal
      paths or PII.
