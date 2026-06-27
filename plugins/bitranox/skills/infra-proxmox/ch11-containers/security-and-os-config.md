# Security and OS Configuration

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Changing CGroup Version
Before Proxmox VE 9.0, you could switch back to the previous version with the following kernel command-line
parameter:

systemd.unified_cgroup_hierarchy=0
See this section on editing the kernel boot command line on where to add the parameter.


## 11.6 Guest Operating System Configuration


Proxmox VE tries to detect the Linux distribution in the container, and modifies some files. Here is a short
list of things done at container startup:

set /etc/hostname
to set the container name
modify /etc/hosts
to allow lookup of the local hostname
network setup
pass the complete network setup to the container
configure DNS
pass information about DNS servers
adapt the init system
for example, fix the number of spawned getty processes
set the root password
when creating a new container
rewrite ssh_host_keys
so that each container has unique keys
randomize crontab
so that cron does not start at the same time on all containers
Changes made by Proxmox VE are enclosed by comment markers:

# --- BEGIN PVE --<data>
# --- END PVE --Those markers will be inserted at a reasonable location in the file. If such a section already exists, it will be
updated in place and will not be moved.
Modification of a file can be prevented by adding a .pve-ignore. file for it. For instance, if the file
/etc/.pve-ignore.hosts exists then the /etc/hosts file will not be touched. This can be a
simple empty file created via:


# touch /etc/.pve-ignore.hosts
Most modifications are OS dependent, so they differ between different distributions and versions. You can
completely disable modifications by manually setting the ostype to unmanaged.
OS type detection is done by testing for certain files inside the container. Proxmox VE first checks the
/etc/os-release file 3 . If that file is not present, or it does not contain a clearly recognizable distribution
identifier the following distribution specific release files are checked.

Ubuntu
inspect /etc/lsb-release (DISTRIB_ID=Ubuntu)
Debian
test /etc/debian_version
Fedora
test /etc/fedora-release
RedHat or CentOS
test /etc/redhat-release
ArchLinux
test /etc/arch-release
Alpine
test /etc/alpine-release
Gentoo
test /etc/gentoo-release

> **Note:**
> Container start fails if the configured ostype differs from the auto detected type.


## 11.7 Container Storage


The Proxmox VE LXC container storage model is more flexible than traditional container storage models. A
container can have multiple mount points. This makes it possible to use the best suited storage for each
application.
For example the root file system of the container can be on slow and cheap storage while the database can
be on fast and distributed storage via a second mount point. See section Mount Points for further details.
Any storage type supported by the Proxmox VE storage library can be used. This means that containers
can be stored on local (for example lvm, zfs or directory), shared external (like iSCSI, NFS) or even
3 /etc/os-release

release.5.en.html

replaces the multitude of per-distribution release files https://manpages.debian.org/stable/systemd/os-


distributed storage systems like Ceph. Advanced storage features like snapshots or clones can be used if
the underlying storage supports them. The vzdump backup tool can use snapshots to provide consistent
container backups.
Furthermore, local devices or local directories can be mounted directly using bind mounts. This gives access
to local resources inside a container with practically zero overhead. Bind mounts can be used as an easy
way to share data between containers.


### 11.7.1 FUSE Mounts


> **Warning:**
> Because of existing issues in the Linux kernel’s freezer subsystem the usage of FUSE mounts inside
> a container is strongly advised against, as containers need to be frozen for suspend or snapshot
> mode backups.


If FUSE mounts cannot be replaced by other mounting mechanisms or storage technologies, it is possible to
establish the FUSE mount on the Proxmox host and use a bind mount point to make it accessible inside the
container.


### 11.7.2 Using Quotas Inside Containers


Quotas allow to set limits inside a container for the amount of disk space that each user can use.

> **Note:**
> This currently requires the use of legacy cgroups.


> **Note:**
> This only works on ext4 image based storage types and currently only works with privileged containers.


Activating the quota option causes the following mount options to be used for a mount point: usrjquota=aquot
This allows quotas to be used like on any other system. You can initialize the /aquota.user and
/aquota.group files by running:

# quotacheck -cmug /
# quotaon /
Then edit the quotas using the edquota command. Refer to the documentation of the distribution running
inside the container for details.

> **Note:**
> You need to run the above commands for every mount point by passing the mount point’s path instead of
> just /.


### 11.7.3 Using ACLs Inside Containers


The standard Posix Access Control Lists are also available inside containers. ACLs allow you to set more
detailed file ownership than the traditional user/group/others model.


### 11.7.4 Backup of Container mount points


To include a mount point in backups, enable the backup option for it in the container configuration. For an
existing mount point mp0

mp0: guests:subvol-100-disk-1,mp=/root/files,size=8G
add backup=1 to enable it.

mp0: guests:subvol-100-disk-1,mp=/root/files,size=8G,backup=1


> **Note:**
> When creating a new mount point in the GUI, this option is enabled by default.


To disable backups for a mount point, add backup=0 in the way described above, or uncheck the Backup
checkbox on the GUI.


### 11.7.5 Replication of Containers mount points


By default, additional mount points are replicated when the Root Disk is replicated. If you want the Proxmox
VE storage replication mechanism to skip a mount point, you can set the Skip replication option for that
mount point. As of Proxmox VE 5.0, replication requires a storage of type zfspool. Adding a mount point
to a different type of storage when the container has replication configured requires to have Skip replication
enabled for that mount point.


## 11.8 Backup and Restore


### 11.8.1 Container Backup


It is possible to use the vzdump tool for container backup. Please refer to the vzdump manual page for
details.


### 11.8.2 Restoring Container Backups


Restoring container backups made with vzdump is possible using the pct restore command. By
default, pct restore will attempt to restore as much of the backed up container configuration as possible.
It is possible to override the backed up configuration by manually setting container options on the command
line (see the pct manual page for details).
