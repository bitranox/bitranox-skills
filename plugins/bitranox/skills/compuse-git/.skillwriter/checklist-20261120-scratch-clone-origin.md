# checklist - a scratch clone of a local checkout inherits its stale local main

One queued contribution: `git clone --no-local <checkout>` makes the checkout the clone's origin,
so the clone's `origin/main` is the checkout's LOCAL main. New quick-reference row: fetch in the
checkout, fetch its `refs/remotes/origin/main` into the clone, branch from FETCH_HEAD.

Decisions: none - additive row

## RED

- [x] Skill decisions read first: none recorded for compuse-git.
- [x] Reproduced in a scratch repo: forge two commits, checkout's local main one behind; the
      scratch clone's origin/main was the stale commit, the fetch of refs/remotes/origin/main gave
      the current one.
- [x] Text check at HEAD: `clone --no-local <checkout>` and `refs/remotes/origin/main` 0 hits.

## GREEN

- [x] Quote-back probe (haiku): base and cause answered by quotes; its gap "no command to branch
      from FETCH_HEAD" closed by adding `git -C <dir> switch -c <branch> FETCH_HEAD`.

## REFACTOR

- [x] Table re-padded by the formatter; ASCII check clean.
