# Cluster Network

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 5.7 Cluster Network


The cluster network is the core of a cluster. All messages sent over it have to be delivered reliably to all
nodes in their respective order. In Proxmox VE this part is done by corosync, an implementation of a high
performance, low overhead, high availability development toolkit. It serves our decentralized configuration
file system (pmxcfs).


### 5.7.1 Network Requirements


The Proxmox VE cluster stack requires a reliable network with latencies under 5 milliseconds (LAN performance) between all nodes to operate stably. While on setups with a small node count a network with higher
latencies may work, this is not guaranteed and gets rather unlikely with more than three nodes and latencies
above around 10 ms.


The network should not be used heavily by other members, as while corosync does not uses much bandwidth
it is sensitive to latency jitters; ideally corosync runs on its own physically separated network. Especially do
not use a shared network for corosync and storage (except as a potential low-priority fallback in a redundant
configuration).
Before setting up a cluster, it is good practice to check if the network is fit for that purpose. To ensure that
the nodes can connect to each other on the cluster network, you can test the connectivity between them with
the ping tool.
If the Proxmox VE firewall is enabled, ACCEPT rules for corosync will automatically be generated - no manual
action is required.

> **Note:**
> Corosync used Multicast before version 3.0 (introduced in Proxmox VE 6.0). Modern versions rely on
> Kronosnet for cluster communication, which, for now, only supports regular UDP unicast.


> **Caution:**
> You can still enable Multicast or legacy unicast by setting your transport to udp or udpu in your
> corosync.conf, but keep in mind that this will disable all cryptography and redundancy support. This
> is therefore not recommended.


### 5.7.2 Corosync Over Bonds


Recommendations
We recommend at least one dedicated physical NIC for the primary Corosync link, see Requirements. Bonds
may be used as additional links for increased redundancy. The following caveats apply whenever a bond is
used for Corosync traffic:

- Bond mode active-backup may not provide the expected redundancy in certain failure scenarios, see
below for details.

- We advise against using bond modes balance-rr, balance-xor, balance-tlb, or balance-alb for Corosync
traffic. They are known to be problematic in certain failure scenarios, see below for details.

- IEEE 802.3ad (LACP): If LACP bonds are used for corosync traffic, we strongly recommend setting
bond-lacp-rate fast on the Proxmox VE node and the switch! With the default setting bond-lacp-ra
slow, this mode is known to be problematic in certain failure scenarios, see below for details.
Background
Using a bond as a Corosync link can be problematic in certain failure scenarios. Consider the failure scenario
where one of the bonded interfaces fails and stops transmitting packets, but its link state stays up, and there
are no other Corosync links available. In this scenario, some bond modes may cause a state of asymmetric
connectivity where cluster nodes can only communicate with different subsets of other nodes. Affected are
bond modes that provide load balancing, as these modes may still try to send out a subset of packets via the
failed interface. In case of asymmetric connectivity, Corosync may not be able to form a stable quorum in


the cluster. If this state persists and HA is enabled, even nodes whose bond does not have any issues may
fence themselves. In the worst case, the whole cluster may fence itself.
The bond mode active-backup will not cause asymmetric connectivity in the failure scenario described
above. However, the bond with the interface failure may not switch over to the backup link. The node may
lose connection to the cluster and, if HA is enabled, fence itself.
Bond modes balance-rr, balance-xor, balance_tlb, or balance-alb may cause asymmetric connectivity in
the failure scenario above, which can lead to unexpected fencing if HA is enabled.
Bond mode IEEE 802.3ad (LACP) can cause asymmetric connectivity in the failure scenario above, but it
can recover from this state, as each side of the bond (Proxmox VE node and switch) can stop using a bonded
interface if it has not received three LACPDUs in a row on it. However, with default settings, LACPDUs are
only sent every 30 seconds, yielding a failover time of 90 seconds. This is too long, as nodes with HA
resources will fence themselves already after roughly one minute without a stable quorum. If LACP bonds
are used for corosync traffic, we recommend setting bond-lacp-rate fast on the Proxmox VE node
and the switch! Setting this option on one side requests the other side to send an LACPDU every second.
Setting this option on both sides can reduce the failover time in the scenario above to 3 seconds and thus
prevent fencing.


### 5.7.3 Separate Cluster Network


When creating a cluster without any parameters, the corosync cluster network is generally shared with the
web interface and the VMs’ network. Depending on your setup, even storage traffic may get sent over the
same network. It’s recommended to change that, as corosync is a time-critical, real-time application.
Setting Up a New Network
First, you have to set up a new network interface. It should be on a physically separate network. Ensure that
your network fulfills the cluster network requirements.
Separate On Cluster Creation
This is possible via the linkX parameters of the pvecm create command, used for creating a new cluster.
If you have set up an additional NIC with a static address on 10.10.10.1/25, and want to send and receive all
cluster communication over this interface, you would execute:


```
pvecm create test --link0 10.10.10.1
```

To check if everything is working properly, execute:

systemctl status corosync
Afterwards, proceed as described above to add nodes with a separated cluster network.
Separate After Cluster Creation
You can do this if you have already created a cluster and want to switch its communication to another network,
without rebuilding the whole cluster. This change may lead to short periods of quorum loss in the cluster, as
nodes have to restart corosync and come up one after the other on the new network.
Check how to edit the corosync.conf file first. Then, open it and you should see a file similar to:


logging {
debug: off
to_syslog: yes
}
nodelist {
node {
name: due
nodeid: 2
quorum_votes: 1
ring0_addr: due
}
node {
name: tre
nodeid: 3
quorum_votes: 1
ring0_addr: tre
}
node {
name: uno
nodeid: 1
quorum_votes: 1
ring0_addr: uno
}
}
quorum {
provider: corosync_votequorum
}
totem {
cluster_name: testcluster
config_version: 3
ip_version: ipv4-6
secauth: on
version: 2
interface {
linknumber: 0
}
}


> **Note:**


ringX_addr actually specifies a corosync link address. The name "ring" is a remnant of older corosync
versions that is kept for backwards compatibility.


The first thing you want to do is add the name properties in the node entries, if you do not see them already.
Those must match the node name.
Then replace all addresses from the ring0_addr properties of all nodes with the new addresses. You may
use plain IP addresses or hostnames here. If you use hostnames, ensure that they are resolvable from all
nodes (see also Link Address Types).
In this example, we want to switch cluster communication to the 10.10.10.0/25 network, so we change the
ring0_addr of each node respectively.

> **Note:**
> The exact same procedure can be used to change other ringX_addr values as well. However, we recommend only changing one link address at a time, so that it’s easier to recover if something goes wrong.


After we increase the config_version property, the new configuration file should look like:

logging {
debug: off
to_syslog: yes
}
nodelist {
node {
name: due
nodeid: 2
quorum_votes: 1
ring0_addr: 10.10.10.2
}
node {
name: tre
nodeid: 3
quorum_votes: 1
ring0_addr: 10.10.10.3
}
node {
name: uno
nodeid: 1
quorum_votes: 1
ring0_addr: 10.10.10.1
}
}
quorum {
provider: corosync_votequorum
}
totem {
cluster_name: testcluster


config_version: 4
ip_version: ipv4-6
secauth: on
version: 2
interface {
linknumber: 0
}
}
Then, after a final check to see that all changed information is correct, we save it and once again follow the
edit corosync.conf file section to bring it into effect.
The changes will be applied live, so restarting corosync is not strictly necessary. If you changed other
settings as well, or notice corosync complaining, you can optionally trigger a restart.
On a single node execute:

systemctl restart corosync
Now check if everything is okay:

systemctl status corosync
If corosync begins to work again, restart it on all other nodes too. They will then join the cluster membership
one by one on the new network.


### 5.7.4 Corosync Addresses


A corosync link address (for backwards compatibility denoted by ringX_addr in corosync.conf) can be
specified in two ways:

- IPv4/v6 addresses can be used directly. They are recommended, since they are static and usually not
changed carelessly.

- Hostnames will be resolved using getaddrinfo, which means that by default, IPv6 addresses will
be used first, if available (see also man gai.conf). Keep this in mind, especially when upgrading an
existing cluster to IPv6.

> **Caution:**
> Hostnames should be used with care, since the addresses they resolve to can be changed without
> touching corosync or the node it runs on - which may lead to a situation where an address is
> changed without thinking about implications for corosync.


A separate, static hostname specifically for corosync is recommended, if hostnames are preferred. Also,
make sure that every node in the cluster can resolve all hostnames correctly.
Since Proxmox VE 5.1, while supported, hostnames will be resolved at the time of entry. Only the resolved
IP is saved to the configuration.
Nodes that joined the cluster on earlier versions likely still use their unresolved hostname in corosync.conf.
It might be a good idea to replace them with IPs or a separate hostname, as mentioned above.


## 5.8 Corosync Redundancy


Corosync supports redundant networking via its integrated Kronosnet layer by default (it is not supported on
the legacy udp/udpu transports). It can be enabled by specifying more than one link address, either via the
- `--linkX` parameters of pvecm, in the GUI as Link 1 (while creating a cluster or adding a new node) or by
specifying more than one ringX_addr in corosync.conf.

> **Note:**
> To provide useful failover, every link should be on its own physical network connection.


The following examples assume that each cluster node has one static address in 10.10.10.0/25 and one
static address in 10.20.20.0/25 configured.
Links are used according to a priority setting. You can configure this priority by setting knet_link_priority in
the corresponding interface section in corosync.conf, or, preferably, using the priority parameter when
creating your cluster with pvecm:


```
# pvecm create CLUSTERNAME --link0 10.10.10.1,priority=15 --link1
10.20.20.1,priority=20
```


←-

This would cause link1 to be used first, since it has the higher priority.
If no priorities are configured manually (or two links have the same priority), links will be used in order of their
number, with the lower number having higher priority.
Even if all links are working, only the one with the highest priority will see corosync traffic. Link priorities
cannot be mixed, meaning that links with different priorities will not be able to communicate with each other.
Since lower priority links will not see traffic unless all higher priorities have failed, it becomes a useful strategy
to specify networks used for other tasks (VMs, storage, etc.) as low-priority links. If worst comes to worst, a
higher latency or more congested connection might be better than no connection at all.


### 5.8.1 Adding Redundant Links To An Existing Cluster


To add a new link to a running configuration, first check how to edit the corosync.conf file.
Then, add a new ringX_addr to every node in the nodelist section. Make sure that your X is the same
for every node you add it to, and that it is unique for each node.
Lastly, add a new interface, as shown below, to your totem section, replacing X with the link number chosen
above.
Assuming you added a link with number 1, the new configuration file could look like this:

logging {
debug: off
to_syslog: yes
}
nodelist {
node {
name: due


nodeid: 2
quorum_votes: 1
ring0_addr: 10.10.10.2
ring1_addr: 10.20.20.2
}
node {
name: tre
nodeid: 3
quorum_votes: 1
ring0_addr: 10.10.10.3
ring1_addr: 10.20.20.3
}
node {
name: uno
nodeid: 1
quorum_votes: 1
ring0_addr: 10.10.10.1
ring1_addr: 10.20.20.1
}
}
quorum {
provider: corosync_votequorum
}
totem {
cluster_name: testcluster
config_version: 4
ip_version: ipv4-6
secauth: on
version: 2
interface {
linknumber: 0
}
interface {
linknumber: 1
}
}
The new link will be enabled as soon as you follow the last steps to edit the corosync.conf file. A restart
should not be necessary. You can check that corosync loaded the new link using:

journalctl -b -u corosync
It might be a good idea to test the new link by temporarily disconnecting the old link on one node and making
sure that its status remains online while disconnected:


```
pvecm status
```

If you see a healthy cluster state, it means that your new link is being used.


## 5.9 Role of SSH in Proxmox VE Clusters


Proxmox VE utilizes SSH tunnels for various features.

- Proxying console/shell sessions (node and guests)
When using the shell for node B while being connected to node A, connects to a terminal proxy on node
A, which is in turn connected to the login shell on node B via a non-interactive SSH tunnel.

- VM and CT memory and local-storage migration in secure mode.
During the migration, one or more SSH tunnel(s) are established between the source and target nodes, in
order to exchange migration information and transfer memory and disk contents.

- Storage replication


### 5.9.1 SSH setup


On Proxmox VE systems, the following changes are made to the SSH configuration/setup:

- the root user’s SSH client config gets setup to prefer AES over ChaCha20
- the root user’s authorized_keys file gets linked to /etc/pve/priv/authorized_keys,
merging all authorized keys within a cluster

- sshd is configured to allow logging in as root with a password

> **Note:**
> Older systems might also have /etc/ssh/ssh_known_hosts set up as symlink pointing to
> /etc/pve/priv/known_hosts, containing a merged version of all node host keys. This system
> was replaced with explicit host key pinning in pve-cluster <<INSERT VERSION>>, the symlink
> can be deconfigured if still in place by running pvecm updatecerts --unmerge-known-hosts.


### 5.9.2 Pitfalls due to automatic execution of .bashrc and siblings


In case you have a custom .bashrc, or similar files that get executed on login by the configured shell,
ssh will automatically run it once the session is established successfully. This can cause some unexpected
behavior, as those commands may be executed with root permissions on any of the operations described
above. This can cause possible problematic side-effects!
In order to avoid such complications, it’s recommended to add a check in /root/.bashrc to make sure
the session is interactive, and only then run .bashrc commands.
You can add this snippet at the beginning of your .bashrc file:

# Early exit if not running interactively to avoid side-effects!
case $- in
*i*) ;;
*) return;;
esac


## See also

- [Cluster Manager Overview](_index.md)
- [Remove and Rejoin Nodes](remove-rejoin.md)
- [QDevice and Advanced Topics](qdevice-advanced.md)
