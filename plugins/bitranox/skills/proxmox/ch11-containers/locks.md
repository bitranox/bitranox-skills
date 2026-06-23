# Container Locks

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

template: <boolean> (default = 0)
Enable/disable Template.

timezone: <string>
Time zone to use in the container. If option isn’t set, then nothing will be done. Can be set to host to
match the host time zone, or an arbitrary time zone option from /usr/share/zoneinfo/zone.tab

tty: <integer> (0 - 6) (default = 2)
Specify the number of tty available to the container

unprivileged: <boolean> (default = 0)
Makes the container run as unprivileged user. For creation, the default is 1. For restore, the default is
the value from the backup. (Should not be modified manually.)

unused[n]: [volume=]<volume>
Reference to unused volumes. This is used internally, and should not be modified manually.

volume=<volume>
The volume that is not used currently.


## 11.12 Locks


Container migrations, snapshots and backups (vzdump) set a lock to prevent incompatible concurrent actions on the affected container. Sometimes you need to remove such a lock manually (e.g., after a power
failure).


```
# pct unlock <CTID>
```


> **Caution:**
> Only do this if you are sure the action which set the lock is no longer running.


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
