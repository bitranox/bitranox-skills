# skill-writer checklist - compuse-git (peel an annotated tag, tar a git file list)

Entries covered: compare a release tag with HEAD only after peeling it; never pack
`git ls-files | xargs tar cf -`.

- [x] Change: two quick-reference rows: "Which commit does a release tag point at?" and "Packing a
      git file list into a tar".
- [x] Mechanism claims measured in a throwaway repo: annotated `v1.0.0` on HEAD - `rev-parse v1.0.0`
      printed the tag object sha (type `tag`), `rev-parse --verify -q 'v1.0.0^{commit}'` printed
      HEAD, `ls-remote .` listed `refs/tags/v1.0.0` and `refs/tags/v1.0.0^{}` (the HEAD sha);
      `git ls-files | xargs -n 2 tar cf -` gave a stream whose `tar tf` listed 2 of 6 files with rc
      0, an extracting receiver got 2 files with rc 0 and xargs reported tar killed by signal 13;
      `git ls-files -z | tar --null -T - -cf` held 6 files; with one tracked file deleted it exited
      2 (`Cannot stat`) and still wrote the other 5.
- [x] RED: the opus no-text arm peeled the tag and avoided `xargs tar` from its own knowledge
      (contaminated); evidence is the text check: `^{commit}` HEAD 0 now 1, `xargs tar` HEAD 0 now 1.
- [x] GREEN (opus and haiku, rows pasted): both used `'v1.2.3^{commit}'` and `refs/tags/v1.2.3^{}`
      and the `tar --null -T -` form for uncommitted edits, quoting "Peel it:" and "Let `tar` read
      the list itself, one archive".
- [x] Skill gaps decided: a tracked file deleted from the working tree (closed: the row names the
      `Cannot stat` exit 2); reading tar's status inside the pipeline (closed: `${PIPESTATUS[1]}`
      added); re-probe on the final text (haiku) quoted the new clause and reported no new gap on
      this row.
- [x] Width and fence check over added lines: no output; table canonical; ASCII only; history
      finder 0 hits; no private names.
