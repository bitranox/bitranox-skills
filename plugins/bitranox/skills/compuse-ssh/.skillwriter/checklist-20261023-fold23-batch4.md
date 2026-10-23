# skill-writer checklist - compuse-ssh (fold of memory rules into the skill)

- [x] Change: Authentication and host keys - inside the trusted-subnet bullet, new paragraph
      directly after 'NEVER apply it to internet/untrusted hosts - there use `accept-new` (new ok,
      changed rejected) or verify the fingerprint.' (extends that line with HOW to verify). Verified
      against ground truth: `qm guest exec <vmid> [<extra-args>]` executes a command via the guest
      agent -> skills/infra-proxmox/appendix-a-cli/qm-create-help.md:369-372. Guest agent must be
      installed+running in the guest and communication enabled in the VM's Options ->
      skills/infra-proxmox/ch10-qemu/vm-settings-advanced.md:88-102 (also
      ch16-backup-restore/_index.md:45 'enabled (agent: 1) and running'). `ssh-keygen -lf <pub>`
      prints '256 SHA256:<fp> <comment> (ED25519)' i.e. SHA256 by default -> ran locally on
      OpenSSH_10.2p1 against /etc/ssh/ssh_host_ed25519_key.pub.
- [x] Added after review: removal uses the `ssh-keygen -f <file> -R <name>` line ssh printed, and
      the destroy case spells out the `[host]:port` form.
- [x] Claims the source contradicts were dropped or corrected; machine-local figures, private names
      and incident history were not carried over.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against the pre-edit snapshot (partial for scenario
      1). Only a verbatim quote from the snapshot counts, so context inherited from this machine
      cannot satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files, in four rounds: after the edit,
      after the first review's fixes, after the delta review's fixes, and a final round on the
      questions the last fixes touched. Every scenario was answered with a quote from the new text
      on both tiers in every round; no NONE.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or recorded below.
- [x] Gaps closed or declined: closed - the removal command for port entries and for the destroy
      case (re-tested by quote-back); declined - mapping an address to a vmid and parsing qm guest
      exec output (Proxmox mechanics owned by infra-proxmox), incident handling after a mismatch
      (the rule is to stop).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, repo file paths or reserved examples.
