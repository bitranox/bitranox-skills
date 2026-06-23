# CIFS Backend

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Configuration Example (/etc/pve/storage.cfg)

nfs: iso-templates
path /mnt/pve/iso-templates
server 10.0.0.10
export /space/iso-templates
options vers=3,soft
content iso,vztmpl


> **Tip:**
> After an NFS request times out, NFS request are retried indefinitely by default. This can lead to unexpected
> hangs on the client side. For read-only content, it is worth to consider the NFS soft option, which limits
> the number of retries to three.


### 7.6.2 Storage Features


NFS does not support snapshots, but the backend uses qcow2 features to implement snapshots and
cloning.

Table 7.4: Storage features for backend nfs
Content types

Image formats

images
rootdir
vztmpl iso
backup
snippets

raw qcow2
vmdk


### 7.6.3 Shared

yes

Snapshots
qcow2

Clones
qcow2

Examples

You can get a list of exported NFS shares with:


```
# pvesm scan nfs <server>
```


## 7.7 CIFS Backend


Storage pool type: cifs
The CIFS backend extends the directory backend, so that no manual setup of a CIFS mount is needed. Such
a storage can be added directly through the Proxmox VE API or the web UI, with all our backend advantages,
like server heartbeat check or comfortable selection of exported shares.


### 7.7.1 Configuration


The backend supports all common storage properties, except the shared flag, which is always set. Additionally, the following CIFS special properties are available:

server
Server IP or DNS name. Required.

> **Tip:**
> To avoid DNS lookup delays, it is usually preferable to use an IP address instead of a DNS name - unless
> you have a very reliable DNS server, or list the server in the local /etc/hosts file.


share
CIFS share to use (get available ones with pvesm scan cifs <address> or the web UI). Required.
username
The username for the CIFS storage. Optional, defaults to ‘guest’.

password
The user password. Optional. It will be saved in a file only readable by root (/etc/pve/priv/storage/
domain
Sets the user domain (workgroup) for this storage. Optional.
smbversion
SMB protocol Version. Optional, default is 3. SMB1 is not supported due to security issues.
path
The local mount point. Optional, defaults to /mnt/pve/<STORAGE_ID>/.
content-dirs
Overrides for the default directory layout. Optional.
options
Additional CIFS mount options (see man mount.cifs). Some options are set automatically and
shouldn’t be set here. Proxmox VE will always set the option soft. Depending on the configuration,
these options are set automatically: username, credentials, guest, domain, vers.
subdir
The subdirectory of the share to mount. Optional, defaults to the root directory of the share.


Configuration Example (/etc/pve/storage.cfg)

cifs: backup
path /mnt/pve/backup
server 10.0.0.11
share VMData
content backup
options noserverino,echo_interval=30
username anna
smbversion 3
subdir /data


### 7.7.2 Storage Features


CIFS does not support snapshots on a storage level. But you may use qcow2 backing files if you still want
to have snapshots and cloning features available.

Table 7.5: Storage features for backend cifs
Content types

Image formats

images
rootdir
vztmpl iso
backup
snippets

raw qcow2
vmdk


### 7.7.3 Shared

yes

Snapshots
qcow2

Clones
qcow2

Examples

You can get a list of exported CIFS shares with:


```
# pvesm scan cifs <server> [--username <username>] [--password]
Then you can add one of these shares as a storage to the whole Proxmox VE cluster with:

# pvesm add cifs <storagename> --server <server> --share <share> [-- ←username <username>] [--password]
```


## 7.8 Proxmox Backup Server


Storage pool type: pbs
This backend allows direct integration of a Proxmox Backup Server into Proxmox VE like any other storage.
A Proxmox Backup storage can be added directly through the Proxmox VE API, CLI or the web interface.
