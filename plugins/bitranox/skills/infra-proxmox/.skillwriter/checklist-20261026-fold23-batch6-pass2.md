# skill-writer checklist - infra-proxmox (memory rules folded in)

- [x] Rule: Avoid cpu: host because it exposes vmx and Win11 then turns on VBS (about 25% CPU
      penalty); use a named no-vmx model such as IvyBridge or x86-64-v2-AES (not kvm64, which will
      not boot Win11); confirm with Win32_DeviceGuard VirtualizationBasedSecurityStatus (2 = VBS
      on, 0 = off), knowing that registry HVCI/Credential Guard toggles do not clear it and only
      bcdedit hypervisorlaunchtype off does; Docker must then use process isolation, because
      hyperv isolation needs the same hypervisor.
      Where: SKILL.md, 6. Troubleshooting Quick Reference, row **Windows VM ~25% slower** (existing row's
      Diagnosis cell replaced, extended)
- [x] Rule: Inside the unprivileged CT also run dpkg-divert --rename --add
      /usr/sbin/apparmor_parser, so Docker no longer thinks AppArmor is usable, and put that
      divert in the guest's post-deploy hook or a rebuild silently loses Docker; a privileged CT
      fails differently ('apparmor_parser: Access denied') and needs only the unconfined profile
      plus an empty lxc.cap.drop, no divert, and keyctl=1 does nothing there.
      Where: SKILL.md, 6. Troubleshooting Quick Reference, new row **Docker in a PRIVILEGED CT** directly
      after the existing **Docker in an UNPRIVILEGED CT** row (existing row untouched:
      ALREADY+cut, only the skeptic's 'lost' privileged-CT fix added)
- [x] Rule: A bare PVE 9 / Debian 13 install has no git, rsync or rsyslog (so no
      /var/log/mail.log), so install git and rsync first and verify mail with journalctl -t
      postfix/smtp requiring status=sent; pct restore keeps the source's net0 MAC, so restore with
      --unique 1 or set a fresh MAC before the first start and check pct config | grep ^net0;
      vzdump --notes-template requires --storage and is refused with --dumpdir; on a laptop node a
      missing iw makes a radio look dead, so read /sys/class/rfkill instead.
      Where: restored-guest-identity.md for the MAC half, see the de-cloning row), 6. Troubleshooting
      Quick Reference, new rows **Fresh PVE 9 node gaps** and **vzdump notes-template 400** (MAC
      half routed to **Restored CT as a new machine**)
- [x] Rule: The dhclient timeout under ifreload -a -n (there is no --test) is a no-act artifact,
      not a lease failure; prove DHCP with dhclient -1 -sf /bin/true -v <iface> and kill that
      probe by PID afterwards because a successful run daemonizes; neither ifreload -a nor -f
      restarts the running client, so a dhclient.conf edit lands only at a reboot and is verified
      by the content and mtime of resolv.conf; apply remotely only after arming a systemd-run
      --on-active rollback, launch the apply detached with systemd-run --no-block, and cancel the
      rollback only once the new config is verified.
      Where: host-networking.md, SKILL.md: 2. Safety Protocols row **Network changes** (pointer
      appended), 6. Troubleshooting new row **DHCP dry-run says timeout**, Which File table new
      row 'Change node networking over SSH'; references/host-networking.md sections 'Dry run, DHCP
      and dhclient.conf' and 'Applying a change on a remote node'
- [x] Rule: Set options bonding fail_over_mac=1 in /etc/modprobe.d (ifupdown2 has no attribute for
      it), and override PVE's shipped policy bridge_set_static_mac_from_port=yes with an
      /etc/network/ifupdown2/policy.d JSON setting it to no, then reboot because ifreload cannot
      unpin a live bridge; verify that /sys/class/net/vmbr0/addr_assign_type reads 1 (not 3) and
      that vmbr0's MAC equals bond0's, then test failover behind an auto-restore, expecting guests
      to stay dark on the WLAN and the host's DHCP address to possibly change.
      Where: host-networking.md, 6. Troubleshooting new row **WLAN bond slave: no traffic**;
      references/host-networking.md section 'Bridge over an active-backup bond with a WLAN standby
      slave'
- [x] Rule: Do not use a wpa-conf line, because under ifreload the ifupdown hook starts the
      supplicant and kills it in the same second; run the packaged wpa_supplicant@<iface>.service
      with /etc/wpa_supplicant/wpa_supplicant-<iface>.conf and a drop-in adding Restart=on-failure
      and RestartSec=10, declaring the interface inet manual; on the jailed host the handshake
      failure is a blocked crypto module (ccm/cmac/gcm, loaded by alias), so read journalctl -t
      modulejail and allowlist those modules, as infra-modulejail describes.
      Where: host-networking.md, 6. Troubleshooting new row **WLAN drops after ifreload**;
      references/host-networking.md section 'WLAN that must stay associated: run the supplicant as
      a unit'
- [x] Rule: Do not put bond-primary in the stanza: ifupdown2 3.3.0 aborts the whole bond when it
      names a missing NIC ('not present in cache', and then the bridge port bond0 does not exist),
      whereas a missing bond-slaves entry is merely skipped; set the primary in post-up via echo
      <nic> > /sys/class/net/bond0/bonding/primary 2>/dev/null || true; ifquery -a -i checks
      syntax only, so prove the missing-NIC and present-NIC cases by running the node's own
      ifupdown2 under unshare -mn with veth pairs named like the real NICs.
      Where: host-networking.md, 6. Troubleshooting new row **Bond down: slave NIC absent**;
      references/host-networking.md section 'A bond that must survive a missing slave NIC'
- [x] Rule: The enterprise repo's 401 makes apt-get update exit 100 (a hard error), so every run
      fails; after a major upgrade, check the deb822 pve-enterprise.sources as well as the old
      .list, because it arrives enabled; disable it with Enabled: no, keeping pve-no-subscription
      as the source; verify with apt-get update; echo rc=$? and require rc=0, since a failing
      updater looks just like one with nothing to do.
      Where: SKILL.md, 6. Troubleshooting new row **apt-get update exits 100**
- [x] Rule: Offline against the stopped rootfs (pct mount, or the path from pct config): give it a
      fresh net0 MAC (pct restore --unique 1 or pct set); blank /etc/machine-id and delete
      /var/lib/dbus/machine-id; regenerate SSH host keys and chown them to the idmap base on an
      unprivileged CT; set hostname, nameserver/searchdomain and a description that no longer
      describes the source; grep every unit for the source's checkout or deploy path, because a
      service may run from it; blank the application's site data and advertised addresses; archive
      what you remove to a dated tar; then verify from ground truth with new key fingerprints and
      idmap-base ownership.
      Where: restored-guest-identity.md, 6. Troubleshooting new row **Restored CT as a new machine**;
      Which File table new row 'Turn a restored CT into a new machine'; whole new file
      references/restored-guest-identity.md
- [x] Rule: Restart the CT (its cgroup is recreated at start, so the peak begins fresh), run its
      heaviest phase, then read /sys/fs/cgroup/lxc/<vmid>/memory.peak and memory.events; a peak
      equal to the limit with high events counting means it is undersized even while oom_kill is
      0; size from the peak with headroom and require high to stay 0; echo 0 > memory.peak resets
      only that file descriptor, so it does not give a fresh reading.
      Where: SKILL.md, 6. Troubleshooting new row **CT memory limit / rare OOM**
- [x] Rule: Look for a boot-time SATA link exception or downshift in the kernel log, which can
      leave the primary GPT unreadable while the secondary GPT is intact; repair in place with
      sgdisk --backup=FILE (kept off that disk), sgdisk -p, --load-backup, sgdisk -v, partprobe
      and udevadm settle; confirm the label with zdb -l or blkid UUID_SUB, then zpool online
      <pool> <guid> and let it resilver; never zpool replace and never clone a sibling's GPT; a
      climbing UDMA_CRC_Error_Count with otherwise clean SMART means a cable fault, so fix the
      cable and confirm the count stops climbing on every member.
      Where: zfs-member-label-missing.md, 6. Troubleshooting new row **ZFS member label missing**; Which
      File table new row 'Repair a ZFS member with no label'; whole new file references/zfs-
      member-label-missing.md
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts.
- [x] GREEN quote-back on haiku and opus against the edited files (11 questions), again after the
      review fixes for every question, and a third time for the 0 questions the fix-delta fixes
      touched: every answer quoted the edited text, no NONE. Quotes were substring-checked against
      the files; the pre-edit snapshots fail the same check.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed or
      declined with evidence by the fixer, and the fix delta re-reviewed.
- [x] Each GREEN Skill gaps list triaged: 4 closed in the text, 18 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
