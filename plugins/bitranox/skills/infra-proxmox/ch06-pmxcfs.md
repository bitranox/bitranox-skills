# Proxmox Cluster File System (pmxcfs)

*[Main Index](SKILL.md)*

The Proxmox Cluster file system (“pmxcfs”) is a database-driven file system for storing configuration files,
replicated in real time to all cluster nodes using corosync. We use this to store all Proxmox VE related
configuration files.
Although the file system stores all data inside a persistent database on disk, a copy of the data resides in
RAM. This imposes restrictions on the maximum size, which is currently 128 MiB. This is still enough to store
the configuration of several thousand virtual machines.
This system provides the following advantages:

- Seamless replication of all configuration to all nodes in real time
- Provides strong consistency checks to avoid duplicate VM IDs
- Read-only when a node loses quorum
- Automatic updates of the corosync cluster configuration to all nodes
- Includes a distributed locking mechanism


## 6.1 POSIX Compatibility


The file system is based on FUSE, so the behavior is POSIX like. But some feature are simply not implemented, because we do not need them:

- You can just generate normal files and directories, but no symbolic links, . . .
- You can’t rename non-empty directories (because this makes it easier to guarantee that VMIDs are
unique).

- You can’t change file permissions (permissions are based on paths)
- O_EXCL creates were not atomic (like old NFS)
- O_TRUNC creates are not atomic (FUSE restriction)


## 6.2 File Access Rights


All files and directories are owned by user root and have group www-data. Only root has write permissions, but group www-data can read most files. Files below the following paths are only accessible by
root:

/etc/pve/priv/
/etc/pve/nodes/${NAME}/priv/


## 6.3 Technology


We use the Corosync Cluster Engine for cluster communication, and SQlite for the database file. The file
system is implemented in user space using FUSE.


## 6.4 File System Layout


The file system is mounted at:

/etc/pve


### 6.4.1 Files


authkey.pub
ceph.conf
corosync.conf
datacenter.cfg
domains.cfg
firewall/cluster.fw
firewall/<NAME>.fw
firewall/<VMID>.fw
ha/crm_commands
ha/manager_status
ha/resources.cfg
ha/rules.cfg
nodes/<NAME>/config
nodes/<NAME>/lxc/<VMID>.conf

Public key used by the ticket system
Ceph configuration file (note: /etc/ceph/ceph.conf
is a symbolic link to this)
Corosync cluster configuration file (prior to
Proxmox VE 4.x, this file was called cluster.conf)
Proxmox VE datacenter-wide configuration
(keyboard layout, proxy, . . . )
Proxmox VE authentication domains
Firewall configuration applied to all nodes
Firewall configuration for individual nodes
Firewall configuration for VMs and containers
Displays HA operations that are currently being
carried out by the CRM
JSON-formatted information regarding HA
services on the cluster
Resources managed by high availability, and their
current state
Rules putting constraints on the HA manager’s
scheduling of HA resources
Node-specific configuration
VM configuration data for LXC containers


Prior to Proxmox VE 4.0, used for container
configuration data (deprecated, removed soon)
nodes/<NAME>/pve-ssl.key
Private SSL key for pve-ssl.pem
nodes/<NAME>/pve-ssl.pem
Public SSL certificate for web server (signed by
cluster CA)
nodes/<NAME>/pveproxy-ssl.key
Private SSL key for pveproxy-ssl.pem
(optional)
nodes/<NAME>/pveproxy-ssl.pem
Public SSL certificate (chain) for web server
(optional override for pve-ssl.pem)
nodes/<NAME>/qemu-server/<VMID>.conf
VM configuration data for KVM VMs
priv/authkey.key
Private key used by ticket system
priv/authorized_keys
SSH keys of cluster members for authentication
priv/ceph*
Ceph authentication keys and associated
capabilities
priv/known_hosts
SSH keys of the cluster members for verification
priv/lock/*
Lock files used by various services to ensure safe
cluster-wide operations
priv/pve-root-ca.key
Private key of cluster CA
priv/shadow.cfg
Shadow password file for PVE Realm users
priv/storage/<STORAGE-ID>.pw
Contains the password of a storage in plain text
priv/tfa.cfg
Base64-encoded two-factor authentication
configuration
priv/token.cfg
API token secrets of all tokens
pve-root-ca.pem
Public certificate of cluster CA
pve-www.key
Private key used for generating CSRF tokens
sdn/*
Shared configuration files for Software Defined
Networking (SDN)
status.cfg
Proxmox VE external metrics server configuration
storage.cfg
Proxmox VE storage configuration
user.cfg
Proxmox VE access control configuration
(users/groups/. . . )
virtual-guest/cpu-models.conf
For storing custom CPU models
vzdump.cron
Cluster-wide vzdump backup-job schedule

nodes/<NAME>/openvz/


### 6.4.2 Symbolic links


Certain directories within the cluster file system use symbolic links, in order to point to a node’s own configuration files. Thus, the files pointed to in the table below refer to different files on each node of the cluster.

local
lxc
openvz
qemu-server


### 6.4.3 nodes/<LOCAL_HOST_NAME>

nodes/<LOCAL_HOST_NAME>/lxc/
nodes/<LOCAL_HOST_NAME>/openvz/
(deprecated, removed soon)
nodes/<LOCAL_HOST_NAME>/qemu-server/

Special status files for debugging (JSON)


.version
.members
.vmlist
.clusterlog
.rrd


### 6.4.4 File versions (to detect file modifications)

Info about cluster members
List of all VMs
Cluster log (last 50 entries)
RRD data (most recent entries)

Enable/Disable debugging

You can enable verbose syslog messages with:

echo "1" >/etc/pve/.debug
And disable verbose syslog messages with:

echo "0" >/etc/pve/.debug


## 6.5 Recovery


If you have major problems with your Proxmox VE host, for example hardware issues, it could be helpful
to copy the pmxcfs database file /var/lib/pve-cluster/config.db, and move it to a new Proxmox VE host. On the new host (with nothing running), you need to stop the pve-cluster service and
replace the config.db file (required permissions 0600). Following this, adapt /etc/hostname and
/etc/hosts according to the lost Proxmox VE host, then reboot and check (and don’t forget your VM/CT
data).


### 6.5.1 Remove Cluster Configuration


The recommended way is to reinstall the node after you remove it from your cluster. This ensures that all
secret cluster/ssh keys and any shared configuration data is destroyed.
In some cases, you might prefer to put a node back to local mode without reinstalling, which is described in
Separate A Node Without Reinstalling


### 6.5.2 Recovering/Moving Guests from Failed Nodes


For the guest configuration files in nodes/<NAME>/qemu-server/ (VMs) and nodes/<NAME>/lxc/
(containers), Proxmox VE sees the containing node <NAME> as the owner of the respective guest. This concept enables the usage of local locks instead of expensive cluster-wide locks for preventing concurrent guest
configuration changes.
As a consequence, if the owning node of a guest fails (for example, due to a power outage, fencing event,
etc.), a regular migration is not possible (even if all the disks are located on shared storage), because such
a local lock on the (offline) owning node is unobtainable. This is not a problem for HA-managed guests, as
Proxmox VE’s High Availability stack includes the necessary (cluster-wide) locking and watchdog functionality
to ensure correct and automatic recovery of guests from fenced nodes.
If a non-HA-managed guest has only shared disks (and no other local resources which are only available on
the failed node), a manual recovery is possible by simply moving the guest configuration file from the failed


node’s directory in /etc/pve/ to an online node’s directory (which changes the logical owner or location
of the guest).
For example, recovering the VM with ID 100 from an offline node1 to another node node2 works by
running the following command as root on any member node of the cluster:

mv /etc/pve/nodes/node1/qemu-server/100.conf /etc/pve/nodes/node2/ ←qemu-server/


> **Warning:**
> Before manually recovering a guest like this, make absolutely sure that the failed source node
> is really powered off/fenced. Otherwise Proxmox VE’s locking principles are violated by the mv
> command, which can have unexpected consequences.


> **Warning:**
> Guests with local disks (or other local resources which are only available on the offline node) are
> not recoverable like this. Either wait for the failed node to rejoin the cluster or restore such guests
> from backups.


## See also

- [Cluster Manager](ch05-cluster-manager/_index.md)

