# skill-writer checklist - coding-bash-reference (2026-07-17, section pointers now cite full, resolvable section numbers)

Change: Every `> Full details:` pointer used an ambiguous `section N` shorthand. Verified against the four
reference files' real headings: 6 of 13 resolved to the WRONG section (Arrays said 6 -> 6.6 Aliases,
actual 6.7; `set` said 2 -> 4.2 Bash Builtins, actual 4.3.1; Compound Commands said 3 -> a heading in
another file; Redirections said 1, actual 3.6; Signals said 5, actual 3.7.6; Prompt said 8 -> 6.8
Directory Stack, actual 6.9). Two rows already used the full number and were correct.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: grep of the real `^#{1,3} N.N` headings in bash-features.md / shell-builtins.md /
      shell-syntax-and-commands.md / redirections-and-execution.md proved 6 pointers sent the reader
      to the wrong section; a wrong pointer is indistinguishable from a right one to a reader
- [x] GREEN: adopted the convention that already worked (full section number + title) for all 11 pointers;
      a scripted checker now confirms all 14 resolve to a real heading, 0 unresolved
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
