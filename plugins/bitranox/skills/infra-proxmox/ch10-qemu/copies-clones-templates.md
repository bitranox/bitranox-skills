# Copies, Clones and Templates

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


```
# qm set VMID -delete vmgenid
The most prominent use case for vmgenid are newer Microsoft Windows operating systems, which use it
to avoid problems in time sensitive or replicate services (such as databases or domain controller 15 ) on
snapshot rollback, backup restore or a whole VM clone operation.
```


## 10.7 Importing Virtual Machines


Importing existing virtual machines from foreign hypervisors or other Proxmox VE clusters can be achieved
through various methods, the most common ones are:

- Using the native import wizard, which utilizes the import content type, such as provided by the ESXi special
storage.

- Performing a backup on the source and then restoring on the target. This method works best when
migrating from another Proxmox VE instance.

- using the OVF-specific import command of the qm command-line tool.
If you import VMs to Proxmox VE from other hypervisors, it’s recommended to familiarize yourself with the
concepts of Proxmox VE.
15 https://docs.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/virtualized-domain-controllerarchitecture


### 10.7.1 Import Wizard


Proxmox VE provides an integrated VM importer using the storage plugin system for native integration into
the API and web-based user interface. You can use this to import the VM as a whole, with most of its config
mapped to Proxmox VE’s config model and reduced downtime.

> **Note:**
> The import wizard was added during the Proxmox VE 8.2 development cycle and is in tech preview state.
> While it’s already promising and working stable, it’s still under active development.


To use the import wizard you have to first set up a new storage for an import source, you can do so on the
web-interface under Datacenter → Storage → Add.
Then you can select the new storage in the resource tree and use the Virtual Guests content tab to see all
available guests that can be imported.


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
