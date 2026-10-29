# When a tomlkit round-trip is not diff-minimal

tomlkit keeps comments and formatting inside a table, but on parse it groups tables by dotted prefix.
Several edits come out larger than the change you made. Each one is valid TOML, so no parser complains;
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

## 4. Comments inside an array belong to a position, not to a value

tomlkit keeps a multiline array's comments, but no array operation moves them with the value they
explain. The output is valid TOML and re-loads to the values you expect, so only reading the diff
catches a comment that was dropped, stranded or left beside the wrong value (measured on tomlkit
0.15.2):

| Operation                                                         | What happens to the comment                                                       |
|-------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| `arr.insert(i, it)` or `arr.append(it)` after `it.comment("why")` | The comment is DROPPED: the dumped line has no `# why`                            |
| `arr.add_line("value", indent="  ", comment="why")`               | Kept as an inline `# why`, but `add_line` only appends at the end                 |
| `arr[i] = "new"` on a value with an inline comment                | The comment stays on that line, now beside the new value it does not describe     |
| `del arr[i]` below a whole-line `# comment`                       | The comment stays, now above the next value it does not describe                  |
| Remove a whole-line comment itself                                | No public API: it sits in an internal `_ArrayItemGroup` that `del` cannot address |

So add a commented value with `add_line(..., comment=...)` when the end of the array is an acceptable
place, and otherwise edit the comment lines by exact text and verify the values with a parser:

```python
import tomllib

# remove one value together with the whole-line comment that explains it
block = '  # keep ruff pinned until 0.16 lands\n  "ruff>=0.15",\n'
assert src.count(block) == 1                      # the anchor is unique
new = src.replace(block, "")
expected = tomllib.loads(src)["project"]["optional-dependencies"]["dev"]
expected.remove("ruff>=0.15")
assert tomllib.loads(new)["project"]["optional-dependencies"]["dev"] == expected
```

After any array edit, read the diff around every comment in that array. A reason that only lives in
an inline comment (a CVE id behind a pin or an audit ignore) is also worth repeating in the commit
message, where an array edit cannot detach it.
