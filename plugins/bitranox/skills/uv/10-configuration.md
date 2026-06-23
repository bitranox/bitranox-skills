# Configuration, Indexes, Cache and Storage

## Configuration Files

uv supports persistent configuration files at both the project- and user-level.

Specifically, uv will search for a `pyproject.toml` or `uv.toml` file in the current directory, or in the nearest parent directory.

**Note:** For `tool` commands, which operate at the user level, local configuration files will be ignored. Instead, uv will exclusively read from user-level configuration (e.g., `~/.config/uv/uv.toml`) and system-level configuration (e.g., `/etc/uv/uv.toml`).

In workspaces, uv will begin its search at the workspace root, ignoring any configuration defined in workspace members. Since the workspace is locked as a single unit, configuration is shared across all members. For details on workspace structure, see `12-workspaces.md`.

If a `pyproject.toml` file is found, uv will read configuration from the `[tool.uv]` table. For example, to set a persistent index URL, add the following to a `pyproject.toml`:

```toml
[[tool.uv.index]]
url = "https://test.pypi.org/simple"
default = true
```

(If there is no such table, the `pyproject.toml` file will be ignored, and uv will continue searching in the directory hierarchy.)

uv will also search for `uv.toml` files, which follow an identical structure, but omit the `[tool.uv]` prefix. For example:

```toml
[[index]]
url = "https://test.pypi.org/simple"
default = true
```

**Note:** `uv.toml` files take precedence over `pyproject.toml` files, so if both `uv.toml` and `pyproject.toml` files are present in a directory, configuration will be read from `uv.toml`, and `[tool.uv]` section in the accompanying `pyproject.toml` will be ignored.

uv will also discover `uv.toml` configuration files in the user- and system-level configuration directories, e.g., user-level configuration in `~/.config/uv/uv.toml`, and system-level configuration at `/etc/uv/uv.toml` on macOS and Linux.

**Important:** User- and system-level configuration files cannot use the `pyproject.toml` format.

### Configuration precedence

If project-, user-, and system-level configuration files are found, the settings will be merged, with project-level configuration taking precedence over the user-level configuration, and user-level configuration taking precedence over the system-level configuration. (If multiple system-level configuration files are found, e.g., at both `/etc/uv/uv.toml` and `$XDG_CONFIG_DIRS/uv/uv.toml`, only the first-discovered file will be used, with XDG taking priority.)

For example, if a string, number, or boolean is present in both the project- and user-level configuration tables, the project-level value will be used, and the user-level value will be ignored. If an array is present in both tables, the arrays will be concatenated, with the project-level settings appearing earlier in the merged array.

Settings provided via environment variables take precedence over persistent configuration, and settings provided via the command line take precedence over both.

uv accepts a `--no-config` command-line argument which, when provided, disables the discovery of any persistent configuration.

uv also accepts a `--config-file` command-line argument, which accepts a path to a `uv.toml` to use as the configuration file. When provided, this file will be used in place of _any_ discovered configuration files (e.g., user-level configuration will be ignored).

### `.env` files

`uv run` can load environment variables from dotenv files (e.g., `.env`, `.env.local`, `.env.development`), powered by the `dotenvy` crate.

To load a `.env` file from a dedicated location, set the `UV_ENV_FILE` environment variable, or pass the `--env-file` flag to `uv run`.

For example, to load environment variables from a `.env` file in the current working directory:

```console
$ echo "MY_VAR='Hello, world!'" > .env
$ uv run --env-file .env -- python -c 'import os; print(os.getenv("MY_VAR"))'
Hello, world!
```

The `--env-file` flag can be provided multiple times, with subsequent files overriding values defined in previous files. To provide multiple files via the `UV_ENV_FILE` environment variable, separate the paths with a space (e.g., `UV_ENV_FILE="/path/to/file1 /path/to/file2"`).

To disable dotenv loading (e.g., to override `UV_ENV_FILE` or the `--env-file` command-line argument), set the `UV_NO_ENV_FILE` environment variable to `1`, or pass the `--no-env-file` flag to `uv run`.

If the same variable is defined in the environment and in a `.env` file, the value from the environment will take precedence.

### Configuring the pip interface

A dedicated `[tool.uv.pip]` section is provided for configuring _just_ the `uv pip` command line interface. Settings in this section will not apply to `uv` commands outside the `uv pip` namespace. However, many of the settings in this section have corollaries in the top-level namespace which _do_ apply to the `uv pip` interface unless they are overridden by a value in the `uv.pip` section.

The `uv.pip` settings are designed to adhere closely to pip's interface and are declared separately to retain compatibility while allowing the global settings to use alternate designs (e.g., `--no-build`).

As an example, setting the `index-url` under `[tool.uv.pip]`, as in the following `pyproject.toml`, would only affect the `uv pip` subcommands (e.g., `uv pip install`, but not `uv sync`, `uv lock`, or `uv run`):

```toml
[tool.uv.pip]
index-url = "https://test.pypi.org/simple"
```

## Package Indexes

By default, uv uses the Python Package Index (PyPI) for dependency resolution and package installation. However, uv can be configured to use other package indexes, including private indexes, via the `[[tool.uv.index]]` configuration option (and `--index`, the analogous command-line option).

### Defining an index

To include an additional index when resolving dependencies, add a `[[tool.uv.index]]` entry to your `pyproject.toml`:

```toml
[[tool.uv.index]]
# Optional name for the index.
name = "pytorch"
# Required URL for the index.
url = "https://download.pytorch.org/whl/cpu"
```

Indexes are prioritized in the order in which they're defined, such that the first index listed in the configuration file is the first index consulted when resolving dependencies, with indexes provided via the command line taking precedence over those in the configuration file.

By default, uv includes the Python Package Index (PyPI) as the "default" index, i.e., the index used when a package is not found on any other index. To exclude PyPI from the list of indexes, set `default = true` on another index entry (or use the `--default-index` command-line option):

```toml
[[tool.uv.index]]
name = "pytorch"
url = "https://download.pytorch.org/whl/cpu"
default = true
```

The default index is always treated as lowest priority, regardless of its position in the list of indexes.

Index names may only contain alphanumeric characters, dashes, underscores, and periods, and must be valid ASCII.

When providing an index on the command line (with `--index` or `--default-index`) or through an environment variable (`UV_INDEX` or `UV_DEFAULT_INDEX`), names are optional but can be included using the `<name>=<url>` syntax, as in:

```shell
# On the command line.
$ uv lock --index pytorch=https://download.pytorch.org/whl/cpu
# Via an environment variable.
$ UV_INDEX=pytorch=https://download.pytorch.org/whl/cpu uv lock
```

### Pinning a package to an index

A package can be pinned to a specific index by specifying the index in its `tool.uv.sources` entry. For example, to ensure that `torch` is _always_ installed from the `pytorch` index, add the following to your `pyproject.toml`:

```toml
[tool.uv.sources]
torch = { index = "pytorch" }

[[tool.uv.index]]
name = "pytorch"
url = "https://download.pytorch.org/whl/cpu"
```

Similarly, to pull from a different index based on the platform, you can provide a list of sources disambiguated by environment markers:

```toml
[project]
dependencies = ["torch"]

[tool.uv.sources]
torch = [
  { index = "pytorch-cu118", marker = "sys_platform == 'darwin'"},
  { index = "pytorch-cu124", marker = "sys_platform != 'darwin'"},
]

[[tool.uv.index]]
name = "pytorch-cu118"
url = "https://download.pytorch.org/whl/cu118"

[[tool.uv.index]]
name = "pytorch-cu124"
url = "https://download.pytorch.org/whl/cu124"
```

An index can be marked as `explicit = true` to prevent packages from being installed from that index unless explicitly pinned to it. For example, to ensure that `torch` is installed from the `pytorch` index, but all other packages are installed from PyPI, add the following to your `pyproject.toml`:

```toml
[tool.uv.sources]
torch = { index = "pytorch" }

[[tool.uv.index]]
name = "pytorch"
url = "https://download.pytorch.org/whl/cpu"
explicit = true
```

Named indexes referenced via `tool.uv.sources` must be defined within the project's `pyproject.toml` file; indexes provided via the command-line, environment variables, or user-level configuration will not be recognized.

If an index is marked as both `default = true` and `explicit = true`, it will be treated as an explicit index (i.e., only usable via `tool.uv.sources`) while also removing PyPI as the default index.

### Searching across multiple indexes

By default, uv will stop at the first index on which a given package is available, and limit resolutions to those present on that first index (`first-index`).

For example, if an internal index is specified via `[[tool.uv.index]]`, uv's behavior is such that if a package exists on that internal index, it will _always_ be installed from that internal index, and never from PyPI. The intent is to prevent "dependency confusion" attacks, in which an attacker publishes a malicious package on PyPI with the same name as an internal package, thus causing the malicious package to be installed instead of the internal package.

To opt in to alternate index behaviors, use the `--index-strategy` command-line option, or the `UV_INDEX_STRATEGY` environment variable, which supports the following values:

- `first-index` (default): Search for each package across all indexes, limiting the candidate versions to those present in the first index that contains the package.
- `unsafe-first-match`: Search for each package across all indexes, but prefer the first index with a compatible version, even if newer versions are available on other indexes.
- `unsafe-best-match`: Search for each package across all indexes, and select the best version from the combined set of candidate versions.

While `unsafe-best-match` is the closest to pip's behavior, it exposes users to the risk of "dependency confusion" attacks.

### Index authentication

Most private package indexes require authentication to access packages, typically via a username and password (or access token).

#### Providing credentials directly

Credentials can be provided directly via environment variables or by embedding them in the URL.

For example, given an index named `internal-proxy` that requires a username (`public`) and password (`koala`), define the index (without credentials) in your `pyproject.toml`:

```toml
[[tool.uv.index]]
name = "internal-proxy"
url = "https://example.com/simple"
```

From there, you can set the `UV_INDEX_INTERNAL_PROXY_USERNAME` and `UV_INDEX_INTERNAL_PROXY_PASSWORD` environment variables, where `INTERNAL_PROXY` is the uppercase version of the index name, with non-alphanumeric characters replaced by underscores:

```sh
export UV_INDEX_INTERNAL_PROXY_USERNAME=public
export UV_INDEX_INTERNAL_PROXY_PASSWORD=koala
```

By providing credentials via environment variables, you can avoid storing sensitive information in the plaintext `pyproject.toml` file.

Alternatively, credentials can be embedded directly in the index definition:

```toml
[[tool.uv.index]]
name = "internal"
url = "https://public:koala@pypi-proxy.corp.dev/simple"
```

For security purposes, credentials are _never_ stored in the `uv.lock` file; as such, uv _must_ have access to the authenticated URL at installation time.

#### Using credential providers

In addition to providing credentials directly, uv supports discovery of credentials from netrc and keyring. See `11-authentication.md` for details on setting up specific credential providers.

By default, uv will attempt an unauthenticated request before querying providers. If the request fails, uv will search for credentials. If credentials are found, an authenticated request will be attempted.

**Note:** If a username is set, uv will search for credentials before making an unauthenticated request.

Some indexes (e.g., GitLab) will forward unauthenticated requests to a public index, like PyPI -- which means that uv will not search for credentials. This behavior can be changed per-index, using the `authenticate` setting. For example, to always search for credentials:

```toml
[[tool.uv.index]]
name = "example"
url = "https://example.com/simple"
authenticate = "always"
```

When `authenticate` is set to `always`, uv will eagerly search for credentials and error if credentials cannot be found.

#### Ignoring error codes when searching across indexes

When using the first-index strategy, uv will stop searching across indexes if an HTTP 401 Unauthorized or HTTP 403 Forbidden status code is encountered. The one exception is that uv will ignore 403s when searching the `pytorch` index (since this index returns a 403 when a package is not present).

To configure which error codes are ignored for an index, use the `ignored-error-codes` setting. For example, to ignore 403s (but not 401s) for a private index:

```toml
[[tool.uv.index]]
name = "private-index"
url = "https://private-index.com/simple"
authenticate = "always"
ignore-error-codes = [403]
```

uv will always continue searching across indexes when it encounters a `404 Not Found`. This cannot be overridden.

#### Disabling authentication

To prevent leaking credentials, authentication can be disabled for an index:

```toml
[[tool.uv.index]]
name = "example"
url = "https://example.com/simple"
authenticate = "never"
```

When `authenticate` is set to `never`, uv will never search for credentials for the given index and will error if credentials are provided directly.

### Customizing cache control headers

By default, uv will respect the cache control headers provided by the index. For example, PyPI serves package metadata with a `max-age=600` header, thereby allowing uv to cache package metadata for 10 minutes; and wheels and source distributions with a `max-age=365000000, immutable` header, thereby allowing uv to cache artifacts indefinitely.

To override the cache control headers for an index, use the `cache-control` setting:

```toml
[[tool.uv.index]]
name = "example"
url = "https://example.com/simple"
cache-control = { api = "max-age=600", files = "max-age=365000000, immutable" }
```

The `cache-control` setting accepts an object with two optional keys:

- `api`: Controls caching for Simple API requests (package metadata).
- `files`: Controls caching for artifact downloads (wheels and source distributions).

The values for these keys are strings that follow the HTTP Cache-Control syntax. For example, to force uv to always revalidate package metadata, set `api = "no-cache"`:

```toml
[[tool.uv.index]]
name = "example"
url = "https://example.com/simple"
cache-control = { api = "no-cache" }
```

This setting is most commonly used to override the default cache control headers for private indexes that otherwise disable caching, often unintentionally. We typically recommend following PyPI's approach to caching headers, i.e., setting `api = "max-age=600"` and `files = "max-age=365000000, immutable"`.

### "Flat" indexes

By default, `[[tool.uv.index]]` entries are assumed to be PyPI-style registries that implement the PEP 503 Simple Repository API. However, uv also supports "flat" indexes, which are local directories or HTML pages that contain flat lists of wheels and source distributions. In pip, such indexes are specified using the `--find-links` option.

To define a flat index in your `pyproject.toml`, use the `format = "flat"` option:

```toml
[[tool.uv.index]]
name = "example"
url = "/path/to/directory"
format = "flat"
```

Flat indexes support the same feature set as Simple Repository API indexes (e.g., `explicit = true`); you can also pin a package to a flat index using `tool.uv.sources`.

### `--index-url` and `--extra-index-url`

In addition to the `[[tool.uv.index]]` configuration option, uv supports pip-style `--index-url` and `--extra-index-url` command-line options for compatibility, where `--index-url` defines the default index and `--extra-index-url` defines additional indexes.

These options can be used in conjunction with the `[[tool.uv.index]]` configuration option, and follow the same prioritization rules:

- The default index is always treated as lowest priority, whether defined via the legacy `--index-url` argument, the recommended `--default-index` argument, or a `[[tool.uv.index]]` entry with `default = true`.
- Indexes are consulted in the order in which they're defined, either via the legacy `--extra-index-url` argument, the recommended `--index` argument, or `[[tool.uv.index]]` entries.

In effect, `--index-url` and `--extra-index-url` can be thought of as unnamed `[[tool.uv.index]]` entries, with `default = true` enabled for the former. In that context, `--index-url` maps to `--default-index`, and `--extra-index-url` maps to `--index`.

## Caching

### Dependency caching

uv uses aggressive caching to avoid re-downloading (and re-building) dependencies that have already been accessed in prior runs.

The specifics of uv's caching semantics vary based on the nature of the dependency:

- **For registry dependencies** (like those downloaded from PyPI), uv respects HTTP caching headers.
- **For direct URL dependencies**, uv respects HTTP caching headers, and also caches based on the URL itself.
- **For Git dependencies**, uv caches based on the fully-resolved Git commit hash. As such, `uv pip compile` will pin Git dependencies to a specific commit hash when writing the resolved dependency set.
- **For local dependencies**, uv caches based on the last-modified time of the source archive (i.e., the local `.whl` or `.tar.gz` file). For directories, uv caches based on the last-modified time of the `pyproject.toml`, `setup.py`, or `setup.cfg` file.

If you're running into caching issues, uv includes a few escape hatches:

- To clear the cache entirely, run `uv cache clean`. To clear the cache for a specific package, run `uv cache clean <package-name>`. For example, `uv cache clean ruff` will clear the cache for the `ruff` package.
- To force uv to revalidate cached data for all dependencies, pass `--refresh` to any command (e.g., `uv sync --refresh` or `uv pip install --refresh ...`).
- To force uv to revalidate cached data for a specific dependency pass `--refresh-package` to any command (e.g., `uv sync --refresh-package ruff` or `uv pip install --refresh-package ruff ...`).
- To force uv to ignore existing installed versions, pass `--reinstall` to any installation command (e.g., `uv sync --reinstall` or `uv pip install --reinstall ...`). (Consider running `uv cache clean <package-name>` first, to ensure that the cache is cleared prior to reinstallation.)

As a special case, uv will always rebuild and reinstall any local directory dependencies passed explicitly on the command-line (e.g., `uv pip install .`).

### Dynamic metadata

By default, uv will _only_ rebuild and reinstall local directory dependencies (e.g., editables) if the `pyproject.toml`, `setup.py`, or `setup.cfg` file in the directory root has changed, or if a `src` directory is added or removed. This is a heuristic and, in some cases, may lead to fewer re-installs than desired.

To incorporate additional information into the cache key for a given package, you can add cache key entries under `tool.uv.cache-keys`, which covers both file paths and Git commit hashes. Setting `tool.uv.cache-keys` will replace defaults, so any necessary files (like `pyproject.toml`) should still be included in the user-defined cache keys.

For example, if a project specifies dependencies in `pyproject.toml` but uses `setuptools-scm` to manage its version, and should thus be rebuilt whenever the commit hash or dependencies change, you can add the following to the project's `pyproject.toml`:

```toml
[tool.uv]
cache-keys = [{ file = "pyproject.toml" }, { git = { commit = true } }]
```

If your dynamic metadata incorporates information from the set of Git tags, you can expand the cache key to include the tags:

```toml
[tool.uv]
cache-keys = [{ file = "pyproject.toml" }, { git = { commit = true, tags = true } }]
```

Similarly, if a project reads from a `requirements.txt` to populate its dependencies, you can add the following to the project's `pyproject.toml`:

```toml
[tool.uv]
cache-keys = [{ file = "pyproject.toml" }, { file = "requirements.txt" }]
```

Globs are supported for `file` keys, following the syntax of the `glob` crate. For example, to invalidate the cache whenever a `.toml` file in the project directory or any of its subdirectories is modified, use the following:

```toml
[tool.uv]
cache-keys = [{ file = "**/*.toml" }]
```

**Note:** The use of globs can be expensive, as uv may need to walk the filesystem to determine whether any files have changed. This may, in turn, require traversal of large or deeply nested directories.

Similarly, if a project relies on an environment variable, you can add the following to the project's `pyproject.toml` to invalidate the cache whenever the environment variable changes:

```toml
[tool.uv]
cache-keys = [{ file = "pyproject.toml" }, { env = "MY_ENV_VAR" }]
```

Finally, to invalidate a project whenever a specific directory (like `src`) is created or removed, add the following to the project's `pyproject.toml`:

```toml
[tool.uv]
cache-keys = [{ file = "pyproject.toml" }, { dir = "src" }]
```

Note that the `dir` key will only track changes to the directory itself, and not arbitrary changes within the directory.

As an escape hatch, if a project uses `dynamic` metadata that isn't covered by `tool.uv.cache-keys`, you can instruct uv to _always_ rebuild and reinstall it by adding the project to the `tool.uv.reinstall-package` list:

```toml
[tool.uv]
reinstall-package = ["my-package"]
```

This will force uv to rebuild and reinstall `my-package` on every run, regardless of whether the package's `pyproject.toml`, `setup.py`, or `setup.cfg` file has changed.

### Cache safety

It's safe to run multiple uv commands concurrently, even against the same virtual environment. uv's cache is designed to be thread-safe and append-only, and thus robust to multiple concurrent readers and writers. uv applies a file-based lock to the target virtual environment when installing, to avoid concurrent modifications across processes.

Note that it's _never_ safe to modify the cache directly (e.g., by removing a file or directory).

### Clearing the cache

uv provides a few different mechanisms for removing entries from the cache:

- `uv cache clean` removes _all_ cache entries from the cache directory, clearing it out entirely.
- `uv cache clean ruff` removes all cache entries for the `ruff` package, useful for invalidating the cache for a single or finite set of packages.
- `uv cache prune` removes all _unused_ cache entries. For example, the cache directory may contain entries created in previous uv versions that are no longer necessary and can be safely removed. `uv cache prune` is safe to run periodically, to keep the cache directory clean.

uv blocks cache-modifying operations while other uv commands are running. By default, those `uv cache` commands have a 5 min timeout waiting for other uv processes to terminate to avoid deadlocks. This timeout can be changed with `UV_LOCK_TIMEOUT`. In cases where it is known that no other uv processes are reading or writing from the cache, `--force` can be used to ignore the lock.

### Caching in continuous integration

It's common to cache package installation artifacts in continuous integration environments (like GitHub Actions or GitLab CI) to speed up subsequent runs. For CI/CD-specific guidance, see `14-ci-cd.md`.

By default, uv caches both the wheels that it builds from source and the pre-built wheels that it downloads directly, to enable high-performance package installation.

However, in continuous integration environments, persisting pre-built wheels may be undesirable. With uv, it turns out that it's often faster to _omit_ pre-built wheels from the cache (and instead re-download them from the registry on each run). On the other hand, caching wheels that are built from source tends to be worthwhile, since the wheel building process can be expensive, especially for extension modules.

To support this caching strategy, uv provides a `uv cache prune --ci` command, which removes all pre-built wheels and unzipped source distributions from the cache, but retains any wheels that were built from source. We recommend running `uv cache prune --ci` at the end of your continuous integration job to ensure maximum cache efficiency.

### Cache directory

uv determines the cache directory according to, in order:

1. A temporary cache directory, if `--no-cache` was requested.
2. The specific cache directory specified via `--cache-dir`, `UV_CACHE_DIR`, or `tool.uv.cache-dir`.
3. A system-appropriate cache directory, e.g., `$XDG_CACHE_HOME/uv` or `$HOME/.cache/uv` on Unix and `%LOCALAPPDATA%\uv\cache` on Windows.

**Note:** uv _always_ requires a cache directory. When `--no-cache` is requested, uv will still use a temporary cache for sharing data within that single invocation. In most cases, `--refresh` should be used instead of `--no-cache` -- as it will update the cache for subsequent operations but not read from the cache.

It is important for performance for the cache directory to be located on the same file system as the Python environment uv is operating on. Otherwise, uv will not be able to link files from the cache into the environment and will instead need to fallback to slow copy operations.

### Cache versioning

The uv cache is composed of a number of buckets (e.g., a bucket for wheels, a bucket for source distributions, a bucket for Git repositories, and so on). Each bucket is versioned, such that if a release contains a breaking change to the cache format, uv will not attempt to read from or write to an incompatible cache bucket.

For example, uv 0.4.13 included a breaking change to the core metadata bucket. As such, the bucket version was increased from v12 to v13. Within a cache version, changes are guaranteed to be both forwards- and backwards-compatible.

Since changes in the cache format are accompanied by changes in the cache version, multiple versions of uv can safely read and write to the same cache directory. However, if the cache version changed between a given pair of uv releases, then those releases may not be able to share the same underlying cache entries.

For example, it's safe to use a single shared cache for uv 0.4.12 and uv 0.4.13, though the cache itself may contain duplicate entries in the core metadata bucket due to the change in cache version.

## Preview Features

uv includes opt-in preview features to provide an opportunity for community feedback and increase confidence that changes are a net-benefit before enabling them for everyone.

### Enabling preview features

To enable all preview features, use the `--preview` flag:

```console
$ uv run --preview ...
```

Or, set the `UV_PREVIEW` environment variable:

```console
$ UV_PREVIEW=1 uv run ...
```

To enable specific preview features, use the `--preview-features` flag:

```console
$ uv run --preview-features foo ...
```

The `--preview-features` flag can be repeated to enable multiple features:

```console
$ uv run --preview-features foo --preview-features bar ...
```

Or, features can be provided in a comma separated list:

```console
$ uv run --preview-features foo,bar ...
```

The `UV_PREVIEW_FEATURES` environment variable can be used similarly, e.g.:

```console
$ UV_PREVIEW_FEATURES=foo,bar uv run ...
```

For backwards compatibility, enabling preview features that do not exist will warn, but not error.

### Using preview features

Often, preview features can be used without changing any preview settings if the behavior change is gated by some sort of user interaction. For example, while `pylock.toml` support is in preview, you can use `uv pip install` with a `pylock.toml` file without additional configuration because specifying the `pylock.toml` file indicates you want to use the feature. However, a warning will be displayed that the feature is in preview. The preview feature can be enabled to silence the warning.

### Available preview features

The following preview features are available:

- `add-bounds`: Allows configuring the default bounds for `uv add` invocations.
- `json-output`: Allows `--output-format json` for various uv commands.
- `package-conflicts`: Allows defining workspace conflicts at the package level.
- `pylock`: Allows installing from `pylock.toml` files.
- `python-install-default`: Allows installing `python` and `python3` executables.
- `format`: Allows using `uv format`.
- `native-auth`: Enables storage of credentials in a system-native location.
- `workspace-metadata`: Allows using `uv workspace metadata`.
- `workspace-dir`: Allows using `uv workspace dir`.
- `workspace-list`: Allows using `uv workspace list`.

### Disabling preview features

The `--no-preview` option can be used to disable preview features.

## Storage Locations

uv uses the following high-level directories for storage.

For each location, uv checks for the existence of environment variables in the given order and uses the first path found.

The paths of storage directories are platform-specific. uv follows the XDG conventions on Linux and macOS and the Known Folder scheme on Windows.

### Temporary directory

The temporary directory is used for ephemeral data.

#### Unix

1. `$TMPDIR`
2. `/tmp`

#### Windows

1. `%TMP%`
2. `%TEMP%`
3. `%USERPROFILE%`

### Cache directory (storage)

The cache directory is used for data that is disposable, but is useful to be long-lived.

#### Unix

1. `$XDG_CACHE_HOME/uv`
2. `$HOME/.cache/uv`

#### Windows

1. `%LOCALAPPDATA%\uv\cache`
2. `uv\cache` within `FOLDERID_LocalAppData`

### Persistent data directory

The persistent data directory is used for non-disposable data.

#### Unix

1. `$XDG_DATA_HOME/uv`
2. `$HOME/.local/share/uv`
3. `$CWD/.uv`

#### Windows

1. `%APPDATA%\uv\data`
2. `.\.uv`

### Configuration directories

The configuration directories are used to store changes to uv's settings.

User-level configuration:

#### Unix

1. `$XDG_CONFIG_HOME/uv`
2. `$HOME/.config/uv`

#### Windows

1. `%APPDATA%\uv`
2. `uv` within `FOLDERID_RoamingAppData`

System-level configuration:

#### Unix

1. `$XDG_CONFIG_DIRS/uv`
2. `/etc/uv`

#### Windows

1. `%PROGRAMDATA%\uv`
2. `uv` within `FOLDERID_AppDataProgramData`

### Executable directory

The executable directory is used to store files that can be run by the user, i.e., a directory that should be on the `PATH`.

#### Unix

1. `$XDG_BIN_HOME`
2. `$XDG_DATA_HOME/../bin`
3. `$HOME/.local/bin`

#### Windows

1. `%XDG_BIN_HOME%`
2. `%XDG_DATA_HOME%\..\bin`
3. `%USERPROFILE%\.local\bin`

### Types of data

#### Dependency cache

uv uses a local cache to avoid re-downloading and re-building dependencies.

By default, the cache is stored in the cache directory but it can be overridden via command line arguments, environment variables, or settings as detailed in the Caching section above. When the cache is disabled, the cache will be stored in a temporary directory.

Use `uv cache dir` to show the current cache directory path.

**Important:** For optimal performance, the cache directory needs to be on the same filesystem as virtual environments.

#### Python versions

uv can install managed Python versions, e.g., with `uv python install`.

By default, Python versions managed by uv are stored in a `python/` subdirectory of the persistent data directory, e.g., `~/.local/share/uv/python`.

Use `uv python dir` to show the Python installation directory.

Use the `UV_PYTHON_INSTALL_DIR` environment variable to override the installation directory.

**Note:** Changing where Python is installed will not be automatically reflected in existing virtual environments; they will keep referring to the old location, and will need to be updated manually (e.g. by re-creating them).

#### Python executables

uv installs executables for Python versions, e.g., `python3.13`.

By default, Python executables are stored in the executable directory.

Use `uv python dir --bin` to show the Python executable directory.

Use the `UV_PYTHON_BIN_DIR` environment variable to override the Python executable directory.

#### Tools

uv can install Python packages as command-line tools using `uv tool install`.

By default, tools are installed in a `tools/` subdirectory of the persistent data directory, e.g., `~/.local/share/uv/tools`.

Use `uv tool dir` to show the tool installation directory.

Use the `UV_TOOL_DIR` environment variable to configure the installation directory.

#### Tool executables

uv installs executables for installed tools, e.g., `ruff`.

By default, tool executables are stored in the executable directory.

Use `uv tool dir --bin` to show the tool executable directory.

Use the `UV_TOOL_BIN_DIR` environment variable to configure the tool executable directory.

#### The uv executable

When using uv's standalone installer to install uv, the `uv` and `uvx` executables are installed into the executable directory.

Use the `UV_INSTALL_DIR` environment variable to configure uv's installation directory.

#### Configuration files (storage)

uv's behavior can be configured through TOML files.

Configuration files are discovered in the configuration directories.

#### Project virtual environments

When working on projects, uv creates a dedicated virtual environment for each project.

By default, project virtual environments are created in `.venv` in the project or workspace root, i.e., next to the `pyproject.toml`.

Use the `UV_PROJECT_ENVIRONMENT` environment variable to override this location.

#### Script virtual environments

When running scripts with inline metadata, uv creates a dedicated virtual environment for each script in the cache directory. For details on scripts and inline metadata, see `07-tools-and-scripts.md`.

## See Also

- `03-project-config.md` - pyproject.toml project configuration
- `07-tools-and-scripts.md` - Tool storage and script environments
- `11-authentication.md` - Authentication for package indexes
- `12-workspaces.md` - Workspace configuration and shared settings
- `14-ci-cd.md` - CI/CD caching strategies
