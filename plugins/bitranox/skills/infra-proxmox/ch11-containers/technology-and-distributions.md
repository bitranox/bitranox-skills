# Technology Overview and Distributions

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Containers are a lightweight alternative to fully virtualized machines (VMs). They use the kernel of the host
system that they run on, instead of emulating a full operating system (OS). This means that containers can
access resources on the host system directly.
The runtime costs for containers is low, usually negligible. However, there are some drawbacks that need be
considered:

- Only Linux distributions can be run in Proxmox Containers. It is not possible to run other operating systems
like, for example, FreeBSD or Microsoft Windows inside a container.

- For security reasons, access to host resources needs to be restricted. Therefore, containers run in their
own separate namespaces. Additionally some syscalls (user space requests to the Linux kernel) are not
allowed within containers.
Proxmox VE uses Linux Containers (LXC) as its underlying container technology. The “Proxmox Container
Toolkit” (pct) simplifies the usage and management of LXC, by providing an interface that abstracts complex
tasks.
Containers are tightly integrated with Proxmox VE. This means that they are aware of the cluster setup, and
they can use the same network and storage resources as virtual machines. You can also use the Proxmox
VE firewall, or manage containers using the HA framework.
Our primary goal has traditionally been to offer an environment that provides the benefits of using a VM, but
without the additional overhead. This means that Proxmox Containers have been primarily categorized as
“System Containers”.
With the introduction of OCI (Open Container Initiative) image support, Proxmox VE now also integrates
“Application Containers” as a technology preview. When creating a container from an OCI image, the image
is automatically converted to the LXC stack that Proxmox VE uses.
This approach allows users to benefit from a wide ecosystem of pre-packaged applications while retaining
the robust management features of Proxmox VE.
While running lightweight “Application Containers” directly offers significant advantages over a full VM, for
use cases demanding maximum isolation and the ability to live-migrate, nesting containers inside a Proxmox
QEMU VM remains a recommended practice.


## 11.1 Technology Overview


- LXC (https://linuxcontainers.org/)
- Integrated into Proxmox VE graphical web user interface (GUI)
- Easy to use command-line tool pct
- Access via Proxmox VE REST API
- lxcfs to provide containerized /proc file system
- Control groups (cgroups) for resource isolation and limitation
- AppArmor and seccomp to improve security
- Modern Linux kernels
- Image based deployment (templates)
- Uses Proxmox VE storage library
- Container setup from host (network, DNS, storage, etc.)


## 11.2 Supported Distributions


List of officially supported distributions can be found below.
Templates for the following distributions are available through our repositories. You can use pveam tool or
the Graphical User Interface to download them.


### 11.2.1 Alpine Linux


Alpine Linux is a security-oriented, lightweight Linux distribution based on musl libc and busybox.
— https://alpinelinux.org
For currently supported releases see:
https://alpinelinux.org/releases/


### 11.2.2 Arch Linux


Arch Linux, a lightweight and flexible Linux® distribution that tries to Keep It Simple.
— https://archlinux.org/
Arch Linux is using a rolling-release model, see its wiki for more details:
https://wiki.archlinux.org/title/Arch_Linux


### 11.2.3 CentOS, Almalinux, Rocky Linux


CentOS / CentOS Stream
The CentOS Linux distribution is a stable, predictable, manageable and reproducible platform
derived from the sources of Red Hat Enterprise Linux (RHEL)
— https://centos.org
For currently supported releases see:
https://en.wikipedia.org/wiki/CentOS#End-of-support_schedule

Almalinux
An Open Source, community owned and governed, forever-free enterprise Linux distribution,
focused on long-term stability, providing a robust production-grade platform. AlmaLinux OS is
1:1 binary compatible with RHEL® and pre-Stream CentOS.
— https://almalinux.org
For currently supported releases see:
https://en.wikipedia.org/wiki/AlmaLinux#Releases

Rocky Linux
Rocky Linux is a community enterprise operating system designed to be 100% bug-for-bug
compatible with America’s top enterprise Linux distribution now that its downstream partner has
shifted direction.
— https://rockylinux.org
For currently supported releases see:
https://en.wikipedia.org/wiki/Rocky_Linux#Releases


### 11.2.4 Debian


Debian is a free operating system, developed and maintained by the Debian project. A free
Linux distribution with thousands of applications to meet our users’ needs.
— https://www.debian.org/intro/index#software
For currently supported releases see:
https://www.debian.org/releases/stable/releasenotes


### 11.2.5 Devuan


Devuan GNU+Linux is a fork of Debian without systemd that allows users to reclaim control over
their system by avoiding unnecessary entanglements and ensuring Init Freedom.
— https://www.devuan.org
For currently supported releases see:
https://www.devuan.org/os/releases


### 11.2.6 Fedora


Fedora creates an innovative, free, and open source platform for hardware, clouds, and containers that enables software developers and community members to build tailored solutions for
their users.
— https://getfedora.org
For currently supported releases see:
https://fedoraproject.org/wiki/Releases


### 11.2.7 Gentoo


a highly flexible, source-based Linux distribution.
— https://www.gentoo.org
Gentoo is using a rolling-release model.


### 11.2.8 OpenSUSE


The makers’ choice for sysadmins, developers and desktop users.
— https://www.opensuse.org
For currently supported releases see:
https://get.opensuse.org/leap/


### 11.2.9 Ubuntu


Ubuntu is the modern, open source operating system on Linux for the enterprise server, desktop,
cloud, and IoT.
— https://ubuntu.com/
For currently supported releases see:
https://wiki.ubuntu.com/Releases


## 11.3 Container Images


Container images, sometimes also referred to as “templates” or “appliances”, are tar archives which contain everything to run a container. Proxmox VE can utilize two main types of images: System Container
Templates for creating full virtual environments, and Application Container Images based on the OCI
standard for running specific applications.


### 11.3.1 System Container Templates


Proxmox VE itself provides a variety of basic templates for the most common Linux distributions. They can
be downloaded using the GUI or the pveam (short for Proxmox VE Appliance Manager) command-line utility.
Additionally, TurnKey Linux container templates are also available to download.
The list of available templates is updated daily through the pve-daily-update timer. You can also trigger an
update manually by executing:

# pveam update
To view the list of available images run:

# pveam available
You can restrict this large list by specifying the section you are interested in, for example basic system
images:

List available system images

# pveam available --section system
system
alpine-3.12-default_20200823_amd64.tar.xz
system
alpine-3.13-default_20210419_amd64.tar.xz
system
alpine-3.14-default_20210623_amd64.tar.xz
system
archlinux-base_20210420-1_amd64.tar.gz
system
centos-7-default_20190926_amd64.tar.xz
system
centos-8-default_20201210_amd64.tar.xz
system
debian-9.0-standard_9.7-1_amd64.tar.gz
system
debian-10-standard_10.7-1_amd64.tar.gz
system
devuan-3.0-standard_3.0_amd64.tar.gz
system
fedora-33-default_20201115_amd64.tar.xz
system
fedora-34-default_20210427_amd64.tar.xz
system
gentoo-current-default_20200310_amd64.tar.xz
system
opensuse-15.2-default_20200824_amd64.tar.xz
system
ubuntu-16.04-standard_16.04.5-1_amd64.tar.gz
system
ubuntu-18.04-standard_18.04.1-1_amd64.tar.gz
system
ubuntu-20.04-standard_20.04-1_amd64.tar.gz
system
ubuntu-20.10-standard_20.10-1_amd64.tar.gz
system
ubuntu-21.04-standard_21.04-1_amd64.tar.gz
Before you can use such a template, you need to download them into one of your storages. If you’re unsure
to which one, you can simply use the local named storage for that purpose. For clustered installations, it
is preferred to use a shared storage so that all nodes can access those images.


# pveam download local debian-10.0-standard_10.0-1_amd64.tar.gz
You are now ready to create containers using that image, and you can list all downloaded images on storage
local with:

# pveam list local
local:vztmpl/debian-10.0-standard_10.0-1_amd64.tar.gz

219.95MB


> **Tip:**
> You can also use the Proxmox VE web interface GUI to download, list and delete container templates.


```
pct uses them to create a new container, for example:
```


```
# pct create 999 local:vztmpl/debian-10.0-standard_10.0-1_amd64.tar.gz
The above command shows you the full Proxmox VE volume identifiers. They include the storage name, and
most other Proxmox VE commands can use them. For example you can delete that image later with:

# pveam remove local:vztmpl/debian-10.0-standard_10.0-1_amd64.tar.gz
```


### 11.3.2 Open Container Initiative (OCI) Images


Proxmox VE can also use OCI images to create containers, both system containers but also application
containers. Note that running application containers in Proxmox VE is currently considered a technology
preview.
A container created from an OCI image still uses the existing LXC framework.


### 11.3.3 Obtaining OCI Images


In the web interface an OCI image can be uploaded manually or pulled from a registry using the Pull from
OCI registry button on the container template view of a storage.
Once the template is on a storage, you can create the container with pct create or use the wizard in the
web interface.


## 11.4 Container Settings


### 11.4.1 General Settings


General settings of a container include

- the Node : the physical server on which the container will run
- the CT ID: a unique number in this Proxmox VE installation used to identify your container
- Hostname: the hostname of the container
- Resource Pool: a logical group of containers and VMs
- Password: the root password of the container
- SSH Public Key: a public key for connecting to the root account over SSH
- Unprivileged container: this option allows to choose at creation time if you want to create a privileged or
unprivileged container.

- Nesting: expose procfs and sysfs to allow nested containers. Note that systemd also uses this to isolate
services.

Unprivileged Containers
Unprivileged containers use a new kernel feature called user namespaces. The root UID 0 inside the container is mapped to an unprivileged user outside the container. This means that most security issues (container escape, resource abuse, etc.) in these containers will affect a random unprivileged user, and would
be a generic kernel security bug rather than an LXC issue. The LXC team thinks unprivileged containers are
safe by design.
This is the default option when creating a new container.
