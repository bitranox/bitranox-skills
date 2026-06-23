# Maintenance and Scheduling

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Migrate
Once the Local Resource manager (LRM) gets a shutdown request and this policy is enabled, it will mark
itself as unavailable for the current HA manager. This triggers a migration of all HA Services currently located
on this node. The LRM will try to delay the shutdown process, until all running services get moved away. But,
this expects that the running services can be migrated to another node. In other words, the service must
not be locally bound, for example by using hardware passthrough. For example, strict node affinity rules
tell the HA Manager that the service cannot run outside of the chosen set of nodes. If all of these nodes
are unavailable, the shutdown will hang until you manually intervene. Once the shut down node comes
back online again, the previously displaced services will be moved back, if they were not already manually
migrated in-between.

> **Note:**
> The watchdog is still active during the migration process on shutdown. If the node loses quorum it will be
> fenced and the services will be recovered.


If you start a (previously stopped) service on a node which is currently being maintained, the node needs to
be fenced to ensure that the service can be moved and started on another available node.

Failover
This mode ensures that all services get stopped, but that they will also be recovered, if the current node is
not online soon. It can be useful when doing maintenance on a cluster scale, where live-migrating VMs may
not be possible if too many nodes are powered off at a time, but you still want to ensure HA services get
recovered and started again as soon as possible.

Freeze
This mode ensures that all services get stopped and frozen, so that they won’t get recovered until the current
node is online again.

Conditional
The Conditional shutdown policy automatically detects if a shutdown or a reboot is requested, and changes
behaviour accordingly.

Shutdown
A shutdown (poweroff ) is usually done if it is planned for the node to stay down for some time. The LRM stops
all managed services in this case. This means that other nodes will take over those services afterwards.

> **Note:**
> Recent hardware has large amounts of memory (RAM). So we stop all resources, then restart them to
> avoid online migration of all that RAM. If you want to use online migration, you need to invoke that manually
> before you shutdown the node.


Reboot
Node reboots are initiated with the reboot command. This is usually done after installing a new kernel.
Please note that this is different from “shutdown”, because the node immediately starts again.
The LRM tells the CRM that it wants to restart, and waits until the CRM puts all resources into the freeze
state (same mechanism is used for Package Updates). This prevents those resources from being moved to
other nodes. Instead, the CRM starts the resources after the reboot on the same node.

Manual Resource Movement
Last but not least, you can also manually move resources to other nodes, before you shutdown or restart a
node. The advantage is that you have full control, and you can decide if you want to use online migration or
not.

> **Note:**
> Please do not kill services like pve-ha-crm, pve-ha-lrm or watchdog-mux. They manage and
> use the watchdog, so this can result in an immediate node reboot or even reset.


## 15.12 Cluster Resource Scheduling


The cluster resource scheduler (CRS) mode controls how HA selects nodes for the recovery of a service as
well as for migrations that are triggered by a shutdown policy. The default mode is basic, you can change
it in the Web UI (Datacenter → Options), or directly in datacenter.cfg:

crs: ha=static

The change will be in effect starting with the next manager round (after a few seconds).
For each service that needs to be recovered or migrated, the scheduler iteratively chooses the best node
among the nodes that are available to the service according to their HA rules, if any.

> **Note:**
> There are plans to add modes for (static and dynamic) load-balancing in the future.


### 15.12.1 Basic Scheduler


The number of active HA services on each node is used to choose a recovery node. Non-HA-managed
services are currently not counted.


### 15.12.2 Static-Load Scheduler


> **Important:**
> The static mode is still a technology preview.


Static usage information from HA services on each node is used to choose a recovery node. Usage of
non-HA-managed services is currently not considered.
For this selection, each node in turn is considered as if the service was already running on it, using CPU
and memory usage from the associated guest configuration. Then for each such alternative, CPU and
memory usage of all nodes are considered, with memory being weighted much more, because it’s a truly
limited resource. For both, CPU and memory, highest usage among nodes (weighted more, as ideally no
node should be overcommitted) and average usage of all nodes (to still be able to distinguish in case there
already is a more highly committed node) are considered.


> **Important:**
> The more services the more possible combinations there are, so it’s currently not recommended to
> use it if you have thousands of HA managed services.


### 15.12.3 CRS Scheduling Points


The CRS algorithm is not applied for every service in every round, since this would mean a large number
of constant migrations. Depending on the workload, this could put more strain on the cluster than could be
avoided by constant balancing. That’s why the Proxmox VE HA manager favors keeping services on their
current node.
The CRS is currently used at the following scheduling points:

- Service recovery (always active). When a node with active HA services fails, all its services need to be
recovered to other nodes. The CRS algorithm will be used here to balance that recovery over the remaining
nodes.

- HA group config changes (always active). If a node is removed from a group, or its priority is reduced, the
HA stack will use the CRS algorithm to find a new target node for the HA services in that group, matching
the adapted priority constraints.

- HA rule config changes (always active). If a rule emposes different constraints on the HA resources, the
HA stack will use the CRS algorithm to find a new target node for the HA resources affected by these rules
depending on the type of the new rules:


– Node affinity rules: If a node affinity rule is created or HA resources/nodes are added to an existing node
affinity rule, the HA stack will use the CRS algorithm to ensure that these HA resources are assigned
according to their node and priority constraints.

– Positive resource affinity rules: If a positive resource affinity rule is created or HA resources are added
to an existing positive resource affinity rule, the HA stack will use the CRS algorithm to ensure that these
HA resources are moved to a common node.

– Negative resource affinity rules: If a negative resource affinity rule is created or HA resources are
added to an existing negative resource affinity rule, the HA stack will use the CRS algorithm to ensure
that these HA resources are moved to separate nodes.

- HA service stopped → start transition (opt-in). Requesting that a stopped service should be started is an
good opportunity to check for the best suited node as per the CRS algorithm, as moving stopped services
is cheaper to do than moving them started, especially if their disk volumes reside on shared storage. You
can enable this by setting the ha-rebalance-on-start CRS option in the datacenter config. You
can change that option also in the Web UI, under Datacenter → Options → Cluster Resource
Scheduling.
