# checklist-20261011 - an incoming file silently overwrites an ignored local file

## What the change is

A new section and one Quick reference row: when an incoming commit adds a path that exists locally as
an IGNORED untracked file, `pull`, `merge`, `checkout` and `switch` replace it with exit 0 and no
output. The section gives the pre-pull check (`git diff --name-only --diff-filter=A HEAD..@{upstream}
| git check-ignore -v --stdin`) and a back-up step.

## RED

- [x] Reproduced in throwaway repos, git 2.53.0 (a repo adds `CLAUDE.md`; clones hold a different
      local `CLAUDE.md`):
      - ignored via `.git/info/exclude`: `git pull` rc=0, no output, content became upstream's;
        `git merge` (fast-forward) rc=0, prints only the file list, content became upstream's;
        `git checkout -B feat origin/main` rc=0, content became upstream's.
      - ignored via `.gitignore`: `git switch other` rc=0 and `git merge other` rc=0, both left
        upstream's content.
      - control, NOT ignored: `git pull` rc=1, "untracked working tree files would be overwritten"
        (localized text), local content kept.
      - pre-check printed `CLAUDE.md` with `.git/info/exclude:7:CLAUDE.md`, `check-ignore` rc=0.
- [x] Behavioural arms, scenario "ignored local CLAUDE.md, upstream adds one, write the steps":
      - sonnet: "git pull silently overwrites the local CLAUDE.md ... It gives no 'untracked files
        would be overwritten' refusal." Gap: "The ignored-files-overwritten-silently claim is from my
        knowledge of git ... I could not probe it." Steps backed up the one known file and
        verified with `git check-ignore -v CLAUDE.md`, not the added-path list.
      - haiku: "git lets a merge overwrite an ignored untracked file silently ... This is from
        knowledge of git behaviour and is unverified here." It also backed up only the known file.
- [x] Both arms already knew the behaviour (it is in this machine's general knowledge), so the
      gap is the missing GENERAL check over every added path and the missing durable procedure, not
      the awareness. No `redcheck --corpus-cascade` was run; the claim is checked by the git
      reproduction above, which no inherited context can supply.

## GREEN

- [x] haiku, skill section pasted: ran `git fetch -q` then the `diff --diff-filter=A ... |
      git check-ignore -v --stdin` pipeline, "Back up every hit ... outside the repo", and stated
      "Git does not refuse ... replaces the content silently, exits 0 and prints nothing."
- [x] sonnet, same: "git pull will overwrite the local CLAUDE.md ... It will not refuse, will print
      nothing about it, and will exit 0", and used the pipeline as the pre-pull check.
- Skill gaps reported by GREEN and their disposition:
  - [x] where to put the backup (sonnet): CLOSED, text now says a durable place outside the repo,
        not a session scratch dir.
  - [x] what to do after the pull (sonnet, haiku): CLOSED, text now says keep local content as an
        untracked file under another name (`CLAUDE.local.md`) or merge by hand, never edit the
        tracked file in place.
  - [x] no configured upstream (sonnet): CLOSED, text says use `HEAD..<incoming-ref>`.
  - [x] `pull --rebase` and a global `core.excludesFile` unmeasured (haiku): CLOSED by stating they
        were not measured.
  - [x] nested added path (haiku): CLOSED, text says paths print repo-relative.
  - [x] fast-forward vs real merge (sonnet): DECLINED, same command and same measured outcome for
        both; a non-fast-forward merge was not separately measured.
  - [x] "if it exists on disk" has no test (sonnet): DECLINED, `ls` or `test -e` is obvious and the
        reader backs up only hits that exist.
  - [x] what to do with the local content, a decision for the reader (haiku, sonnet): DECLINED, the
        text offers the two safe defaults and leaves the choice open.
- [x] Lost-result diff, GREEN against RED: nothing a RED arm produced is missing from GREEN; RED
      arms' extra advice (compare checksums, read the diff) was reported again by the GREEN arms.
- [x] No quote-back round was run on the final wording; the two GREEN arms ran against the section
      before the gap fixes, and the fixes only add the items listed above.

## Quality

- [x] Present tense; no session narrative, no scratch paths, no hostnames; description and `name`
      unchanged; one section and one table row added.
- [x] ASCII only.
