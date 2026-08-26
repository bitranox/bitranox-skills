#!/usr/bin/env python3
"""Take one speaker onto the local service, or report where it stands.

    uv run scripts/soundtouch_onboard.py --ip 192.0.2.31 state
    uv run scripts/soundtouch_onboard.py --ip 192.0.2.31 --service http://192.0.2.10:8000 migrate --confirm
    uv run scripts/soundtouch_onboard.py --ip 192.0.2.31 reboot --confirm
    uv run scripts/soundtouch_onboard.py --ip 192.0.2.31 play --preset 1 \
                                         --expect "Example Radio" --confirm

Nothing that changes the speaker runs without --confirm.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

try:
    from soundtouch_core import (API_PORT, URL_FIELDS, SpeakerError, build_url_commands,
                                 cloud_leftovers, http_get, injected_values, parse_sources,
                                 parse_urls, port_open, telnet_run)
except ModuleNotFoundError:  # pragma: no cover - direct execution from another directory
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from soundtouch_core import (API_PORT, URL_FIELDS, SpeakerError, build_url_commands,
                                 cloud_leftovers, http_get, injected_values, parse_sources,
                                 parse_urls, port_open, telnet_run)

__all__ = ["build_parser", "migration_verdict", "wait_down", "wait_up", "main"]


def migration_verdict(urls: dict[str, str]) -> dict[str, object]:
    """Is this speaker fully migrated, and if not, what is wrong with it?"""
    return {
        "urls": urls,
        "cloud_leftovers": cloud_leftovers(urls),
        "still_injected": injected_values(urls),
        "missing": [f for f in URL_FIELDS if f not in urls],
        "ok": bool(urls) and not cloud_leftovers(urls) and not injected_values(urls)
             and not [f for f in URL_FIELDS if f not in urls],
    }


def wait_down(ip: str, limit: float = 60.0) -> float | None:
    """Prove the speaker actually went down.

    A wait that only checks for "back up" reports success instantly when the reboot never happened,
    which is the case worth catching.
    """
    start = time.monotonic()
    while time.monotonic() - start < limit:
        if not port_open(ip, API_PORT, timeout=2):
            return round(time.monotonic() - start, 1)
        time.sleep(2)
    return None


def wait_up(ip: str, limit: float = 180.0) -> float | None:
    start = time.monotonic()
    while time.monotonic() - start < limit:
        if port_open(ip, API_PORT, timeout=2):
            return round(time.monotonic() - start, 1)
        time.sleep(3)
    return None


def _key(ip: str, name: str) -> None:
    for state in ("press", "release"):
        body = f'<key state="{state}" sender="Gabbo">{name}</key>'.encode()
        req = urllib.request.Request(f"http://{ip}:{API_PORT}/key", data=body, method="POST")
        with urllib.request.urlopen(req, timeout=15):  # noqa: S310 - fixed http URL built above
            pass
        time.sleep(0.4)


def build_parser() -> argparse.ArgumentParser:
    """The CLI surface, separate from main so the documented usage lines can be parsed in a test."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ip", required=True)
    parser.add_argument("--service", help="AfterTouch base URL (needed for migrate)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("state")
    p_mig = sub.add_parser("migrate", help="rewrite the four service URLs")
    p_mig.add_argument("--confirm", action="store_true")
    p_reb = sub.add_parser("reboot", help="restart and wait for the radio sources")
    p_reb.add_argument("--confirm", action="store_true")
    p_reb.add_argument("--sources-wait", type=float, default=240.0)
    p_play = sub.add_parser("play", help="play a preset and prove it really played")
    p_play.add_argument("--preset", type=int, default=1)
    p_play.add_argument("--expect", required=True,
                        help="station name that must appear. Required: without it an "
                             "already-playing speaker passes trivially and proves nothing")
    p_play.add_argument("--wait", type=float, default=60.0)
    p_play.add_argument("--confirm", action="store_true",
                        help="required: this starts audio on the speaker, at its current volume")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    def emit(ok: bool, data: dict[str, object]) -> int:
        print(json.dumps({"ok": ok, "command": args.cmd, "data": data}, indent=2))
        return 0 if ok else 1

    try:
        if args.cmd == "state":
            urls = parse_urls(
                str(telnet_run(args.ip, ["getpdo CurrentSystemConfiguration"])[0]["reply"]))
            data = migration_verdict(urls)
            data["sources"] = parse_sources(http_get(f"http://{args.ip}:{API_PORT}/sources"))
            return emit(bool(data["ok"]), data)

        if args.cmd == "migrate":
            if not args.service:
                return emit(False, {"error": "--service is required for migrate"})
            if not args.confirm:
                return emit(False, {"would_run": build_url_commands(args.service),
                                    "note": "re-run with --confirm. The speaker must be restarted "
                                            "afterwards for the radio sources to mount."})
            replies = telnet_run(args.ip, build_url_commands(args.service))
            verdict = migration_verdict(parse_urls(
                str(telnet_run(args.ip, ["getpdo CurrentSystemConfiguration"])[0]["reply"])))
            verdict["telnet"] = replies
            verdict["truncated_replies"] = [r["cmd"] for r in replies if not r["complete"]]
            verdict["next"] = ("This is the LIVE configuration. Only a reboot shows what was "
                               "persisted, and the radio sources do not mount until then: run "
                               "`reboot --confirm` next, then check `state` again.")
            return emit(bool(verdict["ok"]) and not verdict["truncated_replies"], verdict)

        if args.cmd == "reboot":
            if not args.confirm:
                return emit(False, {"note": "re-run with --confirm; the speaker will restart and "
                                            "be unavailable for about 80 seconds"})
            telnet_run(args.ip, ["sys reboot"])
            down = wait_down(args.ip)
            if down is None:
                return emit(False, {"error": "the speaker never went down, so the reboot did not "
                                             "happen"})
            up = wait_up(args.ip)
            deadline = time.monotonic() + args.sources_wait
            ready: dict[str, str] = {}
            while time.monotonic() < deadline:
                try:
                    ready = parse_sources(http_get(f"http://{args.ip}:{API_PORT}/sources"))
                except SpeakerError:
                    time.sleep(5)
                    continue
                if all(v == "READY" for v in ready.values()):
                    break
                time.sleep(5)
            return emit(bool(ready) and all(v == "READY" for v in ready.values()),
                        {"down_after_s": down, "up_after_s": up, "sources": ready})

        if not args.confirm:
            return emit(False, {"note": f"re-run with --confirm; this presses PRESET_{args.preset}"
                                        " and starts audio at the speaker's current volume. "
                                        "Turn the volume down first."})
        _key(args.ip, f"PRESET_{args.preset}")
        states: list[str] = []
        item = "-"
        deadline = time.monotonic() + args.wait
        while time.monotonic() < deadline:
            try:
                raw = http_get(f"http://{args.ip}:{API_PORT}/now_playing")
            except SpeakerError:
                time.sleep(2)
                continue
            status = raw.split("<playStatus>", 1)[1].split("</", 1)[0] if "<playStatus>" in raw else "-"
            item = raw.split("<itemName>", 1)[1].split("</", 1)[0] if "<itemName>" in raw else "-"
            step = f"{item}/{status}"
            if not states or states[-1] != step:
                states.append(step)
            if status == "PLAY_STATE" and args.expect.lower() in item.lower():
                break
            time.sleep(2)
        ok = (bool(states) and states[-1].endswith("PLAY_STATE")
              and args.expect.lower() in item.lower())
        return emit(ok, {"preset": args.preset, "expect": args.expect, "itemName": item,
                         "states": states})
    except SpeakerError as exc:
        return emit(False, {"error": str(exc)})


if __name__ == "__main__":
    sys.exit(main())
