# Proxmox VE Storage

*[Main Index](../SKILL.md)*

## Contents

| Section                                 | File                                                       |
|-----------------------------------------|------------------------------------------------------------|
| 7.1-7.4 Storage Types and Configuration | [storage-types-and-config.md](storage-types-and-config.md) |
| 7.5 Directory Backend                   | [directory-backend.md](directory-backend.md)               |
| 7.6 NFS Backend                         | [nfs-backend.md](nfs-backend.md)                           |
| 7.7 CIFS Backend                        | [cifs-backend.md](cifs-backend.md)                         |
| 7.8 Proxmox Backup Server               | [proxmox-backup-server.md](proxmox-backup-server.md)       |
| 7.9 Local ZFS Pool Backend              | [zfs-pool-backend.md](zfs-pool-backend.md)                 |
| 7.10 LVM Backend                        | [lvm-backend.md](lvm-backend.md)                           |
| 7.11 LVM thin Backend                   | [lvm-thin-backend.md](lvm-thin-backend.md)                 |
| 7.12-7.13 iSCSI Backends                | [iscsi-backends.md](iscsi-backends.md)                     |
| 7.14 Ceph RADOS Block Devices (RBD)     | [ceph-rbd.md](ceph-rbd.md)                                 |
| 7.15 Ceph Filesystem (CephFS)           | [cephfs.md](cephfs.md)                                     |
| 7.16 BTRFS Backend                      | [btrfs-backend.md](btrfs-backend.md)                       |
| 7.17 ZFS over ISCSI Backend             | [zfs-over-iscsi.md](zfs-over-iscsi.md)                     |


## See also

- [Ceph Cluster](../ch08-ceph/_index.md)
- [pvesm CLI Reference](../appendix-a-cli/pvesm.md)

## Overview

The Proxmox VE storage model is very flexible. Virtual machine images can either be stored on one or
several local storages, or on shared storage like NFS or iSCSI (NAS, SAN). There are no limits, and you
may configure as many storage pools as you like. You can use all storage technologies available for Debian
Linux.
One major benefit of storing VMs on shared storage is the ability to live-migrate running machines without
any downtime, as all nodes in the cluster have direct access to VM disk images. There is no need to copy
VM image data, so live migration is very fast in that case.
The storage library (package libpve-storage-perl) uses a flexible plugin system to provide a common interface to all storage types. This can be easily adopted to include further storage types in the future.


## 7.1 Storage Types


There are basically two different classes of storage types:

File level storage
File level based storage technologies allow access to a fully featured (POSIX) file system. They are in
general more flexible than any Block level storage (see below), and allow you to store content of any
type. ZFS is probably the most advanced system, and it has full support for snapshots and clones.
Block level storage
Allows to store large raw images. It is usually not possible to store other files (ISO, backups, ..) on
such storage types. Most modern block level storage implementations support snapshots and clones.
Ceph RADOS is a distributed systems, replicating storage data to different nodes that can be accessed
as RBD (RADOS Block Device).

Table 7.1: Available storage types
Description
ZFS (local)
Directory
BTRFS
