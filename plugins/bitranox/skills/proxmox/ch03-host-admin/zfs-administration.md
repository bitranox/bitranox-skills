# ZFS Administration

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 3.9.6 ZFS Administration


This section gives you some usage examples for common tasks. ZFS itself is really powerful and provides
many options. The main commands to manage ZFS are zfs and zpool. Both commands come with great
manual pages, which can be read with:

# man zpool
# man zfs


Create a new zpool
To create a new pool, at least one disk is needed. The ashift should have the same sector-size (2 power
of ashift) or larger as the underlying disk.


```
# zpool create -f -o ashift=12 <pool> <device>
```


> **Tip:**
> Pool names must adhere to the following rules:


- begin with a letter (a-z or A-Z)
- contain only alphanumeric, -, _, ., : or ` ` (space) characters
- must not begin with one of mirror, raidz, draid or spare
- must not be log

To activate compression (see section Compression in ZFS):


```
# zfs set compression=lz4 <pool>
```


Create a new pool with RAID-0
Minimum 1 disk


```
# zpool create -f -o ashift=12 <pool> <device1> <device2>
```


Create a new pool with RAID-1
Minimum 2 disks


```
# zpool create -f -o ashift=12 <pool> mirror <device1> <device2>
```


Create a new pool with RAID-10
Minimum 4 disks


```
# zpool create -f -o ashift=12 <pool> mirror <device1> <device2> mirror < ←device3> <device4>
```


Create a new pool with RAIDZ-1
Minimum 3 disks


```
# zpool create -f -o ashift=12 <pool> raidz1 <device1> <device2> <device3>
```


Create a new pool with RAIDZ-2
Minimum 4 disks


```
# zpool create -f -o ashift=12 <pool> raidz2 <device1> <device2> <device3>
<device4>
```


←-

Please read the section for ZFS RAID Level Considerations to get a rough estimate on how IOPS and
bandwidth expectations before setting up a pool, especially when wanting to use a RAID-Z mode.

Extend RAIDZ-N

> **Note:**
> This feature only works starting with Proxmox VE 9 (ZFS 2.3.3).


Assuming you have an existing <pool> with a RAIDZ-N <raidzN-M> vdev, you can add a new physical
disk <device> using the following syntax:

zpool attach <pool> <raidzN-M> <device>
You can verify general success by running zpool status <pool> and get verbose output for all attached disks by running zpool list <pool> -v. To inspect the new capacity of your pool run zfs
list <pool>.

Create a new pool with cache (L2ARC)
It is possible to use a dedicated device, or partition, as second-level cache to increase the performance.
Such a cache device will especially help with random-read workloads of data that is mostly static. As it acts
as additional caching layer between the actual storage, and the in-memory ARC, it can also help if the ARC
must be reduced due to memory constraints.

Create ZFS pool with a on-disk cache


```
# zpool create -f -o ashift=12 <pool> <device> cache <cache-device>
Here only a single <device> and a single <cache-device> was used, but it is possible to use more
devices, like it’s shown in Create a new pool with RAID.
Note that for cache devices no mirror or raid modi exist, they are all simply accumulated.
If any cache device produces errors on read, ZFS will transparently divert that request to the underlying
storage layer.
```


Create a new pool with log (ZIL)
It is possible to use a dedicated drive, or partition, for the ZFS Intent Log (ZIL), it is mainly used to provide
safe synchronous transactions, so often in performance critical paths like databases, or other programs that
issue fsync operations more frequently.


The pool is used as default ZIL location, diverting the ZIL IO load to a separate device can, help to reduce
transaction latencies while relieving the main pool at the same time, increasing overall performance.
For disks to be used as log devices, directly or through a partition, it’s recommend to:

- use fast SSDs with power-loss protection, as those have much smaller commit latencies.
- Use at least a few GB for the partition (or whole device), but using more than half of your installed memory
won’t provide you with any real advantage.
Create ZFS pool with separate log device


```
# zpool create -f -o ashift=12 <pool> <device> log <log-device>
In the example above, a single <device> and a single <log-device> is used, but you can also combine
this with other RAID variants, as described in the Create a new pool with RAID section.
You can also mirror the log device to multiple devices, this is mainly useful to ensure that performance doesn’t
immediately degrades if a single log device fails.
If all log devices fail the ZFS main pool itself will be used again, until the log device(s) get replaced.
Add cache and log to an existing pool
If you have a pool without cache and log you can still add both, or just one of them, at any time.
For example, let’s assume you got a good enterprise SSD with power-loss protection that you want to use
for improving the overall performance of your pool.
As the maximum size of a log device should be about half the size of the installed physical memory, it means
that the ZIL will most likely only take up a relatively small part of the SSD, the remaining space can be used
as cache.
First you have to create two GPT partitions on the SSD with parted or gdisk.
Then you’re ready to add them to a pool:
Add both, a separate log device and a second-level cache, to an existing pool

# zpool add -f <pool> log <device-part1> cache <device-part2>
Just replace <pool>, <device-part1> and <device-part2> with the pool name and the two
/dev/disk/by-id/ paths to the partitions.
You can also add ZIL and cache separately.
Add a log device to an existing ZFS pool

# zpool add <pool> log <log-device>
```


Changing a failed device


```
# zpool replace -f <pool> <old-device> <new-device>
```


Changing a failed bootable device

Depending on how Proxmox VE was installed it is either using systemd-boot or GRUB through proxmox-boo
3 or plain GRUB as bootloader (see Host Bootloader). You can check by running:


```
# proxmox-boot-tool status
The first steps of copying the partition table, reissuing GUIDs and replacing the ZFS partition are the same.
To make the system bootable from the new disk, different steps are needed which depend on the bootloader
in use.

# sgdisk <healthy bootable device> -R <new device>
# sgdisk -G <new device>
# zpool replace -f <pool> <old zfs partition> <new zfs partition>
```


> **Note:**
> Use the zpool status -v command to monitor how far the resilvering process of the new disk has
> progressed.


With proxmox-boot-tool:


```
# proxmox-boot-tool format <new disk's ESP>
# proxmox-boot-tool init <new disk's ESP> [grub]
```


> **Note:**


ESP stands for EFI System Partition, which is set up as partition #2 on bootable disks when using the
Proxmox VE installer since version 5.4. For details, see Setting up a new partition for use as synced ESP.


> **Note:**
> Make sure to pass grub as mode to proxmox-boot-tool init if proxmox-boot-tool
> status indicates your current disks are using GRUB, especially if Secure Boot is enabled!


With plain GRUB:

# grub-install <new disk>


> **Note:**
> Plain GRUB is only used on systems installed with Proxmox VE 6.3 or earlier, which have not been
> manually migrated to use proxmox-boot-tool yet.
> 3 Systems installed with Proxmox VE 6.4 or later, EFI systems installed with Proxmox VE 5.4 or later


### 3.9.7 Configure E-Mail Notification


ZFS comes with an event daemon ZED, which monitors events generated by the ZFS kernel module. The
daemon can also send emails on ZFS events like pool errors. Newer ZFS packages ship the daemon in a
separate zfs-zed package, which should already be installed by default in Proxmox VE.
You can configure the daemon via the file /etc/zfs/zed.d/zed.rc with your favorite editor. The
required setting for email notification is ZED_EMAIL_ADDR, which is set to root by default.

ZED_EMAIL_ADDR="root"
Please note Proxmox VE forwards mails to root to the email address configured for the root user.


### 3.9.8 Limit ZFS Memory Usage


ZFS uses 50 % of the host memory for the Adaptive Replacement Cache (ARC) by default. For new installations starting with Proxmox VE 8.1, the ARC usage limit will be set to 10 % of the installed physical memory,
clamped to a maximum of 16 GiB. This value is written to /etc/modprobe.d/zfs.conf.
Allocating enough memory for the ARC is crucial for IO performance, so reduce it with caution. As a general
rule of thumb, allocate at least 2 GiB Base + 1 GiB/TiB-Storage. For example, if you have a
pool with 8 TiB of available storage space then you should use 10 GiB of memory for the ARC.
ZFS also enforces a minimum value of 64 MiB.
You can change the ARC usage limit for the current boot (a reboot resets this change again) by writing to the
zfs_arc_max module parameter directly:

echo "$[10 * 1024*1024*1024]" >/sys/module/zfs/parameters/zfs_arc_max

To permanently change the ARC limits, add (or change if already present) the following line to /etc/modprobe.

options zfs zfs_arc_max=8589934592
This example setting limits the usage to 8 GiB (8 * 230 ).

> **Important:**
> In case your desired zfs_arc_max value is lower than or equal to zfs_arc_min (which
> defaults to 1/32 of the system memory), zfs_arc_max will be ignored unless you also set
> zfs_arc_min to at most zfs_arc_max - 1.


echo "$[8 * 1024*1024*1024 - 1]" >/sys/module/zfs/parameters/zfs_arc_min
echo "$[8 * 1024*1024*1024]" >/sys/module/zfs/parameters/zfs_arc_max
This example setting (temporarily) limits the usage to 8 GiB (8 * 230 ) on systems with more than 256 GiB of
total memory, where simply setting zfs_arc_max alone would not work.

> **Important:**
> If your root file system is ZFS, you must update your initramfs every time this value changes:


# update-initramfs -u -k all
You must reboot to activate these changes.


### 3.9.9 SWAP on ZFS


Swap-space created on a zvol may generate some troubles, like blocking the server or generating a high IO
load, often seen when starting a Backup to an external Storage.
We strongly recommend to use enough memory, so that you normally do not run into low memory situations.
Should you need or want to add swap, it is preferred to create a partition on a physical disk and use it as
a swap device. You can leave some space free for this purpose in the advanced options of the installer.
Additionally, you can lower the “swappiness” value. A good value for servers is 10:


```
# sysctl -w vm.swappiness=10
To make the swappiness persistent, open /etc/sysctl.conf with an editor of your choice and add the
following line:
```


vm.swappiness = 10

Table 3.3: Linux kernel swappiness parameter values
Value

vm.swappiness = 0
vm.swappiness = 1
vm.swappiness = 10
vm.swappiness = 60
vm.swappiness = 100


## See also

- [ZFS on Linux](zfs.md)
- [ZFS Encryption, Compression and Special Devices](zfs-advanced.md)
- [ZFS Pool Storage Backend](../ch07-storage/zfs-pool-backend.md)
