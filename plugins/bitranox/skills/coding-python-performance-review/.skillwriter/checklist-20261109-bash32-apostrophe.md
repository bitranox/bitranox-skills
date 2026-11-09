# skill-writer checklist - coding-python-performance-review (2026-11-09, bash 3.2 apostrophe)

Steps 3 and 7 held an apostrophe in a Python comment inside a heredoc inside a command substitution,
which macOS's bash 3.2 reads as an unterminated quote, so the whole block is a syntax error there.

Decisions: none - a one-word comment rewording in two bash blocks; no recorded decision is touched (skill_decisions.py show coding-python-performance-review run first)

- [x] Step 0b `skill_decisions.py show coding-python-performance-review` read before the edit; nothing touches this comment.
- [x] RED: the pre-edit Step 7 block run through `bash -n` in a bash:3.2 container exits 2 with "unexpected EOF while looking for matching".
- [x] GREEN: the same block with the comment reworded exits 0 under bash 3.2, and the new test fails on the pre-edit text.
- [x] Added lines checked: ASCII only, no history wording, description unchanged.
- [x] Deployment: committed on a worktree branch and pushed as 10.42.1 with CI watched.
