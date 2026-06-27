# Documentation

## Introduction

- [A little about RPyC](docs/about.md) - related projects, contributors, and logo issues
- [Theory of Operation](docs/theory.md) - background on the inner workings of RPyC and the terminology
- [Use cases](docs/usecases.md) - some common use-cases, demonstrating the power and ease of RPyC
- [How to's](docs/howto.md) - solutions to specific problems

## Reference

- [Servers](docs/servers.md) - using the built-in servers and writing custom ones
- [Classic RPyC](docs/classic.md) - using RPyC in *slave mode* (AKA *classic mode*), where the client has unrestricted control over the server.
- [RPyC Services](docs/services.md) - writing well-defined services which restrict the operations a client (or server) can carry out.
- [Asynchronous Operation](docs/async.md) - invoking operations in the background, without having to wait for them to finish.
- [Security Concerns](docs/security.md) - keeping security in mind when using RPyC
- [Secure Connections](docs/secure-connection.md) - create an encrypted and authenticated connection over SSL or SSH
- [Zero-Deploy](docs/zerodeploy.md) - spawn temporary, short-lived RPyC server on remote machine with nothing more than SSH and a Python interpreter
- [Advanced Debugging](docs/advanced-debugging.md) - debugging at the packet level
