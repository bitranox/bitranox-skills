# checklist-20260827 - `--apply` after the subcommand, and where a snapshot lands

## What the change is

Three defects in one surface, all of them about the safety switch on a tool that edits a firewall.

1. `--apply` was registered on the top-level parser only, while every documented example places it
   after the subcommand. Every documented mutation therefore failed.
2. The docs claimed all mutating verbs snapshot first. Two of the six do not, and cannot.
3. A snapshot defaulted to the current directory. It is a whole `config.xml`, so that writes
   password hashes, private keys and certificates wherever the operator happens to be standing.

## RED

- [x] The documented invocation fails. `pfsense.py --fw home dns add --name nas.example.com
      --ip 192.0.2.10 --apply` exits 2 with `error: unrecognized arguments: --apply`.
- [x] The snapshot claim is false for two verbs. `_guard_mutation` is the only caller of
      `do_snapshot` on a mutation path, and it is called by four commands (`dhcp rm`,
      `dhcp rm-static-arp`, `dns add`, `dns rm`). `cmd_table` and `cmd_snort_unblock` gate on
      `args.apply` and never call it.
- [x] The destination defaults to the cwd: `--snapshot-dir` defaulted to `"."`, and `snapshot
      --dir` likewise. Two 183 KB snapshots carrying 12 secret-bearing elements each were produced
      into a working directory during this change.
- [x] RED-verified by mutation: reverting the `inside_git_worktree` return contract makes
      `test_prepare_refuses_a_git_work_tree` fail (rc 1, 1 failed / 72 passed) and restoring it
      returns 73 passed. `__pycache__` cleared between runs so the source edit is not masked.

## GREEN

- [x] `--apply` and `--snapshot-dir` are a shared parent parser on all six mutating leaves, with
      `default=argparse.SUPPRESS` so a subparser cannot overwrite a value the top level parsed -
      without that, `--apply` given FIRST would be silently reset to False and a mutation the
      operator asked for would run as a dry run.
- [x] The documented invocation now parses and reaches the command.
- [x] Both the module docstring and `SKILL.md` now name the four verbs that snapshot and say why
      `table del` and `snort unblock` cannot.
- [x] The default destination is a private per-user state directory, mode 0700 on POSIX.
- [x] Writing a snapshot inside a git work tree is refused, with `--allow-repo-snapshot` as the
      override. Verified against the real `git` binary from inside a checkout: REFUSED. Known
      negative: a directory outside any checkout is allowed and created 0700.
- [x] The destination is resolved BEFORE the remote fetch, so a refusal does not first pull 180 KB
      of credentials over the wire.
- [x] `_run` now passes `encoding="utf-8", errors="replace"`. With `text=True` alone it decoded
      with the machine's locale codec, which returns `stdout=None` from a reader thread on Windows
      and raises on POSIX.

## REFACTOR

- [x] The first version of `inside_git_worktree` read `proc.returncode` / `proc.stdout`, but `_run`
      returns the tuple `(rc, stdout, stderr)`. The real call raised, the fail-open swallowed it,
      and the guard was inert while every unit test passed - because the test double had the wrong
      SHAPE. The double now returns the tuple, asserts it is invoked on `git`, and
      `test_the_git_double_matches_the_real_run_signature` fails if `_run`'s contract moves.
- [x] Fail-open is deliberate and stated: a machine without git must still be able to snapshot.
      It is the second layer, behind a default that already points outside any checkout.
- [x] No result lost against the baseline.

## Quality

- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] Addresses are RFC 5737 documentation ranges; no real host appears.
- [x] `name` and `description` unchanged; no routing keyword moved.
- [x] 73 tests pass, 8 of them new and covering both directions of the refusal.
