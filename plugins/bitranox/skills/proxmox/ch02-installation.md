# Installing Proxmox VE

*[Main Index](SKILL.md)*

Proxmox VE is based on Debian. This is why the install disk images (ISO files) provided by Proxmox include
a complete Debian system as well as all necessary Proxmox VE packages.

> **Tip:**
> See the support table in the FAQ for the relationship between Proxmox VE releases and Debian releases.


The installer will guide you through the setup, allowing you to partition the local disk(s), apply basic system
configurations (for example, timezone, language, network) and install all required packages. This process
should not take more than a few minutes. Installing with the provided ISO is the recommended method for
new and existing users.
Alternatively, Proxmox VE can be installed on top of an existing Debian system. This option is only recommended for advanced users because detailed knowledge about Proxmox VE is required.


## 2.1 System Requirements


We recommend using high quality server hardware, when running Proxmox VE in production. To further
decrease the impact of a failed host, you can run Proxmox VE in a cluster with highly available (HA) virtual
machines and containers.
Proxmox VE can use local storage (DAS), SAN, NAS, and distributed storage like Ceph RBD. For details see
chapter storage.


### 2.1.1 Minimum Requirements, for Evaluation


These minimum requirements are for evaluation purposes only and should not be used in production.

* CPU: 64bit (Intel 64 or AMD64)
* Intel VT/AMD-V capable CPU/motherboard for KVM full virtualization support
* RAM: 1 GB RAM, plus additional RAM needed for guests
* Hard drive
* One network card (NIC)


### 2.1.2 Recommended System Requirements


* Intel 64 or AMD64 with Intel VT/AMD-V CPU flag.
* Memory: Minimum 2 GB for the OS and Proxmox VE services, plus designated memory for guests. For
Ceph and ZFS, additional memory is required; approximately 1GB of memory for every TB of used storage.

* Fast and redundant storage, best results are achieved with SSDs.
* OS storage: Use a hardware RAID with battery protected write cache ("BBU") or non-RAID with ZFS
(optional SSD for ZIL).

* VM storage:
  - For local storage, use either a hardware RAID with battery backed write cache (BBU) or non-RAID for
ZFS and Ceph. Neither ZFS nor Ceph are compatible with a hardware RAID controller.
  - Shared and distributed storage is possible.
  - SSDs with Power-Loss-Protection (PLP) are recommended for good performance. Using consumer
SSDs is discouraged.

* Redundant (Multi-)Gbit NICs, with additional NICs depending on the preferred storage technology and
cluster setup.

* For PCI(e) passthrough the CPU needs to support the VT-d/AMD-d flag.


### 2.1.3 Simple Performance Overview


To get an overview of the CPU and hard disk performance on an installed Proxmox VE system, run the
included pveperf tool.

> **Note:**
> This is just a very quick and general benchmark. More detailed tests are recommended, especially regarding the I/O performance of your system.


### 2.1.4 Supported Web Browsers for Accessing the Web Interface


To access the web-based user interface, we recommend using one of the following browsers:

* Firefox, a release from the current year, or the latest Extended Support Release
* Chrome, a release from the current year
* Microsoft's currently supported version of Edge
* Safari, a release from the current year
When accessed from a mobile device, Proxmox VE will show a lightweight, touch-based interface.


## 2.2 Prepare Installation Media


Download the installer ISO image from: https://www.proxmox.com/en/downloads/proxmox-virtual-environment/iso
The Proxmox VE installation media is a hybrid ISO image. It works in two ways:

* An ISO image file ready to burn to a CD or DVD.
* A raw sector (IMG) image file ready to copy to a USB flash drive (USB stick).
Using a USB flash drive to install Proxmox VE is the recommended way because it is the faster option.


### 2.2.1 Prepare a USB Flash Drive as Installation Medium


The flash drive needs to have at least 1 GB of storage available.

> **Note:**
> Do not use UNetbootin. It does not work with the Proxmox VE installation image.


> **Important:**
> Make sure that the USB flash drive is not mounted and does not contain any important data.


### 2.2.2 Instructions for GNU/Linux


On Unix-like operating system use the dd command to copy the ISO image to the USB flash drive. First find
the correct device name of the USB flash drive (see below). Then run the dd command.


```
# dd bs=1M conv=fdatasync if=./proxmox-ve_*.iso of=/dev/XYZ
```


> **Note:**
> Be sure to replace /dev/XYZ with the correct device name and adapt the input filename (if ) path.


> **Caution:**
> Be very careful, and do not overwrite the wrong disk!


Find the Correct USB Device Name
There are two ways to find out the name of the USB flash drive. The first one is to compare the last lines of
the dmesg command output before and after plugging in the flash drive. The second way is to compare the
output of the lsblk command. Open a terminal and run:


```
# lsblk
Then plug in your USB flash drive and run the command again:

# lsblk
A new device will appear. This is the one you want to use. To be on the extra safe side check if the reported
size matches your USB flash drive.
```


### 2.2.3 Instructions for macOS


Open the terminal (query Terminal in Spotlight).
Convert the .iso file to .dmg format using the convert option of hdiutil, for example:

# hdiutil convert proxmox-ve_*.iso -format UDRW -o proxmox-ve_*.dmg


> **Tip:**
> macOS tends to automatically add .dmg to the output file name.


To get the current list of devices run the command:

# diskutil list
Now insert the USB flash drive and run this command again to determine which device node has been
assigned to it. (e.g., /dev/diskX).

# diskutil list
# diskutil unmountDisk /dev/diskX


> **Note:**
> replace X with the disk number from the last command.


# sudo dd if=proxmox-ve_*.dmg bs=1M of=/dev/rdiskX


> **Note:**
> rdiskX, instead of diskX, in the last command is intended. It will increase the write speed.


### 2.2.4 Instructions for Windows


Using Etcher
Etcher works out of the box. Download Etcher from https://etcher.io. It will guide you through the process of
selecting the ISO and your USB flash drive.

Using Rufus
Rufus is a more lightweight alternative, but you need to use the DD mode to make it work. Download Rufus
from https://rufus.ie/. Either install it or use the portable version. Select the destination drive and the Proxmox
VE ISO file.

> **Important:**
> Once you Start you have to click No on the dialog asking to download a different version of GRUB.
> In the next dialog select the DD mode.

## See also

- [Using the Installer and Advanced Options](ch02-installation-advanced.md)
- [Introduction and overview](ch01-introduction.md)
- [Host System Administration](ch03-host-admin/_index.md)
