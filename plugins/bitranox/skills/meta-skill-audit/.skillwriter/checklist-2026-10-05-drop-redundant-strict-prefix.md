# Skill-writer checklist: drop redundant BITRANOX_RUN_PYTHON_STRICT=1 prefix (2026-10-05)

Scope: the Procedure section prefixed every launch with `BITRANOX_RUN_PYTHON_STRICT=1`. Verified
against `run-python.sh`: a CLI call with no `--hook` flag already exits 3 loudly on a missing
script by default (`_hook_mode` is unset for a non-hook call, so the loud `_degrade_rc` stays in
effect without the env var). The variable only changes behaviour for a `--hook` launch, which
these scripts never use. The prefix was therefore inert for every command the Procedure actually
shows. Dropped the prefix and reworded the sentence to state the real default/override
relationship instead of claiming the override is needed.

## Verification

- [x] Claim re-checked against the current shim source (`run-python.sh`), not assumed from the
      skill's own prior wording.
- [x] No new trigger, rule, or workflow step added - a redundant flag removed from an existing
      command line; the launch shape (`bash hooks/run-python.sh <script> [args]`) and every
      numbered step are unchanged, so no RED/GREEN pressure test applies.
- [x] Frontmatter still parses (`name`/`description` only); `description` unchanged, 416
      characters, well under the 1024 cap.
- [x] `grep BITRANOX_RUN_PYTHON_STRICT` over this SKILL.md after the edit shows exactly one
      remaining mention, in the corrected explanatory sentence - no other command line in the
      file still carries the now-redundant prefix.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, address, hostname, or real machine path added.
- [x] Added text is ASCII only (no em/en dashes or curly quotes).
