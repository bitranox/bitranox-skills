# skill-writer checklist - meta-skill-writer (2026-07-25, bare-env import rule)

Change: add one authoring rule to "Ship tests for every script" (5.99.3) - a bundled script must
IMPORT in a bare environment, because the contribution gate / plain pytest does not provision a
script's PEP 723 deps (only `uv run` does); guard third-party imports with a stdlib fallback and
verify in a deps-free venv.

- [x] Skill type: reference / authoring guidance - validated by a real application (a shipped incident), not a synthetic scenario
- [x] RED (real): this session shipped `compuse-toolbox` `jsonl_grep`+`transcript_tail` with a hard `import orjson`; local + `uv run` were green, CI failed with `ModuleNotFoundError` on the bare-env gate. The live failure IS the baseline the rule would have prevented.
- [x] GREEN: orjson-or-stdlib fallback fixed CI (5.99.1), reproduced + verified in a fresh deps-free venv; the new rule now instructs exactly that, with the deps-free-venv verification command
- [x] Placement: appended to the existing "Ship tests for every script" bullet list, next to "Keep scripts import-safe" (same concern: a script that cannot be imported cannot be tested)
- [x] Description unchanged (triggers only) - no skill_triggers.json / catalog regen needed
- [x] Body edit only; no @ links; cross-refs intact; ASCII only
- [x] Receipt held this session (skill_receipt.py start meta-skill-writer)
- [x] Security scan: prose-only edit, no secrets/paths/PII
- [x] Also captured as a memory entry (reference-bundled-skill-scripts-must-import-in-a-bare-env-...) so it is recall-able cross-session
- [x] repo-gate --ci green
