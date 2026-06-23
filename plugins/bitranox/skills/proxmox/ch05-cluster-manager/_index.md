# Cluster Manager

*[Main Index](../SKILL.md)*


The Proxmox VE cluster manager pvecm is a tool to create a group of physical servers. Such a group is
called a cluster. We use the Corosync Cluster Engine for reliable group communication. There’s no explicit
limit for the number of nodes in a cluster. In practice, the actual possible node count may be limited by the
host and network performance. Currently (2021), there are reports of clusters (using high-end enterprise
hardware) with over 50 nodes in production.


`pvecm` can be used to create a new cluster, join nodes to a cluster, leave the cluster, get status information, and do various other cluster-related tasks. The Proxmox Cluster File System ("pmxcfs") is used to transparently distribute the cluster configuration to all cluster nodes.
Grouping nodes into a cluster has the following advantages:

- Centralized, web-based management
- Multi-master clusters: each node can do all management tasks
- Use of pmxcfs, a database-driven file system, for storing configuration files, replicated in real-time on all
nodes using corosync
- Easy migration of virtual machines and containers between physical hosts
- Fast deployment
- Cluster-wide services like firewall and HA


## 5.1 Requirements


- All nodes must be able to connect to each other via UDP ports 5405-5412 for corosync to work.
- Date and time must be synchronized.
- An SSH tunnel on TCP port 22 between nodes is required.
- If you are interested in High Availability, you need to have at least three nodes for reliable quorum. All
nodes should have the same version.


> **Note:**
> For smaller 2-node clusters, the QDevice can be used to provide a 3rd vote.


- We recommend a dedicated physical NIC for the cluster traffic.

> **Note:**
> The Proxmox VE cluster communication uses the Corosync protocol. It needs consistent low latency but
> not a lot of bandwidth. A dedicated 1 Gbit NIC is enough in most situations. It helps to avoid situations
> where other services can use up all the available bandwidth. Which in turn would increase the latency
> for the Corosync packets.


- Additional links for cluster traffic offers redundancy in case the dedicated network is down.

> **Note:**
> Corosync supports up to 8 links.


> **Note:**
> To ensure reliable Corosync redundancy, it is essential to have at least another link on a different physical
> network. This enables Corosync to keep the cluster communication alive should the dedicated network
> be down.


> **Note:**
> A single link backed by a bond can be problematic in certain failure scenarios, see Corosync Over
> Bonds.


- The root password of a cluster node is required for adding nodes.
- Online migration of virtual machines is only supported when nodes have CPUs from the same vendor. It
might work otherwise, but this is never guaranteed.


## 5.2 Preparing Nodes


First, install Proxmox VE on all nodes. Make sure that each node is installed with the final hostname and IP
configuration. Changing the hostname and IP is not possible after cluster creation.
While it’s common to reference all node names and their IPs in /etc/hosts (or make their names resolvable through other means), this is not necessary for a cluster to work. It may be useful however, as you can
then connect from one node to another via SSH, using the easier to remember node name (see also Link
Address Types). Note that we always recommend referencing nodes by their IP addresses in the cluster
configuration.


## 5.3 Create a Cluster


You can either create a cluster on the console (login via ssh), or through the API using the Proxmox VE web
interface (Datacenter → Cluster ).

> **Note:**
> Use a unique name for your cluster. This name cannot be changed later. The cluster name follows the
> same rules as node names.


### 5.3.1 Create via Web GUI


Under Datacenter → Cluster, click on Create Cluster. Enter the cluster name and select a network connection from the drop-down list to serve as the main cluster network (Link 0). It defaults to the IP resolved via
the node’s hostname.
As of Proxmox VE 6.2, up to 8 fallback links can be added to a cluster. To add a redundant link, click the Add
button and select a link number and IP address from the respective fields. Prior to Proxmox VE 6.2, to add a
second link as fallback, you can select the Advanced checkbox and choose an additional network interface
(Link 1, see also Corosync Redundancy).

> **Note:**
> Ensure that the network selected for cluster communication is not used for any high traffic purposes, like
> network storage or live-migration. While the cluster network itself produces small amounts of data, it is
> very sensitive to latency. Check out full cluster network requirements.


### 5.3.2 Create via the Command Line


Login via ssh to the first Proxmox VE node and run the following command:

hp1# pvecm create CLUSTERNAME
To check the state of the new cluster use:

hp1# pvecm status


### 5.3.3 Multiple Clusters in the Same Network


It is possible to create multiple clusters in the same physical or logical network. In this case, each cluster
must have a unique name to avoid possible clashes in the cluster communication stack. Furthermore, this
helps avoid human confusion by making clusters clearly distinguishable.


While the bandwidth requirement of a corosync cluster is relatively low, the latency of packets and the
packets per second (PPS) rate is the limiting factor. Different clusters in the same network can compete with
each other for these resources, so it may still make sense to use separate physical network infrastructure for
bigger clusters.


## 5.4 Adding Nodes to the Cluster


> **Caution:**
> All existing configuration in /etc/pve is overwritten when joining a cluster. In particular, a joining
> node cannot hold any guests, since guest IDs could otherwise conflict, and the node will inherit the
> cluster’s storage configuration. To join a node with existing guest, as a workaround, you can create
> a backup of each guest (using vzdump) and restore it under a different ID after joining. If the
> node’s storage layout differs, you will need to re-add the node’s storages, and adapt each storage’s
> node restriction to reflect on which nodes the storage is actually available.


### 5.4.1 Join Node to Cluster via GUI


Log in to the web interface on an existing cluster node. Under Datacenter → Cluster, click the Join Information button at the top. Then, click on the button Copy Information. Alternatively, copy the string from the
Information field manually.

Next, log in to the web interface on the node you want to add. Under Datacenter → Cluster, click on Join
Cluster. Fill in the Information field with the Join Information text you copied earlier. Most settings required
for joining the cluster will be filled out automatically. For security reasons, the cluster password has to be
entered manually.

> **Note:**
> To enter all required data manually, you can disable the Assisted Join checkbox.


After clicking the Join button, the cluster join process will start immediately. After the node has joined the
cluster, its current node certificate will be replaced by one signed from the cluster certificate authority (CA).
This means that the current session will stop working after a few seconds. You then might need to forcereload the web interface and log in again with the cluster credentials.
Now your node should be visible under Datacenter → Cluster.


### 5.4.2 Join Node to Cluster via Command Line


Log in to the node you want to join into an existing cluster via ssh.


```
# pvecm add IP-ADDRESS-CLUSTER
For IP-ADDRESS-CLUSTER, use the IP or hostname of an existing cluster node. An IP address is recommended (see Link Address Types).
To check the state of the cluster use:

# pvecm status
```


Cluster status after adding 4 nodes


```
# pvecm status
Cluster information
~~~~~~~~~~~~~~~~~~~
Name:
prod-central
Config Version:
3
Transport:
knet
Secure auth:
on
Quorum information
~~~~~~~~~~~~~~~~~~
Date:
Tue Sep 14 11:06:47 2021
Quorum provider: corosync_votequorum
Nodes:
4
Node ID:
0x00000001
Ring ID:
1.1a8
Quorate:
Yes
Votequorum information
~~~~~~~~~~~~~~~~~~~~~~
Expected votes:
4
Highest expected: 4
Total votes:
4
Quorum:
3
Flags:
Quorate
Membership information
~~~~~~~~~~~~~~~~~~~~~~
Nodeid
Votes Name
0x00000001
1 192.168.15.91
0x00000002
1 192.168.15.92 (local)
```


0x00000003
0x00000004


1 192.168.15.93
1 192.168.15.94

If you only want a list of all nodes, use:


```
# pvecm nodes
```


List nodes in a cluster


```
# pvecm nodes
Membership information
~~~~~~~~~~~~~~~~~~~~~~
Nodeid
Votes Name
1
1 hp1
2
1 hp2 (local)
3
1 hp3
4
1 hp4
```


### 5.4.3 Adding Nodes with Separated Cluster Network


When adding a node to a cluster with a separated cluster network, you need to use the link0 parameter to
set the nodes address on that network:


```
# pvecm add IP-ADDRESS-CLUSTER --link0 LOCAL-IP-ADDRESS-LINK0
If you want to use the built-in redundancy of the Kronosnet transport layer, also use the link1 parameter.
Using the GUI, you can select the correct interface from the corresponding Link X fields in the Cluster Join
dialog.
```


## See also

- [Remove and Rejoin Nodes](remove-rejoin.md)
- [Cluster Network](cluster-network.md)
- [QDevice and Advanced Topics](qdevice-advanced.md)
- [Proxmox Cluster File System](../ch06-pmxcfs.md)
- [High Availability](../ch15-high-availability/_index.md)
- [pvecm CLI Reference](../appendix-a-cli/pvecm.md)
