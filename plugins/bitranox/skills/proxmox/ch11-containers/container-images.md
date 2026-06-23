# Container Images

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


## 11.4 Container Settings


### 11.4.1 General Settings


General settings of a container include

- the Node : the physical server on which the container will run
- the CT ID: a unique number in this Proxmox VE installation used to identify your container
- Hostname: the hostname of the container
- Resource Pool: a logical group of containers and VMs
- Password: the root password of the container
- SSH Public Key: a public key for connecting to the root account over SSH
- Unprivileged container: this option allows to choose at creation time if you want to create a privileged or
unprivileged container.

- Nesting: expose procfs and sysfs to allow nested containers. Note that systemd also uses this to isolate
services.

Unprivileged Containers
Unprivileged containers use a new kernel feature called user namespaces. The root UID 0 inside the container is mapped to an unprivileged user outside the container. This means that most security issues (container escape, resource abuse, etc.) in these containers will affect a random unprivileged user, and would
be a generic kernel security bug rather than an LXC issue. The LXC team thinks unprivileged containers are
safe by design.
This is the default option when creating a new container.


> **Note:**
> If the container uses systemd as an init system, please be aware the systemd version running inside the
> container should be equal to or greater than 220.


Privileged Containers
Security in containers is achieved by using mandatory access control AppArmor restrictions, seccomp filters
and Linux kernel namespaces. The LXC team considers this kind of container as unsafe, and they will not
consider new container escape exploits to be security issues worthy of a CVE and quick fix. That’s why
privileged containers should only be used in trusted environments.


### 11.4.2 CPU


You can restrict the number of visible CPUs inside the container using the cores option. This is implemented using the Linux cpuset cgroup (control group). A special task inside pvestatd tries to distribute
running containers among available CPUs periodically. To view the assigned CPUs run the following command:


```
# pct cpusets
--------------------102:
6 7
105:
2 3 4 5
108: 0 1
--------------------Containers use the host kernel directly. All tasks inside a container are handled by the host CPU scheduler.
Proxmox VE uses the Linux CFS (Completely Fair Scheduler) scheduler by default, which has additional
bandwidth control options.
```


cpulimit:

cpuunits:


### 11.4.3 You can use this option to further limit assigned CPU time. Please note that this is a

floating point number, so it is perfectly valid to assign two cores to a container, but
restrict overall CPU consumption to half a core.

cores: 2
cpulimit: 0.5
This is a relative weight passed to the kernel scheduler. The larger the number is, the
more CPU time this container gets. Number is relative to the weights of all the other
running containers. The default is 100 (or 1024 if the host uses legacy cgroup v1).
You can use this setting to prioritize some containers.

Memory

Container memory is controlled using the cgroup memory controller.

memory:
swap:

Limit overall memory usage. This corresponds to the memory.limit_in_bytes
cgroup setting.
Allows the container to use additional swap memory from the host swap space. This
corresponds to the memory.memsw.limit_in_bytes cgroup setting, which is
set to the sum of both value (memory + swap).
