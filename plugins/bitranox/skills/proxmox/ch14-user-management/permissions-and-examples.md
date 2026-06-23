# Permission Management and Examples

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

- VM.GuestAgent.FileSystemMgmt: freeze/thaw/trim file systems via QEMU guest agent
- VM.GuestAgent.FileWrite: write files in the guest via QEMU guest agent
- VM.GuestAgent.Unrestricted: issue arbitrary QEMU guest agent commands
- VM.Migrate: migrate VM to alternate server on cluster
- VM.PowerMgmt: power management (start, stop, reset, shutdown, . . . )
- VM.Replicate: configure and run guest replication
- VM.Snapshot.Rollback: rollback VM to one of its snapshots
- VM.Snapshot: create/delete VM snapshots
Storage related privileges

- Datastore.Allocate: create/modify/remove a datastore and delete volumes
- Datastore.AllocateSpace: allocate space on a datastore
- Datastore.AllocateTemplate: allocate/upload templates and ISO images
- Datastore.Audit: view/browse a datastore

> **Warning:**
> Both Permissions.Modify and Sys.Modify should be handled with care, as they allow
> modifying aspects of the system and its configuration that are dangerous or sensitive.


> **Warning:**
> Carefully read the section about inheritance below to understand how assigned roles (and their
> privileges) are propagated along the ACL tree.


### 14.7.3 Objects and Paths


Access permissions are assigned to objects, such as virtual machines, storages or resource pools. We use
file system like paths to address these objects. These paths form a natural tree, and permissions of higher
levels (shorter paths) can optionally be propagated down within this hierarchy.
Paths can be templated. When an API call requires permissions on a templated path, the path may contain
references to parameters of the API call. These references are specified in curly braces. Some parameters
are implicitly taken from the API call’s URI. For instance, the permission path /nodes/{node} when
calling /nodes/mynode/status requires permissions on /nodes/mynode, while the path {path} in a
PUT request to /access/acl refers to the method’s path parameter.
Some examples are:

- /nodes/{node}: Access to Proxmox VE server machines
- /vms: Covers all VMs
- /vms/{vmid}: Access to specific VMs


- /storage/{storeid}: Access to a specific storage
- /pool/{poolname}: Access to resources contained in a specific pool
- /access/groups: Group administration
- /access/realms/{realmid}: Administrative access to realms
Inheritance
As mentioned earlier, object paths form a file system like tree, and permissions can be inherited by objects
down that tree (the propagate flag is set by default). We use the following inheritance rules:

- Permissions for individual users always replace group permissions.
- Permissions for groups apply when the user is member of that group.
- Permissions on deeper levels replace those inherited from an upper level.
- NoAccess cancels all other roles on a given path.
Additionally, privilege separated tokens can never have permissions on any given path that their associated
user does not have.


### 14.7.4 Pools


Pools can be used to group a set of virtual machines and datastores. You can then simply set permissions
on pools (/pool/{poolid}), which are inherited by all pool members. This is a great way to simplify
access control.


### 14.7.5 Which Permissions Do I Need?


The required API permissions are documented for each individual method, and can be found at https://pve.proxmox.
pve-docs/api-viewer/.
The permissions are specified as a list, which can be interpreted as a tree of logic and access-check functions:

["and", <subtests>...] and ["or", <subtests>...]
Each(and) or any(or) further element in the current list has to be true.
["perm", <path>, [ <privileges>... ], <options>...]
The path is a templated parameter (see Objects and Paths). All (or, if the any option is used, any) of
the listed privileges must be allowed on the specified path. If a require-param option is specified,
then its specified parameter is required even if the API call’s schema otherwise lists it as being optional.

["userid-group", [ <privileges>...

], <options>...]

The caller must have any of the listed privileges on /access/groups. In addition, there are two
possible checks, depending on whether the groups_param option is set:


- groups_param is set: The API call has a non-optional groups parameter and the caller must
have any of the listed privileges on all of the listed groups.

- groups_param is not set: The user passed via the userid parameter must exist and be part of
a group on which the caller has any of the listed privileges (via the /access/groups/<group>
path).

["userid-param", "self"]
The value provided for the API call’s userid parameter must refer to the user performing the action
(usually in conjunction with or, to allow users to perform an action on themselves, even if they don’t
have elevated privileges).

["userid-param", "Realm.AllocateUser"]
The user needs Realm.AllocateUser access to /access/realm/<realm>, with <realm>
referring to the realm of the user passed via the userid parameter. Note that the user does
not need to exist in order to be associated with a realm, since user IDs are passed in the form of
<username>@<realm>.

["perm-modify", <path>]
The path is a templated parameter (see Objects and Paths). The user needs either the Permissions.Mo
privilege or, depending on the path, the following privileges as a possible substitute:

- /storage/...: requires ’Datastore.Allocate`
- /vms/...: requires ’VM.Allocate`
- /pool/...: requires ’Pool.Allocate`
If the path is empty, Permissions.Modify on /access is required.
If the user does not have the Permissions.Modify privilege, they can only delegate subsets of
their own privileges on the given path (e.g., a user with PVEVMAdmin could assign PVEVMUser,
but not PVEAdmin).


## 14.8 Command-line Tool


Most users will simply use the GUI to manage users. But there is also a fully featured command-line tool
called pveum (short for “Proxmox VE User Manager”). Please note that all Proxmox VE command-line tools
are wrappers around the API, so you can also access those functions through the REST API.
Here are some simple usage examples. To show help, type:

pveum
or (to show detailed help about a specific command)


```
pveum help user add
```

Create a new user:


```
pveum user add testuser@pve -comment "Just a test"
```

Set or change the password (not all realms support this):


```
pveum passwd testuser@pve
```

Disable a user:


```
pveum user modify testuser@pve -enable 0
```

Create a new group:


```
pveum group add testgroup
```

Create a new role:


```
pveum role add PVE_Power-only -privs "VM.PowerMgmt VM.Console"
```


## 14.9 Real World Examples


### 14.9.1 Administrator Group


It is possible that an administrator would want to create a group of users with full administrator rights (without
using the root account).
To do this, first define the group:


```
pveum group add admin -comment "System Administrators"
```

Then assign the role:


```
pveum acl modify / -group admin -role Administrator
```

Finally, you can add users to the new admin group:


```
pveum user modify testuser@pve -group admin
```


### 14.9.2 Auditors


You can give read only access to users by assigning the PVEAuditor role to users or groups.
Example 1: Allow user joe@pve to see everything


```
pveum acl modify / -user joe@pve -role PVEAuditor
```

Example 2: Allow user joe@pve to see all virtual machines


```
pveum acl modify /vms -user joe@pve -role PVEAuditor
```


### 14.9.3 Delegate User Management


If you want to delegate user management to user joe@pve, you can do that with:


```
pveum acl modify /access -user joe@pve -role PVEUserAdmin
```

User joe@pve can now add and remove users, and change other user attributes, such as passwords.
This is a very powerful role, and you most likely want to limit it to selected realms and groups. The following
example allows joe@pve to modify users within the realm pve, if they are members of group customers:


```
pveum acl modify /access/realm/pve -user joe@pve -role PVEUserAdmin
```


```
pveum acl modify /access/groups/customers -user joe@pve -role PVEUserAdmin
```


> **Note:**
> The user is able to add other users, but only if they are members of the group customers and within
> the realm pve.


### 14.9.4 Limited API Token for Monitoring


Permissions on API tokens are always a subset of those of their corresponding user, meaning that an API
token can’t be used to carry out a task that the backing user has no permission to do. This section will
demonstrate how you can use an API token with separate privileges, to limit the token owner’s permissions
further.
Give the user joe@pve the role PVEVMAdmin on all VMs:


```
pveum acl modify /vms -user joe@pve -role PVEVMAdmin
```

Add a new API token with separate privileges, which is only allowed to view VM information (for example, for
monitoring purposes):


```
pveum user token add joe@pve monitoring -privsep 1
```


```
pveum acl modify /vms -token 'joe@pve!monitoring' -role PVEAuditor
```

Verify the permissions of the user and token:


```
pveum user permissions joe@pve
```


```
pveum user token permissions joe@pve monitoring
```


### 14.9.5 Resource Pools


An enterprise is usually structured into several smaller departments, and it is common that you want to
assign resources and delegate management tasks to each of these. Let’s assume that you want to set up a
pool for a software development department. First, create a group:


```
pveum group add developers -comment "Our software developers"
```

Now we create a new user which is a member of that group:


```
pveum user add developer1@pve -group developers -password
```


> **Note:**
> The "-password" parameter will prompt you for a password


Then we create a resource pool for our development department to use:


```
pveum pool add dev-pool --comment "IT development pool"
```

Finally, we can assign permissions to that pool:


```
pveum acl modify /pool/dev-pool/ -group developers -role PVEAdmin
```

Our software developers can now administer the resources assigned to that pool.
