# When a tomlkit round-trip is not diff-minimal

tomlkit keeps comments and formatting inside a table, but on parse it groups tables by dotted prefix.
Three edits come out larger than the change you made. Each one is valid TOML, so no parser complains;
only the diff shows it, and a reviewer cannot tell a moved table from a content change.

## 1. Interleaved table families are regrouped, even with no edit

When a file INTERLEAVES table families - for example `[a.x]` and `[a.y]` separated by `[[other]]`
array-of-tables entries - `tomlkit.dumps` can move every `[a.*]` sub-table next to its first sibling.
An untouched file already comes back reordered:

```toml
[rowsets.a]      # dumps puts [rowsets.b] right here,
x = 1            # above both [[claim]] entries
[[claim]]
id = 1
[rowsets.b]
y = 2
[[claim]]
id = 2
```

Check before editing:

```python
import tomlkit
from pathlib import Path

src = Path("file.toml").read_text(encoding="utf-8")
if tomlkit.dumps(tomlkit.parse(src)) != src:
    ...  # tomlkit will reorder this file: edit by exact text instead (below)
```

A plain interleave does not always trigger it, which is why the check, not the layout, decides.

**Edit such a file by exact text, then verify it like a library edit:**

1. Copy the file aside before editing; restore from that copy, not from git, if a check fails.
2. Insert or replace the EXACT block at an anchor that occurs once: `assert src.count(anchor) == 1`.
3. Re-parse the result with `tomllib.loads` and check the keys or ids you touched for duplicates.
4. Read the diff: a pure insertion has ZERO removed lines.

## 2. A new table lands by the same grouping

Adding a new `[tool.x]` table places it right after the FIRST existing `[tool.*]` table, not at the
end of the file - in a `pyproject.toml` that can be above `[project.urls]`, with no blank line before
the next header. Check where it landed before committing.

## 3. `del` leaves the comment above the key

`del doc["t"]["a"]` removes the key but not the comment line above it, which then sits above the next
key it does not describe (or dangles at the end of the table). Read the diff for an orphaned comment
and remove it by exact text at an asserted unique anchor.
