# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-10-16, fold 23)

- [x] Change (rich-click facade diagnosis): new paragraph after the module-cast facade example - the
      flood arrives with a pyright upgrade, not the edit or a rich-click change; do not bisect or pin
      rich-click; keep `@click.command`/`@click.group` from rich-click; verify `cmd.params[0]` is a
      `RichOption` and `--help` still renders. The "Run pyright first" sentence no longer implies a
      rich-click downgrade could clear it.
- [x] Change (default_factory): new worked example "a mutable-state dataclass with
      `field(default_factory=...)`" after the recursive-alias example - convert a pure mutable-state
      class to a typed `__init__`, keep names, check for `replace`/`asdict`/`fields`, value objects
      stay dataclasses, re-test after a pyright upgrade.
- [x] Change (ValidationError refusals): new `references/validation-error-messages.md` (never
      `str(ValidationError)`; `<dotted loc>: <reason>` lines; `__cause__`; shared formatter; walking
      `__cause__ or __context__`; union-arm tags walked against the input; `(key)` suffix; dedupe;
      `str(item["ctx"]["error"])` for `value_error`). SKILL.md gets a short rule plus pointer after the
      Anti-Patterns block (applies to new code), and STEP C item 5 now names `item["msg"]` /
      `str(item["ctx"]["error"])` instead of stripping the `Value error, ` prefix, pointing at the file.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact): before this edit the skill had no text for the pyright-version
      diagnosis, `@click.command`/`@click.group` staying on rich-click, or the RichOption/--help check;
      did "not mention field(default_factory=...) or the set/dict/list[Unknown] inference anywhere";
      and its only ValidationError text sat in STEP C, "gated to refactors that MOVED where validation
      happens". Behavioural RED replaced on purpose because the rules are in the always-loaded memory
      index of the authoring machine (inherited coverage).
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): rich-click
      diagnosis -> SKILL.md:560-564 "The flood arrives with a PYRIGHT upgrade, not with your edit and
      not with a rich-click change ... so do not bisect your own change or pin rich-click. Keep
      `@click.command` and `@click.group` from rich-click (already fully typed)"; default_factory ->
      SKILL.md:651-657 "it inferred `set[Unknown]` from the bare factory ... convert it to a plain
      class with a typed `__init__` (`self.x: set[str] = set()`) ... first confirm nothing uses it AS
      a dataclass"; ValidationError refusal -> SKILL.md:166-171 "never interpolate
      `str(ValidationError)` into one ... read `references/validation-error-messages.md`", which
      covers the wrapped error (:31-45 "Walk the chain"), union arms (:49-56 "walk `loc` against the
      INPUT"), value_error (:59-61 "show `str(item["ctx"]["error"])`") and the shared formatter
      (:26-27); contradictions: none in the job; step-4 scan of SKILL.md and the new reference: no hit
- [x] Gaps closed or declined: none
- [x] Description measured: unchanged (451 characters)
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
