# skill-writer checklist - files-edit-toml (comments inside a tomlkit array)

- [x] Change: references/tomlkit-not-diff-minimal.md gains section 4 "Comments inside an array
      belong to a position, not to a value" (operation table, text-edit plus tomllib recipe);
      SKILL.md's not-diff-minimal paragraph names the array cases and routes to it; the
      description adds "adding or removing a comment in one" as a trigger.
- [x] RED (text check): `grep -rniE 'add_line|insert\(|array item|_ArrayItemGroup'` over SKILL.md
      and references/ returned nothing; the only comment-loss text was section 3 (`del` of a key).
- [x] Every library claim run on tomlkit 0.15.2: `arr.insert(1, it)` and `arr.append(it)` after
      `it.comment("...")` dump the line with no comment; `arr.add_line(v, indent="  ",
      comment="...")` dumps `"v", # ...` at the end; `arr[2] = "mypy>=1.20"` keeps the old
      inline comment on that line; `del arr[1]` below a whole-line comment leaves the comment above
      the next value; the array body is five `_ArrayItemGroup` entries while `list(arr)` has three
      values, so no index addresses a comment.
- [x] The recipe in section 4 executed: anchor count 1, `tomllib` values equal the expected list
      after removing the comment and its value.
- [x] GREEN quote-back: section 4 table row "`arr.insert(i, it)` or `arr.append(it)` after
      `it.comment("why")` | The comment is DROPPED"; SKILL.md "no array operation carries a
      comment with its value".
- [x] Description measured with len(): 424 characters, trigger-only.
- [x] Not done here: the separate queue entry about `del` of a key leaving its comment is already
      covered by section 3 (re-run: `del doc["t"]["a"]` leaves `# explains a` above `b`).
- [x] Receipt: the editing agent loaded bitranox:meta-skill-writer through the Skill tool before its
      first edit; the SKILL.md edits were accepted.
- [x] ASCII only, present tense, no history lines (finder pattern over the added lines: no hit
      except an example comment), tables canonical (reformat_tables.py run after each table edit).
- [x] Security scan: prose and examples only; no secrets, hostnames, private paths or PII; example
      paths are generic.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for this skill.
