# System Software Updates

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 3.1.8 SecureApt


The Release files in the repositories are signed with GnuPG. APT is using these signatures to verify that all
packages are from a trusted source.
If you install Proxmox VE from an official ISO image, the key for verification is already installed.
If you install Proxmox VE on top of Debian, download and install the key with the following commands:


```
# wget https://enterprise.proxmox.com/debian/proxmox-archive-keyring- ←trixie.gpg -O /usr/share/keyrings/proxmox-archive-keyring.gpg
```


> **Note:**
> The wget command above adds the keyring for Proxmox releases based on Debian Trixie. Once the
> proxmox-archive-keyring package is installed, it will manage this file. At that point, the hashes
> below may no longer match the hashes of this file, as keys for new Proxmox releases get added or
> removed. This is intended, apt will ensure that only trusted keys are being used. Modifying this file is
> discouraged once proxmox-archive-keyring is installed.


Verify the checksum afterwards with the sha512sum CLI tool:

# sha256sum /usr/share/keyrings/proxmox-archive-keyring.gpg
136673be77aba35dcce385b28737689ad64fd785a797e57897589aed08db6e45 /usr/ ←share/keyrings/proxmox-archive-keyring.gpg
or the md5sum CLI tool:

# md5sum /usr/share/keyrings/proxmox-archive-keyring.gpg
77c8b1166d15ce8350102ab1bca2fcbf /usr/share/keyrings/proxmox-archive- ←keyring.gpg


> **Note:**
> Make sure the path you install the key to matches the Signed-By: lines in your repository stanzas.


## 3.2 System Software Updates


Proxmox provides updates on a regular basis for all repositories. To install updates use the web-based GUI
or the following CLI commands:


```
# apt-get update
# apt-get dist-upgrade
For occasionally upgrading Ceph to its succeeding major release, see Ceph Repositories.
Note
The APT package management system is very flexible and provides many features, see man apt-get,
or [Hertzog13] for additional information.
```


> **Tip:**
> Regular updates are essential to get the latest patches and security related fixes. Major system upgrades
> are announced in the Proxmox VE Community Forum.


## 3.3 Firmware Updates


Firmware updates from this chapter should be applied when running Proxmox VE on a bare-metal server.
Whether configuring firmware updates is appropriate within guests, e.g. when using device pass-through,
depends strongly on your setup and is therefore out of scope.
In addition to regular software updates, firmware updates are also important for reliable and secure operation.
When obtaining and applying firmware updates, a combination of available options is recommended to get
them as early as possible or at all.
The term firmware is usually divided linguistically into microcode (for CPUs) and firmware (for other devices).


### 3.3.1 Persistent Firmware


This section is suitable for all devices. Updated microcode, which is usually included in a BIOS/UEFI update,
is stored on the motherboard, whereas other firmware is stored on the respective device. This persistent
method is especially important for the CPU, as it enables the earliest possible regular loading of the updated
microcode at boot time.

> **Caution:**
> With some updates, such as for BIOS/UEFI or storage controller, the device configuration could be
> reset. Please follow the vendor’s instructions carefully and back up the current configuration.


Please check with your vendor which update methods are available.

- Convenient update methods for servers can include Dell’s Lifecycle Manager or Service Packs from HPE.
- Sometimes there are Linux utilities available as well. Examples are mlxup for NVIDIA ConnectX or
bnxtnvm/niccli for Broadcom network cards.

- LVFS is also an option if there is a cooperation with the hardware vendor and supported hardware in use.
The technical requirement for this is that the system was manufactured after 2014 and is booted via UEFI.
Proxmox VE ships its own version of the fwupd package to enable Secure Boot Support with the Proxmox
signing key. This package consciously dropped the dependency recommendation for the udisks2 package, due to observed issues with its use on hypervisors. That means you must explicitly configure the correct
mount point of the EFI partition in /etc/fwupd/daemon.conf, for example:

## See also

- [Package Repositories](package-repositories.md)

