# Directory Backend

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

List storage status


```
pvesm status
```

List storage contents


```
pvesm list <STORAGE_ID> [--vmid <VMID>]
```

List volumes allocated by VMID


```
pvesm list <STORAGE_ID> --vmid <VMID>
```

List iso images


```
pvesm list <STORAGE_ID> --content iso
```

List container templates


```
pvesm list <STORAGE_ID> --content vztmpl
```

Show file system path for a volume


```
pvesm path <VOLUME_ID>
```

Exporting the volume local:103/vm-103-disk-0.qcow2 to the file target. This is mostly used
internally with pvesm import. The stream format qcow2+size is different to the qcow2 format. Consequently, the exported file cannot simply be attached to a VM. This also holds for the other formats.


```
pvesm export local:103/vm-103-disk-0.qcow2 qcow2+size target --with- ←snapshots 1
```


## 7.5 Directory Backend


Storage pool type: dir
Proxmox VE can use local directories or locally mounted shares for storage. A directory is a file level storage,
so you can store any content type like virtual disk images, containers, templates, ISO images or backup files.

> **Note:**
> You can mount additional storages via standard linux /etc/fstab, and then define a directory storage
> for that mount point. This way you can use any file system supported by Linux.


This backend assumes that the underlying directory is POSIX compatible, but nothing else. This implies that
you cannot create snapshots at the storage level. But there exists a workaround for VM images using the
qcow2 file format, because that format supports snapshots internally.

> **Tip:**
> Some storage types do not support O_DIRECT, so you can’t use cache mode none with such storages.
> Simply use cache mode writeback instead.


We use a predefined directory layout to store different content types into different sub-directories. This layout
is used by all file level storage backends.

Table 7.2: Directory layout
Content type
VM images
ISO images
Container templates
Backup files
Snippets


### 7.5.1 Subdir


images/<VMID>/
template/iso/
template/cache/
dump/
snippets/

Configuration

This backend supports all common storage properties, and adds two additional properties. The path
property is used to specify the directory. This needs to be an absolute file system path.
The optional content-dirs property allows for the default layout to be changed. It consists of a commaseparated list of identifiers in the following format:

vtype=path
Where vtype is one of the allowed content types for the storage, and path is a path relative to the
mountpoint of the storage.
Configuration Example (/etc/pve/storage.cfg)

dir: backup
path /mnt/backup
content backup
prune-backups keep-last=7
max-protected-backups 3
content-dirs backup=custom/backup/dir
The above configuration defines a storage pool called backup. That pool can be used to store up to 7
regular backups (keep-last=7) and 3 protected backups per VM. The real path for the backup files is
/mnt/backup/custom/backup/dir/....


### 7.5.2 File naming conventions


This backend uses a well defined naming scheme for VM images:

vm-<VMID>-<NAME>.<FORMAT>

<VMID>
This specifies the owner VM.


<NAME>
This can be an arbitrary name (ascii) without white space. The backend uses disk-[N] as
default, where [N] is replaced by an integer to make the name unique.

<FORMAT>
Specifies the image format (raw|qcow2|vmdk).
When you create a VM template, all VM images are renamed to indicate that they are now read-only, and
can be used as a base image for clones:

base-<VMID>-<NAME>.<FORMAT>


> **Note:**
> Such base images are used to generate cloned images. So it is important that those files are read-only,
> and never get modified. The backend changes the access mode to 0444, and sets the immutable flag
> (chattr +i) if the storage supports that.


### 7.5.3 Storage Features


As mentioned above, most file systems do not support snapshots out of the box. To workaround that problem,
this backend is able to use qcow2 internal snapshot capabilities.
Same applies to clones. The backend uses the qcow2 base image feature to create clones.

Table 7.3: Storage features for backend dir
Content types

Image formats

images
rootdir
vztmpl iso
backup
snippets

raw qcow2
vmdk subvol


### 7.5.4 Shared

no

Snapshots
qcow2

Clones
qcow2

Examples

Please use the following command to allocate a 4GB image on storage local:


```
# pvesm alloc local 100 vm-100-disk10.raw 4G
Formatting '/var/lib/vz/images/100/vm-100-disk10.raw', fmt=raw size ←=4294967296
successfully created 'local:100/vm-100-disk10.raw'
```


> **Note:**
> The image name must conform to above naming conventions.


The real file system path is shown with:


```
# pvesm path local:100/vm-100-disk10.raw
/var/lib/vz/images/100/vm-100-disk10.raw
And you can remove the image with:

# pvesm free local:100/vm-100-disk10.raw
```


## 7.6 NFS Backend


Storage pool type: nfs
The NFS backend is based on the directory backend, so it shares most properties. The directory layout
and the file naming conventions are the same. The main advantage is that you can directly configure the
NFS server properties, so the backend can mount the share automatically. There is no need to modify
/etc/fstab. The backend can also test if the server is online, and provides a method to query the server
for exported shares.


### 7.6.1 Configuration


The backend supports all common storage properties, except the shared flag, which is always set. Additionally, the following properties are used to configure the NFS server:

server
Server IP or DNS name. To avoid DNS lookup delays, it is usually preferable to use an IP address
instead of a DNS name - unless you have a very reliable DNS server, or list the server in the local
/etc/hosts file.
export
NFS export path (as listed by pvesm nfsscan).
You can also set NFS mount options:

path
The local mount point (defaults to /mnt/pve/<STORAGE_ID>/).
content-dirs
Overrides for the default directory layout. Optional.
options
NFS mount options (see man nfs).
