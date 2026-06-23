# Ceph Installation and Configuration

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 8.1 Introduction


Proxmox VE unifies your compute and storage systems, that is, you can use the same physical nodes within
a cluster for both computing (processing VMs and containers) and replicated storage. The traditional silos of
compute and storage resources can be wrapped up into a single hyper-converged appliance. Separate storage networks (SANs) and connections via network attached storage (NAS) disappear. With the integration
of Ceph, an open source software-defined storage platform, Proxmox VE has the ability to run and manage
Ceph storage directly on the hypervisor nodes.
Ceph is a distributed object store and file system designed to provide excellent performance, reliability and
scalability.

S OME ADVANTAGES OF C EPH ON P ROXMOX VE ARE :
- Easy setup and management via CLI and GUI
- Thin provisioning
- Snapshot support


- Self healing
- Scalable to the exabyte level
- Provides block, file system, and object storage
- Setup pools with different performance and redundancy characteristics
- Data is replicated, making it fault tolerant
- Runs on commodity hardware
- No need for hardware RAID controllers
- Open source
For small to medium-sized deployments, it is possible to install a Ceph server for using RADOS Block Devices
(RBD) or CephFS directly on your Proxmox VE cluster nodes (see Ceph RADOS Block Devices (RBD)).
Recent hardware has a lot of CPU power and RAM, so running storage services and virtual guests on the
same node is possible.
To simplify management, Proxmox VE provides you native integration to install and manage Ceph services
on Proxmox VE nodes either via the built-in web interface, or using the pveceph command line tool.


## 8.2 Terminology


C EPH CONSISTS OF MULTIPLE DAEMONS , FOR USE AS AN RBD STORAGE :
- Ceph Monitor (ceph-mon, or MON)
- Ceph Manager (ceph-mgr, or MGS)
- Ceph Metadata Service (ceph-mds, or MDS)
- Ceph Object Storage Daemon (ceph-osd, or OSD)

> **Tip:**
> We highly recommend to get familiar with Ceph a , its architecture b and vocabulary c .
> a Ceph intro https://docs.ceph.com/en/squid/start/
> b Ceph architecture https://docs.ceph.com/en/squid/architecture/
> c Ceph glossary https://docs.ceph.com/en/squid/glossary


## 8.3 Recommendations for a Healthy Ceph Cluster


To build a hyper-converged Proxmox + Ceph Cluster, you must use at least three (preferably) identical servers
for the setup.
Check also the recommendations from Ceph’s website.


> **Note:**
> The recommendations below should be seen as a rough guidance for choosing hardware. Therefore, it
> is still essential to adapt it to your specific needs. You should test your setup and monitor health and
> performance continuously.


CPU
Ceph services can be classified into two categories:

- Intensive CPU usage, benefiting from high CPU base frequencies and multiple cores. Members of that
category are:

– Object Storage Daemon (OSD) services
– Meta Data Service (MDS) used for CephFS
- Moderate CPU usage, not needing multiple CPU cores. These are:
– Monitor (MON) services
– Manager (MGR) services
As a simple rule of thumb, you should assign at least one CPU core (or thread) to each Ceph service to
provide the minimum resources required for stable and durable Ceph performance.
For example, if you plan to run a Ceph monitor, a Ceph manager and 6 Ceph OSDs services on a node you
should reserve 8 CPU cores purely for Ceph when targeting basic and stable performance.
Note that OSDs CPU usage depend mostly from the disks performance. The higher the possible IOPS (IO
Operations per Second) of a disk, the more CPU can be utilized by a OSD service. For modern enterprise
SSD disks, like NVMe’s that can permanently sustain a high IOPS load over 100’000 with sub millisecond
latency, each OSD can use multiple CPU threads, e.g., four to six CPU threads utilized per NVMe backed
OSD is likely for very high performance disks.

Memory
Especially in a hyper-converged setup, the memory consumption needs to be carefully planned out and
monitored. In addition to the predicted memory usage of virtual machines and containers, you must also
account for having enough memory available for Ceph to provide excellent and stable performance.
While usage may be less under normal conditions, it will consume more memory during critical operations,
such as recovery, rebalancing, or backfilling. That means you should avoid maxing out your available memory
already on regular operation, but rather leave some headroom to cope with outages.
The current recommendation is to configure OSDs with at least 8 GiB of memory for good performance.
The OSD daemon requires 4 GiB by default.

> **Note:**
> Total memory consumption is primarily determined by the number of OSD daemons. However, for critical
> operations, all Ceph services may require additional memory.


Network
We recommend a network bandwidth of at least 10 Gbps, or more, to be used exclusively for Ceph traffic. A
meshed network setup 1 is also an option for three to five node clusters, if there are no 10+ Gbps switches
available.

> **Important:**
> The volume of traffic, especially during recovery, will interfere with other services on the same network, especially the latency sensitive Proxmox VE corosync cluster stack can be affected, resulting
> in possible loss of cluster quorum. Moving the Ceph traffic to dedicated and physical separated
> networks will avoid such interference, not only for corosync, but also for the networking services
> provided by any virtual guests.


For estimating your bandwidth needs, you need to take the performance of your disks into account.. While
a single HDD might not saturate a 1 Gb link, multiple HDD OSDs per node can already saturate 10 Gbps
too. If modern NVMe-attached SSDs are used, a single one can already saturate 10 Gbps of bandwidth, or
more. For such high-performance setups we recommend at least a 25 Gpbs, while even 40 Gbps or 100+
Gbps might be required to utilize the full performance potential of the underlying disks.
If unsure, we recommend using three (physical) separate networks for high-performance setups:

- one very high bandwidth (25+ Gbps) network for Ceph (internal) cluster traffic.
- one high bandwidth (10+ Gpbs) network for Ceph (public) traffic between the ceph server and ceph client
storage traffic. Depending on your needs this can also be used to host the virtual guest traffic and the VM
live-migration traffic.

- one medium bandwidth (1 Gbps) exclusive for the latency sensitive corosync cluster communication.
Disks
When planning the size of your Ceph cluster, it is important to take the recovery time into consideration.
Especially with small clusters, recovery might take long. It is recommended that you use SSDs instead of
HDDs in small setups to reduce recovery time, minimizing the likelihood of a subsequent failure event during
recovery.
In general, SSDs will provide more IOPS than spinning disks. With this in mind, in addition to the higher
cost, it may make sense to implement a class based separation of pools. Another way to speed up OSDs is
to use a faster disk as a journal or DB/Write-Ahead-Log device, see creating Ceph OSDs. If a faster disk is
used for multiple OSDs, a proper balance between OSD and WAL / DB (or journal) disk must be selected,
otherwise the faster disk becomes the bottleneck for all linked OSDs.
Aside from the disk type, Ceph performs best with an evenly sized, and an evenly distributed amount of disks
per node. For example, 4 x 500 GB disks within each node is better than a mixed setup with a single 1 TB
and three 250 GB disk.
You also need to balance OSD count and single OSD capacity. More capacity allows you to increase storage
density, but it also means that a single OSD failure forces Ceph to recover more data at once.
1 Full Mesh Network for Ceph https://pve.proxmox.com/wiki/Full_Mesh_Network_for_Ceph_Server


Avoid RAID
As Ceph handles data object redundancy and multiple parallel writes to disks (OSDs) on its own, using a
RAID controller normally doesn’t improve performance or availability. On the contrary, Ceph is designed to
handle whole disks on it’s own, without any abstraction in between. RAID controllers are not designed for
the Ceph workload and may complicate things and sometimes even reduce performance, as their write and
caching algorithms may interfere with the ones from Ceph.


> **Warning:**
> Avoid RAID controllers. Use host bus adapter (HBA) instead.


## 8.4 Initial Ceph Installation & Configuration


### 8.4.1 Using the Web-based Wizard


With Proxmox VE you have the benefit of an easy to use installation wizard for Ceph. Click on one of your
cluster nodes and navigate to the Ceph section in the menu tree. If Ceph is not already installed, you will
see a prompt offering to do so.


The wizard is divided into multiple sections, where each needs to finish successfully, in order to use Ceph.
First you need to chose which Ceph version you want to install. Prefer the one from your other nodes, or the
newest if this is the first node you install Ceph.
After starting the installation, the wizard will download and install all the required packages from Proxmox
VE’s Ceph repository.

After finishing the installation step, you will need to create a configuration. This step is only needed once per
cluster, as this configuration is distributed automatically to all remaining cluster members through Proxmox
VE’s clustered configuration file system (pmxcfs).
The configuration step includes the following settings:

- Public Network: This network will be used for public storage communication (e.g., for virtual machines
using a Ceph RBD backed disk, or a CephFS mount), and communication between the different Ceph
services. This setting is required.
Separating your Ceph traffic from the Proxmox VE cluster communication (corosync), and possible the
front-facing (public) networks of your virtual guests, is highly recommended. Otherwise, Ceph’s highbandwidth IO-traffic could cause interference with other low-latency dependent services.

- Cluster Network: Specify to separate the OSD replication and heartbeat traffic as well. This setting is
optional.
Using a physically separated network is recommended, as it will relieve the Ceph public and the virtual
guests network, while also providing a significant Ceph performance improvements.
The Ceph cluster network can be configured and moved to another physically separated network at a later
time.


You have two more options which are considered advanced and therefore should only changed if you know
what you are doing.

- Number of replicas: Defines how often an object is replicated.
- Minimum replicas: Defines the minimum number of required replicas for I/O to be marked as complete.
Additionally, you need to choose your first monitor node. This step is required.
That’s it. You should now see a success page as the last step, with further instructions on how to proceed.
Your system is now ready to start using Ceph. To get started, you will need to create some additional
monitors, OSDs and at least one pool.
The rest of this chapter will guide you through getting the most out of your Proxmox VE based Ceph setup.
This includes the aforementioned tips and more, such as CephFS, which is a helpful addition to your new
Ceph cluster.


### 8.4.2 CLI Installation of Ceph Packages


Alternatively to the the recommended Proxmox VE Ceph installation wizard available in the web interface,
you can use the following CLI command on each node:


```
pveceph install
```

This sets up an apt package repository in /etc/apt/sources.list.d/ceph.sources and installs the required software.


### 8.4.3 Initial Ceph configuration via CLI


Use the Proxmox VE Ceph installation wizard (recommended) or run the following command on one node:


```
pveceph init --network 10.10.10.0/24
```


This creates an initial configuration at /etc/pve/ceph.conf with a dedicated network for Ceph. This file
is automatically distributed to all Proxmox VE nodes, using pmxcfs. The command also creates a symbolic
link at /etc/ceph/ceph.conf, which points to that file. Thus, you can simply run Ceph commands
without the need to specify a configuration file.


## 8.5 Ceph Monitor


The Ceph Monitor (MON) 2 maintains a master copy of the cluster map. For high availability, you need at
least 3 monitors. One monitor will already be installed if you used the installation wizard. You won’t need
more than 3 monitors, as long as your cluster is small to medium-sized. Only really large clusters will require
more than this.


### 8.5.1 Create Monitors


On each node where you want to place a monitor (three monitors are recommended), create one by using
the Ceph → Monitor tab in the GUI or run:


```
pveceph mon create
```

2 Ceph Monitor https://docs.ceph.com/en/squid/rados/configuration/mon-config-ref/
