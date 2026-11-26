---
name: compuse-toolbox
description: Use when about to hand-roll a one-off shell/Python utility for a recurring chore - finding or killing a process (pgrep -f, pkill -f); a gate's real exit status, not a pipe's; git across repos - branch/sync/dirty, tracked vs ignored, conflict markers, resolving a conflict hunk; errors in a noisy CI log; did CI finish on my commit and pass; filtering JSONL or tallying a field; mining a Claude Code transcript; is this text already present; a sweep that skips no gitignored file; a UTF-16/BOM log grep cannot read; a rate-capped transfer or hung job; an ssh key/BatchMode one-liner, scp; pytest on a Windows host; waiting for a log marker (tail -F | grep); do old and new behave the same; the latest backup or log; could a RED baseline fail; does a test catch a mutated line, a mutation battery; disk a deleted worktree kept; duplicated CLAUDE.md sections; how many source files a codebase owns; which memory level holds a fact; how often a new guard would fire on real history; a guard or detector judged against a control.
---

# compuse-toolbox

A small set of tested Python jigs for recurring computer-use chores. Reach for one BEFORE
hand-rolling a throwaway `pgrep`/`awk`/`jq`/`json.loads` one-liner - the jig has already handled the
edge cases (self-match, exit-code traps, wrapper argv) that the one-liner gets wrong.

Each jig is a self-contained PEP 723 script: run it with `uv run` (uv provisions its deps) - except
the jigs that run YOUR commands or scripts (`gate`, `adjudicate`, `diffbehave`, `ci_triage --cmd`,
`transfer check --cmd`), which must be launched with plain `python3`, see the `gate` notes below -
and get its full arguments from `--help`. Run from the skill directory, or give the full path. The jigs sit
in the skill's `scripts/` directory.

**Every jig answers in the same exit codes.** 0 = it ran and the answer is yes (nothing wrong),
1 = it ran and the answer is no (a finding), 2 = it could not run: bad input, a missing tool, an
unreadable path, a refusal of the whole action, a crash. An action jig with no "no" answer
(`anchor_edit`, `mdwrap`, `transfer fetch`) has no 1. Two jigs pass another program's code through
instead: `gate` exits the failing gate's own code and `fleet_ssh` the remote command's (255 = ssh
itself failed). Every `--json` prints one envelope `{ok, command, data, skipped}` on EVERY exit, 2
included, with an `error` string when there is one; `ok` means "ran without error", so it is false
exactly on exit 2 and a 1 is `ok: true`. Read the verdict from the exit code or `data`, never from
`ok`.

**From a script you commit, name the marketplace clone, never the plugin cache.** The base
directory a session announces is a version directory under `<plugins root>/cache/`: it names one
plugin version, changes on every update, and is deleted 14 days after it is superseded. A script
that hard-codes it, globs across its versions or picks one (`sort -V`, `tail -1`, `find -quit`)
breaks, or quietly runs a stale copy - or a copy of a skill that has since moved to another
plugin. The marketplace clone has no version in its path:

```bash
TOOLBOX="${CLAUDE_CODE_PLUGIN_CACHE_DIR:-$HOME/.claude/plugins}/marketplaces/bitranox-skills/plugins/bitranox/skills/compuse-toolbox/scripts"
[ -f "$TOOLBOX/ci_wait.py" ] || { echo "compuse-toolbox not found at $TOOLBOX - add it: /plugin marketplace add bitranox/bitranox-skills" >&2; exit 2; }
uv run "$TOOLBOX/ci_wait.py" --ref HEAD
```

The plugins root is `~/.claude/plugins` unless `CLAUDE_CODE_PLUGIN_CACHE_DIR` moves it; in Python
build the same path from that variable or `Path.home()`. The clone is what `/plugin marketplace
update` pulls, so it can be AHEAD of the version a running session loaded. A marketplace added from
a local directory has no clone there: read its `installLocation` from `known_marketplaces.json` in
the plugins root.

Where no marketplace exists - CI, a server, a machine without Claude Code - copy the one file into
the repository with a header naming its source path and plugin version, and refresh it on purpose.
Such a script then runs that copy everywhere, workstations included - preferring the clone where it
exists makes local runs and CI run different versions of the same jig. Never download it from a
branch when the script runs: that executes whatever the branch holds at that moment.

## Tools

| Tool | Use it for (the full entry: `references/tools.md`) | Invoke |
|---|---|---|
| `procsig` | finding or killing a process (`pgrep -f` / `pkill -f`, which self-match your own shell); with `--peer`, which process and which Claude session holds a connection to a host or port | `uv run scripts/procsig.py --exe <name> [--kill]` (exit 0 = a match other than itself, 1 = none, 2 = empty needle, unknown signal, no /proc, or a signal not delivered - refused, or the target already exited); `uv run scripts/procsig.py --peer HOST[:PORT]` lists each holder with its nearest `claude` ancestor and that session's cwd (list only; 1 = no holder, 2 = a matching connection whose owner is another user's process - run it as root to list that one - or a bad `--peer`, and stderr says which) |
| `suite_busy` | is a test suite already running (`pgrep -f pytest`, `ps aux \| grep pytest`) in this repo or any of its worktrees, before you start a gate | `uv run scripts/suite_busy.py [--repo PATH] [--match TOKENS] [--wait-s N] [--json]` (exit 0 nothing running, 1 a suite is running - or still is when `--wait-s` ran out, 2 could not answer) |
| `git_state` | a branch/sync/dirty check before a risky commit or bulk op, over one repo or many; or which copies of a file across a tree are tracked, modified, gitignored or untracked | `uv run scripts/git_state.py [REPO ...] [--root DIR] [--fetch] [--json]` / `--files CLAUDE.md --root DIR [--json]` |
| `conflict_scan` | a `grep -rn '^<<<<<<<'` sweep for merge-conflict markers left in a tree | `uv run scripts/conflict_scan.py [PATH ...]` |
| `quotecheck` | checking a subagent's quote-back against the files it cites, one verdict per quote, also over a Workflow journal | `uv run scripts/quotecheck.py text --dir SKILL_DIR --quote "the sentence"` |
| `raisesmatch` | judging whether a `pytest.raises` / `pytest.warns` `match=` pins the refusal or would pass any unrelated one | `uv run scripts/raisesmatch.py tests/` |
| `conflict_resolve` | resolving a merge conflict hunk by hunk (ours, theirs, both with the newer CHANGELOG entry on top, the diff3 base) instead of a hand-written `re.sub` | `uv run scripts/conflict_resolve.py CHANGELOG.md --all both-theirs-first --expect-hunks 1` / `F --list` / `F --hunk 1=ours --match 'import os=theirs' --json` |
| `ci_wait` | waiting for GitHub Actions to finish on a commit you pushed - every workflow, not the first - and whether it passed, before tagging a release; also a re-run's new attempt only (`--min-attempt`), and a spent GitHub API rate limit, which it reports instead of retrying | `uv run scripts/ci_wait.py --ref HEAD [--repo OWNER/REPO] [--event push\|any]` |
| `ci_triage` | finding the error lines in a noisy build/CI log instead of `grep`/`sed`/`awk` | `python3 scripts/ci_triage.py --file LOG [--step NAME]` (NAME is the gh step name or the `##[group]` header text, and every job's copy of the step is triaged) (exit 0 clean, 1 error lines found or `--cmd` exited non-zero, 2 tool error or `--step` not found) |
| `pushcheck` | before a push: is this repo public, and does the push publish a local path, internal hostname, username or private address | `uv run scripts/pushcheck.py --repo . --json`<br>`uv run scripts/pushcheck.py --range origin/main..HEAD --denylist-file ~/.config/infra.txt` (exit 0 safe, 1 a public range carries private-looking content, 2 refused; under --json `ok` means the check ran and the verdict is `data.safe`) |
| `redaction_scan` | checking a diff against a list of private names before publishing (`git diff \| grep -iFf names`) | `uv run scripts/redaction_scan.py --list names.txt --range origin/main..HEAD [--redact-hits] [--json]` (exit 0 clean, 1 a hit, 2 could not run: zero patterns, a failed control, a change adding no line) |
| `backstop` | a deadline for a background agent or long job that alerts only if it never finishes, and refuses to arm when the finish signal is already true | `uv run scripts/backstop.py --deadline 2400 --done-file report.md --cancel-file .done --label 'task 30'`<br>`uv run scripts/backstop.py --deadline 1800 --repo /path/to/worktree --base 8d9e72e` |
| `markerwatch` | waiting for a log line that says a run finished (`tail -F LOG \| grep MARKER`) without a banner or echo answering early | `uv run scripts/markerwatch.py calibrate last-good.log --terminal 'ALL GATES PASSED'` / `watch gate.log --from start --terminal 'ALL GATES PASSED' --terminal 'GATE RED' --timeout 1800` / `--json` |
| `enforced` | does any code actually DECIDE on a config setting, or is it only declared, parsed and read | `uv run scripts/enforced.py planner_kinds --root src/`<br>`uv run scripts/enforced.py on_auth_failure --root . --json` |
| `confound` | can a table of runs where several things changed attribute a result to ONE change, or is the comparison confounded | `uv run scripts/confound.py --claim model --arm 'a model=opus tokens=23556 outcome=read 23554' --arm 'b model=fable tokens=23557 outcome=read 0'` |
| `transcript_index` | full-text search for something worked out in an old Claude Code session, across every past transcript | `uv run scripts/transcript_index.py index`<br>`uv run scripts/transcript_index.py search "zpool scrub"` (each word literal, all required; `--fts` for raw FTS5 syntax; exit 2 = query error, a query with no letter or digit, or an index database that cannot be opened or written, never a miss) |
| `jsonl_grep` | filtering a JSONL by type/role, extracting or tallying a field, or learning what values a field takes across a transcript corpus | `uv run scripts/jsonl_grep.py <file> [--type ...]` / `<dir> --type assistant --field message.model --count` (walks the `*.jsonl` below `<dir>`, or reads stdin; exit 1 = read, nothing matched; 2 = read nothing, bad arguments, or a named path missing or unopenable beside one that was read; `--raw` prints strings bare like `jq -r`; any existing path is read, so `<(cmd)` works; JSON null counts as `null`) |
| `transcript_tail` | the last user/assistant text of a Claude Code transcript, every text turn of a session, or every call of one tool with its input | `uv run scripts/transcript_tail.py <file> [--role ...]` / `--all` (every turn; each row has `kind` prompt/tool_result/text) / `--all --role user --prompts-only` (what a person typed) / `--tool Agent` (every call, with input) / `--json` |
| `claim_check` | is some text already present in a set of files (`grep -c` / `grep -l`), literal or as a regex | `uv run scripts/claim_check.py FILE... --pattern P --control C` |
| `grep_all` | a repo-wide `grep -r` that must be COMPLETE, gitignored files included | `uv run scripts/grep_all.py PATTERN [PATH ...] [--glob G]` |
| `gate` | running gates and acting on the result by the gate's own exit status, not a pipe's (`<gate> \| grep summary && git push`) | `python3 scripts/gate.py [--log L] [--summary RE] --gate C [--gate C ...] [--then C]` (NOT `uv run` - see below; the default log is per-invocation, and a gate that ran 0 tests is REFUSED - pytest, cargo, unittest and go test are recognised, any other runner is judged on its exit status alone, and so is a wrapper that prints no test counts at all, such as bmk's `make test` in its default JSON mode: to show a NEW test file actually ran there, run it directly (`pytest -q <file>`) and read its `N passed`; a malformed invocation is a usage error, exit 2; exit = the single failing gate's OWN code, so a taxonomy code such as 2 survives, else 1; 2 when a gate could not be STARTED, the --log cannot be written, or the runner crashed). Gates run WITHOUT a shell, so `--gate 'cd DIR && pytest'` exits 2 (`cd` cannot be started): say `cd DIR` / `FOO=1` as `--cwd DIR` / `--env K=V` (every gate and --then) or `--gate-cwd` / `--gate-env` written after one --gate; `--gate-env K=@FILE` reads the value from a file (trailing newlines dropped; `K=@@x` is a literal `@x`), the shell-free way to hand a message to a gate: `--gate "make push" --gate-env MSG=@msgfile`. A quoted gate holding `$(` or a backtick is a usage error (exit 2, names the token): no shell expands it, so the program would get the characters literally (a `make push MSG="$(cat f)"` gate once pushed a commit titled with the unexpanded text); tokens after `bash -c` and after `--` are exempt. Anything else needs an explicit `--gate "bash -c '...'"` |
| `winlog` | searching a Windows log `grep` cannot read: UTF-16 (PowerShell `Tee-Object`, `Out-File`), BOM or mixed encodings | `uv run scripts/winlog.py read FILE [--grep DONE-OK] [--tail 20] [--json]` (exit 1 = no match) |
| `transfer` | a big-file download or host-to-host copy under a real speed limit, or judging whether a long job has hung | `python3 scripts/transfer.py fetch URL --rate 8Mbit` / `push F user@host:/d/ --rate 8Mbit` / `check --file F --pid N` (`--pid` is Linux-only; `--cmd CMD` runs with no shell - wrap a pipeline in `sh -c '...'`) (check: 0 ADVANCING, 1 STALLED, 2 UNKNOWN; fetch/push: 0 done, 2 the transfer did not happen - curl/rsync failed or could not start; there is no 1) |
| `fleet_ssh` | an `ssh` with key, `BatchMode` and timeout retyped per call, or an scp with the login user inside the path | `uv run scripts/fleet_ssh.py [--user U] HOST [cmd]` / `--scp SRC DST` (exactly two paths; more is refused, exit 2) (add `--trust-changing-host-keys` for a fleet you reimage: accept-new in a separate known-hosts file; ssh REFUSES a changed key before the command runs, so the stale entry is dropped and the call retried ONCE - the command's first and only run - keyed on ssh's own `-E` log and never on the remote command's stderr. Exit = the remote command's code, 255 = ssh failed, 2 = the script's own failure; `--dry-run --json` prints the envelope) |
| `winpytest` | copying a repo to a Windows test host and running its pytest suite there over ssh | `uv run scripts/winpytest.py --host WINHOST --user USER --key KEY --dest 'C:\work\proj' --extra dev -- -q tests/` / `--json` |
| `diffbehave` | do an OLD and a NEW version of a script (or two CLIs) behave the same on the same inputs; or is a hand-rolled detector a rubber stamp | `python3 scripts/diffbehave.py --a "OLD_CMD" --b "NEW_CMD" --case-file CASES.jsonl` / `--expect-differ N` (known-negative check) |
| `adjudicate` | confirming a claim about a guard or a hand-rolled detector by the one input that shows it, against a control that must answer differently | `python3 scripts/adjudicate.py --hook HOOK.py --name N --probe TEXT --control TEXT` (each TEXT is fed on that side's own stdin, e.g. a hook's JSON payload) / `--claim-file CLAIMS.jsonl` / path mode: `--subject DETECTOR.py --probe-path PLANTED --control-path CLEAN -- --root {path} --json` (everything after a bare `--` is the subject's argv, `{path}` where each side's path goes; with no `--` the path is its only argument; a claim file takes `probe_path`/`control_path`) / `--fired-when nonzero\|match --fired-pattern RX` / `--json` (exit 0 = every claim confirmed or refuted; exit 2 = a control did not discriminate (UNUSABLE), a usage error, or a side timed out / could not be launched - verdict ERROR, never counted as fired - or a non-positive `--timeout`; there is no exit 1, since a refuted claim is an adjudicated one; NOT `uv run`, whose env lacks a hook's optional deps) |
| `newest` | which backup, log or snapshot is the latest, without `ls <glob> \| sort \| tail -1` | `uv run scripts/newest.py /backups/nightly-*` / `--all` (every match, newest first) / `--json` / `--name-timestamp` (key on a fixed-width stamp in the FILENAME) (exit 1 = no match, 2 = no match while a path exists but could not be stat'd) |
| `redcheck` | could a RED baseline really fail, or does the agent's startup context (CLAUDE.md chain, memory bodies) already teach it | `uv run ../process-test-driven-development/scripts/redcheck.py --scenario S.txt --corpus-cascade . --json` (exit 1 = already covered; 2 = unchecked, a named corpus (either flag) assembled 0 documents or an --answer yielded no terms, with `data.unchecked` true) / `--answer A.txt --corpus docs/` |
| `wtclean` | the disk space a deleted worktree never gave back: its build cache left outside the checkout (ships in `git-worktrees`) | `uv run ../git-worktrees/scripts/wtclean.py my-feature` (plan, with sizes) / `my-feature --apply` / `--cache-dir DIR` |
| `claudemd_variance` | which `## ` sections are duplicated across CLAUDE.md files, and where each should live (ships in `meta-consolidate-claude-md`) | `uv run ../meta-consolidate-claude-md/scripts/claudemd_variance.py --root ~/src` / `--json` / `--min-members 1` |
| `srccount` | how many source files a codebase actually owns, vendored and generated trees excluded | `uv run scripts/srccount.py --root DIR [--root DIR2] [--ext .py] [--json]` / `--audit --root DIR` (exit 1 = nothing matched in ANY root, usually the wrong `--ext`) |
| `mem_levels` | which curated memory levels exist, what sits at each, and which level holds a fact | `uv run scripts/mem_levels.py --root ANCHOR [--slug S] [--json]` (exit 1 = no level holds that slug, 2 = --root is not a tree anchor, a level could not be read, or hooks/uuid_store.py will not import; a level is a CLAUDE.local.md carrying a managed pointer block) |
| `anchor_edit` | editing a file by anchor in a script or across many files (`str.replace`, `partition`, a span between markers), refusing a missed or ambiguous anchor | `uv run scripts/anchor_edit.py replace F --anchor-file old.txt --new-file new.txt` / `insert F --anchor-file a.txt --new-file n.txt --before` / `replace-span F --start-file s.txt --end-file e.txt --new-text '' --expect-removed-lines 3 --must-keep 'def survivor('` / `--json` / `--dry-run` |
| `mutation_arm` | does a test catch a mutated line - proving a test is not vacuous by breaking the code and requiring red; a mutation battery; sources restored after a kill, a SIGKILL on the next start | `.venv/bin/python scripts/mutation_arm.py --mutate src/x.py old.txt new.txt --test tests/t.py::test_y --timeout 90` (runs the arm under `--python PATH`, else `--with DEP` via uv, else ./.venv's python, else this interpreter - under a bare `uv run` with no .venv every arm is INCONCLUSIVE; the report names `runner` and `caught_by`) / repeat `--mutate` for one multi-layer arm / `--battery arms.json` for many labelled arms with a green baseline before and after / `--json`. Exit 0 killed (battery: every arm), 1 survived (battery: any arm), 2 the arm never ran (battery: any arm, or a red baseline) (including a pytest that exited 1 without reporting a failure), timed out, could not write the source, a file was not UTF-8, or the restore failed; 128 + N stopped by signal N (its stderr line says whether the sources are back) |
| `mutation_arm --revert` | running a test against the COMMITTED version of a file while your fix is still uncommitted, and getting the fix back | `.venv/bin/python scripts/mutation_arm.py --revert src/x.py HEAD --test tests/t.py::test_y` / repeat `--revert` for several files in one arm / combine with `--mutate` (anchors match the reverted text) / `--json`. Exit 0 the test FAILED against REV (killed: it catches the bug), 1 it passed (survived: it does not), 2 the arm never ran or was refused |
| `fanout_crosscheck` | did any agent of a per-target fan-out write into a sibling's target | `python3 scripts/fanout_crosscheck.py --target alpha_lib=../alpha_lib --target beta-tool=../beta-tool` (two or more) / `--since REV` or `--since NAME=REV` per target / `--ident NAME=TOKEN` for another identifier / `--allow NAME=TOKEN` / `--json`. Exit 0 nothing foreign, 1 findings (target, file:line, foreign target and token), 2 usage, unreadable target, or zero added lines |
| `guard_replay` | how often a new hook or guard would fire on real history, and whether its firings are worth it, before shipping it | `uv run scripts/guard_replay.py --module ../../hooks/my-guard.py --func notice` / `--tool Write` / `--tool Edit --field file_path` / `--sample 5` / `--firings OUT.jsonl` / `--root DIR` / `--json` (exit 1 = never fired, 2 = could not measure: tool or field unreadable, bad --block-pattern, module will not import, corpus unread, or the predicate raised on some command - `data.inconclusive` says which) |
| `corpus_prompts` | how often a rule that reads a PROMPT (a router trigger, a nudge, a classifier) would fire on what people actually typed | `uv run scripts/corpus_prompts.py --count`<br>`uv run scripts/corpus_prompts.py --module ../../hooks/g.py --func notice --module-b old.py --json` (exit 1 = the corpus held no prompt; 2 = a missing --root, a predicate option without its module, --count with --module, or an unreadable transcript; `--sample N` shows N FIRINGS) |
| `mdwrap` | re-flowing ONE paragraph of a long markdown file to a column width without touching its neighbours | `uv run scripts/mdwrap.py --file TODO.md --anchor 'NEXT STEP:' --width 100` / `--apply` / `--json` |
| `renamescope` | which hits of a `sed -i 's/old/new/g'` fall outside the functions you set out to change | `uv run scripts/renamescope.py src/net.py --name mac --intended _apply_iface` / `--regex RE` (indent with `[ \t]*`, not `\s*`) / `--intended file.py::func` for a name defined in several files / `--json` |
| `plan_codecheck` | running pytest, pyright and ruff on the python blocks of a written plan before handing it off | `uv run scripts/plan_codecheck.py --plan PLAN.md --section 'Task 3' --repo .` / `--check pytest` (repeatable) / `--python .venv/bin/python` / `--json` (exit 1 = a check failed, or a block was unplaced - `--allow-unplaced` accepts that; 2 = no such section or a heading matched twice, no python block, not one block naming a path, a path outside the repo, a tool missing or crashed, or an interpreter without pytest) |
| `instrument_share` | how much session time goes to instrumentation (memory upkeep, handovers, plugin detours), comparable across periods | `uv run scripts/instrument_share.py --since YYYY-MM-DD --until YYYY-MM-DD` / `--json` / `--max-gap 5` / `--exclude-cwd ''` (exit 1 = no tool call in the range; 2 = a bad option, a missing --root, or a transcript that could not be read) |
| `statusrot` | memory entries still claiming "shipped", "TODO" or an issue number long after (ships in `meta-dream-tree`) | `uv run ../meta-dream-tree/statusrot.py scan --chain DIR` (or `--level FILE`) / `--json` |
| `factedit` | rewording a memory fact's hook or replacing its body: owning level, hook cap, parse check (ships in `meta-dream-tree`) | `uv run ../meta-dream-tree/factedit.py show --slug SLUG` / `check --hook '...'` |

Per-tool arguments live in each tool's `--help` (loaded only when used, so this index stays small).
The rest lives in `references/`; load a page with the Read tool when its line applies:

- `references/tools.md` - the full entry for each row above, one `## ` heading per tool: what
  the hand-rolled version gets wrong, what the tool reports, its exit codes and refusals. Read a
  tool's entry before you run it for the first time in a session or act on its verdict, and
  when the one-line summary does not settle whether it fits your chore.

Three traps no `--help` covers:

- `references/anchored-edits.md` - before an `anchor_edit` run or a hand-scripted edit: a
  replacement whose new text is a substring of the old, a span computed between two markers, an
  indented end marker, and a script editing several files that must measure every count and
  check every file before it writes any.
- `references/mutation-arms.md` - before trusting a `mutation_arm` verdict: the inert control,
  which interpreter runs the arm, `--mutate` file paths, whole-suite doctests, and the `.pyc`
  cache when you must mutate by hand.
- `references/transcript-corpus.md` - before hand-walking `~/.claude/projects` instead of
  `jsonl_grep`, `guard_replay` or `corpus_prompts`: the shallow glob that misses subagent
  transcripts, duplicate calls from resumed sessions, task notifications that are not user
  records, and stub sessions that dilute a corpus-wide rate unless you report two denominators.

## Why a jig over a one-liner

- **`procsig` cannot self-match.** It reads `/proc` directly and always excludes its own process and
  every ancestor, so it structurally cannot signal the shell that launched it - the failure mode
  `pkill -f X` has whenever the shell's own command line contains `X`. Its exit code ignores itself
  and its ancestors too, so `procsig --cmdline X && echo running` is not fooled by its own argv.
- **`procsig --cmdline` also never searches a command STRING a shell was handed.** Exclusion covers
  only self and ancestors, and a SIBLING shell quoting the needle is neither: one such match killed
  a live command mid-run. So `bash -c '<text>'` and every equivalent is searched only up to the flag
  that introduces the string, and an argv that MIGHT hold one but cannot be classified with
  certainty is skipped entirely rather than assumed harmless. The bias is deliberate and one-way - a
  miss costs you one `kill <pid>`, a false match kills the wrong process - so if an expected process
  is absent from the listing, match it with `--exe` or `--comm`. Full rules in the tool's `--help`.
- **`suite_busy` asks per checkout, by argv token, and never sees itself.** "Is a suite
  already running here?" decides whether starting a gate corrupts both verdicts (shared ports,
  database, coverage file, venv), and the hand-rolled `pgrep -f pytest` answers a different
  question three ways: it matches the shell running it, it matches any command line merely
  CONTAINING the word, and it cannot say WHERE a process runs. `suite_busy` reads each
  process's cwd and puts it in the deepest of the repo's checkouts (a worktree nested under
  the main checkout is in both paths, and belongs to the worktree), compares whole argv tokens,
  and excludes its own process chain, so `--match pytest` on its own command line cannot
  report itself.
- **`redaction_scan` reads the list the way its owner wrote it.** A redaction list is prose
  for people (comment lines, `name==>replacement` rules), and `grep -Ff` reads it as raw
  patterns, so the scan is noisy where it should be quiet and blind where it should fire -
  and both look like a result. The jig parses the list, scans only what the change ADDS, and
  will not report clean until a planted line holding each pattern has come back as a hit,
  because a matcher that cannot see a name prints the same nothing as a clean change.
- **`claim_check` refuses to answer "no" blindly.** A content check's dangerous result is the
  NEGATIVE, because "not present" and "I never really looked" print the same. So every query carries
  a CONTROL pattern that MUST match; if the control misses, the verdict is BROKEN (exit 2), not
  ABSENT (exit 1), and no answer is given. A path it could not read - a typo, a binary, UTF-16
  without a BOM - blocks ABSENT the same way, because a control hit in the other files says
  nothing about one never read: with no hit anywhere the verdict is BROKEN. A hit in the files it
  DID read is still PRESENT (exit 0), with the unread paths listed on stderr as `skipped:`, since
  an unread file cannot undo a match. That converts a silent false all-clear into a loud
  failure - the exact shape behind a `grep -c` whose `file:count` output was never parsed, and a
  threshold set above the whole distribution so no pair could ever match.
- **`grep_all` cannot silently under-report.** In a Claude Code session `grep` routes to a
  gitignore-aware backend, so a repo-wide sweep drops ignored files and the miss reads as a
  clean result. `grep_all` walks the filesystem itself and then reports how many of its hits
  git considers ignored, which is exactly the number a normal grep would have missed. Measured
  on this tree: 73 pointer blocks found, 55 of them gitignored, against 17 from the session
  grep. A zero in that stderr line means the two agree and your earlier grep was safe. "Ignored" is
  judged from where you pointed it: a match in a nested repo or linked worktree inside a
  directory the outer repo ignores counts as missed when you searched the outer repo. A file you
  NAME on the command line never counts as missed, since a gitignore-aware search reads a file it
  is given. It never searches `.git` (a repo's directory or a linked worktree's gitdir file),
  `node_modules`, the Python caches, or any `.venv*` directory. When git
  cannot answer - no git, a failing check-ignore, or a repo git refuses to read (dubious
  ownership, a broken `.git` file) - the line says the count is UNKNOWN and the exit is 2, and every file or directory
  it could not read is listed as NOT READ.
- **`gate`'s per-gate options follow the `--gate` they apply to**:
  `python3 scripts/gate.py --gate "make push" --gate-cwd DIR --gate-env MSG=@msgfile`. Written
  before any `--gate` they are a usage error, exit 2.
- **`gate` reports the gate's OWN exit status, never a pipe's.** `<gate> | grep summary && git push`
  exits with `grep`'s status, so a red gate whose log still holds a green-looking line reads as
  success and the `&&` fires; writing `rc=$?` after the pipe records the same wrong status. `gate`
  runs each command with no shell and no pipe, so `returncode` is the gate's, sends output to a log,
  and greps the summary from that log AFTERWARDS - then runs `--then` only on a real pass. The
  plugin already BLOCKS the masked form (`hooks/block-masked-gate-exit.py`); this is the safe form
  to reach for instead of hand-rolling per-gate `rc=$?` capture and temp files each time.
  Launch this one with plain `python3`, not `uv run`: it declares no dependencies, and `uv run`
  puts its own ephemeral interpreter on the environment the CHILD gates inherit - measured, a gate
  shelling out to `python3 -m pytest` then died with `No module named pytest` and reported a false
  RED. The same holds for `ci_triage --cmd`, `transfer check --cmd` and `diffbehave`, which run
  your commands too, and for `adjudicate`, which runs the hook on its own interpreter (under
  `uv run`, one without the hook's optional PyYAML/lxml); each declares `LAUNCH_WITH = "python3"`,
  which is what the nudge suggests.
  Every other jig here is fine under `uv run`, except where its own row names the interpreter that
  runs YOUR tests (`mutation_arm`: a bare `uv run` with no `.venv` makes every arm INCONCLUSIVE).
- **`winlog` decodes a Windows log per SEGMENT, because one file can hold two encodings.**
  PowerShell writes UTF-16 from `Tee-Object`/`Out-File` but UTF-8 or ANSI from `Set-Content`, so a
  log created by one and appended to by the other is MIXED - with no BOM to announce it. Nothing
  errors: `grep` just finds nothing and `cat` prints `D O N E - O K`. A wait loop keyed on that
  marker then reports "not finished" for a run that finished, and times out on SUCCESS exactly as
  it would on failure. `iconv -f UTF-16LE` is not the fix: on a real mixed log it decoded the
  UTF-16 tail fine, exited 0, and silently turned the ASCII head into CJK mojibake - the header
  and the `running as NT-AUTORITAET\SYSTEM` line, which was the evidence that the task ran
  elevated. Partial, silent, and reported as success. `file` calls such a log plain `data`, so it
  will not even confirm the diagnosis. `winlog` decodes each segment on its own, keeps both halves
  (umlauts included), normalizes CRLF, and prints what it found on stderr - naming a MIXED file so
  it gets fixed at the WRITER instead of worked around in every reader.
- **`fleet_ssh` keeps the key and the login the same identity.** scp carries the login user INSIDE
  the path and has no `--user` flag, so a wrapper that reads `--user` only to pick the key hands
  scp a destination naming nobody: it logs in as the LOCAL user while offering the other user's
  key. On a host that accepts root and refuses your account that is `Permission denied
  (publickey)` from a command line where the flag looks honoured. It also keeps `BatchMode=yes` on
  always, because `-i <key>` alone still falls back to a PASSWORD PROMPT when the key is rejected
  and hangs an unattended run, and it picks a key by READABILITY - a shared key path can exist and
  be root-only on this box, which fails as `Permission denied` with EMPTY stdout far from the
  cause. Host-key checking stays at ssh's strict default; `--trust-changing-host-keys` is the
  opt-in for a fleet you reimage, and it keeps that churn in a separate known-hosts file rather
  than `/dev/null`, which would make every connect a first connect. It uses `accept-new`,
  which records a NEW host and REFUSES a changed key before anything runs, so a changed key is
  healed by dropping the stale entry - under the name ssh says it recorded (an ssh_config alias
  or a non-default port is stored under the resolved name) - and retrying ONCE, which is the
  command's first and only run. The retry is keyed on ssh's OWN messages, written to a log via
  `-E`, never on stderr: a remote command that itself runs ssh relays its inner ssh's refusal
  through stderr. A key marked @revoked names no entry to drop, so it is refused, never healed.
- **`git_state --files` cannot conflate tracked-and-ignored.** `git status --porcelain -- <path>`
  is EMPTY for a gitignored file and for a tracked-clean file ALIKE, so a naive per-file check
  reads them as the same thing - and only the tracked one is restorable with `git checkout`.
  `--files` classifies with `git ls-files --error-unmatch` (tracked) and `git check-ignore
  --no-index` (ignored) instead, and asks `check-ignore` only about the paths `ls-files` did NOT
  report tracked - so TRACKED WINS the tracked-and-ignored case deliberately, not by relying on
  git's own default (which happens to also hide tracked files from `check-ignore`, but only
  without `--no-index`). Batches at most 4 git calls PER REPO regardless of file count, never 2
  per file. `git_state`'s repo-state mode reads porcelain v2 (no `rev-parse --short` 2-rev
  footgun).
- **`diffbehave` answers "does this behave differently" by RUNNING both sides, never by reading
  them.** An `ast.dump` diff is identifier-sensitive, so a rename alone reads as a behaviour
  change, and neither a line count nor a `grep -c` executes anything either - none of the three
  can answer the question, only running both sides on the same input and diffing what happened
  can. Its `--expect-differ N` flag is the other half: a hand-rolled detector verified only
  against cases where it already agrees has proved nothing, so the tool fails unless at least N
  cases come back DIFFER - a comparison that can only ever say AGREE is a rubber stamp, not a
  check. A case where EITHER side did not run (it could not be started, or exited 126/127 as a
  launcher does for not-found and not-executable) is ERROR and exits 2 - never AGREE, and never the
  DIFFER a typo on one side would otherwise hand `--expect-differ`. Both sides timing out is ERROR
  too; one side timing out while the other answers is DIFFER, because that side ran and hung.
- **`adjudicate` scores a claim against a CONTROL, and keeps three answers rather than two.**
  Running the one input that shows a claim proves the claim and the guard are compatible, not that
  the guard is discriminating - so it runs a second input differing only in the thing claimed. The
  third bucket is the point: when BOTH sides fire, the control did not discriminate and the run
  measured nothing, which is not the same as the claim being refuted. Collapsing the two reported
  10 claims refuted where the truth was 7 refuted plus 3 never tested, and a report of refuted
  claims is acted on by deleting the finding. Any UNUSABLE claim exits 2 (could not answer) for that reason. A side
  that times out or cannot be launched is a fourth verdict, ERROR (exit 2), never scored as firing,
  since a hung probe would otherwise read CONFIRMED. It also says WHICH END is at fault, because two different causes give that one verdict: one unusable
  claim among several is a control that does not differ in the claimed way, while EVERY claim
  unusable is the subject firing on every input - which under the default `--fired-when output` is
  what a program that always prints a banner looks like, and the fix there is `--fired-when
  nonzero` or `match`, not a rewritten control. Re-run it after every fix: a fix that turns the
  suite green has twice not closed the finding it was for. A detector or scan you write during a
  review is a subject like any guard: a clean result on the real tree is the one input that shows
  the claim, so run it in path mode on a tree you planted the target in and one you did not
  before reporting "none found".
- **`newest` never compares names.** `ls <glob> | sort | tail -1` looks like "the newest" and is
  not: a longer name sharing the same date prefix sorts AFTER a shorter one, so an extra word
  beats the date. Pruning the wrong file this way is loud and gets noticed; VERIFYING against the
  wrong baseline is silent, which is the expensive half. `newest` sorts by mtime only (files and
  directories alike), breaks a genuine tie by input order - deterministic, not directory-listing
  luck - and reports the AGE of what it picked, because the newest member of a stale set is still
  stale and a bare path gives no way to notice that.
- **`redcheck` catches a RED that cannot fail, which reads exactly like one that can.** A
  scenario-based RED (a prompt, not code) fails for two reasons a code RED never has: the agent is
  handed a config cascade and shipped reference material before it ever sees the scenario, so a
  lesson already documented there gets answered from that, not from the scenario; and prose that
  names the trap or pre-diagnoses the cause hands over its own answer. Both make a RED pass for
  the wrong reason with nothing in the transcript to say so. `redcheck` checks a scenario for
  both leaks BEFORE an agent dispatch is spent on it, reporting which corpus document already
  teaches the lesson or which phrase telegraphs the answer. `--corpus-cascade DIR` assembles the
  first corpus for you rather than leaving you to enumerate it: the `CLAUDE.md` and
  `CLAUDE.local.md` chain from DIR up to the filesystem root plus the memory fact bodies on it,
  read by walking the filesystem, because those files are routinely gitignored and a
  gitignore-aware search returns a small corpus in which everything looks clean. A hit is strong
  evidence and names the file; a clean result only means not caught, since term overlap cannot
  see a paraphrase; exit 2 with `data.unchecked` true means the corpus was empty and nothing was checked. Ships in
  `process-test-driven-development`, indexed here so this table stays the one place that answers
  "is there already a tool for this?".
- **`wtclean` reclaims what removing a worktree leaves behind, which nothing else lists.** A
  per-worktree build cache is deliberately kept OUTSIDE the checkout - that is the point of giving
  each worktree its own - so `git worktree remove` does not touch it and it survives every
  cleanup at gigabytes a time. Nothing enumerates them, so they are normally found by running out
  of disk and then hunting by hand with `du` and `rm -rf`, which is the dangerous way to do it.
  `wtclean` names the worktree and its caches together with sizes, deletes nothing until
  `--apply`, then removes exactly what it listed rather than re-scanning; it refuses a symlinked
  target, a checkout holding uncommitted work, and a topic that is a path rather than a name.
  Ships in `git-worktrees`, indexed here so this table stays the one place that answers "is there
  already a tool for this?".
- **`claudemd_variance` computes a lift target instead of eyeballing one.** Deduplicating
  CLAUDE.md content without checking WHERE it truly belongs is how a false line gets promoted to
  an ancestor that binds every repo below - the common ancestor of a group's member paths is not
  the directory you happened to be looking at, and the common ancestor of a SINGLE file is its own
  parent directory, never the filesystem root. `claudemd_variance` splits every CLAUDE.md into
  `## ` sections, hashes each body (whitespace-normalised, so a reflow does not read as a
  different variant), groups the identical ones, and reports each group's true common ancestor
  plus the largest variant's share - the same "60-75% means one dominant version" signal
  `bitranox:meta-consolidate-claude-md`'s own variance table keys on. It enumerates by a plain
  filesystem WALK and never shells out at all, so - unlike a hand-rolled version built on the
  session's own `grep` - it cannot silently drop a gitignored CLAUDE.md. Ships in
  `meta-consolidate-claude-md`, indexed here so this table stays the one place that answers "is
  there already a tool for this?".
- **`transcript_tail` reads a FINISHED session, not only its last turn.** A record's content shape
  varies - user `content` is a plain string or a list of `tool_result` blocks, assistant `content`
  a list of thinking/text/tool_use blocks - so a one-line parser flattens the wrong one and returns
  empty without saying so. That is the tail mode. The whole-transcript modes exist because the tail
  alone cannot answer the questions a session review actually asks: "what did the user ask across
  the run?" (`--all --role user --prompts-only`: most user records are tool output, not prompts)
  and "which `Agent` dispatches went out, with what input?" both need every record, and
  answering them from the tail means writing one throwaway extractor per question - four of them in
  a single session, because a raw field dump (`jsonl_grep --field message.content`) hands back block
  JSON rather than the text. `--all` returns every text turn and `--tool NAME` every call of one
  tool with its input, each row carrying the 1-based JSONL LINE it came from, so a finding is
  addressable (`sed -n '<line>p'`) instead of searched for again. The line count includes blank and
  unparseable lines for exactly that reason, an unparseable one is counted onto stderr rather than
  vanishing, and a mode that matched nothing exits 1 instead of printing nothing and succeeding.
- **`jsonl_grep --count` answers a corpus question directly, and says what it reached.** "What
  values does this field actually take across every transcript?" is the DIRECT instrument for
  questions that otherwise get settled by inference, and answering it meant hand-rolling a walk
  over ~1500 files each time - one session built three designs for a value the corpus named in
  one command once it was finally asked. A NEGATIVE is the dangerous result, because "the field
  holds nothing" and "I never really looked" print the same, so the scan reports how many files
  it READ on stderr and exits 2 when it read none (1 when it read files and nothing matched). Point it at a directory and it walks the
  `*.jsonl` below it, streaming each file rather than loading it.
- **`guard_replay`'s sample shows you shapes, never proportions.** The corpus is walked file
  by file, so firings arrive grouped by project. The sample is therefore drawn EVENLY across them
  rather than from the front, which stops it being whichever project sorts first - but a spread
  sample is still a sample. Measured 2026-08-30: 40 of 557 firings put a residual at ~10 percent
  and all 557 put it at ~2, and the unread remainder held four firings that were a live regression
  in the guard being measured. Read the sample to learn what the firings look like, then classify
  the whole set when the answer is a ratio or a residual. YOU classify every firing; the figure
  you report comes from your verdicts. The same holds for a skimmed sample of ANY judged set
  (re-sent questions, review findings, labelled items), and the error runs in either direction:
  measured, 10 of 61 items read by eye gave "1-2 real catches of 10", while all 61 labelled against
  a fixed rubric gave 20 of 61, which flipped the recommendation built on it. Whenever you quote
  such a figure, say how it was produced (sample or full set, which corpus): one machine's habits
  are not a population.
  - **Jev shadow on that classification** (only when `jev_shadow.py status` exits 0; home
    `<plugin>/skills/meta-self-improve/`, launch via `hooks/run-python.sh`; procedure in its
    `references/jev-shadow.md`; all three files in a fresh `D=$(mktemp -d)` outside any repo, since
    they hold raw commands and their error output): replay with `--firings "$D/firings.jsonl"`,
    build the items with `jev_shadow.py items --site guard-firing --firings "$D/firings.jsonl"
    --hazard "<what the guard warns about>" --out "$D/items.jsonl"`, write YOUR verdict for every
    firing to `$D/verdicts.jsonl` FIRST (`{"id": "<firing id>", "verdict": {"real_hazard": true}}`,
    `false` for a false alarm; none left out, since the ratio counts every firing), then
    `jev_shadow.py run --site guard-firing --items "$D/items.jsonl" --verdicts "$D/verdicts.jsonl"`,
    then `rm -rf "$D"`. `run` prints counts only. Report the ratio from your own verdicts, whatever
    `run` printed or exited with.
- **`guard_replay` asks the second question too.** A guard's unit tests are written from the same
  imagination as the guard, so they cannot report its rate on real work or its precision when it
  speaks. Both have been measured wrong here after the tests were green: one arm fired on 7.8% of
  60,517 real commands because routine nested-sub-repo work is structurally identical to the
  hazard, and a later version was checked for its RATE alone, leaving 131 of its 344 firings with
  nothing to warn about. Rate and precision are separate columns for that reason. Read the
  precision figure for what it asks - "did a GATE refuse this call" is the right question for a
  guard about commands that cannot succeed as written, and the wrong one for a guard whose hazard
  is a plausible-but-wrong RESULT, which is never followed by a block and scores 0% while being
  useful. For such a guard, say in the report that the precision is unscoreable and adjudicate
  the firings by hand against their source. Fix the fire rate before re-pricing it: an excusing
  condition (an escaped form the author plainly meant) removes more false firings than any tuning.
- **`guard_replay` counts where a guard FIRES; it cannot count where it should have fired and
  stayed silent**, because the only predicate it runs is the guard itself. Before claiming a guard
  misses a lot, or proposing a smarter classifier for it, measure its misses (its recall) in three
  steps. (1) Write an ORACLE predicate deliberately WIDER than the guard, not copied from it; for
  each oracle hit compute the guard's production verdict through the guard's own text extraction,
  and return truthy only when the guard stayed silent, skipping calls that already use the tool
  the guard points at. Replayed with `--firings OUT.jsonl`, its firings are the candidate misses.
  (2) Group those candidates by the shape they matched: most are the oracle's own breadth, not
  misses. Measured 2026-09-24 on one guard, the wide count alone overstated real misses about 40x.
  (3) From the shapes write NARROW defect classes, count each exactly on the full commands, and
  read every row. Report the narrow, read counts, never the wide oracle count. Two traps: keep the
  command whole until the shape pass has re-matched it (a truncated command loses the matched
  span), and keep test fixtures that contain a pattern another guard blocks (a `pgrep -f` line,
  for instance) in a file, since inline in a Bash call they get the whole call refused.

- **`ci_wait` on a release: name the TAG and the event it fired on, and read an exit 2 before
  reporting.** A release workflow triggered by pushing a `v*` tag (`on: push: tags`) records its
  run as event `push` on the tagged commit, so wait with `--ref v2.3.0 --event push` (or with no
  `--event`, which counts every event but `schedule`). `--event release` is accepted, and on a
  workflow with no `release:` trigger it matches nothing: the wait ends `no-runs`, exit 2, while
  the release is running or already published. The tag resolves to the commit the branch push
  already tested, so those CI runs count too and may be green before the release run exists:
  confirm the summary names the release workflow (`Release=success`) before calling it
  published, and set `--timeout` (default 3600 s) to cover a full OS matrix plus the publish.
  Exit 2 means "could not tell", never "the release failed": it covers `timeout`, `no-runs`,
  `error` (gh failing for longer than `--error-grace`, 300 s), `pending-approval`,
  `stuck-queued`, `billing-blocked`, and a ref or flag it refused. Read the last line first (`<state>: <summary>` on
  stderr, `data.state` under `--json`), then the jobs (`gh run view <id> --json jobs`, the ids are
  in `data.runs`), and only then report: a `timeout` naming `Release=in_progress` is a release
  still running, and misreading it costs a re-tag of a published version or a debug session on
  green code.

- **`ci_wait` ends `no-runs` on a sha you pushed: ask whether anything could build that sha
  before suspecting CI.** Waiting longer or polling again rarely changes a `no-runs` (exit 2)
  after the grace period: usually no run exists and none ever will, and a retry loop on it is
  chasing an infrastructure fault that is not there. Check, in order: (1) run from the repo you
  pushed or name its checkout with `--repo DIR`, since `--ref` resolves in that `--repo`
  directory, else in the current directory's repo (with an `OWNER/NAME` `--repo`, a cwd whose
  remotes all name another repository is refused before any poll); (2) does that repo have a
  `.github/workflows` at all? If not, it has no CI: say so and stop, never report it green;
  (3) is the sha on a remote branch? `git branch -r --contains <sha>` empty means it was never
  pushed (`git rev-list --count @{u}..HEAD` non-zero shows unpushed commits), or a rebase (yours,
  or a peer session's `git pull --rebase` in a shared checkout) republished the change under a
  new sha: find it by content, its subject in `git log origin/<default> -- <path>`, and watch
  THAT sha; (4) read each workflow's `on:` block. `on: push: branches: [main, master]` plus a
  `pull_request` trigger against them matches nothing on a feature-branch push, though the sha is
  pushed and the repo has CI. Settle it by reading the runs themselves, never by the remote
  branch alone: `gh run list --repo <owner>/<repo> --json headSha,workflowName,event --limit 20`
  with no row carrying the full sha means no run exists. Then report that no workflow triggers on
  that branch, that the work has been validated by nothing beyond the local gate (none of CI's OS
  cells ran), and what would
  get a verdict: a merge to the default branch, or a pull request against it. A post-push notice
  that CI "is now running" checks that the repo has workflow files and a forge that runs them, not
  that they trigger on the branch, so it is no evidence a run exists.

- **`ci_wait` beside a long dispatched run on the same sha: wait for push CI with
  `--event push`.** With no `--event` the wait counts every run on the sha except a scheduled one,
  so a `workflow_dispatch` run started on the pushed commit (an integration or benchmark workflow
  that takes an hour) is counted too: the default wait ends `timeout` (exit 2) while every push
  job is already green, and the summary names only that run (`<workflow>=in_progress`). Wait for
  push CI with `--ref HEAD --event push`, and watch the dispatched run separately with a deadline
  sized to that workflow: a second `ci_wait --ref HEAD --event workflow_dispatch --timeout <s>`,
  or `gh run watch <run-id> --exit-status` under `timeout`.

- **The others encode the trap.** `ci_triage` strips ANSI, isolates a step (exit 2 if the step is absent, never a silent whole-log fallback) and fails a `--cmd` that exits non-zero even when it printed no keyword; `ci_wait` refuses
  a short sha before it polls, so the loop cannot spin on a filter that matches nothing; `jsonl_grep` parses
  JSONL by field, not by fragile text slicing.

## Building or enhancing a jig

Each jig is one import-safe core function plus a thin `argparse` CLI, shipped with a pytest test.
When a jig is insufficient in use, ENHANCE it (add a RED regression test for the gap, then fix),
rather than hand-rolling around it - so the tool matures and cannot silently regress.

**REQUIRED SUB-SKILLS for a jig's Python code:** load `bitranox:coding-python-data-architecture`
(typed models at the boundaries, enums for fixed values, no raw dicts passed around) and
`bitranox:coding-python-performance-review` (no per-item I/O in a loop, compiled regexes, bounded
memory, measured claims) before you write or edit a jig. Apply both to a new jig as a whole, and
on an edit to an existing jig to the code the edit touches. A bash launcher follows
`bitranox:coding-bash-clean-architecture` and `bitranox:coding-bash-reference` instead.

When a hook or jig settles a choice a later editor could plausibly undo (a rule tightened or
loosened, an alternative tried and dropped, a threshold picked from a measurement), record it in
the module docstring, in a block headed `Decisions:`:

```text
Decisions:
    - <what the code does, one sentence>. Why: <the reason>. Evidence: <measured | user |
      argued | inherited>: <where it came from>. Reopen if: <the condition that would change it>.
      Pinned by: <tests/test_file.py::test_name>
    - Rejected: <the alternative not taken>. Why: ... Reopen if: ...
```

Pin each decision with a test that fails when the decision is reverted, and name that test in the
block; a decision with no test says `Pinned by: none - <why no test can hold it>`. A skill's
SKILL.md text uses the per-skill ledger instead (`bitranox:meta-skill-writer`, Step 0b); code
gets no ledger file.

**Read the block, and the tests it names, before you change a jig's matcher, rule or
threshold.** A change that reverses an entry (tightens what an entry loosened, adopts a
`Rejected:` alternative) is made only when you can say what met its `Reopen if:`. Then rewrite
that entry instead of adding one that contradicts it, put that answer in its `Why:`, and keep a
test that fails on the behaviour you replaced: a narrowing keeps a test for what must still match.
The form you replaced stays in the block as a `- Rejected:` entry beside it. When the decision
you reverse has no entry (it predates the block, or only a commit records it), recover its reason
from that commit and the tests it added, write it into a `- Rejected:` entry naming the commit as
its source, and reverse it only when you can say why that reason no longer holds. The block
states what the code does now and why, with no history narrative: a commit is named only as the
source of a reason, and a commit message alone is no record, because the next editor reads the
module, not the log.
