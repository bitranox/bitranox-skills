# iSCSI Backends

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

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


> **Tip:**
> If you want to use LVM on top of iSCSI, it make sense to set content none. That way it is not possible
> to create VMs using iSCSI LUNs directly.


### 7.12.2 File naming conventions


The iSCSI protocol does not define an interface to allocate or delete data. Instead, that needs to be done on
the target side and is vendor specific. The target simply exports them as numbered LUNs. So Proxmox VE
iSCSI volume names just encodes some information about the LUN as seen by the linux kernel.


### 7.12.3 Storage Features


iSCSI is a block level type storage, and provides no management interface. So it is usually best to export
one big LUN, and setup LVM on top of that LUN. You can then use the LVM plugin to manage the storage on
that iSCSI LUN.

Table 7.10: Storage features for backend iscsi
Content types

Image formats

images none

raw


### 7.12.4 Shared

yes

Snapshots
no

Clones
no

Examples

You can scan a remote iSCSI portal and get a list of possible targets with:


```
pvesm scan iscsi <HOST[:PORT]>
```


## 7.13 User Mode iSCSI Backend


Storage pool type: iscsidirect
This backend provides basically the same functionality as the Open-iSCSI backed, but uses a user-level
library to implement it. You need to install the libiscsi-bin package in order to use this backend.
It should be noted that there are no kernel drivers involved, so this can be viewed as performance optimization. But this comes with the drawback that you cannot use LVM on top of such iSCSI LUN. So you need to
manage all space allocations at the storage server side.


### 7.13.1 Configuration


The user mode iSCSI backend uses the same configuration options as the Open-iSCSI backed.


Configuration Example (/etc/pve/storage.cfg)

iscsidirect: faststore
portal 10.10.10.1
target iqn.2006-01.openfiler.com:tsn.dcb5aaaddd


### 7.13.2 Storage Features


> **Note:**
> This backend works with VMs only. Containers cannot use this driver.


Table 7.11: Storage features for backend iscsidirect
Content types

Image formats

images

raw


## 7.14 Shared

yes

Snapshots
no

Clones
no

Ceph RADOS Block Devices (RBD)

Storage pool type: rbd
Ceph is a distributed object store and file system designed to provide excellent performance, reliability and
scalability. RADOS block devices implement a feature rich block level storage, and you get the following
advantages:

- thin provisioning
- resizable volumes
- distributed and redundant (striped over multiple OSDs)
- full snapshot and clone capabilities
- self healing
- no single point of failure
- scalable to the exabyte level
- kernel and user space implementation available

> **Note:**
> For smaller deployments, it is also possible to run Ceph services directly on your Proxmox VE nodes.
> Recent hardware has plenty of CPU power and RAM, so running storage services and VMs on same
> node is possible.

