# ZFS on Linux

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 3.8.6 Create a LVM-thin pool


A thin pool has to be created on top of a volume group. How to create a volume group see Section LVM.


```
# lvcreate -L 80G -T -n vmstore vmdata
```


## 3.9 ZFS on Linux


ZFS is a combined file system and logical volume manager designed by Sun Microsystems. Starting with
Proxmox VE 3.4, the native Linux kernel port of the ZFS file system is introduced as optional file system and
also as an additional selection for the root file system. There is no need for manually compile ZFS modules
- all packages are included.
By using ZFS, its possible to achieve maximum enterprise features with low budget hardware, but also high
performance systems by leveraging SSD caching or even SSD only setups. ZFS can replace cost intense
hardware raid cards by moderate CPU and memory load combined with easy management.

**General ZFS Advantages**
- Easy configuration and management with Proxmox VE GUI and CLI.
- Reliable
- Protection against data corruption
- Data compression on file system level
- Snapshots
- Copy-on-write clone
- Various raid levels: RAID0, RAID1, RAID10, RAIDZ-1, RAIDZ-2, RAIDZ-3, dRAID, dRAID2, dRAID3
- Can use SSD for cache
- Self healing
- Continuous integrity checking
- Designed for high storage capacities
- Asynchronous replication over network
- Open Source
- Encryption
- ...


### 3.9.1 Hardware


ZFS depends heavily on memory, so you need at least 8GB to start. In practice, use as much as you can
get for your hardware/budget. To prevent data corruption, we recommend the use of high quality ECC RAM.
If you use a dedicated cache and/or log disk, you should use an enterprise class SSD. This can increase the
overall performance significantly.

> **Important:**
> Do not use ZFS on top of a hardware RAID controller which has its own cache management. ZFS
> needs to communicate directly with the disks. An HBA adapter or something like an LSI controller
> flashed in “IT” mode is more appropriate.


If you are experimenting with an installation of Proxmox VE inside a VM (Nested Virtualization), don’t use
virtio for disks of that VM, as they are not supported by ZFS. Use IDE or SCSI instead (also works with
the virtio SCSI controller type).


### 3.9.2 Installation as Root File System


When you install using the Proxmox VE installer, you can choose ZFS for the root file system. You need to
select the RAID type at installation time:
RAID0

RAID1
RAID10
RAIDZ-1
RAIDZ-2
RAIDZ-3

Also called “striping”. The capacity of such volume is the sum of the capacities of all
disks. But RAID0 does not add any redundancy, so the failure of a single drive
makes the volume unusable.
Also called “mirroring”. Data is written identically to all disks. This mode requires at
least 2 disks with the same size. The resulting capacity is that of a single disk.
A combination of RAID0 and RAID1. Requires at least 4 disks.
A variation on RAID-5, single parity. Requires at least 3 disks.
A variation on RAID-5, double parity. Requires at least 4 disks.
A variation on RAID-5, triple parity. Requires at least 5 disks.

The installer automatically partitions the disks, creates a ZFS pool called rpool, and installs the root file
system on the ZFS subvolume rpool/ROOT/pve-1.
Another subvolume called rpool/data is created to store VM images. In order to use that with the
Proxmox VE tools, the installer creates the following configuration entry in /etc/pve/storage.cfg:

zfspool: local-zfs
pool rpool/data
sparse
content images,rootdir
After installation, you can view your ZFS pool status using the zpool command:


```
# zpool status
pool: rpool
state: ONLINE
scan: none requested
config:
```


NAME
rpool
mirror-0
sda2
sdb2
mirror-1
sdc
sdd

STATE
ONLINE
ONLINE
ONLINE
ONLINE
ONLINE
ONLINE
ONLINE


READ WRITE CKSUM
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0

errors: No known data errors
The zfs command is used to configure and manage your ZFS file systems. The following command lists all
file systems after installation:


```
# zfs list
NAME
rpool
rpool/ROOT
rpool/ROOT/pve-1
rpool/data
rpool/swap
```


### 3.9.3 USED

4.94G
702M
702M
96K
4.25G

AVAIL
7.68T
7.68T
7.68T
7.68T
7.69T

REFER
96K
96K
702M
96K
64K

MOUNTPOINT
/rpool
/rpool/ROOT
/
/rpool/data
-

ZFS RAID Level Considerations

There are a few factors to take into consideration when choosing the layout of a ZFS pool. The basic building
block of a ZFS pool is the virtual device, or vdev. All vdevs in a pool are used equally and the data is striped
among them (RAID0). Check the zpoolconcepts(7) manpage for more details on vdevs.
Performance
Each vdev type has different performance behaviors. The two parameters of interest are the IOPS (Input/Output Operations per Second) and the bandwidth with which data can be written or read.
A mirror vdev (RAID1) will approximately behave like a single disk in regard to both parameters when writing
data. When reading data the performance will scale linearly with the number of disks in the mirror.
A common situation is to have 4 disks. When setting it up as 2 mirror vdevs (RAID10) the pool will have
the write characteristics as two single disks in regard to IOPS and bandwidth. For read operations it will
resemble 4 single disks.
A RAIDZ of any redundancy level will approximately behave like a single disk in regard to IOPS with a lot of
bandwidth. How much bandwidth depends on the size of the RAIDZ vdev and the redundancy level.
A dRAID pool should match the performance of an equivalent RAIDZ pool.
For running VMs, IOPS is the more important metric in most situations.
Size, Space usage and Redundancy
While a pool made of mirror vdevs will have the best performance characteristics, the usable space will be
50% of the disks available. Less if a mirror vdev consists of more than 2 disks, for example in a 3-way mirror.
At least one healthy disk per mirror is needed for the pool to stay functional.


The usable space of a RAIDZ type vdev of N disks is roughly N-P, with P being the RAIDZ-level. The RAIDZlevel indicates how many arbitrary disks can fail without losing data. A special case is a 4 disk pool with
RAIDZ2. In this situation it is usually better to use 2 mirror vdevs for the better performance as the usable
space will be the same.
Another important factor when using any RAIDZ level is how ZVOL datasets, which are used for VM disks,
behave. For each data block the pool needs parity data which is at least the size of the minimum block size
defined by the ashift value of the pool. With an ashift of 12 the block size of the pool is 4k. The default
block size for a ZVOL is 8k. Therefore, in a RAIDZ2 each 8k block written will cause two additional 4k parity
blocks to be written, 8k + 4k + 4k = 16k. This is of course a simplified approach and the real situation will be
slightly different with metadata, compression and such not being accounted for in this example.
This behavior can be observed when checking the following properties of the ZVOL:

- volsize
- refreservation (if the pool is not thin provisioned)
- used (if the pool is thin provisioned and without snapshots present)

```
# zfs get volsize,refreservation,used <pool>/vm-<vmid>-disk-X
```


volsize is the size of the disk as it is presented to the VM, while refreservation shows the reserved
space on the pool which includes the expected space needed for the parity data. If the pool is thin provisioned, the refreservation will be set to 0. Another way to observe the behavior is to compare the
used disk space within the VM and the used property. Be aware that snapshots will skew the value.
There are a few options to counter the increased use of space:

- Increase the volblocksize to improve the data to parity ratio
- Use mirror vdevs instead of RAIDZ
- Use ashift=9 (block size of 512 bytes)
The volblocksize property can only be set when creating a ZVOL. The default value can be changed in
the storage configuration. When doing this, the guest needs to be tuned accordingly and depending on the
use case, the problem of write amplification is just moved from the ZFS layer up to the guest.
Using ashift=9 when creating the pool can lead to bad performance, depending on the disks underneath,
and cannot be changed later on.
Mirror vdevs (RAID1, RAID10) have favorable behavior for VM workloads. Use them, unless your environment has specific needs and characteristics where RAIDZ performance characteristics are acceptable.


### 3.9.4 ZFS dRAID


In a ZFS dRAID (declustered RAID) the hot spare drive(s) participate in the RAID. Their spare capacity
is reserved and used for rebuilding when one drive fails. This provides, depending on the configuration,
faster rebuilding compared to a RAIDZ in case of drive failure. More information can be found in the official
OpenZFS documentation. 2
2 OpenZFS dRAID https://openzfs.github.io/openzfs-docs/Basic%20Concepts/dRAID%20Howto.html


> **Note:**
> dRAID is intended for more than 10-15 disks in a dRAID. A RAIDZ setup should be better for a lower
> amount of disks in most use cases.


> **Note:**
> The GUI requires one more disk than the minimum (i.e. dRAID1 needs 3). It expects that a spare disk is
> added as well.


- dRAID1 or dRAID: requires at least 2 disks, one can fail before data is lost
- dRAID2: requires at least 3 disks, two can fail before data is lost
- dRAID3: requires at least 4 disks, three can fail before data is lost
Additional information can be found on the manual page:

# man zpoolconcepts

Spares and Data
The number of spares tells the system how many disks it should keep ready in case of a disk failure. The
default value is 0 spares. Without spares, rebuilding won’t get any speed benefits.

data defines the number of devices in a redundancy group. The default value is 8. Except when disks parity - spares equal something less than 8, the lower number is used. In general, a smaller number
of data devices leads to higher IOPS, better compression ratios and faster resilvering, but defining fewer
data devices reduces the available storage capacity of the pool.


### 3.9.5 Bootloader


Proxmox VE uses proxmox-boot-tool to manage the bootloader configuration. See the chapter on Proxmox
VE host bootloaders for details.


## See also

- [ZFS Administration](zfs-administration.md)
- [ZFS Encryption, Compression and Special Devices](zfs-advanced.md)
- [ZFS Pool Storage Backend](../ch07-storage/zfs-pool-backend.md)
