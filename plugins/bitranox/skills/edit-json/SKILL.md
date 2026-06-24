---
name: edit-json
description: Use when creating, generating, editing, or validating a JSON file - package.json, tsconfig, plugin.json, VS Code settings, API fixtures, config - especially when modifying an existing file or producing one programmatically. Use instead of hand-typing JSON or editing it with sed/regex.
---

# Edit JSON with a Python library, never by hand

## Overview

Build and edit JSON by round-tripping through a Python data structure, then re-load to confirm it
parses. Editing JSON as raw text invites the classic breakages: a trailing comma, an unquoted key,
a single quote, a missing brace. A library serialization is valid by construction; re-loading it
verifies it.

## Library

- **`json`** (stdlib) - the default: `json.load` / `json.dump` (use `indent=2` for human-edited
  config, `sort_keys=True` for stable diffs). Correct and always available.
- **`orjson`** - when speed/throughput matters (fast, returns `bytes`, strict). `pip install orjson`.

JSON has **no comments**. If a file has `//` or `/* */` (JSONC, e.g. tsconfig, VS Code settings)
or trailing commas (JSON5), plain `json` will fail - use `pyjson5`/`json5` to load it, but write
back as strict JSON unless the consumer requires the relaxed form.

See **bitranox:python-use-modern-libraries** for the wider list.

## Pattern: load -> edit the structure -> dump -> re-load to validate

```python
import json
from pathlib import Path

path = Path("plugins/bitranox/.claude-plugin/plugin.json")
data = json.loads(path.read_text(encoding="utf-8"))   # parse into Python objects

data["version"] = "1.5.0"                              # edit the structure

path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")  # serialize back

# validate: re-load and assert (raises JSONDecodeError if malformed)
assert json.loads(path.read_text(encoding="utf-8"))["version"] == "1.5.0"
```

For a quick syntax check of any JSON file without editing:
`python3 -c "import json,sys; json.load(open(sys.argv[1])); print('ok')" file.json`

## Common mistakes

| Mistake                                          | Do instead                                          |
|--------------------------------------------------|-----------------------------------------------------|
| Hand-editing and leaving a trailing comma        | `load` -> edit the object -> `dump` (no trailing commas) |
| `sed`/regex to bump a value or add a key         | `load` -> edit -> `dump`                            |
| Single quotes or unquoted keys                   | The serializer emits correct double-quoted JSON     |
| Running `json.load` on a JSONC/tsconfig file     | Load with `pyjson5`; write back strict JSON         |
| Losing key order / churning diffs                | Python dicts keep insertion order; `sort_keys` for stable diffs |
| Committing without re-loading                    | Re-`load` after dump and assert the expected value  |
