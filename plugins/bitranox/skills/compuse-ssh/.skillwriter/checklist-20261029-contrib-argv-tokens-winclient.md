# skill-writer checklist - compuse-ssh (three rows, one sentence)

- [x] Change: rows for building the remote command from a Python argv (`shlex.join`), building ssh
      path options or a ProxyCommand (refuse %, quotes, whitespace), and the Windows ssh CLIENT
      hanging inside an sshd session; one sentence in "Why inline remote commands break".
- [x] Mechanism claims measured locally, no remote host (OpenSSH 10.2p1):
      `ssh -G -o UserKnownHostsFile=/kh%h host.example` -> `/khhost.example`; top-level `%%h` ->
      `/kh%h`; a ProxyCommand `ssh -G -o UserKnownHostsFile=/kh%%h %h >&2; exit 1` printed
      `/khhost.example` (double expansion). ssh_config(5): "one or more files ... separated by
      whitespace". The remote shell's re-split simulated through `sh -c`: space-joined
      `printf %s, a b c\d` -> `a,b,cd,`; `shlex.join` -> `a b,c\d,`.
- [x] Not reproducible here (Windows only), worded as observed with the versions named: ssh.exe
      not exiting inside an sshd session, the ssh-add agent side effect, single quotes in a
      Windows ProxyCommand.
- [x] RED text check (origin/master): `shlex.join` 0, `ProxyCommand` 0, `ssh.exe` 0.
- [x] GREEN quote-back: "Join it with `shlex.join(argv)`"; "Refuse `%`, double quotes and (for a
      known-hosts path) whitespace in those paths when the configuration is LOADED"; "Run client
      probes in the console session instead".
- [x] Description: unchanged (477 chars).
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the first SKILL.md edit.
- [x] Behavioural probes: none dispatched (this batch ran under a no-subagent rule), so RED and
      GREEN are TEXT checks of the skill file: each rule's key fragment counted in
      `git show origin/master:<file>` (0) and in the edited file (>=1). Recorded as a text check,
      not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] ASCII only (no byte above 0x7F in the diff), present tense (history-phrase finder: 0 hits in
      added lines), no private host, VMID, cluster or repo name in the added text.
