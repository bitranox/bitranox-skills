# Cluster: Remove and Rejoin Nodes

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 5.5 Remove a Cluster Node


> **Caution:**
> Read the procedure carefully before proceeding, as it may not be what you want or need.


Move all virtual machines from the node. Ensure that you have made copies of any local data or backups
that you want to keep. In addition, make sure to remove any scheduled replication jobs to the node to be
removed.

> **Caution:**
> Failure to remove replication jobs to a node before removing said node will result in the replication
> job becoming irremovable. Especially note that replication automatically switches direction if a
> replicated VM is migrated, so by migrating a replicated VM from a node to be deleted, replication
> jobs will be set up to that node automatically.


If the node to be removed has been configured for Ceph:
1. Ensure that sufficient Proxmox VE nodes with running OSDs (up and in) continue to exist.

> **Note:**
> By default, Ceph pools have a size/min_size of 3/2 and a full node as failure domain
> at the object balancer CRUSH. So if less than size (3) nodes with running OSDs are online, data
> redundancy will be degraded. If less than min_size are online, pool I/O will be blocked and
> affected guests may crash.


2. Ensure that sufficient monitors, managers and, if using CephFS, metadata servers remain available.
3. To maintain data redundancy, each destruction of an OSD, especially the last one on a node, will
trigger a data rebalance. Therefore, ensure that the OSDs on the remaining nodes have sufficient free
space left.
4. To remove Ceph from the node to be deleted, start by destroying its OSDs, one after the other.
5. Once the CEPH status is HEALTH_OK again, proceed by:
1. destroying its metadata server via web interface at Ceph → CephFS or by running:


```
# pveceph mds destroy <local hostname>
2. destroying its monitor
3. destroying its manager
6. Finally, remove the now empty bucket (Proxmox VE node to be removed) from the CRUSH hierarchy
by running:

# ceph osd crush remove <hostname>
```


In the following example, we will remove the node hp4 from the cluster.
Log in to a different cluster node (not hp4), and issue a pvecm nodes command to identify the node ID
to remove:

hp1# pvecm nodes
Membership information
~~~~~~~~~~~~~~~~~~~~~~
Nodeid
Votes Name
1
1 hp1 (local)
2
1 hp2
3
1 hp3
4
1 hp4
At this point, you must power off hp4 and ensure that it will not power on again (in the network) with its
current configuration.


> **Important:**
> As mentioned above, it is critical to power off the node before removal, and make sure that it will
> not power on again (in the existing cluster network) with its current configuration. If you power on
> the node as it is, the cluster could end up broken, and it could be difficult to restore it to a functioning
> state.


After powering off the node hp4, we can safely remove it from the cluster.

hp1# pvecm delnode hp4
Killing node 4


> **Note:**
> At this point, it is possible that you will receive an error message stating Could not kill node
> (error = CS_ERR_NOT_EXIST). This does not signify an actual failure in the deletion of the node,
> but rather a failure in corosync trying to kill an offline node. Thus, it can be safely ignored.


Use pvecm nodes or pvecm status to check the node list again. It should look something like:

hp1# pvecm status
...
Votequorum information
~~~~~~~~~~~~~~~~~~~~~~
Expected votes:
3
Highest expected: 3
Total votes:
3
Quorum:
2
Flags:
Quorate
Membership information
~~~~~~~~~~~~~~~~~~~~~~
Nodeid
Votes Name
0x00000001
1 192.168.15.90 (local)
0x00000002
1 192.168.15.91
0x00000003
1 192.168.15.92
If, for whatever reason, you want this server to join the same cluster again, you have to:

- do a fresh install of Proxmox VE on it,
- then join it, as explained in the previous section.
The configuration files for the removed node will still reside in /etc/pve/nodes/hp4. Recover any configuration
you still need and remove the directory afterwards.

> **Note:**
> After removal of the node, its SSH fingerprint will still reside in the known_hosts of the other nodes. If you
> receive an SSH error after rejoining a node with the same IP or hostname, run pvecm updatecerts
> once on the re-added node to update its fingerprint cluster wide.


### 5.5.1 Separate a Node Without Reinstalling


> **Caution:**
> This is not the recommended method, proceed with caution. Use the previous method if you’re
> unsure.


You can also separate a node from a cluster without reinstalling it from scratch. But after removing the
node from the cluster, it will still have access to any shared storage. This must be resolved before you start
removing the node from the cluster. A Proxmox VE cluster cannot share the exact same storage with another
cluster, as storage locking doesn’t work over the cluster boundary. Furthermore, it may also lead to VMID
conflicts.
It’s suggested that you create a new storage, where only the node which you want to separate has access.
This can be a new export on your NFS or a new Ceph pool, to name a few examples. It’s just important that
the exact same storage does not get accessed by multiple clusters. After setting up this storage, move all
data and VMs from the node to it. Then you are ready to separate the node from the cluster.


> **Warning:**
> Ensure that all shared resources are cleanly separated! Otherwise you will run into conflicts and
> problems.


First, stop the corosync and pve-cluster services on the node:

systemctl stop pve-cluster
systemctl stop corosync
Start the cluster file system again in local mode:

pmxcfs -l
Delete the corosync configuration files:

rm /etc/pve/corosync.conf
rm -r /etc/corosync/*
You can now start the file system again as a normal service:

killall pmxcfs
systemctl start pve-cluster
The node is now separated from the cluster. You can deleted it from any remaining node of the cluster with:


```
pvecm delnode oldnode
```

If the command fails due to a loss of quorum in the remaining node, you can set the expected votes to 1 as
a workaround:


```
pvecm expected 1
```


And then repeat the pvecm delnode command.
Now switch back to the separated node and delete all the remaining cluster files on it. This ensures that the
node can be added to another cluster again without problems.

rm /var/lib/corosync/*
As the configuration files from the other nodes are still in the cluster file system, you may want to clean those
up too. After making absolutely sure that you have the correct node name, you can simply remove the entire
directory recursively from /etc/pve/nodes/NODENAME.

> **Caution:**
> The node’s SSH keys will remain in the authorized_key file. This means that the nodes can still
> connect to each other with public key authentication. You should fix this by removing the respective
> keys from the /etc/pve/priv/authorized_keys file.


## 5.6 Quorum


Proxmox VE use a quorum-based technique to provide a consistent state among all cluster nodes.
A quorum is the minimum number of votes that a distributed transaction has to obtain in order
to be allowed to perform an operation in a distributed system.
— from Wikipedia Quorum (distributed computing)
In case of network partitioning, state changes requires that a majority of nodes are online. The cluster
switches to read-only mode if it loses quorum.

> **Note:**
> Proxmox VE assigns a single vote to each node by default.


## See also

- [Cluster Manager Overview](_index.md)
- [Cluster Network](cluster-network.md)
- [QDevice and Advanced Topics](qdevice-advanced.md)
