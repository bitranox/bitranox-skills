# Network Bonding, VLANs and Advanced Configuration

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 3.4.7 Linux Bond


Bonding (also called NIC teaming or Link Aggregation) is a technique for binding multiple NIC’s to a single
network device. It is possible to achieve different goals, like make the network fault-tolerant, increase the
performance or both together.
High-speed hardware like Fibre Channel and the associated switching hardware can be quite expensive. By
doing link aggregation, two NICs can appear as one logical interface, resulting in double speed. This is a
native Linux kernel feature that is supported by most switches. If your nodes have multiple Ethernet ports,
you can distribute your points of failure by running network cables to different switches and the bonded
connection will failover to one cable or the other in case of network trouble.


Aggregated links can improve live-migration delays and improve the speed of replication of data between
Proxmox VE Cluster nodes.
There are 7 modes for bonding:

- Round-robin (balance-rr): Transmit network packets in sequential order from the first available network
interface (NIC) slave through the last. This mode provides load balancing and fault tolerance.

- Active-backup (active-backup): Only one NIC slave in the bond is active. A different slave becomes
active if, and only if, the active slave fails. The single logical bonded interface’s MAC address is externally
visible on only one NIC (port) to avoid distortion in the network switch. This mode provides fault tolerance.

- XOR (balance-xor): Transmit network packets based on [(source MAC address XOR’d with destination
MAC address) modulo NIC slave count]. This selects the same NIC slave for each destination MAC
address. This mode provides load balancing and fault tolerance.

- Broadcast (broadcast): Transmit network packets on all slave network interfaces. This mode provides
fault tolerance.

- IEEE 802.3ad Dynamic link aggregation (802.3ad)(LACP): Creates aggregation groups that share the
same speed and duplex settings. Utilizes all slave network interfaces in the active aggregator group
according to the 802.3ad specification.

- Adaptive transmit load balancing (balance-tlb): Linux bonding driver mode that does not require any
special network-switch support. The outgoing network packet traffic is distributed according to the current
load (computed relative to the speed) on each network interface slave. Incoming traffic is received by one
currently designated slave network interface. If this receiving slave fails, another slave takes over the MAC
address of the failed receiving slave.

- Adaptive load balancing (balance-alb): Includes balance-tlb plus receive load balancing (rlb) for IPV4
traffic, and does not require any special network switch support. The receive load balancing is achieved by
ARP negotiation. The bonding driver intercepts the ARP Replies sent by the local system on their way out
and overwrites the source hardware address with the unique hardware address of one of the NIC slaves in
the single logical bonded interface such that different network-peers use different MAC addresses for their
network packet traffic.
If your switch supports the LACP (IEEE 802.3ad) protocol, then we recommend using the corresponding
bonding mode (802.3ad). Otherwise you should generally use the active-backup mode.
For the cluster network (Corosync) we recommend configuring it with multiple networks. Corosync does not
need a bond for network redundancy as it can switch between networks by itself, if one becomes unusable.
Some bond modes are known to be problematic for Corosync, see Corosync over Bonds.
The following bond configuration can be used as distributed/shared storage network. The benefit would be
that you get more speed and the network will be fault-tolerant.

Example: Use bond with fixed IP address

auto lo
iface lo inet loopback
iface eno1 inet manual


iface eno2 inet manual
iface eno3 inet manual
auto bond0
iface bond0 inet static
bond-slaves eno1 eno2
address 192.168.1.2/24
bond-miimon 100
bond-mode 802.3ad
bond-xmit-hash-policy layer2+3
auto vmbr0
iface vmbr0 inet static
address 10.10.10.2/24
gateway 10.10.10.1
bridge-ports eno3
bridge-stp off
bridge-fd 0

Top of Rack Switch 1
1

2

MLAG

Top of Rack Switch 2
1

eno1 eno2

eno1 eno2

bond0

bond0

LACP

LACP

bond0

bond0

2

vmbr0

vmbr0

10.10.10.2/24

10.10.10.3/24

tap100i0

tap100i0

ens18

ens18

VM 100

VM 200


#### 10.10.10.100 10.10.10.200


Node: proxmox1

Node: proxmox2

Another possibility is to use the bond directly as the bridge port. This can be used to make the guest network
fault-tolerant.
Example: Use a bond as the bridge port

auto lo
iface lo inet loopback


iface eno1 inet manual
iface eno2 inet manual
auto bond0
iface bond0 inet manual
bond-slaves eno1 eno2
bond-miimon 100
bond-mode 802.3ad
bond-xmit-hash-policy layer2+3
auto vmbr0
iface vmbr0 inet static
address 10.10.10.2/24
gateway 10.10.10.1
bridge-ports bond0
bridge-stp off
bridge-fd 0


### 3.4.8 VLAN 802.1Q


A virtual LAN (VLAN) is a broadcast domain that is partitioned and isolated in the network at layer two. So it
is possible to have multiple networks (4096) in a physical network, each independent of the other ones.
Each VLAN network is identified by a number often called tag. Network packages are then tagged to identify
which virtual network they belong to.

VLAN for Guest Networks
Proxmox VE supports this setup out of the box. You can specify the VLAN tag when you create a VM.
The VLAN tag is part of the guest network configuration. The networking layer supports different modes to
implement VLANs, depending on the bridge configuration:

- VLAN awareness on the Linux bridge: In this case, each guest’s virtual network card is assigned to
a VLAN tag, which is transparently supported by the Linux bridge. Trunk mode is also possible, but that
makes configuration in the guest necessary.

- "traditional" VLAN on the Linux bridge: In contrast to the VLAN awareness method, this method is not
transparent and creates a VLAN device with associated bridge for each VLAN. That is, creating a guest on
VLAN 5 for example, would create two interfaces eno1.5 and vmbr0v5, which would remain until a reboot
occurs.

- Open vSwitch VLAN: This mode uses the OVS VLAN feature.
- Guest configured VLAN: VLANs are assigned inside the guest. In this case, the setup is completely
done inside the guest and can not be influenced from the outside. The benefit is that you can use more
than one VLAN on a single virtual NIC.


VLAN on the Host
To allow host communication with an isolated network. It is possible to apply VLAN tags to any network
device (NIC, Bond, Bridge). In general, you should configure the VLAN on the interface with the least
abstraction layers between itself and the physical NIC.
For example, in a default configuration where you want to place the host management address on a separate
VLAN.

Example: Use VLAN 5 for the Proxmox VE management IP with traditional Linux bridge

auto lo
iface lo inet loopback
iface eno1 inet manual
iface eno1.5 inet manual
auto vmbr0v5
iface vmbr0v5 inet static
address 10.10.10.2/24
gateway 10.10.10.1
bridge-ports eno1.5
bridge-stp off
bridge-fd 0
auto vmbr0
iface vmbr0 inet manual
bridge-ports eno1
bridge-stp off
bridge-fd 0

Example: Use VLAN 5 for the Proxmox VE management IP with VLAN aware Linux bridge

auto lo
iface lo inet loopback
iface eno1 inet manual

auto vmbr0.5
iface vmbr0.5 inet static
address 10.10.10.2/24
gateway 10.10.10.1
auto vmbr0
iface vmbr0 inet manual
bridge-ports eno1
bridge-stp off
bridge-fd 0
bridge-vlan-aware yes


bridge-vids 2-4094
The next example is the same setup but a bond is used to make this network fail-safe.

Example: Use VLAN 5 with bond0 for the Proxmox VE management IP with traditional Linux bridge

auto lo
iface lo inet loopback
iface eno1 inet manual
iface eno2 inet manual
auto bond0
iface bond0 inet manual
bond-slaves eno1 eno2
bond-miimon 100
bond-mode 802.3ad
bond-xmit-hash-policy layer2+3
iface bond0.5 inet manual
auto vmbr0v5
iface vmbr0v5 inet static
address 10.10.10.2/24
gateway 10.10.10.1
bridge-ports bond0.5
bridge-stp off
bridge-fd 0
auto vmbr0
iface vmbr0 inet manual
bridge-ports bond0
bridge-stp off
bridge-fd 0


### 3.4.9 Disabling IPv6 on the Node


Proxmox VE works correctly in all environments, irrespective of whether IPv6 is deployed or not. We recommend leaving all settings at the provided defaults.
Should you still need to disable support for IPv6 on your node, do so by creating an appropriate sysctl.conf
(5) snippet file and setting the proper sysctls, for example adding /etc/sysctl.d/disable-ipv6.conf
with content:

net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
This method is preferred to disabling the loading of the IPv6 module on the kernel commandline.


### 3.4.10 Disabling MAC Learning on a Bridge


By default, MAC learning is enabled on a bridge to ensure a smooth experience with virtual guests and their
networks.
But in some environments this can be undesired. Since Proxmox VE 7.3 you can disable MAC learning on the
bridge by setting the ‘bridge-disable-mac-learning 1` configuration on a bridge in `/etc/network/interfaces’,
for example:

# ...
auto vmbr0
iface vmbr0 inet static
address 10.10.10.2/24
gateway 10.10.10.1
bridge-ports ens18
bridge-stp off
bridge-fd 0
bridge-disable-mac-learning 1
Once enabled, Proxmox VE will manually add the configured MAC address from VMs and Containers to the
bridges forwarding database to ensure that guest can still use the network - but only when they are using
their actual MAC address.


## 3.5 Time Synchronization


The Proxmox VE cluster stack itself relies heavily on the fact that all the nodes have precisely synchronized
time. Some other components, like Ceph, also won’t work properly if the local time on all nodes is not in
sync.
Time synchronization between nodes can be achieved using the “Network Time Protocol” (NTP). As of Proxmox VE 7, chrony is used as the default NTP daemon, while Proxmox VE 6 uses systemd-timesyncd.
Both come preconfigured to use a set of public servers.


> **Important:**
> If you upgrade your system to Proxmox VE 7, it is recommended that you manually install either
> chrony, ntp or openntpd.


### 3.5.1 Using Custom NTP Servers


In some cases, it might be desired to use non-default NTP servers. For example, if your Proxmox VE nodes
do not have access to the public internet due to restrictive firewall rules, you need to set up local NTP servers
and tell the NTP daemon to use them.

For systems using chrony:
Specify which servers chrony should use in /etc/chrony/chrony.conf:

## See also

- [Network Configuration](network-configuration.md)
- [Software-Defined Network](../ch12-sdn/_index.md)
- [Firewall](../ch13-firewall/_index.md)
