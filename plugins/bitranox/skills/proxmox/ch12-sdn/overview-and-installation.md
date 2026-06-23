# SDN Overview and Installation

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

The Software-Defined Network (SDN) feature in Proxmox VE enables the creation of virtual zones and
networks (VNets). This functionality simplifies advanced networking configurations and multitenancy setup.


## 12.1 Introduction


The Proxmox VE SDN allows for separation and fine-grained control of virtual guest networks, using flexible,
software-controlled configurations.
Separation is managed through zones, virtual networks (VNets), and subnets. A zone is its own virtually
separated network area. A VNet is a virtual network that belongs to a zone. A subnet is an IP range inside
a VNet.
Depending on the type of the zone, the network behaves differently and offers specific features, advantages,
and limitations.
Use cases for SDN range from an isolated private network on each individual node to complex overlay
networks across multiple PVE clusters on different locations.
After configuring an VNet in the cluster-wide datacenter SDN administration interface, it is available as a
common Linux bridge, locally on each node, to be assigned to VMs and Containers.


## 12.2 Support Status


### 12.2.1 History


The Proxmox VE SDN stack has been available as an experimental feature since 2019 and has been continuously improved and tested by many developers and users. With its integration into the web interface in
Proxmox VE 6.2, a significant milestone towards broader integration was achieved. During the Proxmox VE
7 release cycle, numerous improvements and features were added. Based on user feedback, it became
apparent that the fundamental design choices and their implementation were quite sound and stable. Consequently, labeling it as ‘experimental’ did not do justice to the state of the SDN stack. For Proxmox VE 8, a
decision was made to lay the groundwork for full integration of the SDN feature by elevating the management
of networks and interfaces to a core component in the Proxmox VE access control stack. In Proxmox VE 8.1,
two major milestones were achieved: firstly, DHCP integration was added to the IP address management
(IPAM) feature, and secondly, the SDN integration is now installed by default.


### 12.2.2 Current Status


The current support status for the various layers of our SDN installation is as follows:

- Core SDN, which includes VNet management and its integration with the Proxmox VE stack, is fully supported.

- IPAM, including DHCP management for virtual guests, is in tech preview.
- Complex routing via FRRouting and controller integration are in tech preview.


## 12.3 Installation


### 12.3.1 SDN Core


Since Proxmox VE 8.1 the core Software-Defined Network (SDN) packages are installed by default.
If you upgrade from an older version, you need to install the libpve-network-perl package on every
node:

apt update
apt install libpve-network-perl


> **Note:**
> Proxmox VE version 7.0 and above have the ifupdown2 package installed by default. If you originally
> installed your system with an older version, you need to explicitly install the ifupdown2 package.


After installation, you need to ensure that the following line is present at the end of the /etc/network/interfa
configuration file on all nodes, so that the SDN configuration gets included and activated.

source /etc/network/interfaces.d/*


### 12.3.2 DHCP IPAM


The DHCP integration into the built-in PVE IP Address Management stack currently uses dnsmasq for
giving out DHCP leases. This is currently opt-in.
To use that feature you need to install the dnsmasq package on every node:

apt update
apt install dnsmasq
# disable default instance
systemctl disable --now dnsmasq


### 12.3.3 FRRouting


The Proxmox VE SDN stack uses the FRRouting project for advanced setups. This is currently opt-in.
To use the SDN routing integration you need to install the frr-pythontools package on all nodes:

apt update
apt install frr-pythontools
Then enable the frr service on all nodes:

systemctl enable frr.service


## 12.4 Configuration Overview


Configuration is done at the web UI at datacenter level, separated into the following sections:

- SDN: Here you get an overview of the current active SDN state, and you can apply all pending changes to
the whole cluster.

- Zones: Create and manage the virtually separated network zones
- VNets: Create virtual network bridges and manage subnets
The Options category allows adding and managing additional services to be used in your SDN setup.

- Controllers: For controlling layer 3 routing in complex setups
- DHCP: Define a DHCP server for a zone that automatically allocates IPs for guests in the IPAM and leases
them to the guests via DHCP.

- IPAM: Enables external for IP address management for guests
- DNS: Define a DNS server integration for registering virtual guests’ hostname and IP addresses


## 12.5 Technology & Configuration


The Proxmox VE Software-Defined Network implementation uses standard Linux networking as much as
possible. The reason for this is that modern Linux networking provides almost all needs for a feature full SDN
implementation and avoids adding external dependencies and reduces the overall amount of components
that can break.
The Proxmox VE SDN configurations are located in /etc/pve/sdn, which is shared with all other cluster
nodes through the Proxmox VE configuration file system. Those configurations get translated to the respective configuration formats of the tools that manage the underlying network stack (for example ifupdown2
or frr).
New changes are not immediately applied but recorded as pending first. You can then apply a set of different
changes all at once in the main SDN overview panel on the web interface. This system allows to roll-out
various changes as single atomic one.
The SDN tracks the rolled-out state through the .running-config and .version files located in /etc/pve/sdn.


## 12.6 Zones


A zone defines a virtually separated network. Zones are restricted to specific nodes and assigned permissions, in order to restrict users to a certain zone and its contained VNets.
Different technologies can be used for separation:

- Simple: Isolated Bridge. A simple layer 3 routing bridge (NAT)
- VLAN: Virtual LANs are the classic method of subdividing a LAN
- QinQ: Stacked VLAN (formally known as IEEE 802.1ad)
- VXLAN: Layer 2 VXLAN network via a UDP tunnel
- EVPN (BGP EVPN): VXLAN with BGP to establish Layer 3 routing


### 12.6.1 Common Options


The following options are available for all zone types:

Nodes
The nodes which the zone and associated VNets should be deployed on.
IPAM
Use an IP Address Management (IPAM) tool to manage IPs in the zone. Optional, defaults to pve.
DNS
DNS API server. Optional.
ReverseDNS
Reverse DNS API server. Optional.
DNSZone
DNS domain name. Used to register hostnames, such as <hostname>.<domain>. The DNS
zone must already exist on the DNS server. Optional.


### 12.6.2 Simple Zones


This is the simplest plugin. It will create an isolated VNet bridge. This bridge is not linked to a physical
interface, and VM traffic is only local on each the node. It can be used in NAT or routed setups.


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

