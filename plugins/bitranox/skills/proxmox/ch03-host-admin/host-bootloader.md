# Host Bootloader

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Status is 'valid'!
[Wed Apr 22 09:25:48 CEST 2020] Using OVH endpoint: ovh-eu
[Wed Apr 22 09:25:48 CEST 2020] Checking authentication
[Wed Apr 22 09:25:48 CEST 2020] Consumer key is ok.
Remove TXT record: _acme-challenge.example.proxmox.com
All domains validated!
Creating CSR
Checking order status
Order is ready, finalizing order
valid!
Downloading certificate
Setting pveproxy certificate and key
Restarting pveproxy
Task OK

Example: Switching from the staging to the regular ACME directory
Changing the ACME directory for an account is unsupported, but as Proxmox VE supports more than one
account you can just create a new one with the production (trusted) ACME directory as endpoint. You can
also deactivate the staging account and recreate it.

Example: Changing the default ACME account from staging to directory using pvenode

root@proxmox:~# pvenode acme account deactivate default
Renaming account file from '/etc/pve/priv/acme/default' to '/etc/pve/priv/ ←acme/_deactivated_default_4'
Task OK
root@proxmox:~# pvenode acme account register default example@proxmox.com
Directory endpoints:
0) Let's Encrypt V2 (https://acme-v02.api.letsencrypt.org/directory)
1) Let's Encrypt V2 Staging (https://acme-staging-v02.api.letsencrypt.org/ ←directory)
2) Custom
Enter selection: 0
Terms of Service: https://letsencrypt.org/documents/LE-SA-v1.2-November ←-15-2017.pdf
Do you agree to the above terms? [y|N]y
...
Task OK


## 3.13 Host Bootloader


Proxmox VE currently uses one of two bootloaders depending on the disk setup selected in the installer.


For EFI Systems installed with ZFS as the root filesystem systemd-boot is used, unless Secure Boot
is enabled. All other deployments use the standard GRUB bootloader (this usually also applies to systems
which are installed on top of Debian).


### 3.13.1 Partitioning Scheme Used by the Installer


The Proxmox VE installer creates 3 partitions on all disks selected for installation.
The created partitions are:

- a 1 MB BIOS Boot Partition (gdisk type EF02)
- a 512 MB EFI System Partition (ESP, gdisk type EF00)
- a third partition spanning the set hdsize parameter or the remaining space used for the chosen storage
type
Systems using ZFS as root filesystem are booted with a kernel and initrd image stored on the 512 MB EFI
System Partition. For legacy BIOS systems, and EFI systems with Secure Boot enabled, GRUB is used, for
EFI systems without Secure Boot, systemd-boot is used. Both are installed and configured to point to
the ESPs.
GRUB in BIOS mode (--target i386-pc) is installed onto the BIOS Boot Partition of all selected disks
on all systems booted with GRUB 5 .


### 3.13.2 Synchronizing the content of the ESP with proxmox-boot-tool


proxmox-boot-tool is a utility used to keep the contents of the EFI System Partitions properly configured and synchronized. It copies certain kernel versions to all ESPs and configures the respective bootloader
to boot from the vfat formatted ESPs. In the context of ZFS as root filesystem this means that you can use
all optional features on your root pool instead of the subset which is also present in the ZFS implementation
in GRUB or having to create a separate small boot-pool 6 .
In setups with redundancy all disks are partitioned with an ESP, by the installer. This ensures the system
boots even if the first boot device fails or if the BIOS can only boot from a particular disk.
The ESPs are not kept mounted during regular operation. This helps to prevent filesystem corruption to the
vfat formatted ESPs in case of a system crash, and removes the need to manually adapt /etc/fstab
in case the primary boot device fails.

proxmox-boot-tool handles the following tasks:
- formatting and setting up a new partition
- copying and configuring new kernel images and initrd images to all listed ESPs
- synchronizing the configuration on kernel upgrades and other maintenance tasks
- managing the list of kernel versions which are synchronized
5 These are all installs with root on ext4 or xfs and installs with root on ZFS on non-EFI systems
6 Booting
ZFS
on
root
with
GRUB
Debian%20Bookworm%20Root%20on%20ZFS.html

https://openzfs.github.io/openzfs-docs/Getting%20Started/Debian/-


- configuring the boot-loader to boot a particular kernel version (pinning)
You can view the currently configured ESPs and their state by running:


```
# proxmox-boot-tool status
```


Setting up a new partition for use as synced ESP

To format and initialize a partition as synced ESP, e.g., after replacing a failed vdev in an rpool, or when converting an existing system that pre-dates the sync mechanism, proxmox-boot-tool from proxmox-kernel
can be used.


> **Warning:**
> the format command will format the <partition>, make sure to pass in the right device/partition!


For example, to format an empty partition /dev/sda2 as ESP, run the following:


```
# proxmox-boot-tool format /dev/sda2
To setup an existing, unmounted ESP located on /dev/sda2 for inclusion in Proxmox VE’s kernel update
synchronization mechanism, use the following:

# proxmox-boot-tool init /dev/sda2
or

# proxmox-boot-tool init /dev/sda2 grub
to force initialization with GRUB instead of systemd-boot, for example for Secure Boot support.
Afterwards /etc/kernel/proxmox-boot-uuids should contain a new line with the UUID of the
newly added partition. The init command will also automatically trigger a refresh of all configured ESPs.
```


Updating the configuration on all ESPs

To copy and configure all bootable kernels and keep all ESPs listed in /etc/kernel/proxmox-boot-uuids
in sync you just need to run:


```
# proxmox-boot-tool refresh
(The equivalent to running update-grub systems with ext4 or xfs on root).
This is necessary should you make changes to the kernel commandline, or want to sync all kernels and
initrds.
Note
Both update-initramfs and apt (when necessary) will automatically trigger a refresh.
```


Kernel Versions considered by proxmox-boot-tool
The following kernel versions are configured by default:

- the currently running kernel
- the version being newly installed on package updates
- the two latest already installed kernels
- the latest version of the second-to-last kernel series (e.g. 5.0, 5.3), if applicable
- any manually selected kernels
Manually keeping a kernel bootable

Should you wish to add a certain kernel and initrd image to the list of bootable kernels use proxmox-boot-tool
kernel add.
For example run the following to add the kernel with ABI version 5.0.15-1-pve to the list of kernels to
keep installed and synced to all ESPs:


```
# proxmox-boot-tool kernel add 5.0.15-1-pve
```


proxmox-boot-tool kernel list will list all kernel versions currently selected for booting:

```
# proxmox-boot-tool kernel list
Manually selected kernels:
5.0.15-1-pve
Automatically selected kernels:
5.0.12-1-pve
4.15.18-18-pve
Run proxmox-boot-tool kernel remove to remove a kernel from the list of manually selected
kernels, for example:

# proxmox-boot-tool kernel remove 5.0.15-1-pve
```


> **Note:**
> It’s required to run proxmox-boot-tool refresh to update all EFI System Partitions (ESPs) after
> a manual kernel addition or removal from above.


### 3.13.3 Determine which Bootloader is Used


The simplest and most reliable way to determine which bootloader is used, is to watch the boot process of
the Proxmox VE node.
You will either see the blue box of GRUB or the simple black on white systemd-boot.

Determining the bootloader from a running system might not be 100% accurate. The safest way is to run the
following command:


# efibootmgr -v
If it returns a message that EFI variables are not supported, GRUB is used in BIOS/Legacy mode.
If the output contains a line that looks similar to the following, GRUB is used in UEFI mode.

Boot0005* proxmox

[...] File(\EFI\proxmox\grubx64.efi)

If the output contains a line similar to the following, systemd-boot is used.

Boot0006* Linux Boot Manager
)

[...] File(\EFI\systemd\systemd-bootx64.efi ←-

By running:


```
# proxmox-boot-tool status
you can find out if proxmox-boot-tool is configured, which is a good indication of how the system is
booted.
```


## See also

- [GRUB, Systemd-boot and Secure Boot](host-bootloader-grub-secureboot.md)
- [System Administration Overview](_index.md)
