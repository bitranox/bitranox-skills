# skill-writer checklist - process-test-design (2026-10-12, Windows permission-wall tests)

Gap: the skill had no guidance for a test that needs a path `stat` cannot check on Windows. The
obvious build (deny the user on the directory) leaves `os.stat` succeeding, and an elevated session
ignores the deny entirely, so such a test passes or fails for reasons unrelated to the code.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Test: coverage check against the file, plus an application scenario
      (fix a draft fixture) with quote-back.
- [x] Scope: one new section before "Prune low-value tests" and one Quick-checklist line.
      Frontmatter untouched, so no derived artifact regenerates.

## RED
- [x] Claims verified by execution on Windows (CPython 3.10.20 and 3.14.6), from a process with
      SeBackupPrivilege and SeRestorePrivilege disabled: deny on the directory only -> `stat` OK,
      `listdir` and `mkdir` inside it PermissionError; deny list on the parent only -> `stat` OK;
      read-attributes denied on the directory plus list-directory on the parent -> `stat`
      PermissionError (errno 13, winerror 5). With the privileges enabled, as an elevated OpenSSH
      session holds them, every shape stats, lists and creates normally.
- [x] Claim verified: a full-control deny made the entry impossible to remove again (icacls
      /remove:d rc 5); the two narrow rights left it removable.
- [x] Claim verified: a test built on the API wall passed on GitHub's windows-latest runner.
- [x] `redcheck --corpus-cascade` flagged the scenario as INHERITED (STRONG): a memory fact on the
      authoring machine already teaches it. Route taken: the coverage check against the file is the
      RED evidence; the behavioural arm runs only as GREEN, with the skill text pasted and every
      answer required as a direct quote.
- [x] Coverage RED with a positive control: control `order-independent` 3; `SeBackupPrivilege` 0;
      `FindFirstFile`/`PARENT directory` 0; `backup semantics` 0; `permission-wall` 0; `icacls` 0;
      `assert the wall holds` 0.

## GREEN
- [x] Coverage after the edit: control 3; every target term at least 1.
- [x] Behavioural GREEN (sonnet, inert probe agent): given a draft that denies Full Control with
      icacls by name over an elevated SSH session and asserts only the behaviour, it named all five
      defects, each with a direct quote (full-control deny, parent listing not denied, backup
      privilege bypass, no wall assertion, icacls by name), and wrote the wall assertion first.
- [x] Every dispatch asked for a `Skill gaps` section; lists recorded below.
- [x] Diffed GREEN against RED both ways: RED was a text check, so nothing behavioural to lose; the
      existing sections were not edited.

## Gaps and decisions
- [x] Closed: no API names or access masks - the text now names `GetTokenInformation`,
      `GetNamedSecurityInfoW`, `SetEntriesInAclW`/`DENY_ACCESS`, `SetNamedSecurityInfoW`,
      `FILE_READ_ATTRIBUTES` (0x80) and `FILE_LIST_DIRECTORY` (0x1).
- [x] Closed: how to disable the privileges and keep their state - `AdjustTokenPrivileges`,
      attributes 0, keeping the previous state it returns.
- [x] Closed: process-wide token versus parallel tests - stated.
- [x] Closed: inheritance of the parent's entry - non-inheritable, on a parent the test owns.
- [x] Closed: teardown order - privileges first, then the parent's DACL, then the directory's.
- [x] Declined: a runner where the privilege cannot be disabled - the wall assertion already makes
      that runner fail loudly, which is the intended outcome.
- [x] Declined: a failing ACL restore - an ordinary teardown error, not specific to this technique.
- [x] Quote-back, five touched questions, each answered by a direct quote: "add ONE
      non-inheritable deny entry (`SetEntriesInAclW` with `DENY_ACCESS`; `FILE_READ_ATTRIBUTES`
      (0x80) on the directory, `FILE_LIST_DIRECTORY` (0x1) on a parent the test owns ...)";
      "Disable the privileges with `AdjustTokenPrivileges` (attributes 0, keeping the previous state
      it returns)"; "Take it down in reverse: privileges first, then the parent's saved DACL, then
      the directory's"; "The token is process-wide, so the wall must not span tests running in
      parallel threads".
- [x] Declined (quote-back gaps): no numbered build order and no mechanism for sharing the wall
      across threads - the teardown order is stated outright, and sharing is ruled out on purpose.
