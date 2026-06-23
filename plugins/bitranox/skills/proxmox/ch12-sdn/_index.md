# Software-Defined Network

*[Main Index](../SKILL.md)*

## Contents

| Section                                           | File                                                         |
|---------------------------------------------------|--------------------------------------------------------------|
| 12.1-12.5 SDN Overview and Installation           | [overview-and-installation.md](overview-and-installation.md) |
| 12.6 Zones                                        | [zones.md](zones.md)                                         |
| 12.7-12.9 VNets, Subnets, and Controllers         | [vnets-subnets-controllers.md](vnets-subnets-controllers.md) |
| 12.10 Fabrics                                     | [fabrics.md](fabrics.md)                                     |
| 12.11-12.13 IPAM, DNS, and DHCP                   | [ipam-dns-dhcp.md](ipam-dns-dhcp.md)                         |
| 12.14-12.16 SDN Firewall Integration and Examples | [firewall-and-examples.md](firewall-and-examples.md)         |


## See also

- [Network Configuration](../ch03-host-admin/network-configuration.md)
- [Firewall](../ch13-firewall/_index.md)

## Overview

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
