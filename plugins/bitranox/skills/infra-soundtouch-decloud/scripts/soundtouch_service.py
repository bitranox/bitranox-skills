#!/usr/bin/env python3
"""Check Docker, render the service compose file, and check the service is alive.

    uv run scripts/soundtouch_service.py check-docker
    uv run scripts/soundtouch_service.py render --host 192.0.2.10 --out docker-compose.yml
    uv run scripts/soundtouch_service.py health --service http://192.0.2.10:8000
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import shutil
import subprocess
import sys

try:
    from soundtouch_core import SpeakerError, http_get
except ModuleNotFoundError:  # pragma: no cover - direct execution from another directory
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from soundtouch_core import SpeakerError, http_get

LOOPBACK_HINT = "must be an address the SPEAKERS can reach, never localhost or 127.0.0.1"

INSTALL_HINTS = {
    "windows": "Install Docker Desktop from docker.com, start it, then run the check again.",
    "macos": "Install Docker Desktop from docker.com, start it, then run the check again.",
    "debian": "Run: curl -fsSL https://get.docker.com | sh    then: sudo usermod -aG docker $USER "
              "and log out and back in.",
    "fedora": "Run: sudo dnf install docker docker-compose-plugin    then: "
              "sudo systemctl enable --now docker",
    "nas": "Install the Container Manager (Synology) or Container Station (QNAP) package from the "
           "vendor's package centre, then run the check again.",
}

__all__ = ["install_hint", "render_compose", "validate_host", "docker_report", "main"]


def install_hint(system: str) -> str:
    """The instruction for one platform, or a prompt to name the platform."""
    return INSTALL_HINTS.get(system.strip().lower(),
                             "Ask which system this machine runs: "
                             + ", ".join(sorted(INSTALL_HINTS)))


def validate_host(host: str) -> tuple[bool, str]:
    """Reject an address the speakers could never call back to.

    A loopback address here is the quiet killer: the service starts, the owner can browse it, and
    every speaker is told to call itself.
    """
    if not host or host != host.strip():
        return False, "empty or padded address"
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        if host in ("localhost", "localhost.localdomain"):
            return False, f"'{host}' {LOOPBACK_HINT}"
        return True, "hostname (make sure it resolves to the LAN address on every speaker)"
    if addr.is_loopback:
        return False, f"'{host}' {LOOPBACK_HINT}"
    if addr.is_unspecified or addr.is_multicast:
        return False, f"'{host}' is not a usable host address"
    return True, "ok"


def render_compose(host: str, version: str = "latest", data_dir: str = "/opt/soundtouch/data") -> str:
    """The compose file, with host networking and no ports block.

    Host networking is mandatory: discovery is SSDP and mDNS multicast, which Docker's bridge does
    not forward into a container, so on a bridge the service answers HTTP and finds no speakers at
    all. A ports block is invalid alongside it and Docker only warns, so a leftover one reads as
    though it applies and does nothing.
    """
    ok, why = validate_host(host)
    if not ok:
        raise ValueError(why)
    return f"""services:
  soundtouch-service:
    image: ghcr.io/gesellix/bose-soundtouch:{version}
    container_name: soundtouch-service
    restart: unless-stopped
    network_mode: host
    environment:
      PORT: 8000
      HTTPS_PORT: 8443
      DATA_DIR: /app/data
      SERVER_URL: http://{host}:8000
      HTTPS_SERVER_URL: https://{host}:8443
      RECORD_INTERACTIONS: "true"
      DISCOVERY_INTERVAL: 5m
    volumes:
      - {data_dir}:/app/data
"""


def docker_report() -> dict[str, object]:
    """What is installed, and whether compose is usable."""
    report: dict[str, object] = {"docker": shutil.which("docker") is not None}
    if not report["docker"]:
        report["compose"] = False
        return report
    try:
        proc = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=30, check=False)
        report["compose"] = proc.returncode == 0
        report["compose_version"] = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
    except (OSError, subprocess.SubprocessError) as exc:
        report["compose"] = False
        report["compose_error"] = str(exc)
    return report


def _emit(command: str, ok: bool, data: dict[str, object]) -> int:
    print(json.dumps({"ok": ok, "command": command, "data": data}, indent=2))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-docker", help="is Docker and compose available")
    p_render = sub.add_parser("render", help="write the compose file")
    p_render.add_argument("--host", required=True, help="address the speakers will call back to")
    p_render.add_argument("--version", default="latest")
    p_render.add_argument("--out", default="-")
    p_health = sub.add_parser("health", help="is the service answering")
    p_health.add_argument("--service", required=True)
    p_hint = sub.add_parser("install-hint", help="how to install Docker on one platform")
    p_hint.add_argument("system")
    args = parser.parse_args(argv)

    if args.cmd == "check-docker":
        rep = docker_report()
        ready = bool(rep.get("docker")) and bool(rep.get("compose"))
        if not ready:
            rep["next"] = "Docker is not usable here. Ask the owner which system this is, then: " \
                          + install_hint("")
        return _emit("check-docker", ready, rep)

    if args.cmd == "install-hint":
        return _emit("install-hint", True, {"system": args.system, "hint": install_hint(args.system)})

    if args.cmd == "render":
        try:
            text = render_compose(args.host, args.version)
        except ValueError as exc:
            return _emit("render", False, {"error": str(exc)})
        if args.out == "-":
            print(text)
            return 0
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return _emit("render", True, {"path": args.out, "host": args.host})

    try:
        body = http_get(f"{args.service.rstrip('/')}/api/setup/devices")
    except SpeakerError as exc:
        return _emit("health", False, {"error": str(exc)})
    try:
        devices = json.loads(body)
    except json.JSONDecodeError:
        return _emit("health", False, {"error": "the service answered but not with JSON"})
    return _emit("health", True, {"devices": len(devices),
                                  "names": [d.get("name") for d in devices if isinstance(d, dict)]})


if __name__ == "__main__":
    sys.exit(main())
