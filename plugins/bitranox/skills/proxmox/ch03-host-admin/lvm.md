# Logical Volume Manager (LVM)

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Starting with Proxmox VE 4.3, the package smartmontools 1 is installed and required. This is a set of tools
to monitor and control the S.M.A.R.T. system for local hard disks.
You can get the status of a disk by issuing the following command:

# smartctl -a /dev/sdX
where /dev/sdX is the path to one of your local disks.
If the output says:

SMART support is: Disabled
you can enable it with the command:

# smartctl -s on /dev/sdX
For more information on how to use smartctl, please see man smartctl.
By default, the smartmontools daemon smartd is active and enabled, and scans any devices matching

- /dev/sd[a-z]
- /dev/sd[a-z][a-z]
- /dev/hd[a-t]
- or /dev/nvme[0-99]
every 30 minutes for errors and warnings, and sends an e-mail to root if it detects a problem.
For more information about how to configure smartd, please see man smartd and man smartd.conf.
If you use your hard disks with a hardware raid controller, there are most likely tools to monitor the disks in
the raid array and the array itself. For more information about this, please refer to the vendor of your raid
controller.


## 3.8 Logical Volume Manager (LVM)


Most people install Proxmox VE directly on a local disk. The Proxmox VE installation CD offers several
options for local disk management, and the current default setup uses LVM. The installer lets you select a
single disk for such setup, and uses that disk as physical volume for the Volume Group (VG) pve. The
following output is from a test installation using a small 8GB disk:

# pvs
PV
/dev/sda3

```
# vgs
VG
pve
```


VG
pve

Fmt Attr PSize PFree
lvm2 a-- 7.87g 876.00m

#PV #LV #SN Attr
VSize VFree
1
3
0 wz--n- 7.87g 876.00m

The installer allocates three Logical Volumes (LV) inside this VG:
1 smartmontools homepage https://www.smartmontools.org


```
# lvs
LV
VG
data pve
root pve
swap pve
```


Attr
LSize
Pool Origin Data%
twi-a-tz-4.38g
0.00
-wi-ao---1.75g
-wi-ao---- 896.00m


Meta%

## 0.63 root

Formatted as ext4, and contains the operating system.
swap
Swap partition
data
This volume uses LVM-thin, and is used to store VM images. LVM-thin is preferable for this task,
because it offers efficient support for snapshots and clones.
For Proxmox VE versions up to 4.1, the installer creates a standard logical volume called “data”, which is
mounted at /var/lib/vz.
Starting from version 4.2, the logical volume “data” is a LVM-thin pool, used to store block based guest
images, and /var/lib/vz is simply a directory on the root file system.


### 3.8.1 Hardware


We highly recommend to use a hardware RAID controller (with BBU) for such setups. This increases performance, provides redundancy, and make disk replacements easier (hot-pluggable).
LVM itself does not need any special hardware, and memory requirements are very low.


### 3.8.2 Bootloader


We install two boot loaders by default. The first partition contains the standard GRUB boot loader. The
second partition is an EFI System Partition (ESP), which makes it possible to boot on EFI systems and to
apply persistent firmware updates from the user space.


### 3.8.3 Creating a Volume Group


Let’s assume we have an empty disk /dev/sdb, onto which we want to create a volume group named
“vmdata”.


> **Caution:**
> Please note that the following commands will destroy all existing data on /dev/sdb.


First create a partition.


```
# sgdisk -N 1 /dev/sdb
Create a Physical Volume (PV) without confirmation and 250K metadatasize.

# pvcreate --metadatasize 250k -y -ff /dev/sdb1
Create a volume group named “vmdata” on /dev/sdb1

# vgcreate vmdata /dev/sdb1
```


### 3.8.4 Creating an extra LV for /var/lib/vz


This can be easily done by creating a new thin LV.


```
# lvcreate -n <Name> -V <Size[M,G,T]> <VG>/<LVThin_pool>
A real world example:

# lvcreate -n vz -V 10G pve/data
Now a filesystem must be created on the LV.

# mkfs.ext4 /dev/pve/vz
At last this has to be mounted.
```


> **Warning:**
> be sure that /var/lib/vz is empty. On a default installation it’s not.


To make it always accessible add the following line in /etc/fstab.


```
# echo '/dev/pve/vz /var/lib/vz ext4 defaults 0 2' >> /etc/fstab
```


### 3.8.5 Resizing the thin pool


Resize the LV and the metadata pool with the following command:

# lvresize --size +<size[\M,G,T]> --poolmetadatasize +<size[\M,G]> < ←VG>/<LVThin_pool>


> **Note:**
> When extending the data pool, the metadata pool must also be extended.


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

## See also

- [LVM Storage Backend](../ch07-storage/lvm-backend.md)
- [LVM-thin Storage Backend](../ch07-storage/lvm-thin-backend.md)

