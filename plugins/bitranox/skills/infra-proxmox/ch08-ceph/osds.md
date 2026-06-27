# Ceph OSDs

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 8.7 Ceph OSDs


Ceph Object Storage Daemons store objects for Ceph over the network. It is recommended to use one OSD
per physical disk.


### 8.7.1 Create OSDs


You can create an OSD either via the Proxmox VE web interface or via the CLI using pveceph. For
example:


```
pveceph osd create /dev/sd[X]
```


> **Tip:**
> We recommend a Ceph cluster with at least three nodes and at least 12 OSDs, evenly distributed among
> the nodes.


If the disk was in use before (for example, for ZFS or as an OSD) you first need to zap all traces of that usage.
To remove the partition table, boot sector and any other OSD leftover, you can use the following command:

ceph-volume lvm zap /dev/sd[X] --destroy


> **Warning:**
> The above command will destroy all data on the disk!


Ceph Bluestore
Starting with the Ceph Kraken release, a new Ceph OSD storage type was introduced called Bluestore 4 .
This is the default when creating OSDs since Ceph Luminous.


```
pveceph osd create /dev/sd[X]
```


Block.db and block.wal
If you want to use a separate DB/WAL device for your OSDs, you can specify it through the -db_dev and
-wal_dev options. The WAL is placed with the DB, if not specified separately.


```
pveceph osd create /dev/sd[X] -db_dev /dev/sd[Y] -wal_dev /dev/sd[Z]
```

You can directly choose the size of those with the -db_size and -wal_size parameters respectively. If they
are not given, the following values (in order) will be used:

- bluestore_block_{db,wal}_size from Ceph configuration. . .
– . . . database, section osd
– . . . database, section global
– . . . file, section osd
– . . . file, section global
- 10% (DB)/1% (WAL) of OSD size

> **Note:**
> The DB stores BlueStore’s internal metadata, and the WAL is BlueStore’s internal journal or write-ahead
> log. It is recommended to use a fast SSD or NVRAM for better performance.


Ceph Filestore
Before Ceph Luminous, Filestore was used as the default storage type for Ceph OSDs. Starting with Ceph
Nautilus, Proxmox VE does not support creating such OSDs with pveceph anymore. If you still want to create
filestore OSDs, use ceph-volume directly.

ceph-volume lvm create --filestore --data /dev/sd[X] --journal /dev/sd[Y]
4 Ceph Bluestore https://ceph.com/community/new-luminous-bluestore/


### 8.7.2 Destroy OSDs


If you experience problems with an OSD or its disk, try to troubleshoot them first to decide if a replacement
is needed.
To destroy an OSD, navigate to the <Node> → Ceph → OSD panel or use the mentioned CLI commands
on the node where the OSD is located.
1. Make sure the cluster has enough space to handle the removal of the OSD. In the Ceph → OSD
panel,if the to-be destroyed OSD is still up and in (non-zero value at AVAIL), make sure that all
OSDs have their Used (%) value well below the nearfull_ratio of default 85%.
This way you can reduce the risk from the upcoming rebalancing, which may cause OSDs to run full
and thereby blocking I/O on Ceph pools.
Use the following command to get the same information on the CLI:

ceph osd df tree
2. If the to-be destroyed OSD is not out yet, select the OSD and click on Out. This will exclude it from
data distribution and start a rebalance.
The following command does the same:

ceph osd out <id>
3. If you can, wait until Ceph has finished the rebalance to always have enough replicas. The OSD will
be empty; once it is, it will show 0 PGs.
4. Click on Stop. If stopping is not safe yet, a warning will appear, and you should click on Cancel. Try it
again in a few moments.
The following commands can be used to check if it is safe to stop and stop the OSD:

ceph osd ok-to-stop <id>

```
pveceph stop --service osd.<id>
```

5. Finally:
To remove the OSD from Ceph and delete all disk data, first click on More → Destroy. Enable
the cleanup option to clean up the partition table and other structures. This makes it possible to
immediately reuse the disk in Proxmox VE. Then, click on Remove.
The CLI command to destroy the OSD is:


```
pveceph osd destroy <id> [--cleanup]
```


## 8.8 Ceph Configuration


Ceph daemon and clients pull their configuration from one or more sources 5 . In Proxmox VE, a minimal
ceph.conf file is used to hold bootstrap settings. Most of the configuration is held in the central configuration
database maintained by the MON services.
5 Ceph config sources https://docs.ceph.com/en/latest/rados/configuration/ceph-conf/#config-sources


To persistently change configuration values use the following commands 6 :

ceph config dump
ceph config get <who> <name>
ceph config set <who> <name>
<value>
ceph config rm <who> <name>

Show all configuration option(s)
Show configuration option(s) for an entity
Set a configuration option for one or more entities
Clear a configuration option for one or more
entities

Example for increasing the osd_memory_target for all OSD daemons

ceph config set osd osd_memory_target 8G

> **Note:**
> If an option exists in a local configuration file, the configuration in the MON DB will be ignored because it
> has a lower precedence.


## 8.9 Ceph Pools


A pool is a logical group for storing objects. It holds a collection of objects, known as Placement Groups (PG,
pg_num).
6 Ceph MON DB commands https://docs.ceph.com/en/latest/rados/configuration/ceph-conf/#commands
