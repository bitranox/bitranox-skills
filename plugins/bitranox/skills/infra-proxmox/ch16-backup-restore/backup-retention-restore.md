# Backup Retention and Restore

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 16.6 Backup Retention


With the prune-backups option you can specify which backups you want to keep in a flexible manner.

The following retention options are available:

keep-all <boolean>
Keep all backups. If this is true, no other options can be set.

keep-last <N>
Keep the last <N> backups.
keep-hourly <N>
Keep backups for the last <N> hours. If there is more than one backup for a single hour, only the latest
is kept.

keep-daily <N>
Keep backups for the last <N> days. If there is more than one backup for a single day, only the latest
is kept.

keep-weekly <N>
Keep backups for the last <N> weeks. If there is more than one backup for a single week, only the
latest is kept.

> **Note:**
> Weeks start on Monday and end on Sunday. The software uses the ISO week date-system and
> handles weeks at the end of the year correctly.


keep-monthly <N>
Keep backups for the last <N> months. If there is more than one backup for a single month, only the
latest is kept.


keep-yearly <N>
Keep backups for the last <N> years. If there is more than one backup for a single year, only the latest
is kept.
The retention options are processed in the order given above. Each option only covers backups within its
time period. The next option does not take care of already covered backups. It will only consider older
backups.
Specify the retention options you want to use as a comma-separated list, for example:


```
# vzdump 777 --prune-backups keep-last=3,keep-daily=13,keep-yearly=9
While you can pass prune-backups directly to vzdump, it is often more sensible to configure the setting
on the storage level, which can be done via the web interface.
```


### 16.6.1 Prune Simulator


You can use the prune simulator of the Proxmox Backup Server documentation to explore the effect of
different retention options with various backup schedules.


### 16.6.2 Retention Settings Example


The backup frequency and retention of old backups may depend on how often data changes, and how
important an older state may be, in a specific work load. When backups act as a company’s document
archive, there may also be legal requirements for how long backups must be kept.
For this example, we assume that you are doing daily backups, have a retention period of 10 years, and the
period between backups stored gradually grows.

keep-last=3 - even if only daily backups are taken, an admin may want to create an extra one just before
or after a big upgrade. Setting keep-last ensures this.

keep-hourly is not set - for daily backups this is not relevant. You cover extra manual backups already,
with keep-last.

keep-daily=13 - together with keep-last, which covers at least one day, this ensures that you have at
least two weeks of backups.
keep-weekly=8 - ensures that you have at least two full months of weekly backups.
keep-monthly=11 - together with the previous keep settings, this ensures that you have at least a year
of monthly backups.

keep-yearly=9 - this is for the long term archive. As you covered the current year with the previous
options, you would set this to nine for the remaining ones, giving you a total of at least 10 years of coverage.
We recommend that you use a higher retention period than is minimally required by your environment; you
can always reduce it if you find it is unnecessarily high, but you cannot recreate backups once they have
been removed.


## 16.7 Backup Protection


You can mark a backup as protected to prevent its removal. Attempting to remove a protected backup
via Proxmox VE’s UI, CLI or API will fail. However, this is enforced by Proxmox VE and not the file-system,
that means that a manual removal of a backup file itself is still possible for anyone with write access to the
underlying backup storage.

> **Note:**
> Protected backups are ignored by pruning and do not count towards the retention settings.


For filesystem-based storages, the protection is implemented via a sentinel file <backup-name>.protected.
For Proxmox Backup Server, it is handled on the server side (available since Proxmox Backup Server version
2.1).
Use the storage option max-protected-backups to control how many protected backups per guest are
allowed on the storage. Use -1 for unlimited. The default is unlimited for users with Datastore.Allocate
privilege and 5 for other users.


## 16.8 Backup Notes


You can add notes to backups using the Edit Notes button in the UI or via the storage content API.

It is also possible to specify a template for generating notes dynamically for a backup job and for manual
backup. The template string can contain variables, surrounded by two curly braces, which will be replaced
by the corresponding value when the backup is executed.
Currently supported are:

- {{cluster}} the cluster name, if any
- {{guestname}} the virtual guest’s assigned name
- {{node}} the host name of the node the backup is being created
- {{vmid}} the numerical VMID of the guest
When specified via API or CLI, it needs to be a single line, where newline and backslash need to be escaped
as literal \n and \\ respectively.


## 16.9 Restore


A backup archive can be restored through the Proxmox VE web GUI or through the following CLI tools:


```
pct restore
```

Container restore utility

qmrestore
Virtual Machine restore utility
For details see the corresponding manual pages.


### 16.9.1 Bandwidth Limit


Restoring one or more big backups may need a lot of resources, especially storage bandwidth for both
reading from the backup storage and writing to the target storage. This can negatively affect other virtual
guests as access to storage can get congested.
To avoid this you can set bandwidth limits for a backup job. Proxmox VE implements two kinds of limits for
restoring and archive:

- per-restore limit: denotes the maximal amount of bandwidth for reading from a backup archive
- per-storage write limit: denotes the maximal amount of bandwidth used for writing to a specific storage
The read limit indirectly affects the write limit, as we cannot write more than we read. A smaller per-job limit
will overwrite a bigger per-storage limit. A bigger per-job limit will only overwrite the per-storage limit if you
have ‘Data.Allocate’ permissions on the affected storage.
You can use the ‘--bwlimit <integer>` option from the restore CLI commands to set up a restore job specific
bandwidth limit. KiB/s is used as unit for the limit, this means passing `10240’ will limit the read speed of
the backup to 10 MiB/s, ensuring that the rest of the possible storage bandwidth is available for the already
running virtual guests, and thus the backup does not impact their operations.

> **Note:**
> You can use ‘0` for the bwlimit parameter to disable all limits for a specific restore job. This can be
> helpful if you need to restore a very important virtual guest as fast as possible. (Needs `Data.Allocate’
> permissions on storage)


Most times your storage’s generally available bandwidth stays the same over time, thus we implemented the
possibility to set a default bandwidth limit per configured storage, this can be done with:


```
# pvesm set STORAGEID --bwlimit restore=KIBs
```


### 16.9.2 Live-Restore


Restoring a large backup can take a long time, in which a guest is still unavailable. For VM backups stored
on a Proxmox Backup Server, this wait time can be mitigated using the live-restore option.
Enabling live-restore via either the checkbox in the GUI or the --live-restore argument of qmrestore
causes the VM to start as soon as the restore begins. Data is copied in the background, prioritizing chunks
that the VM is actively accessing.
Note that this comes with two caveats:

- During live-restore, the VM will operate with limited disk read speeds, as data has to be loaded from the
backup server (once loaded, it is immediately available on the destination storage however, so accessing
data twice only incurs the penalty the first time). Write speeds are largely unaffected.

- If the live-restore fails for any reason, the VM will be left in an undefined state - that is, not all data might
have been copied from the backup, and it is most likely not possible to keep any data that was written
during the failed restore operation.
This mode of operation is especially useful for large VMs, where only a small amount of data is required
for initial operation, e.g. web servers - once the OS and necessary services have been started, the VM is
operational, while the background task continues copying seldom used data.


### 16.9.3 Single File Restore


The File Restore button in the Backups tab of the storage GUI can be used to open a file browser directly on
the data contained in a backup. This feature is only available for backups on a Proxmox Backup Server.
For containers, the first layer of the file tree shows all included pxar archives, which can be opened and
browsed freely. For VMs, the first layer shows contained drive images, which can be opened to reveal a list
of supported storage technologies found on the drive. In the most basic case, this will be an entry called
part, representing a partition table, which contains entries for each partition found on the drive. Note that for
VMs, not all data might be accessible (unsupported guest file systems, storage technologies, etc. . . ).
Files and directories can be downloaded using the Download button, the latter being compressed into a zip
archive on the fly.
To enable secure access to VM images, which might contain untrusted data, a temporary VM (not visible as
a guest) is started. This does not mean that data downloaded from such an archive is inherently safe, but it
avoids exposing the hypervisor system to danger. The VM will stop itself after a timeout. This entire process
happens transparently from a user’s point of view.

> **Note:**
> For troubleshooting


purposes,

each

temporary

VM instance generates a log file in
/var/log/proxmox-backup/file-restore/. The log file might contain additional information in case an attempt to restore individual files or accessing file systems contained in a backup
archive fails.


## See also

- [Backup and Restore Overview](_index.md)
- [Backup Configuration and vzdump](backup-configuration.md)
- [QEMU/KVM VMs](../ch10-qemu/_index.md)
- [Containers](../ch11-containers/_index.md)
