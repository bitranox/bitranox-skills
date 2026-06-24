---
name: proxmox
description: >-
  Use when configuring, managing, or troubleshooting Proxmox VE -
  installation, host administration, clusters, VMs, containers,
  storage, Ceph, SDN, firewall, user management, HA, backups,
  notifications, and CLI tools. Covers Proxmox VE 9.1.2.
---

# Proxmox VE Operations Reference (Release 9.1.2)

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

## 2. Cluster Requirements

### 2.1 Port Requirements

| Protocol | Ports       | Purpose                  |
|----------|-------------|--------------------------|
| UDP      | 5405-5412   | Corosync cluster traffic |
| TCP      | 22          | SSH                      |
| TCP      | 8006        | Web GUI / API (HTTPS)    |
| TCP      | 3128        | SPICE proxy              |
| TCP      | 5900-5999   | VNC console              |
| TCP      | 60000-60050 | Live migration (default) |
| TCP      | 5403        | QDevice (corosync-qnetd) |

### 2.2 General Requirements

- **Time sync** -- All nodes must have synchronized clocks. Verify: `timedatectl status`. Use chrony or systemd-timesyncd. Drift causes auth and replication failures.
- **Network latency** -- Corosync requires <5 ms (LAN). Above 10 ms unreliable for >3 nodes. Dedicated physical NIC recommended.
- **Corosync links** -- Up to 8 redundant links (link0..link7). Each on separate physical network. Priority-based failover: `--link0 IP,priority=15 --link1 IP,priority=20`.
- **CPU compatibility** -- Online migration requires same vendor (Intel-to-Intel, AMD-to-AMD). Cross-vendor not guaranteed.
- **Hostname/IP** -- Cannot be changed after cluster creation. Use IP addresses in cluster config to avoid DNS issues.

---

## 3. Cluster Creation & Management

```bash
# Create cluster (optionally with dedicated network)
pvecm create CLUSTERNAME
pvecm create CLUSTERNAME --link0 10.10.10.1

# Join cluster (run on joining node, using an existing member's IP)
pvecm add IP-ADDRESS-CLUSTER                         # join via API (or GUI: Datacenter > Cluster > Join Information)
pvecm add IP-ADDRESS-CLUSTER --use_ssh               # force SSH join instead of API
pvecm add IP-ADDRESS-CLUSTER --link0 LOCAL-IP        # separated cluster network

# Remove node (migrate all VMs/CTs first!)
# On the node being removed:
systemctl stop pve-cluster corosync
# On a remaining node:
pvecm delnode NODENAME
rm -rf /etc/pve/nodes/NODENAME                       # clean up

# Emergency quorum override (use with extreme caution)
pvecm expected 1

# Update/regenerate node certificates
pvecm updatecerts
pvecm updatecerts --force                             # force new SSL cert
pvecm updatecerts --unmerge-known-hosts               # clean legacy SSH
```

---

## 4. QDevice (External Vote Support)

> Provides external vote for even-node clusters (especially 2-node). Grants vote to only one partition in split-brain.

```bash
# Install (external server)
apt install corosync-qnetd

# Install (all PVE nodes)
apt install corosync-qdevice

# Setup (run on ONE PVE node)
pvecm qdevice setup <QDEVICE-IP>

# Remove
pvecm qdevice remove

# Verify
pvecm status          # look for "Qdevice" in Flags
```

**Status flags:** `A` = Alive, `V` = Voting, `MW` = Master Wins, `NA` = Not Alive, `NV` = Not Voting, `NR` = Not Registered.

**Important:**
- Uses TCP 5403 -- ensure firewall allows it.
- Remove QDevice before adding/removing nodes. Re-add after reaching even node count.
- Odd-node clusters: QDevice provides (N-1) votes, creating near-SPOF. Not recommended.

---

## 5. Safety Protocols

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

**Corosync config change procedure:**

```bash
cp /etc/pve/corosync.conf /etc/pve/corosync.conf.new     # 1. copy
# edit corosync.conf.new (increment config_version!)
cp /etc/pve/corosync.conf /etc/pve/corosync.conf.bak     # 2. backup current
mv /etc/pve/corosync.conf.new /etc/pve/corosync.conf     # 3. activate
systemctl status corosync                                  # 4. verify
```

---

## 6. Action Review Protocol

> **Mandatory.** Perform this review before every action executed directly on a Proxmox node, VM, or container (commands, config changes, service operations).

> **Exception:** Read-only operations - reading logs, querying status, gathering information without changing anything - are considered safe and can be performed immediately without this review.

### 6.1 Steelman Prompt

Consider the planned action or configuration to be executed on the Proxmox server in its ideal, most successful form.
Imagine this action represents the safest, most efficient, and optimally integrated solution.
Articulate how this action perfectly fulfills the goals of system administration, increases stability, and fully meets user needs.

### 6.2 Red-Team Prompt

Review the planned Proxmox action as if you were an experienced admin or security analyst seeking to uncover potential risks.
Identify possible weaknesses in the configuration, consider outage risks, data loss, or unintended side effects.
Test the robustness of the plan under worst-case scenarios to ensure it remains safe and reliable even under pressure.

### 6.3 Decision

At the end of the red-team review, assess whether the identified risks or weaknesses are severe enough to stop the planned action.
If the action appears safe, logical, and robust, it can be executed immediately.
If significant uncertainties remain, the user must be explicitly asked for confirmation.
Conclude with a clear decision: either **"Execute action"** or **"Ask user for confirmation"**.

---

## 7. Management Commands

### 7.1 Cluster & Node

```bash
pvecm status                                               # cluster status
pvecm nodes                                                # list nodes
pveversion --verbose                                       # PVE version details

pvesh get /nodes --output-format json                      # node list (API)
pvesh get /nodes/{node}/status --output-format json        # node metrics
pvesh get /cluster/nextid                                  # next free VMID

pvenode config get                                         # node config
pvenode config set --description "node description"        # set config
pvenode task list --limit 20                               # recent tasks
pvenode task log {UPID}                                    # task log
pvenode task status {UPID}                                 # task status

pvenode migrateall {target_node} --maxworkers 4            # evacuate node
pvenode startall                                           # start onboot guests
pvenode stopall --timeout 300                              # stop all guests
pvenode wakeonlan {node}                                   # Wake-on-LAN
```

### 7.2 VM Management (`qm`)

#### Lifecycle

```bash
qm list                                                    # list VMs on node
qm config {vmid}                                           # show VM config
qm status {vmid}                                           # VM status

qm create {vmid} --name myvm --memory 2048 --cores 2 \
  --net0 virtio,bridge=vmbr0 --scsi0 local-lvm:32 \
  --scsihw virtio-scsi-single --ostype l26                 # create VM
qm start {vmid}                                            # start
qm shutdown {vmid}                                         # graceful shutdown
qm stop {vmid}                                             # hard stop
qm reboot {vmid}                                           # reboot
qm reset {vmid}                                            # hard reset
qm suspend {vmid}                                          # suspend
qm resume {vmid}                                           # resume

qm destroy {vmid}                                          # delete VM
qm destroy {vmid} --destroy-unreferenced-disks             # + cleanup orphans
```

#### Migration & Cloning

```bash
qm migrate {vmid} {target} --online                        # live migration
qm migrate {vmid} {target} --online --with-local-disks     # + local disks
qm migrate {vmid} {target} --online \
  --migration_network 10.1.2.0/24                          # dedicated net

qm clone {vmid} {newid} --name cloned-vm --full            # full clone
qm clone {vmid} {newid} --name linked-clone                # linked (template)
qm template {vmid}                                         # convert to template
```

#### Snapshots

```bash
qm snapshot {vmid} {snapname}                              # create
qm listsnapshot {vmid}                                     # list
qm rollback {vmid} {snapname}                              # rollback
qm delsnapshot {vmid} {snapname}                           # delete
```

#### Disks & Hardware

```bash
qm set {vmid} --memory 4096 --cores 4                     # modify resources
qm disk resize {vmid} scsi0 +10G                           # resize disk
qm disk move {vmid} scsi0 {target_storage}                 # move disk
qm disk import {vmid} /path/to/disk.qcow2 {storage}       # import disk
qm unlock {vmid}                                           # remove lock
```

#### Cloud-Init

```bash
qm set {vmid} --ciuser admin --cipassword secret \
  --ipconfig0 ip=10.0.0.10/24,gw=10.0.0.1 \
  --sshkeys /path/to/keys.pub                              # configure
qm cloudinit update {vmid}                                 # regenerate drive
qm cloudinit dump {vmid} user                              # dump config
```

#### Guest Agent & Settings

```bash
qm agent {vmid} ping                                      # test agent
qm agent {vmid} fsfreeze-freeze                            # freeze filesystems
qm agent {vmid} fsfreeze-thaw                              # thaw filesystems
qm monitor {vmid}                                          # QEMU monitor

qm set {vmid} --boot 'order=scsi0;ide2;net0'               # boot order
qm set {vmid} --startup order=10,up=30,down=60             # startup order
qm set {vmid} --onboot 1                                   # autostart
qm set {vmid} --tags "production;web"                      # tags
qm set {vmid} --protection 1                               # protect
qm set {vmid} --hotplug network,disk,usb,cpu,memory        # hotplug
```

### 7.3 Container Management (`pct`)

#### Lifecycle

```bash
pct list                                                   # list CTs
pct config {vmid}                                          # show config

pct create {vmid} {storage}:vztmpl/{template} \
  --hostname myct --memory 1024 --cores 2 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --rootfs {storage}:8 --unprivileged 1                    # create CT
pct start {vmid}                                           # start
pct shutdown {vmid}                                        # graceful shutdown
pct stop {vmid}                                            # hard stop
pct reboot {vmid}                                          # reboot

pct destroy {vmid}                                         # delete
pct destroy {vmid} --purge                                 # + remove from HA/backups
```

#### Access & Interaction

```bash
pct enter {vmid}                                           # shell access
pct console {vmid}                                         # console
pct exec {vmid} -- {command}                               # run command
pct push {vmid} {local_path} {ct_path}                     # push file in
pct pull {vmid} {ct_path} {local_path}                     # pull file out
```

#### Migration, Cloning & Snapshots

```bash
pct migrate {vmid} {target_node}                           # migrate
pct clone {vmid} {newid} --hostname cloned-ct --full       # clone
pct template {vmid}                                        # convert to template

pct snapshot {vmid} {snapname}                             # snapshot
pct listsnapshot {vmid}                                    # list
pct rollback {vmid} {snapname}                             # rollback
pct delsnapshot {vmid} {snapname}                          # delete snapshot
```

#### Storage & Maintenance

```bash
pct resize {vmid} rootfs +5G                               # resize rootfs
pct move-volume {vmid} rootfs {target_storage}             # move volume
pct fsck {vmid}                                            # filesystem check
pct fstrim {vmid}                                          # fstrim
pct df {vmid}                                              # disk usage
pct mount {vmid}                                           # mount for rescue
pct unmount {vmid}                                         # unmount
```

#### Settings

```bash
pct set {vmid} --memory 2048 --cores 4                     # resources
pct set {vmid} --features nesting=1,fuse=1,keyctl=1        # features
pct set {vmid} --onboot 1                                  # autostart
pct set {vmid} --startup order=5,up=15,down=30             # startup order
pct set {vmid} --tags "database;staging"                   # tags
pct set {vmid} --protection 1                              # protect
```

**Supported OS types:** `alpine`, `archlinux`, `centos`, `debian`, `devuan`, `fedora`, `gentoo`, `nixos`, `opensuse`, `ubuntu`, `unmanaged`.

### 7.4 Container Templates (`pveam`)

```bash
pveam update                                               # update database
pveam available                                            # list all available
pveam available --section system                           # system templates
pveam available --section turnkeylinux                     # turnkey templates
pveam download {storage} {template_name}                   # download
pveam list {storage}                                       # list downloaded
pveam remove {storage}:vztmpl/{template_name}              # remove
```

---

## 8. Storage Management (`pvesm`)

### 8.1 Status & Configuration

```bash
pvesm status                                               # overview all stores
pvesm status --storage {storage_id}                        # specific store
cat /etc/pve/storage.cfg                                   # full config

pvesm list {storage}                                       # list content
pvesm list {storage} --content images                      # VM disks only
pvesm list {storage} --content backup                      # backups only
pvesm list {storage} --content iso                         # ISOs only
pvesm list {storage} --content vztmpl                      # CT templates only
```

### 8.2 Add Storage

**Available types:** `dir`, `nfs`, `cifs`, `pbs`, `zfspool`, `lvm`, `lvmthin`, `iscsi`, `iscsidirect`, `rbd`, `cephfs`, `btrfs`, `zfs`, `esxi`

```bash
# NFS
pvesm add nfs mynas --server 10.0.0.50 --export /data \
  --content images,backup,iso

# LVM-thin
pvesm add lvmthin local-lvm --vgname pve --thinpool data \
  --content images,rootdir

# Proxmox Backup Server
pvesm add pbs mypbs --server 10.0.0.60 --datastore mystore \
  --username user@pbs --password secret --fingerprint AA:BB:...

# Ceph RBD
pvesm add rbd ceph-pool --pool mypool --content images,rootdir \
  --monhost "10.0.0.1;10.0.0.2;10.0.0.3"

# CephFS
pvesm add cephfs ceph-fs --content vztmpl,iso,backup \
  --monhost "10.0.0.1;10.0.0.2;10.0.0.3"

# Local directory
pvesm add dir mydir --path /mnt/data \
  --content images,backup,iso,vztmpl --mkdir 1
```

### 8.3 Manage Storage

```bash
pvesm set {storage_id} --content images,backup             # update content types
pvesm set {storage_id} --nodes node1,node2,node3           # restrict to nodes
pvesm set {storage_id} --shared 1                          # mark as shared
pvesm set {storage_id} --bwlimit \
  clone=100000,migration=200000,restore=150000             # bandwidth limits

pvesm remove {storage_id}                                  # remove config (NOT data)
```

### 8.4 Volume Operations

```bash
pvesm alloc {storage} {vmid} vm-{vmid}-disk-0 32G          # allocate disk
pvesm free {storage}:{volume}                               # delete volume
pvesm path {storage}:{volume}                               # get filesystem path
pvesm extractconfig {backup_volume}                         # extract config from backup
```

### 8.5 Scan Remote Storage

```bash
pvesm scan nfs {server_ip}                                  # NFS exports
pvesm scan cifs {server_ip}                                 # CIFS shares
pvesm scan iscsi {portal_ip}                                # iSCSI targets
pvesm scan pbs {server} {username} --password {pass}        # PBS datastores
pvesm scan lvm                                              # local LVM VGs
pvesm scan lvmthin {vg_name}                                # local thin pools
pvesm scan zfs                                              # local ZFS pools
```

### 8.6 Backup Pruning

```bash
pvesm prune-backups {storage} \
  --keep-last 5 --keep-daily 7 --keep-weekly 4 \
  --keep-monthly 6                                         # prune
pvesm prune-backups {storage} --keep-last 3 --dry-run 1    # dry run
```

### 8.7 Content Types

| Type       | Description                      |
|------------|----------------------------------|
| `images`   | VM disk images                   |
| `rootdir`  | CT root volumes                  |
| `backup`   | vzdump backup files              |
| `iso`      | ISO images                       |
| `vztmpl`   | CT templates                     |
| `snippets` | Hookscripts, cloud-init snippets |

---

## 9. Backup & Restore

### 9.1 Create Backups (`vzdump`)

```bash
vzdump {vmid} --storage {storage} --mode snapshot \
  --compress zstd                                          # single guest
vzdump --all --storage {storage} --mode snapshot \
  --compress zstd                                          # all guests
vzdump --pool mypool --storage {storage} --mode snapshot   # by pool
vzdump --all --exclude 100,200 --storage {storage}         # exclude guests
vzdump --stop                                              # stop running jobs
```

### 9.2 Backup Options

| Option                   | Values / Example                                                  |
|--------------------------|-------------------------------------------------------------------|
| **Mode**                 | `snapshot` (recommended), `stop` (highest consistency), `suspend` |
| **Compression**          | `--compress zstd` (recommended), `gzip`, `lzo`, `0` (none)        |
| **Zstd threads**         | `--zstd 0` (half cores), `--zstd 4` (explicit)                    |
| **Bandwidth**            | `--bwlimit 50000` (KiB/s)                                         |
| **Fleecing (VM)**        | `--fleecing enabled=1,storage=local-lvm`                          |
| **Retention**            | `--prune-backups keep-last=3,keep-daily=7,keep-weekly=4`          |
| **Protected**            | `--protected 1`                                                   |
| **Exclude paths (CT)**   | `--exclude-path /tmp --exclude-path /var/cache`                   |
| **Notes**                | `--notes-template '{{guestname}} on {{node}} ({{vmid}})'`         |
| **PBS change detection** | `--pbs-change-detection-mode metadata` (incremental CT backups)   |

### 9.3 Scheduled Backups

- Configure: **Datacenter > Backup** or `/etc/pve/jobs.cfg`
- Schedule format: Calendar events (`sat 02:00`, `*/6:00`, `mon..fri 22:00`)
- Managed by `pvescheduler` daemon
- **Repeat missed:** Runs skipped jobs after host was offline

### 9.4 Restore

```bash
# Restore VM
qmrestore {backup_file_or_volume} {vmid}
qmrestore {backup_file} {vmid} --storage {target_storage}
qmrestore {backup_file} {vmid} --live-restore 1           # start while restoring

# Restore CT
pct restore {vmid} {backup_file_or_volume}
pct restore {vmid} {backup_file} --storage {target_storage}

# Inspect backup without restoring
pvesm extractconfig {backup_volume}
```

### 9.5 Backup Encryption

Only with PBS storage:

```bash
pvesm set {pbs_storage} --encryption-key autogen           # auto-generate key
```

**File naming:** `vzdump-{type}-{vmid}-{YYYY_MM_DD-HH_MM_SS}.{ext}` (type: `qemu` or `lxc`)

---

## 10. Storage Replication (`pvesr`)

> Replicates guest volumes via ZFS snapshots to another node. Reduces migration time and adds redundancy for local storage. **Supported storage: ZFS (local) only.**

```bash
pvesr create-local-job {vmid}-0 {target_node} \
  --schedule "*/15" --rate 10                              # create (every 15m, 10 MBps)
pvesr list                                                 # list jobs
pvesr status                                               # job status
pvesr disable {vmid}-0                                     # disable
pvesr enable {vmid}-0                                      # enable
pvesr update {vmid}-0 --schedule "*/5"                     # change schedule
pvesr delete {vmid}-0                                      # delete
```

**Schedule examples:** `*/15` (every 15 min), `*/00` (hourly), `1:00` (daily at 1am)

**Replication network:**

```
# /etc/pve/datacenter.cfg
replication: secure,network=10.1.2.0/24
```

**Behavior:**
- Failed jobs retry every 30 minutes automatically.
- Migration to replication target = fast (delta sync only). Direction auto-reverses.
- HA + replication: supported, but potential data loss between last sync and failure.

---

## 11. High Availability (`ha-manager`)

### 11.1 Status & Resources

```bash
ha-manager status                                          # HA status
ha-manager status --verbose                                # + full CRM/LRM JSON
ha-manager config                                          # list all HA resources
ha-manager config --type vm                                # VMs only
ha-manager config --type ct                                # CTs only
```

### 11.2 Manage Resources

```bash
ha-manager add vm:{vmid} --state started \
  --max_restart 3 --max_relocate 2                         # add VM
ha-manager add ct:{vmid} --state started                   # add CT
ha-manager remove vm:{vmid}                                # remove
ha-manager set vm:{vmid} --state started \
  --max_restart 2 --max_relocate 1                         # update
ha-manager set vm:{vmid} --failback 1                      # enable failback
```

**Resource states:** `started`, `stopped`, `disabled`, `enabled`, `ignored`

### 11.3 Migration & Maintenance

```bash
ha-manager migrate vm:{vmid} {target_node}                 # online migrate
ha-manager relocate vm:{vmid} {target_node}                # stop + start on target
ha-manager crm-command stop vm:{vmid} 120                  # stop (0 = hard stop)

ha-manager crm-command node-maintenance enable {node}      # enable maintenance
ha-manager crm-command node-maintenance disable {node}     # disable maintenance
```

### 11.4 HA Rules

```bash
# Node affinity (prefer/restrict nodes)
ha-manager rules add node-affinity myrule \
  --resources vm:100,vm:101 --nodes node1:2,node2:1 --strict 0

# Resource affinity (keep together or apart)
ha-manager rules add resource-affinity keepapart \
  --resources vm:100,vm:101 --affinity negative            # keep on separate nodes

ha-manager rules list                                      # list all rules
ha-manager rules remove {rule_id}                          # remove rule
```

### 11.5 Fencing & Logs

- **Fencing:** Watchdog-based (softdog or hardware). Node fences itself on quorum loss. Use hardware watchdog (IPMI) in production.
- **CRM log:** `journalctl -u pve-ha-crm -f`
- **LRM log:** `journalctl -u pve-ha-lrm -f`

---

## 12. Firewall

### 12.1 Configuration Files

| Scope   | Path                                   | Sections                                                  |
|---------|----------------------------------------|-----------------------------------------------------------|
| Cluster | `/etc/pve/firewall/cluster.fw`         | `[OPTIONS]`, `[RULES]`, `[IPSET]`, `[GROUP]`, `[ALIASES]` |
| Host    | `/etc/pve/nodes/{nodename}/host.fw`    | `[OPTIONS]`, `[RULES]`                                    |
| VM/CT   | `/etc/pve/firewall/{vmid}.fw`          | `[OPTIONS]`, `[RULES]`, `[IPSET]`, `[ALIASES]`            |
| VNet    | `/etc/pve/sdn/firewall/{vnet_name}.fw` | `[OPTIONS]`, `[RULES]` (FORWARD only, nftables)           |

### 12.2 Enable Firewall

```ini
# /etc/pve/firewall/cluster.fw
[OPTIONS]
enable: 1                    # cluster-wide enable (default: disabled)
policy_in: DROP
policy_out: ACCEPT
```

> Enabling blocks all traffic except WebGUI (8006) and SSH (22) from local network. Create a "management" IPSet with admin IPs for remote access.

For VMs/CTs: set `enable: 1` in VM firewall config **AND** `firewall=1` on each network interface.

### 12.3 Rule Syntax

```ini
[RULES]
DIRECTION ACTION [OPTIONS]
|DIRECTION ACTION [OPTIONS]                  # disabled (prefix |)
DIRECTION MACRO(ACTION) [OPTIONS]            # use macro

# Examples
IN SSH(ACCEPT) -i net0 -source 192.168.2.0/24
IN ACCEPT -p tcp -dport 8000:8100 -source 10.0.0.0/8
OUT ACCEPT
IN DROP
GROUP webserver                               # reference security group
```

**Directions:** `IN`, `OUT`, `FORWARD`
**Actions:** `ACCEPT`, `DROP`, `REJECT`
**Options:** `--source`, `--dest`, `--sport`, `--dport`, `--proto`, `--iface`, `--log`, `--icmp-type`

### 12.4 Security Groups & IP Sets

```ini
# /etc/pve/firewall/cluster.fw

[group webserver]
IN ACCEPT -p tcp -dport 80
IN ACCEPT -p tcp -dport 443

[IPSET management]
192.168.1.0/24
10.0.0.5

[ALIASES]
myserver 10.0.0.5
```

### 12.5 Host Options

| Option                                 | Default                          | Description                    |
|----------------------------------------|----------------------------------|--------------------------------|
| `protection_synflood`                  | `0`                              | SYN flood protection           |
| `protection_synflood_rate`             | `200`                            | SYN/sec per source IP          |
| `protection_synflood_burst`            | `1000`                           | Burst per source IP            |
| `tcpflags`                             | `0`                              | Filter illegal TCP flag combos |
| `nosmurfs`                             | -                                | SMURF filter                   |
| `nf_conntrack_max`                     | `262144`                         | Max tracked connections        |
| `nf_conntrack_tcp_timeout_established` | `432000`                         | Established timeout (5 days)   |
| `nftables`                             | `0`                              | Enable nftables (tech preview) |
| `log_ratelimit`                        | `enable=1,rate=1/second,burst=5` | Log rate limiting              |

### 12.6 VM/CT Options

| Option      | Default | Description                        |
|-------------|---------|------------------------------------|
| `dhcp`      | `0`     | Enable DHCP                        |
| `macfilter` | `1`     | MAC address filtering              |
| `ipfilter`  | -       | Restrict to assigned IPs           |
| `ndp`       | `1`     | Neighbor Discovery Protocol (IPv6) |
| `radv`      | -       | Allow Router Advertisement         |

**Log levels:** `nolog`, `emerg`, `alert`, `crit`, `err`, `warning`, `notice`, `info`, `debug`
**IPv6:** Fully supported -- rules apply to both IPv4 and IPv6 by default.

---

## 13. User & Permission Management (`pveum`)

### 13.1 Users & Groups

```bash
pveum user list                                            # list users
pveum user add user@pve --password secret \
  --email user@example.com                                 # add user
pveum user delete user@pve                                 # delete
pveum user modify user@pve --enable 1 --expire 0          # modify
pveum passwd user@pve                                      # change password

pveum group list                                           # list groups
pveum group add admins --comment "Admin group"             # add group
pveum user modify user@pve --groups admins                 # assign to group
```

### 13.2 Roles & ACLs

```bash
pveum role list                                            # list roles
pveum role add MyRole \
  --privs "VM.Console,VM.Audit,VM.PowerMgmt"              # custom role

pveum acl list                                             # list ACLs
pveum acl modify /vms/{vmid} \
  --users user@pve --roles PVEVMAdmin                      # set ACL
pveum acl modify /pool/mypool \
  --groups admins --roles PVEAdmin                         # ACL on pool
pveum acl delete /vms/{vmid} \
  --users user@pve --roles PVEVMAdmin                      # remove ACL
```

### 13.3 API Tokens

```bash
pveum user token add user@pve mytoken --privsep 0          # create (inherit perms)
pveum user token list user@pve                             # list
pveum user token remove user@pve mytoken                   # remove
```

### 13.4 Auth Realms

| Realm    | Type                |
|----------|---------------------|
| `pam`    | Linux PAM           |
| `pve`    | Proxmox VE built-in |
| `ldap`   | LDAP                |
| `ad`     | Active Directory    |
| `openid` | OpenID Connect      |

```bash
pveum realm add myldap --type ldap \
  --server1 ldap.example.com \
  --base-dn "dc=example,dc=com" --user-attr uid           # add LDAP
```

### 13.5 Pools & 2FA

```bash
pveum pool add mypool --comment "Development pool"         # create pool
pveum pool set mypool --vms 100,101,102                    # assign VMs
```

**Two-factor auth:** TOTP, WebAuthn/FIDO2, Yubico. Configure per user via GUI. Recovery keys available.

**Built-in roles:** `PVEAdmin`, `PVEAuditor`, `PVEDatastoreAdmin`, `PVEDatastoreUser`, `PVEPoolAdmin`, `PVEPoolUser`, `PVESysAdmin`, `PVETemplateUser`, `PVEUserAdmin`, `PVEVMAdmin`, `PVEVMUser`, `Administrator`, `NoAccess`

---

## 14. Ceph Management (`pveceph`)

```bash
pveceph install                                            # install (each node)
pveceph init --network 10.10.10.0/24 \
  --cluster-network 10.20.20.0/24                          # initialize

pveceph mon create                                         # create monitor (min 3)
pveceph mgr create                                         # create manager
pveceph osd create /dev/sdX                                # create OSD
pveceph osd create /dev/sdX --db_dev /dev/nvmeX            # OSD + separate DB
pveceph osd list                                           # list OSDs

pveceph pool create mypool --size 3 --min_size 2 \
  --pg_num 128                                             # create pool
pveceph pool destroy mypool                                # destroy pool

pveceph status                                             # Ceph status
pveceph start                                              # start all services
pveceph start --service mon                                # start monitors
pveceph start --service osd.0                              # start specific OSD
pveceph stop                                               # stop all
pveceph purge --crash --logs                               # destroy all Ceph data

# CephFS
pveceph mds create                                         # create MDS first
pveceph fs create --name myfs --pg_num 64                  # create CephFS
```

**Native Ceph commands:**

```bash
ceph -s                                                    # cluster status
ceph health detail                                         # health details
ceph df                                                    # space usage
ceph osd tree                                              # OSD tree
ceph osd df                                                # per-OSD usage
ceph osd set noout                                         # maintenance flag
ceph osd unset noout                                       # clear flag
ceph osd crush rule ls                                     # CRUSH rules
ceph osd crush tree                                        # CRUSH tree
ceph pg stat                                               # PG health
```

---

## 15. SDN (Software-Defined Network)

> Virtual zones (isolation), VNets (virtual networks), and subnets (IP ranges). Applied cluster-wide.

**Zone types:** `simple`, `VLAN` (802.1Q), `QinQ`, `VXLAN` (overlay), `EVPN` (BGP overlay)

```bash
pvesh set /cluster/sdn                                     # apply SDN changes
```

- After apply, VNets appear as Linux bridges on all nodes.
- **IPAM:** Built-in PVE, Netbox, or phpIPAM.
- **DHCP:** dnsmasq-based, per-subnet.
- **Firewall:** VNet-level rules require nftables-based `proxmox-firewall`.

**Config files:** `/etc/pve/sdn/zones.cfg`, `/etc/pve/sdn/vnets.cfg`, `/etc/pve/sdn/subnets.cfg`, `/etc/pve/sdn/controllers.cfg`

---

## 16. Network Diagnostics

```bash
# Interface status
pvesh get /nodes/{node}/network --output-format json
cat /etc/network/interfaces
cat /etc/network/interfaces.new                            # pending changes

# Apply / test
ifreload -a                                                # apply live (ifupdown2)
ifreload -a --test                                         # dry-run (ALWAYS test first)

# Bonding
ls /proc/net/bonding/ 2>/dev/null                          # list bonds
cat /proc/net/bonding/{name}                               # inspect bond

# Layer 2 / Layer 3
ip link show                                               # MTU, speed, state
bridge vlan show                                           # VLAN check
ovs-vsctl show                                             # OVS (if used)
getent hosts {hostname}                                    # DNS resolution

# Corosync
pvecm status                                               # link states
journalctl -b -u corosync                                  # corosync logs
journalctl -b -u corosync | grep -i "link\|knet"          # link debugging
```

**Bond recommendations for corosync:**
- Use dedicated physical NICs for primary link.
- `active-backup` is safest for bonds.
- LACP: set `bond-lacp-rate fast` on **both** node and switch (failover: 3s vs 90s default).

**NIC naming:** Pin scheme: `net.naming-scheme=v252` in kernel cmdline. Pin specific: `pve-network-interface-pinning generate --interface enp1s0 --target-name nic1`.

---

## 17. Service Daemons & Logs

### 17.1 Daemons

| Service        | Port / Address   | User     | Purpose                              |
|----------------|------------------|----------|--------------------------------------|
| `pvedaemon`    | 127.0.0.1:85     | root     | API daemon (all privileges)          |
| `pveproxy`     | TCP 8006 (HTTPS) | www-data | API proxy to outside world           |
| `pvestatd`     | -                | -        | Status collection, cluster broadcast |
| `spiceproxy`   | TCP 3128         | www-data | SPICE proxy                          |
| `pvescheduler` | -                | -        | Backup/replication job scheduler     |

**Worker tuning:** Set `MAX_WORKERS=N` (default 3) in:
- `/etc/default/pvedaemon`
- `/etc/default/pveproxy`

### 17.2 Log Commands

```bash
journalctl -u pve-cluster -f                               # cluster filesystem
journalctl -u corosync -f                                  # corosync
journalctl -u pvedaemon -f                                 # API daemon
journalctl -u pveproxy -f                                  # proxy
journalctl -u pve-ha-crm -f                                # HA cluster resource mgr
journalctl -u pve-ha-lrm -f                                # HA local resource mgr
journalctl -u pve-firewall -f                              # firewall
journalctl -u pvescheduler -f                              # scheduler
journalctl -u pve-guests -f                                # guest startup
journalctl -u ceph.target -f                               # Ceph
```

**Log files:**
- Proxy access: `/var/log/pveproxy/access.log`
- Task logs: `/var/log/pve/tasks/`

### 17.3 Service Management

```bash
systemctl reload pveproxy                                  # graceful reload (preferred)
systemctl restart pvedaemon pveproxy                       # restart (interrupts consoles)
```

### 17.4 pveproxy Configuration (`/etc/default/pveproxy`)

| Setting                | Description                                        |
|------------------------|----------------------------------------------------|
| `ALLOW_FROM`           | Allowed source IPs/ranges                          |
| `DENY_FROM`            | Denied source IPs/ranges                           |
| `POLICY`               | `allow` (default) or `deny`                        |
| `LISTEN_IP`            | Bind to specific IP                                |
| `CIPHERS`              | TLS <= 1.2 cipher list                             |
| `CIPHERSUITES`         | TLS >= 1.3 cipher suites                           |
| `HONOR_CIPHER_ORDER`   | Server chooses cipher (`0` = client chooses)       |
| `DHPARAMS`             | Path to DH parameters file                         |
| `DISABLE_TLS_1_2`      | Disable TLS 1.2                                    |
| `DISABLE_TLS_1_3`      | Disable TLS 1.3                                    |
| `COMPRESSION`          | `0` to disable gzip compression                    |
| `PROXY_REAL_IP_HEADER` | Header for real client IP (e.g. `X-Forwarded-For`) |
| `MAX_WORKERS`          | Number of worker processes                         |

**Alternative HTTPS cert:**
- Place at `/etc/pve/local/pveproxy-ssl.pem` + `/etc/pve/local/pveproxy-ssl.key`
- Falls back to `/etc/pve/local/pve-ssl.pem`

---

## 18. Certificate Management (`pvenode`)

```bash
pvenode cert info                                          # view certificates
pvenode cert set {cert.pem} {key.pem} --restart 1          # upload custom cert
pvenode cert delete --restart 1                            # delete custom cert

# ACME (Let's Encrypt)
pvenode acme account register default {email} \
  --directory https://acme-v02.api.letsencrypt.org/directory
pvenode acme account info                                  # account info
pvenode acme cert order                                    # order certificate
pvenode acme cert renew                                    # renew
pvenode acme cert renew --force                            # force (>30 days to expiry)
pvenode acme cert revoke                                   # revoke

# ACME plugins (DNS challenge)
pvenode acme plugin list
pvenode acme plugin add dns myplugin --api cf \
  --data {base64_credentials}

# Node ACME config
pvenode config set \
  --acme account=default,domains="pve.example.com" \
  --acmedomain0 domain=pve.example.com,plugin=myplugin
```

---

## 19. Code & Response Style

- **Responses:** Short, precise, CLI-focused (`pvesh`, `pvecm`, `pvesm`, `qm`, `pct`, `ha-manager`, `vzdump`, `pvesr`, `pvenode`, `pveceph`, `pveum`, `pveam`).
- **Troubleshooting:** Always query logs first: `journalctl -u pvedaemon -n 50`, `pvenode task list --errors 1`, `/var/log/pveproxy/access.log`.
- **JSON preference:** Use `--output-format json` or `json-pretty`. Use `--noborder --noheader` for scripted parsing.
- **Rollback plan:** Every change must include rollback. Back up config files first. Ensure backups exist before storage/VM changes.

---

## 20. Cluster-Size-Aware Workflows

| Size            | Behavior                                                                                               |
|-----------------|--------------------------------------------------------------------------------------------------------|
| **Single node** | No cluster ops. No HA. Focus on local storage + external backups.                                      |
| **2-node**      | QDevice strongly recommended. Without it: 1 node loss = quorum loss. `pvecm expected 1` for emergency. |
| **3+ nodes**    | Full HA. Tolerates `floor((N-1)/2)` failures (3 nodes: 1, 5 nodes: 2).                                 |

**Detect node count:** `pvecm nodes | grep -c '^\s*[0-9]'`

### Rolling Updates

1. `apt update && apt dist-upgrade`
2. `pveversion --verbose`
3. `pvecm status`
4. `qm list && pct list`
5. Proceed to next node.

### Migration Pre-Check

```bash
pvesh get /nodes/{node}/status --output-format json        # target capacity
pvesm status --target {target_node}                        # shared storage check
```

### ID Management

```bash
pvesh get /cluster/nextid                                  # next free VMID
pvesh get /cluster/resources --type vm --output-format json # all existing IDs
```

Set VMID range: **Datacenter > Options > Next Free VMID Range**

---

## 21. Node Maintenance Workflow

1. **Pre-check:** `pvecm status` (quorum survives -1 node), `ha-manager status`
2. **Enable maintenance:** `ha-manager crm-command node-maintenance enable {node}`
3. **Migrate remaining:** `pvenode migrateall {target_node} --maxworkers 2`
4. **Verify empty:** `qm list` + `pct list` (no running guests)
5. **Perform maintenance:** updates, reboot, hardware changes
6. **Verify after reboot:** `pvecm status`, `pveversion --verbose`, `pvesm status`
7. **Disable maintenance:** `ha-manager crm-command node-maintenance disable {node}`
8. **Migrate back:** `ha-manager migrate vm:{vmid} {node}` or let failback handle it

---

## 22. Cluster Cold Start (After Power Failure)

1. Power on nodes -- cluster is inquorate until enough nodes boot.
2. `pve-guests` service waits for quorum before starting onboot guests.
3. Once quorum reached: guests with `onboot=1` start in startup order.
4. If nodes don't reach quorum: `systemctl status corosync`, verify network.
5. **Emergency:** `pvecm expected 1` on one node. Bring others back ASAP. Avoid cluster changes.

---

## 23. Guest Migration Details

| Type              | Command                                                  | Notes                                         |
|-------------------|----------------------------------------------------------|-----------------------------------------------|
| VM online (live)  | `qm migrate {vmid} {target} --online`                    | Near-zero downtime. Same CPU vendor required. |
| VM online + local | `qm migrate {vmid} {target} --online --with-local-disks` | Copies local storage live.                    |
| VM offline        | `qm migrate {vmid} {target}`                             | VM stopped, disk copied. Any storage.         |
| CT                | `pct migrate {vmid} {target}`                            | Shared or compatible storage needed.          |
| HA-managed        | `ha-manager migrate vm:{vmid} {target}`                  | Keeps HA state consistent.                    |

**Global settings** (`/etc/pve/datacenter.cfg`):

```ini
migration: secure,network=10.1.2.0/24
```

| Setting            | Values                                             |
|--------------------|----------------------------------------------------|
| **Type**           | `secure` (encrypted, default), `insecure` (faster) |
| **Network**        | CIDR notation, auto-selects per-node IP            |
| **Bandwidth (VM)** | `--migrate_speed 500` (MB/s, 0 = unlimited)        |

**Replication-assisted:** If guest is replicated to target, only delta synced (very fast).

---

## 24. Important Configuration Files

### Cluster & Datacenter

| File                            | Purpose                                    |
|---------------------------------|--------------------------------------------|
| `/etc/pve/corosync.conf`        | Corosync membership and network            |
| `/etc/pve/datacenter.cfg`       | Migration, console, HA, keyboard, language |
| `/etc/pve/storage.cfg`          | Storage backend definitions                |
| `/etc/pve/user.cfg`             | Users, groups, ACLs, tokens                |
| `/etc/pve/jobs.cfg`             | Backup job schedules                       |
| `/etc/pve/ceph.conf`            | Ceph configuration                         |
| `/etc/pve/priv/authorized_keys` | Cluster-wide SSH authorized keys           |

### Per-Node

| File                                            | Purpose                          |
|-------------------------------------------------|----------------------------------|
| `/etc/pve/nodes/{node}/qemu-server/{vmid}.conf` | VM configuration                 |
| `/etc/pve/nodes/{node}/lxc/{vmid}.conf`         | CT configuration                 |
| `/etc/pve/nodes/{node}/host.fw`                 | Host firewall rules              |
| `/etc/pve/local/pve-ssl.pem`                    | Node SSL certificate             |
| `/etc/pve/local/pve-ssl.key`                    | Node SSL private key             |
| `/etc/pve/local/pveproxy-ssl.pem`               | Custom proxy SSL certificate     |
| `/etc/pve/local/pveproxy-ssl.key`               | Custom proxy SSL private key     |
| `/etc/network/interfaces`                       | Network configuration            |
| `/etc/network/interfaces.new`                   | Pending (staged) network changes |
| `/etc/default/pveproxy`                         | Proxy daemon settings            |
| `/etc/default/pvedaemon`                        | API daemon settings              |

### Firewall

| File                                   | Purpose                     |
|----------------------------------------|-----------------------------|
| `/etc/pve/firewall/cluster.fw`         | Cluster-wide firewall rules |
| `/etc/pve/firewall/{vmid}.fw`          | VM/CT firewall rules        |
| `/etc/pve/sdn/firewall/{vnet_name}.fw` | VNet firewall rules         |

### SDN

| File                           | Purpose                |
|--------------------------------|------------------------|
| `/etc/pve/sdn/zones.cfg`       | Zone definitions       |
| `/etc/pve/sdn/vnets.cfg`       | VNet definitions       |
| `/etc/pve/sdn/subnets.cfg`     | Subnet definitions     |
| `/etc/pve/sdn/controllers.cfg` | Controller definitions |

### HA

| File                        | Purpose                 |
|-----------------------------|-------------------------|
| `/etc/pve/ha/resources.cfg` | HA resource definitions |
| `/etc/pve/ha/groups.cfg`    | HA groups (deprecated)  |
| `/etc/pve/ha/rules.cfg`     | HA rules                |

### System

| File                             | Purpose                                    |
|----------------------------------|--------------------------------------------|
| `/etc/apt/sources.list`          | APT package sources                        |
| `/etc/apt/sources.list.d/`       | Additional APT sources                     |
| `/var/lib/pve-cluster/config.db` | pmxcfs database (**DO NOT edit directly**) |

---

## 25. API Shell (`pvesh`) Quick Reference

```bash
pvesh ls /nodes                                            # list child paths
pvesh get /nodes/{node}/status --output-format json        # GET
pvesh create /nodes/{node}/qemu \
  --vmid 100 --name test --memory 1024                     # POST (create)
pvesh set /nodes/{node}/qemu/{vmid}/config \
  --memory 2048                                            # PUT (update)
pvesh delete /nodes/{node}/qemu/{vmid}                     # DELETE

pvesh usage /nodes/{node}/qemu/{vmid} \
  --command set --verbose                                  # API usage info
```

| Option                        | Description                       |
|-------------------------------|-----------------------------------|
| `--output-format json`        | Compact JSON                      |
| `--output-format json-pretty` | Indented JSON                     |
| `--output-format yaml`        | YAML output                       |
| `--output-format text`        | Human-readable (default)          |
| `--quiet`                     | Suppress output                   |
| `--noborder --noheader`       | For scripted text parsing         |
| `--noproxy`                   | Force local execution, skip proxy |

---

## 26. Troubleshooting Quick Reference

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

| I need to...                     | Read                                        |
|----------------------------------|---------------------------------------------|
| Understand PVE features          | `ch01-introduction.md`                      |
| Install or upgrade Proxmox VE    | `ch02-installation.md`                      |
| Use advanced installer options   | `ch02-installation-advanced.md`             |
| Configure package repositories   | `ch03-host-admin/package-repositories.md`   |
| Set up networking                | `ch03-host-admin/network-configuration.md`  |
| Manage ZFS on the host           | `ch03-host-admin/zfs.md`                    |
| Manage LVM on the host           | `ch03-host-admin/lvm.md`                    |
| Manage BTRFS on the host         | `ch03-host-admin/btrfs.md`                  |
| Configure certificates / ACME    | `ch03-host-admin/certificate-management.md` |
| Configure the bootloader         | `ch03-host-admin/host-bootloader.md`        |
| Monitor disk health              | `ch03-host-admin/disk-health.md`            |
| Set up time sync / NTP           | `ch03-host-admin/time-synchronization.md`   |
| Use the web GUI                  | `ch04-gui.md`                               |
| Create or manage a cluster       | `ch05-cluster-manager/_index.md`            |
| Understand pmxcfs                | `ch06-pmxcfs.md`                            |
| Add or configure storage         | `ch07-storage/_index.md`                    |
| Deploy Ceph                      | `ch08-ceph/_index.md`                       |
| Set up storage replication       | `ch09-storage-replication.md`               |
| Create or manage VMs             | `ch10-qemu/_index.md`                       |
| Import a VM (OVF, disk images)   | `ch10-qemu/importing-vms.md`                |
| Set up PCI passthrough           | `ch10-qemu/pci-passthrough.md`              |
| Use Cloud-Init with VMs          | `ch10-qemu/cloud-init.md`                   |
| Create or manage containers      | `ch11-containers/_index.md`                 |
| Configure SDN                    | `ch12-sdn/_index.md`                        |
| Configure the firewall           | `ch13-firewall/_index.md`                   |
| Manage users and permissions     | `ch14-user-management/_index.md`            |
| Set up High Availability         | `ch15-high-availability/_index.md`          |
| Back up or restore VMs/CTs       | `ch16-backup-restore/_index.md`             |
| Configure notifications          | `ch17-notifications.md`                     |
| Manage PVE service daemons       | `ch18-service-daemons.md`                   |
| Find answers to common questions | `ch20-faq.md`                               |
| Look up a CLI command            | `appendix-a-cli/_index.md`                  |
| Check firewall macros            | `appendix-f-firewall-macros.md`             |
| Understand config file format    | `appendix-c-config-files.md`                |
| Schedule jobs (calendar events)  | `appendix-d-calendar-events.md`             |
| Look up QEMU vCPU types          | `appendix-e-vcpu-list.md`                   |
| Daemon CLI (pve-firewall, etc.)  | `appendix-b-service-daemons.md`             |

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

