# Reaching a VM console with an external VNC viewer

The GUI console is noVNC over a websocket. To point another VNC client (a desktop viewer, an
automation library) at a VM, there are two routes, and the obvious third one fails. Measured on
PVE 9.2; the port's TLS behaviour below was observed, not explained.

## Route 1: the API's one-shot port

`POST /nodes/<node>/qemu/<vmid>/vncproxy` WITHOUT `websocket` opens a one-shot listening port (the
next free one from 5900) on ALL addresses of the node, for one connection:

```bash
pvesh create /nodes/<node>/qemu/<vmid>/vncproxy --generate-password 1 --output-format json
#   -> read "port" and "password" from the response
```

Connect a PLAIN VNC client to `<node>:<port>` and answer VNC Authentication with the returned
`password`, promptly (it is short-lived). A TLS client on the same port was refused: the
connection closed. The code sets the listener up with `IO::Socket::SSL` (`SSL_server => 1`), yet
the stream measured plain, so test the client you mean to use rather than reasoning from the
source. The port listens on every address while it waits: allow it only from where the viewer
runs (PVE firewall), and do not leave unused tickets open.

## Route 2: `qm vncproxy` over ssh

`qm vncproxy <vmid>` proxies the VM's VNC socket to stdin/stdout, so it can sit at the far end of
an ssh pipe. It needs the `LC_PVE_TICKET` environment variable: that value becomes the VNC
password (valid for about 30 seconds), so pass it through ssh (`SendEnv`/`SetEnv LC_PVE_TICKET`,
which sshd accepts for `LC_*` on a default Debian config) and have the viewer authenticate with
the same value.

## What does not work: a bare tunnel to the socket

`ssh -L <port>:/var/run/qemu-server/<vmid>.vnc root@<node>` reaches the socket, but VNC
authentication fails, because nothing set a password on it - setting one is what both routes above
do.
