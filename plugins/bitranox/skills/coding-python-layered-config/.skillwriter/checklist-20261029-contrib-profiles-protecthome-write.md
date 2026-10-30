# Review: profile consequence, ProtectHome, writing a value into a layer (three contrib entries)

## Profiles: a profile replaces the base paths
- [x] RED: the pre-edit Profiles section said only that the segment is "inserted"; nothing said
      the base files stop being read.
- [x] Source: `adapters/path_resolvers/_linux.py:44-47,59-63,77-78,87-88` (and the macOS and
      Windows twins) build every app, host, user and per-user `.env` path WITH the profile segment;
      no base path is yielded beside it.
- [x] Executed (`lib_layered_config read-json` in a scratch XDG root): base `config.toml` with
      `[node] host`, `profile/site-b/config.toml` with only `[ssh] known_hosts_file`; no profile
      shows `node.host`, `--profile site-b` shows only `ssh.known_hosts_file`. In Python with
      `profile="site-b"`: `defaults` (default_file), `dotenv` (upward `.env`) and `env` still
      supply their keys (`origin()` layers printed).
- [x] GREEN: `grep -n "REPLACES the base paths" SKILL.md` quotes the new text.

## ProtectHome=yes makes every start fail
- [x] RED: `grep -c ProtectHome SKILL.md` was 0 (the coerce_numbers_to_str half of that entry was
      already present).
- [x] Executed: a user-layer dir with mode 000 makes `read_config` raise `LayerLoadError:
      .../<slug>/.env cannot be read: Permission denied`; a missing dir loads (exit 0).
- [x] `man systemd.exec`: `ProtectHome=yes` makes /home, /root, /run/user inaccessible; `tmpfs`
      mounts empty read-only filesystems there.
- [x] Exit 78 is attributed to the app's EX_CONFIG mapping, not the library (the library's own
      CLI exits 1 on the same error).
- [x] Declined, not run: `systemd-run` with the unit's properties (needs root on a systemd host); the text
      gives it as the check to run, not as a measured result here.

## Writing one value back into a layer
- [x] RED: no section on writing; `grep -c tomlkit SKILL.md` was 0.
- [x] Source: `adapters/file_loaders/_dot_d.py:38-115` yields the base file, then the `.d` files
      with a `.toml/.yaml/.yml/.json` suffix in `sorted()` order.
- [x] Executed: base `config.toml` dpi 203, `config.d/50-printer.toml` dpi 300; writing 600 into
      the base file with tomlkit still reads 300 and `origin()` names `50-printer.toml`.
      `deploy_config_paths(src, targets=["user"])` returns the user `config.toml`, plus copies
      inside `config.d/` when the source has a `.d` (hence "the one path outside a `.d`").
- [x] GREEN: `grep -n "Writing one value back into a layer" SKILL.md` quotes the heading.

## All three
- [x] Twin regenerated; `diff -r -x .skillwriter -x __pycache__` shows only the `name:` line.
- [x] ASCII only; added lines pass the history finder; description untouched.
- [x] Declined, not run: subagent quote-back probes (this pass dispatched no subagents).
