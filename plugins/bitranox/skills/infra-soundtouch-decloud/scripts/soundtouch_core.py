#!/usr/bin/env python3
"""Shared logic for talking to a Bose SoundTouch speaker.

Only the standard library, so these modules import in a bare environment.

The parsing here looks simpler than it is, and each function documents the reading that a plausible
implementation gets wrong: a configuration value sits on the line AFTER its field name, the source
entries are self-closing tags whose status is an attribute rather than a label, and the telnet
writes have an order in which the persisting command must come last.
"""

from __future__ import annotations

import base64
import socket
import urllib.parse
import urllib.request

TELNET_PORT = 17000
API_PORT = 8090
SSH_PORT = 22
PROMPT = b"->"

URL_FIELDS = ("margeServerUrl", "statsServerUrl", "swUpdateUrl", "bmxRegistryUrl")
CLOUD_MARKERS = ("bose.com", "bose.io", "bosecm.com")
RADIO_SOURCES = ("TUNEIN", "LOCAL_INTERNET_RADIO", "RADIO_BROWSER")
PLAYBACK_PATH = "/custom/v1/playback/"

__all__ = [
    "parse_urls", "parse_sources", "cloud_leftovers", "injected_values", "service_urls",
    "build_url_commands", "playback_location", "decode_playback_location", "missing_presets",
    "parse_presets", "port_open", "telnet_run", "http_get", "SpeakerError",
]


class SpeakerError(RuntimeError):
    """The speaker did not answer the way its firmware is documented to."""


def parse_urls(raw: str) -> dict[str, str]:
    """Read the four service URLs out of `getpdo CurrentSystemConfiguration` output.

    getpdo prints `<name> {` and puts the value on a FOLLOWING line as `text: "..."`. A single-line
    pattern therefore matches the field names and captures no values at all, which reads as a
    successful check against a speaker that was never actually read.
    """
    found: dict[str, str] = {}
    lines = raw.splitlines()
    for idx, line in enumerate(lines):
        for name in URL_FIELDS:
            if name in line and "{" in line:
                for follow in lines[idx + 1: idx + 4]:
                    if "text:" in follow:
                        found[name] = follow.split("text:", 1)[1].strip().strip('",')
                        break
    return found


def parse_sources(raw: str) -> dict[str, str]:
    """Map each radio source to its status, defaulting to ABSENT.

    The entries are SELF-CLOSING tags carrying no text, so a `<tag>Label</tag>` pattern finds
    nothing and reports every source missing. Match the attribute. ABSENT stays distinct from a real
    status so a source the speaker never published cannot read as READY.
    """
    seen: dict[str, str] = {}
    for chunk in raw.split("<sourceItem")[1:]:
        for name in RADIO_SOURCES:
            if f'source="{name}"' in chunk:
                seen[name] = chunk.split('status="', 1)[1].split('"', 1)[0] if 'status="' in chunk else "?"
    return {name: seen.get(name, "ABSENT") for name in RADIO_SOURCES}


def service_urls(service: str) -> dict[str, str]:
    """The four URLs a migrated speaker must carry."""
    service = service.rstrip("/")
    return {
        "margeServerUrl": service,
        "statsServerUrl": service,
        "swUpdateUrl": f"{service}/updates/soundtouch",
        "bmxRegistryUrl": f"{service}/bmx/registry/v1/services",
    }


def cloud_leftovers(urls: dict[str, str]) -> dict[str, str]:
    """Fields still pointing at the shut-down Bose cloud.

    All three domains are checked because they are not interchangeable: clearing only bose.com
    leaves bmxRegistryUrl on bose.io, and without that the speaker mounts no radio source at all
    while otherwise looking migrated.
    """
    return {k: v for k, v in urls.items() if any(m in v for m in CLOUD_MARKERS)}


def injected_values(urls: dict[str, str]) -> dict[str, str]:
    """Fields still carrying shell text from the injection method, which must be cleaned up."""
    return {k: v for k, v in urls.items() if ";" in v}


def build_url_commands(service: str, *, inject: str = "") -> list[str]:
    """The telnet sequence that points a speaker at the local service.

    Two rules are encoded here, neither discoverable from the replies. All four fields go through
    `sys configuration`, because `envswitch boseurls set` accepts only the account and update URLs;
    omit them and bmxRegistryUrl is never written, so the speaker syncs presets and plays nothing.
    And `envswitch` comes LAST, because it SAVES the current runtime state: in the other order every
    value is gone after the reboot even though each command answered OK.
    """
    wanted = service_urls(service)
    marge = wanted["margeServerUrl"] + inject
    return [
        f'sys configuration margeServerUrl "{marge}"',
        f'sys configuration bmxRegistryUrl "{wanted["bmxRegistryUrl"]}"',
        f'sys configuration statsServerUrl "{wanted["statsServerUrl"]}"',
        f'sys configuration swUpdateUrl "{wanted["swUpdateUrl"]}"',
        f'envswitch boseurls set "{marge}" "{wanted["swUpdateUrl"]}"',
    ]


def playback_location(service: str, stream_url: str, name: str) -> str:
    """Wrap a stream URL as a preset location the speaker can actually follow.

    A LOCAL_INTERNET_RADIO location is FOLLOWED by the speaker, which expects a station document
    describing the stream. Given the stream URL itself the speaker receives audio where it expected
    a document, holds the source about twenty seconds and discards it without ever buffering. The
    encoding is URL-safe base64 WITH padding.
    """
    encoded = base64.urlsafe_b64encode(stream_url.encode("utf-8")).decode("ascii")
    return (f"{service.rstrip('/')}{PLAYBACK_PATH}{encoded}"
            f"?name={urllib.parse.quote(name)}")


def decode_playback_location(location: str) -> str:
    """Recover the stream URL a stored location wraps, or "" if it is not one of ours."""
    if PLAYBACK_PATH not in location:
        return ""
    encoded = location.split(PLAYBACK_PATH, 1)[1].split("?", 1)[0]
    try:
        return base64.urlsafe_b64decode(encoded).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""


def parse_presets(raw: str) -> list[str]:
    """Every location currently stored on the speaker, in document order."""
    out: list[str] = []
    for chunk in raw.split("<ContentItem")[1:]:
        if 'location="' in chunk:
            out.append(chunk.split('location="', 1)[1].split('"', 1)[0])
    return out


def missing_presets(raw: str, wanted: list[dict[str, str]]) -> list[str]:
    """Which wanted streams the speaker does NOT currently hold.

    Compares by DECODED stream, not by count. Counting says six presets are present when one of them
    now points at a station the owner replaced, so a changed template would never be applied.
    """
    have = {decode_playback_location(loc) for loc in parse_presets(raw)}
    return [p["location"] for p in wanted if p["location"] not in have]


def port_open(ip: str, port: int, timeout: float = 3.0) -> bool:
    """Is the port accepting connections?

    A real socket rather than the `echo > /dev/tcp/host/port` shell redirect, which is a bash
    builtin: run under sh (dash on Debian and Ubuntu, and what docker exec or ssh host 'cmd' often
    give you) it fails for every port, so a live service reports as closed.
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def _read_to_prompt(sock: socket.socket, timeout: float = 10.0) -> str:
    """Read until the `->` prompt, which every command ends with.

    Waiting for OK would hang: `envswitch boseurls set` replies `Setting Bose Server URLs to ...`
    and never says OK, while every command does end at the prompt.
    """
    import time
    sock.settimeout(timeout)
    buf = b""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            chunk = sock.recv(4096)
        except (TimeoutError, socket.timeout):
            break
        if not chunk:
            break
        buf += chunk
        if buf.rstrip().endswith(PROMPT):
            break
    return buf.decode("utf-8", "replace")


def telnet_run(ip: str, commands: list[str], settle: float = 0.2) -> list[dict[str, str]]:
    """Send commands to the diagnostic port in order and collect each reply."""
    import time
    out: list[dict[str, str]] = []
    try:
        with socket.create_connection((ip, TELNET_PORT), timeout=10) as sock:
            _read_to_prompt(sock, timeout=6)
            for cmd in commands:
                sock.sendall(cmd.encode() + b"\r\n")
                out.append({"cmd": cmd, "reply": _read_to_prompt(sock).strip()})
                time.sleep(settle)
    except OSError as exc:
        raise SpeakerError(f"diagnostic port {TELNET_PORT} on {ip}: {exc}") from exc
    return out


def http_get(url: str, timeout: float = 8.0) -> str:
    if not url.startswith(("http://", "https://")):
        raise SpeakerError(f"refusing non-http URL: {url}")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - scheme checked above
            return resp.read().decode("utf-8", "replace")
    except OSError as exc:
        raise SpeakerError(f"{url}: {exc}") from exc
