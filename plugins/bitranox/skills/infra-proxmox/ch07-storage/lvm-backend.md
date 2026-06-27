# LVM Backend

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 7.9.3 Storage Features


ZFS is probably the most advanced storage type regarding snapshot and cloning. The backend uses ZFS
datasets for both VM images (format raw) and container data (format subvol). ZFS properties are inherited from the parent dataset, so you can simply set defaults on the parent dataset.

Table 7.7: Storage features for backend zfs
Content types

Image formats

images
rootdir

raw subvol


### 7.9.4 Shared

no

Snapshots
yes

Clones
yes

Examples

It is recommended to create an extra ZFS file system to store your VM images:


```
# zfs create tank/vmdata
To enable compression on that newly allocated file system:

# zfs set compression=on tank/vmdata
You can get a list of available ZFS filesystems with:

# pvesm scan zfs
```


## 7.10 LVM Backend


Storage pool type: lvm
LVM is a lightweight software layer that sits on top of hard disks and partitions. It can be used to divide
available disk space into smaller logical volumes.
Another use case is placing LVM on top of a large iSCSI LUN (Logical Unit Number) or a SAN (Storage Area
Network) connected via Fibre Channel. This allows you to easily manage the space on the iSCSI LUN, which
would otherwise be impossible because the iSCSI specification does not define a management interface for
space allocation.


### 7.10.1 Configuration


The LVM backend supports the common storage properties content, nodes, disable, and the following LVM specific properties:

vgname
LVM volume group name. This must point to an existing volume group.


base
Base volume. This volume is automatically activated before accessing the storage. This is mostly
useful when the LVM volume group resides on a remote iSCSI server.

saferemove
Called "Wipe Removed Volumes" in the web UI. Zero-out data when removing LVs. When removing
a volume, this makes sure that all data gets erased and cannot be accessed by other LVs created
later (which happen to be assigned the same physical extents). This is a costly operation, but may be
required as a security measure in certain environments.
Storage devices that support the "write zeroes" operation will use blkdiscard to zero blocks. Otherwise, a fallback to cstream is performed.

saferemove-stepsize
Wipe step size in MiB (blkdiscard -p paramater value), capped to the maximum step size supported by the underlying storage. Up to 32 MiB (maximum) by default.

saferemove_throughput
Wipe throughput (cstream -t parameter value), up to 10 MiB/s by default.
snapshot-as-volume-chain
Set this flag to enable snapshot support for virtual machines on LVM with a volume backing chain.
With this setting, taking a snapshot persists the current state under the snapshot’s name and starts a
new volume backed by the snapshot.
A volume based on a snapshot references its parent snapshot volume as its backing volume and
records only the differences to that backing volume. Snapshot volumes are currently thick-provisioned
LVM logical volumes.
This design avoids issues with native LVM snapshots, such as significant input/output (I/O) penalties
and unexpected, dangerous behavior when running out of pre-allocated space.
Snapshots as volume chains provide vendor-agnostic support for snapshots on any storage system
that supports block storage. This includes iSCSI and Fibre Channel-attached SANs.
Note that, although this feature relies on qcow2, it only uses qcow2’s ability to layer multiple volumes
in a backing chain, not qcow2’s snapshot functionality. The snapshot functionality is managed by the
PVE storage system.
Enabling or disabling this flag only affects newly created virtual disk volumes.
For efficient support of snapshot-as-volume-chain, the backing storage must support thinprovisioning and discard. Each snapshot will appear to use the full volume size on the PVE side, but
the actual space usage on the underlying storage will be smaller if those requirements are met.


> **Warning:**
> Snapshots as volume chains are currently a technology preview in Proxmox VE.


Configuration Example (/etc/pve/storage.cfg)

lvm: myspace
vgname myspace
content rootdir,images


### 7.10.2 File naming conventions


The backend use basically the same naming conventions as the ZFS pool backend.

vm-<VMID>-<NAME>


### 7.10.3 // normal VM images


Storage Features

LVM is a typical block storage system. Unfortunately, regular LVM snapshots are inefficient because they
interfere with all write operations within the entire volume group while the snapshot is active, which causes
significant I/O degradation. This is why LVM does not support linked clones, and why Proxmox VE added
support for snapshots as volume chains. This feature manages the snapshot volume through the storage
plugin and uses qcow2 to layer separate volumes as a backing chain. This creates a single disk state that is
exposed to the guest.
A benefit of LVM is that it can be used with shared storage. For example, an iSCSI LUN. The backend
implements proper cluster-wide locking if the storage is marked as shared in the configuration.

> **Tip:**
> You can use the LVM-thin backend for non-shared local storage. It supports snapshots and linked clones.


Table 7.8: Storage features for backend lvm
Content types

Image formats

Linked
Clones

images
rootdir

Shared
raw, qcow2

1

Snapshots
possible

Full Clones
yes1

: Since Proxmox VE 9, snapshots as a volume chain have been available for VMs, for details see the LVM
configuration section.


### 7.10.4 Examples


You can get a list of available LVM volume groups with:


```
# pvesm scan lvm
```


## 7.11 LVM thin Backend


Storage pool type: lvmthin
LVM normally allocates blocks when you create a volume. LVM thin pools instead allocates blocks when they
are written. This behaviour is called thin-provisioning, because volumes can be much larger than physically
available space.
You can use the normal LVM command-line tools to manage and create LVM thin pools (see man lvmthin
for details). Assuming you already have a LVM volume group called pve, the following commands create a
new LVM thin pool (size 100G) called data:

lvcreate -L 100G -n data pve
lvconvert --type thin-pool pve/data


### 7.11.1 Configuration


The LVM thin backend supports the common storage properties content, nodes, disable, and the
following LVM specific properties:

vgname
LVM volume group name. This must point to an existing volume group.

thinpool
The name of the LVM thin pool.

Configuration Example (/etc/pve/storage.cfg)

lvmthin: local-lvm
thinpool data
vgname pve
content rootdir,images


### 7.11.2 File naming conventions


The backend use basically the same naming conventions as the ZFS pool backend.

vm-<VMID>-<NAME>


### 7.11.3 // normal VM images


Storage Features

LVM thin is a block storage, but fully supports snapshots and clones efficiently. New volumes are automatically initialized with zero.
It must be mentioned that LVM thin pools cannot be shared across multiple nodes, so you can only use them
as local storage.

## See also

- [LVM (Host)](../ch03-host-admin/lvm.md)

