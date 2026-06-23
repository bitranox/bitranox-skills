# Container Storage

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


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


> **Note:**


```
pvesm extractconfig can be used to view the backed up configuration contained in a vzdump
```

archive.
There are two basic restore modes, only differing by their handling of mount points:
“Simple” Restore Mode
If neither the rootfs parameter nor any of the optional mpX parameters are explicitly set, the mount point
configuration from the backed up configuration file is restored using the following steps:
1. Extract mount points and their options from backup
2. Create volumes for storage backed mount points on the storage provided with the storage parameter (default: local).
3. Extract files from backup archive
4. Add bind and device mount points to restored configuration (limited to root user)

> **Note:**
> Since bind and device mount points are never backed up, no files are restored in the last step, but only
> the configuration options. The assumption is that such mount points are either backed up with another
> mechanism (e.g., NFS space that is bind mounted into many containers), or not intended to be backed up
> at all.


This simple mode is also used by the container restore operations in the web interface.
“Advanced” Restore Mode
By setting the rootfs parameter (and optionally, any combination of mpX parameters), the pct restore
command is automatically switched into an advanced mode. This advanced mode completely ignores the
rootfs and mpX configuration options contained in the backup archive, and instead only uses the options
explicitly provided as parameters.
This mode allows flexible configuration of mount point settings at restore time, for example:

- Set target storages, volume sizes and other options for each mount point individually
- Redistribute backed up files according to new mount point scheme
- Restore to device and/or bind mount points (limited to root user)


## 11.9 Managing Containers with pct


The “Proxmox Container Toolkit” (pct) is the command-line tool to manage Proxmox VE containers. It
enables you to create or destroy containers, as well as control the container execution (start, stop, reboot,
migrate, etc.). It can be used to set parameters in the config file of a container, for example the network
configuration or memory limits.


### 11.9.1 CLI Usage Examples


Create a container based on a Debian template (provided you have already downloaded the template via
the web interface)


```
# pct create 100 /var/lib/vz/template/cache/debian-10.0-standard_10.0-1 ←_amd64.tar.gz
Start container 100

# pct start 100
Start a login session via getty

# pct console 100
Enter the LXC namespace and run a shell as root user

# pct enter 100
Display the configuration

# pct config 100
Add a network interface called eth0, bridged to the host bridge vmbr0, set the address and gateway, while
it’s running

# pct set 100 -net0 name=eth0,bridge=vmbr0,ip=192.168.15.147/24,gw ←=192.168.15.1
Reduce the memory of the container to 512MB

# pct set 100 -memory 512
Destroying a container always removes it from Access Control Lists and it always removes the firewall configuration of the container. You have to activate --purge, if you want to additionally remove the container from
replication jobs, backup jobs and HA resource configurations.
Note
Activating purge will also remove the HA resource from any affinity rules referencing it and will remove
rules that have only this one remaining resource.

# pct destroy 100 --purge
Move a mount point volume to a different storage.

# pct move-volume 100 mp0 other-storage
Reassign a volume to a different CT. This will remove the volume mp0 from the source CT and attaches it
as mp1 to the target CT. In the background the volume is being renamed so that the name matches the new
owner.
```


#


```
pct move-volume 100 mp0 --target-vmid 200 --target-volume mp1
```

