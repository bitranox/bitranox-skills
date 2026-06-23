# Zones

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 12.6.3 VLAN Zones


The VLAN plugin uses an existing local Linux or OVS bridge to connect to the node’s physical interface. It
uses VLAN tagging defined in the VNet to isolate the network segments. This allows connectivity of VMs
between different nodes.
VLAN zone configuration options:

Bridge
The local bridge or OVS switch, already configured on each node that allows node-to-node connection.


### 12.6.4 QinQ Zones


QinQ also known as VLAN stacking, that uses multiple layers of VLAN tags for isolation. The QinQ zone
defines the outer VLAN tag (the Service VLAN) whereas the inner VLAN tag is defined by the VNet.

> **Note:**
> Your physical network switches must support stacked VLANs for this configuration.


QinQ zone configuration options:

Bridge
A local, VLAN-aware bridge that is already configured on each local node
Service VLAN
The main VLAN tag of this zone
Service VLAN Protocol
Allows you to choose between an 802.1q (default) or 802.1ad service VLAN type.
MTU
Due to the double stacking of tags, you need 4 more bytes for QinQ VLANs. For example, you must
reduce the MTU to 1496 if you physical interface MTU is 1500.


### 12.6.5 VXLAN Zones


The VXLAN plugin establishes a tunnel (overlay) on top of an existing network (underlay). This encapsulates
layer 2 Ethernet frames within layer 4 UDP datagrams using the default destination port 4789.
You have to configure the underlay network yourself to enable UDP connectivity between all peers.
You can, for example, create a VXLAN overlay network on top of public internet, appearing to the VMs as if
they share the same local Layer 2 network.

> **Warning:**
> VXLAN on its own does does not provide any encryption. When joining multiple sites via VXLAN,
> make sure to establish a secure connection between the site, for example by using a site-to-site
> VPN.


VXLAN zone configuration options:

Peers Address List
A list of IP addresses of each node in the VXLAN zone. This can be external nodes reachable at this
IP address. All nodes in the cluster need to be mentioned here.
SDN Fabric
Instead of manually defining all the peers, use a Fabric for automatically generating the peer list.
MTU
Because VXLAN encapsulation uses 50 bytes, the MTU needs to be 50 bytes lower than the outgoing
physical interface.


### 12.6.6 EVPN Zones


The EVPN zone creates a routable Layer 3 network, capable of spanning across multiple clusters. This is
achieved by establishing a VPN and utilizing BGP as the routing protocol.
The VNet of EVPN can have an anycast IP address and/or MAC address. The bridge IP is the same on each
node, meaning a virtual guest can use this address as gateway.
Routing can work across VNets from different zones through a VRF (Virtual Routing and Forwarding) interface.
EVPN zone configuration options:

VRF VXLAN ID
A VXLAN-ID used for dedicated routing interconnect between VNets. It must be different than the
VXLAN-ID of the VNets.
Controller
The EVPN-controller to use for this zone. (See controller plugins section).
VNet MAC Address
Anycast MAC address that gets assigned to all VNets in this zone. Will be auto-generated if not
defined.
Exit Nodes
Nodes that shall be configured as exit gateways from the EVPN network, through the real network.
The configured nodes will announce a default route in the EVPN network. Optional.
Primary Exit Node
If you use multiple exit nodes, force traffic through this primary exit node, instead of load-balancing on
all nodes. Optional but necessary if you want to use SNAT or if your upstream router doesn’t support
ECMP.
Exit Nodes Local Routing
This is a special option if you need to reach a VM/CT service from an exit node. (By default, the exit
nodes only allow forwarding traffic between real network and EVPN network). Optional.


Advertise Subnets
Announce the full subnet in the EVPN network. If you have silent VMs/CTs (for example, if you have
multiple IPs and the anycast gateway doesn’t see traffic from these IPs, the IP addresses won’t be
able to be reached inside the EVPN network). Optional.
Disable ARP ND Suppression
Don’t suppress ARP or ND (Neighbor Discovery) packets. This is required if you use floating IPs in
your VMs (IP and MAC addresses are being moved between systems). Optional.
Route-target Import
Allows you to import a list of external EVPN route targets. Used for cross-DC or different EVPN
network interconnects. Optional.
MTU
Because VXLAN encapsulation uses 50 bytes, the MTU needs to be 50 bytes less than the maximal
MTU of the outgoing physical interface. Optional, defaults to 1450.


## 12.7 VNets


After creating a virtual network (VNet) through the SDN GUI, a local network interface with the same name
is available on each node. To connect a guest to the VNet, assign the interface to the guest and set the IP
address accordingly.
Depending on the zone, these options have different meanings and are explained in the respective zone
section in this document.


> **Warning:**
> In the current state, some options may have no effect or won’t work in certain zones.


VNet configuration options:

ID
An up to 8 character ID to identify a VNet
Comment
More descriptive identifier. Assigned as an alias on the interface. Optional
Zone
The associated zone for this VNet
Tag
The unique VLAN or VXLAN ID
VLAN Aware
Enables vlan-aware option on the interface, enabling configuration in the guest.


Isolate Ports
Sets the isolated flag for all guest ports of this interface, but not for the interface itself. This means
guests can only send traffic to non-isolated bridge-ports, which is the bridge itself. In order for this
setting to take effect, you need to restart the affected guest.

> **Note:**
> Port isolation is local to each host. Use the VNET Firewall to further isolate traffic in the VNET across
> nodes. For example, DROP by default and only allow traffic from the IP subnet to the gateway and vice
> versa.


## 12.8 Subnets


A subnet define a specific IP range, described by the CIDR network address. Each VNet, can have one or
more subnets.
A subnet can be used to:

- Restrict the IP addresses you can define on a specific VNet
- Assign routes/gateways on a VNet in layer 3 zones
- Enable SNAT on a VNet in layer 3 zones
- Auto assign IPs on virtual guests (VM or CT) through IPAM plugins
- DNS registration through DNS plugins
If an IPAM server is associated with the subnet zone, the subnet prefix will be automatically registered in the
IPAM.
Subnet configuration options:

ID
A CIDR network address, for example 10.0.0.0/8
Gateway
The IP address of the network’s default gateway. On layer 3 zones (Simple/EVPN plugins), it will be
deployed on the VNet.
SNAT
Enable Source NAT which allows VMs from inside a VNet to connect to the outside network by forwarding the packets to the nodes outgoing interface. On EVPN zones, forwarding is done on EVPN
gateway-nodes. Optional.
DNS Zone Prefix
Add a prefix to the domain registration, like <hostname>.prefix.<domain> Optional.


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
