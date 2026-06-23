# SDN Firewall Integration and Examples

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


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


### 12.15.4 QinQ Setup Example


This example configures two QinQ zones and adds two VMs to each zone to demonstrate the additional
layer of VLAN tags which allows the configuration of more isolated VLANs.
A typical use case for this configuration is a hosting provider that provides an isolated network to customers
for VM communication but isolates the VMs from other customers.
Create a QinQ zone named qinqzone1 with service VLAN 20

ID: qinqzone1
Bridge: vmbr0
Service VLAN: 20
Create another QinQ zone named qinqzone2 with service VLAN 30

ID: qinqzone2
Bridge: vmbr0
Service VLAN: 30
Create a VNet named myvnet1 with VLAN-ID 100 on the previously created qinqzone1 zone.

ID: qinqvnet1
Zone: qinqzone1
Tag: 100
Create a myvnet2 with VLAN-ID 100 on the qinqzone2 zone.

ID: qinqvnet2
Zone: qinqzone2
Tag: 100
Apply the configuration on the main SDN web interface panel to create VNets locally on each node.
Create four Debian-bases virtual machines (vm1, vm2, vm3, vm4) and add network interfaces to vm1 and
vm2 with bridge qinqvnet1 and vm3 and vm4 with bridge qinqvnet2.
Inside the VM, configure the IP addresses of the interfaces, for example via /etc/network/interfaces:

auto eth0
iface eth0 inet static
address 10.0.3.101/24
Configure all four VMs to have IP addresses from the 10.0.3.101 to 10.0.3.104 range.
Now you should be able to ping between the VMs vm1 and vm2, as well as between vm3 and vm4. However,
neither of VMs vm1 or vm2 can ping VMs vm3 or vm4, as they are on a different zone with a different serviceVLAN.


### 12.15.5 VXLAN Setup Example


The example assumes a cluster with three nodes, with the node IP addresses 192.168.0.1, 192.168.0.2 and
192.168.0.3.
Create a VXLAN zone named myvxlanzone and add all IPs from the nodes to the peer address list. Use
the default MTU of 1450 or configure accordingly.


ID: myvxlanzone
Peers Address List: 192.168.0.1,192.168.0.2,192.168.0.3
Create a VNet named vxvnet1 using the VXLAN zone myvxlanzone created previously.

ID: vxvnet1
Zone: myvxlanzone
Tag: 100000
Apply the configuration on the main SDN web interface panel to create VNets locally on each nodes.
Create a Debian-based virtual machine (vm1) on node1, with a vNIC on vxvnet1.
Use the following network configuration for this VM (note the lower MTU).

auto eth0
iface eth0 inet static
address 10.0.3.100/24
mtu 1450
Create a second virtual machine (vm2) on node3, with a vNIC on the same VNet vxvnet1 as vm1.
Use the following network configuration for this VM:

auto eth0
iface eth0 inet static
address 10.0.3.101/24
mtu 1450
Then, you should be able to ping between between vm1 and vm2.


### 12.15.6 EVPN Setup Example


The example assumes a cluster with three nodes (node1, node2, node3) with IP addresses 192.168.0.1,

#### 192.168.0.2 and 192.168.0.3.

Create an EVPN controller, using a private ASN number and the above node addresses as peers.

ID: myevpnctl
ASN#: 65000
Peers: 192.168.0.1,192.168.0.2,192.168.0.3
Create an EVPN zone named myevpnzone, assign the previously created EVPN-controller and define
node1 and node2 as exit nodes.

ID: myevpnzone
VRF VXLAN Tag: 10000
Controller: myevpnctl
MTU: 1450
VNet MAC Address: 32:F4:05:FE:6C:0A
Exit Nodes: node1,node2
Create the first VNet named myvnet1 using the EVPN zone myevpnzone.


ID: myvnet1
Zone: myevpnzone
Tag: 11000
Create a subnet on myvnet1:

Subnet: 10.0.1.0/24
Gateway: 10.0.1.1
Create the second VNet named myvnet2 using the same EVPN zone myevpnzone.

ID: myvnet2
Zone: myevpnzone
Tag: 12000
Create a different subnet on myvnet2`:

Subnet: 10.0.2.0/24
Gateway: 10.0.2.1
Apply the configuration from the main SDN web interface panel to create VNets locally on each node and
generate the FRR configuration.
Create a Debian-based virtual machine (vm1) on node1, with a vNIC on myvnet1.
Use the following network configuration for vm1:

auto eth0
iface eth0 inet static
address 10.0.1.100/24
gateway 10.0.1.1
mtu 1450
Create a second virtual machine (vm2) on node2, with a vNIC on the other VNet myvnet2.
Use the following network configuration for vm2:

auto eth0
iface eth0 inet static
address 10.0.2.100/24
gateway 10.0.2.1
mtu 1450
Now you should be able to ping vm2 from vm1, and vm1 from vm2.
If you ping an external IP from vm2 on the non-gateway node3, the packet will go to the configured myvnet2
gateway, then will be routed to the exit nodes (node1 or node2) and from there it will leave those nodes over
the default gateway configured on node1 or node2.

> **Note:**
> You need to add reverse routes for the 10.0.1.0/24 and 10.0.2.0/24 networks to node1 and node2 on your
> external gateway, so that the public network can reply back.


If you have configured an external BGP router, the BGP-EVPN routes (10.0.1.0/24 and 10.0.2.0/24 in this
example), will be announced dynamically.


## 12.16 Notes


### 12.16.1 Multiple EVPN Exit Nodes


If you have multiple gateway nodes, you should disable the rp_filter (Strict Reverse Path Filter) option,
because packets can arrive at one node but go out from another node.
Add the following to /etc/sysctl.conf:

net.ipv4.conf.default.rp_filter=0
net.ipv4.conf.all.rp_filter=0


### 12.16.2 VXLAN IPSEC Encryption


To add IPSEC encryption on top of a VXLAN, this example shows how to use strongswan.
You`ll need to reduce the MTU by additional 60 bytes for IPv4 or 80 bytes for IPv6 to handle encryption.
So with default real 1500 MTU, you need to use a MTU of 1370 (1370 + 80 (IPSEC) + 50 (VXLAN) == 1500).
Install strongswan on the host.

apt install strongswan
Add configuration to /etc/ipsec.conf. We only need to encrypt traffic from the VXLAN UDP port 4789.

conn %default
ike=aes256-sha1-modp1024!
on modern HW
esp=aes256-sha1!
leftfirewall=yes
firewall rules

←-

# the fastest, but reasonably secure cipher

# this is necessary when using Proxmox VE

conn output
rightsubnet=%dynamic[udp/4789]
right=%any
type=transport
authby=psk
auto=route
conn input
leftsubnet=%dynamic[udp/4789]
type=transport
authby=psk
auto=route
Generate a pre-shared key with:

openssl rand -base64 128
and add the key to /etc/ipsec.secrets, so that the file contents looks like:

: PSK <generatedbase64key>
Copy the PSK and the configuration to all nodes participating in the VXLAN network.

←-


Proxmox VE Firewall provides an easy way to protect your IT infrastructure. You can setup firewall rules for
all hosts inside a cluster, or define rules for virtual machines and containers. Features like firewall macros,
security groups, IP sets and aliases help to make that task easier.
While all configuration is stored on the cluster file system, the iptables-based firewall service runs on
each cluster node, and thus provides full isolation between virtual machines. The distributed nature of this
system also provides much higher bandwidth than a central firewall solution.
The firewall has full support for IPv4 and IPv6. IPv6 support is fully transparent, and we filter traffic for both
protocols by default. So there is no need to maintain a different set of rules for IPv6.


## 13.1 Directions & Zones


The Proxmox VE firewall groups the network into multiple logical zones. You can define rules for each zone
independently. Depending on the zone, you can define rules for incoming, outgoing or forwarded traffic.


### 13.1.1 Directions


There are 3 directions that you can choose from when defining rules for a zone:

In
Traffic that is arriving in a zone.
Out
Traffic that is leaving a zone.
Forward
Traffic that is passing through a zone. In the host zone this can be routed traffic (when the host is
acting as a gateway or performing NAT). At a VNet-level this affects all traffic that is passing by a VNet,
including traffic from/to bridged network interfaces.

## See also

- [Proxmox VE Firewall](../ch13-firewall/_index.md)

