#!/usr/bin/env python3
"""Back up, check and restore a speaker's presets.

    uv run scripts/soundtouch_presets.py backup  --ip 192.0.2.31 --outdir ./backup
    uv run scripts/soundtouch_presets.py check   --ip 192.0.2.31 --template speaker.json --service http://192.0.2.10:8000
    uv run scripts/soundtouch_presets.py restore --ip 192.0.2.31 --template speaker.json --service http://192.0.2.10:8000 --confirm

Nothing is written without --confirm.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.request

try:
    from soundtouch_core import (API_PORT, SpeakerError, http_get, missing_presets, parse_sources,
                                 playback_location)
except ModuleNotFoundError:  # pragma: no cover - direct execution from another directory
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from soundtouch_core import (API_PORT, SpeakerError, http_get, missing_presets, parse_sources,
                                 playback_location)

REQUIRED_FIELDS = ("buttonNumber", "name", "location")

__all__ = ["load_template", "radio_ready", "preset_xml", "main"]


def load_template(path: str) -> dict[str, object]:
    """Read and validate a preset template.

    Validated rather than trusted because a template whose location already carries the playback
    adapter would be double-wrapped, and one missing a button number silently writes nothing.
    """
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    presets = data.get("presets")
    if not isinstance(presets, list) or not presets:
        raise ValueError("template has no presets")
    seen: set[int] = set()
    for entry in presets:
        for field in REQUIRED_FIELDS:
            if field not in entry:
                raise ValueError(f"preset is missing '{field}': {entry}")
        button = entry["buttonNumber"]
        if not isinstance(button, int) or not 1 <= button <= 6:
            raise ValueError(f"buttonNumber must be 1..6, got {button!r}")
        if button in seen:
            raise ValueError(f"buttonNumber {button} appears twice")
        seen.add(button)
        if "/custom/v1/playback/" in entry["location"]:
            raise ValueError("location must be the PLAIN stream URL; the wrapping is added on write")
    return data


def radio_ready(ip: str) -> bool:
    """Has the speaker mounted the radio source yet?

    Writing presets before it has is silently undone by the same boot-time wipe they are meant to
    survive, so a restore run must do nothing at all in that window.
    """
    try:
        return parse_sources(http_get(f"http://{ip}:{API_PORT}/sources"))["LOCAL_INTERNET_RADIO"] == "READY"
    except (SpeakerError, KeyError):
        return False


def preset_xml(service: str, entry: dict[str, object]) -> str:
    """The body for one preset slot, with the location wrapped for the playback adapter."""
    location = playback_location(service, str(entry["location"]), str(entry["name"]))
    name = str(entry["name"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (f'<ContentItem source="{entry.get("source", "LOCAL_INTERNET_RADIO")}" '
            f'type="{entry.get("contentItemType", "stationurl")}" '
            f'location="{location.replace("&", "&amp;")}" sourceAccount="" isPresetable="true">'
            f"<itemName>{name}</itemName></ContentItem>")


def _store(ip: str, service: str, entry: dict[str, object]) -> None:
    url = f"http://{ip}:{API_PORT}/storePreset"
    body = (f'<preset id="{entry["buttonNumber"]}">{preset_xml(service, entry)}</preset>').encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=15):  # noqa: S310 - fixed http URL built above
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("backup", "check", "restore"):
        p = sub.add_parser(name)
        p.add_argument("--ip", required=True)
        if name == "backup":
            p.add_argument("--outdir", default=".")
        else:
            p.add_argument("--template", required=True)
            p.add_argument("--service", required=True)
        if name == "restore":
            p.add_argument("--confirm", action="store_true",
                           help="required: without it nothing is written")
    args = parser.parse_args(argv)

    def emit(ok: bool, data: dict[str, object]) -> int:
        print(json.dumps({"ok": ok, "command": args.cmd, "data": data}, indent=2))
        return 0 if ok else 1

    if args.cmd == "backup":
        out = pathlib.Path(args.outdir)
        out.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        saved: dict[str, object] = {}
        for endpoint in ("presets", "info", "recents", "sources"):
            try:
                body = http_get(f"http://{args.ip}:{API_PORT}/{endpoint}")
            except SpeakerError as exc:
                saved[endpoint] = f"FAILED: {exc}"
                continue
            path = out / f"{args.ip}-{stamp}-{endpoint}.xml"
            path.write_text(body, encoding="utf-8")
            saved[endpoint] = str(path)
        ok = isinstance(saved.get("presets"), str) and not str(saved["presets"]).startswith("FAILED")
        return emit(ok, {"saved": saved})

    try:
        template = load_template(args.template)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return emit(False, {"error": str(exc)})
    try:
        current = http_get(f"http://{args.ip}:{API_PORT}/presets")
    except SpeakerError as exc:
        return emit(False, {"error": str(exc)})

    presets = list(template["presets"])  # type: ignore[arg-type]
    missing = missing_presets(current, presets)  # type: ignore[arg-type]

    if args.cmd == "check":
        return emit(not missing, {"wanted": len(presets), "missing": len(missing),
                                  "missing_streams": missing})

    if not missing:
        return emit(True, {"wrote": 0, "note": "already correct"})
    if not radio_ready(args.ip):
        return emit(False, {"error": "the radio source is not mounted yet, so a write would be "
                                     "silently undone. Wait about 80 seconds after a restart."})
    if not args.confirm:
        return emit(False, {"would_write": len(missing), "missing_streams": missing,
                            "note": "re-run with --confirm to write these"})
    wrote = []
    for entry in sorted(presets, key=lambda p: p["buttonNumber"]):  # type: ignore[index]
        if entry["location"] in missing:
            try:
                _store(args.ip, args.service, entry)  # type: ignore[arg-type]
                wrote.append(entry["name"])
            except OSError as exc:
                return emit(False, {"wrote": wrote, "error": f"{entry['name']}: {exc}"})
            time.sleep(0.5)
    after = missing_presets(http_get(f"http://{args.ip}:{API_PORT}/presets"), presets)  # type: ignore[arg-type]
    return emit(not after, {"wrote": wrote, "still_missing": after})


if __name__ == "__main__":
    sys.exit(main())
