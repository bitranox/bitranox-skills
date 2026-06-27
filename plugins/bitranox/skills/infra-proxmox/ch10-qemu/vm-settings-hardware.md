# VM Settings: Hardware

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

The removal policy is not yet in effect for Proxmox VE 8, so the baseline for supported machine versions is
2.4. The last QEMU binary version released for Proxmox VE 9 is expected to be QEMU 11.2. This QEMU
binary will remove support for machine versions older than 6.0, so 6.0 is the baseline for the Proxmox VE
9 release life cycle. The baseline is expected to increase by 2 major versions for each major Proxmox VE
release, for example 8.0 for Proxmox VE 10.

Update to a Newer Machine Version
If you see a deprecation warning, you should change the machine version to a newer one. Be sure to have
a working backup first and be prepared for changes to how the guest sees hardware. In some scenarios,
re-installing certain drivers might be required. You should also check for snapshots with RAM that were taken
with these machine versions (i.e. the runningmachine configuration entry). Unfortunately, there is no
way to change the machine version of a snapshot, so you’d need to load the snapshot to salvage any data
from it.


### 10.2.4 Hard Disk


Bus/Controller
QEMU can emulate a number of storage controllers:

> **Tip:**
> It is highly recommended to use the VirtIO SCSI or VirtIO Block controller for performance reasons and
> because they are better maintained.


- the IDE controller, has a design which goes back to the 1984 PC/AT disk controller. Even if this controller
has been superseded by recent designs, each and every OS you can think of has support for it, making
it a great choice if you want to run an OS released before 2003. You can connect up to 4 devices on this
controller.

- the SATA (Serial ATA) controller, dating from 2003, has a more modern design, allowing higher throughput
and a greater number of devices to be connected. You can connect up to 6 devices on this controller.

- the SCSI controller, designed in 1985, is commonly found on server grade hardware, and can connect up
to 14 storage devices. Proxmox VE emulates by default a LSI 53C895A controller.
A SCSI controller of type VirtIO SCSI single and enabling the IO Thread setting for the attached disks is
recommended if you aim for performance. This is the default for newly created Linux VMs since Proxmox
VE 7.3. Each disk will have its own VirtIO SCSI controller, and QEMU will handle the disks IO in a
dedicated thread. Linux distributions have support for this controller since 2012, and FreeBSD since 2014.
For Windows OSes, you need to provide an extra ISO containing the drivers during the installation.

- The VirtIO Block controller, often just called VirtIO or virtio-blk, is an older type of paravirtualized controller.
It has been superseded by the VirtIO SCSI Controller, in terms of features.


Image Format
On each controller you attach a number of emulated hard disks, which are backed by a file or a block device
residing in the configured storage. The choice of a storage type will determine the format of the hard disk
image. Storages which present block devices (LVM, ZFS, Ceph) will require the raw disk image format,
whereas files based storages (like Ext4, XFS, NFS, or CIFS) will let you to choose either the raw disk image
format or the QEMU image format.

- the QEMU image format is a copy on write format which allows snapshots, and thin provisioning of the
disk image.

- the raw disk image is a bit-to-bit image of a hard disk, similar to what you would get when executing the
dd command on a block device in Linux. This format does not support thin provisioning or snapshots by
itself, requiring cooperation from the storage layer for these tasks. It may, however, be up to 10% faster
than the QEMU image format. 1

- the VMware image format only makes sense if you intend to import/export the disk image to other hypervisors.
Cache Mode
Setting the Cache mode of the hard drive will impact how the host system will notify the guest systems of
block write completions. The No cache default means that the guest system will be notified that a write is
complete when each block reaches the physical storage write queue, ignoring the host page cache. This
provides a good balance between safety and speed.
If you want the Proxmox VE backup manager to skip a disk when doing a backup of a VM, you can set the
No backup option on that disk.
If you want the Proxmox VE storage replication mechanism to skip a disk when starting a replication job, you
can set the Skip replication option on that disk. As of Proxmox VE 5.0, replication requires the disk images
to be on a storage of type zfspool, so adding a disk image to other storages when the VM has replication
configured requires to skip replication for this disk image.
Trim/Discard
If your storage supports thin provisioning (see the storage chapter in the Proxmox VE guide), you can activate
the Discard option on a drive. With Discard set and a TRIM-enabled guest OS 2 , when the VM’s filesystem
marks blocks as unused after deleting files, the controller will relay this information to the storage, which will
then shrink the disk image accordingly. For the guest to be able to issue TRIM commands, you must enable
the Discard option on the drive. Some guest operating systems may also require the SSD Emulation flag
to be set. Note that Discard on VirtIO Block drives is only supported on guests using Linux Kernel 5.0 or
higher.
If you would like a drive to be presented to the guest as a solid-state drive rather than a rotational hard disk,
you can set the SSD emulation option on that drive. There is no requirement that the underlying storage
actually be backed by SSDs; this feature can be used with physical media of any type. Note that SSD
emulation is not supported on VirtIO Block drives.
1 See

this
benchmark
for
details
https://events.static.linuxfound.org/sites/events/files/slides/CloudOpen2013_Khoa_Huynh_v3.pdf
2 TRIM, UNMAP, and discard https://en.wikipedia.org/wiki/Trim_%28computing%29


IO Thread
The option IO Thread can only be used when using a disk with the VirtIO controller, or with the SCSI
controller, when the emulated controller type is VirtIO SCSI single. With IO Thread enabled, QEMU creates
one I/O thread per storage controller rather than handling all I/O in the main event loop or vCPU threads.
One benefit is better work distribution and utilization of the underlying storage. Another benefit is reduced
latency (hangs) in the guest for very I/O-intensive host workloads, since neither the main thread nor a vCPU
thread can be blocked by disk I/O.


## See also

- [VM CPU and Memory Settings](vm-cpu-memory.md)
- [VM Memory Encryption and Display](vm-memory-encryption-display.md)
- [VM USB, Audio, PCI and Boot Options](vm-usb-pci-boot.md)
- [QEMU/KVM Overview](_index.md)
