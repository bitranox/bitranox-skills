# IPAM, DNS, and DHCP

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


> **Note:**
> Some features (adding/editing/removing IP mappings) are currently only available when using the PVE
> IPAM plugin.


### 12.13.1 Configuration


You can enable automatic DHCP for a zone in the Web UI via the Zones panel and enabling DHCP in the
advanced options of a zone.

> **Note:**
> Currently only Simple Zones have support for automatic DHCP


After automatic DHCP has been enabled for a Zone, DHCP Ranges need to be configured for the subnets in
a Zone. In order to that, go to the Vnets panel and select the Subnet for which you want to configure DHCP
ranges. In the edit dialogue you can configure DHCP ranges in the respective Tab. Alternatively you can set
DHCP ranges for a Subnet via the following CLI command:


```
pvesh set /cluster/sdn/vnets/<vnet>/subnets/<subnet>
```

-dhcp-range start-address=10.0.1.100,end-address=10.0.1.200
-dhcp-range start-address=10.0.2.100,end-address=10.0.2.200
You also need to have a gateway configured for the subnet - otherwise automatic DHCP will not work.
The DHCP plugin will then allocate IPs in the IPAM only in the configured ranges.
Do not forget to follow the installation steps for the dnsmasq DHCP plugin as well.


### 12.13.2 Plugins


Dnsmasq Plugin
Currently this is the only DHCP plugin and therefore the plugin that gets used when you enable DHCP for a
zone.
Installation
For installation see the DHCP IPAM section.
Configuration
The plugin will create a new systemd service for each zone that dnsmasq gets deployed to. The name for
the service is dnsmasq@<zone>. The lifecycle of this service is managed by the DHCP plugin.
The plugin automatically generates the following configuration files in the folder /etc/dnsmasq.d/<zone>:

00-default.conf
This contains the default global configuration for a dnsmasq instance.


10-<zone>-<subnet_cidr>.conf
This file configures specific options for a subnet, such as the DNS server that should get configured
via DHCP.

10-<zone>-<subnet_cidr>.ranges.conf
This file configures the DHCP ranges for the dnsmasq instance.

ethers
This file contains the MAC-address and IP mappings from the IPAM plugin. In order to override those
mappings, please use the respective IPAM plugin rather than editing this file, as it will get overwritten
by the dnsmasq plugin.
You must not edit any of the above files, since they are managed by the DHCP plugin. In order to customize
the dnsmasq configuration you can create additional files (e.g. 90-custom.conf) in the configuration
folder - they will not get changed by the dnsmasq DHCP plugin.
Configuration files are read in order, so you can control the order of the configuration directives by naming
your custom configuration files appropriately.
DHCP leases are stored in the file /var/lib/misc/dnsmasq.<zone>.leases.
When using the PVE IPAM plugin, you can update, create and delete DHCP leases. For more information
please consult the documentation of the PVE IPAM plugin. Changing DHCP leases is currently not supported
for the other IPAM plugins.


## 12.14 Firewall Integration


SDN integrates with the Proxmox VE firewall by automatically generating IPSets which can then be referenced in the source / destination fields of firewall rules. This happens automatically for VNets and IPAM
entries.


### 12.14.1 VNets and Subnets


The firewall automatically generates the following IPSets in the SDN scope for every VNet:

vnet-all
Contains the CIDRs of all subnets in a VNet

vnet-gateway
Contains the IPs of the gateways of all subnets in a VNet

vnet-no-gateway
Contains the CIDRs of all subnets in a VNet, but excludes the gateways

vnet-dhcp
Contains all DHCP ranges configured in the subnets in a VNet
When making changes to your configuration, the IPSets update automatically, so you do not have to update
your firewall rules when changing the configuration of your Subnets.


Simple Zone Example
Assuming the configuration below for a VNet and its contained subnets:

# /etc/pve/sdn/vnets.cfg
vnet: vnet0
zone simple
# /etc/pve/sdn/subnets.cfg
subnet: simple-192.0.2.0-24
vnet vnet0
dhcp-range start-address=192.0.2.100,end-address=192.0.2.199
gateway 192.0.2.1
subnet: simple-2001:db8::-64
vnet vnet0
dhcp-range start-address=2001:db8::1000,end-address=2001:db8::1999
gateway 2001:db8::1
In this example we configured an IPv4 subnet in the VNet vnet0, with 192.0.2.0/24 as its IP Range,

#### 192.0.2.1 as the gateway and the DHCP range is 192.0.2.100 - 192.0.2.199.

Additionally we configured an IPv6 subnet with 2001:db8::/64 as the IP range, 2001:db8::1 as the gateway
and a DHCP range of 2001:db8::1000 - 2001:db8::1999.
The respective auto-generated IPsets for vnet0 would then contain the following elements:

vnet0-all
- 192.0.2.0/24
- 2001:db8::/64
vnet0-gateway
- 192.0.2.1
- 2001:db8::1
vnet0-no-gateway
- 192.0.2.0/24
- 2001:db8::/64
- !192.0.2.1
- !2001:db8::1
vnet0-dhcp
- 192.0.2.100 - 192.0.2.199
- 2001:db8::1000 - 2001:db8::1999


### 12.14.2 IPAM


If you are using the built-in PVE IPAM, then the firewall automatically generates an IPset for every guest
that has entries in the IPAM. The respective IPset for a guest with ID 100 would be guest-ipam-100. It
contains all IP addresses from all IPAM entries. So if guest 100 is member of multiple VNets, then the IPset
would contain the IPs from all VNets.
When entries get added / updated / deleted, then the respective IPSets will be updated accordingly.


> **Warning:**
> When removing all entries for a guest and there are firewall rules still referencing the auto-generated
> IPSet then the firewall will fail to update the ruleset, since it references a non-existing IPSet.


## 12.15 Examples


This section presents multiple configuration examples tailored for common SDN use cases. It aims to offer
tangible implementations, providing additional details to enhance comprehension of the available configuration options.


### 12.15.1 Simple Zone Example


Simple zone networks create an isolated network for guests on a single host to connect to each other.

> **Tip:**
> connection between guests are possible if all guests reside on a same host but cannot be reached on
> other nodes.


- Create a simple zone named simple.
- Add a VNet names vnet1.
- Create a Subnet with a gateway and the SNAT option enabled.
- This creates a network bridge vnet1 on the node. Assign this bridge to the guests that shall join the
network and configure an IP address.
The network interface configuration in two VMs may look like this which allows them to communicate via the
10.0.1.0/24 network.

allow-hotplug ens19
iface ens19 inet static
address 10.0.1.14/24
allow-hotplug ens19
iface ens19 inet static
address 10.0.1.15/24


### 12.15.2 Source NAT Example


If you want to allow outgoing connections for guests in the simple network zone the simple zone offers a
Source NAT (SNAT) option.
Starting from the configuration above, Add a Subnet to the VNet vnet1, set a gateway IP and enable the
SNAT option.

Subnet: 172.16.0.0/24
Gateway: 172.16.0.1
SNAT: checked
In the guests configure the static IP address inside the subnet’s IP range.
The node itself will join this network with the Gateway IP 172.16.0.1 and function as the NAT gateway for
guests within the subnet range.


### 12.15.3 VLAN Setup Example


When VMs on different nodes need to communicate through an isolated network, the VLAN zone allows
network level isolation using VLAN tags.
Create a VLAN zone named myvlanzone:

ID: myvlanzone
Bridge: vmbr0
Create a VNet named myvnet1 with VLAN tag 10 and the previously created myvlanzone.

ID: myvnet1
Zone: myvlanzone
Tag: 10
Apply the configuration through the main SDN panel, to create VNets locally on each node.
Create a Debian-based virtual machine (vm1) on node1, with a vNIC on myvnet1.
Use the following network configuration for this VM:

auto eth0
iface eth0 inet static
address 10.0.3.100/24
Create a second virtual machine (vm2) on node2, with a vNIC on the same VNet myvnet1 as vm1.
Use the following network configuration for this VM:

auto eth0
iface eth0 inet static
address 10.0.3.101/24
Following this, you should be able to ping between both VMs using that network.
