# Importing Virtual Machines

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Select one and use the Import button (or double-click) to open the import wizard. You can modify a subset of the available options here and then start the import. Please note that you can do more advanced
modifications after the import finished.

> **Tip:**
> The ESXi import wizard has been tested with ESXi versions 6.5 through 8.0. Note that guests using vSAN
> storage cannot be directly imported directly; their disks must first be moved to another storage. While it
> is possible to use a vCenter as the import source, performance is dramatically degraded (5 to 10 times
> slower).


For a step-by-step guide and tips for how to adapt the virtual guest to the new hyper-visor see our migrate to
Proxmox VE wiki article.
OVA/OVF Import
To import OVA/OVF files, you first need a File-based storage with the import content type. On this storage,
there will be an import folder where you can put OVA files or OVF files with the corresponding images in a
flat structure. Alternatively you can use the web UI to upload or download OVA files directly. You can then
use the web UI to select those and use the import wizard to import the guests.
For OVA files, there is additional space needed to temporarily extract the image. This needs a file-based
storage that has the images content type configured. By default the source storage is selected for this, but
you can specify a Import Working Storage on which the images will be extracted before importing to the
actual target storage.


> **Note:**
> Since OVA/OVF file structure and content are not always well maintained or defined, it might be necessary
> to adapt some guest settings manually. For example the SCSI controller type is almost never defined
> in OVA/OVF files, but the default is unbootable with OVMF (UEFI), so you should select Virtio SCSI or
> VMware PVSCSI for these cases.


### 10.7.2 Import OVF/OVA Through CLI


A VM export from a foreign hypervisor takes usually the form of one or more disk images, with a configuration
file describing the settings of the VM (RAM, number of cores).
The disk images can be in the vmdk format, if the disks come from VMware or VirtualBox, or qcow2 if
the disks come from a KVM hypervisor. The most popular configuration format for VM exports is the OVF
standard, but in practice interoperation is limited because many settings are not implemented in the standard
itself, and hypervisors export the supplementary information in non-standard extensions.
Besides the problem of format, importing disk images from other hypervisors may fail if the emulated hardware changes too much from one hypervisor to another. Windows VMs are particularly concerned by this,
as the OS is very picky about any changes of hardware. This problem may be solved by installing the
MergeIDE.zip utility available from the Internet before exporting and choosing a hard disk type of IDE before
booting the imported Windows VM.
Finally there is the question of paravirtualized drivers, which improve the speed of the emulated system and
are specific to the hypervisor. GNU/Linux and other free Unix OSes have all the necessary drivers installed
by default and you can switch to the paravirtualized drivers right after importing the VM. For Windows VMs,
you need to install the Windows paravirtualized drivers by yourself.
GNU/Linux and other free Unix can usually be imported without hassle. Note that we cannot guarantee a
successful import/export of Windows VMs in all cases due to the problems above.

Step-by-step example of a Windows OVF import
Microsoft provides Virtual Machines downloads to get started with Windows development.We are going to
use one of these to demonstrate the OVF import feature.

Download the Virtual Machine zip
After getting informed about the user agreement, choose the Windows 10 Enterprise (Evaluation - Build) for
the VMware platform, and download the zip.

Extract the disk image from the zip
Using the unzip utility or any archiver of your choice, unpack the zip, and copy via ssh/scp the ovf and
vmdk files to your Proxmox VE host.

Import the Virtual Machine
This will create a new virtual machine, using cores, memory and VM name as read from the OVF manifest,
and import the disks to the local-lvm storage. You have to configure the network manually.


```
# qm importovf 999 WinDev1709Eval.ovf local-lvm
The VM is ready to be started.
```


Adding an external disk image to a Virtual Machine
You can also add an existing disk image to a VM, either coming from a foreign hypervisor, or one that you
created yourself.
Suppose you created a Debian/Ubuntu disk image with the vmdebootstrap tool:

vmdebootstrap --verbose \
- `--size` 10GiB --serial-console \
- `--grub` --no-extlinux \
- `--package` openssh-server \
- `--package` avahi-daemon \
- `--package` qemu-guest-agent \
- `--hostname` vm600 --enable-dhcp \
--customize=./copy_pub_ssh.sh \
- `--sparse` --image vm600.raw
You can now create a new target VM, importing the image to the storage pvedir and attaching it to the
VM’s SCSI controller:


```
# qm create 600 --net0 virtio,bridge=vmbr0 --name vm600 --serial0 socket \
--boot order=scsi0 --scsihw virtio-scsi-pci --ostype l26 \
--scsi0 pvedir:0,import-from=/path/to/dir/vm600.raw
The VM is ready to be started.
```


## 10.8 Cloud-Init Support


Cloud-Init is the de facto multi-distribution package that handles early initialization of a virtual machine instance. Using Cloud-Init, configuration of network devices and ssh keys on the hypervisor side is possible.
When the VM starts for the first time, the Cloud-Init software inside the VM will apply those settings.
Many Linux distributions provide ready-to-use Cloud-Init images, mostly designed for OpenStack. These
images will also work with Proxmox VE. While it may seem convenient to get such ready-to-use images, we
usually recommended to prepare the images by yourself. The advantage is that you will know exactly what
you have installed, and this helps you later to easily customize the image for your needs.
Once you have created such a Cloud-Init image we recommend to convert it into a VM template. From a VM
template you can quickly create linked clones, so this is a fast method to roll out new VM instances. You just
need to configure the network (and maybe the ssh keys) before you start the new VM.
We recommend using SSH key-based authentication to login to the VMs provisioned by Cloud-Init. It is also
possible to set a password, but this is not as safe as using SSH key-based authentication because Proxmox
VE needs to store an encrypted version of that password inside the Cloud-Init data.
Proxmox VE generates an ISO image to pass the Cloud-Init data to the VM. For that purpose, all Cloud-Init
VMs need to have an assigned CD-ROM drive. Usually, a serial console should be added and used as


a display. Many Cloud-Init images rely on this, it is a requirement for OpenStack. However, other images
might have problems with this configuration. Switch back to the default display configuration if using a serial
console doesn’t work.


### 10.8.1 Preparing Cloud-Init Templates


The first step is to prepare your VM. Basically you can use any VM. Simply install the Cloud-Init packages
inside the VM that you want to prepare. On Debian/Ubuntu based systems this is as simple as:

apt-get install cloud-init


> **Warning:**
> This command is not intended to be executed on the Proxmox VE host, but only inside the VM.


Already many distributions provide ready-to-use Cloud-Init images (provided as .qcow2 files), so alternatively you can simply download and import such images. For the following example, we will use the cloud
image provided by Ubuntu at https://cloud-images.ubuntu.com.

# download the image
wget https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg- ←amd64.img
# create a new VM with VirtIO SCSI controller

```
qm create 9000 --memory 2048 --net0 virtio,bridge=vmbr0 --scsihw virtio- ←scsi-pci
```

# import the downloaded disk to the local-lvm storage, attaching it as a ←SCSI drive

```
qm set 9000 --scsi0 local-lvm:0,import-from=/path/to/bionic-server-cloudimg ←-amd64.img
```


> **Note:**
> Ubuntu Cloud-Init images require the virtio-scsi-pci controller type for SCSI drives.


Add Cloud-Init CD-ROM drive

The next step is to configure a CD-ROM drive, which will be used to pass the Cloud-Init data to the VM.


```
qm set 9000 --ide2 local-lvm:cloudinit
```

To be able to boot directly from the Cloud-Init image, set the boot parameter to order=scsi0 to restrict
BIOS to boot from this disk only. This will speed up booting, because VM BIOS skips the testing for a
bootable CD-ROM.


```
qm set 9000 --boot order=scsi0
```

For many Cloud-Init images, it is required to configure a serial console and use it as a display. If the configuration doesn’t work for a given image however, switch back to the default display instead.


```
qm set 9000 --serial0 socket --vga serial0
```

In a last step, it is helpful to convert the VM into a template. From this template you can then quickly create
linked clones. The deployment from VM templates is much faster than creating a full clone (copy).


```
qm template 9000
```

