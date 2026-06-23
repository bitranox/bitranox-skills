# Local ZFS Pool Backend

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

It is recommended that you keep your key safe, but easily accessible, in order for quick disaster recovery.
For this reason, the best place to store it is in your password manager, where it is immediately recoverable.
As a backup to this, you should also save the key to a USB flash drive and store that in a secure place.
This way, it is detached from any system, but is still easy to recover from, in case of emergency. Finally, in
preparation for the worst case scenario, you should also consider keeping a paper copy of your key locked
away in a safe place. The paperkey subcommand can be used to create a QR encoded version of your
key. The following command sends the output of the paperkey command to a text file, for easy printing.

# proxmox-backup-client key paperkey /etc/pve/priv/storage/<STORAGE-ID>.enc ←--output-format text > qrkey.txt
Additionally, it is possible to use a single RSA master key pair for key recovery purposes: configure all
clients doing encrypted backups to use a single public master key, and all subsequent encrypted backups
will contain a RSA-encrypted copy of the used AES encryption key. The corresponding private master key
allows recovering the AES key and decrypting the backup even if the client system is no longer available.

> **Warning:**
> The same safe-keeping rules apply to the master key pair as to the regular encryption keys. Without
> a copy of the private key recovery is not possible! The paperkey command supports generating
> paper copies of private master keys for storage in a safe, physical location.


Because the encryption is managed on the client side, you can use the same datastore on the server for
unencrypted backups and encrypted backups, even if they are encrypted with different keys. However,
deduplication between backups with different keys is not possible, so it is often better to create separate
datastores.

> **Note:**
> Do not use encryption if there is no benefit from it, for example, when you are running the server locally in
> a trusted network. It is always easier to recover from unencrypted backups.


### 7.8.4 Example: Add Storage over CLI


You can get a list of available Proxmox Backup Server datastores with:


```
# pvesm scan pbs <server> <username> [--password <string>] [--fingerprint < ←string>]
Then you can add one of these datastores as a storage to the whole Proxmox VE cluster with:

# pvesm add pbs <id> --server <server> --datastore <datastore> --username < ←username> --fingerprint 00:B4:... --password
```


## 7.9 Local ZFS Pool Backend


Storage pool type: zfspool
This backend allows you to access local ZFS pools (or ZFS file systems inside such pools).


### 7.9.1 Configuration


The backend supports the common storage properties content, nodes, disable, and the following
ZFS specific properties:

pool
Select the ZFS pool/filesystem. All allocations are done within that pool.
blocksize
Set ZFS blocksize parameter.
sparse
Use ZFS thin-provisioning. A sparse volume is a volume whose reservation is not equal to the volume
size.
mountpoint
The mount point of the ZFS pool/filesystem. Changing this does not affect the mountpoint property
of the dataset seen by zfs. Defaults to /<pool>.

Configuration Example (/etc/pve/storage.cfg)

zfspool: vmdata
pool tank/vmdata
content rootdir,images
sparse


### 7.9.2 File naming conventions


The backend uses the following naming scheme for VM images:

vm-<VMID>-<NAME>
base-<VMID>-<NAME>
subvol-<VMID>-<NAME>

// normal VM images
// template VM image (read-only)
// subvolumes (ZFS filesystem for containers)

<VMID>
This specifies the owner VM.

<NAME>
This can be an arbitrary name (ascii) without white space. The backend uses disk[N] as default,
where [N] is replaced by an integer to make the name unique.


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

## See also

- [ZFS on Linux (Host)](../ch03-host-admin/zfs.md)

