<div style="float:right; margin:1em 0em 1em 1em; padding: 0em 1em 1em 1em;">
<a href="http://tomerfiliba.com" target="_blank">
<img style="display: block; margin-left: auto; margin-right: auto" alt="Tomer Filiba"
src="_static/fish-text-black.png" title="Tomer's Blog"/>
<span style="color:transparent;position: absolute;font-size:5px;width: 0px;height: 0px;">Tomer Filiba</span></a>
<br/>
</div>

# RPyC - Transparent, Symmetric Distributed Computing

<div class="admonition note">

A new version has been released!

Be sure to read the [changelog](changelog.md) before upgrading!

Please use the [github issues](https://github.com/tomerfiliba/rpyc/issues) to ask questions report problems. **Please do not email me directly**

</div>

**RPyC** (pronounced as *are-pie-see*), or *Remote Python Call*, is a **transparent** [python](https://www.python.org/) library for **symmetrical** [remote procedure calls](https://en.wikipedia.org/wiki/Remote_procedure_calls), [clustering](https://en.wikipedia.org/wiki/Clustering) and [distributed-computing](http://en.wikipedia.org/wiki/Distributed_computing). RPyC makes use of [object-proxying](http://en.wikipedia.org/wiki/Proxy_pattern), a technique that employs python's dynamic nature, to overcome the physical boundaries between processes and computers, so that remote objects can be manipulated as if they were local.

<figure>
<img src="_static/screenshot.png" alt="_static/screenshot.png" />
<figcaption>A screenshot of a Windows client connecting to a Linux server. Note that text written to the server's <code>stdout</code> is actually printed on the server's console.</figcaption>
</figure>

## Getting Started

[Installing](install.md) RPyC is as easy as `pip install rpyc`.

If you're new to RPyC, be sure to check out the [Tutorial](tutorial.md). Next, refer to the [Documentation](docs.md) and [API Reference](api.md), as well as the [Mailing List](install.md#mailing-list).

For an introductory reading (that may or may not be slightly outdated), David Mertz wrote a very thorough [Charming Python](https://web.archive.org/web/20160928013509/http://www.ibm.com/developerworks/linux/library/l-rpyc/) installment about RPyC, explaining how it's different from existing alternatives (Pyro, XMLRPC, etc.), what roles it can play, and even show-cases some key features of RPyC (like the security model, remote monkey-patching, or remote resource utilization).

## Features

- **Transparent** - access to remote objects as if they were local; existing code works seamlessly with both local or remote objects.
- **Symmetric** - the protocol itself is completely symmetric, meaning both client and server can serve requests. This allows, among other things, for the server to invoke [callbacks](http://en.wikipedia.org/wiki/Callback_(computer_science)) on the client side.
- **Synchronous** and [asynchronous](docs/async.md) operation
- **Platform Agnostic** - 32/64 bit, little/big endian, Windows/Linux/Solaris/Mac... access objects across different architectures.
- **Low Overhead** - RpyC takes an *all-in-one* approach, using a compact binary protocol, and requiring no complex setup (name servers, HTTP, URL-mapping, etc.)
- **Secure** - employs a [Capability based](https://en.wikipedia.org/wiki/Capability-based_security) security model; integrates easily with SSH
- **Zero-Deploy Enabled** -- Read more about [Zero-Deploy RPyC](docs/zerodeploy.md)
- **Integrates** with [TLS/SSL](https://en.wikipedia.org/wiki/Transport_Layer_Security), [SSH](https://en.wikipedia.org/wiki/Secure_Shell) and [inetd](https://en.wikipedia.org/wiki/Inetd).

## Use Cases

- Excels in testing environments -- run your tests from a central machine offering a convenient development environment, while the actual operations take place on remote ones.
- Control/administer multiple hardware or software platforms from a central point: any machine that runs Python is at your hand! No need to master multiple shell-script languages (BASH, Windows batch files, etc.) and use awkward tools (`awk`, `sed`, `grep`, ...)
- Access remote hardware resources transparently. For instance, suppose you have some proprietary electronic testing equipment that comes with drivers only for HPUX, but no one wants to actually use HPUX... just connect to the machine and use the remote `ctypes` module (or open the `/dev` file directly).
- [Monkey-patch](http://en.wikipedia.org/wiki/Monkey_patch) local code or remote code. For instance, using monkey-patching you can cross network boundaries by replacing the `socket` module of one program with a remote one. Another example could be replacing the `os` module of your program with a remote module, causing `os.system` (for instance) to run remotely.
- Distributing workload among multiple machines with ease
- Implement remote services (like [WSDL](https://en.wikipedia.org/wiki/WSDL) or [RMI](https://en.wikipedia.org/wiki/Java_remote_method_invocation)) quickly and concisely (without the overhead and limitations of these technologies)

## Contents

- [Install](install.md)
- [Tutorial](tutorial.md)
- [Documentation](docs.md)
- [API Reference](api.md)
- [License](license.md)
- [Changelog](changelog.md)
