# CRUSH and Ceph Client

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

warn
on
off


A health warning is issued if the suggested pg_num value differs too much from the
current value.
The pg_num is adjusted automatically with no need for any manual interaction.
No automatic pg_num adjustments are made, and no warning will be issued if the
PG count is not optimal.

The scaling factor can be adjusted to facilitate future data storage with the target_size, target_size_rati
and the pg_num_min options.


> **Warning:**
> By default, the autoscaler considers tuning the PG count of a pool if it is off by a factor of 3. This
> will lead to a considerable shift in data placement and might introduce a high load on the cluster.


You can find a more in-depth introduction to the PG autoscaler on Ceph’s Blog - New in Nautilus: PG merging
and autotuning.


## 8.10 Ceph CRUSH & Device Classes


The 13 (Controlled Replication Under Scalable Hashing) algorithm is at the foundation of Ceph.
13 https://ceph.com/assets/pdfs/weil-crush-sc06.pdf


CRUSH calculates where to store and retrieve data from. This has the advantage that no central indexing
service is needed. CRUSH works using a map of OSDs, buckets (device locations) and rulesets (data
replication) for pools.

> **Note:**
> Further information can be found in the Ceph documentation, under the section CRUSH map a .
> a CRUSH map https://docs.ceph.com/en/squid/rados/operations/crush-map/


This map can be altered to reflect different replication hierarchies. The object replicas can be separated
(e.g., failure domains), while maintaining the desired distribution.
A common configuration is to use different classes of disks for different Ceph pools. For this reason, Ceph
introduced device classes with luminous, to accommodate the need for easy ruleset generation.
The device classes can be seen in the ceph osd tree output. These classes represent their own root bucket,
which can be seen with the below command.

ceph osd crush tree --show-shadow
Example output form the above command:

ID CLASS WEIGHT TYPE NAME
-16 nvme 2.18307 root default~nvme
-13 nvme 0.72769
host sumi1~nvme
12 nvme 0.72769
osd.12
-14 nvme 0.72769
host sumi2~nvme
13 nvme 0.72769
osd.13
-15 nvme 0.72769
host sumi3~nvme
14 nvme 0.72769
osd.14
-1

## 7.70544 root default

-3

## 2.56848 host sumi1

12 nvme 0.72769
osd.12
-5

## 2.56848 host sumi2

13 nvme 0.72769
osd.13
-7

## 2.56848 host sumi3

14 nvme 0.72769
osd.14
To instruct a pool to only distribute objects on a specific device class, you first need to create a ruleset for
the device class:

ceph osd crush rule create-replicated <rule-name> <root> <failure-domain> < ←class>
<rule-name>
<root>
<failure-domain>
<class>

name of the rule, to connect with a pool (seen in GUI & CLI)
which crush root it should belong to (default Ceph root "default")
at which failure-domain the objects should be distributed (usually host)
what type of OSD backing store to use (e.g., nvme, ssd, hdd)

Once the rule is in the CRUSH map, you can tell a pool to use the ruleset.

ceph osd pool set <pool-name> crush_rule <rule-name>


> **Tip:**
> If the pool already contains objects, these must be moved accordingly. Depending on your setup, this may
> introduce a big performance impact on your cluster. As an alternative, you can create a new pool and
> move disks separately.


## 8.11 Ceph Client


Following the setup from the previous sections, you can configure Proxmox VE to use such pools to store
VM and Container images. Simply use the GUI to add a new RBD storage (see section Ceph RADOS Block
Devices (RBD)).
You also need to copy the keyring to a predefined location for an external Ceph cluster. If Ceph is installed
on the Proxmox nodes itself, then this will be done automatically.

> **Note:**
> The filename needs to be <storage_id> + `.keyring, where <storage_id> is the expression after rbd: in /etc/pve/storage.cfg. In the following example, my-ceph-storage is the
> <storage_id>:


mkdir /etc/pve/priv/ceph
cp /etc/ceph/ceph.client.admin.keyring /etc/pve/priv/ceph/my-ceph-storage. ←keyring


## 8.12 CephFS


Ceph also provides a filesystem, which runs on top of the same object storage as RADOS block devices do.
A Metadata Server (MDS) is used to map the RADOS backed objects to files and directories, allowing Ceph
to provide a POSIX-compliant, replicated filesystem. This allows you to easily configure a clustered, highly
available, shared filesystem. Ceph’s Metadata Servers guarantee that files are evenly distributed over the
entire Ceph cluster. As a result, even cases of high load will not overwhelm a single host, which can be an
issue with traditional shared filesystem approaches, for example NFS.

Proxmox VE supports both creating a hyper-converged CephFS and using an existing CephFS as storage
to save backups, ISO files, and container templates.


### 8.12.1 Metadata Server (MDS)


CephFS needs at least one Metadata Server to be configured and running, in order to function. You can
create an MDS through the Proxmox VE web GUI’s Node -> CephFS panel or from the command line
with:


```
pveceph mds create
```

