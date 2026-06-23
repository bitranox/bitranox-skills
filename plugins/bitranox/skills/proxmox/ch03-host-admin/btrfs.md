# BTRFS

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

- A system with root on ZFS, that still boots using GRUB will become unbootable if a new feature is active
on the rpool, due to the incompatible implementation of ZFS in GRUB.

- The system will not be able to import any upgraded pool when booted with an older kernel, which still ships
with the old ZFS modules.

- Booting an older Proxmox VE ISO to repair a non-booting system will likewise not work.

> **Important:**
> Do not upgrade your rpool if your system is still booted with GRUB, as this will render your system
> unbootable. This includes systems installed before Proxmox VE 5.4, and systems booting with
> legacy BIOS boot (see how to determine the bootloader).


Enable new features for a ZFS pool:


```
# zpool upgrade <pool>
```


## 3.10 BTRFS


> **Warning:**
> BTRFS integration is currently a technology preview in Proxmox VE.


BTRFS is a modern copy on write file system natively supported by the Linux kernel, implementing features
such as snapshots, built-in RAID and self healing via checksums for data and metadata. Starting with
Proxmox VE 7.0, BTRFS is introduced as optional selection for the root file system.

**General BTRFS Advantages**
- Main system setup almost identical to the traditional ext4 based setup
- Snapshots
- Data compression on file system level
- Copy-on-write clone
- RAID0, RAID1 and RAID10
- Protection against data corruption
- Self healing
- Natively supported by the Linux kernel
**Caveats**
- RAID levels 5/6 are experimental and dangerous, see BTRFS Status


### 3.10.1 Installation as Root File System


When you install using the Proxmox VE installer, you can choose BTRFS for the root file system. You need
to select the RAID type at installation time:
RAID0

RAID1
RAID10

Also called “striping”. The capacity of such volume is the sum of the capacities of all
disks. But RAID0 does not add any redundancy, so the failure of a single drive
makes the volume unusable.
Also called “mirroring”. Data is written identically to all disks. This mode requires at
least 2 disks with the same size. The resulting capacity is that of a single disk.
A combination of RAID0 and RAID1. Requires at least 4 disks.

The installer automatically partitions the disks and creates an additional subvolume at /var/lib/pve/local-b
In order to use that with the Proxmox VE tools, the installer creates the following configuration entry in
/etc/pve/storage.cfg:

dir: local
path /var/lib/vz
content iso,vztmpl,backup
disable
btrfs: local-btrfs
path /var/lib/pve/local-btrfs
content iso,vztmpl,backup,images,rootdir
This explicitly disables the default local storage in favor of a BTRFS specific storage entry on the additional
subvolume.
The btrfs command is used to configure and manage the BTRFS file system, After the installation, the
following command lists all additional subvolumes:


```
# btrfs subvolume list /
ID 256 gen 6 top level 5 path var/lib/pve/local-btrfs
```


### 3.10.2 BTRFS Administration


This section gives you some usage examples for common tasks.
Creating a BTRFS file system
To create BTRFS file systems, mkfs.btrfs is used. The -d and -m parameters are used to set the
profile for metadata and data respectively. With the optional -L parameter, a label can be set.
Generally, the following modes are supported: single, raid0, raid1, raid10.
Create a BTRFS file system on a single disk /dev/sdb with the label My-Storage:


```
# mkfs.btrfs -m single -d single -L My-Storage /dev/sdb
Or create a RAID1 on the two partitions /dev/sdb1 and /dev/sdc1:

# mkfs.btrfs -m raid1 -d raid1 -L My-Storage /dev/sdb1 /dev/sdc1
```


Mounting a BTRFS file system
The new file-system can then be mounted either manually, for example:


```
# mkdir /my-storage
# mount /dev/sdb /my-storage
A BTRFS can also be added to /etc/fstab like any other mount point, automatically mounting it on boot.
It’s recommended to avoid using block-device paths but use the UUID value the mkfs.btrfs command
printed, especially there is more than one disk in a BTRFS setup.
For example:
File /etc/fstab

# ... other mount points left out for brevity
# using the UUID from the mkfs.btrfs output is highly recommended
UUID=e2c0c3ff-2114-4f54-b767-3a203e49f6f3 /my-storage btrfs defaults 0 0
```


> **Tip:**
> If you do not have the UUID available anymore you can use the blkid tool to list all properties of blockdevices.


Afterwards you can trigger the first mount by executing:

mount /my-storage
After the next reboot this will be automatically done by the system at boot.
Adding a BTRFS file system to Proxmox VE
You can add an existing BTRFS file system to Proxmox VE via the web interface, or using the CLI, for
example:


```
pvesm add btrfs my-storage --path /my-storage
```


Creating a subvolume
Creating a subvolume links it to a path in the BTRFS file system, where it will appear as a regular directory.


```
# btrfs subvolume create /some/path
Afterwards /some/path will act like a regular directory.
Deleting a subvolume
Contrary to directories removed via rmdir, subvolumes do not need to be empty in order to be deleted via
the btrfs command.

# btrfs subvolume delete /some/path
```


Creating a snapshot of a subvolume
BTRFS does not actually distinguish between snapshots and normal subvolumes, so taking a snapshot can
also be seen as creating an arbitrary copy of a subvolume. By convention, Proxmox VE will use the read-only
flag when creating snapshots of guest disks or subvolumes, but this flag can also be changed later on.


```
# btrfs subvolume snapshot -r /some/path /a/new/path
This will create a read-only "clone" of the subvolume on /some/path at /a/new/path. Any future
modifications to /some/path cause the modified data to be copied before modification.
If the read-only (-r) option is left out, both subvolumes will be writable.
Enabling compression
By default, BTRFS does not compress data. To enable compression, the compress mount option can be
added. Note that data already written will not be compressed after the fact.
By default, the rootfs will be listed in /etc/fstab as follows:
```


UUID=<uuid of your root file system> / btrfs defaults 0 1
You can simply append compress=zstd, compress=lzo, or compress=zlib to the defaults
above like so:

UUID=<uuid of your root file system> / btrfs defaults,compress=zstd 0 1
This change will take effect after rebooting.
Checking Space Usage
The classic df tool may output confusing values for some BTRFS setups. For a better estimate use the
btrfs filesystem usage /PATH command, for example:


```
# btrfs fi usage /my-storage
```


## 3.11 Proxmox Node Management


The Proxmox VE node management tool (pvenode) allows you to control node specific settings and resources.
Currently pvenode allows you to set a node’s description, run various bulk operations on the node’s guests,
view the node’s task history, and manage the node’s SSL certificates, which are used for the API and the
web GUI through pveproxy.


### 3.11.1 Wake-on-LAN


Wake-on-LAN (WoL) allows you to switch on a sleeping computer in the network, by sending a magic packet.
At least one NIC must support this feature, and the respective option needs to be enabled in the computer’s
firmware (BIOS/UEFI) configuration. The option name can vary from Enable Wake-on-Lan to Power On By
PCIE Device; check your motherboard’s vendor manual, if you’re unsure. ethtool can be used to check
the WoL configuration of <interface> by running:

## See also

- [BTRFS Storage Backend](../ch07-storage/btrfs-backend.md)

