# skill-writer checklist - meta-adopting-external-skills (2026-09-25, rename at identity sites only)

Change: Step 2 gains one paragraph stating where `adopt_skill.py` renames the upstream name - the
front matter `name:`, an H1 that is exactly the name, a `<namespace>:<name>` reference and a path
segment under `skills/` - and that a plain word is never rewritten, with the tool-named skill
(`git`, `git commit`) as the reason; plain mentions are counted per file as "left for review".

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique, tool-bearing. Test approach: the shared retrieval arm (quote or NONE,
      haiku, inert `bitranox:baseline-probe`, text pasted). The question here is Q5: an upstream
      skill named "git" whose body says "Run `git commit` before you push" - is that rewritten?
- [x] Scope: one added paragraph in Step 2; frontmatter, `name:` and description untouched.

## RED

- [x] Inherited coverage: the same `redcheck --corpus-cascade` run as the compuse-toolbox checklist
      of this date (STRONG on function words only); route taken: the quote-back text check.
- [x] RED, pre-change text: Q5 answered "NO" by inference from "rewrites the skill's internal
      cross-references to `bitranox:<name>`". That is the wrong answer for the tool it described,
      which rewrote the word everywhere, so the old text actively misled on this question.

## GREEN

- [x] Q5 "not rewritten", quoting "A plain word is never rewritten, because a skill named after its
      tool (`git`) uses that word for the tool (`git commit`)".
- [x] GREEN `Skill gaps`: "required inference from a general principle". Declined: the quoted
      sentence names this exact case (`git`, `git commit`), so no further rule is missing.
- [x] Diffed against RED in both directions: RED's answer was right by accident and is now right by
      the text; nothing lost.

## Quality

- [x] The claim is executed by the script's own end-to-end test (a real subprocess adopting an
      upstream skill named `git`: `git commit` survives, the front matter name and the
      `superpowers:git` reference are rewritten, and the report prints "left for review").
- [x] No address, hostname or machine path added; no bare package-local doc reference.
- [x] Security: prose only.
