# skill-writer checklist - docs-convert-markitdown (2026-09-27, plugin recipe and model dates)

Scope: a rewritten "Creating Plugins" recipe in `references/api_reference.md`, and a date on every
model recommendation in `SKILL.md`, `references/api_reference.md`, `assets/example_usage.md` and
the `--help` text of `scripts/convert_with_ai.py`. The frontmatter `description` is unchanged, so no
routing keyword moved and no derived artifact needs regenerating.

Why the RED/GREEN is an executed probe rather than a subagent arm: both changes are factual
corrections to a reference skill installed on this machine, so a subagent would answer from the
installed wording, not the file under test. The recipe is runnable, so it is tested by building it.

- [x] WRONG - the plugin recipe could not produce a working plugin. markitdown 0.1.8 (the current
      PyPI release) loads entry points from group `markitdown.plugin` and calls the loaded
      object's `register_converters(markitdown, **kwargs)`; the recipe used group
      `markitdown.plugins`, pointed at a converter class, defined `convert(stream,
      file_extension)` with no `accepts()`, and built `DocumentConverterResult(text_content=...)`,
      whose constructor is `(markdown, *, title=None)`.
- [x] RED: the recipe's `setup.py` and `converter.py` blocks, extracted verbatim from the previous
      text and installed into a fresh venv with markitdown 0.1.8: `markitdown --list-plugins` says
      "No 3rd-party plugins installed", `MarkItDown(enable_plugins=True).convert("sample.custom")`
      returns the file text unchanged (`'hello custom\n'`, title None) and raises no warning.
- [x] GREEN: the new `pyproject.toml` and `markitdown_my_plugin/__init__.py` blocks, extracted
      verbatim from the edited file and installed the same way: `--list-plugins` lists
      `my_plugin (package: markitdown_my_plugin)`, the Python call returns
      `'# Converted Content\n\nhello custom\n'` with title `'My Document'`, and `markitdown -p
      sample.custom` prints the same. No warnings.
- [x] The text's claim about the second failure mode was run too: the correct group pointing at
      the converter CLASS loads it, converts nothing, and warns `Plugin '<class ...>' failed to
      register converters`.
- [x] `__plugin_interface_version__` is described as what it is: the upstream sample plugin
      declares it, and markitdown 0.1.8 has no reader for it (grep of the installed package).
- [x] WRONG - four "recommended" model lines carried no date while the model IDs they name
      change; one ID the list offered, `google/gemini-3-pro-preview`, is no longer served by
      `https://openrouter.ai/api/v1/models`. Every recommendation now reads "as of 2026-09" or
      points at the one dated list in `references/api_reference.md`, which names three IDs checked
      present with image input on that endpoint, and ships the command that lists current
      image-capable IDs (executed: exit 0, 288 IDs, all three listed IDs among them, the retired one
      absent).
- [x] `convert_with_ai.py`: help text only; the `--model` default is unchanged. New test
      `test_help_dates_every_model_it_names` failed first ("Recommended" present) and passes after.
- [x] Skill tests: CI dependency set 88 passed, 9 skipped; with the real markitdown 0.1.8 and
      python-pptx added, 97 passed.
- [x] An example comment that contradicted its own code ("use GPT-4o" above a Claude model) now
      describes what the code does.
- [x] Description unchanged (not in the diff).
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] No session narrative or private provenance; no machine paths or addresses added.
- [x] Added lines are ASCII only; table reformatter reports every edited file unchanged.
