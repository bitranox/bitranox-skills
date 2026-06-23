# Package Repositories

*[Chapter Index](_index.md) | [Main Index](../SKILL.md)*

The following sections will focus on common virtualization tasks and explain the Proxmox VE specifics regarding the administration and management of the host machine.
Proxmox VE is based on Debian GNU/Linux with additional repositories to provide the Proxmox VE related
packages. This means that the full range of Debian packages is available including security updates and
bug fixes. Proxmox VE provides its own Linux kernel based on the Ubuntu kernel. It has all the necessary
virtualization and container features enabled and includes ZFS and several extra hardware drivers.
For other topics not included in the following sections, please refer to the Debian documentation. The Debian Administrator’s Handbook is available online, and provides a comprehensive introduction to the Debian
operating system (see [Hertzog13]).


## 3.1 Package Repositories


Proxmox VE uses APT as its package management tool like any other Debian-based system.
Proxmox VE automatically checks for package updates on a daily basis. The root@pam user is notified via
email about available updates. From the GUI, the Changelog button can be used to see more details about
an selected update.


### 3.1.1 Repositories in Proxmox VE


Repositories are a collection of software packages, they can be used to install new software, but are also
important to get new updates.

> **Note:**
> You need valid Debian and Proxmox repositories to get the latest security updates, bug fixes and new
> features.


APT Repositories are defined in the file /etc/apt/sources.list in the legacy single-line format and
in .sources files placed in /etc/apt/sources.list.d/ for the modern deb822 multi-line format,
see Repository Formats for details.


Repository Management

Since Proxmox VE 7, you can check the repository state in the web interface. The node summary panel
shows a high level status overview, while the separate Repository panel shows in-depth status and list of all
configured repositories.
Basic repository management, for example, activating or deactivating a repository, is also supported.
The available packages from a repository are acquired by running apt update. Updates can be installed
directly using apt, or via the GUI (Node → Updates).

Repository Formats
Package repositories can be configured in the source list /etc/apt/sources.list and the files contained in
/etc/apt/sources.list.d/.
There are two formats supported:

single line
In a single-line sources.list file, each line defines a package repository. Empty lines are ignored.
A # character anywhere on a line marks the remainder of that line as a comment. This is the legacy
format. Since Debian 13 Trixie apt will complain about using this format. You can automatically migrate
most repositories using the apt modernize-sources command.
deb822
In the multi-line format repo.sources file each entry consists of multiple lines of key-value pairs. A
file can include multiple entries by separating each group with a blank line. This is the modern format.


Available Repositories
Proxmox VE provides three different package repositories in addition to requiring the base Debian repositories.


### 3.1.2 Debian Base Repositories


File /etc/apt/sources.list.d/debian.sources

Types: deb deb-src
URIs: http://deb.debian.org/debian/
Suites: trixie trixie-updates
Components: main non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
Types: deb deb-src
URIs: http://security.debian.org/debian-security/
Suites: trixie-security
Components: main non-free-firmware
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg


### 3.1.3 Proxmox VE Enterprise Repository


This is the recommended repository and available for all Proxmox VE subscription users. It contains the
most stable packages and is suitable for production use. The pve-enterprise repository is enabled by
default:

File /etc/apt/sources.list.d/pve-enterprise.sources

Types: deb
URIs: https://enterprise.proxmox.com/debian/pve
Suites: trixie
Components: pve-enterprise
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg
Please note that you need a valid subscription key to access the pve-enterprise repository. We offer
different support levels, which you can find further details about at https://proxmox.com/en/proxmox-virtualenvironment/pricing.

> **Note:**
> You can disable this repository by adding an Enabled: no line to the relevant entry in the file. This
> will prevent error messages if your host does not have a subscription key. In that case, please configure
> the pve-no-subscription repository.


### 3.1.4 Proxmox VE No-Subscription Repository


As the name suggests, you do not need a subscription key to access this repository. It can be used for
testing and non-production use. It’s not recommended to use this on production servers, as these packages
are not always as heavily tested and validated.
We recommend to configure this repository in /etc/apt/sources.list.d/proxmox.sources.

File /etc/apt/sources.list.d/proxmox.sources

Types: deb
URIs: http://download.proxmox.com/debian/pve
Suites: trixie
Components: pve-no-subscription
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg


> **Note:**
> Remember that you will always need the base Debian repositories in addition to a Proxmox VE Proxmox
> repository.


### 3.1.5 Proxmox VE Test Repository


This repository contains the latest packages and is primarily used by developers to test new features. To
configure it, add the following stanza to the file /etc/apt/sources.list.d/proxmox.sources:

File /etc/apt/sources.list.d/proxmox.sources

Types: deb
URIs: http://download.proxmox.com/debian/pve
Suites: trixie
Components: pve-test
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg


> **Warning:**
> The pve-test repository should (as the name implies) only be used for testing new features or
> bug fixes.


### 3.1.6 Ceph Repositories


Ceph-related packages are kept up to date with a preconfigured Ceph enterprise repository. Preinstalled
packages enable connecting to an external Ceph cluster and adding its RBD or CephFS pools as storage.
You can also build a hyper-converged infrastructure (HCI) by running Ceph on top of the Proxmox VE cluster.
Information from this chapter is helpful in the following cases:


Installing Ceph to build an HCI
Decide on a below described repository and recent Ceph release, which you can then select in the
web-based wizard or the CLI tool.
Already running the HCI and want to upgrade to the succeeding Ceph major release
Please follow the related Ceph upgrade guide.
Already running the HCI and want to upgrade to the succeeding Proxmox VE major release
In an HCI each Proxmox VE major release requires a corresponding minimum Ceph major release,
please follow the related Proxmox VE upgrade guide.
Not running an HCI but using an external Ceph cluster
To install newer packages used to connect to Ceph, apply available system updates, decide on a
repository and Ceph release listed below, add it to your node via the Repository panel, apply newly
available system updates, verify the result by running ceph --version and disable the old Ceph
repository.
Ceph releases available in Proxmox VE 9
To read the latest version of the admin guide for your Proxmox VE release, make sure that all system updates
are installed and that this page has been reloaded.

ceph-squid

Estimated End-of-Life
2026-09 (v19.2)

enterprise
recommended

no-subscription
available

test
available

Ceph repositories for Proxmox VE 9
The content of the ceph.sources file below serves as a reference (prior to Proxmox VE 9 the file
ceph.list was used). To make changes, please follow the case that applies to your situation as described at the beginning of this subchapter. If you have disabled a repository in the web UI and also want to
delist it, you can manually remove the corresponding entry from the file.

enterprise
This repository is recommended for production use and contains the most stable package versions. It is
accessible if the Proxmox VE node has a valid subscription of any level. For details and included customer
support levels visit:
https://proxmox.com/en/proxmox-virtual-environment/pricing
File /etc/apt/sources.list.d/ceph.sources

Types: deb
URIs: https://enterprise.proxmox.com/debian/ceph-squid
Suites: trixie
Components: enterprise
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg

no-subscription
This repository is suitable for testing and for non-production use. It is freely accessible and does not require a
valid subscription. After some time, its package versions are also made available in the enterprise repository.


File /etc/apt/sources.list.d/ceph.sources

Types: deb
URIs: http://download.proxmox.com/debian/ceph-squid
Suites: trixie
Components: no-subscription
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg

test
This repository contains the latest package versions and is primarily used by developers to test new features
and bug fixes.

File /etc/apt/sources.list.d/ceph.sources

Types: deb
URIs: http://download.proxmox.com/debian/ceph-squid
Suites: trixie
Components: test
Signed-By: /usr/share/keyrings/proxmox-archive-keyring.gpg


> **Warning:**
> The Ceph test repository should (as the name implies) only be used for testing new features or
> bug fixes.


### 3.1.7 Debian Firmware Repository


Starting with Debian Bookworm (Proxmox VE 8) non-free firmware (as defined by DFSG) has been moved
to the newly created Debian repository component non-free-firmware.
Since Proxmox VE 9 this repository is enabled by default for new installations to ensure they can get Early
OS Microcode Updates.
You can also acquire need additional Runtime Firmware Files not already included in the pre-installed package pve-firmware.
To be able to install packages from this component, run editor /etc/apt/sources.list, append
non-free-firmware to the end of each .debian.org repository line and run apt update.

If you upgraded your Proxmox VE 9 install from a previous version of Proxmox VE and have modernized your
package repositories to the new deb822-style, you will need to adapt /etc/apt/sources.list.d/debian.
instead. Run editor /etc/apt/sources.list.d/debian.sources and add non-free-firmwar
to the lines starting with Components: of each stanza.

> **Note:**
> Modernizing your package repositories is recommended. Otherwise, apt on Debian Trixie will complain.
> You can run apt modernize-sources to do so.


### 3.1.8 SecureApt


The Release files in the repositories are signed with GnuPG. APT is using these signatures to verify that all
packages are from a trusted source.
If you install Proxmox VE from an official ISO image, the key for verification is already installed.
If you install Proxmox VE on top of Debian, download and install the key with the following commands:


```
# wget https://enterprise.proxmox.com/debian/proxmox-archive-keyring- ←trixie.gpg -O /usr/share/keyrings/proxmox-archive-keyring.gpg
```


> **Note:**
> The wget command above adds the keyring for Proxmox releases based on Debian Trixie. Once the
> proxmox-archive-keyring package is installed, it will manage this file. At that point, the hashes
> below may no longer match the hashes of this file, as keys for new Proxmox releases get added or
> removed. This is intended, apt will ensure that only trusted keys are being used. Modifying this file is
> discouraged once proxmox-archive-keyring is installed.


Verify the checksum afterwards with the sha512sum CLI tool:

# sha256sum /usr/share/keyrings/proxmox-archive-keyring.gpg
136673be77aba35dcce385b28737689ad64fd785a797e57897589aed08db6e45 /usr/ ←share/keyrings/proxmox-archive-keyring.gpg
or the md5sum CLI tool:

# md5sum /usr/share/keyrings/proxmox-archive-keyring.gpg
77c8b1166d15ce8350102ab1bca2fcbf /usr/share/keyrings/proxmox-archive- ←keyring.gpg


> **Note:**
> Make sure the path you install the key to matches the Signed-By: lines in your repository stanzas.


## 3.2 System Software Updates


Proxmox provides updates on a regular basis for all repositories. To install updates use the web-based GUI
or the following CLI commands:


```
# apt-get update
# apt-get dist-upgrade
For occasionally upgrading Ceph to its succeeding major release, see Ceph Repositories.
Note
The APT package management system is very flexible and provides many features, see man apt-get,
or [Hertzog13] for additional information.
```


## See also

- [System Software Updates](software-updates.md)

