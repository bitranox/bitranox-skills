# pip-Compatible Interface

uv provides a drop-in replacement for common `pip`, `pip-tools`, and `virtualenv` commands. These commands work directly with the virtual environment, in contrast to uv's primary interfaces (see `02-projects.md`) where the virtual environment is managed automatically. The `uv pip` interface exposes the speed and functionality of uv to power users and projects that are not ready to transition away from `pip` and `pip-tools`.

**Important:** uv does not rely on or invoke pip. The pip interface is named as such to highlight its dedicated purpose of providing low-level commands that match pip's interface and to separate it from the rest of uv's commands which operate at a higher level of abstraction.

Please note these commands do not _exactly_ implement the interfaces and behavior of the tools they are based on. The further you stray from common workflows, the more likely you are to encounter differences. See the Compatibility with pip section at the end of this document for details.

## Using Python Environments

Each Python installation has an environment that is active when Python is used. Packages can be installed into an environment to make their modules available from your Python scripts. Generally, it is considered best practice not to modify a Python installation's environment. This is especially important for Python installations that come with the operating system which often manage the packages themselves. A virtual environment is a lightweight way to isolate packages from a Python installation's environment. Unlike `pip`, uv requires using a virtual environment by default.

### Creating a virtual environment

uv supports creating virtual environments, e.g., to create a virtual environment at `.venv`:

```console
$ uv venv
```

A specific name or path can be specified, e.g., to create a virtual environment at `my-name`:

```console
$ uv venv my-name
```

A Python version can be requested, e.g., to create a virtual environment with Python 3.11:

```console
$ uv venv --python 3.11
```

Note this requires the requested Python version to be available on the system. However, if unavailable, uv will download Python for you.

### Using a virtual environment

When using the default virtual environment name, uv will automatically find and use the virtual environment during subsequent invocations.

```console
$ uv venv

$ # Install a package in the new virtual environment
$ uv pip install ruff
```

The virtual environment can be "activated" to make its packages available:

#### macOS and Linux

```console
$ source .venv/bin/activate
```

#### Windows

```pwsh-session
PS> .venv\Scripts\activate
```

**Note:** The default activation script on Unix is for POSIX compliant shells like `sh`, `bash`, or `zsh`. There are additional activation scripts for common alternative shells.

#### fish

```console
$ source .venv/bin/activate.fish
```

#### csh / tcsh

```console
$ source .venv/bin/activate.csh
```

#### Nushell

```console
$ use .venv\Scripts\activate.nu
```

### Deactivating an environment

To exit a virtual environment, use the `deactivate` command:

```console
$ deactivate
```

### Using arbitrary Python environments

Since uv has no dependency on Python, it can install into virtual environments other than its own. For example, setting `VIRTUAL_ENV=/path/to/venv` will cause uv to install into `/path/to/venv`, regardless of where uv is installed. Note that if `VIRTUAL_ENV` is set to a directory that is **not** a PEP 405 compliant virtual environment, it will be ignored.

uv can also install into arbitrary, even non-virtual environments, with the `--python` argument provided to `uv pip sync` or `uv pip install`. For example, `uv pip install --python /path/to/python` will install into the environment linked to the `/path/to/python` interpreter.

For convenience, `uv pip install --system` will install into the system Python environment. Using `--system` is roughly equivalent to `uv pip install --python $(which python)`, but note that executables that are linked to virtual environments will be skipped. Although we generally recommend using virtual environments for dependency management, `--system` is appropriate in continuous integration and containerized environments.

The `--system` flag is also used to opt in to mutating system environments. For example, the `--python` argument can be used to request a Python version (e.g., `--python 3.12`), and uv will search for an interpreter that meets the request. If uv finds a system interpreter (e.g., `/usr/lib/python3.12`), then the `--system` flag is required to allow modification of this non-virtual Python environment. Without the `--system` flag, uv will ignore any interpreters that are not in virtual environments. Conversely, when the `--system` flag is provided, uv will ignore any interpreters that _are_ in virtual environments.

Installing into system Python across platforms and distributions is notoriously difficult. uv supports the common cases, but will not work in all cases. For example, installing into system Python on Debian prior to Python 3.10 is unsupported due to the distribution's patching of `distutils` (but not `sysconfig`). While we always recommend the use of virtual environments, uv considers them to be required in these non-standard environments.

If uv is installed in a Python environment, e.g., with `pip`, it can still be used to modify other environments. However, when invoked with `python -m uv`, uv will default to using the parent interpreter's environment. Invoking uv via Python adds startup overhead and is not recommended for general usage.

uv itself does not depend on Python, but it does need to locate a Python environment to (1) install dependencies into the environment and (2) build source distributions.

### Discovery of Python environments

When running a command that mutates an environment such as `uv pip sync` or `uv pip install`, uv will search for a virtual environment in the following order:

- An activated virtual environment based on the `VIRTUAL_ENV` environment variable.
- An activated Conda environment based on the `CONDA_PREFIX` environment variable.
- A virtual environment at `.venv` in the current directory, or in the nearest parent directory.

If no virtual environment is found, uv will prompt the user to create one in the current directory via `uv venv`.

If the `--system` flag is included, uv will skip virtual environments search for an installed Python version. Similarly, when running a command that does not mutate the environment such as `uv pip compile`, uv does not _require_ a virtual environment -- however, a Python interpreter is still required.

## Managing Packages

### Installing a package

To install a package into the virtual environment, e.g., Flask:

```console
$ uv pip install flask
```

To install a package with optional dependencies enabled, e.g., Flask with the "dotenv" extra:

```console
$ uv pip install "flask[dotenv]"
```

To install multiple packages, e.g., Flask and Ruff:

```console
$ uv pip install flask ruff
```

To install a package with a constraint, e.g., Ruff v0.2.0 or newer:

```console
$ uv pip install 'ruff>=0.2.0'
```

To install a package at a specific version, e.g., Ruff v0.3.0:

```console
$ uv pip install 'ruff==0.3.0'
```

To install a package from the disk:

```console
$ uv pip install "ruff @ ./projects/ruff"
```

To install a package from GitHub:

```console
$ uv pip install "git+https://github.com/astral-sh/ruff"
```

To install a package from GitHub at a specific reference:

```console
$ # Install a tag
$ uv pip install "git+https://github.com/astral-sh/ruff@v0.2.0"

$ # Install a commit
$ uv pip install "git+https://github.com/astral-sh/ruff@1fadefa67b26508cc59cf38e6130bde2243c929d"

$ # Install a branch
$ uv pip install "git+https://github.com/astral-sh/ruff@main"
```

### Editable packages

Editable packages do not need to be reinstalled for changes to their source code to be active.

To install the current project as an editable package:

```console
$ uv pip install -e .
```

To install a project in another directory as an editable package:

```console
$ uv pip install -e "ruff @ ./project/ruff"
```

### Installing packages from files

Multiple packages can be installed at once from standard file formats.

Install from a `requirements.txt` file:

```console
$ uv pip install -r requirements.txt
```

Install from a `pyproject.toml` file:

```console
$ uv pip install -r pyproject.toml
```

Install from a `pyproject.toml` file with optional dependencies enabled, e.g., the "foo" extra:

```console
$ uv pip install -r pyproject.toml --extra foo
```

Install from a `pyproject.toml` file with all optional dependencies enabled:

```console
$ uv pip install -r pyproject.toml --all-extras
```

To install dependency groups in the current project directory's `pyproject.toml`, for example the group `foo`:

```console
$ uv pip install --group foo
```

To specify the project directory where groups should be sourced from:

```console
$ uv pip install --project some/path/ --group foo --group bar
```

Alternatively, you can specify a path to a `pyproject.toml` for each group:

```console
$ uv pip install --group some/path/pyproject.toml:foo --group other/pyproject.toml:bar
```

**Note:** As in pip, `--group` flags do not apply to other sources specified with flags like `-r` or `-e`. For instance, `uv pip install -r some/path/pyproject.toml --group foo` sources `foo` from `./pyproject.toml` and **not** `some/path/pyproject.toml`.

### Uninstalling a package

To uninstall a package, e.g., Flask:

```console
$ uv pip uninstall flask
```

To uninstall multiple packages, e.g., Flask and Ruff:

```console
$ uv pip uninstall flask ruff
```

## Declaring Dependencies

It is best practice to declare dependencies in a static file instead of modifying environments with ad-hoc installations. Once dependencies are defined, they can be locked to create a consistent, reproducible environment.

### Using `pyproject.toml`

The `pyproject.toml` file is the Python standard for defining configuration for a project.

To define project dependencies in a `pyproject.toml` file:

```toml
[project]
dependencies = [
  "httpx",
  "ruff>=0.3.0"
]
```

To define optional dependencies in a `pyproject.toml` file:

```toml
[project.optional-dependencies]
cli = [
  "rich",
  "click",
]
```

Each of the keys defines an "extra", which can be installed using the `--extra` and `--all-extras` flags or `package[<extra>]` syntax.

See the official [`pyproject.toml` guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) for more details on getting started with a `pyproject.toml`.

### Using `requirements.in`

It is also common to use a lightweight requirements file format to declare the dependencies for the project. Each requirement is defined on its own line. Commonly, this file is called `requirements.in` to distinguish it from `requirements.txt` which is used for the locked dependencies.

To define dependencies in a `requirements.in` file:

```text
httpx
ruff>=0.3.0
```

Optional dependencies groups are not supported in this format.

## Locking and Syncing Environments

Locking is to take a dependency, e.g., `ruff`, and write an exact version to use to a file. When working with many dependencies, it is useful to lock the exact versions so the environment can be reproduced. Without locking, the versions of dependencies could change over time, when using a different tool, or across platforms.

### Locking requirements

uv allows dependencies to be locked in the `requirements.txt` format. It is recommended to use the standard `pyproject.toml` to define dependencies, but other dependency formats are supported as well.

To lock dependencies declared in a `pyproject.toml`:

```console
$ uv pip compile pyproject.toml -o requirements.txt
```

Note by default the `uv pip compile` output is just displayed and `--output-file` / `-o` argument is needed to write to a file.

To lock dependencies declared in a `requirements.in`:

```console
$ uv pip compile requirements.in -o requirements.txt
```

To lock dependencies declared in multiple files:

```console
$ uv pip compile pyproject.toml requirements-dev.in -o requirements-dev.txt
```

uv also supports legacy `setup.py` and `setup.cfg` formats. To lock dependencies declared in a `setup.py`:

```console
$ uv pip compile setup.py -o requirements.txt
```

To lock dependencies from stdin, use `-`:

```console
$ echo "ruff" | uv pip compile -
```

To lock with optional dependencies enabled, e.g., the "foo" extra:

```console
$ uv pip compile pyproject.toml --extra foo
```

To lock with all optional dependencies enabled:

```console
$ uv pip compile pyproject.toml --all-extras
```

Note extras are not supported with the `requirements.in` format.

To lock a dependency group in the current project directory's `pyproject.toml`, for example the group `foo`:

```console
$ uv pip compile --group foo
```

**Important:** A `--group` flag has to be added to pip-tools' `pip compile`, although they're considering it (see [pip-tools#2062](https://github.com/jazzband/pip-tools/issues/2062)). We expect to support whatever syntax and semantics they adopt.

To specify the project directory where groups should be sourced from:

```console
$ uv pip compile --project some/path/ --group foo --group bar
```

Alternatively, you can specify a path to a `pyproject.toml` for each group:

```console
$ uv pip compile --group some/path/pyproject.toml:foo --group other/pyproject.toml:bar
```

**Note:** `--group` flags do not apply to other specified sources. For instance, `uv pip compile some/path/pyproject.toml --group foo` sources `foo` from `./pyproject.toml` and **not** `some/path/pyproject.toml`.

### Upgrading requirements

When using an output file, uv will consider the versions pinned in an existing output file. If a dependency is pinned it will not be upgraded on a subsequent compile run. For example:

```console
$ echo "ruff==0.3.0" > requirements.txt
$ echo "ruff" | uv pip compile - -o requirements.txt
# This file was autogenerated by uv via the following command:
#    uv pip compile - -o requirements.txt
ruff==0.3.0
```

To upgrade a dependency, use the `--upgrade-package` flag:

```console
$ uv pip compile - -o requirements.txt --upgrade-package ruff
```

To upgrade all dependencies, there is an `--upgrade` flag.

### Syncing an environment

Dependencies can be installed directly from their definition files or from compiled `requirements.txt` files with `uv pip install`.

When installing with `uv pip install`, packages that are already installed will not be removed unless they conflict with the lockfile. This means that the environment can have dependencies that aren't declared in the lockfile, which isn't great for reproducibility. To ensure the environment exactly matches the lockfile, use `uv pip sync` instead.

To sync an environment with a `requirements.txt` file:

```console
$ uv pip sync requirements.txt
```

To sync an environment with a PEP 751 `pylock.toml` file:

```console
$ uv pip sync pylock.toml
```

### Adding constraints

Constraints files are `requirements.txt`-like files that only control the _version_ of a requirement that's installed. However, including a package in a constraints file will _not_ trigger the installation of that package. Constraints can be used to add bounds to dependencies that are not dependencies of the current project.

To define a constraint, define a bound for a package:

```text
pydantic<2.0
```

To use a constraints file:

```console
$ uv pip compile requirements.in --constraint constraints.txt
```

Note that multiple constraints can be defined in each file and multiple files can be used.

uv will also read `constraint-dependencies` from the `pyproject.toml` at the workspace root, and append them to those specified in the constraints file.

### Adding build constraints

Similar to `constraints`, but specifically for build-time dependencies, including those required when building runtime dependencies.

Build constraint files are `requirements.txt`-like files that only control the _version_ of a build-time requirement. However, including a package in a build constraints file will _not_ trigger its installation at build time; instead, constraints apply only when the package is required as a direct or transitive build-time dependency. Build constraints can be used to add bounds to dependencies that are not explicitly declared as build-time dependencies of the current project.

For example, if a package defines its build dependencies as follows:

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
```

Build constraints could be used to ensure that a specific version of `setuptools` is used for every package in the workspace:

```text
setuptools==75.0.0
```

uv will also read `build-constraint-dependencies` from the `pyproject.toml` at the workspace root, and append them to those specified in the build constraints file.

### Overriding dependency versions

Overrides files are `requirements.txt`-like files that force a specific version of a requirement to be installed, regardless of the requirements declared by any constituent package, and regardless of whether this would be considered an invalid resolution.

While constraints are _additive_, in that they're combined with the requirements of the constituent packages, overrides are _absolute_, in that they completely replace the requirements of the constituent packages.

Overrides are most often used to remove upper bounds from a transitive dependency. For example, if `a` requires `c>=1.0,<2.0` and `b` requires `c>=2.0` and the current project requires `a` and `b` then the dependencies cannot be resolved.

To define an override, define the new requirement for the problematic package:

```text
c>=2.0
```

To use an overrides file:

```console
$ uv pip compile requirements.in --override overrides.txt
```

Now, resolution can succeed. However, note that if `a` is _correct_ that it does not support `c>=2.0` then a runtime error will likely be encountered when using the packages.

Note that multiple overrides can be defined in each file and multiple files can be used.

## Inspecting Environments

### Listing installed packages

To list all the packages in the environment:

```console
$ uv pip list
```

To list the packages in a JSON format:

```console
$ uv pip list --format json
```

To list all the packages in the environment in a `requirements.txt` format:

```console
$ uv pip freeze
```

### Inspecting a package

To show information about an installed package, e.g., `numpy`:

```console
$ uv pip show numpy
```

Multiple packages can be inspected at once.

### Verifying an environment

It is possible to install packages with conflicting requirements into an environment if installed in multiple steps.

To check for conflicts or missing dependencies in the environment:

```console
$ uv pip check
```

## Compatibility with pip and pip-tools

uv is designed as a drop-in replacement for common `pip` and `pip-tools` workflows.

Informally, the intent is such that existing `pip` and `pip-tools` users can switch to uv without making meaningful changes to their packaging workflows; and, in most cases, swapping out `pip install` for `uv pip install` should "just work".

However, uv is _not_ intended to be an _exact_ clone of `pip`, and the further you stray from common `pip` workflows, the more likely you are to encounter differences in behavior. In some cases, those differences may be known and intentional; in others, they may be the result of implementation details; and in others, they may be bugs.

This section outlines the known differences between uv and `pip`, along with rationale, workarounds, and a statement of intent for compatibility in the future.

### Configuration files and environment variables

uv does not read configuration files or environment variables that are specific to `pip`, like `pip.conf` or `PIP_INDEX_URL`.

Reading configuration files and environment variables intended for other tools has a number of drawbacks:

1. It requires bug-for-bug compatibility with the target tool, since users end up relying on bugs in the format, the parser, etc.
2. If the target tool _changes_ the format in some way, uv is then locked-in to changing it in equivalent ways.
3. If that configuration is versioned in some way, uv would need to know _which version_ of the target tool the user is expecting to use.
4. It prevents uv from introducing any settings or configuration that don't exist in the target tool, since otherwise `pip.conf` (or similar) would no longer be usable with `pip`.
5. It can lead to user confusion, since uv would be reading settings that don't actually affect its behavior, and many users may _not_ expect uv to read configuration files intended for other tools.

Instead, uv supports its own environment variables, like `UV_INDEX_URL`. uv also supports persistent configuration in a `uv.toml` file or a `[tool.uv.pip]` section of `pyproject.toml`. For details on configuration files, see `10-configuration.md`.

### Pre-release compatibility

By default, uv will accept pre-release versions during dependency resolution in two cases:

1. If the package is a direct dependency, and its version markers include a pre-release specifier (e.g., `flask>=2.0.0rc1`).
2. If _all_ published versions of a package are pre-releases.

If dependency resolution fails due to a transitive pre-release, uv will prompt the user to re-run with `--prerelease allow`, to allow pre-releases for all dependencies.

Alternatively, you can add the transitive dependency to your `requirements.in` file with pre-release specifier (e.g., `flask>=2.0.0rc1`) to opt in to pre-release support for that specific dependency.

In sum, uv needs to know upfront whether the resolver should accept pre-releases for a given package. Meanwhile `pip`, respects pre-release identifiers in transitive dependencies, and allows pre-releases of transitive dependencies if no stable versions match the dependency requirements.

**Note:** Prior to pip 26.0, this behavior was not consistent.

Pre-releases are notoriously difficult to model, and are a frequent source of bugs in packaging tools. uv's pre-release handling is _intentionally_ limited and _intentionally_ requires user opt-in for pre-releases, to ensure correctness.

In the future, uv _may_ support pre-release identifiers in transitive dependencies. However, it's likely contingent on evolution in the Python packaging specifications. The existing PEPs do not cover "dependency resolution" and are instead focused on behavior for a _single_ version specifier.

### Packages that exist on multiple indexes

In both uv and `pip`, users can specify multiple package indexes from which to search for the available versions of a given package. However, uv and `pip` differ in how they handle packages that exist on multiple indexes.

For example, imagine that a company publishes an internal version of `requests` on a private index (`--extra-index-url`), but also allows installing packages from PyPI by default. In this case, the private `requests` would conflict with the public `requests` on PyPI.

When uv searches for a package across multiple indexes, it will iterate over the indexes in order (preferring the `--extra-index-url` over the default index), and stop searching as soon as it finds a match. This means that if a package exists on multiple indexes, uv will limit its candidate versions to those present in the first index that contains the package.

`pip`, meanwhile, will combine the candidate versions from all indexes, and select the best version from the combined set, though it makes no guarantees around the order in which it searches indexes, and expects that packages are unique up to name and version, even across indexes.

uv's behavior is such that if a package exists on an internal index, it should always be installed from the internal index, and never from PyPI. The intent is to prevent "dependency confusion" attacks, in which an attacker publishes a malicious package on PyPI with the same name as an internal package, thus causing the malicious package to be installed instead of the internal package. See, for example, the `torchtriton` attack from December 2022.

As of v0.1.39, users can opt in to `pip`-style behavior for multiple indexes via the `--index-strategy` command-line option, or the `UV_INDEX_STRATEGY` environment variable, which supports the following values:

- `first-index` (default): Search for each package across all indexes, limiting the candidate versions to those present in the first index that contains the package, prioritizing the `--extra-index-url` indexes over the default index URL.
- `unsafe-first-match`: Search for each package across all indexes, but prefer the first index with a compatible version, even if newer versions are available on other indexes.
- `unsafe-best-match`: Search for each package across all indexes, and select the best version from the combined set of candidate versions.

While `unsafe-best-match` is the closest to `pip`'s behavior, it exposes users to the risk of "dependency confusion" attacks.

uv also supports pinning packages to dedicated indexes, such that a given package is _always_ installed from a specific index.

### PEP 517 build isolation

uv uses PEP 517 build isolation by default (akin to `pip install --use-pep517`), following `pypa/build` and in anticipation of `pip` defaulting to PEP 517 builds in the future.

If a package fails to install due to a missing build-time dependency, try using a newer version of the package; if the problem persists, consider filing an issue with the package maintainer, requesting that they update the packaging setup to declare the correct PEP 517 build-time dependencies.

As an escape hatch, you can preinstall a package's build dependencies, then run `uv pip install` with `--no-build-isolation`, as in:

```shell
uv pip install wheel && uv pip install --no-build-isolation biopython==1.77
```

### Transitive URL dependencies

While uv includes first-class support for URL dependencies (e.g., `ruff @ https://...`), it differs from pip in its handling of _transitive_ URL dependencies in two ways.

First, uv makes the assumption that non-URL dependencies do not introduce URL dependencies into the resolution. In other words, it assumes that dependencies fetched from a registry do not themselves depend on URLs. If a non-URL dependency _does_ introduce a URL dependency, uv will reject the URL dependency during resolution. (Note that PyPI does not allow published packages to depend on URL dependencies; other registries may be more permissive.)

Second, if a constraint (`--constraint`) or override (`--override`) is defined using a direct URL dependency, and the constrained package has a direct URL dependency of its own, uv _may_ reject that transitive direct URL dependency during resolution, if the URL isn't referenced elsewhere in the set of input requirements.

If uv rejects a transitive URL dependency, the best course of action is to provide the URL dependency as a direct dependency in the relevant `pyproject.toml` or `requirement.in` file, as the above constraints do not apply to direct dependencies.

### Virtual environments by default

`uv pip install` and `uv pip sync` are designed to work with virtual environments by default.

Specifically, uv will always install packages into the currently active virtual environment, or search for a virtual environment named `.venv` in the current directory or any parent directory (even if it is not activated).

This differs from `pip`, which will install packages into a global environment if no virtual environment is active, and will not search for inactive virtual environments.

In uv, you can install into non-virtual environments by providing a path to a Python executable via the `--python /path/to/python` option, or via the `--system` flag, which installs into the first Python interpreter found on the `PATH`, like `pip`.

In other words, uv inverts the default, requiring explicit opt-in to installing into the system Python, which can lead to breakages and other complications, and should only be done in limited circumstances.

### Resolution strategy

For a given set of dependency specifiers, it's often the case that there is no single "correct" set of packages to install. Instead, there are many valid sets of packages that satisfy the specifiers.

Neither `pip` nor uv make any guarantees about the _exact_ set of packages that will be installed; only that the resolution will be consistent, deterministic, and compliant with the specifiers. As such, in some cases, `pip` and uv will yield different resolutions; however, both resolutions _should_ be equally valid.

For example, consider:

```text
starlette
fastapi
```

At time of writing, the most recent `starlette` version is `0.37.2`, and the most recent `fastapi` version is `0.110.0`. However, `fastapi==0.110.0` also depends on `starlette`, and introduces an upper bound: `starlette>=0.36.3,<0.37.0`.

If a resolver prioritizes including the most recent version of `starlette`, it would need to use an older version of `fastapi` that excludes the upper bound on `starlette`. In practice, this requires falling back to `fastapi==0.1.17`:

```text
# This file was autogenerated by uv via the following command:
#    uv pip compile requirements.in
annotated-types==0.6.0
    # via pydantic
anyio==4.3.0
    # via starlette
fastapi==0.1.17
idna==3.6
    # via anyio
pydantic==2.6.3
    # via fastapi
pydantic-core==2.16.3
    # via pydantic
sniffio==1.3.1
    # via anyio
starlette==0.37.2
    # via fastapi
typing-extensions==4.10.0
    # via
    #   pydantic
    #   pydantic-core
```

Alternatively, if a resolver prioritizes including the most recent version of `fastapi`, it would need to use an older version of `starlette` that satisfies the upper bound. In practice, this requires falling back to `starlette==0.36.3`:

```text
# This file was autogenerated by uv via the following command:
#    uv pip compile requirements.in
annotated-types==0.6.0
    # via pydantic
anyio==4.3.0
    # via starlette
fastapi==0.110.0
idna==3.6
    # via anyio
pydantic==2.6.3
    # via fastapi
pydantic-core==2.16.3
    # via pydantic
sniffio==1.3.1
    # via anyio
starlette==0.36.3
    # via fastapi
typing-extensions==4.10.0
    # via
    #   fastapi
    #   pydantic
    #   pydantic-core
```

When uv resolutions differ from `pip` in undesirable ways, it's often a sign that the specifiers are too loose, and that the user should consider tightening them. For example, in the case of `starlette` and `fastapi`, the user could require `fastapi>=0.110.0`.

### `pip check`

At present, `uv pip check` will surface the following diagnostics:

- A package has no `METADATA` file, or the `METADATA` file can't be parsed.
- A package has a `Requires-Python` that doesn't match the Python version of the running interpreter.
- A package has a dependency on a package that isn't installed.
- A package has a dependency on a package that's installed, but at an incompatible version.
- Multiple versions of a package are installed in the virtual environment.

In some cases, `uv pip check` will surface diagnostics that `pip check` does not, and vice versa. For example, unlike `uv pip check`, `pip check` will _not_ warn when multiple versions of a package are installed in the current environment.

### `--user` and the `user` install scheme

uv does not support the `--user` flag, which installs packages based on the `user` install scheme. Instead, we recommend the use of virtual environments to isolate package installations.

Additionally, pip will fall back to the `user` install scheme if it detects that the user does not have write permissions to the target directory, as is the case on some systems when installing into the system Python. uv does not implement any such fallback.

### `--only-binary` enforcement

The `--only-binary` argument is used to restrict installation to pre-built binary distributions. When `--only-binary :all:` is provided, both pip and uv will refuse to build source distributions from PyPI and other registries.

However, when a dependency is provided as a direct URL (e.g., `uv pip install https://...`), pip does _not_ enforce `--only-binary`, and will build source distributions for all such packages.

uv, meanwhile, _does_ enforce `--only-binary` for direct URL dependencies, with one exception: given `uv pip install https://... --only-binary flask`, uv _will_ build the source distribution at the given URL if it cannot infer the package name ahead of time, since uv can't determine whether the package is "allowed" in such cases without building its metadata.

Both pip and uv allow editables requirements to be built and installed even when `--only-binary` is provided. For example, `uv pip install -e . --only-binary :all:` is allowed.

### `--no-binary` enforcement

The `--no-binary` argument is used to restrict installation to source distributions. When `--no-binary` is provided, uv will refuse to install pre-built binary distributions, but _will_ reuse any binary distributions that are already present in the local cache.

Additionally, and in contrast to pip, uv's resolver will still read metadata from pre-built binary distributions when `--no-binary` is provided.

### `manylinux_compatible` enforcement

PEP 600 describes a mechanism through which Python distributors can opt out of `manylinux` compatibility by defining a `manylinux_compatible` function on the `_manylinux` standard library module.

uv respects `manylinux_compatible`, but only tests against the current glibc version, and applies the return value of `manylinux_compatible` globally.

In other words, if `manylinux_compatible` returns `True`, uv will treat the system as `manylinux`-compatible; if it returns `False`, uv will treat the system as `manylinux`-incompatible, without calling `manylinux_compatible` for every glibc version.

This approach is not a complete implementation of the spec, but is compatible with common blanket `manylinux_compatible` implementations like `no-manylinux`:

```python
from __future__ import annotations
manylinux1_compatible = False
manylinux2010_compatible = False
manylinux2014_compatible = False


def manylinux_compatible(*_, **__):  # PEP 600
    return False
```

### Bytecode compilation

Unlike `pip`, uv does not compile `.py` files to `.pyc` files during installation by default (i.e., uv does not create or populate `__pycache__` directories). To enable bytecode compilation during installs, pass the `--compile-bytecode` flag to `uv pip install` or `uv pip sync`, or set the `UV_COMPILE_BYTECODE` environment variable to `1`.

Skipping bytecode compilation can be undesirable in workflows; for example, we recommend enabling bytecode compilation in Docker builds to improve startup times (at the cost of increased build times). For Docker-specific guidance, see `13-docker.md`.

As bytecode compilation suppresses various warnings issued by the Python interpreter, in rare cases you may see `SyntaxWarning` or `DeprecationWarning` messages when running Python code that was installed with uv that do not appear when using `pip`. These are valid warnings, but are typically hidden by the bytecode compilation process, and can either be ignored, fixed upstream, or similarly suppressed by enabling bytecode compilation in uv.

### Strictness and spec enforcement

uv tends to be stricter than `pip`, and will often reject packages that `pip` would install. For example, uv rejects HTML indexes with invalid URL fragments (see PEP 503), while `pip` will ignore such fragments.

In some cases, uv implements lenient behavior for popular packages that are known to have specific spec compliance issues.

If uv rejects a package that `pip` would install due to a spec violation, the best course of action is to first attempt to install a newer version of the package; and, if that fails, to report the issue to the package maintainer.

### `pip` command-line options and subcommands

uv does not support the complete set of `pip`'s command-line options and subcommands, although it does support a large subset.

Missing options and subcommands are prioritized based on user demand and the complexity of the implementation, and tend to be tracked in individual issues. For example:

- `--trusted-host` ([#1339](https://github.com/astral-sh/uv/issues/1339))
- `--user` ([#2077](https://github.com/astral-sh/uv/issues/2077))

If you encounter a missing option or subcommand, please search the issue tracker to see if it has already been reported, and if not, consider opening a new issue. Feel free to upvote any existing issues to convey your interest.

### Registry authentication

uv does not support `pip`'s `auto` or `import` options for `--keyring-provider`. At present, only the `subprocess` option is supported. For more on authentication, see `11-authentication.md`.

Unlike `pip`, uv does not enable keyring authentication by default.

Unlike `pip`, uv does not wait until a request returns an HTTP 401 before searching for authentication. uv attaches authentication to all requests for hosts with credentials available.

### `egg` support

uv does not support features that are considered legacy or deprecated in `pip`. For example, uv does not support `.egg`-style distributions.

However, uv does have partial support for (1) `.egg-info`-style distributions (which are occasionally found in Docker images and Conda environments) and (2) legacy editable `.egg-link`-style distributions.

Specifically, uv does not support installing new `.egg-info`- or `.egg-link`-style distributions, but will respect any such existing distributions during resolution, list them with `uv pip list` and `uv pip freeze`, and uninstall them with `uv pip uninstall`.

### Build constraints

When constraints are provided via `--constraint` (or `UV_CONSTRAINT`), uv will _not_ apply the constraints when resolving build dependencies (i.e., to build a source distribution). Instead, build constraints should be provided via the dedicated `--build-constraint` (or `UV_BUILD_CONSTRAINT`) setting.

pip, meanwhile, applies constraints to build dependencies when specified via `PIP_CONSTRAINT`, but not when provided via `--constraint` on the command line.

For example, to ensure that `setuptools 60.0.0` is used to build any packages with a build dependency on `setuptools`, use `--build-constraint`, rather than `--constraint`.

### `pip compile` defaults

There are a few small but notable differences in the default behaviors of `pip compile` and `pip-tools`.

By default, uv does not write the compiled requirements to an output file. Instead, uv requires that the user specify an output file explicitly with the `-o` or `--output-file` option.

By default, uv strips extras when outputting the compiled requirements. In other words, uv defaults to `--strip-extras`, while `pip-compile` defaults to `--no-strip-extras`. `pip-compile` is scheduled to change this default in the next major release (v8.0.0), at which point both tools will default to `--strip-extras`. To retain extras with uv, pass the `--no-strip-extras` flag to `uv pip compile`.

By default, uv does not write any index URLs to the output file, while `pip-compile` outputs any `--index-url` or `--extra-index-url` that does not match the default (PyPI). To include index URLs in the output file, pass the `--emit-index-url` flag to `uv pip compile`. Unlike `pip-compile`, uv will include all index URLs when `--emit-index-url` is passed, including the default index URL.

### `requires-python` upper bounds

When evaluating `requires-python` ranges for dependencies, uv only considers lower bounds and ignores upper bounds entirely. For example, `>=3.8, <4` is treated as `>=3.8`. Respecting upper bounds on `requires-python` often leads to formally correct but practically incorrect resolutions, as, e.g., resolvers will backtrack to the first published version that omits the upper bound.

### `requires-python` specifiers

When evaluating Python versions against `requires-python` specifiers, uv truncates the candidate version to the major, minor, and patch components, ignoring (e.g.) pre-release and post-release identifiers.

For example, a project that declares `requires-python: >=3.13` will accept Python 3.13.0b1. While 3.13.0b1 is not strictly greater than 3.13, it is greater than 3.13 when the pre-release identifier is omitted.

While this is not strictly compliant with PEP 440, it _is_ consistent with pip.

### Package priority

There are usually many possible solutions given a set of requirements, and a resolver must choose between them. uv's resolver and pip's resolver have a different set of package priorities. While both resolvers use the user-provided order as one of their priorities, pip has additional priorities that uv does not have. Hence, uv is more likely to be affected by a change in user order than pip is.

For example, `uv pip install foo bar` prioritizes newer versions of `foo` over `bar` and could result in a different resolution than `uv pip install bar foo`. Similarly, this behavior applies to the ordering of requirements in input files for `uv pip compile`.

### Wheel filename and metadata validation

By default, uv will reject wheels whose filenames are inconsistent with the wheel metadata inside the file. For example, a wheel named `foo-1.0.0-py3-none-any.whl` that contains metadata indicating the version is `1.0.1` will be rejected by uv, but accepted by pip.

To force uv to accept such wheels, set `UV_SKIP_WHEEL_FILENAME_CHECK=1` in the environment.

### Package name normalization

By default, uv normalizes package names to match their PEP 503-compliant forms and uses those normalized names in all output contexts. This differs from pip, which tends to preserve the verbatim package name as published on the registry.

For example, `uv pip list` displays normalized packages names (e.g., `docstring-parser`), while `pip list` displays non-normalized package names (e.g., `docstring_parser`):

```shell
(venv) $ diff --side-by-side  <(pip list) <(uv pip list)
Package          Version					Package          Version
---------------- -------					---------------- -------
docstring_parser 0.16					      |	docstring-parser 0.16
jaraco.classes   3.4.0					      |	jaraco-classes   3.4.0
more-itertools   10.7.0				    		more-itertools   10.7.0
pip              25.1					    	pip              25.1
PyMuPDFb         1.24.10				      |	pymupdfb         1.24.10
PyPDF2           3.0.1					      |	pypdf2           3.0.1
```

## See Also

- `04-dependencies.md` - Dependency management, groups, and sources
- `05-resolution.md` - Resolution strategies, overrides, and constraints
- `10-configuration.md` - Configuration files, indexes, and cache settings
- `11-authentication.md` - Authentication for private registries
- `16-migration.md` - Migrating from pip to uv
