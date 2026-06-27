# Backup and Restore

*[Main Index](../SKILL.md)*


Backups are a requirement for any sensible IT deployment, and Proxmox VE provides a fully integrated solution, using the capabilities of each storage and each guest system type. This allows the system administrator
to fine tune via the mode option between consistency of the backups and downtime of the guest system.
Proxmox VE backups are always full backups - containing the VM/CT configuration and all data. Backups
can be started via the GUI or via the vzdump command-line tool.

Backup Storage
Before a backup can run, a backup storage must be defined. Refer to the storage documentation on how
to add a storage. It can either be a Proxmox Backup Server storage, where backups are stored as deduplicated chunks and metadata, or a file-level storage, where backups are stored as regular files. Using
Proxmox Backup Server on a dedicated host is recommended, because of its advanced features. Using an
NFS server is a good alternative. In both cases, you might want to save those backups later to a tape drive,
for off-site archiving.

Scheduled Backup
Backup jobs can be scheduled so that they are executed automatically on specific days and times, for
selectable nodes and guest systems. See the Backup Jobs section for more.


## 16.1 Backup Modes


There are several ways to provide consistency (option mode), depending on the guest type.

BACKUP MODES FOR VM S :

stop mode
This mode provides the highest consistency of the backup, at the cost of a short downtime in the VM
operation. It works by executing an orderly shutdown of the VM, and then runs a background QEMU
process to backup the VM data. After the backup is started, the VM goes to full operation mode if it
was previously running. Consistency is guaranteed by using the live backup feature.


suspend mode
This mode is provided for compatibility reason, and suspends the VM before calling the snapshot
mode. Since suspending the VM results in a longer downtime and does not necessarily improve the
data consistency, the use of the snapshot mode is recommended instead.

snapshot mode
This mode provides the lowest operation downtime, at the cost of a small inconsistency risk. It works
by performing a Proxmox VE live backup, in which data blocks are copied while the VM is running. If
the guest agent is enabled (agent: 1) and running, it calls guest-fsfreeze-freeze and
guest-fsfreeze-thaw to improve consistency.

> **Note:**
> On Windows guests it is necessary to configure the guest agent if another backup software is used
> within the guest. See Freeze & Thaw in the guest agent section for more details.


A technical overview of the Proxmox VE live backup for QemuServer can be found online here.

> **Note:**
> Proxmox VE live backup provides snapshot-like semantics on any storage type. It does not require that
> the underlying storage supports snapshots. Also please note that since the backups are done via a
> background QEMU process, a stopped VM will appear as running for a short amount of time while the VM
> disks are being read by QEMU. However the VM itself is not booted, only its disk(s) are read.


BACKUP MODES FOR C ONTAINERS :

stop mode
Stop the container for the duration of the backup. This potentially results in a very long downtime.

suspend mode
This mode uses rsync to copy the container data to a temporary location (see option --tmpdir).
Then the container is suspended and a second rsync copies changed files. After that, the container
is started (resumed) again. This results in minimal downtime, but needs additional space to hold the
container copy.
When the container is on a local file system and the target storage of the backup is an NFS/CIFS
server, you should set --tmpdir to reside on a local file system too, as this will result in a many
fold performance improvement. Use of a local tmpdir is also required if you want to backup a local
container using ACLs in suspend mode if the backup storage is an NFS server.

snapshot mode
This mode uses the snapshotting facilities of the underlying storage. First, the container will be suspended to ensure data consistency. A temporary snapshot of the container’s volumes will be made
and the snapshot content will be archived in a tar file. Finally, the temporary snapshot is deleted again.


> **Note:**


snapshot mode requires that all backed up volumes are on a storage that supports snapshots. Using
the backup=no mount point option individual volumes can be excluded from the backup (and thus this
requirement).


> **Note:**
> By default additional mount points besides the Root Disk mount point are not included in backups. For
> volume mount points you can set the Backup option to include the mount point in the backup. Device and
> bind mounts are never backed up as their content is managed outside the Proxmox VE storage library.


### 16.1.1 VM Backup Fleecing


When a backup for a VM is started, QEMU will install a "copy-before-write" filter in its block layer. This filter
ensures that upon new guest writes, old data still needed for the backup is sent to the backup target first.
The guest write blocks until this operation is finished so guest IO to not-yet-backed-up sectors will be limited
by the speed of the backup target.
With backup fleecing, such old data is cached in a fleecing image rather than sent directly to the backup
target. This can help guest IO performance and even prevent hangs in certain scenarios, at the cost of
requiring more storage space.
To manually start a backup of VM 123 with fleecing images created on the storage local-lvm, run


```
vzdump 123 --fleecing enabled=1,storage=local-lvm
```

As always, you can set the option for specific backup jobs, or as a node-wide fallback via the configuration
options. In the UI, fleecing can be configured in the Advanced tab when editing a backup job.
The fleecing storage should be a fast local storage, with thin provisioning and discard support. Examples
are LVM-thin, RBD, ZFS with sparse 1 in the storage configuration, many file-based storages. Ideally, the
fleecing storage is a dedicated storage, so it running full will not affect other guests and just fail the backup.
Parts of the fleecing image that have been backed up will be discarded to try and keep the space usage low.
For file-based storages that do not support discard (for example, NFS before version 4.2), you should set
preallocation off in the storage configuration. In combination with qcow2 (used automatically as
the format for the fleecing image when the storage supports it), this has the advantage that already allocated
parts of the image can be re-used later, which can still help save quite a bit of space.

> **Warning:**
> On a storage that’s not thinly provisioned, for example, LVM or ZFS without the sparse option,
> the full size of the original disk needs to be reserved for the fleecing image up-front. On a thinly
> provisioned storage, the fleecing image can grow to the same size as the original image only if the
> guest re-writes a whole disk while the backup is busy with another disk.


### 16.1.2 CT Change Detection Mode


Setting the change detection mode defines the encoding format for the pxar archives and how changed, and
unchanged files are handled for container backups with Proxmox Backup Server as the target.


The change detection mode option can be configured for individual backup jobs in the Advanced tab while
editing a job. Further, this option can be set as node-wide fallback via the configuration options.
There are 3 change detection modes available:
Mode

Default
Data
Metadata

Description
Read and encode all files into a single archive, using the pxar format version 1.
Read and encode all files, but split data and metadata into separate streams,
using the pxar format version 2.
Split streams and use archive format version 2 like Data, but use the metadata
archive of the previous snapshot (if one exists) to detect unchanged files, and
reuse their data chunks without reading file contents from disk, whenever
possible.

To perform a backup using the change detecation mode metadata you can run


```
vzdump 123 --storage pbs-storage --pbs-change-detection-mode
```

metadata

←-


> **Note:**
> Backups of VMs or to storage backends other than Proxmox Backup Server are not affected by this setting.


## 16.2 Backup File Names


Newer versions of vzdump encode the guest type and the backup time into the filename, for example

vzdump-lxc-105-2009_10_09-11_04_43.tar
That way it is possible to store several backup in the same directory. You can limit the number of backups
that are kept with various retention options, see the Backup Retention section below.


## 16.3 Backup File Compression


The backup file can be compressed with one of the following algorithms: lzo 1 , gzip 2 or zstd 3 .
Currently, Zstandard (zstd) is the fastest of these three algorithms. Multi-threading is another advantage of
zstd over lzo and gzip. Lzo and gzip are more widely used and often installed by default.
You can install pigz 4 as a drop-in replacement for gzip to provide better performance due to multi-threading.
For pigz & zstd, the amount of threads/cores can be adjusted. See the configuration options below.
The extension of the backup file name can usually be used to determine which compression algorithm has
been used to create the backup.
1 Lempel–Ziv–Oberhumer a lossless data compression algorithm https://en.wikipedia.org/wiki/Lempel-Ziv-Oberhumer
2 gzip - based on the DEFLATE algorithm https://en.wikipedia.org/wiki/Gzip
3 Zstandard a lossless data compression algorithm https://en.wikipedia.org/wiki/Zstandard
4 pigz - parallel implementation of gzip https://zlib.net/pigz/


.zst
.gz or .tgz
.lzo


Zstandard (zstd) compression
gzip compression
lzo compression

If the backup file name doesn’t end with one of the above file extensions, then it was not compressed by
vzdump.


## 16.4 Backup Encryption


For Proxmox Backup Server storages, you can optionally set up client-side encryption of backups, see the
corresponding section.


## 16.5 Backup Jobs


Besides triggering a backup manually, you can also setup periodic jobs that backup all, or a selection of
virtual guest to a storage. You can manage the jobs in the UI under Datacenter → Backup or via the
/cluster/backup API endpoint. Both will generate job entries in /etc/pve/jobs.cfg, which are
parsed and executed by the pvescheduler daemon.


A job is either configured for all cluster nodes or a specific node, and is executed according to a given
schedule. The format for the schedule is very similar to systemd calendar events, see the calendar events
section for details. The Schedule field in the UI can be freely edited, and it contains several examples that
can be used as a starting point in its drop-down list.
You can configure job-specific retention options overriding those from the storage or node configuration, as
well as a template for notes for additional information to be saved together with the backup.
Since scheduled backups miss their execution when the host was offline or the pvescheduler was disabled
during the scheduled time, it is possible to configure the behaviour for catching up. By enabling the Repeat
missed option (in the Advanced tab in the UI, repeat-missed in the config), you can tell the scheduler
that it should run missed jobs as soon as possible.

There are a few settings for tuning backup performance (some of which are exposed in the Advanced tab in
the UI). The most notable is bwlimit for limiting IO bandwidth. The amount of threads used for the compressor can be controlled with the pigz (replacing gzip), respectively, zstd setting. Furthermore, there


are ionice (when the BFQ scheduler is used) and, as part of the performance setting, max-workers
(affects VM backups only) and pbs-entries-max (affects container backups only). See the configuration
options for details.


## See also

- [Backup Retention and Restore](backup-retention-restore.md)
- [Backup Configuration and vzdump](backup-configuration.md)
- [QEMU/KVM VMs](../ch10-qemu/_index.md)
- [Containers](../ch11-containers/_index.md)
- [vzdump CLI Reference](../appendix-a-cli/vzdump.md)
