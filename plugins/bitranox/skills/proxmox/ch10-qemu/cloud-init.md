# Cloud-Init Support

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

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


### 10.8.2 Deploying Cloud-Init Templates


You can easily deploy such a template by cloning:


```
qm clone 9000 123 --name ubuntu2
```

Then configure the SSH public key used for authentication, and configure the IP setup:


```
qm set 123 --sshkey ~/.ssh/id_rsa.pub
```


```
qm set 123 --ipconfig0 ip=10.0.10.123/24,gw=10.0.10.1
```

You can also configure all the Cloud-Init options using a single command only. We have simply split the
above example to separate the commands for reducing the line length. Also make sure to adopt the IP setup
for your specific environment.


### 10.8.3 Custom Cloud-Init Configuration


The Cloud-Init integration also allows custom config files to be used instead of the automatically generated
configs. This is done via the cicustom option on the command line:


```
qm set 9000 --cicustom "user=<volume>,network=<volume>,meta=<volume>"
```

The custom config files have to be on a storage that supports snippets and have to be available on all nodes
the VM is going to be migrated to. Otherwise the VM won’t be able to start. For example:


```
qm set 9000 --cicustom "user=local:snippets/userconfig.yaml"
```

There are three kinds of configs for Cloud-Init. The first one is the user config as seen in the example above.
The second is the network config and the third the meta config. They can all be specified together or
mixed and matched however needed. The automatically generated config will be used for any that don’t have
a custom config file specified.
The generated config can be dumped to serve as a base for custom configs:


```
qm cloudinit dump 9000 user
```

The same command exists for network and meta.


### 10.8.4 Cloud-Init on Windows


There is a reimplementation of Cloud-Init available for Windows called cloudbase-init. Not every feature of
Cloud-Init is available with Cloudbase-Init, and some features differ compared to Cloud-Init.
Cloudbase-Init requires both ostype set to any Windows version and the citype set to configdrive2,
which is the default with any Windows ostype.
There are no ready-made cloud images for Windows available for free. Using Cloudbase-Init requires manually installing and configuring a Windows guest.


### 10.8.5 Preparing Cloudbase-Init Templates


The first step is to install Windows in a VM. Download and install Cloudbase-Init in the guest. It may be
necessary to install the Beta version. Don’t run Sysprep at the end of the installation. Instead configure
Cloudbase-Init first.
A few common options to set would be:

- username: This sets the username of the administrator
- groups: This allows one to add the user to the Administrators group
- inject_user_password: Set this to true to allow setting the password in the VM config
- first_logon_behaviour : Set this to no to not require a new password on login
- rename_admin_user : Set this to true to allow renaming the default Administrator user to the
username specified with username

- metadata_services: Set this to cloudbaseinit.metadata.services.configdrive.ConfigDriv
for Cloudbase-Init to first check this service. Otherwise it may take a few minutes for Cloudbase-Init to configure the system after boot.
Some plugins, for example the SetHostnamePlugin, require reboots and will do so automatically. To disable
automatic reboots by Cloudbase-Init, you can set allow_reboot to false.
A full set of configuration options can be found in the official cloudbase-init documentation.
It can make sense to make a snapshot after configuring in case some parts of the config still need adjustments. After configuring Cloudbase-Init you can start creating the template. Shutdown the Windows guest,
add a Cloud-Init disk and make it into a template.


```
qm set 9000 --ide2 local-lvm:cloudinit
```


```
qm template 9000
```

Clone the template into a new VM:


```
qm clone 9000 123 --name windows123
```

Then set the password, network config and SSH key:


```
qm set 123 --cipassword <password>
```


```
qm set 123 --ipconfig0 ip=10.0.10.123/24,gw=10.0.10.1
```


```
qm set 123 --sshkey ~/.ssh/id_rsa.pub
```


Make sure that the ostype is set to any Windows version before setting the password. Otherwise the
password will be encrypted and Cloudbase-Init will use the encrypted password as plaintext password.
When everything is set, start the cloned guest. On the first boot the login won’t work and it will reboot
automatically for the changed hostname. After the reboot the new password should be set and login should
work.


### 10.8.6 Cloudbase-Init and Sysprep


Sysprep is a feature to reset the configuration of Windows and provide a new system. This can be used in
conjunction with Cloudbase-Init to create a clean template.
When using Sysprep there are 2 configuration files that need to be adapted. The first one is the normal
configuration file, the second one is the one ending in -unattend.conf.
Cloudbase-Init runs in 2 steps, first the Sysprep step using the -unattend.conf and then the regular
step using the primary config file.
For Windows Server running Sysprep with the provided Unattend.xml file should work out of the
box. Normal Windows versions however require additional steps:
1. Open a PowerShell instance
2. Enable the Administrator user:

net user Administrator /active:yes `
3. Install Cloudbase-Init using the Administrator user
4. Modify Unattend.xml to include the command to enable the Administrator user on the first boot
after sysprepping:

<RunSynchronousCommand wcm:action="add">
<Path>net user administrator /active:yes</Path>
<Order>1</Order>
<Description>Enable Administrator User</Description>
</RunSynchronousCommand>
Make sure the <Order> does not conflict with other synchronous commands. Modify <Order>
of the Cloudbase-Init command to run after this one by increasing the number to a higher value:

<Order>2</Order>
5. (Windows 11 only) Remove the conflicting Microsoft.OneDriveSync package:

Get-AppxPackage -AllUsers Microsoft.OneDriveSync | Remove-AppxPackage
-AllUsers
6. cd into the Cloudbase-Init config directory:

cd 'C:\Program Files\Cloudbase Solutions\Cloudbase-Init\conf'
7. (optional) Create a snapshot of the VM before Sysprep in case of a misconfiguration
8. Run Sysprep:

←-


C:\Windows\System32\Sysprep\sysprep.exe /generalize /oobe /unattend: ←Unattend.xml

After following the above steps the VM should be in shut down state due to the Sysprep. Now you can make
it into a template, clone it and configure it as needed.


### 10.8.7 Cloud-Init specific Options


cicustom: [meta=<volume>] [,network=<volume>] [,user=<volume>]
[,vendor=<volume>]
Specify custom files to replace the automatically generated ones at start.

meta=<volume>
Specify a custom file containing all meta data passed to the VM via cloud-init. This is provider
specific meaning configdrive2 and nocloud differ.

network=<volume>
To pass a custom file containing all network data to the VM via cloud-init.

user=<volume>
To pass a custom file containing all user data to the VM via cloud-init.

vendor=<volume>
To pass a custom file containing all vendor data to the VM via cloud-init.

cipassword: <string>
Password to assign the user. Using this is generally not recommended. Use ssh keys instead. Also
note that older cloud-init versions do not support hashed passwords.

citype: <configdrive2 | nocloud | opennebula>
Specifies the cloud-init configuration format. The default depends on the configured operating system
type (ostype. We use the nocloud format for Linux, and configdrive2 for windows.

ciupgrade: <boolean> (default = 1)
do an automatic package upgrade after the first boot.

ciuser: <string>
User name to change ssh keys and password for instead of the image’s configured default user.

ipconfig[n]: [gw=<GatewayIPv4>] [,gw6=<GatewayIPv6>]
[,ip=<IPv4Format/CIDR>] [,ip6=<IPv6Format/CIDR>]
Specify IP addresses and gateways for the corresponding interface.
IP addresses use CIDR notation, gateways are optional but need an IP of the same type specified.


The special string dhcp can be used for IP addresses to use DHCP, in which case no explicit gateway
should be provided. For IPv6 the special string auto can be used to use stateless autoconfiguration.
This requires cloud-init 19.4 or newer.
If cloud-init is enabled and neither an IPv4 nor an IPv6 address is specified, it defaults to using dhcp
on IPv4.

gw=<GatewayIPv4>
Default gateway for IPv4 traffic.

> **Note:**
> Requires option(s): ip


gw6=<GatewayIPv6>
Default gateway for IPv6 traffic.

> **Note:**
> Requires option(s): ip6


ip=<IPv4Format/CIDR> (default = dhcp)
IPv4 address in CIDR format.

ip6=<IPv6Format/CIDR> (default = dhcp)
IPv6 address in CIDR format.

nameserver: <string>
Sets DNS server IP address for a container. Create will automatically use the setting from the host if
neither searchdomain nor nameserver are set.

searchdomain: <string>
Sets DNS search domains for a container. Create will automatically use the setting from the host if
neither searchdomain nor nameserver are set.

sshkeys: <string>
Setup public SSH keys (one key per line, OpenSSH format).


## 10.9 PCI(e) Passthrough


PCI(e) passthrough is a mechanism to give a virtual machine control over a PCI device from the host. This
can have some advantages over using virtualized hardware, for example lower latency, higher performance,
or more features (e.g., offloading).
But, if you pass through a device to a virtual machine, you cannot use that device anymore on the host or in
any other VM.
Note that, while PCI passthrough is available for i440fx and q35 machines, PCIe passthrough is only available
on q35 machines. This does not mean that PCIe capable devices that are passed through as PCI devices


will only run at PCI speeds. Passing through devices as PCIe just sets a flag for the guest to tell it that the
device is a PCIe device instead of a "really fast legacy PCI device". Some guest applications benefit from
this.


### 10.9.1 General Requirements


Since passthrough is performed on real hardware, it needs to fulfill some requirements. A brief overview of
these requirements is given below, for more information on specific devices, see PCI Passthrough Examples.

Hardware
Your hardware needs to support IOMMU (I/O Memory Management Unit) interrupt remapping, this includes
the CPU and the motherboard.
Generally, Intel systems with VT-d and AMD systems with AMD-Vi support this. But it is not guaranteed that
everything will work out of the box, due to bad hardware implementation and missing or low quality drivers.
Further, server grade hardware has often better support than consumer grade hardware, but even then,
many modern system can support this.
Please refer to your hardware vendor to check if they support this feature under Linux for your specific setup.

Determining PCI Card Address
The easiest way is to use the GUI to add a device of type "Host PCI" in the VM’s hardware tab. Alternatively,
you can use the command line.
You can locate your card using

lspci

Configuration
Once you ensured that your hardware supports passthrough, you will need to do some configuration to
enable PCI(e) passthrough.

IOMMU
You will have to enable IOMMU support in your BIOS/UEFI. Usually the corresponding setting is called
IOMMU or VT-d, but you should find the exact option name in the manual of your motherboard.
With AMD CPUs IOMMU is enabled by default. With recent kernels (6.8 or newer), this is also true for Intel
CPUs. On older kernels, it is necessary to enable it on Intel CPUs via the kernel command line by adding:

intel_iommu=on


IOMMU Passthrough Mode
If your hardware supports IOMMU passthrough mode, enabling this mode might increase performance. This
is because VMs then bypass the (default) DMA translation normally performed by the hyper-visor and instead
pass DMA requests directly to the hardware IOMMU. To enable these options, add:

iommu=pt
to the kernel commandline.
Kernel Modules
You have to make sure the following modules are loaded. This can be achieved by adding them to ‘/etc/modules’.
Mediated devices passthrough
If passing through mediated devices (e.g. vGPUs), the following is not needed. In these cases, the device
will be owned by the appropriate host-driver directly.

vfio
vfio_iommu_type1
vfio_pci
After changing anything modules related, you need to refresh your initramfs. On Proxmox VE this can
be done by executing:

# update-initramfs -u -k all
To check if the modules are being loaded, the output of


```
# lsmod | grep vfio
should include the four modules from above.
Finish Configuration
Finally reboot to bring the changes into effect and check that it is indeed enabled.

# dmesg | grep -e DMAR -e IOMMU -e AMD-Vi
should display that IOMMU, Directed I/O or Interrupt Remapping is enabled, depending on
hardware and kernel the exact message can vary.
For notes on how to troubleshoot or verify if IOMMU is working as intended, please see the Verifying IOMMU
Parameters section in our wiki.
It is also important that the device(s) you want to pass through are in a separate IOMMU group. This can be
checked with a call to the Proxmox VE API:

# pvesh get /nodes/{nodename}/hardware/pci --pci-class-blacklist ""
It is okay if the device is in an IOMMU group together with its functions (e.g. a GPU with the HDMI Audio
device) or with its root port or PCI(e) bridge.
```

