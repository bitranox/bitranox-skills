# skill-writer checklist - coding-python-layered-config (2026-10-12, lib_layered_config 7.1.6)

Three additions, identical in both copies of the skill:

- a "Designing config files" bullet: write a set as a list and binary data as a base64 string,
  because `!!set` and `!!binary` refuse the file;
- the deploy paragraph: a missing source raises `FileNotFoundError`, a source or `.d` file behind
  a permission wall raises `PermissionError` on every Python, before anything is written;
- the display paragraph: `display_config` and the `read` command quote keys, headers and strings
  the same way, so a key named `"a.b"` reads back as one key.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: one retrieval scenario with three questions (a YAML file using
      `!!set` and `!!binary`, deploy from a source behind a permission wall on two Python versions,
      parsing the `read` output for a key named `"a.b"`), answered only from the skill text, old
      text (RED) against new text (GREEN), inert text-only probe (`bitranox:baseline-probe`), model
      pinned to sonnet. Both arms received the same excerpt: the YAML bullets of "Designing config
      files", the "Deploying and scaffolding" paragraph and the first lines of "Display and
      logging".
- [x] Inherited context checked with `redcheck --corpus-cascade` over the source repo: 1494
      documents read, verdict "inherited coverage" on shared vocabulary only. Adjudicated against
      the source: none of the named files mentions `!!set`, `!!binary`, a walled deploy source or
      the `read` output's quoting (the one `a.b` hit is TOML table syntax in an unrelated note), so
      the behavioural arm stands.
- [x] Scope: one bullet and two sentences; frontmatter untouched, no routing keyword moved.
- [x] Every claim executed against the 7.1.6 code before it was written: `!!set` and `!!binary`
      refuse the file through `YAMLFileLoader` and `read_config` (`LayerLoadError`), while
      timestamps and dates load and serialise (tests `test_yaml_unserialisable_tags.py`); a walled
      source raises `PermissionError` and a missing one `FileNotFoundError`, and a `.d` directory
      that can be listed but not entered raises `PermissionError`, both before any destination is
      written, on Python 3.10 to 3.14 (`test_deploy_permission_wall.py`, `make test-all`); the
      `read` output for keys `"a.b"`, `""`, `"k=v"` and a table `"sec tion"` parses back with rtoml
      to the configuration it shows (`test_cli_read_toml_text.py`).
- [x] The deploy sentence names only the source and `.d` cases as raising before anything is
      written: with several targets, a walled later destination raises after an earlier one was
      written, so the text does not claim it for destinations.

## RED (old text)
- [x] `!!set` / `!!binary`: NONE - guessed refusal by analogy with `!!omap`, replacements unstated.
- [x] Walled deploy source: NONE - the excerpt names no exception.
- [x] `read` output key `"a.b"`: NONE - the excerpt says only that `display_config` quotes keys.

## GREEN (new text)
- [x] `!!set` / `!!binary`: refused, write a list and a base64 string; governing line quoted:
      "**Write a set as a list and binary data as a base64 string, never `!!set` or `!!binary`**".
- [x] Walled deploy source: catch `PermissionError`, the same on 3.12 and 3.14, a missing source
      `FileNotFoundError`; governing line quoted: "A missing source raises `FileNotFoundError`; a
      source or a file in its `.d` directory behind a permission wall raises `PermissionError` on
      every Python, before anything is written."
- [x] `read` output key `"a.b"`: one key; governing line quoted: "both quote keys, headers and
      strings the same way, so a key named `"a.b"` reads back as one key."

## REFACTOR
- [x] Both arms asked for a `Skill gaps` section; both lists recorded here.
- [x] GREEN gap declined - which exception a refused YAML file raises: the "Errors" section of the
      skill says a layer file that cannot be parsed surfaces as `LayerLoadError`.
- [x] GREEN gap declined - how `PermissionError` relates to `FileNotFoundError`: Python's own
      exception hierarchy, not this library's.
- [x] GREEN gap declined - the exact quoted form in the `read` output: the sentence states the
      read-back property a parser needs; the form is TOML's.
- [x] GREEN diffed against RED in both directions: RED produced no answer GREEN lost.

## Quality
- [x] No session narrative or private provenance; no addresses, hosts or paths added.
- [x] Mirror level with the source repo's copy except the `name:` line.
- [x] Plugin version bumped (8.13.1 to 8.13.2) with a CHANGELOG entry.
