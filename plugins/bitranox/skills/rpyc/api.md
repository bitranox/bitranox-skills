# API Reference

## Serialization

- [Brine](api/core_brine.md) - A simple and fast serialization format for immutable data (numbers, string, tuples, etc.). Brine is the "over-the-wire" encoding format of RPyC.
- [Vinegar](api/core_brine.md#vinegar) - A configurable serializer for exceptions. Vinegar extracts the exception's details and stores them in a brine-friendly format.

## IO Layer

- [Streams](api/core_stream.md) - The stream layer (byte-oriented, platform-agnostic streams)
- [Channel](api/core_stream.md#channel) - The channel layer (framing and compression)

## Protocol

- [Protocol](api/core_protocol.md) - The RPyC protocol (`Connection` class)
- [Service](api/core_service.md) - The RPyC service model
- [Netref](api/core_netref.md) - Implementation of transparent object proxies (netrefs)
- [Async](api/core_netref.md#async) - Asynchronous object proxies (netrefs)

## Server-Side

- [Server](api/utils_server.md) - The core implementation of RPyC servers; includes the implementation of the forking and threaded servers.
- [Registry](api/utils_registry.md) - Implementation of the Service Registry; the registry is a bonjour-like discovery agent, with which RPyC servers register themselves, and allows clients to locate different servers by name.
- [Authenticators](api/utils_authenticators.md) - Implementation of two common authenticators, for SSL and TLSlite.

## Client-Side

- [Factories](api/utils_factory.md) - general-purpose connection factories (over pipes, sockets, SSL, SSH, TLSlite, etc.)
- [Classic](api/utils_classic.md) - *Classic-mode* factories and utilities
- [Helpers](api/utils_classic.md#helpers) - Various helpers (`timed`, `async_`, `buffiter`, `BgServingThread`, etc.)

## Misc

- [Zero-Deploy](api/utils_zerodeploy.md) - Deploy short-living RPyC servers on remote machines with ease - all you'll need is SSH access and a Python interpreter installed on the host
