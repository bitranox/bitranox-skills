# Introduction

*[Main Index](SKILL.md)*

Proxmox VE is a platform to run virtual machines and containers. It is based on Debian Linux, and completely
open source. For maximum flexibility, we implemented two virtualization technologies - Kernel-based Virtual
Machine (KVM) and container-based virtualization (LXC).
One main design goal was to make administration as easy as possible. You can use Proxmox VE on a
single node, or assemble a cluster of many nodes. All management tasks can be done using our web-based
management interface, and even a novice user can setup and install Proxmox VE within minutes.

User Tools
qm

pvesm

pveum

ha-manager

pct

pvecm

pveceph

pve-firewall

Services
pveproxy

pvedaemon

VM

VM

App

App

Guest OS

App

pvestatd

pve-cluster

App

Guest OS

QEMU
KVM

pve-ha-lrm

Linux Kernel

Container

Container

App

App

App

App

AppArmor cgroups


## 1.1 Central Management


While many people start with a single node, Proxmox VE can scale out to a large set of clustered nodes.
The cluster stack is fully integrated and ships with the default installation.

Unique Multi-Master Design
The integrated web-based management interface gives you a clean overview of all your KVM guests
and Linux containers and even of your whole cluster. You can easily manage your VMs and containers, storage or cluster from the GUI. There is no need to install a separate, complex, and pricey
management server.
Proxmox Cluster File System (pmxcfs)
Proxmox VE uses the unique Proxmox Cluster file system (pmxcfs), a database-driven file system for
storing configuration files. This enables you to store the configuration of thousands of virtual machines.
By using corosync, these files are replicated in real time on all cluster nodes. The file system stores
all data inside a persistent database on disk, nonetheless, a copy of the data resides in RAM which
provides a maximum storage size of 30MB - more than enough for thousands of VMs.
Proxmox VE is the only virtualization platform using this unique cluster file system.
Web-based Management Interface
Proxmox VE is simple to use. Management tasks can be done via the included web based management interface - there is no need to install a separate management tool or any additional management
node with huge databases. The multi-master tool allows you to manage your whole cluster from any
node of your cluster. The central web-based management - based on the JavaScript Framework (ExtJS) - empowers you to control all functionalities from the GUI and overview history and syslogs of each
single node. This includes running backup or restore jobs, live-migration or HA triggered activities.
Command Line
For advanced users who are used to the comfort of the Unix shell or Windows Powershell, Proxmox
VE provides a command-line interface to manage all the components of your virtual environment. This
command-line interface has intelligent tab completion and full documentation in the form of UNIX man
pages.
REST API
Proxmox VE uses a RESTful API. We choose JSON as primary data format, and the whole API is formally defined using JSON Schema. This enables fast and easy integration for third party management
tools like custom hosting environments.
Role-based Administration
You can define granular access for all objects (like VMs, storages, nodes, etc.) by using the role based
user- and permission management. This allows you to define privileges and helps you to control
access to objects. This concept is also known as access control lists: Each permission specifies a
subject (a user or group) and a role (set of privileges) on a specific path.
Authentication Realms
Proxmox VE supports multiple authentication sources like Microsoft Active Directory, LDAP, Linux PAM
standard authentication or the built-in Proxmox VE authentication server.


## 1.2 Flexible Storage


The Proxmox VE storage model is very flexible. Virtual machine images can either be stored on one or
several local storages or on shared storage like NFS and on SAN. There are no limits, you may configure as
many storage definitions as you like. You can use all storage technologies available for Debian Linux.
One major benefit of storing VMs on shared storage is the ability to live-migrate running machines without
any downtime, as all nodes in the cluster have direct access to VM disk images.
We currently support the following Network storage types:

- LVM Group (network backing with iSCSI targets)
- iSCSI target
- NFS Share
- CIFS Share
- Ceph RBD
- CephFS
- Directly use iSCSI LUNs or Fibre Attached SANs.
Local storage types supported are:

- LVM Group (local backing devices like block devices, FC devices, DRBD, etc.)
- Directory (storage on existing filesystem)
- ZFS


## 1.3 Integrated Backup and Restore


The integrated backup tool (vzdump) creates consistent snapshots of running Containers and KVM guests.
It basically creates an archive of the VM or CT data which includes the VM/CT configuration files.
Additionally, the Proxmox Backup Server integration provides advanced features, including the ability to
combine full backups and data deduplication, perform client-side encryption, back up to tape or S3 object
storage, and sync with other offsite Proxmox Backup Server installations.
QEMU/KVM live backup works for all storage types including VM images on NFS, CIFS, iSCSI LUN, Ceph
RBD. The new backup format is optimized for storing VM backups fast and effective (sparse files, out of order
data, minimized I/O).


## 1.4 High Availability Cluster


A multi-node Proxmox VE HA Cluster enables the definition of highly available virtual servers. The Proxmox
VE HA Cluster is based on proven Linux HA technologies, providing stable and reliable HA services.


## 1.5 Flexible Networking


Proxmox VE uses a bridged networking model. All VMs can share one bridge as if virtual network cables
from each guest were all plugged into the same switch. For connecting VMs to the outside world, bridges
are attached to physical network cards and assigned a TCP/IP configuration.
For further flexibility, VLANs (IEEE 802.1q) and network bonding/aggregation are possible. In this way it is
possible to build complex, flexible virtual networks for the Proxmox VE hosts, leveraging the full power of the
Linux network stack.


## 1.6 Integrated Firewall


The integrated firewall allows you to filter network packets on any VM or Container interface. Common sets
of firewall rules can be grouped into “security groups”.


## 1.7 Hyper-converged Infrastructure


Proxmox VE is a virtualization platform that tightly integrates compute, storage and networking resources,
manages highly available clusters, backup/restore as well as disaster recovery. All components are softwaredefined and compatible with one another.
Therefore it is possible to administrate them like a single system via the centralized web management interface. These capabilities make Proxmox VE an ideal choice to deploy and manage an open source hyperconverged infrastructure.


### 1.7.1 Benefits of a Hyper-Converged Infrastructure (HCI) with Proxmox VE


A hyper-converged infrastructure (HCI) is especially useful for deployments in which a high infrastructure
demand meets a low administration budget, for distributed setups such as remote and branch office environments or for virtual private and public clouds.
HCI provides the following advantages:

- Scalability: seamless expansion of compute, network and storage devices (i.e. scale up servers and
storage quickly and independently from each other).

- Low cost: Proxmox VE is open source and integrates all components you need such as compute, storage,
networking, backup, and management center. It can replace an expensive compute/storage infrastructure.

- Data protection and efficiency: services such as backup and disaster recovery are integrated.
- Simplicity: easy configuration and centralized administration.
- Open Source: No vendor lock-in.


### 1.7.2 Hyper-Converged Infrastructure: Storage


Proxmox VE has tightly integrated support for deploying a hyper-converged storage infrastructure. You can,
for example, deploy and manage the following two storage technologies by using the web interface only:

- Ceph: a both self-healing and self-managing shared, reliable and highly scalable storage system. Checkout how to manage Ceph services on Proxmox VE nodes

- ZFS: a combined file system and logical volume manager with extensive protection against data corruption,
various RAID modes, fast and cheap snapshots - among other features. Find out how to leverage the
power of ZFS on Proxmox VE nodes.
Besides above, Proxmox VE has support to integrate a wide range of additional storage technologies. You
can find out about them in the Storage Manager chapter.


## 1.8 Why Open Source


Proxmox VE uses a Linux kernel and is based on the Debian GNU/Linux Distribution. The source code of
Proxmox VE is released under the GNU Affero General Public License, version 3. This means that you are
free to inspect the source code at any time or contribute to the project yourself.
At Proxmox we are committed to use open source software whenever possible. Using open source software
guarantees full access to all functionalities - as well as high security and reliability. We think that everybody
should have the right to access the source code of a software to run it, build on it, or submit changes back
to the project. Everybody is encouraged to contribute while Proxmox ensures the product always meets
professional quality criteria.
Open source software also helps to keep your costs low and makes your core infrastructure independent
from a single vendor.


## 1.9 Your benefits with Proxmox VE


- Open source software
- No vendor lock-in
- Linux kernel
- Fast installation and easy-to-use
- Web-based management interface
- REST API
- Huge active community
- Low administration costs and simple deployment


## 1.10 Getting Help


### 1.10.1 Proxmox VE Wiki


The primary source of information is the Proxmox VE Wiki. It combines the reference documentation with
user contributed content.


### 1.10.2 Community Support Forum


Proxmox VE itself is fully open source, so we always encourage our users to discuss and share their knowledge using the Proxmox VE Community Forum. The forum is moderated by the Proxmox support team, and
has a large user base from all around the world. Needless to say, such a large forum is a great place to get
information.


### 1.10.3 Mailing Lists


This is a fast way to communicate with the Proxmox VE community via email.

- Mailing list for users: Proxmox VE User List
Proxmox VE is fully open source and contributions are welcome! The primary communication channel for
developers is the:

- Mailing list for developers: Proxmox VE development discussion


### 1.10.4 Commercial Support


Proxmox Server Solutions GmbH also offers enterprise support available as Proxmox VE Subscription Service Plans. All users with a subscription get access to the Proxmox VE Enterprise Repository, and—with
a Basic, Standard or Premium subscription—also to the Proxmox Customer Portal. The customer portal
provides help and support with guaranteed response times from the Proxmox VE developers.
For volume discounts, or more information in general, please contact sales@proxmox.com.


### 1.10.5 Bug Tracker


Proxmox runs a public bug tracker at https://bugzilla.proxmox.com. If an issue appears, file your report there.
An issue can be a bug as well as a request for a new feature or enhancement. The bug tracker helps to keep
track of the issue and will send a notification once it has been solved.


## 1.11 Project History


The project started in 2007, followed by a first stable version in 2008. At the time we used OpenVZ for
containers, and QEMU with KVM for virtual machines. The clustering features were limited, and the user
interface was simple (server generated web page).


But we quickly developed new features using the Corosync cluster stack, and the introduction of the new
Proxmox cluster file system (pmxcfs) was a big step forward, because it completely hides the cluster complexity from the user. Managing a cluster of 16 nodes is as simple as managing a single node.
The introduction of our new REST API, with a complete declarative specification written in JSON-Schema,
enabled other people to integrate Proxmox VE into their infrastructure, and made it easy to provide additional
services.
Also, the new REST API made it possible to replace the original user interface with a modern client side
single-page application using JavaScript. We also replaced the old Java based VNC console code with
noVNC. So you only need a web browser to manage your VMs.
The support for various storage types is another big task. Notably, Proxmox VE was the first distribution to
ship ZFS on Linux by default in 2014. Another milestone was the ability to run and manage Ceph storage on
the hypervisor nodes. Such setups are extremely cost effective.
When our project started we were among the first companies providing commercial support for KVM. The
KVM project itself continuously evolved, and is now a widely used hypervisor. New features arrive with each
release. We developed the KVM live backup feature, which makes it possible to create snapshot backups on
any storage type.
The most notable change with version 4.0 was the move from OpenVZ to LXC. Containers are now deeply
integrated, and they can use the same storage and network features as virtual machines. At the same time
we introduced the easy-to-use High Availability (HA) manager, simplifying the configuration and management
of highly available setups.
During the development of Proxmox VE 5 the asynchronous storage replication as well as automated certificate management using ACME/Let’s Encrypt were introduced, among many other features.
The Software Defined Network (SDN) stack was developed in cooperation with our community. It was integrated into the web interface as an experimental feature in version 6.2, simplifying the management of
sophisticated network configurations. Since version 8.1, the SDN integration is fully supported and installed
by default.
2020 marked the release of a new project, the Proxmox Backup Server, written in the Rust programming
language. Proxmox Backup Server is deeply integrated with Proxmox VE and significantly improves backup
capabilities by implementing incremental backups, deduplication, and much more.
Another new tool, the Proxmox Offline Mirror, was released in 2022, enabling subscriptions for systems
which have no connection to the public internet.
The highly requested dark theme for the web interface was introduced in 2023. Later that year, version 8.0
integrated access to the Ceph enterprise repository. Now access to the most stable Ceph repository comes
with any Proxmox VE subscription.
Automated and unattended installation for the official ISO installer was introduced in version 8.2, significantly
simplifying large deployments of Proxmox VE.
With the import wizard, equally introduced in version 8.2, users can easily and efficiently migrate guests
directly from other hypervisors like VMware ESXi 1 . Additionally, archives in Open Virtualization Format
(OVF/OVA) can now be directly imported from file-based storages in the web interface.
1 Migrate to Proxmox VE https://pve.proxmox.com/wiki/Migrate_to_Proxmox_VE


## 1.12 Improving the Proxmox VE Documentation


Contributions and improvements to the Proxmox VE documentation are always welcome. There are several
ways to contribute.
If you find errors or other room for improvement in this documentation, please file a bug at the Proxmox bug
tracker to propose a correction.
If you want to propose new content, choose one of the following options:

- The wiki: For specific setups, how-to guides, or tutorials the wiki is the right option to contribute.
- The reference documentation: For general content that will be helpful to all users please propose your con-

tribution for the reference documentation. This includes all information about how to install, configure, use,
and troubleshoot Proxmox VE features. The reference documentation is written in the asciidoc format. To
edit the documentation you need to clone the git repository at git://git.proxmox.com/git/pve-docs
then follow the README.adoc document.

> **Note:**
> If you are interested in working on the Proxmox VE codebase, the Developer Documentation wiki article
> will show you where to start.


## 1.13 Translating Proxmox VE


The Proxmox VE user interface is in English by default. However, thanks to the contributions of the community, translations to other languages are also available. We welcome any support in adding new languages,
translating the latest features, and improving incomplete or inconsistent translations.
We use gettext for the management of the translation files. Tools like Poedit offer a nice user interface to edit
the translation files, but you can use whatever editor you’re comfortable with. No programming knowledge is
required for translating.


### 1.13.1 Translating with git


The language files are available as a git repository. If you are familiar with git, please contribute according
to our Developer Documentation.
You can create a new translation by doing the following (replace <LANG> with the language ID):

# git clone git://git.proxmox.com/git/proxmox-i18n.git
# cd proxmox-i18n
# make init-<LANG>.po
Or you can edit an existing translation, using the editor of your choice:

# poedit <LANG>.po


### 1.13.2 Translating without git


Even if you are not familiar with git, you can help translate Proxmox VE. To start, you can download the
language files here. Find the language you want to improve, then right click on the "raw" link of this language
file and select Save Link As. . . . Make your changes to the file, and then send your final translation directly
to office(at)proxmox.com, together with a signed contributor license agreement.


### 1.13.3 Testing the Translation


In order for the translation to be used in Proxmox VE, you must first translate the .po file into a .js file.
You can do this by invoking the following script, which is located in the same repository:

# ./po2js.pl -t pve xx.po >pve-lang-xx.js
The resulting file pve-lang-xx.js can then be copied to the directory /usr/share/pve-i18n, on
your proxmox server, in order to test it out.
Alternatively, you can build a deb package by running the following command from the root of the repository:

# make deb


> **Important:**
> For either of these methods to work, you need to have the following perl packages installed on your
> system. For Debian/Ubuntu:


```
# apt-get install perl liblocale-po-perl libjson-perl
```


### 1.13.4 Sending the Translation


You can send the finished translation (.po file) to the Proxmox team at the address office(at)proxmox.com,
along with a signed contributor license agreement. Alternatively, if you have some developer experience,
you can send it as a patch to the Proxmox VE development mailing list. See Developer Documentation.

## See also

- [Installing Proxmox VE](ch02-installation.md)
- [Graphical User Interface](ch04-gui.md)

