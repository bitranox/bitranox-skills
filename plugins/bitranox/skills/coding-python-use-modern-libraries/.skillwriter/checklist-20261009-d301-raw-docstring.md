# skill-writer checklist - coding-python-use-modern-libraries (2026-10-09, D301 raw docstrings)

New Notes bullet: prefixing a docstring with `r` for ruff D301 changes every escape at once -
loud doctest failures, silent prose changes, and examples that stay green on the wrong input -
with the per-escape rewrite, the `__doc__` equality check, and what D301 does and does not flag.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Home chosen by trigger: this skill's description names "linting and formatting" and its
      table owns the ruff row, and its Notes already hold Python-version and stdlib gotchas.
      devops-bmk triggers on running bmk, not on fixing a lint finding. No skill mentioned D301,
      raw docstrings or the escape trap (searched every SKILL.md and reference file).
- [x] Description unchanged - no routing keyword moved, trigger map needs no rebuild.
- [x] Mechanism measured on CPython 3.14.4 with one docstring converted by prefix only: a doctest
      flips 3 -> 4 (loud); the path renders with doubled backslashes and the `\u` escape as six
      characters (silent); `"a\\nb".split("\\n")` still passes on a literal backslash-n (green but
      wrong). The per-escape rewrite passes both doctests and D301.
- [x] ruff 0.16.10 measured: D301 fires on `\\`, `\t`, `\x07` and `\d`; it does NOT fire on a
      docstring whose only backslashes are `\u`/`\N{}` escapes or a line continuation; so
      escaping the offending backslash (`\d` -> `\\d`) leaves D301 firing. Its `r` fix is offered
      only under `--unsafe-fixes` and applies the prefix alone.
- [x] `__doc__` equality measured as a separating check: prefix-only != original, per-escape
      rewrite == original.
- [x] RED (inert baseline-probe, sonnet and haiku): both arms halved the backslashes correctly;
      both GUESSED whether D301 exempts `\\` and `\N{}`. redcheck --corpus-cascade flagged
      inherited coverage; adjudicated: the matching fact body has its pointer at sibling levels,
      not on this chain, and the CLAUDE.local.md hits are function words.
- [x] GREEN (sonnet and haiku, given the edited file): both produced the correct raw docstring and
      quoted the new text for each step, including that escaping one backslash does not clear D301.
- [x] GREEN diffed against RED both ways: both RED arms proposed comparing old and new `__doc__`,
      no GREEN arm did - a lost result, restored as the required mechanical check. Both RED arms
      also dropped the "Status" line as status prose - an unrelated docs-rule judgement, not
      something this note should teach.
- [x] GREEN gaps worked: non-ASCII replacement character (closed: reword where banned), batch of
      many hits (closed: the `__doc__` check scales). Declined: the `r"""` shape (shown in the
      D301 message itself), a lone invalid escape such as `\W` (covered by "each is literal").
- [x] Fixes verified by quote-back (direct quote or NONE).
- [x] No address, MAC, hostname or machine path added; added lines ASCII only.
- [x] Present tense, no session narrative, no private provenance.
