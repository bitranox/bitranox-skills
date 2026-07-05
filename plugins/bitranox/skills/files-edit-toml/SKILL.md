---
name: files-edit-toml
description: Use when creating or editing a TOML file (pyproject.toml, config.toml, a tool's .toml config) - adding or changing a key, bumping a version/value, editing a table or array - instead of hand-editing it or using sed/regex, which corrupt structure or silently drop comments. Covers tomllib (read), tomlkit (round-trip edit that PRESERVES comments and formatting), and rtoml/tomli_w (write).
---

# Edit TOML with a Python library, never by hand

## Overview

Round-trip TOML through a Python parser, then re-load to confirm it parses. Editing TOML as raw text
(sed/regex/manual) breaks the classic things: a value placed under the wrong table, a broken array, a
mangled quote - and worst, it churns or DROPS the comments and formatting that files like
`pyproject.toml` rely on. A library write is valid by construction; re-loading verifies it.

## Library - pick by whether comments must survive

- **`tomllib`** (stdlib, 3.11+) - **read only**, no writer. `tomllib.load(f)` (binary mode). The default
  for reading.
- **`tomlkit`** - **the right tool for EDITING an existing file** (e.g. `pyproject.toml`): a style-
  preserving round-trip that keeps comments, key order, and whitespace. Use this whenever the file has
  comments or hand-formatting you must not lose.
- **`rtoml`** - fast read/write; **does NOT preserve comments**. Fine for machine-owned data files.
- **`tomli_w`** - minimal writer (`tomli` + `tomli_w`); also **drops comments**. Pre-3.11 read companion
  is `tomli`.

See **bitranox:coding-python-use-modern-libraries** for the wider list. Reach for the structured editors
for the other formats too: **bitranox:files-edit-json**, **bitranox:files-edit-yml**,
**bitranox:files-edit-xml**.

## Pattern: edit an existing file (preserve comments) with tomlkit

```python
import tomlkit
from pathlib import Path

path = Path("pyproject.toml")
doc = tomlkit.parse(path.read_text(encoding="utf-8"))   # comments + layout preserved

doc["project"]["version"] = "1.5.0"                      # edit the structure

path.write_text(tomlkit.dumps(doc), encoding="utf-8")    # write back, comments intact

# validate: re-load (raises on malformed TOML)
import tomllib
assert tomllib.loads(path.read_text(encoding="utf-8"))["project"]["version"] == "1.5.0"
```

For a machine-owned data file where comments do not matter, `rtoml.dump(data, f)` / `rtoml.load(f)` is
fine. For a quick syntax check without editing:
`python3 -c "import tomllib,sys; tomllib.load(open(sys.argv[1],'rb')); print('ok')" file.toml`

## Common mistakes

| Mistake                                           | Do instead                                                                   |
|---------------------------------------------------|------------------------------------------------------------------------------|
| `sed`/regex to bump a version or add a key        | `parse` -> edit the object -> `dumps`                                        |
| Editing `pyproject.toml` with `rtoml`/`tomli_w`   | They DROP all comments; use `tomlkit` to preserve them                       |
| Reaching for a writer in the stdlib               | `tomllib` is READ-only (3.11+); install `tomlkit`/`rtoml`/`tomli_w` to write |
| `tomllib.load` on a text-mode file handle         | `tomllib` needs binary mode (`open(p, "rb")`) - or use `tomllib.loads(text)` |
| Hand-editing and breaking a multiline array/table | Edit the parsed object; the serializer emits valid TOML                      |
| Committing without re-loading                     | Re-`load` after dump and assert the expected value                           |
