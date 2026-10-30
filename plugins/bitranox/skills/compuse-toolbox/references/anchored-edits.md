# Anchored edits: the traps `anchor_edit` cannot see for you

`anchor_edit` refuses an absent or ambiguous anchor, so it closes the success-shaped no-match
branches of `str.replace` (a silent no-op), `str.partition` (returns `(whole, "", "")`, so an
"insert after" lands at the END) and `str.find` (returns -1, which then slices from the end). The
traps below are about INTENT: the anchor matched exactly once and the edit is still wrong. They
apply to `anchor_edit` and to any edit you script by hand.

**Every path you hand `anchor_edit` must be ABSOLUTE.** Each subcommand's `F` (`replace`,
`insert`, `replace-span`, `reap`) and every `file` inside a `batch --spec` is refused with exit 2
when relative: which file a relative path names depends on a cwd that persists across calls, and
a sibling repo holding the same template-copied text is exactly where the anchor would match the
wrong file. Write `anchor_edit.py replace /abs/path/doc.md ...`, never `replace doc.md ...`.

## Check the intended result, not the match count

- **When the new text is a substring of the old, a count==1 replace deletes content and reports
  success.** Replacing `NEW + tail` with `tail` (rewriting part of a region you just wrote) removes
  `NEW` while the tool says "replaced 1 occurrence". Assert the INTENDED text is present in each
  computed content (before the write phase, see below) and print the line or byte delta; never
  chain two replacements where the second's anchor contains the first's output - do one
  replacement per region.
- **Check the size of the change.** The line-count delta must roughly equal the text you swapped,
  and a pure insertion must show zero removed lines (`batch --spec` takes `expect_line_delta` per
  file; `replace-span` takes `--expect-removed-lines` and `--must-keep`). A contiguous over-delete
  or a duplicated block looks small in a diffstat and obvious in the delta.
- **Drive the validity check from the list the writer iterated.** When a script writes several
  files, parse or test every path it wrote, not the one you were worried about.
- **A survivor assertion is itself unverified code.** `assert "def split_command" in text` never
  matches `def _split_command`; give it the exact identifier, or prove it matches before writing.

## Computed spans

- **Never compute a span as `s.index(START)` to `s.index(END)`.** It deletes everything between the
  markers, including constructs you believed were not there. Prefer `replace` of the exact old text,
  or `replace-span` with `--expect-removed-lines` and `--must-keep`.
- **When you must compute one, search the end marker FROM the start offset**: `s.index(END,
  start)`, never from 0. A boilerplate end marker that also occurs earlier in the file makes
  `s[:start] + new + s[end:]` write the block between them twice - the file grows by thousands of
  lines and nothing is lost, so no test or parse can see it.
- **An indented end marker matches inside every MORE-indented copy of that line**, so the span ends
  early and the old body survives as unreachable code after the new one. Anchor on `"\n" + line`
  (or a line-anchored regex), and after a function-level rewrite read the function down to the
  next `def` before calling it done.
- **A structural delimiter can be missing.** "From this bullet to the next `- ` or heading" runs past
  the end of its parent for the LAST child of a list. Scope the search to a section, refuse a block
  that contains a heading or a second sibling delimiter, and dry-run first, printing each block's
  line count and last line.
- **Deleting a whole Python construct**: use the AST's `end_lineno`, and start at the first
  decorator's line, not `node.lineno`.

## Multi-edit hygiene

- **A hand-written multi-file edit validates EVERY file before it writes ANY.** Make the script
  two-phase: read every file, compute every new content and run every assertion, and only when all
  of them passed write all the files. Writing as you go leaves the tree half-edited at the first
  wrong count, and a plain re-run then fails or double-applies on the files already done.
- **Measure each expected count; never read it off an earlier listing.** A count guessed from a
  grep listing is routinely off by one. Get it from the same `text.count(old)` the assertion uses,
  in a dry pass that prints the count per file, or, for a single-line anchor only, from
  `grep -o -F -e 'old' FILE | wc -l` - not `grep -c`, which counts LINES, so two hits on one line
  read as one. grep treats each line of a multi-line pattern as its own pattern, so count a
  multi-line anchor with the `text.count` dry pass. Count every anchor in every
  file: an anchor that also sits in a docstring or comment of another file is the usual surprise.
- **On refusal, say which assertion failed and that nothing was written**, or a run that applied
  nothing looks identical to "the script did not run". `anchor_edit batch --spec` is this shape
  already (every count checked before ANY write, so a refusal writes nothing and says so; an IO
  failure mid-write stops at that file and names the files already written): prefer it to a new
  script for a repeat of the chore.
- **A formatter run between capturing an anchor and using it invalidates the anchor** (a gate that
  runs `ruff format` can collapse a multi-line signature). Re-read the file and re-derive anchors
  after any gate run.
- **Copy a gitignored file aside before editing it.** `git checkout` cannot restore a file git never
  held; `anchor_edit` writes a byte-exact backup for any file git cannot restore, a hand-rolled
  script does not.
