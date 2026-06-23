# HA Overview and How It Works

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

Our modern society depends heavily on information provided by computers over the network. Mobile devices
amplified that dependency, because people can access the network any time from anywhere. If you provide
such services, it is very important that they are available most of the time.
We can mathematically define the availability as the ratio of (A), the total time a service is capable of being
used during a given interval to (B), the length of the interval. It is normally expressed as a percentage of
uptime in a given year.

Table 15.1: Availability - Downtime per Year
Availability %
99

## 99.9 99.99


## 99.999 99.9999


## 99.99999 Downtime per year


## 3.65 days


## 8.76 hours


## 52.56 minutes


## 5.26 minutes


## 31.5 seconds


## 3.15 seconds


There are several ways to increase availability. The most elegant solution is to rewrite your software, so
that you can run it on several hosts at the same time. The software itself needs to have a way to detect
errors and do failover. If you only want to serve read-only web pages, then this is relatively simple. However,
this is generally complex and sometimes impossible, because you cannot modify the software yourself. The
following solutions works without modifying the software:

- Use reliable “server” components

> **Note:**
> Computer components with the same functionality can have varying reliability numbers, depending on
> the component quality. Most vendors sell components with higher reliability as “server” components usually at higher price.


- Eliminate single point of failure (redundant components)


– use an uninterruptible power supply (UPS)
– use redundant power supplies in your servers
– use ECC-RAM
– use redundant network hardware
– use RAID for local storage
– use distributed, redundant storage for VM data
- Reduce downtime
– rapidly accessible administrators (24/7)
– availability of spare parts (other nodes in a Proxmox VE cluster)
– automatic error detection (provided by ha-manager)
– automatic failover (provided by ha-manager)
Virtualization environments like Proxmox VE make it much easier to reach high availability because they
remove the “hardware” dependency. They also support the setup and use of redundant storage and network
devices, so if one host fails, you can simply start those services on another host within your cluster.
Better still, Proxmox VE provides a software stack called ha-manager, which can do that automatically for
you. It is able to automatically detect errors and do automatic failover.
Proxmox VE ha-manager works like an “automated” administrator. First, you configure what resources
(VMs, containers, . . . ) it should manage. Then, ha-manager observes the correct functionality, and
handles service failover to another node in case of errors. ha-manager can also handle normal user
requests which may start, stop, relocate and migrate a service.
But high availability comes at a price. High quality components are more expensive, and making them
redundant doubles the costs at least. Additional spare parts increase costs further. So you should carefully
calculate the benefits, and compare with those additional costs.

> **Tip:**
> Increasing availability from 99% to 99.9% is relatively simple. But increasing availability from 99.9999% to
> 99.99999% is very hard and costly. ha-manager has typical error detection and failover times of about
> 2 minutes, so you can get no more than 99.999% availability.


## 15.1 Requirements


You must meet the following requirements before you start with HA:

- at least three cluster nodes (to get reliable quorum)
- shared storage for VMs and containers
- hardware redundancy (everywhere)
- use reliable “server” components
Optionally, a hardware watchdog can be used - if not available we fall back to the linux kernel software
watchdog (softdog).


## 15.2 Resources


We call the primary management unit handled by ha-manager a resource. A resource (also called “service”) is uniquely identified by a service ID (SID), which consists of the resource type and a type specific ID,
for example vm:100. That example would be a resource of type vm (virtual machine) with the ID 100.
For now we have two important resources types - virtual machines and containers. One basic idea here is
that we can bundle related software into such a VM or container, so there is no need to compose one big
service from other services, as was done with rgmanager. In general, a HA managed resource should not
depend on other resources.


## 15.3 Management Tasks


This section provides a short overview of common management tasks. The first step is to enable HA for a
resource. This is done by adding the resource to the HA resource configuration. You can do this using the
GUI, or simply use the command-line tool, for example:


```
# ha-manager add vm:100
The HA stack now tries to start the resources and keep them running. Please note that you can configure
the “requested” resources state. For example you may want the HA stack to stop the resource:

# ha-manager set vm:100 --state stopped
and start it again later:

# ha-manager set vm:100 --state started
You can also use the normal VM and container management commands. They automatically forward the
commands to the HA stack, so

# qm start 100
simply sets the requested state to started. The same applies to qm stop, which sets the requested
state to stopped.
Note
The HA stack works fully asynchronous and needs to communicate with other cluster members. Therefore,
it takes some seconds until you see the result of such actions.
```


To view the current HA resource configuration use:


```
# ha-manager config
vm:100
state stopped
And you can view the actual HA manager and resource state with:

# ha-manager status
quorum OK
master node1 (active, Wed Nov 23 11:07:23 2016)
lrm elsa (active, Wed Nov 23 11:07:19 2016)
service vm:100 (node1, started)
```


You can also initiate resource migration to other nodes:


```
# ha-manager migrate vm:100 node2
This uses online migration and tries to keep the VM running. Online migration needs to transfer all used
memory over the network, so it is sometimes faster to stop the VM, then restart it on the new node. This can
be done using the relocate command:

# ha-manager relocate vm:100 node2
Finally, you can remove the resource from the HA configuration using the following command:

# ha-manager remove vm:100
By default, this will also remove the resource from any rule that references it and will delete rules that only
reference this resource. You can override this behavior using --purge 0.
Note
This does not start or stop the resource.
```


But all HA related tasks can be done in the GUI, so there is no need to use the command line at all.


## 15.4 How It Works


This section provides a detailed description of the Proxmox VE HA manager internals. It describes all
involved daemons and how they work together. To provide HA, two daemons run on each node:

pve-ha-lrm
The local resource manager (LRM), which controls the services running on the local node. It reads
the requested states for its services from the current manager status file and executes the respective
commands.

pve-ha-crm
The cluster resource manager (CRM), which makes the cluster-wide decisions. It sends commands
to the LRM, processes the results, and moves resources to other nodes if something fails. The CRM
also handles node fencing.

> **Note:**
> Locks are provided by our distributed configuration file system (pmxcfs). They are used to guarantee that
> each LRM is active once and working. As an LRM only executes actions when it holds its lock, we can
> mark a failed node as fenced if we can acquire its lock. This then lets us recover any failed HA services
> securely without any interference from the now unknown failed node. This all gets supervised by the CRM
> which currently holds the manager master lock.


### 15.4.1 Service States


The CRM uses a service state enumeration to record the current service state. This state is displayed on
the GUI and can be queried using the ha-manager command-line tool:


```
# ha-manager status
quorum OK
master elsa (active, Mon Nov 21 07:23:29 2016)
lrm elsa (active, Mon Nov 21 07:23:22 2016)
service ct:100 (elsa, stopped)
service ct:102 (elsa, started)
service vm:501 (elsa, started)
Here is the list of possible states:
```


stopped
Service is stopped (confirmed by LRM). If the LRM detects a stopped service is still running, it will stop
it again.
request_stop
Service should be stopped. The CRM waits for confirmation from the LRM.
stopping
Pending stop request. But the CRM did not get the request so far.
started
Service is active an LRM should start it ASAP if not already running. If the Service fails and is detected
to be not running the LRM restarts it (see Start Failure Policy).
starting
Pending start request. But the CRM has not got any confirmation from the LRM that the service is
running.
fence
Wait for node fencing as the service node is not inside the quorate cluster partition (see Fencing). As
soon as node gets fenced successfully the service will be placed into the recovery state.
recovery
Wait for recovery of the service. The HA manager tries to find a new node where the service can run
on. This search depends on the list of online and quorate nodes as well as the affinity rules the service
is part of, if any. As soon as a new available node is found, the service will be moved there and initially
placed into stopped state. If it’s configured to run the new node will do so.
freeze
Do not touch the service state. We use this state while we reboot a node, or when we restart the LRM
daemon (see Package Updates).
ignored
Act as if the service were not managed by HA at all. Useful, when full control over the service is
desired temporarily, without removing it from the HA configuration.


migrate
Migrate service (live) to other node.
error
Service is disabled because of LRM errors. Needs manual intervention (see Error Recovery).
queued
Service is newly added, and the CRM has not seen it so far.
disabled
Service is stopped and marked as disabled


### 15.4.2 Local Resource Manager


The local resource manager (pve-ha-lrm) is started as a daemon on boot and waits until the HA cluster
is quorate and thus cluster-wide locks are working.
It can be in three states:

wait for agent lock
The LRM waits for our exclusive lock. This is also used as idle state if no service is configured.
active
The LRM holds its exclusive lock and has services configured.
lost agent lock
The LRM lost its lock, this means a failure happened and quorum was lost.
After the LRM gets in the active state it reads the manager status file in /etc/pve/ha/manager_status
and determines the commands it has to execute for the services it owns. For each command a worker gets
started, these workers are running in parallel and are limited to at most 4 by default. This default setting may
be changed through the datacenter configuration key max_worker. When finished the worker process
gets collected and its result saved for the CRM.

> **Note:**
> The default value of at most 4 concurrent workers may be unsuited for a specific setup. For example, 4
> live migrations may occur at the same time, which can lead to network congestions with slower networks
> and/or big (memory wise) services. Also, ensure that in the worst case, congestion is at a minimum, even
> if this means lowering the max_worker value. On the contrary, if you have a particularly powerful, highend setup you may also want to increase it.


Each command requested by the CRM is uniquely identifiable by a UID. When the worker finishes, its result
will be processed and written in the LRM status file /etc/pve/nodes/<nodename>/lrm_status.
There the CRM may collect it and let its state machine - respective to the commands output - act on it.
The actions on each service between CRM and LRM are normally always synced. This means that the CRM
requests a state uniquely marked by a UID, the LRM then executes this action one time and writes back


the result, which is also identifiable by the same UID. This is needed so that the LRM does not execute an
outdated command. The only exceptions to this behaviour are the stop and error commands; these two
do not depend on the result produced and are executed always in the case of the stopped state and once in
the case of the error state.

> **Note:**
> The HA Stack logs every action it makes. This helps to understand what and also why something happens
> in the cluster. Here its important to see what both daemons, the LRM and the CRM, did. You may use
> journalctl -u pve-ha-lrm on the node(s) where the service is and the same command for the
> pve-ha-crm on the node which is the current master.


### 15.4.3 Cluster Resource Manager


The cluster resource manager (pve-ha-crm) starts on each node and waits there for the manager lock,
which can only be held by one node at a time. The node which successfully acquires the manager lock gets
promoted to the CRM master.
It can be in three states:

wait for agent lock
The CRM waits for our exclusive lock. This is also used as idle state if no service is configured
active
The CRM holds its exclusive lock and has services configured
lost agent lock
The CRM lost its lock, this means a failure happened and quorum was lost.
Its main task is to manage the services which are configured to be highly available and try to always enforce
the requested state. For example, a service with the requested state started will be started if its not already
running. If it crashes it will be automatically started again. Thus the CRM dictates the actions the LRM needs
to execute.
When a node leaves the cluster quorum, its state changes to unknown. If the current CRM can then secure
the failed node’s lock, the services will be stolen and restarted on another node.
When a cluster member determines that it is no longer in the cluster quorum, the LRM waits for a new
quorum to form. Until there is a cluster quorum, the node cannot reset the watchdog. If there are active
services on the node, or if the LRM or CRM process is not scheduled or is killed, this will trigger a reboot
after the watchdog has timed out (this happens after 60 seconds).
Note that if a node has an active CRM but the LRM is idle, a quorum loss will not trigger a self-fence reset.
The reason for this is that all state files and configurations that the CRM accesses are backed up by the
clustered configuration file system, which becomes read-only upon quorum loss. This means that the CRM
only needs to protect itself against its process being scheduled for too long, in which case another CRM
could take over unaware of the situation, causing corruption of the HA state. The open watchdog ensures
that this cannot happen.
If no service is configured for more than 15 minutes, the CRM automatically returns to the idle state and
closes the watchdog completely.


## 15.5 HA Simulator


By using the HA simulator you can test and learn all functionalities of the Proxmox VE HA solutions.
By default, the simulator allows you to watch and test the behaviour of a real-world 3 node cluster with 6
VMs. You can also add or remove additional VMs or Container.
You do not have to setup or configure a real cluster, the HA simulator runs out of the box.
Install with apt:

apt install pve-ha-simulator
You can even install the package on any Debian-based system without any other Proxmox VE packages. For
that you will need to download the package and copy it to the system you want to run it on for installation.
When you install the package with apt from the local file system it will also resolve the required dependencies
for you.
To start the simulator on a remote machine you must have an X11 redirection to your current system.
If you are on a Linux machine you can use:

ssh root@<IPofPVE> -Y
On Windows it works with mobaxterm.
After connecting to an existing Proxmox VE with the simulator installed or installing it on your local Debianbased system manually, you can try it out as follows.
First you need to create a working directory where the simulator saves its current state and writes its default
config:

mkdir working
Then, simply pass the created directory as a parameter to pve-ha-simulator :


pve-ha-simulator working/
You can then start, stop, migrate the simulated HA services, or even check out what happens on a node
failure.


## 15.6 Configuration


The HA stack is well integrated into the Proxmox VE API. So, for example, HA can be configured via the

```
ha-manager command-line interface, or the Proxmox VE web interface - both interfaces provide an easy
```

way to manage HA. Automation tools can use the API directly.
All HA configuration files are within /etc/pve/ha/, so they get automatically distributed to the cluster
nodes, and all nodes share the same HA configuration.


### 15.6.1 Resources


The resource configuration file /etc/pve/ha/resources.cfg stores the list of resources managed
by ha-manager. A resource configuration inside that list looks like this:

<type>: <name>
<property> <value>
...
It starts with a resource type followed by a resource specific name, separated with colon. Together this forms
the HA resource ID, which is used by all ha-manager commands to uniquely identify a resource (example:
vm:100 or ct:101). The next lines contain additional properties:


comment: <string>
Description.

failback: <boolean> (default = 1)
Automatically migrate HA resource to the node with the highest priority according to their node affinity
rules, if a node with a higher priority than the current node comes online.

group: <string>
The HA group identifier.

max_relocate: <integer> (0 - N) (default = 1)
Maximal number of service relocate tries when a service failes to start.

max_restart: <integer> (0 - N) (default = 1)
Maximal number of tries to restart the service on a node after its start failed.

state: <disabled | enabled | ignored | started | stopped> (default =
started)
Requested resource state. The CRM reads this state and acts accordingly. Please note that enabled
is just an alias for started.

started
The CRM tries to start the resource. Service state is set to started after successful start. On
node failures, or when start fails, it tries to recover the resource. If everything fails, service state
it set to error.

stopped
The CRM tries to keep the resource in stopped state, but it still tries to relocate the resources
on node failures.

disabled
The CRM tries to put the resource in stopped state, but does not try to relocate the resources
on node failures. The main purpose of this state is error recovery, because it is the only way to
move a resource out of the error state.

ignored
The resource gets removed from the manager status and so the CRM and the LRM do not
touch the resource anymore. All {pve} API calls affecting this resource will be executed, directly
bypassing the HA stack. CRM commands will be thrown away while there source is in this state.
The resource will not get relocated on node failures.
Here is a real world example with one VM and one container. As you see, the syntax of those files is really
simple, so it is even possible to read or edit those files using your favorite editor:

Configuration Example (/etc/pve/ha/resources.cfg)
