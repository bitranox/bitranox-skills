---
name: compuse-vnc
description: Use when you must drive a remote machine, VM, or GUI/TUI program over VNC/RFB - sending keystrokes and clicks and reading the screen with OCR - because the target has no network, SSH, agent, or API. Covers Proxmox/hypervisor VM consoles (first boot before networking, or a VM that will never have a network), legacy line-of-business GUIs and dated installers that are only a window, and old TUI apps driven by keypresses. Nothing is installed on the target - it needs only a VNC/RFB server, which a Proxmox VM console already exposes on the host. Driven with the `vnc-remote-control` CLI (PyPI).
---

# Driving a remote machine over VNC (compuse-vnc)

Drive a target's screen over plain VNC/RFB with the `vnc-remote-control` CLI: type text, press
named keys, click, screenshot, and OCR. It is a pure **client** - nothing runs on the target, no
agent, no service, no open port, nothing in its process list. The control happens entirely through
a VNC/RFB server the target already exposes.

## When to use

- **A target with no network.** A Proxmox/hypervisor VM that is not on the network yet (or never
  will be) is still driveable through its VNC console - the same screen as the web UI. Ideal for
  first-boot setup where you configure networking before the guest can reach anything.
- **No footprint wanted.** Operate a machine with nothing installed or visible on it.
- **VNC is the only door.** Remote admin where VNC is the one reachable interface.
- **Legacy GUI software** with no API/CLI/accessibility tree - only a window. Read it with OCR,
  click by label. Legacy UIs rarely move, so coordinates stay stable.
- **Old TUI programs** that you operate purely by keypresses (`type` + `key`); the target needs only
  a VNC server, which Proxmox provides out of the box.

## Step 0: install the tool, then use it (on YOUR control box only, never the target)

This skill installs `vnc-remote-control` and then drives it. First make sure the CLI and tesseract
are present on the machine you drive FROM (never on the target):

```bash
# the CLI - persistent on PATH via uv; skip if already installed
command -v vnc-remote-control >/dev/null || uv tool install vnc-remote-control
# tesseract is a REQUIRED system dependency (OCR is how you find what to click)
command -v tesseract >/dev/null || sudo apt-get install -y tesseract-ocr   # macOS: brew install tesseract | Windows: choco install tesseract
```

For a one-off without a persistent install, `uvx vnc-remote-control ...` runs it on demand (uv
fetches it each run); tesseract is still required. Then drive the target with the commands below.

## Commands

Every command needs `--port`; `--host` defaults to `127.0.0.1`.

| Command                                       | Does                                                                                            |
|-----------------------------------------------|-------------------------------------------------------------------------------------------------|
| `type "text" [--enter] [--us-shift]`          | Type a literal string into the focused field (`--enter` adds Return; `--us-shift`: see below)   |
| `key <name>`                                  | Press one named key: `enter`, `tab`, `esc`, arrows, `f1`-`f12`, ...                             |
| `click X Y`                                   | Left-click at an absolute framebuffer pixel                                                     |
| `screenshot out.png [--mark X,Y] [--grid 50]` | Write the native-resolution PNG; prints `resolution: WxH`; optional crosshair / coordinate grid |
| `ocr [--grep PATTERN]`                        | List on-screen words with their click centers and confidence                                    |
| `click-text "PATTERN"`                        | Click the first on-screen word matching the pattern                                             |

```bash
vnc-remote-control --port 5901 screenshot /tmp/g.png --grid 50
vnc-remote-control --host 10.0.0.5 --port 5901 click-text "Next"
vnc-remote-control --port 5901 type "chkdsk c: /f" --enter
```

## The driving loop (how to click the right pixel every time)

RFB pointer coordinates are **absolute framebuffer pixels - the same pixels as a native-resolution
screenshot.** This tool never scales, so a coordinate read off the screenshot is the exact click
coordinate. (Past "wrong pixel" failures came from reading coordinates off a scaled image.)

1. **Capture and look.** `screenshot out.png` - view it at NATIVE size (do not let the viewer downscale).
2. **Read coordinates directly** off `out.png` - there is no scale factor to undo.
3. **Verify before committing:** `screenshot out.png --mark X,Y` and check the crosshair lands on target (`--grid 50` adds a ruler).
4. **Prefer clicking by label** over guessing pixels: `ocr --grep "Sign in"` then `click <cx> <cy>`, or one-shot `click-text "Sign in"`. `click-text` only sees text OCR can read - low-contrast or placeholder hints (a faint greyed-out search box), icons, and untitled controls are missed and it fails; fall back to reading the pixel off the screenshot and `click X Y`.
5. **Focus, then type.** A freshly opened window/field often does NOT have keyboard focus. Click into the text field first, THEN `type`. Skipping the click is the #1 reason typed text seems to vanish.

## Gotchas

- **Focus before typing** (see step 5). If text vanishes: screenshot, click the field, type again.
- **Keyboard layout is server-side, not yours.** You pass the text you want; the client puts each
  character's Unicode code point on the wire as its keysym (like any VNC client). Your own laptop
  layout is irrelevant. A layout-aware server (openvmm; on Proxmox the ovm shim derives it from the
  VM's `keyboard:` key) maps keysyms to the guest layout. If wrong characters land on such a server,
  its layout is misconfigured - fix it there, never compensate per keystroke on the client.
- **QEMU's own VNC server needs `type --us-shift`.** The console of a plain Proxmox VM is QEMU's
  VNC, which turns a keysym into the scancode of its key in the VM's keymap (`keyboard:`, default
  en-us) but presses no Shift for it: `type 'x@A2Z|'` lands as `x2A2Z\` (letters keep their case,
  shifted symbols lose Shift). `--us-shift` holds Shift_L around every character a US keyboard
  types with Shift, and the same text then lands intact. Leave it off for a layout-aware server
  (openvmm), where an extra Shift would change the character. The guest's own keyboard layout must
  match the VM's keymap: a German guest layout under the default en-us keymap turns `-` into `ss`,
  so pick U.S. English in an installer driven this way. All of this was measured with the default
  en-us keymap; whether `--us-shift` fits a VM with another `keyboard:` value is untested.
- **Sluggish guests drop fast input.** Slow it down: `--delay-scale 2` multiplies every delay, or set
  individual gaps via `--set vnc.key_up_gap=0.2` (keys: `key_down_hold`, `key_up_gap`, `click_move_gap`,
  `click_hold`, `click_release_gap`).
- **Nothing happened, or an error? READ the screen before re-sending input - ROOT-CAUSE it.** When a
  click/keystroke seems to have no effect or the flow stops, `screenshot` + `ocr` FIRST and act on what
  the screen ACTUALLY says (an error dialog, a validation message, a progress indicator, a greyed-out or
  relabeled button). Never blind-retry: if the first click DID land, the same coordinates may now hit a
  DIFFERENT control (re-firing an installer, dismissing an unread error), and on a laggy guest an
  "unchanged" screenshot is weak evidence. Only when two screenshots a few seconds apart show a genuinely
  identical, idle screen is "dropped input" the diagnosis - then retry ONCE with increased delays and
  re-read the screen.
- **A VNC console is a flaky external resource** - it can freeze, drop, or lag mid-session. Verify the
  screen state before acting on it, retry under a timeout, and never assume a keystroke landed. For the
  self-healing patterns, see `bitranox:coding-resilience`.

## Authentication

- **None security** (an openvmm console on localhost) needs nothing. A plain Proxmox QEMU VM's console
  asks for a VNC password instead: see "Proxmox / no-network VMs".
- **VNC password:** pass it via the `VNC_REMOTE_CONTROL_PASSWORD` env var (which `--password` reads by
  default), NOT on the command line - a password in argv is visible in `ps`. TLS/VeNCrypt and Apple
  Remote Desktop auth are not supported. (demand gated)

```bash
VNC_REMOTE_CONTROL_PASSWORD=secret vnc-remote-control --port 5901 key enter
```

## Proxmox / no-network VMs

The VM's console is a VNC/RFB server on the host. Reach it directly, or SSH-tunnel to the console
port with `ssh -N -L <local-port>:127.0.0.1:<console-port> <user>@<host>`, then point the client at
`127.0.0.1:<local-port>` (`-N` because no remote command is wanted, and binding the forward to the
host's loopback keeps the console off its network). `openvmm` is the ideal layout-aware target so arbitrary
characters and non-US layouts type reliably.

A plain Proxmox QEMU VM is different in three ways:

- **Its console is a unix socket**, `/var/run/qemu-server/<vmid>.vnc`, not a TCP port. Forward a
  local port to it: `ssh -N -L 127.0.0.1:<local-port>:/var/run/qemu-server/<vmid>.vnc root@<node>`.
- **It requires VNC password auth.** Keep the password in a file on the machine you drive from,
  outside any repository (mode 600, at most 8 characters: VNC authentication reads no more), set
  it in QEMU's monitor and keep it from expiring. `printf` is a shell builtin, so the password
  never shows in a process list, and `$(cat ...)` drops a trailing newline, so the two monitor
  commands stay on their own lines:

  ```bash
  printf 'set_password vnc %s\nexpire_password vnc never\n' "$(cat pw.txt)" \
    | ssh root@<node> 'qm monitor <vmid>'
  VNC_REMOTE_CONTROL_PASSWORD="$(cat pw.txt)" vnc-remote-control --port <local-port> \
    type --us-shift 'root@pam' --enter
  ```

  The client takes the same password through its environment variable. Without
  `expire_password` the login fails with "VNC authentication failed". Delete the file when done.
  Opening the VM's console in the Proxmox web UI sets a new password and replaces yours, so set it
  again when authentication suddenly starts failing mid-session. It lives only in the running QEMU
  process and is gone at the next VM start.
- **It is not layout-aware:** with the default en-us keymap, type with `--us-shift` (see Gotchas).
