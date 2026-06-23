# Proxmox Backup Server

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

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


### 7.8.1 Configuration


The backend supports all common storage properties, except the shared flag, which is always set. Additionally, the following special properties to Proxmox Backup Server are available:

server
Server IP or DNS name. Required.
port
Use this port instead of the default one, i.e. 8007. Optional.
username
The username for the Proxmox Backup Server storage. Required.

> **Tip:**
> Do not forget to add the realm to the username. For example, root@pam or archiver@pbs.


password
The user password. The value will be saved in a file under /etc/pve/priv/storage/<STORAGE-ID>
with access restricted to the root user. Required.
datastore
The ID of the Proxmox Backup Server datastore to use. Required.
fingerprint
The fingerprint of the Proxmox Backup Server API TLS certificate. You can get it in the Servers
Dashboard or using the proxmox-backup-manager cert info command. Required for selfsigned certificates or any other one where the host does not trusts the servers CA.

encryption-key
A key to encrypt the backup data from the client side. Currently only non-password protected (no key
derive function (kdf)) are supported. Will be saved in a file under /etc/pve/priv/storage/<STORAGE
with access restricted to the root user. Use the magic value autogen to automatically generate a
new one using proxmox-backup-client key create --kdf none <path>. Optional.
master-pubkey
A public RSA key used to encrypt the backup encryption key as part of the backup task. Will be
saved in a file under /etc/pve/priv/storage/<STORAGE-ID>.master.pem with access
restricted to the root user. The encrypted copy of the backup encryption key will be appended to each
backup and stored on the Proxmox Backup Server instance for recovery purposes. Optional, requires
encryption-key.


Configuration Example (/etc/pve/storage.cfg)

pbs: backup
datastore main
server enya.proxmox.com
content backup
fingerprint 09:54:ef:..snip..:88:af:47:fe:4c:3b:cf:8b:26:88:0b:4e:3 ←c:b2
prune-backups keep-all=1
username archiver@pbs
encryption-key a9:ee:c8:02:13:..snip..:2d:53:2c:98
master-pubkey 1


### 7.8.2 Storage Features


Proxmox Backup Server only supports backups, they can be block-level or file-level based. Proxmox VE
uses block-level for virtual machines and file-level for container.

Table 7.6: Storage features for backend pbs
Content types

backup


### 7.8.3 Image formats

n/a

Shared
yes

Snapshots
n/a

Clones
n/a

Encryption

Optionally, you can configure client-side encryption with AES-256 in GCM mode. Encryption can be configured either via the web interface, or on the CLI with the encryption-key option (see above). The key
will be saved in the file /etc/pve/priv/storage/<STORAGE-ID>.enc, which is only accessible
by the root user.

> **Warning:**
> Without their key, backups will be inaccessible. Thus, you should keep keys ordered and in a place
> that is separate from the contents being backed up. It can happen, for example, that you back up an
> entire system, using a key on that system. If the system then becomes inaccessible for any reason
> and needs to be restored, this will not be possible as the encryption key will be lost along with the
> broken system.


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
