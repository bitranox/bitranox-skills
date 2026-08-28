# Container Images

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

## 11.3 Container Images


Container images, sometimes also referred to as "templates" or "appliances", are tar archives which
contain everything to run a container. Proxmox VE can utilize two main types of images: System
Container Templates for creating full virtual environments, and Application Container Images based
on the OCI standard for running specific applications.


### 11.3.1 System Container Templates


Proxmox VE itself provides a variety of basic templates for the most common Linux distributions.
They can be downloaded using the GUI or the pveam (short for Proxmox VE Appliance Manager)
command-line utility. Additionally, TurnKey Linux container templates are also available to
download.

The list of available templates is updated daily through the pve-daily-update timer. You can also
trigger an update manually by executing:

```
# pveam update
```

To view the list of available images run:

```
# pveam available
```

You can restrict this large list by specifying the section you are interested in, for example basic
system images:

```
# pveam available --section system
system          alpine-3.12-default_20200823_amd64.tar.xz
system          debian-10-standard_10.7-1_amd64.tar.gz
system          ubuntu-20.04-standard_20.04-1_amd64.tar.gz
```

Three rows shown; the real listing is longer and its contents change with every template refresh,
so read your own `pveam available` output rather than this sample.

Before you can use such a template, you need to download them into one of your storages. If you are
unsure to which one, you can simply use the local named storage for that purpose. For clustered
installations, it is preferred to use a shared storage so that all nodes can access those images.

```
# pveam download local debian-10.0-standard_10.0-1_amd64.tar.gz
```

You are now ready to create containers using that image, and you can list all downloaded images on
storage local with:

```
# pveam list local
local:vztmpl/debian-10.0-standard_10.0-1_amd64.tar.gz  219.95MB
```

You can also use the Proxmox VE web interface GUI to download, list and delete container templates.

pct uses them to create a new container, for example:

```
# pct create 999 local:vztmpl/debian-10.0-standard_10.0-1_amd64.tar.gz
```

The above command shows you the full Proxmox VE volume identifiers. They include the storage name,
and most other Proxmox VE commands can use them. For example you can delete that image later with:

```
# pveam remove local:vztmpl/debian-10.0-standard_10.0-1_amd64.tar.gz
```


### 11.3.2 Open Container Initiative (OCI) Images


Proxmox VE can also use OCI images to create containers, both system containers but also
application containers. Note that running application containers in Proxmox VE is currently
considered a technology preview.

A container created from an OCI image still uses the existing LXC framework.


### 11.3.3 Obtaining OCI Images


In the web interface an OCI image can be uploaded manually or pulled from a registry using the
Pull from OCI registry button on the container template view of a storage.

Once the template is on a storage, you can create the container with pct create or use the wizard
in the web interface.


## See also

- [Container Settings](container-settings.md)
- [Technology Overview and Distributions](technology-and-distributions.md)
- [Linux Containers](_index.md)
