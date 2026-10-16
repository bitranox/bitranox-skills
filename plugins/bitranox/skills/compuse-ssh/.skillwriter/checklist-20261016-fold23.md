# skill-writer checklist - compuse-ssh (2026-10-16, fold23)

- [x] Change: contradiction resolved - the key-setup walkthrough (Linux/macOS step 2: `ssh-copy-id`
      or append by hand; Windows step 3: `cat >> ~/.ssh/authorized_keys`) now scopes itself away
      from Proxmox VE nodes and points at the "Installing a key on a Proxmox VE node" bullet, which
      says not to rely on `ssh-copy-id` or `>>` there. Ground truth: the bundled Proxmox VE docs
      (`infra-proxmox/ch05-cluster-manager/cluster-network.md`, section 5.9.1) state "the root
      user's authorized_keys file gets linked to /etc/pve/priv/authorized_keys", so the generic
      walkthrough stays correct for ordinary hosts and the Proxmox bullet governs that node type.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded
      the skill
- [x] RED (text check of the artifact): before this edit the walkthrough prescribed `ssh-copy-id`
      and `cat >>` with no Proxmox caveat while the bullet above forbade both on a Proxmox node
      (the verifier's finding). Behavioural RED replaced on purpose because the rule is in the
      always-loaded memory index of the authoring machine (inherited coverage)
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): no rules to add;
      contradictions: Proxmox bullet vs key-setup walkthrough -> resolved. SKILL.md:59 "do not rely
      on `ssh-copy-id` or `>>`: read the file, add the line, and write it back WHOLE" now governs;
      SKILL.md:112-113 "On a Proxmox VE node use the write-it-whole procedure above instead" and
      SKILL.md:123 "(not on a Proxmox VE node: there use the write-it-whole procedure above)" no
      longer disagree. Step-4 scan of SKILL.md (including the earlier pass's PowerShell-row rule at
      SKILL.md:20 and the wrapper sentence at SKILL.md:150): no non-ASCII punctuation, no private
      hosts or paths; every "session" hit means an SSH session.
- [x] Quick reference re-pad checked: after collapsing whitespace, the only table row whose cells
      differ from HEAD is "Remote Windows PowerShell" (the earlier pass's rule); the other 18 rows
      are whitespace-only. `git diff -w` additionally shows the separator row, whose second dash
      run grew from 712 to 776 to match the widened column - width only, no content.
- [x] Gaps closed or declined: none.
- [x] Description measured: unchanged (477 characters)
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
