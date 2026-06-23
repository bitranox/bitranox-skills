# Fencing and Recovery

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 15.7.3 Recover Fenced Services


After a node failed and its fencing was successful, the CRM tries to move services from the failed node to
nodes which are still online.
The selection of the recovery nodes is influenced by the list of currently active nodes, their respective loads
depending on the used scheduler, and the affinity rules the service is part of, if any.
First, the CRM builds a set of nodes available to the service. If the service is part of a node affinity rule, the
set is reduced to the highest priority nodes in the node affinity rule. If the service is part of a resource affinity
rule, the set is further reduced to fulfill their constraints, which is either keeping the service on the same
node as some other services or keeping the service on a different node than some other services. Finally,
the CRM selects the node with the lowest load according to the used scheduler to minimize the possibility of
an overloaded node.

> **Caution:**
> On node failure, the CRM distributes services to the remaining nodes. This increases the service
> count on those nodes, and can lead to high load, especially on small clusters. Please design your
> cluster so that it can handle such worst case scenarios.


## 15.8 Start Failure Policy


The start failure policy comes into effect if a service failed to start on a node one or more times. It can
be used to configure how often a restart should be triggered on the same node and how often a service
should be relocated, so that it has an attempt to be started on another node. The aim of this policy is to
circumvent temporary unavailability of shared resources on a specific node. For example, if a shared storage
isn’t available on a quorate node anymore, for instance due to network problems, but is still available on other
nodes, the relocate policy allows the service to start nonetheless.
There are two service start recover policy settings which can be configured specific for each resource.

max_restart
Maximum number of attempts to restart a failed service on the actual node. The default is set to one.
max_relocate
Maximum number of attempts to relocate the service to a different node. A relocate only happens after
the max_restart value is exceeded on the actual node. The default is set to one.

> **Note:**
> The relocate count state will only reset to zero when the service had at least one successful start. That
> means if a service is re-started without fixing the error only the restart policy gets repeated.


## 15.9 Error Recovery


If, after all attempts, the service state could not be recovered, it gets placed in an error state. In this state,
the service won’t get touched by the HA stack anymore. The only way out is disabling a service:


```
# ha-manager set vm:100 --state disabled
This can also be done in the web interface.
To recover from the error state you should do the following:
```


- bring the resource back into a safe and consistent state (e.g.: kill its process if the service could not be
stopped)

- disable the resource to remove the error flag
- fix the error which led to this failures
- after you fixed all errors you may request that the service starts again


## 15.10 Package Updates


When updating the ha-manager, you should do one node after the other, never all at once for various reasons.
First, while we test our software thoroughly, a bug affecting your specific setup cannot totally be ruled out.
Updating one node after the other and checking the functionality of each node after finishing the update
helps to recover from eventual problems, while updating all at once could result in a broken cluster and is
generally not good practice.
Also, the Proxmox VE HA stack uses a request acknowledge protocol to perform actions between the cluster
and the local resource manager. For restarting, the LRM makes a request to the CRM to freeze all its
services. This prevents them from getting touched by the Cluster during the short time the LRM is restarting.
After that, the LRM may safely close the watchdog during a restart. Such a restart happens normally during
a package update and, as already stated, an active master CRM is needed to acknowledge the requests
from the LRM. If this is not the case the update process can take too long which, in the worst case, may
result in a reset triggered by the watchdog.


## 15.11 Node Maintenance


Sometimes it is necessary to perform maintenance on a node, such as replacing hardware or simply installing
a new kernel image. This also applies while the HA stack is in use.
The HA stack can support you mainly in two types of maintenance:

- for general shutdowns or reboots, the behavior can be configured, see Shutdown Policy.
- for maintenance that does not require a shutdown or reboot, or that should not be switched off automatically
after only one reboot, you can enable the manual maintenance mode.


### 15.11.1 Maintenance Mode


You can use the manual maintenance mode to mark the node as unavailable for HA operation, prompting all
services managed by HA to migrate to other nodes.


The target nodes for these migrations are selected from the other currently available nodes, and determined
by the HA rules configuration and the configured cluster resource scheduler (CRS) mode. During each
migration, the original node will be recorded in the HA managers’ state, so that the service can be moved
back again automatically once the maintenance mode is disabled and the node is back online.
Currently you can enabled or disable the maintenance mode using the ha-manager CLI tool.

Enabling maintenance mode for a node


```
# ha-manager crm-command node-maintenance enable NODENAME
This will queue a CRM command, when the manager processes this command it will record the request for
maintenance-mode in the manager status. This allows you to submit the command on any node, not just on
the one you want to place in, or out of the maintenance mode.
Once the LRM on the respective node picks the command up it will mark itself as unavailable, but still
process all migration commands. This means that the LRM self-fencing watchdog will stay active until all
active services got moved, and all running workers finished.
Note that the LRM status will read maintenance mode as soon as the LRM picked the requested state
up, not only when all services got moved away, this user experience is planned to be improved in the future. For now, you can check for any active HA service left on the node, or watching out for a log line
like: pve-ha-lrm[PID]: watchdog closed (disabled) to know when the node finished its
transition into the maintenance mode.
Note
The manual maintenance mode is not automatically deleted on node reboot, but only if it is either manually
deactivated using the ha-manager CLI or if the manager-status is manually cleared.
```


Disabling maintenance mode for a node


```
# ha-manager crm-command node-maintenance disable NODENAME
The process of disabling the manual maintenance mode is similar to enabling it. Using the ha-manager
CLI command shown above will queue a CRM command that, once processed, marks the respective LRM
node as available again.
If you deactivate the maintenance mode, all services that were on the node when the maintenance mode
was activated will be moved back.
```


### 15.11.2 Shutdown Policy


Below you will find a description of the different HA policies for a node shutdown. Currently Conditional is
the default due to backward compatibility. Some users may find that Migrate behaves more as expected.
The shutdown policy can be configured in the Web UI (Datacenter → Options → HA Settings),
or directly in datacenter.cfg:

ha: shutdown_policy=<value>


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

