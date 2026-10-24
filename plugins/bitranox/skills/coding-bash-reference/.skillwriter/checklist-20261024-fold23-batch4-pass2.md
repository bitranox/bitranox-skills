# skill-writer checklist - coding-bash-reference (memory rules folded in)

- [x] Change: ## Common Mistakes -> new subsection after 'Unquoted variables (word splitting +
      globbing)' - coding-bash-reference/SKILL.md. RED on the pre-edit snapshot: partial. Verified:
      (1) Literal quotes reach the program + exact error: ran MT='uvx --from "mytool>=1.4.0"
      mytool'; $MT --help in a mktemp scratch dir with uv 0.13.0 -> 'Error: Failed to parse:
      `"mytool>=1.4.0"`' / 'cause: Expected package name starting with an alphanumeric character,
      found `"`', rc=2. printf of $MT showed the four words uvx | --from | "mytool>=1.4.0" | mytool.
      (2) Unquoted >= is a redirection: echo --from pkg>=0.2.0 created a file named =0.2.0
      containing '--from pkg'. (3) Function and array forms pass mytool>=1.4.0 as one clean arg:
      printf '<%s>' probes for mt() { ... "$@"; } and "${mt[@]}" both printed <mytool>=1.4.0> with
      following args intact. (4) Mechanism:
      coding-bash-reference/functions-parameters-expansions.md:235 and :984 (quote removal only
      removes quotes that did not result from an expansion). (5) Fresh shell per call: kept generic
      ('a tool that starts a fresh shell per command'). Scratch dir removed by exact path
      afterwards.
- [x] Dropped as stale or unverified: Nothing contradicted. The body's Claude-Code-specific wording
      'A Claude Code Bash call starts a fresh shell' was generalised to 'a tool that starts a fresh
      shell per command'. Its session narrative ('A plan and a RED-baseline agent both produced the
      variable form') and the memory slug link were left out. The exact error text is now the
      backtick form uv 0.13.0 prints (`"pkg>=..."`), where the body had straight double quotes.
- [x] Review C fixed: the uvx error quoted verbatim with its cause line (uvx 0.13.0, exit 2); docs a
      reader may paste into cmd.exe use double quotes, since cmd.exe does not treat single quotes as
      quoting (measured: a single-quoted spec wrote a file and passed `'a`), single quotes stay
      correct for POSIX-shell or PowerShell-only docs; the array renamed so it does not shadow the
      function.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      every scenario again after the first review's fixes, then the scenarios each later fix
      touched. Every answer was a quote from the new text on both tiers in every round; no NONE.
      Quotes were checked against the files (6-word windows; misses traced to line wraps,
      markup and line-number prefixes).
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps not listed
      here asked for detail the rule does not need (out of scope) or were answered elsewhere in
      the skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history finder clean on the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns except where the file keeps one line per paragraph or list item.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
