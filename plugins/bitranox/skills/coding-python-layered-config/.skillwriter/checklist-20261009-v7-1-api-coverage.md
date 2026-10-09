# skill-writer checklist - coding-python-layered-config (2026-10-09, lib_layered_config 7.1.0)

lib_layered_config 7.1.0 adds app-declared not-sensitive keys (`read_config*(not_sensitive=...)`,
`NotSensitiveKeys`, `is_sensitive_at`, `Config.get_redacted`). A check of the package's `__all__`
against the skill text found 20 public callables, enums and exceptions the skill never named
(18 of them already missing at 7.0.1), and the CLI's `fail` command missing from the command
table. This change adds a "Python API beyond read_config" section, the `fail` row, and the
`not_sensitive` sentences.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: retrieval scenarios answered only from the skill text, old text
      (RED) against new text (GREEN), same five questions, inert text-only probe
      (`bitranox:baseline-probe`), model pinned to sonnet. The probe received a condensed copy:
      sections without any of the 20 names were cut from both arms alike.
- [x] Mechanical coverage check against the artifact (immune to inherited context): every name in
      `lib_layered_config.__all__` that is callable, an Enum or an exception must appear in the
      text, and every command in the Click group must appear in backticks. Before: 20 names and
      `fail` missing. After: none.
- [x] Scope: one new section, one CLI row, one sentence; frontmatter untouched (description 401
      characters, unchanged), no routing keyword moved.
- [x] Every claim executed against the installed 7.1.0 before it was written: broken TOML from
      `read_config` raises `LayerLoadError` (a `ConfigError`); `validate_profile_name("../x")`
      raises `ValidationError` (a `ValueError`); `is_valid_profile_name` returns booleans;
      `is_sensitive("key")` is False; `redact_mapping` accepts a `NotSensitiveKeys`;
      `deploy_config` with `file_mode` and `set_permissions=False` raises `DeployModeError`;
      `generate_examples` returns a list of paths; `display_config(..., output_format=JSON)` prints
      redacted JSON; `get_logger()` is a `logging.Logger`; `DeployAction.CREATED == "created"` is
      False and `.value == "created"` is True; a `bind_trace_id` value reaches
      `record.context["trace_id"]` for a direct log call, while every `read_config` record carries
      None.

## RED (old text)
- [x] Exception for broken TOML: NONE (guessed `except Exception`).
- [x] Redacting a plain dict with a declared key: NONE (fell back to the `Config` route).
- [x] Deploying from Python and reading created vs kept: NONE.
- [x] Boolean profile-name check: NONE (guessed the name from convention).
- [x] Logging handler and trace id: NONE.

## GREEN (new text)
- [x] All five answered by direct quote: `LayerLoadError`, `redact_mapping(data, not_sensitive=...)`,
      `deploy_config(...)` returning `DeployResult`s, `is_valid_profile_name`, `get_logger` and
      `bind_trace_id`.

## REFACTOR
- [x] Every dispatch asked for a `Skill gaps` section; each reply's list is recorded here.
- [x] Gap closed: `.action` type unspecified - the GREEN probe compared `r.action == "created"`,
      which is always False for the plain Enum. The text now says `.action` is an enum, compare
      `.action.value`, and names the four values.
- [x] Gap closed: `deploy_config` source and container type - `source` is the path of the file to
      copy, and the return value is a list.
- [x] Gap closed: `get_logger()` return type and where the trace id appears - a stdlib
      `logging.Logger`; every record has `record.context["trace_id"]` plus the event's fields.
- [x] Gap closed: trace-id scope - a `ContextVar`, and `read_config*` resets it to None on entry, so
      its own events carry None (measured; the reset is filed as a library defect in
      `libs/lib_layered_config/OPEN-WORK.md`, and the sentence goes when it is fixed).
- [x] Gap closed: whether `redact_mapping` takes a `NotSensitiveKeys` - it does, stated.
- [x] Gap declined: exception attributes (path, message fields) - the classes carry a message only.
- [x] Gap declined: `read_config_raw` signature - the "Load config" section, cut from the probe's
      condensed copy, covers it.
- [x] Gap declined: whether a binding made before `read_config` is restored afterwards - it is not,
      and that is the filed defect itself.
- [x] Quote-back on the touched questions (`.action` comparison, trace id under `read_config`,
      `NotSensitiveKeys` in `redact_mapping`): each answered by a direct quote of the new text.
- [x] RED vs GREEN diffed both ways: RED answered nothing, so no result was lost.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Tables canonical (`reformat_tables.py --check` unchanged); no typographic tells.
- [x] Twin `libs/lib_layered_config/skills/python-layered-config/SKILL.md` (released in 7.1.0)
      carries the same text; the two differ only in the `name:` line.
