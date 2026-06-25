---
name: edit-yml
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

- **`ruamel.yaml`** - preferred for editing an EXISTING file: it round-trips and preserves comments,
  key order, and formatting (YAML 1.2). `pip install ruamel.yaml`.
- **`PyYAML`** (`import yaml`) - fine for generating a NEW file or when comments do not matter;
  `yaml.safe_load` / `yaml.safe_dump`. Note: it drops comments and reorders, so do not use it to
  round-trip a hand-commented config.

See **bitranox:python-use-modern-libraries** for the wider list.

**Safety:** never load untrusted YAML with PyYAML `yaml.load()` or a custom `Loader` - the
`!!python/object` tags execute arbitrary code. Use `yaml.safe_load`. `ruamel.yaml`'s default
`YAML()` is the safe round-trip loader (only `YAML(typ="unsafe")` is dangerous).

## Pattern: load -> edit the structure -> dump -> re-load to validate

```python
from ruamel.yaml import YAML
from pathlib import Path

yaml = YAML()                      # round-trip mode: keeps comments + order
yaml.preserve_quotes = True
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

## Common mistakes

| Mistake                                              | Do instead                                              |
|------------------------------------------------------|---------------------------------------------------------|
| Hand-typing YAML and hoping the indentation is right | Build the dict/list in Python, `dump` it                |
| `sed`/regex to change a value or add a key           | `load` -> edit the object -> `dump`                     |
| PyYAML to round-trip a commented config              | Use `ruamel.yaml` (PyYAML deletes comments, reorders)   |
| Committing/deploying without re-loading              | Re-`load` after dump and assert the expected keys exist |
| Tabs for indentation                                 | Library emits spaces; never indent YAML with tabs       |
