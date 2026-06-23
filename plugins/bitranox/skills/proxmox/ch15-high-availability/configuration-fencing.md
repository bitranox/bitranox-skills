# HA Fencing, Start Failure Policy and Error Recovery

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 15.7 Fencing


On node failures, fencing ensures that the erroneous node is guaranteed to be offline. This is required to
make sure that no resource runs twice when it gets recovered on another node. This is a really important
task, because without this, it would not be possible to recover a resource on another node.
If a node did not get fenced, it would be in an unknown state where it may have still access to shared
resources. This is really dangerous! Imagine that every network but the storage one broke. Now, while not
reachable from the public network, the VM still runs and writes to the shared storage.
If we then simply start up this VM on another node, we would get a dangerous race condition, because
we write from both nodes. Such conditions can destroy all VM data and the whole VM could be rendered
unusable. The recovery could also fail if the storage protects against multiple mounts.


### 15.7.1 How Proxmox VE Fences


There are different methods to fence a node, for example, fence devices which cut off the power from the
node or disable their communication completely. Those are often quite expensive and bring additional critical
components into a system, because if they fail you cannot recover any service.
We thus wanted to integrate a simpler fencing method, which does not require additional external hardware.
This can be done using watchdog timers.

P OSSIBLE F ENCING M ETHODS
- external power switches
- isolate nodes by disabling complete network traffic on the switch
- self fencing using watchdog timers
Watchdog timers have been widely used in critical and dependable systems since the beginning of microcontrollers. They are often simple, independent integrated circuits which are used to detect and recover from
computer malfunctions.
During normal operation, ha-manager regularly resets the watchdog timer to prevent it from elapsing. If,
due to a hardware fault or program error, the computer fails to reset the watchdog, the timer will elapse and
trigger a reset of the whole server (reboot).
Recent server motherboards often include such hardware watchdogs, but these need to be configured. If
no watchdog is available or configured, we fall back to the Linux Kernel softdog. While still reliable, it is not
independent of the servers hardware, and thus has a lower reliability than a hardware watchdog.


### 15.7.2 Configure Hardware Watchdog


By default, all hardware watchdog modules are blocked for security reasons. They are like a loaded gun
if not correctly initialized. To enable a hardware watchdog, you need to specify the module to load in
/etc/default/pve-ha-manager, for example:

# select watchdog module (default is softdog)
WATCHDOG_MODULE=iTCO_wdt
This configuration is read by the watchdog-mux service, which loads the specified module at startup.


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

## See also

- [HA Configuration](configuration.md)
- [High Availability Overview](_index.md)
