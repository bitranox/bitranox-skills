---
name: infra-proxmox
description: Use when configuring, managing, or troubleshooting Proxmox VE - installation, host administration, clusters, VMs, containers, storage, Ceph, SDN, firewall, user management, HA, backups, notifications, and CLI tools (pvecm, qm, pct, pvesm, pveceph, ha-manager, pvesh, vzdump). Covers Proxmox VE 9.1.2.
---

# Proxmox VE Operations Reference (Release 9.1.2)

Nodes, guests, and services can be down, unreachable, or vanish mid-operation. Never assume one is
up: re-query real state, retry under a timeout, and degrade gracefully. For the self-healing
patterns, see `bitranox:coding-resilience`.

---

## 1. Cluster Configuration (Auto-Detect)

| Check            | Command                                                                                         |
|------------------|-------------------------------------------------------------------------------------------------|
| **Environment**  | `pveversion --verbose` (full component versions: kernel, pve-manager, corosync, qemu-server)    |
| **Nodes**        | `pvecm nodes` (count, names, IDs) / `pvecm status` (IPs, quorum, transport, link states)        |
| **Quorum**       | `pvecm status` -- check "Quorate" field. Threshold: `floor(total_nodes/2) + 1`                  |
| **API Access**   | `pvesh` (local CLI), `pveproxy` (HTTPS :8006), REST API. Use `--output-format json` for scripts |
| **Storage**      | `pvesm status` (active storages) / `cat /etc/pve/storage.cfg` (full config)                     |
| **Network**      | `pvesh get /nodes/{node}/network --output-format json` / `cat /etc/network/interfaces`          |
| **Subscription** | `pvesubscription get` (check status) / `pvesubscription set <key>` (apply key)                  |

---

## 2. Safety Protocols

| Rule                        | Details                                                                                                                              |
|-----------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| **No destructive bulk ops** | Commands affecting >1 node (reboot, shutdown, bulk VM stop) require explicit user confirmation.                                      |
| **Quorum check**            | Before node reboot/maintenance: `pvecm status`. If `(current - 1) < floor(total/2) + 1` -- abort. On 2-node clusters, check QDevice. |
| **Backup first**            | Before VM config changes or upgrades, verify backup exists: `pvesm list {storage} --content backup`                                  |
| **No force delete**         | Never `--purge` or `--force` without verifying resource ID: `qm config {vmid}` or `pct config {vmid}`                                |
| **HA status**               | Before HA resource changes: `ha-manager status` -- verify no migrations/fencing in progress.                                         |
| **Network changes**         | Always test first: `ifreload -a --test`. Never `ifdown` on a bridge carrying guest traffic.                                          |
| **Corosync config**         | Copy first, edit copy, backup current, then move. Always increment `config_version`.                                                 |
| **Storage ops**             | Before removing storage: `pvesm list {storage}` to verify no VMs/CTs reference it.                                                   |
| **Protection flag**         | `qm set {vmid} --protection 1` / `pct set {vmid} --protection 1` to prevent accidental deletion.                                     |


---

## 3. Action Review Protocol

> **Mandatory.** Perform this review before every action executed directly on a Proxmox node, VM, or container (commands, config changes, service operations).

> **Exception:** Read-only operations - reading logs, querying status, gathering information without changing anything - are considered safe and can be performed immediately without this review.

### 3.1 Steelman Prompt

Consider the planned action or configuration to be executed on the Proxmox server in its ideal, most successful form.
Imagine this action represents the safest, most efficient, and optimally integrated solution.
Articulate how this action perfectly fulfills the goals of system administration, increases stability, and fully meets user needs.

### 3.2 Red-Team Prompt

Review the planned Proxmox action as if you were an experienced admin or security analyst seeking to uncover potential risks.
Identify possible weaknesses in the configuration, consider outage risks, data loss, or unintended side effects.
Test the robustness of the plan under worst-case scenarios to ensure it remains safe and reliable even under pressure.

### 3.3 Decision

At the end of the red-team review, assess whether the identified risks or weaknesses are severe enough to stop the planned action.
If the action appears safe, logical, and robust, it can be executed immediately.
If significant uncertainties remain, the user must be explicitly asked for confirmation.
Conclude with a clear decision: either **"Execute action"** or **"Ask user for confirmation"**.

---

## 4. Code & Response Style

- **Responses:** Short, precise, CLI-focused (`pvesh`, `pvecm`, `pvesm`, `qm`, `pct`, `ha-manager`, `vzdump`, `pvesr`, `pvenode`, `pveceph`, `pveum`, `pveam`).
- **Troubleshooting:** Always query logs first: `journalctl -u pvedaemon -n 50`, `pvenode task list --errors 1`, `/var/log/pveproxy/access.log`.
- **JSON preference:** Use `--output-format json` or `json-pretty`. Use `--noborder --noheader` for scripted parsing.
- **Rollback plan:** Every change must include rollback. Back up config files first. Ensure backups exist before storage/VM changes.

---


## 5. Cluster Size Quick Table

| Size            | Behavior                                                                                               |
|-----------------|--------------------------------------------------------------------------------------------------------|
| **Single node** | No cluster ops. No HA. Focus on local storage + external backups.                                      |
| **2-node**      | QDevice strongly recommended. Without it: 1 node loss = quorum loss. `pvecm expected 1` for emergency. |
| **3+ nodes**    | Full HA. Tolerates `floor((N-1)/2)` failures (3 nodes: 1, 5 nodes: 2).                                 |

**Detect node count:** `pvecm nodes | grep -c '^\s*[0-9]'`


---

## 6. Troubleshooting Quick Reference

| Problem                 | Diagnosis                                                                                                        |
|-------------------------|------------------------------------------------------------------------------------------------------------------|
| **Cluster not quorate** | `pvecm status` > "Quorate: No". Check connectivity, `systemctl status corosync`. Emergency: `pvecm expected 1`.  |
| **Node won't join**     | Verify UDP 5405-5412, time sync, SSH (TCP 22). Try: `pvecm add {IP} --fingerprint {SHA256}`.                     |
| **VM won't start**      | Check lock: `qm config {vmid} \| grep lock`. Storage: `pvesm status`. Log: `pvenode task list --vmid {vmid}`.    |
| **CT won't start**      | Check lock: `pct config {vmid} \| grep lock`. Try: `pct fsck {vmid}`. Log: `journalctl -u pve-container@{vmid}`. |
| **Storage offline**     | `pvesm status` (check active). NFS: `mount \| grep nfs`. Ceph: `ceph -s`. iSCSI: `iscsiadm -m session`.          |
| **Migration fails**     | Target storage: `pvesm status --target {node}`. Locks: `qm unlock {vmid}`. Network: `ping {target}`.             |
| **HA fencing**          | `journalctl -u pve-ha-crm -n 100`. Watchdog: `cat /dev/watchdog` (should error if active).                       |
| **Slow GUI**            | `MAX_WORKERS=5` in `/etc/default/pveproxy`, then `systemctl restart pveproxy.service`.                           |
| **Backup failures**     | Space: `pvesm status`. Logs: `/var/log/vzdump/{vmid}-*.log`. PBS: verify connectivity.                           |
| **Ceph issues**         | `ceph health detail`, `ceph osd tree`, `ceph pg stat`. Maintenance: `ceph osd set noout`.                        |
| **NIC names changed**   | `ip link show`. Pin: `pve-network-interface-pinning generate`. Check `/etc/network/interfaces`.                  |

---


## Deep Reference - Chapter Documentation

For detailed documentation beyond this quick reference, read the
relevant chapter file from the skill directory.

## Which File Do I Need?

| I need to...                          | Read                                        |
|---------------------------------------|---------------------------------------------|
| Understand PVE features               | `ch01-introduction.md`                      |
| Install or upgrade Proxmox VE         | `ch02-installation.md`                      |
| Use advanced installer options        | `ch02-installation-advanced.md`             |
| Configure package repositories        | `ch03-host-admin/package-repositories.md`   |
| Set up networking                     | `ch03-host-admin/network-configuration.md`  |
| Manage ZFS on the host                | `ch03-host-admin/zfs.md`                    |
| Manage LVM on the host                | `ch03-host-admin/lvm.md`                    |
| Manage BTRFS on the host              | `ch03-host-admin/btrfs.md`                  |
| Configure certificates / ACME         | `ch03-host-admin/certificate-management.md` |
| Configure the bootloader              | `ch03-host-admin/host-bootloader.md`        |
| Monitor disk health                   | `ch03-host-admin/disk-health.md`            |
| Set up time sync / NTP                | `ch03-host-admin/time-synchronization.md`   |
| Use the web GUI                       | `ch04-gui.md`                               |
| Create or manage a cluster            | `ch05-cluster-manager/_index.md`            |
| Understand pmxcfs                     | `ch06-pmxcfs.md`                            |
| Add or configure storage              | `ch07-storage/_index.md`                    |
| Deploy Ceph                           | `ch08-ceph/_index.md`                       |
| Set up storage replication            | `ch09-storage-replication.md`               |
| Create or manage VMs                  | `ch10-qemu/_index.md`                       |
| Import a VM (OVF, disk images)        | `ch10-qemu/importing-vms.md`                |
| Set up PCI passthrough                | `ch10-qemu/pci-passthrough.md`              |
| Use Cloud-Init with VMs               | `ch10-qemu/cloud-init.md`                   |
| Create or manage containers           | `ch11-containers/_index.md`                 |
| Configure SDN                         | `ch12-sdn/_index.md`                        |
| Configure the firewall                | `ch13-firewall/_index.md`                   |
| Manage users and permissions          | `ch14-user-management/_index.md`            |
| Set up High Availability              | `ch15-high-availability/_index.md`          |
| Back up or restore VMs/CTs            | `ch16-backup-restore/_index.md`             |
| Configure notifications               | `ch17-notifications.md`                     |
| Manage PVE service daemons            | `ch18-service-daemons.md`                   |
| Find answers to common questions      | `ch20-faq.md`                               |
| Look up a CLI command                 | `appendix-a-cli/_index.md`                  |
| Migrate a VM/CT (online/offline/HA)   | `ch10-qemu/migration.md`                    |
| Recover quorum / cluster cold start   | `ch05-cluster-manager/qdevice-advanced.md`  |
| Evacuate a node / maintenance runbook | `ch03-host-admin/node-management.md`        |
| Use the pvesh REST API                | `appendix-a-cli/pvesh.md`                   |
| Run Docker on the host / in an LXC    | `ch11-containers/security-and-os-config.md` |
| Benchmark host / manage subscription  | `ch19-cli-tools.md`                         |
| Check firewall macros                 | `appendix-f-firewall-macros.md`             |
| Understand config file format         | `appendix-c-config-files.md`                |
| Schedule jobs (calendar events)       | `appendix-d-calendar-events.md`             |
| Look up QEMU vCPU types               | `appendix-e-vcpu-list.md`                   |
| Daemon CLI (pve-firewall, etc.)       | `appendix-b-service-daemons.md`             |

---

## Chapter Detail (tier 2)

For topics not in the quick-lookup table, find the right chapter here,
then read its `_index.md` for sub-topic routing to individual files.

| Topic - key terms                                                                                                                                                                                     | Chapter index                      |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------|
| Host Admin - repos, updates, firmware, networking, bonding, VLANs, NTP, metrics, disk health, LVM, ZFS, ZFS encryption, BTRFS, node management, certs, ACME, bootloader, GRUB, Secure Boot, KSM       | `ch03-host-admin/_index.md`        |
| Cluster - create, join, quorum, corosync, QDevice, cluster network, remove node, rejoin                                                                                                               | `ch05-cluster-manager/_index.md`   |
| Storage backends - Dir, NFS, CIFS, PBS, ZFS pool, LVM, LVM-thin, iSCSI, Ceph RBD, CephFS, BTRFS, ZFS-over-iSCSI                                                                                       | `ch07-storage/_index.md`           |
| Ceph - install, config, monitors, managers, OSDs, pools, CRUSH, CephFS, client, maintenance                                                                                                           | `ch08-ceph/_index.md`              |
| QEMU/KVM - settings, hardware, CPU, memory, encryption, display, USB, PCI, boot, migration, clones, templates, import, cloud-init, passthrough, hookscripts, hibernation, resource mapping, qm, locks | `ch10-qemu/_index.md`              |
| Containers - LXC, distributions, images, settings, security, apparmor, storage, backup, migration, pct config, locks                                                                                  | `ch11-containers/_index.md`        |
| SDN - zones, VNets, subnets, controllers, fabrics, IPAM, DNS, DHCP, firewall integration                                                                                                              | `ch12-sdn/_index.md`               |
| Firewall - directions, zones, cluster.fw, host rules, VM/CT rules, security groups, IP sets, nftables                                                                                                 | `ch13-firewall/_index.md`          |
| Users - users, groups, tokens, pools, auth realms, LDAP, AD, OpenID, 2FA, TOTP, WebAuthn, permissions, ACLs, roles                                                                                    | `ch14-user-management/_index.md`   |
| HA - resources, groups, fencing, watchdog, error recovery, maintenance, scheduling                                                                                                                    | `ch15-high-availability/_index.md` |
| Backup - modes (snapshot/suspend/stop), fleecing, compression, encryption, jobs, retention, restore                                                                                                   | `ch16-backup-restore/_index.md`    |

---

## CLI Reference (Appendix A)

| Tool         | File                                                                          |
|--------------|-------------------------------------------------------------------------------|
| -            | [general-and-format-options.md](appendix-a-cli/general-and-format-options.md) |
| `pvesm`      | [pvesm.md](appendix-a-cli/pvesm.md)                                           |
| `pveceph`    | [pveceph.md](appendix-a-cli/pveceph.md)                                       |
| `pvenode`    | [pvenode.md](appendix-a-cli/pvenode.md)                                       |
| `pvesh`      | [pvesh.md](appendix-a-cli/pvesh.md)                                           |
| `qm`         | [qm.md](appendix-a-cli/qm.md)                                                 |
| `qmrestore`  | [qmrestore.md](appendix-a-cli/qmrestore.md)                                   |
| `pct`        | [pct.md](appendix-a-cli/pct.md)                                               |
| `pveam`      | [pveam.md](appendix-a-cli/pveam.md)                                           |
| `pvecm`      | [pvecm.md](appendix-a-cli/pvecm.md)                                           |
| `pvesr`      | [pvesr.md](appendix-a-cli/pvesr.md)                                           |
| `pveum`      | [pveum.md](appendix-a-cli/pveum.md)                                           |
| `vzdump`     | [vzdump.md](appendix-a-cli/vzdump.md)                                         |
| `ha-manager` | [ha-manager.md](appendix-a-cli/ha-manager.md)                                 |

