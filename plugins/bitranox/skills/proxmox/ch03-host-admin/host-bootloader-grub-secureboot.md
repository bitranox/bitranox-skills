# Host Bootloader: GRUB, Systemd-boot and Secure Boot

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 3.13.4 GRUB


GRUB has been the de-facto standard for booting Linux systems for many years and is quite well documented
7.
Configuration
Changes to the GRUB configuration are done via the defaults file /etc/default/grub or config snippets in /etc/default/grub.d. To regenerate the configuration file after a change to the configuration
run: 8


```
# update-grub
```


### 3.13.5 Systemd-boot


systemd-boot is a lightweight EFI bootloader. It reads the kernel and initrd images directly from the EFI
Service Partition (ESP) where it is installed. The main advantage of directly loading the kernel from the ESP
is that it does not need to reimplement the drivers for accessing the storage. In Proxmox VE proxmox-boottool is used to keep the configuration on the ESPs synchronized.
Configuration

systemd-boot is configured via the file loader/loader.conf in the root directory of an EFI System
Partition (ESP). See the loader.conf(5) manpage for details.
Each bootloader entry is placed in a file of its own in the directory loader/entries/
An example entry.conf looks like this (/ refers to the root of the ESP):
7 GRUB Manual https://www.gnu.org/software/grub/manual/grub/grub.html
8 Systems using proxmox-boot-tool will call proxmox-boot-tool

refresh upon update-grub.


title
version
options
linux
initrd


### 3.13.6 Proxmox

5.0.15-1-pve
root=ZFS=rpool/ROOT/pve-1 boot=zfs
/EFI/proxmox/5.0.15-1-pve/vmlinuz-5.0.15-1-pve
/EFI/proxmox/5.0.15-1-pve/initrd.img-5.0.15-1-pve

Editing the Kernel Commandline

You can modify the kernel commandline in the following places, depending on the bootloader used:

GRUB

The kernel commandline needs to be placed in the variable GRUB_CMDLINE_LINUX_DEFAULT in the file
/etc/default/grub. Running update-grub appends its content to all linux entries in /boot/grub/g

Systemd-boot
The kernel commandline needs to be placed as one line in /etc/kernel/cmdline. To apply your
changes, run proxmox-boot-tool refresh, which sets it as the option line for all config files in
loader/entries/proxmox-*.conf.
A complete list of kernel parameters can be found at https://www.kernel.org/doc/html/v<YOUR-KERNELVERSION>/admin-guide/kernel-parameters.html. replace <YOUR-KERNEL-VERSION> with the major.minor
version, for example, for kernels based on version 6.5 the URL would be: https://www.kernel.org/doc/html/v6.5/admin-guide/kernel-parameters.html
You can find your kernel version by checking the web interface (Node → Summary ), or by running

# uname -r
Use the first two numbers at the front of the output.


### 3.13.7 Override the Kernel-Version for next Boot


To select a kernel that is not currently the default kernel, you can either:

- use the boot loader menu that is displayed at the beginning of the boot process
- use the proxmox-boot-tool to pin the system to a kernel version either once or permanently (until
pin is reset).
This should help you work around incompatibilities between a newer kernel version and the hardware.

> **Note:**
> Such a pin should be removed as soon as possible so that all current security patches of the latest kernel
> are also applied to the system.


For example: To permanently select the version 5.15.30-1-pve for booting you would run:


```
# proxmox-boot-tool kernel pin 5.15.30-1-pve
```


> **Tip:**
> The pinning functionality works for all Proxmox VE systems, not only those using proxmox-boot-tool
> to synchronize the contents of the ESPs, if your system does not use proxmox-boot-tool for synchronizing you can also skip the proxmox-boot-tool refresh call in the end.


You can also set a kernel version to be booted on the next system boot only. This is for example useful to
test if an updated kernel has resolved an issue, which caused you to pin a version in the first place:


```
# proxmox-boot-tool kernel pin 5.15.30-1-pve --next-boot
To remove any pinned version configuration use the unpin subcommand:

# proxmox-boot-tool kernel unpin
While unpin has a --next-boot option as well, it is used to clear a pinned version set with --next-boot.
As that happens already automatically on boot, invoking it manually is of little use.
After setting, or clearing pinned versions you also need to synchronize the content and configuration on the
ESPs by running the refresh subcommand.
Tip
You will be prompted to automatically do for proxmox-boot-tool managed systems if you call the
tool interactively.

# proxmox-boot-tool refresh
```


### 3.13.8 Secure Boot


Since Proxmox VE 8.1, Secure Boot is supported out of the box via signed packages and integration in
proxmox-boot-tool.
The following packages are required for secure boot to work. You can install them all at once by using the
‘proxmox-secure-boot-support’ meta-package.

- shim-signed (shim bootloader signed by Microsoft)
- shim-helpers-amd64-signed (fallback bootloader and MOKManager, signed by Proxmox)
- grub-efi-amd64-signed (GRUB EFI bootloader, signed by Proxmox)
- proxmox-kernel-6.X.Y-Z-pve-signed (Kernel image, signed by Proxmox)
Only GRUB is supported as bootloader out of the box, since other bootloader are currently not eligible for
secure boot code-signing.
Any new installation of Proxmox VE will automatically have all of the above packages included.
More details about how Secure Boot works, and how to customize the setup, are available in our wiki.


Switching an Existing Installation to Secure Boot

> **Warning:**
> This can lead to an unbootable installation in some cases if not done correctly. Reinstalling the host
> will setup Secure Boot automatically if available, without any extra interactions. Make sure you
> have a working and well-tested backup of your Proxmox VE host!


An existing UEFI installation can be switched over to Secure Boot if desired, without having to reinstall
Proxmox VE from scratch.
First, ensure all your system is up-to-date. Next, install proxmox-secure-boot-support. GRUB
automatically creates the needed EFI boot entry for booting via the default shim.

systemd-boot
If systemd-boot is used as a bootloader (see Determine which Bootloader is used), some additional
setup is needed. This is only the case if Proxmox VE was installed with ZFS-on-root.
To check the latter, run:


```
# findmnt /
If the host is indeed using ZFS as root filesystem, the FSTYPE column should contain zfs:
```


TARGET SOURCE
FSTYPE OPTIONS
/
rpool/ROOT/pve-1 zfs
rw,relatime,xattr,noacl,casesensitive
Next, a suitable potential ESP (EFI system partition) must be found. This can be done using the lsblk
command as following:


```
# lsblk -o +FSTYPE
The output should look something like this:
```


NAME
MAJ:MIN RM SIZE RO TYPE MOUNTPOINTS FSTYPE
sda
8:0
0
32G 0 disk
&#x251c;&#x2500;sda1
8:1
0 1007K 0 part
&#x251c;&#x2500;sda2
8:2
0 512M 0 part
&#x2514;&#x2500;sda3
8:3
0 31.5G 0 part
sdb
8:16
0
32G 0 disk
&#x251c;&#x2500;sdb1
8:17
0 1007K 0 part
&#x251c;&#x2500;sdb2
8:18
0 512M 0 part
&#x2514;&#x2500;sdb3
8:19
0 31.5G 0 part

vfat
zfs_member

vfat
zfs_member

In this case, the partitions sda2 and sdb2 are the targets. They can be identified by the their size of 512M
and their FSTYPE being vfat, in this case on a ZFS RAID-1 installation.
These partitions must be properly set up for booting through GRUB using proxmox-boot-tool. This
command (using sda2 as an example) must be run separately for each individual ESP:


```
# proxmox-boot-tool init /dev/sda2 grub
Afterwards, you can sanity-check the setup by running the following command:
```


# efibootmgr -v
This list should contain an entry looking similar to this:

[..]
Boot0009* proxmox
shimx64.efi)
[..]

HD(2,GPT,..,0x800,0x100000)/File(\EFI\proxmox\ ←-


> **Note:**
> The old systemd-boot bootloader will be kept, but GRUB will be preferred. This way, if booting using GRUB in Secure Boot mode does not work for any reason, the system can still be booted using
> systemd-boot with Secure Boot turned off.


Now the host can be rebooted and Secure Boot enabled in the UEFI firmware setup utility.
On reboot, a new entry named proxmox should be selectable in the UEFI firmware boot menu, which boots
using the pre-signed EFI shim.
If, for any reason, no proxmox entry can be found in the UEFI boot menu, you can try adding it manually (if
supported by the firmware), by adding the file \EFI\proxmox\shimx64.efi as a custom boot entry.

> **Note:**
> Some UEFI firmwares are known to drop the proxmox boot option on reboot. This can happen if
> the proxmox boot entry is pointing to a GRUB installation on a disk, where the disk itself is not a
> boot option. If possible, try adding the disk as a boot option in the UEFI firmware setup utility and run
> proxmox-boot-tool again.


> **Tip:**
> To enroll custom keys, see the accompanying Secure Boot wiki page.


Using DKMS/Third Party Modules With Secure Boot
On systems with Secure Boot enabled, the kernel will refuse to load modules which are not signed by a
trusted key. The default set of modules shipped with the kernel packages is signed with an ephemeral key
embedded in the kernel image which is trusted by that specific version of the kernel image.
In order to load other modules, such as those built with DKMS or manually, they need to be signed with a
key trusted by the Secure Boot stack. The easiest way to achieve this is to enroll them as Machine Owner
Key (MOK) with mokutil.
The dkms tool will automatically generate a keypair and certificate in /var/lib/dkms/mok.key and
/var/lib/dkms/mok.pub and use it for signing the kernel modules it builds and installs.
You can view the certificate contents with


```
# openssl x509 -in /var/lib/dkms/mok.pub -noout -text
and enroll it on your system using the following command:
```


# mokutil --import /var/lib/dkms/mok.pub
input password:
input password again:
The mokutil command will ask for a (temporary) password twice, this password needs to be entered
one more time in the next step of the process! Rebooting the system should automatically boot into the
MOKManager EFI binary, which allows you to verify the key/certificate and confirm the enrollment using
the password selected when starting the enrollment using mokutil. Afterwards, the kernel should allow
loading modules built with DKMS (which are signed with the enrolled MOK). The MOK can also be used to
sign custom EFI binaries and kernel images if desired.
The same procedure can also be used for custom/third-party modules not managed with DKMS, but the
key/certificate generation and signing steps need to be done manually in that case.


## 3.14 Kernel Samepage Merging (KSM)


Kernel Samepage Merging (KSM) is an optional memory deduplication feature offered by the Linux kernel,
which is enabled by default in Proxmox VE. KSM works by scanning a range of physical memory pages for
identical content, and identifying the virtual pages that are mapped to them. If identical pages are found,
the corresponding virtual pages are re-mapped so that they all point to the same physical page, and the old
pages are freed. The virtual pages are marked as "copy-on-write", so that any writes to them will be written
to a new area of memory, leaving the shared physical page intact.


### 3.14.1 Implications of KSM


KSM can optimize memory usage in virtualization environments, as multiple VMs running similar operating
systems or workloads could potentially share a lot of common memory pages.
However, while KSM can reduce memory usage, it also comes with some security risks, as it can expose
VMs to side-channel attacks. Research has shown that it is possible to infer information about a running VM
via a second VM on the same host, by exploiting certain characteristics of KSM.
Thus, if you are using Proxmox VE to provide hosting services, you should consider disabling KSM, in order
to provide your users with additional security. Furthermore, you should check your country’s regulations, as
disabling KSM may be a legal requirement.


### 3.14.2 Disabling KSM


KSM can be disabled on a node or on a per-VM basis.

Disabe KSM on a Node
To see if KSM is active on a node, you can check the output of:


```
# systemctl status ksmtuned
If it is, it can be disabled immediately with:
```


## See also

- [Host Bootloader: Partitioning and proxmox-boot-tool](host-bootloader.md)
- [System Administration Overview](_index.md)
