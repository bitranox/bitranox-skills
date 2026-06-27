# Ceph RADOS Block Devices (RBD)

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

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


### 7.14.1 Configuration


This backend supports the common storage properties nodes, disable, content, and the following
rbd specific properties:

monhost
List of monitor daemon IPs. Optional, only needed if Ceph is not running on the Proxmox VE cluster.
pool
Ceph pool name.
username
RBD user ID. Optional, only needed if Ceph is not running on the Proxmox VE cluster. Note that only
the user ID should be used. The "client." type prefix must be left out.
krbd
Enforce access to rados block devices through the krbd kernel module. Optional.

> **Note:**
> Containers will use krbd independent of the option value.


Configuration Example for a external Ceph cluster (/etc/pve/storage.cfg)

rbd: ceph-external
monhost 10.1.1.20 10.1.1.21 10.1.1.22
pool ceph-external
content images
username admin


> **Tip:**
> You can use the rbd utility to do low-level management tasks.


### 7.14.2 Authentication


> **Note:**
> If Ceph is installed locally on the Proxmox VE cluster, the following is done automatically when adding the
> storage.


If you use cephx authentication, which is enabled by default, you need to provide the keyring from the
external Ceph cluster.
To configure the storage via the CLI, you first need to make the file containing the keyring available. One
way is to copy the file from the external Ceph cluster directly to one of the Proxmox VE nodes. The following
example will copy it to the /root directory of the node on which we run it:


# scp <external cephserver>:/etc/ceph/ceph.client.admin.keyring /root/rbd. ←keyring
Then use the pvesm CLI tool to configure the external RBD storage, use the --keyring parameter, which
needs to be a path to the keyring file that you copied. For example:


```
# pvesm add rbd <name> --monhost "10.1.1.20 10.1.1.21 10.1.1.22" --content
images --keyring /root/rbd.keyring
```


←-

When configuring an external RBD storage via the GUI, you can copy and paste the keyring into the appropriate field.
The keyring will be stored at

# /etc/pve/priv/ceph/<STORAGE_ID>.keyring


> **Tip:**
> Creating a keyring with only the needed capabilities is recommend when connecting to an external cluster.
> For further information on Ceph user management, see the Ceph docs.a
> a Ceph User Management


### 7.14.3 Ceph client configuration (optional)


Connecting to an external Ceph storage doesn’t always allow setting client-specific options in the config DB
on the external cluster. You can add a ceph.conf beside the Ceph keyring to change the Ceph client
configuration for the storage.
The ceph.conf needs to have the same name as the storage.

# /etc/pve/priv/ceph/<STORAGE_ID>.conf
See the RBD configuration reference 1 for possible settings.

> **Note:**
> Do not change these settings lightly. Proxmox VE is merging the <STORAGE_ID>.conf with the storage
> configuration.


### 7.14.4 Storage Features


The rbd backend is a block level storage, and implements full snapshot and clone functionality.

1 RBD configuration reference https://docs.ceph.com/en/squid/rbd/rbd-config-ref/


Table 7.12: Storage features for backend rbd
Content types

Image formats

images
rootdir

raw


## 7.15 Shared

yes

Snapshots
yes

Clones
yes

Ceph Filesystem (CephFS)

Storage pool type: cephfs
CephFS implements a POSIX-compliant filesystem, using a Ceph storage cluster to store its data. As
CephFS builds upon Ceph, it shares most of its properties. This includes redundancy, scalability, selfhealing, and high availability.

> **Tip:**
> Proxmox VE can manage Ceph setups, which makes configuring a CephFS storage easier. As modern
> hardware offers a lot of processing power and RAM, running storage services and VMs on same node is
> possible without a significant performance impact.


To use the CephFS storage plugin, you must replace the stock Debian Ceph client, by adding our Ceph
repository. Once added, run apt update, followed by apt dist-upgrade, in order to get the newest
packages.


> **Warning:**
> Please ensure that there are no other Ceph repositories configured. Otherwise the installation will
> fail or there will be mixed package versions on the node, leading to unexpected behavior.


### 7.15.1 Configuration


This backend supports the common storage properties nodes, disable, content, as well as the following cephfs specific properties:

fs-name
Name of the Ceph FS.
monhost
List of monitor daemon addresses. Optional, only needed if Ceph is not running on the Proxmox VE
cluster.
path
The local mount point. Optional, defaults to /mnt/pve/<STORAGE_ID>/.

## See also

- [Ceph Cluster](../ch08-ceph/_index.md)

