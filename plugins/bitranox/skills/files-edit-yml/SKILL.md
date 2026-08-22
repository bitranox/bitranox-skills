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
  comments, not layout" below, and pin the two settings there before you dump.
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
from ruamel.yaml import YAML
from pathlib import Path

yaml = YAML()                      # round-trip mode: keeps comments + order
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)   # MATCH the file; the default dedents block sequences
yaml.representer.add_representer(                # keep an explicit `key: null`, not a bare `key:`
    type(None),
    lambda dumper, _: dumper.represent_scalar("tag:yaml.org,2002:null", "null"),
)
path = Path("traefik/dynamic/services.yml")

data = yaml.load(path)             # parse existing file into Python objects
data["http"]["routers"]["media"] = {
    "rule": "Host(`media.example.com`)",
    "entrypoints": ["websecure"],
    "service": "media",
    "tls": True,
}

with path.open("w") as f:
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
- **An explicit `key: null` is rewritten to a bare `key:`.** Equal to a parser, not to a reviewer,
  who now has to adjudicate that for every occurrence.

Neither is caught by the re-load check above: the keys are all present and the file parses, so the
`assert` passes on a fully reflowed document. Pin both settings (shown in the pattern), then DIFF
before committing and require the diff to show only what you meant to change:

```bash
git diff -- path/to/file.yml    # a reflow shows as dozens of untouched lines rewritten
```

A diff far larger than your edit, on a file you loaded with an unpinned `YAML()`, is the reflow.

## Common mistakes

| Mistake                                              | Do instead                                                                      |
|------------------------------------------------------|---------------------------------------------------------------------------------|
| Hand-typing YAML and hoping the indentation is right | Build the dict/list in Python, `dump` it                                        |
| `sed`/regex to change a value or add a key           | `load` -> edit the object -> `dump`                                             |
| PyYAML to round-trip a commented config              | Use `ruamel.yaml` (PyYAML deletes comments, reorders)                           |
| Committing/deploying without re-loading              | Re-`load` after dump and assert the expected keys exist                         |
| Trusting ruamel to preserve the file's layout        | Pin `yaml.indent(...)` AND a `None` representer first                           |
| Treating the re-load assert as the whole check       | It proves the file PARSES; only the diff proves you changed only what you meant |
| Tabs for indentation                                 | Library emits spaces; never indent YAML with tabs                               |
