# LVM thin Backend

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 7.11 LVM thin Backend


Storage pool type: lvmthin
LVM normally allocates blocks when you create a volume. LVM thin pools instead allocates blocks when they
are written. This behaviour is called thin-provisioning, because volumes can be much larger than physically
available space.
You can use the normal LVM command-line tools to manage and create LVM thin pools (see man lvmthin
for details). Assuming you already have a LVM volume group called pve, the following commands create a
new LVM thin pool (size 100G) called data:

lvcreate -L 100G -n data pve
lvconvert --type thin-pool pve/data


### 7.11.1 Configuration


The LVM thin backend supports the common storage properties content, nodes, disable, and the
following LVM specific properties:

vgname
LVM volume group name. This must point to an existing volume group.

thinpool
The name of the LVM thin pool.

Configuration Example (/etc/pve/storage.cfg)

lvmthin: local-lvm
thinpool data
vgname pve
content rootdir,images


### 7.11.2 File naming conventions


The backend use basically the same naming conventions as the ZFS pool backend.

vm-<VMID>-<NAME>


### 7.11.3 // normal VM images


Storage Features

LVM thin is a block storage, but fully supports snapshots and clones efficiently. New volumes are automatically initialized with zero.
It must be mentioned that LVM thin pools cannot be shared across multiple nodes, so you can only use them
as local storage.


Table 7.9: Storage features for backend lvmthin
Content types

Image formats

images
rootdir

raw


### 7.11.4 Shared

no

Snapshots
yes

Clones
yes

Examples

You can get a list of available LVM thin pools on the volume group pve with:


```
# pvesm scan lvmthin pve
```


## 7.12 Open-iSCSI initiator


Storage pool type: iscsi
iSCSI is a widely employed technology used to connect to storage servers. Almost all storage vendors
support iSCSI. There are also open source iSCSI target solutions available, e.g. OpenMediaVault, which is
based on Debian.
To use this backend, you need to install the Open-iSCSI (open-iscsi) package. This is a standard Debian
package, but it is not installed by default to save resources.


```
# apt-get install open-iscsi
Low-level iscsi management task can be done using the iscsiadm tool.
```


### 7.12.1 Configuration


The backend supports the common storage properties content, nodes, disable, and the following
iSCSI specific properties:

portal
iSCSI portal (IP or DNS name with optional port).
target
iSCSI target.
Configuration Example (/etc/pve/storage.cfg)

iscsi: mynas
portal 10.10.10.1
target iqn.2006-01.openfiler.com:tsn.dcb5aaaddd
content none
