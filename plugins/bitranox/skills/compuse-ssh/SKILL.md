---
name: compuse-ssh
description: Use when running commands over SSH or driving a remote host - checking or killing remote processes, quoting an inline remote command, backgrounding a remote command, running remote Windows PowerShell, an SSH login asking for a password, a changed or unknown host key ("host key verification failed", "remote host identification has changed"), setting up SSH key-based auth, a remote command failing with exit code 255, or a slow, stalled, or failed remote download or transfer.
---

# computer-use-ssh

## Quick reference

| Situation                                                                        | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Check/kill a remote process by name                                              | `ssh host '... pgrep/pkill -f X ...'` makes the remote shell's OWN argv contain `X`, so it self-matches (false positive; `pkill` kills your ssh shell mid-command). Prefer signals that can't match an argv: `systemctl is-active <unit>`, a cgroup dir, a listening port (`ss -ltnH \| grep :PORT`), pidfile + `kill -0`.                                                                                                                                                                                                                                                                                                                                                                              |
| Must use pgrep/pkill remotely                                                    | Bracket the first char (`[x]pattern`) AND keep that keyword out of any `echo` label in the same command (the label re-introduces the literal). To be sure, exclude the current shell: `... \| grep -vw "$$"`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Quoting an inline remote command                                                 | Nested quotes and `awk '{print $1}'` / `cut -d" "` inside `ssh '...'` get eaten by the outer shell (the `$1` or the `"` is consumed). Prefer a detached on-host script (scp it, then run it) over a long inline one-liner.                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Backgrounding a remote command                                                   | `ssh host '... &'` drops the session (exit 255) when the backgrounded process holds the tty/pipe. Use `setsid CMD </dev/null >/dev/null 2>&1 &` or a detached on-host script.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Long remote reload/restart over SSH                                              | A long step (`services_*_configure()`, `nginx -t && reload`, `apt upgrade`) can outlive the client `ConnectTimeout`; the remote command keeps running ORPHANED and SUCCEEDS. Never infer failure from a dropped SSH connection - re-query the real state afterward (`systemctl is-active`, the listening port, DNS, an HTTP probe).                                                                                                                                                                                                                                                                                                                                                                     |
| Slow/large remote download (GB image, model, tarball)                            | Detach it so the client `ConnectTimeout` can't kill it mid-transfer: `scp` a script that does the download, launch it `setsid bash script >LOG 2>&1 </dev/null &`, then poll LOG + the file SIZE from separate short ssh calls. CONFIRM it moves: measure the byte delta over ~10s - a plausible rate (MB/s for a GB payload), NOT 0. Resume across retries with `curl -C -`. Do NOT put a `pkill -f <name>` in the SAME command that launches `<name>`: the launcher's own argv contains `<name>`, so pkill kills the launcher before `setsid` runs.                                                                                                                                                   |
| ANY remote command fails - ROOT-CAUSE it, never wave it off                      | Exit 255 = ssh ITSELF failed (connect, auth, host key, dropped session) - the remote command may never have run; any OTHER code IS the remote command's own exit. Get evidence before acting: read stderr, rerun a no-op probe with `ssh -v host 'echo ok'` (shows the DNS/connect/auth/host-key stage), then read the REMOTE state and logs (`systemctl status`, `journalctl -u <unit>`, the app's own log). "Flaky network" is a hypothesis to TEST with that probe, never a diagnosis to assume - a blind retry of a mutating command (restart, install, migration step) double-fires it.                                                                                                            |
| A remote download "stalls"/"fails" - ROOT-CAUSE it, do not assume "slow network" | 0 bytes + `curl: (22) ... 404` is a WRONG URL/asset name, not flakiness - retrying or detaching a wrong URL wastes hours. Read the actual curl exit code + HTTP status FIRST; if unsure of the asset, fetch the tool's own installer/source to get the exact name (e.g. ollama publishes `ollama-linux-amd64.tar.zst`, not `.tgz`). Only call it "slow" once you have SEEN a plausible partial transfer.                                                                                                                                                                                                                                                                                                |
| Remote Windows PowerShell                                                        | NEVER inline `ssh host 'powershell -Command "...\|..."'` - the pipe and quotes pass through bash -> ssh -> `cmd.exe` and cmd eats them. ALWAYS write a `.ps1` and run it with `-File`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Host wants a password                                                            | NEVER ask for, type, or accept an SSH password - it leaks into the transcript, shell history, and logs. Use key auth - and `-i <keypath>` ALONE is not enough: on key rejection ssh falls back and PROMPTS, hanging an unattended run. Always `ssh -i <keypath> -o BatchMode=yes -o PreferredAuthentications=publickey` so it fails fast instead. If there is no key, STOP and propose the user set one up (see below).                                                                                                                                                                                                                                                                                 |
| Remote interactive `sudo`, or `ssh -t`                                           | `-t` allocates a pty only when the CLIENT's own stdin is a terminal. From a pipe, an editor's run-shell or an unattended job runner ssh runs the command WITHOUT one, so remote interactive `sudo` has no tty to prompt on and fails as repeated `Permission denied` - which reads as a wrong password. ssh's OWN password prompt is unaffected there (it reads `/dev/tty`, which a redirected stdin does not take away), so "the login works but `sudo` does not" is how you IDENTIFY this - it is a diagnostic, never a licence to feed a password in; the no-password rule below still binds. Reach the step a way that needs no tty: `sudo -n`, a NOPASSWD rule, or a key for the account you need. |
| Connecting on your OWN/trusted subnet                                            | Hosts get reimaged, so keys change. Turn the CHECK off but keep the FILE: `ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=~/.ssh/known_hosts_fleet ...`, scoped in `~/.ssh/config` to the subnet ranges ONLY. NOT `/dev/null` - that is what re-prints `Warning: Permanently added ...` on every call and corrupts merged-output reads (next rows). Untrusted hosts: `accept-new`.                                                                                                                                                                                                                                                                                                               |
| A no-op probe to test REACHABILITY                                               | Use `ssh host 'echo ok'` or `ssh host 'exit 0'`, NEVER `ssh host true`. The default Windows ssh shell is `cmd.exe`, which has NO `true` builtin - it exits non-zero, so every HEALTHY Windows host reports unreachable. Pick a verb valid on BOTH shells and judge by the ssh EXIT CODE, not by matching output text.                                                                                                                                                                                                                                                                                                                                                                                   |
| Reading a remote FILE into a variable                                            | Keep stdout and stderr SEPARATE (`capture_output` / `2>/dev/null`). A helper that MERGES them splices the ssh client's own `Warning: Permanently added '<host>' to the list of known hosts.` into the file CONTENT - and only on the FIRST connect, so the corruption is intermittent and reads as bad data. A byte-for-byte compare then fails for a file that is fine. The warning repeats forever only when `UserKnownHostsFile=/dev/null`; with a persistent file it appears once per host.                                                                                                                                                                                                         |
| Key auth refused on a FRESH Alpine account                                       | `adduser -D <user>` leaves the shadow password field `!`, which sshd treats as a LOCKED account and rejects pubkey auth despite a valid `authorized_keys`. Set the field to `*` to unlock. The symptom points at keys; the cause is the account state.                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Picking a SHARED key path that exists on several boxes                           | Select by READABILITY, not existence: `os.access(p, os.R_OK)` / `test -r`. A shared credentials path can be mounted but root-only on THIS box, so an existence test returns a key you cannot load - ssh then fails `Load key: Permission denied` -> `Permission denied (publickey)` with EMPTY stdout, and the cause surfaces far downstream as "the command returned nothing".                                                                                                                                                                                                                                                                                                                         |
| `scp` to a DIFFERENT remote user                                                 | scp carries the user INSIDE the path (`root@host:/p`), not as a flag, so a `--user`-style option never reaches it. Parse the user from the path when resolving which key to use, or a `root@` destination silently resolves the wrong user's key and every copy fails `Permission denied (publickey)`.                                                                                                                                                                                                                                                                                                                                                                                                  |

## Why inline remote commands break

A command in `ssh host '...'` is parsed by the LOCAL shell, then the REMOTE shell, then (for Windows) `cmd.exe`, then PowerShell. Each layer strips a level of quoting and can self-match patterns. A file moved with `scp` and run by path crosses none of those layers, which is why a detached on-host script beats a clever one-liner for anything non-trivial.

An SSH session is a flaky external resource: it can drop, hang, or time out mid-command. Never infer failure from a dropped connection - retry under a timeout and re-query the real state. For the self-healing patterns (retry+backoff, timeouts, graceful degradation), see `bitranox:coding-resilience`.

**The remote tools are not the ones you have locally.** On a BSD host - FreeBSD, pfSense, or a macOS CI runner - `grep` and `sed` are the BSD builds, and GNU backslash escapes are NOT special there: `\t`, `\d`, `\s`, `\+` match literal characters, and a pattern that ENDS in a backslash aborts with `grep: trailing backslash (\)`. That compounds with the quoting layers above, because local-bash -> ssh -> remote-`sh` can mangle a backslash before grep ever sees it, so a pattern verified locally arrives malformed. Use POSIX classes and literal characters instead (`[[:space:]]`, `[[:alnum:]]`, an actual tab), or - better for anything structured - `scp` the file back and parse it in Python, where you get real regex and real error messages.

## Authentication and host keys

- **Never ask for, type, or accept an SSH password.** A password in a command or prompt leaks into
  the session transcript, shell history, and logs. Use key-based auth only - and never read or
  `cat` the private key either; you reference it, you do not look at it.
- **Log in with a key path, never a secret.** The user creates an SSH key, stores the private key
  with owner-only permissions (`chmod 600`) in a safe location OUTSIDE any repo, and passes you only
  the PATH. Connect with `ssh -i /safe/path/id_key user@host` - you use the key by path and never
  see its contents or any passphrase. (More secure variant: a passphrase-protected key loaded into
  `ssh-agent`; you use the agent, the passphrase never reaches you.)
- **If a host still needs a password, STOP and propose the setup** - do not work around the prompt.
  Ask the user to: generate a key, add its public half to the host's `~/.ssh/authorized_keys`, store
  the private key safely, and hand you the path. Then log in by path.
- **Installing a key for root when only the sudo user can log in.** Ubuntu's default
  `PermitRootLogin prohibit-password` accepts a root KEY but refuses a root PASSWORD, so a fresh host
  gives you the sudo account only - and writing root's `authorized_keys` through `sudo` needs the tty
  a non-terminal client cannot get (see the table). Append the public half to the SUDO USER's OWN
  `~/.ssh/authorized_keys` instead (no `sudo`, no `-t`), or paste it at the console; then work from
  that account with `sudo -n`, or install root's key from a session that does have a tty.
- **Host keys on the user's OWN/trusted subnet: accept new AND changed, into a SEPARATE known_hosts
  file - not `/dev/null`.** Hosts there get reimaged, so a key legitimately changes and the
  "HOST IDENTIFICATION HAS CHANGED" error is just noise. Turn the CHECK off, but keep the FILE:
  ```
  Host 192.0.2.* 198.51.100.*
      StrictHostKeyChecking no
      UserKnownHostsFile ~/.ssh/known_hosts_fleet
  ```
  SCOPE it to those ranges in `~/.ssh/config`, never globally. A separate file keeps the churn out
  of the real `~/.ssh/known_hosts` while still recording each key ONCE.

  **`UserKnownHostsFile=/dev/null` is what produces the `Warning: Permanently added ...` line on
  EVERY call.** ssh is not being chatty; it is recording the key permanently, into the bit bucket,
  so every connect is a first connect. That is the same line that splices into file content through
  a stdout/stderr-merging helper (see the table above) - so `/dev/null` CAUSES that corruption, and
  a persistent file ends it after the first connect instead of forcing you to discard stderr.

  A changed key then fails once. Self-heal rather than reverting to `/dev/null`: drop the stale
  entry and retry exactly once -
  `ssh-keygen -R <host> -f ~/.ssh/known_hosts_fleet`. Gate that retry on the exit status AND on
  stderr matching `REMOTE HOST IDENTIFICATION HAS CHANGED|Host key verification failed`; a bare
  retry re-runs a MUTATING remote command twice.

  **A command-line `-o StrictHostKeyChecking=no` has NO scope** - it disables the check for
  whatever host that invocation is pointed at, so a script carrying the flag weakens every host
  it is ever aimed at, not just the trusted subnet. Prefer the `~/.ssh/config` block above and
  let the script call plain `ssh`; if the flags must be inline, have the script refuse a target
  outside the intended ranges before it connects.

  This is a conscious trade-off (you own the network). NEVER apply it to internet/untrusted hosts -
  there use `accept-new` (new ok, changed rejected) or verify the fingerprint.

### Setting it up (ask the user's OS, then walk them through it)

When a host needs auth, first ask which operating system the user is on, then guide them. Afterwards
they hand you only the private-key PATH and you log in with `ssh -i <keypath> user@host`.

**Linux / macOS:**
1. Generate a key: `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519` (a passphrase + `ssh-agent` is the
   safer choice; a no-passphrase key works but is a credential at rest, so store it well).
2. Install the public half on the host: `ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host` (or append
   `id_ed25519.pub` to the host's `~/.ssh/authorized_keys` by hand).
3. Private key stays at `~/.ssh/id_ed25519` (`chmod 600`); the user gives you that path.

**Windows:**
1. Ensure the OpenSSH client exists (Windows 10/11 usually ship it; check with `ssh -V`). If missing,
   install it - winget: `winget install Microsoft.OpenSSH.Beta`; or the built-in optional feature in
   an elevated PowerShell: `Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0`.
2. Generate a key: `ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\id_ed25519`.
3. There is no `ssh-copy-id` on Windows - install the public key on the host by hand, e.g.
   `type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh user@host "cat >> ~/.ssh/authorized_keys"`.
4. Private key is at `C:\Users\<you>\.ssh\id_ed25519`; the user gives you that path.

### Setting up the SSH *server* on the host (per OS, if it has none)

If the host has no SSH server yet, walk the user through enabling one (ask the OS):

**Linux (Debian/Ubuntu):** `sudo apt install openssh-server && sudo systemctl enable --now ssh`
(RHEL/Fedora: `sudo dnf install -y openssh-server && sudo systemctl enable --now sshd`).

**macOS:** built in - enable Remote Login: `sudo systemsetup -setremotelogin on`
(or System Settings > General > Sharing > Remote Login).

**Windows (elevated PowerShell):**
```
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
# open the firewall if the rule is missing:
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```
The default ssh shell on Windows is `cmd.exe`; to make it PowerShell set the `DefaultShell` value under `HKLM:\SOFTWARE\OpenSSH`.

## Hook / script

`block-pgrep-self-match` (PreToolUse on Bash) catches the echo-label pgrep self-match, including `ssh ... 'pgrep ...'`. `warn-inline-powershell` (PreToolUse on Bash) is the one that fires on an inline remote `-Command`, and it points back here.

For remote PowerShell, write yourself a small wrapper - no such script ships here - doing these two steps:

```bash
# 1. syntax-check locally, so a typo fails here rather than half-running on the target
pwsh -NoProfile -Command '$null = [ScriptBlock]::Create((Get-Content -Raw ./job.ps1))'
# 2. ship it and run the FILE - a path has nothing for cmd.exe to eat
scp ./job.ps1 user@host:C:/Windows/Temp/job.ps1
ssh user@host 'powershell -ExecutionPolicy Bypass -File C:/Windows/Temp/job.ps1'
```

That sequence is what avoids the cmd-quoting trap.
