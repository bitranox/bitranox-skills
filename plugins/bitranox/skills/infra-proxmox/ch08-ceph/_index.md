# Deploy Hyper-Converged Ceph Cluster

*[Main Index](../SKILL.md)*

## Contents

| Section                                        | File                                                                     |
|------------------------------------------------|--------------------------------------------------------------------------|
| 8.1-8.4 Ceph Installation and Configuration    | [installation-and-config.md](installation-and-config.md)                 |
| 8.5-8.6 Ceph Monitors and Managers             | [monitors-and-managers.md](monitors-and-managers.md)                     |
| 8.7 Ceph OSDs                                  | [osds.md](osds.md)                                                       |
| 8.8-8.9 Ceph Pools and Configuration           | [pools-and-config.md](pools-and-config.md)                               |
| 8.10-8.11 CRUSH and Ceph Client                | [crush-and-client.md](crush-and-client.md)                               |
| 8.12 CephFS                                    | [cephfs.md](cephfs.md)                                                   |
| 8.13-8.14 Ceph Maintenance and Troubleshooting | [maintenance-and-troubleshooting.md](maintenance-and-troubleshooting.md) |


## See also

- [Storage](../ch07-storage/_index.md)
- [pveceph CLI Reference](../appendix-a-cli/pveceph.md)

## Overview


## 8.1 Introduction


Proxmox VE unifies your compute and storage systems, that is, you can use the same physical nodes within
a cluster for both computing (processing VMs and containers) and replicated storage. The traditional silos of
compute and storage resources can be wrapped up into a single hyper-converged appliance. Separate storage networks (SANs) and connections via network attached storage (NAS) disappear. With the integration
of Ceph, an open source software-defined storage platform, Proxmox VE has the ability to run and manage
Ceph storage directly on the hypervisor nodes.
Ceph is a distributed object store and file system designed to provide excellent performance, reliability and
scalability.

S OME ADVANTAGES OF C EPH ON P ROXMOX VE ARE :
- Easy setup and management via CLI and GUI
- Thin provisioning
- Snapshot support
