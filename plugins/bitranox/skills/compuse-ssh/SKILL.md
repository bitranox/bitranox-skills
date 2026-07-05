---
name: compuse-ssh
description: Use when running commands over SSH or driving a remote host - checking or killing remote processes, quoting an inline remote command, backgrounding a remote command, running remote Windows PowerShell, an SSH login asking for a password, a changed or unknown host key ("host key verification failed", "remote host identification has changed"), or setting up SSH key-based auth.
---

# computer-use-ssh

## Quick reference

| Situation                             | Rule                                                                                                                                                                                                                                                                                                                                |
|---------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Check/kill a remote process by name   | `ssh host '... pgrep/pkill -f X ...'` makes the remote shell's OWN argv contain `X`, so it self-matches (false positive; `pkill` kills your ssh shell mid-command). Prefer signals that can't match an argv: `systemctl is-active <unit>`, a cgroup dir, a listening port (`ss -ltnH \| grep :PORT`), pidfile + `kill -0`.          |
| Must use pgrep/pkill remotely         | Bracket the first char (`[x]pattern`) AND keep that keyword out of any `echo` label in the same command (the label re-introduces the literal). To be sure, exclude the current shell: `... \| grep -vw "$$"`.                                                                                                                       |
| Quoting an inline remote command      | Nested quotes and `awk '{print $1}'` / `cut -d" "` inside `ssh '...'` get eaten by the outer shell (the `$1` or the `"` is consumed). Prefer a detached on-host script (scp it, then run it) over a long inline one-liner.                                                                                                          |
| Backgrounding a remote command        | `ssh host '... &'` drops the session (exit 255) when the backgrounded process holds the tty/pipe. Use `setsid CMD </dev/null >/dev/null 2>&1 &` or a detached on-host script.                                                                                                                                                       |
| Long remote reload/restart over SSH   | A long step (`services_*_configure()`, `nginx -t && reload`, `apt upgrade`) can outlive the client `ConnectTimeout`; the remote command keeps running ORPHANED and SUCCEEDS. Never infer failure from a dropped SSH connection - re-query the real state afterward (`systemctl is-active`, the listening port, DNS, an HTTP probe). |
| Remote Windows PowerShell             | NEVER inline `ssh host 'powershell -Command "...\|..."'` - the pipe and quotes pass through bash -> ssh -> `cmd.exe` and cmd eats them. ALWAYS write a `.ps1` and run it with `-File`.                                                                                                                                              |
| Host wants a password                 | NEVER ask for, type, or accept an SSH password - it leaks into the transcript, shell history, and logs. Use key auth: `ssh -i <keypath>`. If there is no key, STOP and propose the user set one up (see below).                                                                                                                     |
| Connecting on your OWN/trusted subnet | Hosts get reimaged, so keys change. Accept new AND changed: `ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ...`, scoped in `~/.ssh/config` to the subnet ranges ONLY. Untrusted hosts: `accept-new`.                                                                                                              |

## Why inline remote commands break

A command in `ssh host '...'` is parsed by the LOCAL shell, then the REMOTE shell, then (for Windows) `cmd.exe`, then PowerShell. Each layer strips a level of quoting and can self-match patterns. A file moved with `scp` and run by path crosses none of those layers, which is why a detached on-host script beats a clever one-liner for anything non-trivial.

An SSH session is a flaky external resource: it can drop, hang, or time out mid-command. Never infer failure from a dropped connection - retry under a timeout and re-query the real state. For the self-healing patterns (retry+backoff, timeouts, graceful degradation), see `bitranox:coding-resilience`.

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
- **Host keys on the user's OWN/trusted subnet: accept new AND changed.** Hosts there get reimaged,
  so a host's key legitimately changes and the "HOST IDENTIFICATION HAS CHANGED" error is just noise.
  For that subnet, skip the check and the known_hosts pinning:
  `ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null user@host`. SCOPE it so it can only
  ever hit that subnet - put it in `~/.ssh/config` keyed to the subnet IP ranges, never globally:
  ```
  Host 192.168.0.* 10.0.0.*
      StrictHostKeyChecking no
      UserKnownHostsFile /dev/null
  ```
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

`block-pgrep-self-match` (PreToolUse on Bash) catches the echo-label pgrep self-match, including `ssh ... 'pgrep ...'`. For remote PowerShell, a `runps.sh`-style wrapper that syntax-checks the `.ps1` with `pwsh` locally, then does the scp + `-File` run, avoids the cmd-quoting trap.
