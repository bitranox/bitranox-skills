# CephFS

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

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


Multiple metadata servers can be created in a cluster, but with the default settings, only one can be active at
a time. If an MDS or its node becomes unresponsive (or crashes), another standby MDS will get promoted
to active. You can speed up the handover between the active and standby MDS by using the hotstandby
parameter option on creation, or if you have already created it you may set/add:

mds standby replay = true
in the respective MDS section of /etc/pve/ceph.conf. With this enabled, the specified MDS will
remain in a warm state, polling the active one, so that it can take over faster in case of any issues.

> **Note:**
> This active polling will have an additional performance impact on your system and the active MDS.


Multiple Active MDS
Since Luminous (12.2.x) you can have multiple active metadata servers running at once, but this is normally
only useful if you have a high amount of clients running in parallel. Otherwise the MDS is rarely the bottleneck
in a system. If you want to set this up, please refer to the Ceph documentation. 14


### 8.12.2 Create CephFS


With Proxmox VE’s integration of CephFS, you can easily create a CephFS using the web interface, CLI or
an external API interface. Some prerequisites are required for this to work:

P REREQUISITES FOR A SUCCESSFUL C EPH FS SETUP :
- Install Ceph packages - if this was already done some time ago, you may want to rerun it on an up-to-date
system to ensure that all CephFS related packages get installed.

- Setup Monitors
- Setup your OSDs
- Setup at least one MDS
After this is complete, you can simply create a CephFS through either the Web GUI’s Node -> CephFS
panel or the command-line tool pveceph, for example:


```
pveceph fs create --pg_num 128 --add-storage
```

This creates a CephFS named cephfs, using a pool for its data named cephfs_data with 128 placement
groups and a pool for its metadata named cephfs_metadata with one quarter of the data pool’s placement
groups (32). Check the Proxmox VE managed Ceph pool chapter or visit the Ceph documentation for more
information regarding an appropriate placement group number (pg_num) for your setup 8 . Additionally, the
- `--add-storage` parameter will add the CephFS to the Proxmox VE storage configuration after it has been
created successfully.
14 Configuring multiple active MDS daemons https://docs.ceph.com/en/squid/cephfs/multimds/


### 8.12.3 Destroy CephFS


> **Warning:**
> Destroying a CephFS will render all of its data unusable. This cannot be undone!


To completely and gracefully remove a CephFS, the following steps are necessary:

- Disconnect every non-Proxmox VE client (e.g. unmount the CephFS in guests).
- Disable all related CephFS Proxmox VE storage entries (to prevent it from being automatically mounted).
- Remove all used resources from guests (e.g. ISOs) that are on the CephFS you want to destroy.
- Unmount the CephFS storages on all cluster nodes manually with
umount /mnt/pve/<STORAGE-NAME>
Where <STORAGE-NAME> is the name of the CephFS storage in your Proxmox VE.

- Now make sure that no metadata server (MDS) is running for that CephFS, either by stopping or destroying
them. This can be done through the web interface or via the command-line interface, for the latter you
would issue the following command:


```
pveceph stop --service mds.NAME
```

to stop them, or


```
pveceph mds destroy NAME
```

to destroy them.
Note that standby servers will automatically be promoted to active when an active MDS is stopped or
removed, so it is best to first stop all standby servers.

- Now you can destroy the CephFS with

```
pveceph fs destroy NAME --remove-storages --remove-pools
```

This will automatically destroy the underlying Ceph pools as well as remove the storages from pve config.
After these steps, the CephFS should be completely removed and if you have other CephFS instances, the
stopped metadata servers can be started again to act as standbys.


## 8.13 Ceph Maintenance


### 8.13.1 Replace OSDs


With the following steps you can replace the disk of an OSD, which is one of the most common maintenance tasks in Ceph. If there is a problem with an OSD while its disk still seems to be healthy, read the
troubleshooting section first.


1. If the disk failed, get a recommended replacement disk of the same type and size.
2. Destroy the OSD in question.
3. Detach the old disk from the server and attach the new one.
4. Create the OSD again.
5. After automatic rebalancing, the cluster status should switch back to HEALTH_OK. Any still listed
crashes can be acknowledged by running the following command:

ceph crash archive-all


### 8.13.2 Trim/Discard


It is good practice to run fstrim (discard) regularly on VMs and containers. This releases data blocks that the
filesystem isn’t using anymore. It reduces data usage and resource load. Most modern operating systems
issue such discard commands to their disks regularly. You only need to ensure that the Virtual Machines
enable the disk discard option.


### 8.13.3 Scrub & Deep Scrub


Ceph ensures data integrity by scrubbing placement groups. Ceph checks every object in a PG for its health.
There are two forms of Scrubbing, daily cheap metadata checks and weekly deep data checks. The weekly
deep scrub reads the objects and uses checksums to ensure data integrity. If a running scrub interferes with
business (performance) needs, you can adjust the time when scrubs 15 are executed.


### 8.13.4 Shutdown Proxmox VE + Ceph HCI Cluster


To shut down the whole Proxmox VE + Ceph cluster, first stop all Ceph clients. These will mainly be VMs
and containers. If you have additional clients that might access a Ceph FS or an installed RADOS GW, stop
these as well. Highly available guests will switch their state to stopped when powered down via the Proxmox
VE tooling.
Once all clients, VMs and containers are off or not accessing the Ceph cluster anymore, verify that the Ceph
cluster is in a healthy state. Either via the Web UI or the CLI:

ceph -s
In order to not cause any recovery during the shut down and later power on phases, enable the noout OSD
flag. Either in the Ceph → OSD panel behind the Manage Global Flags button or the CLI:

ceph osd set noout
Start powering down your nodes without a monitor (MON). After these nodes are down, continue by shutting
down nodes with monitors on them.
When powering on the cluster, start the nodes with monitors (MONs) first. Once all nodes are up and
running, confirm that all Ceph services are up and running. In the end, the only warning you should see for
Ceph is that the noout flag is still set. You can disable it via the web UI or via the CLI:
15 Ceph scrubbing https://docs.ceph.com/en/squid/rados/configuration/osd-config-ref/#scrubbing

## See also

- [CephFS Storage Backend](../ch07-storage/cephfs.md)

