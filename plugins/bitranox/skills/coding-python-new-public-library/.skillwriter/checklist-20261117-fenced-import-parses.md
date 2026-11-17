# Review checklist - the usage example's import line parses (2026-11-17)

Change: in section 3 the fenced python example read `import <pkg> as lib`, which is not Python.
It now reads `import your_package as lib   # your_package: the import name of <pkg>`. One line;
frontmatter and every other line unchanged.

## PLAN
- [x] Skill type: reference. Test: a parser check of the fenced block before and after, plus one
      application probe on the weakest tier (haiku, text-only baseline-probe agent).
- [x] Ledger read (`skill_decisions.py show coding-python-new-public-library`, also with
      `--kind rejected,removed --full`): one live entry, a rejected Common-mistakes row about
      rename-project name variants. The change does not touch it.

## RED
- [x] `ast.parse` of the pre-edit block (`import <pkg> as lib` / `lib.emit_greeting()`):
      `SyntaxError invalid syntax`. This is the hit meta-skill-audit's `fenced_python_syntax`
      check reports for the skill.

## GREEN
- [x] `ast.parse` of the edited block: parses.
- [x] `python3 plugins/bitranox/skills/meta-skill-audit/scripts/script_prepass.py --room
      plugins/bitranox` prints `fenced_python_syntax               0 hit(s)`, exit 0.
- [x] Probe (haiku, 1 cell), given the edited block and a library named `acme_tools`: wrote
      `import acme_tools as lib` and `lib.emit_greeting()`, and quoted
      "your_package: the import name of <pkg>" as what the name stands for.

## REFACTOR
- [x] Skill gaps the probe listed, each decided:
  - `<pkg>` is not defined inside the excerpt: declined, covered elsewhere in the skill. The
    paragraph directly above the block (SKILL.md line 70-71) reads "two console commands - the
    package name with underscores and with hyphens, both bound to the same entry point - plus
    `python -m <pkg>`", and the bash block before it uses `<pkg>` as the command name.
  - Whether the import name equals the distribution name: declined, same line 70 text (the
    underscore spelling is the importable one); the new comment says "import name" for that reason.
  - Whether `emit_greeting` exists, and how to replace the placeholder behaviour: declined, out
    of scope of a syntax repair; the line's own comment says "placeholder; swap for your real API".
- [x] Width and fence check over the added line: nothing reported (line is 72 columns, inside a
      fence). The paragraph after the block (section 4 heading) holds no back-reference.
- [x] ASCII only; no address, hostname or private path added; no history wording added.
- [x] Decisions: none - a syntax repair of one example line; it adds, removes and rejects no rule.
