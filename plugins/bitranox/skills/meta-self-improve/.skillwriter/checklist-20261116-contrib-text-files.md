# Checklist 2026-11-16: queue a lesson that quotes code through a file

Change: `contrib_queue.py add` takes `--what-file` / `--why-file` (each mutually exclusive with
its inline flag; UTF-8 with a BOM dropped, one trailing line ending removed, an empty or
whitespace-only file refused, an unreadable or non-UTF-8 file refused with exit 2). Step 2 of
SKILL.md names that route and `mcp__bitranox__contrib_add` for lesson text holding a backtick,
`$(...)` or a quote.

- [x] Step 0b: `skill_decisions.py show meta-self-improve --kind rejected,removed --full` read;
      the one live rejection (name-based misplacement signal) is unrelated.
- [x] Premise checked against the code: `add` had no file option (argparse took `--what` /
      `--why` as argv text only), and `hooks/shell-prefix-selfref-guard.py`
      `substitutes_inside_text_arg` refuses a double-quoted `--what` / `--why` holding a backtick
      OR `$(`, so `--what "$(cat f)"` is refused too. Single quotes survive the guard but break on
      an apostrophe in the lesson.
- [x] Code RED: 15 new tests in `tests/test_contrib_queue.py` (file read, BOM and CRLF, mutual
      exclusion with argparse's "not allowed with argument" message, usage naming `--what-file`,
      empty file, absent and non-UTF-8 file) all FAILED on the unchanged script. GREEN: the
      skill's whole test dir passes (737 + the new tests).
- [x] Text RED: a text-only probe (opus) given the pre-edit step 2 answered Q2 "quote the line
      that says how to pass text with backticks or $(...)" with NONE, and listed as a gap "The
      excerpt shows no `--what-file`/`--why-file` (or stdin) option"; it fell back to a hand-made
      Python argv launcher.
- [x] The added command was executed before GREEN: `contrib_queue.py add --target
      skill:compuse-toolbox --what-file F --why-file G /opt/demo` under a scratch HOME stored a
      lesson holding backticks, `$(...)` and an apostrophe byte for byte (`list` shows it).
- [x] Text GREEN: the same probe on the edited step 2, opus and haiku (2 cells); results below.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion ("In cases 1 and 2 the entry carries the lesson itself") binds to the case list,
      not to the new paragraph.
- [x] No description (frontmatter) change.

## GREEN probe results

Same scenario (queue a lesson holding backticks, `$(...)` and apostrophes, from a temporary
worktree), edited step 2 pasted in, opus and haiku:

- Q1 both tiers: Write each field to a file, then `contrib_queue.py add --target
  skill:compuse-toolbox --what-file <F> --why-file <G> "<main checkout>"`.
- Q2 both tiers quoted the new paragraph verbatim (RED: NONE).
- Q3 both tiers: the MCP tool is out, quoting "outside a temporary worktree only (step 3b)".

Skill gaps reported, and what was decided:

- `<plugin>` unresolved, step 3b not shown, no read-back verb named: excerpt-only. Covered in the
  skill: "Resolving `<plugin>`" under step 4, step 3b's worktree bullet, and step 3's "Listing and
  closing stay CLI-only" beside `contrib_queue.py list`. Declined.
- "double-quoted" might suggest single quotes are safe (opus): the paragraph's opening clause
  "never goes on the command line" already rules that out, as the same probe noted. Declined.
- Whether a relative `F` resolves against the process cwd or the positional `<cwd>`: it resolves
  against the process cwd like any path argument (`Path(path).read_text` in
  `contrib_queue.py` `_read_text_file`); not worth a sentence. Declined.
- Routing case 1 vs 2 and where "what you were doing" goes: predates this change and does not
  change the action in either case; outside this change's scope. Declined.

Decisions: d-20261116-56013d50
