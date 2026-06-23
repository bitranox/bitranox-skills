# VM CPU and Memory Settings

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*


### 10.2.5 CPU


A CPU socket is a physical slot on a PC motherboard where you can plug a CPU. This CPU can then contain
one or many cores, which are independent processing units. Whether you have a single CPU socket with
4 cores, or two CPU sockets with two cores is mostly irrelevant from a performance point of view. However
some software licenses depend on the number of sockets a machine has, in that case it makes sense to set
the number of sockets to what the license allows you.
Increasing the number of virtual CPUs (cores and sockets) will usually provide a performance improvement
though that is heavily dependent on the use of the VM. Multi-threaded applications will of course benefit from
a large number of virtual CPUs, as for each virtual cpu you add, QEMU will create a new thread of execution
on the host system. If you’re not sure about the workload of your VM, it is usually a safe bet to set the number
of Total cores to 2.

> **Note:**
> It is perfectly safe if the overall number of cores of all your VMs is greater than the number of cores on the
> server (for example, 4 VMs each with 4 cores (= total 16) on a machine with only 8 cores). In that case
> the host system will balance the QEMU execution threads between your server cores, just like if you were
> running a standard multi-threaded application. However, Proxmox VE will prevent you from starting VMs
> with more virtual CPU cores than physically available, as this will only bring the performance down due to
> the cost of context switches.


Resource Limits
cpulimit
In addition to the number of virtual cores, the total available “Host CPU Time” for the VM can be set with
the cpulimit option. It is a floating point value representing CPU time in percent, so 1.0 is equal to 100%,

## 2.5 to 250% and so on. If a single process would fully use one single core it would have 100% CPU Time

usage. If a VM with four cores utilizes all its cores fully it would theoretically use 400%. In reality the usage
may be even a bit higher as QEMU can have additional threads for VM peripherals besides the vCPU core
ones.
This setting can be useful when a VM should have multiple vCPUs because it is running some processes in
parallel, but the VM as a whole should not be able to run all vCPUs at 100% at the same time.
For example, suppose you have a virtual machine that would benefit from having 8 virtual CPUs, but you
don’t want the VM to be able to max out all 8 cores running at full load - because that would overload the
server and leave other virtual machines and containers with too little CPU time. To solve this, you could set
cpulimit to 4.0 (=400%). This means that if the VM fully utilizes all 8 virtual CPUs by running 8 processes
simultaneously, each vCPU will receive a maximum of 50% CPU time from the physical cores. However, if
the VM workload only fully utilizes 4 virtual CPUs, it could still receive up to 100% CPU time from a physical
core, for a total of 400%.

> **Note:**
> VMs can, depending on their configuration, use additional threads, such as for networking or IO operations
> but also live migration. Thus a VM can show up to use more CPU time than just its virtual CPUs could
> use. To ensure that a VM never uses more CPU time than vCPUs assigned, set the cpulimit to the same
> value as the total core count.
> cpuunits
> With the cpuunits option, nowadays often called CPU shares or CPU weight, you can control how much
> CPU time a VM gets compared to other running VMs. It is a relative weight which defaults to 100 (or 1024
> if the host uses legacy cgroup v1). If you increase this for a VM it will be prioritized by the scheduler in
> comparison to other VMs with lower weight.
> For example, if VM 100 has set the default 100 and VM 200 was changed to 200, the latter VM 200 would
> receive twice the CPU bandwidth than the first VM 100.


For more information see man systemd.resource-control, here CPUQuota corresponds to cpulimit
and CPUWeight to our cpuunits setting. Visit its Notes section for references and implementation details.
affinity
With the affinity option, you can specify the physical CPU cores that are used to run the VM’s vCPUs.
Peripheral VM processes, such as those for I/O, are not affected by this setting. Note that the CPU affinity
is not a security feature.
Forcing a CPU affinity can make sense in certain cases but is accompanied by an increase in complexity
and maintenance effort. For example, if you want to add more VMs later or migrate VMs to nodes with fewer
CPU cores. It can also easily lead to asynchronous and therefore limited system performance if some CPUs
are fully utilized while others are almost idle.
The affinity is set through the taskset CLI tool. It accepts the host CPU numbers (see lscpu) in the
List Format from man cpuset. This ASCII decimal list can contain numbers but also number ranges.
For example, the affinity 0-1,8-11 (expanded 0, 1, 8, 9, 10, 11) would allow the VM to run on
only these six specific host cores.


CPU Type
QEMU can emulate a number different of CPU types from 486 to the latest Xeon processors. Each new
processor generation adds new features, like hardware assisted 3d rendering, random number generation,
memory protection, etc. Also, a current generation can be upgraded through microcode update with bug or
security fixes.
Usually you should select for your VM a processor type which closely matches the CPU of the host system,
as it means that the host CPU features (also called CPU flags ) will be available in your VMs. If you want an
exact match, you can set the CPU type to host in which case the VM will have exactly the same CPU flags
as your host system.
This has a downside though. If you want to do a live migration of VMs between different hosts, your VM
might end up on a new system with a different CPU type or a different microcode version. If the CPU flags
passed to the guest are missing, the QEMU process will stop. To remedy this QEMU has also its own virtual
CPU types, that Proxmox VE uses by default.
The backend default is kvm64 which works on essentially all x86_64 host CPUs and the UI default when
creating a new VM is x86-64-v2-AES, which requires a host CPU starting from Westmere for Intel or at least
a fourth generation Opteron for AMD.
In short:
If you don’t care about live migration or have a homogeneous cluster where all nodes have the same CPU
and same microcode version, set the CPU type to host, as in theory this will give your guests maximum
performance.
If you care about live migration and security, and you have only Intel CPUs or only AMD CPUs, choose the
lowest generation CPU model of your cluster.
If you care about live migration without security, or have mixed Intel/AMD cluster, choose the lowest compatible virtual QEMU CPU type.

> **Note:**
> Live migrations between Intel and AMD host CPUs have no guarantee to work.


See also List of AMD and Intel CPU Types as Defined in QEMU.

QEMU CPU Types
QEMU also provide virtual CPU types, compatible with both Intel and AMD host CPUs.

> **Note:**
> To mitigate the Spectre vulnerability for virtual CPU types, you need to add the relevant CPU flags, see
> Meltdown / Spectre related CPU flags.


Historically, Proxmox VE had the kvm64 CPU model, with CPU flags at the level of Pentium 4 enabled, so
performance was not great for certain workloads.
In the summer of 2020, AMD, Intel, Red Hat, and SUSE collaborated to define three x86-64 microarchitecture
levels on top of the x86-64 baseline, with modern flags enabled. For details, see the x86-64-ABI specification.


> **Note:**
> Some newer distributions like CentOS 9 are now built with x86-64-v2 flags as a minimum requirement.


- kvm64 (x86-64-v1): Compatible with Intel CPU >= Pentium 4, AMD CPU >= Phenom.
- x86-64-v2: Compatible with Intel CPU >= Nehalem, AMD CPU >= Opteron_G3. Added CPU flags compared to x86-64-v1: +cx16, +lahf-lm, +popcnt, +pni, +sse4.1, +sse4.2, +ssse3.

- x86-64-v2-AES: Compatible with Intel CPU >= Westmere, AMD CPU >= Opteron_G4. Added CPU flags
compared to x86-64-v2: +aes.

- x86-64-v3: Compatible with Intel CPU >= Haswell, AMD CPU >= EPYC. Added CPU flags compared to
x86-64-v2-AES: +avx, +avx2, +bmi1, +bmi2, +f16c, +fma, +movbe, +xsave.

- x86-64-v4: Compatible with Intel CPU >= Skylake, AMD CPU >= EPYC v4 Genoa. Added CPU flags
compared to x86-64-v3: +avx512f, +avx512bw, +avx512cd, +avx512dq, +avx512vl.
Custom CPU Types

You can specify custom CPU types with a configurable set of features. These are maintained in the configuration file /etc/pve/virtual-guest/cpu-models.conf by an administrator. See man cpu-models.c
for format details.
Specified custom types can be selected by any user with the Sys.Audit privilege on /nodes. When
configuring a custom CPU type for a VM via the CLI or API, the name needs to be prefixed with custom-.
Meltdown / Spectre related CPU flags
There are several CPU flags related to the Meltdown and Spectre vulnerabilities 3 which need to be set
manually unless the selected CPU type of your VM already enables them by default.
There are two requirements that need to be fulfilled in order to use these CPU flags:

- The host CPU(s) must support the feature and propagate it to the guest’s virtual CPU(s)
- The guest operating system must be updated to a version which mitigates the attacks and is able to utilize
the CPU feature
Otherwise you need to set the desired CPU flag of the virtual CPU, either by editing the CPU options in the
web UI, or by setting the flags property of the cpu option in the VM configuration file.
For Spectre v1,v2,v4 fixes, your CPU or system vendor also needs to provide a so-called “microcode update”
for your CPU, see chapter Firmware Updates. Note that not all affected CPUs can be updated to support
spec-ctrl.
To check if the Proxmox VE host is vulnerable, execute the following command as root:

for f in /sys/devices/system/cpu/vulnerabilities/*; do echo "${f##*/} -" $( ←cat "$f"); done
A community script is also available to detect if the host is still vulnerable. 4
3 Meltdown Attack https://meltdownattack.com/
4 spectre-meltdown-checker https://meltdown.ovh/


Intel processors

- pcid
This reduces the performance impact of the Meltdown (CVE-2017-5754) mitigation called Kernel PageTable Isolation (KPTI), which effectively hides the Kernel memory from the user space. Without PCID,
KPTI is quite an expensive mechanism 5 .
To check if the Proxmox VE host supports PCID, execute the following command as root:


```
# grep ' pcid ' /proc/cpuinfo
If this does not return empty your host’s CPU has support for pcid.
```


- spec-ctrl
Required to enable the Spectre v1 (CVE-2017-5753) and Spectre v2 (CVE-2017-5715) fix, in cases where
retpolines are not sufficient. Included by default in Intel CPU models with -IBRS suffix. Must be explicitly
turned on for Intel CPU models without -IBRS suffix. Requires an updated host CPU microcode (intelmicrocode >= 20180425).

- ssbd
Required to enable the Spectre V4 (CVE-2018-3639) fix. Not included by default in any Intel CPU model.
Must be explicitly turned on for all Intel CPU models. Requires an updated host CPU microcode(intelmicrocode >= 20180703).
AMD processors

- ibpb
Required to enable the Spectre v1 (CVE-2017-5753) and Spectre v2 (CVE-2017-5715) fix, in cases where
retpolines are not sufficient. Included by default in AMD CPU models with -IBPB suffix. Must be explicitly
turned on for AMD CPU models without -IBPB suffix. Requires the host CPU microcode to support this
feature before it can be used for guest CPUs.

- virt-ssbd
Required to enable the Spectre v4 (CVE-2018-3639) fix. Not included by default in any AMD CPU model.
Must be explicitly turned on for all AMD CPU models. This should be provided to guests, even if amd-ssbd
is also provided, for maximum guest compatibility. Note that this must be explicitly enabled when when
using the "host" cpu model, because this is a virtual feature which does not exist in the physical CPUs.

- amd-ssbd
Required to enable the Spectre v4 (CVE-2018-3639) fix. Not included by default in any AMD CPU model.
Must be explicitly turned on for all AMD CPU models. This provides higher performance than virt-ssbd,
therefore a host supporting this should always expose this to guests if possible. virt-ssbd should none the
less also be exposed for maximum guest compatibility as some kernels only know about virt-ssbd.

- amd-no-ssb
Recommended to indicate the host is not vulnerable to Spectre V4 (CVE-2018-3639). Not included by
default in any AMD CPU model. Future hardware generations of CPU will not be vulnerable to CVE-20183639, and thus the guest should be told not to enable its mitigations, by exposing amd-no-ssb. This is
mutually exclusive with virt-ssbd and amd-ssbd.
5 PCID

is now a critical performance/security feature on x86 https://groups.google.com/forum/m/#!topic/mechanicalsympathy/L9mHTbeQLNU


NUMA
You can also optionally emulate a NUMA 6 architecture in your VMs. The basics of the NUMA architecture
mean that instead of having a global memory pool available to all your cores, the memory is spread into
local banks close to each socket. This can bring speed improvements as the memory bus is not a bottleneck
anymore. If your system has a NUMA architecture 7 we recommend to activate the option, as this will allow
proper distribution of the VM resources on the host system. This option is also required to hot-plug cores or
RAM in a VM.
If the NUMA option is used, it is recommended to set the number of sockets to the number of nodes of the
host system.

vCPU hot-plug
Modern operating systems introduced the capability to hot-plug and, to a certain extent, hot-unplug CPUs
in a running system. Virtualization allows us to avoid a lot of the (physical) problems real hardware can
cause in such scenarios. Still, this is a rather new and complicated feature, so its use should be restricted
to cases where its absolutely needed. Most of the functionality can be replicated with other, well tested and
less complicated, features, see Resource Limits.
In Proxmox VE the maximal number of plugged CPUs is always cores * sockets. To start a VM with
less than this total core count of CPUs you may use the vcpus setting, it denotes how many vCPUs should
be plugged in at VM start.
Currently this feature is only supported on Linux, a kernel newer than 3.10 is needed, a kernel newer than

## 4.7 is recommended.

You can use a udev rule as follow to automatically set new CPUs as online in the guest:

SUBSYSTEM=="cpu", ACTION=="add", TEST=="online", ATTR{online}=="0", ATTR{ ←online}="1"
Save this under /etc/udev/rules.d/ as a file ending in .rules.
Note: CPU hot-remove is machine dependent and requires guest cooperation. The deletion command does
not guarantee CPU removal to actually happen, typically it’s a request forwarded to guest OS using target
dependent mechanism, such as ACPI on x86/amd64.


### 10.2.6 Memory


For each VM you have the option to set a fixed size memory or asking Proxmox VE to dynamically allocate
memory based on the current RAM usage of the host.
6 https://en.wikipedia.org/wiki/Non-uniform_memory_access
7 if the command numactl

a NUMA architecture

- `--hardware` | grep available returns more than one node, then your host system has


Fixed Memory Allocation

When setting memory and minimum memory to the same amount Proxmox VE will simply allocate what you
specify to your VM.
Even when using a fixed memory size, the ballooning device gets added to the VM, because it delivers useful
information such as how much memory the guest really uses. In general, you should leave ballooning
enabled, but if you want to disable it (like for debugging purposes), simply uncheck Ballooning Device or
set

balloon: 0
in the configuration.
Automatic Memory Allocation
When setting the minimum memory lower than memory, Proxmox VE will make sure that the minimum
amount you specified is always available to the VM, and if RAM usage on the host is below a certain target
percentage, will dynamically add memory to the guest up to the maximum memory specified. The target
percentage defaults to 80% and can be configured in the node options.
When the host is running low on RAM, the VM will then release some memory back to the host, swapping
running processes if needed and starting the oom killer in last resort. The passing around of memory
between host and guest is done via a special balloon kernel driver running inside the guest, which will
grab or release memory pages from the host. 8
When multiple VMs use the autoallocate facility, it is possible to set a Shares coefficient which indicates
the relative amount of the free host memory that each VM should take. Suppose for instance you have four
VMs, three of them running an HTTP server and the last one is a database server. The host is configured
to target 80% RAM usage. To cache more database blocks in the database server RAM, you would like to
prioritize the database VM when spare RAM is available. For this you assign a Shares property of 3000 to
the database VM, leaving the other VMs to the Shares default setting of 1000. The host server has 32GB of
8 A good explanation of the inner workings of the balloon driver can be found here https://rwmj.wordpress.com/2010/07/17/-

virtio-balloon/


RAM, and is currently using 16GB, leaving 32 * 80/100 - 16 = 9GB RAM to be allocated to the VMs on top
of their configured minimum memory amount. The database VM will benefit from 9 * 3000 / (3000 + 1000 +
1000 + 1000) = 4.5 GB extra RAM and each HTTP server from 1.5 GB.
All Linux distributions released after 2010 have the balloon kernel driver included. For Windows OSes, the
balloon driver needs to be added manually and can incur a slowdown of the guest, so we don’t recommend
using it on critical systems.
When allocating RAM to your VMs, a good rule of thumb is always to leave 1GB of RAM available to the
host.


## See also

- [VM Settings: Hardware](vm-settings-hardware.md)
- [VM Memory Encryption and Display](vm-memory-encryption-display.md)
- [VM USB, Audio, PCI and Boot Options](vm-usb-pci-boot.md)
- [QEMU/KVM Overview](_index.md)
