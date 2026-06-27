# Ceph Filesystem (CephFS)

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Table 7.12: Storage features for backend rbd
Content types

Image formats

images
rootdir

raw


## 7.15 Shared

yes

Snapshots
yes

Clones
yes

Ceph Filesystem (CephFS)

Storage pool type: cephfs
CephFS implements a POSIX-compliant filesystem, using a Ceph storage cluster to store its data. As
CephFS builds upon Ceph, it shares most of its properties. This includes redundancy, scalability, selfhealing, and high availability.

> **Tip:**
> Proxmox VE can manage Ceph setups, which makes configuring a CephFS storage easier. As modern
> hardware offers a lot of processing power and RAM, running storage services and VMs on same node is
> possible without a significant performance impact.


To use the CephFS storage plugin, you must replace the stock Debian Ceph client, by adding our Ceph
repository. Once added, run apt update, followed by apt dist-upgrade, in order to get the newest
packages.


> **Warning:**
> Please ensure that there are no other Ceph repositories configured. Otherwise the installation will
> fail or there will be mixed package versions on the node, leading to unexpected behavior.


### 7.15.1 Configuration


This backend supports the common storage properties nodes, disable, content, as well as the following cephfs specific properties:

fs-name
Name of the Ceph FS.
monhost
List of monitor daemon addresses. Optional, only needed if Ceph is not running on the Proxmox VE
cluster.
path
The local mount point. Optional, defaults to /mnt/pve/<STORAGE_ID>/.


username
Ceph user id. Optional, only needed if Ceph is not running on the Proxmox VE cluster, where it defaults
to admin.
subdir
CephFS subdirectory to mount. Optional, defaults to /.
fuse
Access CephFS through FUSE, instead of the kernel client. Optional, defaults to 0.
Configuration example for an external Ceph cluster (/etc/pve/storage.cfg)

cephfs: cephfs-external
monhost 10.1.1.20 10.1.1.21 10.1.1.22
path /mnt/pve/cephfs-external
content backup
username admin
fs-name cephfs


> **Note:**
> Don’t forget to set up the client’s secret key file, if cephx was not disabled.


### 7.15.2 Authentication


> **Note:**
> If Ceph is installed locally on the Proxmox VE cluster, the following is done automatically when adding the
> storage.


If you use cephx authentication, which is enabled by default, you need to provide the secret from the
external Ceph cluster.
To configure the storage via the CLI, you first need to make the file containing the secret available. One way
is to copy the file from the external Ceph cluster directly to one of the Proxmox VE nodes. The following
example will copy it to the /root directory of the node on which we run it:

# scp <external cephserver>:/etc/ceph/cephfs.secret /root/cephfs.secret
Then use the pvesm CLI tool to configure the external RBD storage, use the --keyring parameter, which
needs to be a path to the secret file that you copied. For example:


```
# pvesm add cephfs <name> --monhost "10.1.1.20 10.1.1.21 10.1.1.22" -- ←content backup --keyring /root/cephfs.secret
When configuring an external RBD storage via the GUI, you can copy and paste the secret into the appropriate field.
The secret is only the key itself, as opposed to the rbd backend which also contains a [client.userid]
section.
The secret will be stored at
```


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

## See also

- [CephFS (Ceph chapter)](../ch08-ceph/cephfs.md)

