# skill-writer checklist - compuse-toolbox (2026-09-25, four table rows follow their scripts)

Change: four rows of the tool table state behaviour their scripts now have. `mdwrap` refuses a
blockquote paragraph and any wrap that would leave a line Markdown reads as a new block;
`backstop` refuses (exit 2) a `--repo` that is not the repository root; `diffbehave` reports a side
that did not run as ERROR, exit 2, never DIFFER; `corpus_prompts` exits 2 on `--count` with
`--module`. The table was reformatted to its canonical widths afterwards.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference (a tool table). Test approach: a retrieval arm, seven questions the
      change moves and two unchanged controls, each answered with a direct quote or NONE, on the
      least inferential tier (haiku) with the inert `bitranox:baseline-probe` agent type and the
      text pasted into the prompt. The same arm covered meta-adopting-external-skills and
      meta-skill-audit; the four questions here are Q1-Q4, the control Q8.
- [x] Scope: four table cells; frontmatter, `name:` and description untouched.

## RED

- [x] Inherited coverage checked first: `redcheck --corpus-cascade` from the worktree read 1252
      documents and reported STRONG coverage, on shared terms that are tool names and function
      words (armed, backstop, diffbehave, kind, saying). Route taken: the behavioural arm is
      replaced by the quote-back text check of the artifact, which inherited context cannot answer.
- [x] RED, pre-change rows: Q1 (blockquote), Q2 (`--repo` a subdirectory), Q3 (a typo on one side
      with `--expect-differ 1`) and Q4 (`--count` with `--module`) all answered NONE. Control Q8
      (a list paragraph) answered "refused, exit 1" with the governing quote.
- [x] RED `Skill gaps` recorded: edge cases of mdwrap, backstop, diffbehave and corpus_prompts
      not documented.

## GREEN

- [x] Q1 refused, exit 1; Q2 refused, exit 2; Q3 ERROR, exit 2; Q4 exit 2 - each with a direct
      quote of the new row text. Control Q8 unchanged, same quote.
- [x] GREEN `Skill gaps`: none for these rows.
- [x] Diffed against RED in both directions: the one RED answer that was right (Q8) is still right
      with the same quote; nothing lost.

## Quality

- [x] Every claim executed against the real script, each with a control: a blockquote paragraph
      exits 1 ("paragraph is or holds a blockquote"), a list exits 1, a plain paragraph exits 0;
      `--repo` naming a subdirectory exits 2 ("is not the root of a repository"); `--a` naming a
      command that does not exist exits 2 with ERROR ("--a did not run (rc=127)"), while two
      commands that really differ satisfy `--expect-differ 1` with exit 0.
- [x] No address, hostname or machine path added; no bare package-local doc reference.
- [x] Table is in the formatter's canonical form (`reformat_tables.py --check` exits 0).
- [x] Script tests cover each stated case (test_mdwrap, test_backstop, test_diffbehave,
      test_corpus_prompts).
- [x] Security: prose only.
