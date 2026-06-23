# VNets, Subnets, and Controllers

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 12.9 Controllers


Some zones implement a separated control and data plane that require an external controller to manage the
VNet’s control plane.
Currently, only the EVPN zone requires an external controller.


### 12.9.1 EVPN Controller


The EVPN, zone requires an external controller to manage the control plane. The EVPN controller plugin
configures the Free Range Routing (frr) router.
To enable the EVPN controller, you need to enable FRR on every node, see install FRRouting.
EVPN controller configuration options:

ASN #
A unique BGP ASN number. It’s highly recommended to use a private ASN number (64512 – 65534,
4200000000 – 4294967294), as otherwise you could end up breaking global routing by mistake.
SDN Fabric
A Fabric that contains all the nodes part of the EVPN zone. Will be used as the underlay network.
Peers
An IP list of all nodes that are part of the EVPN zone. (could also be external nodes or route reflector
servers)


### 12.9.2 BGP Controller


The BGP controller is not used directly by a zone. You can use it to configure FRR to manage BGP peers.
For BGP-EVPN, it can be used to define a different ASN by node, so doing EBGP. It can also be used to
export EVPN routes to an external BGP peer.

> **Note:**
> By default, for a simple full mesh EVPN, you don’t need to define a BGP controller.


BGP controller configuration options:

Node
The node of this BGP controller
ASN #
A unique BGP ASN number. It’s highly recommended to use a private ASN number in the range (64512
- 65534) or (4200000000 - 4294967294), as otherwise you could break global routing by mistake.
Peer
A list of peer IP addresses you want to communicate with using the underlying BGP network.


EBGP
If your peer’s remote-AS is different, this enables EBGP.
Loopback Interface
Use a loopback or dummy interface as the source of the EVPN network (for multipath).
ebgp-mutltihop
Increase the number of hops to reach peers, in case they are not directly connected or they use
loopback.
bgp-multipath-as-path-relax
Allow ECMP if your peers have different ASN.


### 12.9.3 ISIS Controller


The ISIS controller is not used directly by a zone. You can use it to configure FRR to export EVPN routes to
an ISIS domain.
ISIS controller configuration options:

Node
The node of this ISIS controller.
Domain
A unique ISIS domain.
Network Entity Title
A Unique ISIS network address that identifies this node.
Interfaces
A list of physical interface(s) used by ISIS.
Loopback
Use a loopback or dummy interface as the source of the EVPN network (for multipath).


## 12.10 Fabrics


Fabrics in Proxmox VE SDN provide automated routing between nodes in a cluster. They simplify the configuration of underlay networks between nodes to form the foundation for SDN deployments.
They automatically configure routing protocols on your physical network interfaces to establish connectivity
between nodes in the cluster. This creates a resilient, auto-configuring network fabric that adapts to changes
in network topology. These fabrics can be used as a full-mesh network for Ceph or in the EVPN controller
and VXLAN zone.


### 12.10.1 Installation


The FRR implementations of OpenFabric and OSPF are used, so first ensure that the frr and frr-pythontool
packages are installed:

apt update
apt install frr frr-pythontools


### 12.10.2 Permissions


To view the configuration of an SDN fabric users need SDN.Audit or SDN.Allocate permissions. To create
or modify a fabric configuration, users need SDN.Allocate permissions. To view the configuration of a node,


users need the Sys.Audit or Sys.Modify permissions. When adding or updating nodes within a fabric, additional Sys.Modify permission for the specific node is required, since this operation involves writing to the
node’s /etc/network/interfaces file.


### 12.10.3 Configuration


To create a Fabric, head over to Datacenter→SDN→Fabrics and click "Add Fabric". After selecting the
preferred protocol, the fabric is created. With the "+" button you can select the nodes which you want to add
to the fabric, you also have to select the interfaces used to communicate with the other nodes.

Loopback Prefix
You can specify a CIDR network range (e.g., 192.0.2.0/24) as a loopback prefix for the fabric. When configured, the system will automatically verify that all router-IDs are contained within this prefix. This ensures
consistency in your addressing scheme and helps prevent addressing conflicts or errors.

Router-ID Selection
Each node in a fabric needs a unique router-ID, which is an IPv4 address in dotted decimal notation (e.g.,
192.0.2.1). In OpenFabric this can also be an IPv6 address in the typical hexadecimal representation separated by colons (e.g., 2001:db8::1428:57ab). A dummy interface with the router-ID as address will automatically be created and will act as a loopback interface for the fabric (it’s also passive by default).

RouteMaps
For every fabric, an access-list and a route-map are automatically created. These configure the router to
rewrite the source address of outgoing packets. When you communicate with another node (for example,
by pinging it), this ensures that traffic originates from the local dummy interface’s IP address rather than
from the physical interface. This provides consistent routing behavior and proper source address selection
throughout the fabric.

Notes on IPv6
IPv6 is currently only usable on OpenFabric fabrics. These IPv6 Fabrics need global IPv6 forwarding enabled
on all nodes contained in the fabric. Without IPv6 forwarding, non-full-mesh fabrics won’t work because
the transit nodes don’t forward packets to the outer nodes. Currently there isn’t an easy way to enable
IPv6 forwarding per-interface like with IPv4, so it has to be enabled globally. This can be accomplished by
appending this line:

post-up sysctl -w net.ipv6.conf.all.forwarding=1

to a fabric interface in the /etc/network/interfaces file. This will enable IPv6 forwarding globally once that interface comes up. Note that this affects how your interfaces handle automatic IPv6 setup
(SLAAC), Neighbour Advertisements, Router Solicitations, and Router Advertisements. More details here:
https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt under net.ipv6.conf.all.forwarding


### 12.10.4 OpenFabric


OpenFabric is a routing protocol specifically designed for data center fabrics. It’s based on IS-IS and optimized for the spine-leaf topology common in data centers.

Configuration options:

On the Fabric

Name
This is the name of the OpenFabric fabric and can be at most 8 characters long.
IPv4 Prefix
IPv4 CIDR network range (e.g., 192.0.2.0/24) used to verify that all router-IDs in the fabric are contained within this prefix.
IPv6 Prefix
IPv6 CIDR network range (e.g., 2001:db8::/64) used to verify that all router-IDs in the fabric are contained within this prefix.


> **Warning:**
> For IPv6 fabrics to work, global forwarding needs to be enabled on all nodes. Check Notes on IPv6
> for how to do it and additional info.


Hello Interval
Controls how frequently (in seconds) hello packets are sent to discover and maintain connections with
neighboring nodes. Lower values detect failures faster but increase network traffic. This option is
global on the fabric, meaning every interface on every node in this fabric will inherit this hello-interval
property. The default value is 3 seconds.
CSNP Interval
Sets how frequently (in seconds) the node synchronizes its routing database with neighbors. Lower
values keep the network topology information more quickly in sync but increase network traffic. This
option is global on the fabric, meaning every interface on every node in this fabric will inherit this
property. The default value is 10 seconds.
