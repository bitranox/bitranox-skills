---
name: computer-use-ssh
description: Use when running commands over SSH or driving a remote host - checking or killing remote processes, quoting an inline remote command, backgrounding a remote command, or running remote Windows PowerShell.
---

# computer-use-ssh

## Quick reference

| Situation | Rule |
|-----------|------|
| Check/kill a remote process by name | `ssh host '... pgrep/pkill -f X ...'` makes the remote shell's OWN argv contain `X`, so it self-matches (false positive; `pkill` kills your ssh shell mid-command). Prefer signals that can't match an argv: `systemctl is-active <unit>`, a cgroup dir, a listening port (`ss -ltnH \| grep :PORT`), pidfile + `kill -0`. |
| Must use pgrep/pkill remotely | Bracket the first char (`[x]pattern`) AND keep that keyword out of any `echo` label in the same command (the label re-introduces the literal). To be sure, exclude the current shell: `... \| grep -vw "$$"`. |
| Quoting an inline remote command | Nested quotes and `awk '{print $1}'` / `cut -d" "` inside `ssh '...'` get eaten by the outer shell (the `$1` or the `"` is consumed). Prefer a detached on-host script (scp it, then run it) over a long inline one-liner. |
| Backgrounding a remote command | `ssh host '... &'` drops the session (exit 255) when the backgrounded process holds the tty/pipe. Use `setsid CMD </dev/null >/dev/null 2>&1 &` or a detached on-host script. |
| Remote Windows PowerShell | NEVER inline `ssh host 'powershell -Command "...\|..."'` - the pipe and quotes pass through bash -> ssh -> `cmd.exe` and cmd eats them. ALWAYS write a `.ps1` and run it with `-File`. |

## Why inline remote commands break

A command in `ssh host '...'` is parsed by the LOCAL shell, then the REMOTE shell, then (for Windows) `cmd.exe`, then PowerShell. Each layer strips a level of quoting and can self-match patterns. A file moved with `scp` and run by path crosses none of those layers, which is why a detached on-host script beats a clever one-liner for anything non-trivial.

## Hook / script

`block-pgrep-self-match` (PreToolUse on Bash) catches the echo-label pgrep self-match, including `ssh ... 'pgrep ...'`. For remote PowerShell, a `runps.sh`-style wrapper that syntax-checks the `.ps1` with `pwsh` locally, then does the scp + `-File` run, avoids the cmd-quoting trap.
