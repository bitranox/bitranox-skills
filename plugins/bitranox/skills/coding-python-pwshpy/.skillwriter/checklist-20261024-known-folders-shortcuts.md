# skill-writer checklist - coding-python-pwshpy (2026-10-24, known folders, shortcuts, update categories)

- [x] Change: the skill names the pwshpy 1.7 surface for known folders and Windows shortcuts. Three
      translation rows (`[Environment]::GetFolderPath('Desktop')`, WScript.Shell `CreateShortcut`
      write and read), a paragraph on their inputs (the six `KnownFolder` values, exact case in the
      library and any case on the CLI, `None` where pwsh returns `""`, `Programs` off Windows, the
      absolute or `%NAME%\` target, `arguments` as an argv list, the up-front length limits, the
      expansion refused by Windows at SetPath, `force=True`), `KnownFolder` and `ShortcutInfo` in
      the public-name list, a CLI index line, and the "When to use" list. Separately, one sentence on
      selecting Windows Updates by `category_details[].category_id` with a ready `.where()`
      predicate.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`); this agent loaded the skill.
- [x] RED, known folders and shortcuts: reference content (names of a library release), so a text
      check of the pre-change file. `get_known_folder`, `new_shortcut`, `get_shortcut`,
      `KnownFolder`, `ShortcutInfo`: 0 hits each.
- [x] RED, update categories: text check 0 hits for `category_id` / `category_details` / any
      mention of categories. Behavioural arm, opus and haiku, given the pre-change Windows Update
      row and paragraph and asked for a `.where()` keeping only security updates on machines in
      several languages: both arms had to invent the field (`category_ids`, a placeholder) and said
      so in their gaps list.
- [x] GREEN, update categories, opus and haiku, the new paragraph pasted as the text under test: both
      wrote `.where(lambda u: any(c.category_id == "0fa1201d-4330-4fa8-8ae9-b877473b6441" for c in
      u.category_details))` and quoted the governing sentence verbatim (2 tiers, 2 cells).
- [x] GREEN text check, known folders and shortcuts: every name above is present in the skill.
- [x] Every example executed against the package on Linux: `ps.get_known_folder(KnownFolder.DESKTOP)`
      and `ps.get_known_folder("MyDocuments")` (the XDG folder, not `~/Desktop`), `KnownFolder.PROGRAMS`
      raising `PlatformUnsupportedError`, `ps.new_shortcut(...)` raising `PlatformUnsupportedError`
      off Windows, `pwshpy get_known_folder desktop` (exit 0), and the update predicate over a
      `WindowsUpdate` holding one `UpdateCategory` with a localized name (True). The `.lnk`
      round trip is pinned by the package's own Windows oracle tests against WScript.Shell.
- [x] Gaps declined (GREEN arms, excerpt only): the default `criteria` and its syntax, the timeout
      default and error (the skill's errors section names `OperationTimeoutError` for
      `get_windows_update`; `pwshpy get_windows_update --help` and the docstring give the default);
      whether other categories also carry security fixes (a judgement the skill leaves to the
      caller; the record names the Security Updates GUID); whether `category_id` is always lower
      case (the record guarantees it); the `exec` timeout sentence beside the paragraph (it is about
      `ps.exec`, unchanged); fleet-wide remote execution (outside this skill).
- [x] GREEN diffed against RED both ways: no row or sentence removed; the paragraph keeps the
      `__main__` guard, the whole-result note and the `exec` sentence.
- [x] Description measured: unchanged (no frontmatter line in the diff).
- [x] Mirror: the same body as the pwshpy repo's `skills/using-pwsh/SKILL.md`; the only difference
      is the `name:` line.
- [x] Security: no host, address, credential or private path added; the GUID is Microsoft's public
      Security Updates classification id.
