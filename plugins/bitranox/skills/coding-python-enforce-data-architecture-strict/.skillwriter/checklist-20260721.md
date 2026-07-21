# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-07-21, add "define types, never suppress/exclude the checker")

Change: add a section establishing that the same discipline forbidding stringly-typed values also
forbids silencing the type checker - DEFINE the missing types (annotation, then a typed facade
Protocol+cast or a local .pyi stub) rather than a per-file rule-off, an `exclude`, or a bare
`# type: ignore`; a narrow rule-specific `# pyright: ignore[rule]` with a remove-when reason is the
documented last resort. Worked example: the rich-click module-cast Protocol facade (partially-typed
option/argument/version_option decorators). Origin: a fleet-wide sweep where every rich-click repo
had carved out the stub gap with `# pyright: ignore[reportUnknownMemberType]` wrappers.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: baseline subagent under a 20-min deadline; a harder variant admits it would fall back to a
      per-file suppression + follow-up ticket. Real-world baseline: the fleet's typed_click.py files
      all silenced the rule with `# pyright: ignore[reportUnknownMemberType]` rather than typing it.
- [x] GREEN: added the section + the module-cast Protocol facade example + three suppression-specific
      rationalization counters. Verified with the skill present: the subagent rejects the reviewer's
      "per-file rule-off is standard" push under deadline and defines the types instead.
- [x] Verified the facade against ground truth: `cast` is a runtime no-op, so the wrappers forward to
      rich-click's own decorators (RichOption preserved); casting the module (not the function or a
      from-import) is what moves the flagged access onto a typed surface (confirmed in a pyright-strict
      scratch project: module-cast -> 0 errors; wrapper-calls-`_rc.option` / `from rich_click import
      option` -> still flagged).
- [x] CSO description: unchanged - the trigger (enforce a strict data architecture, make a data flow
      type-safe end to end) already covers this addition; no workflow summary added.
- [x] Security scan: prose/example change only - no secrets, credentials, hostnames, private paths.
- [x] Docs describe current state: no legacy/migration narrative; the example is generic (rich-click).
- [x] Version bumped: plugins/bitranox/.claude-plugin/plugin.json 5.96.2 -> 5.96.3 (PATCH, content edit
      to an existing skill; no registry/taxonomy/README change since no skill was added or renamed).
