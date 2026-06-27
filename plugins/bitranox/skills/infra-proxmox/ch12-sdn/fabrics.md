# Fabrics

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


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


On the Node

Options that are available on every node that is part of a fabric:

Node
Select the node which will be added to the fabric. Only nodes that currently are in the cluster will be
shown.
IPv4
A unique IPv4 address used to generate the OpenFabric Network Entity Title (NET). Each node in the
same fabric must have a different Router-ID, while a single node must use the same NET address
across all fabrics (If this is not given Proxmox VE will automatically choose one and ensure that the
configuration is valid).
IPv6
A unique IPv6 address used to generate the OpenFabric Network Entity Title (NET). Each node in the
same fabric must have a different Router-ID, while a single node must use the same NET address
across all fabrics. If a IPv4 and IPv6 address is configured, the IPv4 one will be used to derive the
NET.


> **Warning:**
> When using IPv6 addresses, the last 3 segments are used to generate the NET. Ensure these
> segments differ between nodes.


Interfaces
Specify the interfaces used to establish peering connections with other OpenFabric nodes. Preferably
select interfaces without pre-assigned IP addresses, then configure addresses in the IPv4/IPv6 column
if needed. A dummy "loopback" interface with the router-id is automatically created.


On The Interface
The following optional parameters can be configured per interface when enabling the additional columns:

IP
A IPv4 that should get automatically configured on this interface. Must include the netmask (e.g. /31)
IPv6
A IPv6 that should get automatically configured on this interface. Must include the netmask (e.g. /127).
Hello Multiplier
Defines how many missed hello packets constitute a failed connection. Higher values make the connection more resilient to packet loss but slow down failure detection. The default value is 10.


> **Warning:**
> When you remove an interface with an entry in /etc/network/interfaces that has
> manual set, then the IP will not get removed on applying the SDN configuration.


### 12.10.5 OSPF


OSPF (Open Shortest Path First) is a widely-used link-state routing protocol that efficiently calculates the
shortest path for routing traffic through IP networks.

Configuration options:

On the Fabric

IPv4 Prefix
IPv4 CIDR network range (e.g., 192.0.2.0/24) used to verify that all router-IDs in the fabric are contained within this prefix.
Area
This specifies the OSPF area identifier, which can be either a 32-bit signed integer or an IP address.
Areas are a way to organize and structure OSPF networks hierarchically, with Area 0 (or 0.0.0.0)
serving as the backbone area.


On the Node

Options that are available on every node that is part of a fabric:

Node
Select the node which will be added to the fabric. Only nodes that are currently in the cluster will be
shown.
IPv4
A unique Router-ID used to identify this router within the OSPF network. Each node in the same fabric
must have a different Router-ID.
Interfaces
Specify the interfaces used to establish peering connections with other OSPF nodes. Preferably select
interfaces without pre-assigned IP addresses, then configure addresses in the IPv4 column if needed.
A dummy "loopback" interface with the router-id is automatically created.
On The Interface
The following optional parameter can be configured per interface:

IP
A IPv4 that should get automatically configured on this interface. Must include the netmask (e.g. /31)


> **Warning:**
> When you remove an interface with an entry in /etc/network/interfaces that has
> manual set, then the IP will not get removed on applying the SDN configuration.


> **Note:**
> The dummy interface will automatically be configured as passive. Every interface which doesn’t have
> an ip-address configured will be treated as a point-to-point link.


## 12.11 IPAM


IP Address Management (IPAM) tools manage the IP addresses of clients on the network. SDN in Proxmox
VE uses IPAM for example to find free IP addresses for new guests.
A single IPAM instance can be associated with one or more zones.


### 12.11.1 PVE IPAM Plugin


The default built-in IPAM for your Proxmox VE cluster.
You can inspect the current status of the PVE IPAM Plugin via the IPAM panel in the SDN section of the
datacenter configuration. This UI can be used to create, update and delete IP mappings. This is particularly
convenient in conjunction with the DHCP feature.
If you are using DHCP, you can use the IPAM panel to create or edit leases for specific VMs, which enables
you to change the IPs allocated via DHCP. When editing an IP of a VM that is using DHCP you must make
sure to force the guest to acquire a new DHCP leases. This can usually be done by reloading the network
stack of the guest or rebooting it.


### 12.11.2 NetBox IPAM Plugin


NetBox is an open-source IP Address Management (IPAM) and datacenter infrastructure management
(DCIM) tool.

To integrate NetBox with Proxmox VE SDN, create an API token in NetBox as described here: https://docs.netbox.de
en/stable/integrations/rest-api/#tokens
The NetBox configuration properties are:

URL
The NetBox REST API endpoint: http://yournetbox.domain.com/api
Token
An API access token

Fingerprint
The SHA-256 fingerprint of the NetBox API. Can be retrieved with openssl x509 -in /etc/ssl/cer
-noout -fingerprint -sha256 when using the default certificate.


### 12.11.3 phpIPAM Plugin


In phpIPAM you need to create an "application" and add an API token with admin privileges to the application.
The phpIPAM configuration properties are:

URL
The REST-API endpoint: http://phpipam.domain.com/api/<appname>/


Token
An API access token
Section
An integer ID. Sections are a group of subnets in phpIPAM. Default installations use sectionid=1
for customers.


## 12.12 DNS


The DNS plugin in Proxmox VE SDN is used to define a DNS API server for registration of your hostname
and IP address. A DNS configuration is associated with one or more zones, to provide DNS registration for
all the subnet IPs configured for a zone.


### 12.12.1 PowerDNS Plugin


https://doc.powerdns.com/authoritative/http-api/index.html
You need to enable the web server and the API in your PowerDNS config:

api=yes
api-key=arandomgeneratedstring
webserver=yes
webserver-port=8081
The PowerDNS configuration options are:

url
The REST API endpoint: http://yourpowerdnserver.domain.com:8081/api/v1/servers/localhost
key
An API access key
ttl
The default TTL for records


## 12.13 DHCP


The DHCP plugin in Proxmox VE SDN can be used to automatically deploy a DHCP server for a Zone. It
provides DHCP for all Subnets in a Zone that have a DHCP range configured. Currently the only available
backend plugin for DHCP is the dnsmasq plugin.
The DHCP plugin works by allocating an IP in the IPAM plugin configured in the Zone when adding a new
network interface to a VM/CT. You can find more information on how to configure an IPAM in the respective
section of our documentation.
When the VM starts, a mapping for the MAC address and IP gets created in the DHCP plugin of the zone.
When the network interfaces is removed or the VM/CT are destroyed, then the entry in the IPAM and the
DHCP server are deleted as well.


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
