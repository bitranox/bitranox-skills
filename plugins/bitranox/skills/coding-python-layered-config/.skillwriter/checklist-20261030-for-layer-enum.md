# skill-writer checklist - coding-python-layered-config (for_layer takes the Layer enum)

- [x] Change: SKILL.md, Python API beyond read_config, the "What a deploy sees" paragraph:
      `perms.for_layer("app" | "host" | "user")` becomes `perms.for_layer(Layer.APP)` with the
      `Layer` enum named and its package; a `DeployMode`'s `.value` is stated as the int mode and
      `0o600` as the user layer's default file mode. Mirror twin lib_layered_config/skills/python-layered-config
      carries the same text.
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the edit.
- [x] Every API claim executed against the installed library: `DeployPermissions.defaults()
      .for_layer(Layer.USER).file` prints `0o600`, its `.value` is the int 384, `Layer` is an
      Enum importable from `lib_layered_config`.
- [x] RED (opus, pre-edit paragraph): wrote `perms.for_layer("user")`, guessed `Layer` from outside
      the text, quoted NONE for which enum to pass.
- [x] GREEN round 1 (opus and haiku, edited paragraph): both wrote `perms.for_layer(Layer.USER).file`
      and quoted the governing sentence. Gaps reported: the ambiguous `0o700` example, no way named
      to get an int, the import of `deploy_permissions_from_config` (declined: SKILL.md "Everything
      below is importable from `lib_layered_config`" opens the section), `that_config` (declined:
      defined earlier in the same paragraph, outside the excerpt).
- [x] GREEN round 2 (haiku, final text, 2 cells over both tiers in all): wrote
      `perms.for_layer(Layer.USER).file.value` as the int, quoted both governing phrases; its only
      new gap, the user default, closed by naming `0o600` the user layer's default file mode.
- [x] Round 3 (haiku, the final paragraph): answered `0o600` for the user layer with nothing
      configured and `os.chmod(path, perms.for_layer(Layer.USER).file.value)`, both from quotes. No
      new undecided gap; its remaining notes are the excerpt's cut start and `path`, outside it.
- [x] RED vs GREEN diffed both ways: no baseline result lost; the import cue "from
      `lib_layered_config`" kept after a draft had dropped it.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, prose wrapped to the file's width; repo-gate --mirror-of: in sync.
- [x] Security scan: prose only; no secrets, private host, path or name.
