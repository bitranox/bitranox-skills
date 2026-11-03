"""Stand-in for store_manifest.py with the same CLI surface the guard drives.

backup: a --from containing "nostore" exits 2 with the real script's no-store message, one
containing "refuse" exits 2 with another refusal, one containing "slow" sleeps past any short
timeout; otherwise it writes manifest.json and reports 3 entries. verify: a file named CHANGED
beside the manifest makes it exit 1 with a diff, one named UNREADABLE makes it exit 2.
"""
import argparse
import json
import sys
import time
from pathlib import Path


def _envelope(ok, command, data):
    print(json.dumps({"ok": ok, "command": command, "data": data, "skipped": []}))


def _backup(start, out):
    if "nostore" in start:
        _envelope(False, "backup", {"error": "no .claude-memory/ store at the memory anchor of " + start})
        return 2
    if "refuse" in start:
        _envelope(False, "backup", {"error": "--out exists, is not empty and holds no manifest.json"})
        return 2
    if "slow" in start:
        time.sleep(30)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text("{}", encoding="utf-8")
    _envelope(True, "backup", {"entries": 3})
    return 0


def _verify(out):
    if (out / "UNREADABLE").exists():
        _envelope(False, "verify", {"error": "cannot read manifest.json"})
        return 2
    if (out / "CHANGED").exists():
        _envelope(True, "verify", {"identical": False, "changed": [{"slug": "x", "what": "hook"}],
                                   "added": [], "removed": [], "moved": []})
        return 1
    _envelope(True, "verify", {"identical": True, "changed": [], "added": [], "removed": [], "moved": []})
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    bk = sub.add_parser("backup")
    bk.add_argument("--from", dest="start", required=True)
    bk.add_argument("--scope", default="tree")
    bk.add_argument("--out", required=True)
    bk.add_argument("--json", action="store_true")
    vf = sub.add_parser("verify")
    vf.add_argument("--out", required=True)
    vf.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "backup":
        return _backup(a.start, Path(a.out))
    return _verify(Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
