# Kernel Samepage Merging (KSM)

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

# mokutil --import /var/lib/dkms/mok.pub
input password:
input password again:
The mokutil command will ask for a (temporary) password twice, this password needs to be entered
one more time in the next step of the process! Rebooting the system should automatically boot into the
MOKManager EFI binary, which allows you to verify the key/certificate and confirm the enrollment using
the password selected when starting the enrollment using mokutil. Afterwards, the kernel should allow
loading modules built with DKMS (which are signed with the enrolled MOK). The MOK can also be used to
sign custom EFI binaries and kernel images if desired.
The same procedure can also be used for custom/third-party modules not managed with DKMS, but the
key/certificate generation and signing steps need to be done manually in that case.


## 3.14 Kernel Samepage Merging (KSM)


Kernel Samepage Merging (KSM) is an optional memory deduplication feature offered by the Linux kernel,
which is enabled by default in Proxmox VE. KSM works by scanning a range of physical memory pages for
identical content, and identifying the virtual pages that are mapped to them. If identical pages are found,
the corresponding virtual pages are re-mapped so that they all point to the same physical page, and the old
pages are freed. The virtual pages are marked as "copy-on-write", so that any writes to them will be written
to a new area of memory, leaving the shared physical page intact.


### 3.14.1 Implications of KSM


KSM can optimize memory usage in virtualization environments, as multiple VMs running similar operating
systems or workloads could potentially share a lot of common memory pages.
However, while KSM can reduce memory usage, it also comes with some security risks, as it can expose
VMs to side-channel attacks. Research has shown that it is possible to infer information about a running VM
via a second VM on the same host, by exploiting certain characteristics of KSM.
Thus, if you are using Proxmox VE to provide hosting services, you should consider disabling KSM, in order
to provide your users with additional security. Furthermore, you should check your country’s regulations, as
disabling KSM may be a legal requirement.


### 3.14.2 Disabling KSM


KSM can be disabled on a node or on a per-VM basis.

Disabe KSM on a Node
To see if KSM is active on a node, you can check the output of:


```
# systemctl status ksmtuned
If it is, it can be disabled immediately with:
```


```
# systemctl disable --now ksmtuned
Finally, to unmerge all the currently merged pages, run:

# echo 2 > /sys/kernel/mm/ksm/run
```


Disabe KSM for a Specific VM
The allow-ksm VM configuration option controls whether memory page merging is allowed for a given
VM. The option defaults to true and can be disabled with:


```
# qm set <vmid> --allow-ksm 0
```

