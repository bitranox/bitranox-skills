---
name: files-edit-yml
description: Use when creating, generating, editing, or validating a YAML file (*.yml/*.yaml) - app config, Traefik dynamic config, Docker Compose, Kubernetes manifests, CI pipelines, Ansible - especially when modifying an existing file or producing one programmatically. Use instead of hand-typing YAML or editing it with sed/regex.
---

# Edit YAML with a Python library, never by hand

## Overview

Build and edit YAML by round-tripping through a Python data structure with a YAML library, then
re-load to confirm it parses. Editing YAML as raw text (typing it, `sed`, regex, string
concatenation) produces indentation and quoting errors that break the file or, worse, load as the
wrong structure. A library serialization is syntactically correct by construction; re-loading it
verifies it.

## Library

- **`ruamel.yaml`** - preferred for editing an EXISTING file: it round-trips and preserves comments
  and key order (YAML 1.2). It does NOT preserve LAYOUT out of the box - see "Round-tripping keeps
  comments, not layout" below, and match the file's indent and null style before you dump.
  `pip install ruamel.yaml`.
- **`PyYAML`** (`import yaml`) - fine for generating a NEW file or when comments do not matter;
  `yaml.safe_load` / `yaml.safe_dump`. Note: it drops comments and reorders, so do not use it to
  round-trip a hand-commented config.

See **bitranox:coding-python-use-modern-libraries** for the wider list. Reach for the structured editors
for the other formats too: **bitranox:files-edit-json**, **bitranox:files-edit-toml**, **bitranox:files-edit-xml**.

**Safety:** never load untrusted YAML with PyYAML `yaml.load()` or a custom `Loader` - the
`!!python/object` tags execute arbitrary code. Use `yaml.safe_load`. `ruamel.yaml`'s default
`YAML()` is the safe round-trip loader (only `YAML(typ="unsafe")` is dangerous).

## Pattern: load -> edit the structure -> dump -> re-load to validate

```python
import io
from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML()                      # round-trip mode: keeps comments + order
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)   # MATCH the file; the default dedents block sequences
# A file that writes explicit `key: null` or `key: ~` also needs its null spelling pinned:
# see "Match the file's null style" below. A file with bare `key:` nulls needs nothing.
path = Path("traefik/dynamic/services.yml")

# prove the settings match the file BEFORE editing: an unedited round trip must change nothing
buf = io.StringIO()
yaml.dump(yaml.load(path), buf)
assert buf.getvalue() == path.read_text(encoding="utf-8"), "settings reflow the file - fix them first"

data = yaml.load(path)             # parse existing file into Python objects
data["http"]["routers"]["media"] = {
    "rule": "Host(`media.example.com`)",
    "entrypoints": ["websecure"],
    "service": "media",
    "tls": True,
}

with path.open("w", encoding="utf-8") as f:
    yaml.dump(data, f)             # serialize back - correct indentation guaranteed

# validate: re-load and assert the change is present and parses
check = YAML().load(path)
assert "media" in check["http"]["routers"], "router not written"
```

For a quick syntax check of any YAML file without editing:
`python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1])); print('ok')" file.yml`

## Round-tripping keeps comments, not layout

The round-trip loader preserves comments and key order, but a plain `YAML()` load-and-dump still
REFLOWS the document. Two defaults do it, and both are silent:

- **Block sequences get dedented.** The default indent does not match most hand-written files, so
  every list in the document shifts. Measured: a two-key edit to a 238-line commented file
  produced a 120-line diff.
- **Every null is written ONE way, whatever the file had.** A plain `YAML()` writes every null as a
  bare `key:`, so an explicit `key: null` or `key: ~` is rewritten. Equal to a parser, not to a
  reviewer, who now has to adjudicate that for every occurrence.

Neither is caught by the re-load check: the keys are all present and the file parses, so that
`assert` passes on a fully reflowed document. The unedited round trip in the pattern is what
catches both, BEFORE you have changed anything; when it fails, diff `buf.getvalue()` against the
file to see which lines your settings move. The diff before committing confirms the edit:

```bash
git diff -- path/to/file.yml    # must show only the lines you meant to change
```

### Match the file's null style

Inspect the file first. Explicit nulls can be counted; bare ones cannot, because a bare `key:`
also opens every nested block (`on:`, `jobs:`), so the unedited round trip finds those for you:

```bash
grep -cE ':[[:space:]]+(null|Null|NULL)[[:space:]]*(#.*)?$' path/to/file.yml   # explicit null
grep -cE ':[[:space:]]+~[[:space:]]*(#.*)?$' path/to/file.yml                  # explicit ~
```

`grep -c` exits 1 when the count is 0, so read the number it prints, never its exit status.

- **Both counts 0** (a GitHub workflow's `pull_request:`, `workflow_dispatch:`): pin nothing. A
  plain `YAML()` keeps bare nulls, and a `None` you add is written bare too.
- **One explicit spelling, and the unedited round trip with it pinned passes:** pin it. Do it on a
  SUBCLASS: `yaml.representer.add_representer` registers on the shared `RoundTripRepresenter`
  class, so it changes every `YAML()` in the process, and the next bare-null file you dump comes
  out with `key: null` throughout.

  ```python
  from ruamel.yaml.representer import RoundTripRepresenter

  def null_as(spelling: str) -> type[RoundTripRepresenter]:   # "null" or "~", as the file writes it
      class FileNullRepresenter(RoundTripRepresenter):
          pass
      FileNullRepresenter.add_representer(
          type(None),
          lambda dumper, _: dumper.represent_scalar("tag:yaml.org,2002:null", spelling),
      )
      return FileNullRepresenter

  yaml.Representer = null_as("null")   # before the first dump
  ```

  A `None` you add is then written in that spelling too.
- **Mixed** - both counts above 0, or one spelling pinned and the unedited round trip still turns
  bare `key:` lines into that spelling: ruamel writes one spelling per dump and cannot keep two.
  Pin the spelling most of the file's nulls use (the bare ones are the lines a round trip with an
  explicit spelling pinned rewrites), and make the unedited round trip its own commit:
  write `buf.getvalue()` to the file instead of asserting on it, require its diff to show null
  lines only, and commit that as a normalisation. Then run the pattern unchanged - the assert now
  passes - so your edit's commit shows only your lines. Where normalising someone else's file is
  not acceptable, say so and ask; never let the rewritten null lines ride inside your change.

## Common mistakes

| Mistake                                              | Do instead                                                                      |
|------------------------------------------------------|---------------------------------------------------------------------------------|
| Hand-typing YAML and hoping the indentation is right | Build the dict/list in Python, `dump` it                                        |
| `sed`/regex to change a value or add a key           | `load` -> edit the object -> `dump`                                             |
| PyYAML to round-trip a commented config              | Use `ruamel.yaml` (PyYAML deletes comments, reorders)                           |
| Committing/deploying without re-loading              | Re-`load` after dump and assert the expected keys exist                         |
| Trusting ruamel to preserve the file's layout        | Pin `yaml.indent(...)`, and a null spelling only if the file writes one         |
| Pinning `key: null` on a file with bare `key:` nulls | Count the file's explicit nulls first; a bare-null file needs no representer    |
| Treating the re-load assert as the whole check       | It proves the file PARSES; only the diff proves you changed only what you meant |
| Tabs for indentation                                 | Library emits spaces; never indent YAML with tabs                               |
