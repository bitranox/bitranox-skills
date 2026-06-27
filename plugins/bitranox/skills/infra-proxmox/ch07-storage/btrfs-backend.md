# BTRFS Backend

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

# /etc/pve/priv/ceph/<STORAGE_ID>.secret
A secret can be received from the Ceph cluster (as Ceph admin) by issuing the command below, where
userid is the client ID that has been configured to access the cluster. For further information on Ceph user
management, see the Ceph docs.a

# ceph auth get-key client.userid > cephfs.secret


### 7.15.3 Storage Features


The cephfs backend is a POSIX-compliant filesystem, on top of a Ceph cluster.

Table 7.13: Storage features for backend cephfs

[1]

Content types

Image formats

vztmpl iso
backup
snippets

none

Shared
yes

Snapshots
yes[1]

Clones
no

While no known bugs exist, snapshots are not yet guaranteed to be stable, as they lack sufficient testing.


## 7.16 BTRFS Backend


Storage pool type: btrfs
On the surface, this storage type is very similar to the directory storage type, so see the directory backend
section for a general overview.
The main difference is that with this storage type raw formatted disks will be placed in a subvolume, in order
to allow taking snapshots and supporting offline storage migration with snapshots being preserved.

> **Note:**
> BTRFS will honor the O_DIRECT flag when opening files, meaning VMs should not use cache mode
> none, otherwise there will be checksum errors.


### 7.16.1 Configuration


This backend is configured similarly to the directory storage. Note that when adding a directory as a BTRFS
storage, which is not itself also the mount point, it is highly recommended to specify the actual mount point
via the is_mountpoint option.
For example, if a BTRFS file system is mounted at /mnt/data2 and its pve-storage/ subdirectory
(which may be a snapshot, which is recommended) should be added as a storage pool called data2, you
can use the following entry:


btrfs: data2
path /mnt/data2/pve-storage
content rootdir,images
is_mountpoint /mnt/data2


### 7.16.2 Snapshots


When taking a snapshot of a subvolume or raw file, the snapshot will be created as a read-only subvolume
with the same path followed by an @ and the snapshot’s name.


## 7.17 ZFS over ISCSI Backend


Storage pool type: zfs
This backend accesses a remote machine having a ZFS pool as storage and an iSCSI target implementation
via ssh. For each guest disk it creates a ZVOL and, exports it as iSCSI LUN. This LUN is used by Proxmox
VE for the guest disk.
The following iSCSI target implementations are supported:

- LIO (Linux)
- IET (Linux)
- ISTGT (FreeBSD)
- Comstar (Solaris)

> **Note:**
> This plugin needs a ZFS capable remote storage appliance, you cannot use it to create a ZFS Pool on a
> regular Storage Appliance/SAN


### 7.17.1 Configuration


In order to use the ZFS over iSCSI plugin you need to configure the remote machine (target) to accept ssh
connections from the Proxmox VE node. Proxmox VE connects to the target for creating the ZVOLs and
exporting them via iSCSI. Authentication is done through a ssh-key (without password protection) stored in

/etc/pve/priv/zfs/<target_ip>_id_rsa
The following steps create a ssh-key and distribute it to the storage machine with IP 192.0.2.1:

mkdir /etc/pve/priv/zfs
ssh-keygen -f /etc/pve/priv/zfs/192.0.2.1_id_rsa
ssh-copy-id -i /etc/pve/priv/zfs/192.0.2.1_id_rsa.pub root@192.0.2.1
ssh -i /etc/pve/priv/zfs/192.0.2.1_id_rsa root@192.0.2.1
The backend supports the common storage properties content, nodes, disable, and the following
ZFS over ISCSI specific properties:

## See also

- [BTRFS (Host)](../ch03-host-admin/btrfs.md)

