# VM Memory Encryption and Display

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 10.2.7 Memory Encryption


AMD SEV
SEV (Secure Encrypted Virtualization) enables memory encryption per VM using AES-128 encryption and
the AMD Secure Processor.
SEV-ES (Secure Encrypted Virtualization - Encrypted State) in addition encrypts all CPU register contents,
to prevent leakage of information to the hypervisor.
SEV-SNP (Secure Encrypted Virtualization - Secure Nested Paging) also attempts to prevent software-based
integrity attacks. See the AMD SEV SNP white paper for more information.
Host Requirements:

- AMD EPYC CPU
- SEV-ES is only supported on AMD EPYC 7002 series and newer EPYC CPUs
- SEV-SNP is only supported on AMD EPYC 7003 series and newer EPYC CPUs
- SEV-SNP requires host kernel version 6.11 or higher.
- configure AMD memory encryption in the BIOS settings of the host machine
- add "kvm_amd.sev=1" to kernel parameters if not enabled by default
- add "mem_encrypt=on" to kernel parameters if you want to encrypt memory on the host (SME) see
https://www.kernel.org/doc/Documentation/x86/amd-memory-encryption.txt

- maybe increase SWIOTLB see https://github.com/AMDESE/AMDSEV#faq-4
To check if SEV is enabled on the host search for sev in dmesg and print out the SEV kernel parameter of
kvm_amd:

# dmesg | grep -i sev
[...] ccp 0000:45:00.1: sev enabled
[...] ccp 0000:45:00.1: SEV API: <buildversion>
[...] SEV supported: <number> ASIDs
[...] SEV-ES supported: <number> ASIDs

```
# cat /sys/module/kvm_amd/parameters/sev
Y
Guest Requirements:
```


- edk2-OVMF
- advisable to use Q35
- The guest operating system must contain SEV-support.
Limitations:

- Because the memory is encrypted the memory usage on host is always wrong.
- Operations that involve saving or restoring memory like snapshots & live migration do not work yet or are
attackable.

- PCI passthrough is not supported.
- SEV-ES & SEV-SNP are very experimental.
- EFI disks are not supported with SEV-SNP.
- With SEV-SNP, the reboot command inside a VM simply shuts down the VM.
Example Configuration (SEV):


```
# qm set <vmid> -amd-sev type=std,no-debug=1,no-key-sharing=1,kernel-hashes ←=1
The type defines the encryption technology ("type=" is not necessary). Available options are std, es & snp.
The QEMU policy parameter gets calculated with the no-debug and no-key-sharing parameters. These
parameters correspond to policy-bit 0 and 1. If type is es the policy-bit 2 is set to 1 so that SEV-ES is
enabled. Policy-bit 3 (nosend) is always set to 1 to prevent migration-attacks. For more information on how
to calculate the policy see: AMD SEV API Specification Chapter 3
The kernel-hashes option is off per default for backward compatibility with older OVMF images and guests
that do not measure the kernel/initrd. See https://lists.gnu.org/archive/html/qemu-devel/2021-11/msg02598.html
Check if SEV is working in the VM
Method 1 - dmesg:
Output should look like this.

# dmesg | grep -i sev
AMD Memory Encryption Features active: SEV
Method 2 - MSR 0xc0010131 (MSR_AMD64_SEV):
Output should be 1.

# apt install msr-tools
# modprobe msr
# rdmsr -a 0xc0010131
1
Example Configuration (SEV-SNP):

# qm set <vmid> -amd-sev type=snp,allow-smt=1,no-debug=1,kernel-hashes=1
```


The allow-smt policy-bit is set by default. If you disable it by setting allow-smt to 0, SMT must be
disabled on the host in order for the VM to run.
Check if SEV-SNP is working in the VM

# dmesg | grep -i snp
Memory Encryption Features active: AMD SEV SEV-ES SEV-SNP
SEV: Using SNP CPUID table, 29 entries present.
SEV: SNP guest platform device initialized.
Links:

- https://developer.amd.com/sev/
- https://github.com/AMDESE/AMDSEV
- https://www.qemu.org/docs/master/system/i386/amd-memory-encryption.html
- https://www.amd.com/system/files/TechDocs/55766_SEV-KM_API_Specification.pdf
- https://documentation.suse.com/sles/15-SP1/html/SLES-amd-sev/index.html
- SEV Secure Nested Paging Firmware ABI Specification


### 10.2.8 Network Device


Each VM can have many Network interface controllers (NIC), of four different types:

- Intel E1000 is the default, and emulates an Intel Gigabit network card.
- the VirtIO paravirtualized NIC should be used if you aim for maximum performance. Like all VirtIO devices,
the guest OS should have the proper driver installed.

- the Realtek 8139 emulates an older 100 MB/s network card, and should only be used when emulating
older operating systems ( released before 2002 )


- the vmxnet3 is another paravirtualized device, which should only be used when importing a VM from
another hypervisor.
Proxmox VE will generate for each NIC a random MAC address, so that your VM is addressable on Ethernet
networks.
The NIC you added to the VM can follow one of two different models:

- in the default Bridged mode each virtual NIC is backed on the host by a tap device, ( a software loopback
device simulating an Ethernet NIC ). This tap device is added to a bridge, by default vmbr0 in Proxmox VE.
In this mode, VMs have direct access to the Ethernet LAN on which the host is located.

- in the alternative NAT mode, each virtual NIC will only communicate with the QEMU user networking
stack, where a built-in router and DHCP server can provide network access. This built-in DHCP will serve
addresses in the private 10.0.2.0/24 range. The NAT mode is much slower than the bridged mode, and
should only be used for testing. This mode is only available via CLI or the API, but not via the web UI.
You can also skip adding a network device when creating a VM by selecting No network device.
You can overwrite the MTU setting for each VM network device manually. Leaving the field empty or setting
mtu=1 will inherit the MTU from the underlying bridge. This option is only available for VirtIO network
devices.

Multiqueue
If you are using the VirtIO driver, you can optionally activate the Multiqueue option. This option allows
the guest OS to process networking packets using multiple virtual CPUs, providing an increase in the total
number of packets transferred.
When using the VirtIO driver with Proxmox VE, each NIC network queue is passed to the host kernel, where
the queue will be processed by a kernel thread spawned by the vhost driver. With this option activated, it is
possible to pass multiple network queues to the host kernel for each NIC.
When using Multiqueue, it is recommended to set it to a value equal to the number of vCPUs of your guest.
Remember that the number of vCPUs is the number of sockets times the number of cores configured for
the VM. You also need to set the number of multi-purpose channels on each VirtIO NIC in the VM with this
ethtool command:

ethtool -L ens1 combined X
where X is the number of the number of vCPUs of the VM.
To configure a Windows guest for Multiqueue install the Redhat VirtIO Ethernet Adapter drivers, then adapt
the NIC’s configuration as follows. Open the device manager, right click the NIC under "Network adapters",
and select "Properties". Then open the "Advanced" tab and select "Receive Side Scaling" from the list on
the left. Make sure it is set to "Enabled". Next, navigate to "Maximum number of RSS Queues" in the list
and set it to the number of vCPUs of your VM. Once you verified that the settings are correct, click "OK" to
confirm them.
You should note that setting the Multiqueue parameter to a value greater than one will increase the CPU
load on the host and guest systems as the traffic increases. We recommend to set this option only when the
VM has to process a great number of incoming connections, such as when the VM is running as a router,
reverse proxy or a busy HTTP server doing long polling.


### 10.2.9 Display


QEMU can virtualize a few types of VGA hardware. Some examples are:

- std, the default, emulates a card with Bochs VBE extensions.
- cirrus, this was once the default, it emulates a very old hardware module with all its problems. This display
type should only be used if really necessary 9 , for example, if using Windows XP or earlier

- vmware, is a VMWare SVGA-II compatible adapter.
- qxl, is the QXL paravirtualized graphics card. Selecting this also enables SPICE (a remote viewer protocol)
for the VM.

- virtio-gl, often named VirGL is a virtual 3D GPU for use inside VMs that can offload workloads to the
host GPU without requiring special (expensive) models and drivers and neither binding the host GPU
completely, allowing reuse between multiple guests and or the host.

> **Note:**
> VirGL support needs some extra libraries that aren’t installed by default due to being relatively big and
> also not available as open source for all GPU models/vendors. For most setups you’ll just need to do:


apt install libgl1 libegl1

You can edit the amount of memory given to the virtual GPU, by setting the memory option. This can enable
higher resolutions inside the VM, especially with SPICE/QXL.
As the memory is reserved by display device, selecting Multi-Monitor mode for SPICE (such as qxl2 for
dual monitors) has some implications:

- Windows needs a device for each monitor, so if your ostype is some version of Windows, Proxmox VE
gives the VM an extra device per monitor. Each device gets the specified amount of memory.

- Linux VMs, can always enable more virtual monitors, but selecting a Multi-Monitor mode multiplies the
memory given to the device with the number of monitors.
Selecting serialX as display type disables the VGA output, and redirects the Web Console to the selected
serial port. A configured display memory setting will be ignored in that case.
VNC clipboard
You can enable the VNC clipboard by setting clipboard to vnc.


```
# qm set <vmid> -vga <displaytype>,clipboard=vnc
In order to use the clipboard feature, you must first install the SPICE guest tools. On Debian-based distributions, this can be achieved by installing spice-vdagent. For other Operating Systems search for it in the
official repositories or see: https://www.spice-space.org/download.html
Once you have installed the spice guest tools, you can use the VNC clipboard function (e.g. in the noVNC
console panel). However, if you’re using SPICE, virtio or virgl, you’ll need to choose which clipboard to use.
This is because the default SPICE clipboard will be replaced by the VNC clipboard, if clipboard is set to
vnc.
9 https://www.kraxel.org/blog/2014/10/qemu-using-cirrus-considered-harmful/ qemu: using cirrus considered harmful
```


> **Note:**
> In order to enable the VNC clipboard, QEMU is configured to use the qemu-vdagent device. Currently,
> the qemu-vdagent device does not support live migration. This means that a VM with an enabled VNC
> clipboard cannot be live-migrated at the moment.


## See also

- [VM Settings: Hardware](vm-settings-hardware.md)
- [VM CPU and Memory Settings](vm-cpu-memory.md)
- [VM USB, Audio, PCI and Boot Options](vm-usb-pci-boot.md)
- [QEMU/KVM Overview](_index.md)
