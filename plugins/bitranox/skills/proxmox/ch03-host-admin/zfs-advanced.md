# ZFS Encryption, Compression and Special Devices

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 3.9.10 Strategy

The kernel will swap only to avoid an out of memory condition
Minimum amount of swapping without disabling it entirely.
This value is sometimes recommended to improve performance
when sufficient memory exists in a system.
The default value.
The kernel will swap aggressively.

Encrypted ZFS Datasets

> **Warning:**
> Native ZFS encryption in Proxmox VE is experimental. Known limitations and issues include Replication with encrypted datasets a , as well as checksum errors when using Snapshots or ZVOLs. b
> a https://bugzilla.proxmox.com/show_bug.cgi?id=2350
> b https://github.com/openzfs/zfs/issues/11688


ZFS on Linux version 0.8.0 introduced support for native encryption of datasets. After an upgrade from
previous ZFS on Linux versions, the encryption feature can be enabled per pool:


```
# zpool get feature@encryption tank
NAME PROPERTY
VALUE
tank feature@encryption disabled
```


SOURCE
local


```
# zpool set feature@encryption=enabled
# zpool get feature@encryption tank
NAME PROPERTY
VALUE
tank feature@encryption enabled
```


SOURCE
local


> **Warning:**
> There is currently no support for booting from pools with encrypted datasets using GRUB, and
> only limited support for automatically unlocking encrypted datasets on boot. Older versions of ZFS
> without encryption support will not be able to decrypt stored data.


> **Note:**
> It is recommended to either unlock storage datasets manually after booting, or to write a custom unit to
> pass the key material needed for unlocking on boot to zfs load-key.


> **Warning:**
> Establish and test a backup procedure before enabling encryption of production data. If the associated key material/passphrase/keyfile has been lost, accessing the encrypted data is no longer
> possible.


Encryption needs to be setup when creating datasets/zvols, and is inherited by default to child datasets. For
example, to create an encrypted dataset tank/encrypted_data and configure it as storage in Proxmox
VE, run the following commands:


```
# zfs create -o encryption=on -o keyformat=passphrase tank/encrypted_data
Enter passphrase:
Re-enter passphrase:
# pvesm add zfspool encrypted_zfs -pool tank/encrypted_data
All guest volumes/disks create on this storage will be encrypted with the shared key material of the parent
dataset.
To actually use the storage, the associated key material needs to be loaded and the dataset needs to be
mounted. This can be done in one step with:

# zfs mount -l tank/encrypted_data
Enter passphrase for 'tank/encrypted_data':
It is also possible to use a (random) keyfile instead of prompting for a passphrase by setting the keylocation
and keyformat properties, either at creation time or with zfs change-key on existing datasets:

# dd if=/dev/urandom of=/path/to/keyfile bs=32 count=1
# zfs change-key -o keyformat=raw -o keylocation=file:///path/to/keyfile
tank/encrypted_data
```


←-


> **Warning:**
> When using a keyfile, special care needs to be taken to secure the keyfile against unauthorized
> access or accidental loss. Without the keyfile, it is not possible to access the plaintext data!


A guest volume created underneath an encrypted dataset will have its encryptionroot property set
accordingly. The key material only needs to be loaded once per encryptionroot to be available to all encrypted
datasets underneath it.
See the encryptionroot, encryption, keylocation, keyformat and keystatus properties, the zfs load-key, zfs unload-key and zfs change-key commands and the Encryption
section from man zfs for more details and advanced usage.


### 3.9.11 Compression in ZFS


When compression is enabled on a dataset, ZFS tries to compress all new blocks before writing them and
decompresses them on reading. Already existing data will not be compressed retroactively.
You can enable compression with:


```
# zfs set compression=<algorithm> <dataset>
We recommend using the lz4 algorithm, because it adds very little CPU overhead. Other algorithms like
lzjb and gzip-N, where N is an integer from 1 (fastest) to 9 (best compression ratio), are also available. Depending on the algorithm and how compressible the data is, having compression enabled can even
increase I/O performance.
You can disable compression at any time with:

# zfs set compression=off <dataset>
Again, only new blocks will be affected by this change.
```


### 3.9.12 ZFS Special Device


Since version 0.8.0 ZFS supports special devices. A special device in a pool is used to store metadata, deduplication tables, and optionally small file blocks.
A special device can improve the speed of a pool consisting of slow spinning hard disks with a lot of
metadata changes. For example workloads that involve creating, updating or deleting a large number of
files will benefit from the presence of a special device. ZFS datasets can also be configured to store
whole small files on the special device which can further improve the performance. Use fast SSDs for the
special device.


> **Important:**
> The redundancy of the special device should match the one of the pool, since the special
> device is a point of failure for the whole pool.


> **Warning:**
> Adding a special device to a pool cannot be undone!


Create a pool with special device and RAID-1:


```
# zpool create -f -o ashift=12 <pool> mirror <device1> <device2> special
mirror <device3> <device4>
```


←-

Add a special device to an existing pool with RAID-1:


```
# zpool add <pool> special mirror <device1> <device2>
ZFS datasets expose the special_small_blocks=<size> property. size can be 0 to disable
storing small file blocks on the special device or a power of two in the range between 512B to 1M. After
setting the property new file blocks smaller than size will be allocated on the special device.
```


> **Important:**
> If the value for special_small_blocks is greater than or equal to the recordsize (default
> 128K) of the dataset, all data will be written to the special device, so be careful!


Setting the special_small_blocks property on a pool will change the default value of that property
for all child ZFS datasets (for example all containers in the pool will opt in for small file blocks).

Opt in for all file smaller than 4K-blocks pool-wide:


```
# zfs set special_small_blocks=4K <pool>
```


Opt in for small file blocks for a single dataset:


```
# zfs set special_small_blocks=4K <pool>/<filesystem>
```


Opt out from small file blocks for a single dataset:


```
# zfs set special_small_blocks=0 <pool>/<filesystem>
```


### 3.9.13 ZFS Pool Features


Changes to the on-disk format in ZFS are only made between major version changes and are specified
through features. All features, as well as the general mechanism are well documented in the zpool-features(
manpage.
Since enabling new features can render a pool not importable by an older version of ZFS, this needs to be
done actively by the administrator, by running zpool upgrade on the pool (see the zpool-upgrade(8)
manpage).
Unless you need to use one of the new features, there is no upside to enabling them.
In fact, there are some downsides to enabling new features:


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

## See also

## See also

- [ZFS on Linux](zfs.md)
- [ZFS Administration](zfs-administration.md)
- [ZFS Pool Storage Backend](../ch07-storage/zfs-pool-backend.md)
- [ZFS over iSCSI Backend](../ch07-storage/zfs-over-iscsi.md)
