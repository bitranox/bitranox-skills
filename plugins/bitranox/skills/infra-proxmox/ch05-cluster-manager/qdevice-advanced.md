# QDevice, SSH and Advanced Cluster Topics

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 5.10 Corosync External Vote Support


This section describes a way to deploy an external voter in a Proxmox VE cluster. When configured, the
cluster can sustain more node failures without violating safety properties of the cluster communication.
For this to work, there are two services involved:

- A QDevice daemon which runs on each Proxmox VE node
- An external vote daemon which runs on an independent server
As a result, you can achieve higher availability, even in smaller setups (for example 2+1 nodes).


### 5.10.1 QDevice Technical Overview


The Corosync Quorum Device (QDevice) is a daemon which runs on each cluster node. It provides a
configured number of votes to the cluster’s quorum subsystem, based on an externally running third-party
arbitrator’s decision. Its primary use is to allow a cluster to sustain more node failures than standard quorum
rules allow. This can be done safely as the external device can see all nodes and thus choose only one set
of nodes to give its vote. This will only be done if said set of nodes can have quorum (again) after receiving
the third-party vote.
Currently, only QDevice Net is supported as a third-party arbitrator. This is a daemon which provides a vote
to a cluster partition, if it can reach the partition members over the network. It will only give votes to one
partition of a cluster at any time. It’s designed to support multiple clusters and is almost configuration and
state free. New clusters are handled dynamically and no configuration file is needed on the host running a
QDevice.
The only requirements for the external host are that it needs network access to the cluster and to have a
corosync-qnetd package available. We provide a package for Debian based hosts, and other Linux distributions should also have a package available through their respective package manager.

> **Note:**
> Unlike corosync itself, a QDevice connects to the cluster over TCP/IP. The daemon can also run outside
> the LAN of the cluster and isn’t limited to the low latencies requirements of corosync.


### 5.10.2 Supported Setups


We support QDevices for clusters with an even number of nodes and recommend it for 2 node clusters, if
they should provide higher availability. For clusters with an odd node count, we currently discourage the use
of QDevices. The reason for this is the difference in the votes which the QDevice provides for each cluster
type. Even numbered clusters get a single additional vote, which only increases availability, because if the
QDevice itself fails, you are in the same position as with no QDevice at all.
On the other hand, with an odd numbered cluster size, the QDevice provides (N-1) votes — where N corresponds to the cluster node count. This alternative behavior makes sense; if it had only one additional vote,
the cluster could get into a split-brain situation. This algorithm allows for all nodes but one (and naturally the
QDevice itself) to fail. However, there are two drawbacks to this:


- If the QNet daemon itself fails, no other node may fail or the cluster immediately loses quorum. For
example, in a cluster with 15 nodes, 7 could fail before the cluster becomes inquorate. But, if a QDevice is
configured here and it itself fails, no single node of the 15 may fail. The QDevice acts almost as a single
point of failure in this case.

- The fact that all but one node plus QDevice may fail sounds promising at first, but this may result in a mass
recovery of HA services, which could overload the single remaining node. Furthermore, a Ceph server will
stop providing services if only ((N-1)/2) nodes or less remain online.
If you understand the drawbacks and implications, you can decide yourself if you want to use this technology
in an odd numbered cluster setup.


### 5.10.3 QDevice-Net Setup


We recommend running any daemon which provides votes to corosync-qdevice as an unprivileged user.
Proxmox VE and Debian provide a package which is already configured to do so. The traffic between
the daemon and the cluster must be encrypted to ensure a safe and secure integration of the QDevice in
Proxmox VE.
First, install the corosync-qnetd package on your external server

external# apt install corosync-qnetd
and the corosync-qdevice package on all cluster nodes

pve# apt install corosync-qdevice
After doing this, ensure that all the nodes in the cluster are online.
You can now set up your QDevice by running the following command on one of the Proxmox VE nodes:

pve# pvecm qdevice setup <QDEVICE-IP>
The SSH key from the cluster will be automatically copied to the QDevice.

> **Note:**
> Make sure to setup key-based access for the root user on your external server, or temporarily allow root
> login with password during the setup phase. If you receive an error such as Host key verification failed. at
> this stage, running pvecm updatecerts could fix the issue.


After all the steps have successfully completed, you will see "Done". You can verify that the QDevice has
been set up with:

pve# pvecm status
...
Votequorum information
~~~~~~~~~~~~~~~~~~~~~
Expected votes:
3
Highest expected: 3
Total votes:
3

Quorum:
Flags:


2
Quorate Qdevice

Membership information
~~~~~~~~~~~~~~~~~~~~~~
Nodeid
Votes
0x00000001
1
0x00000002
1
0x00000000
1

Qdevice Name
A,V,NMW 192.168.22.180 (local)
A,V,NMW 192.168.22.181
Qdevice

QDevice Status Flags
The status output of the QDevice, as seen above, will usually contain three columns:

- A / NA: Alive or Not Alive. Indicates if the communication to the external corosync-qnetd daemon
works.

- V / NV: If the QDevice will cast a vote for the node. In a split-brain situation, where the corosync connection
between the nodes is down, but they both can still communicate with the external corosync-qnetd
daemon, only one node will get the vote.

- MW / NMW: Master wins (MV) or not (NMW). Default is NMW, see 1 .
- NR: QDevice is not registered.

> **Note:**
> If your QDevice is listed as Not Alive (NA in the output above), ensure that port 5403 (the default port
> of the qnetd server) of your external server is reachable via TCP/IP!


### 5.10.4 Frequently Asked Questions


Tie Breaking
In case of a tie, where two same-sized cluster partitions cannot see each other but can see the QDevice, the
QDevice chooses one of those partitions randomly and provides a vote to it.
Possible Negative Implications
For clusters with an even node count, there are no negative implications when using a QDevice. If it fails to
work, it is the same as not having a QDevice at all.
Adding/Deleting Nodes After QDevice Setup
If you want to add a new node or remove an existing one from a cluster with a QDevice setup, you need to
remove the QDevice first. After that, you can add or remove nodes normally. Once you have a cluster with
an even node count again, you can set up the QDevice again as described previously.
1 votequorum_qdevice_master_wins

votequorum_qdevice_master_wins.3.en.html

manual

page

https://manpages.debian.org/stable/libvotequorum-dev/-


Removing the QDevice
If you used the official pvecm tool to add the QDevice, you can remove it by running:

pve# pvecm qdevice remove


## 5.11 Corosync Configuration


The /etc/pve/corosync.conf file plays a central role in a Proxmox VE cluster. It controls the cluster
membership and its network. For further information about it, check the corosync.conf man page:

man corosync.conf
For node membership, you should always use the pvecm tool provided by Proxmox VE. You may have to
edit the configuration file manually for other changes. Here are a few best practice tips for doing this.


### 5.11.1 Edit corosync.conf


Editing the corosync.conf file is not always very straightforward. There are two on each cluster node, one in
/etc/pve/corosync.conf and the other in /etc/corosync/corosync.conf. Editing the one
in our cluster file system will propagate the changes to the local one, but not vice versa.
The configuration will get updated automatically, as soon as the file changes. This means that changes
which can be integrated in a running corosync will take effect immediately. Thus, you should always make a
copy and edit that instead, to avoid triggering unintended changes when saving the file while editing.

cp /etc/pve/corosync.conf /etc/pve/corosync.conf.new
Then, open the config file with your favorite editor, such as nano or vim.tiny, which come pre-installed
on every Proxmox VE node.

> **Note:**
> Always increment the config_version number after configuration changes; omitting this can lead to problems.
> After making the necessary changes, create another copy of the current working configuration file. This
> serves as a backup if the new configuration fails to apply or causes other issues.


cp /etc/pve/corosync.conf /etc/pve/corosync.conf.bak
Then replace the old configuration file with the new one:

mv /etc/pve/corosync.conf.new /etc/pve/corosync.conf
You can check if the changes could be applied automatically, using the following commands:

systemctl status corosync
journalctl -b -u corosync
If the changes could not be applied automatically, you may have to restart the corosync service via:

systemctl restart corosync
On errors, check the troubleshooting section below.


### 5.11.2 Troubleshooting


Issue: quorum.expected_votes must be configured
When corosync starts to fail and you get the following message in the system log:

[...]
corosync[1647]: [QUORUM] Quorum provider: corosync_votequorum failed to ←initialize.
corosync[1647]: [SERV ] Service engine 'corosync_quorum' failed to load ←for reason
'configuration error: nodelist or quorum.expected_votes must be ←configured!'
[...]
It means that the hostname you set for a corosync ringX_addr in the configuration could not be resolved.
Write Configuration When Not Quorate
If you need to change /etc/pve/corosync.conf on a node with no quorum, and you understand what you are
doing, use:


```
pvecm expected 1
```

This sets the expected vote count to 1 and makes the cluster quorate. You can then fix your configuration,
or revert it back to the last working backup.
This is not enough if corosync cannot start anymore. In that case, it is best to edit the local copy of the
corosync configuration in /etc/corosync/corosync.conf, so that corosync can start again. Ensure that on all
nodes, this configuration has the same content to avoid split-brain situations.


### 5.11.3 Corosync Configuration Glossary


ringX_addr
This names the different link addresses for the Kronosnet connections between nodes.


## 5.12 Cluster Cold Start


It is obvious that a cluster is not quorate when all nodes are offline. This is a common case after a power
failure.

> **Note:**
> It is always a good idea to use an uninterruptible power supply (“UPS”, also called “battery backup”) to
> avoid this state, especially if you want HA.
> On node startup, the pve-guests service is started and waits for quorum. Once quorate, it starts all
> guests which have the onboot flag set.
> When you turn on nodes, or when power comes back after power failure, it is likely that some nodes will boot
> faster than others. Please keep in mind that guest startup is delayed until you reach quorum.


## 5.13 Guest VMID Auto-Selection


When creating new guests the web interface will ask the backend for a free VMID automatically. The default
range for searching is 100 to 1000000 (lower than the maximal allowed VMID enforced by the schema).
Sometimes admins either want to allocate new VMIDs in a separate range, for example to easily separate
temporary VMs with ones that choose a VMID manually. Other times its just desired to provided a stable
length VMID, for which setting the lower boundary to, for example, 100000 gives much more room for.
To accommodate this use case one can set either lower, upper or both boundaries via the datacenter.cfg
configuration file, which can be edited in the web interface under Datacenter → Options.

> **Note:**
> The range is only used for the next-id API call, so it isn’t a hard limit.


## 5.14 Guest Migration


Migrating virtual guests to other nodes is a useful feature in a cluster. There are settings to control the
behavior of such migrations. This can be done via the configuration file datacenter.cfg or for a specific
migration via API or command-line parameters.
It makes a difference if a guest is online or offline, or if it has local resources (like a local disk).
For details about virtual machine migration, see the QEMU/KVM Migration Chapter.
For details about container migration, see the Container Migration Chapter.


### 5.14.1 Migration Type


The migration type defines if the migration data should be sent over an encrypted (secure) channel or an
unencrypted (insecure) one. Setting the migration type to insecure means that the RAM content of
a virtual guest is also transferred unencrypted, which can lead to information disclosure of critical data from
inside the guest (for example, passwords or encryption keys).
Therefore, we strongly recommend using the secure channel if you do not have full control over the network
and can not guarantee that no one is eavesdropping on it.

> **Note:**
> Storage migration does not follow this setting. Currently, it always sends the storage content over a secure
> channel.


Encryption requires a lot of computing power, so this setting is often changed to insecure to achieve
better performance. The impact on modern systems is lower because they implement AES encryption in
hardware. The performance impact is particularly evident in fast networks, where you can transfer 10 Gbps
or more.


### 5.14.2 Migration Network


By default, Proxmox VE uses the network in which cluster communication takes place to send the migration
traffic. This is not optimal both because sensitive cluster traffic can be disrupted and this network may not
have the best bandwidth available on the node.
Setting the migration network parameter allows the use of a dedicated network for all migration traffic. In
addition to the memory, this also affects the storage traffic for offline migrations.
The migration network is set as a network using CIDR notation. This has the advantage that you don’t have
to set individual IP addresses for each node. Proxmox VE can determine the real address on the destination
node from the network specified in the CIDR form. To enable this, the network must be specified so that
each node has exactly one IP in the respective network.

Example
We assume that we have a three-node setup, with three separate networks. One for public communication
with the Internet, one for cluster communication, and a very fast one, which we want to use as a dedicated
network for migration.
A network configuration for such a setup might look as follows:

iface eno1 inet manual
# public network
auto vmbr0
iface vmbr0 inet static
address 192.X.Y.57/24
gateway 192.X.Y.1
bridge-ports eno1
bridge-stp off
bridge-fd 0
# cluster network
auto eno2
iface eno2 inet static
address 10.1.1.1/24
# fast network
auto eno3
iface eno3 inet static
address 10.1.2.1/24
Here, we will use the network 10.1.2.0/24 as a migration network. For a single migration, you can do this
using the migration_network parameter of the command-line tool:


```
# qm migrate 106 tre --online --migration_network 10.1.2.0/24
To configure this as the default network for all migrations in the cluster, set the migration property of the
```


/etc/pve/datacenter.cfg file:
# use dedicated migration network
migration: secure,network=10.1.2.0/24


> **Note:**
> The migration


type

must

always
/etc/pve/datacenter.cfg.


be

set

when

the

migration

network

is

set

in


## See also

- [Cluster Manager Overview](_index.md)
- [Remove and Rejoin Nodes](remove-rejoin.md)
- [Cluster Network](cluster-network.md)
- [Proxmox Cluster File System](../ch06-pmxcfs.md)
- [High Availability](../ch15-high-availability/_index.md)
- [pvecm CLI Reference](../appendix-a-cli/pvecm.md)
