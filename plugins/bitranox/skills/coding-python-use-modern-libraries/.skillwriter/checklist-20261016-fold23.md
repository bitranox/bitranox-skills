# skill-writer checklist - coding-python-use-modern-libraries (2026-10-16, fold 23)

- [x] Change (version-gated stdlib): new `## Notes` bullet after the PEP 758 bullet - read the
      project's own `requires-python` before importing a stdlib name added after its floor;
      `tomllib`, `enum.StrEnum`, `ExceptionGroup`/`except*` are 3.11 and `typing.override` 3.12; a
      local green run proves nothing, only the oldest CI cell fails; take the version from the docs;
      new projects start at `>=3.11`, an existing project's declared floor binds its CI; the guard
      shape (`TYPE_CHECKING` plus runtime `try`/`except ModuleNotFoundError` backport); `tomllib` is
      read-only and `tomli_w` third-party, so `rtoml` stays the TOML choice.
- [x] Versions measured with `uv run --python 3.10/3.11/3.12 python -I`: all four names absent on
      3.10; `typing.override` still absent on 3.11; all present on 3.12.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact): before this edit "Nothing in it tells the agent to read the
      repo's own requires-python before importing a version-gated stdlib name"; the Enums row said only
      "(`StrEnum` is 3.11+)". Behavioural RED replaced on purpose because the rule is in the
      always-loaded memory index of the authoring machine (inherited coverage).
- [x] GREEN quote-back (fresh-context verifier): SKILL.md "Before importing a stdlib name added
      after the project's floor, read its own `requires-python`"; versions measured with uv run
      --python 3.10/3.11/3.12: tomllib, StrEnum, ExceptionGroup arrive in 3.11, typing.override in
      3.12. The verifier refused the first guard sentence (`except ModuleNotFoundError`); measured on
      3.10 and 3.11: `from typing import override` and `from enum import StrEnum` raise ImportError,
      only `import tomllib` raises ModuleNotFoundError. The sentence now says `except ImportError` or
      typing_extensions, the exceptiongroup backport for the builtin, and a raised floor for
      `except*`.
- [x] Gaps closed or declined: the wrong guard sentence, closed as above; no other gaps.
- [x] Description measured: unchanged (527 characters)
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
