# Project Management

uv supports managing Python projects, which define their dependencies in a `pyproject.toml` file.

## Creating Projects

uv supports creating a project with `uv init`.

When creating projects, uv supports two basic templates: **applications** and **libraries**. By default, uv will create a project for an application. The `--lib` flag can be used to create a project for a library instead.

You can create a new Python project using the `uv init` command:

```console
$ uv init hello-world
$ cd hello-world
```

Alternatively, you can initialize a project in the working directory:

```console
$ mkdir hello-world
$ cd hello-world
$ uv init
```

### Target Directory

uv will create a project in the working directory, or, in a target directory by providing a name, e.g., `uv init foo`. The working directory can be modified with the `--directory` option, which will cause the target directory path to be interpreted relative to the specified working directory. If there's already a project in the target directory, i.e., if there's a `pyproject.toml`, uv will exit with an error.

### Applications

Application projects are suitable for web servers, scripts, and command-line interfaces.

Applications are the default target for `uv init`, but can also be specified with the `--app` flag.

```console
$ uv init example-app
```

The project includes a `pyproject.toml`, a sample file (`main.py`), a readme, and a Python version pin file (`.python-version`).

```console
$ tree example-app
example-app
├── .python-version
├── README.md
├── main.py
└── pyproject.toml
```

**Note:** Prior to v0.6.0, uv created a file named `hello.py` instead of `main.py`.

The `pyproject.toml` includes basic metadata. It does not include a build system, it is not a package and will not be installed into the environment:

```toml
[project]
name = "example-app"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = []
```

The sample file defines a `main` function with some standard boilerplate:

```python
def main():
    print("Hello from example-app!")


if __name__ == "__main__":
    main()
```

Python files can be executed with `uv run`:

```console
$ cd example-app
$ uv run main.py
Hello from example-project!
```

### Packaged Applications

Many use-cases require a package. For example, if you are creating a command-line interface that will be published to PyPI or if you want to define tests in a dedicated directory.

The `--package` flag can be used to create a packaged application:

```console
$ uv init --package example-pkg
```

The source code is moved into a `src` directory with a module directory and an `__init__.py` file:

```console
$ tree example-pkg
example-pkg
├── .python-version
├── README.md
├── pyproject.toml
└── src
    └── example_pkg
        └── __init__.py
```

A build system is defined, so the project will be installed into the environment:

```toml
[project]
name = "example-pkg"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
example-pkg = "example_pkg:main"

[build-system]
requires = ["uv_build>=0.10.2,<0.11.0"]
build-backend = "uv_build"
```

**Tip:** The `--build-backend` option can be used to request an alternative build system.

A command definition is included in `[project.scripts]`. The command can be executed with `uv run`:

```console
$ cd example-pkg
$ uv run example-pkg
Hello from example-pkg!
```

### Libraries

A library provides functions and objects for other projects to consume. Libraries are intended to be built and distributed, e.g., by uploading them to PyPI.

Libraries can be created by using the `--lib` flag:

```console
$ uv init --lib example-lib
```

**Note:** Using `--lib` implies `--package`. Libraries always require a packaged project.

As with a packaged application, a `src` layout is used. A `py.typed` marker is included to indicate to consumers that types can be read from the library:

```console
$ tree example-lib
example-lib
├── .python-version
├── README.md
├── pyproject.toml
└── src
    └── example_lib
        ├── py.typed
        └── __init__.py
```

**Note:** A `src` layout is particularly valuable when developing libraries. It ensures that the library is isolated from any `python` invocations in the project root and that distributed library code is well separated from the rest of the project source.

A build system is defined, so the project will be installed into the environment:

```toml
[project]
name = "example-lib"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[build-system]
requires = ["uv_build>=0.10.2,<0.11.0"]
build-backend = "uv_build"
```

**Tip:** You can select a different build backend template by using `--build-backend` with `hatchling`, `uv_build`, `flit-core`, `pdm-backend`, `setuptools`, `maturin`, or `scikit-build-core`. An alternative backend is required if you want to create a library with extension modules.

The created module defines a simple API function:

```python
def hello() -> str:
    return "Hello from example-lib!"
```

And you can import and execute it using `uv run`:

```console
$ cd example-lib
$ uv run python -c "import example_lib; print(example_lib.hello())"
Hello from example-lib!
```

### Projects with Extension Modules

Most Python projects are "pure Python", meaning they do not define modules in other languages like C, C++, FORTRAN, or Rust. However, projects with extension modules are often used for performance sensitive code.

Creating a project with an extension module requires choosing an alternative build system. uv supports creating projects with the following build systems that support building extension modules:

- `maturin` for projects with Rust
- `scikit-build-core` for projects with C, C++, FORTRAN, Cython

Specify the build system with the `--build-backend` flag:

```console
$ uv init --build-backend maturin example-ext
```

**Note:** Using `--build-backend` implies `--package`.

The project contains a `Cargo.toml` and a `lib.rs` file in addition to the typical Python project files:

```console
$ tree example-ext
example-ext
├── .python-version
├── Cargo.toml
├── README.md
├── pyproject.toml
└── src
    ├── lib.rs
    └── example_ext
        ├── __init__.py
        └── _core.pyi
```

**Note:** If using `scikit-build-core`, you'll see CMake configuration and a `main.cpp` file instead.

The Rust library defines a simple function:

```rust
use pyo3::prelude::*;

#[pymodule]
mod _core {
    use pyo3::prelude::*;

    #[pyfunction]
    fn hello_from_bin() -> String {
        "Hello from example-ext!".to_string()
    }
}
```

And the Python module imports it:

```python
from example_ext._core import hello_from_bin


def main() -> None:
    print(hello_from_bin())
```

The command can be executed with `uv run`:

```console
$ cd example-ext
$ uv run example-ext
Hello from example-ext!
```

**Important:** When creating a project with maturin or scikit-build-core, uv configures `tool.uv.cache-keys` to include common source file types. To force a rebuild, e.g. when changing files outside `cache-keys` or when not using `cache-keys`, use `--reinstall`.

### Creating a Minimal Project

If you only want to create a `pyproject.toml`, use the `--bare` option:

```console
$ uv init example --bare
```

uv will skip creating a Python version pin file, a README, and any source directories or files. Additionally, uv will not initialize a version control system (i.e., `git`).

```console
$ tree example-bare
example-bare
└── pyproject.toml
```

uv will also not add extra metadata to the `pyproject.toml`, such as the `description` or `authors`.

```toml
[project]
name = "example"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []
```

The `--bare` option can be used with other options like `--lib` or `--build-backend` -- in these cases uv will still configure a build system but will not create the expected file structure.

When `--bare` is used, additional features can still be used opt-in:

```console
$ uv init example --bare --description "Hello world" --author-from git --vcs git --python-pin
```

## Project Structure and Files

### The `pyproject.toml`

Python project metadata is defined in a `pyproject.toml` file. uv requires this file to identify the root directory of a project.

A minimal project definition includes a name and version:

```toml
[project]
name = "example"
version = "0.1.0"
```

You'll use this file to specify dependencies, as well as details about the project such as its description or license. You can edit this file manually, or use commands like `uv add` and `uv remove` to manage your project from the terminal. For details on dependency management, see `04-dependencies.md`.

You'll also use this file to specify uv configuration options in a `[tool.uv]` section. For `pyproject.toml` configuration details, see `03-project-config.md`.

### The `.python-version` File

The `.python-version` file contains the project's default Python version. This file tells uv which Python version to use when creating the project's virtual environment.

### The Project Environment

When working on a project with uv, uv will create a virtual environment as needed. While some uv commands will create a temporary environment (e.g., `uv run --isolated`), uv also manages a persistent environment with the project and its dependencies in a `.venv` directory next to the `pyproject.toml`. It is stored inside the project to make it easy for editors to find -- they need the environment to give code completions and type hints. It is not recommended to include the `.venv` directory in version control; it is automatically excluded from `git` with an internal `.gitignore` file.

To run a command in the project environment, use `uv run`. Alternatively the project environment can be activated as normal for a virtual environment.

When `uv run` is invoked, it will create the project environment if it does not exist yet or ensure it is up-to-date if it exists. The project environment can also be explicitly created with `uv sync`.

It is _not_ recommended to modify the project environment manually, e.g., with `uv pip install`. For project dependencies, use `uv add` to add a package to the environment. For one-off requirements, use `uvx` or `uv run --with`.

**Tip:** If you don't want uv to manage the project environment, set `managed = false` to disable automatic locking and syncing of the project. For example:

```toml
[tool.uv]
managed = false
```

### The Lockfile

uv creates a `uv.lock` file next to the `pyproject.toml`.

`uv.lock` is a _universal_ or _cross-platform_ lockfile that captures the packages that would be installed across all possible Python markers such as operating system, architecture, and Python version.

Unlike the `pyproject.toml`, which is used to specify the broad requirements of your project, the lockfile contains the exact resolved versions that are installed in the project environment. This file should be checked into version control, allowing for consistent and reproducible installations across machines.

A lockfile ensures that developers working on the project are using a consistent set of package versions. Additionally, it ensures when deploying the project as an application that the exact set of used package versions is known.

The lockfile is automatically created and updated during uv invocations that use the project environment, i.e., `uv sync` and `uv run`. The lockfile may also be explicitly updated using `uv lock`.

`uv.lock` is a human-readable TOML file but is managed by uv and should not be edited manually. The `uv.lock` format is specific to uv and not usable by other tools.

#### Relationship to `pylock.toml`

In PEP 751, Python standardized a new resolution file format, `pylock.toml`.

`pylock.toml` is a resolution output format intended to replace `requirements.txt` (e.g., in the context of `uv pip compile`, whereby a "locked" `requirements.txt` file is generated from a set of input requirements). `pylock.toml` is standardized and tool-agnostic, such that in the future, `pylock.toml` files generated by uv could be installed by other tools, and vice versa.

Some of uv's functionality cannot be expressed in the `pylock.toml` format; as such, uv will continue to use the `uv.lock` format within the project interface.

However, uv supports `pylock.toml` as an export target and in the `uv pip` CLI. For example:

- To export a `uv.lock` to the `pylock.toml` format, run: `uv export -o pylock.toml`
- To generate a `pylock.toml` file from a set of requirements, run: `uv pip compile requirements.in -o pylock.toml`
- To install from a `pylock.toml` file, run: `uv pip sync pylock.toml` or `uv pip install -r pylock.toml`

## Running Commands

When working on a project, it is installed into the virtual environment at `.venv`. This environment is isolated from the current shell by default, so invocations that require the project, e.g., `python -c "import example"`, will fail. Instead, use `uv run` to run commands in the project environment:

```console
$ uv run python -c "import example"
```

When using `run`, uv will ensure that the project environment is up-to-date before running the given command. Prior to every `uv run` invocation, uv will verify that the lockfile is up-to-date with the `pyproject.toml`, and that the environment is up-to-date with the lockfile, keeping your project in-sync without the need for manual intervention. `uv run` guarantees that your command is run in an environment with all required dependencies at their locked versions.

The given command can be provided by the project environment or exist outside of it, e.g.:

```console
$ # Presuming the project provides `example-cli`
$ uv run example-cli foo

$ # Running a `bash` script that requires the project to be available
$ uv run bash scripts/foo.sh
```

For example, to use `flask`:

```console
$ uv add flask
$ uv run -- flask run -p 3000
```

Or, to run a script:

```python
# Require a project dependency
import flask

print("hello world")
```

```console
$ uv run example.py
```

Alternatively, you can use `uv sync` to manually update the environment then activate it before executing a command:

#### macOS and Linux

```console
$ uv sync
$ source .venv/bin/activate
$ flask run -p 3000
$ python example.py
```

#### Windows

```pwsh-session
PS> uv sync
PS> .venv\Scripts\activate
PS> flask run -p 3000
PS> python example.py
```

**Note:** The virtual environment must be active to run scripts and commands in the project without `uv run`. Virtual environment activation differs per shell and platform.

**Note:** `uv run` does not remove extraneous packages (those not in the lockfile) from the environment by default. See the "Handling of extraneous packages" section for details.

### Requesting Additional Dependencies

Additional dependencies or different versions of dependencies can be requested per invocation.

The `--with` option is used to include a dependency for the invocation, e.g., to request a different version of `httpx`:

```console
$ uv run --with httpx==0.26.0 python -c "import httpx; print(httpx.__version__)"
0.26.0
$ uv run --with httpx==0.25.0 python -c "import httpx; print(httpx.__version__)"
0.25.0
```

The requested version will be respected regardless of the project's requirements. For example, even if the project requires `httpx==0.24.0`, the output above would be the same.

### Running Scripts

Scripts that declare inline metadata are automatically executed in environments isolated from the project. For more on scripts and inline metadata, see `07-tools-and-scripts.md`.

For example, given a script:

```python
# /// script
# dependencies = [
#   "httpx",
# ]
# ///

import httpx

resp = httpx.get("https://peps.python.org/api/peps.json")
data = resp.json()
print([(k, v["title"]) for k, v in data.items()][:10])
```

The invocation `uv run example.py` would run _isolated_ from the project with only the given dependencies listed.

### Legacy Scripts on Windows

Support is provided for legacy setuptools scripts. These types of scripts are additional files installed by setuptools in `.venv\Scripts`.

Currently only legacy scripts with the `.ps1`, `.cmd`, and `.bat` extensions are supported.

For example, below is an example running a Command Prompt script:

```console
$ uv run --with nuitka==2.6.7 -- nuitka.cmd --version
```

In addition, you don't need to specify the extension. `uv` will automatically look for files ending in `.ps1`, `.cmd`, and `.bat` in that order of execution on your behalf.

```console
$ uv run --with nuitka==2.6.7 -- nuitka --version
```

### Signal Handling

uv does not cede control of the process to the spawned command in order to provide better error messages on failure. Consequently, uv is responsible for forwarding some signals to the child process the requested command runs in.

On Unix systems, uv will forward most signals (with the exception of SIGKILL, SIGCHLD, SIGIO, and SIGPOLL) to the child process. Since terminals send SIGINT to the foreground process group on Ctrl-C, uv will only forward a SIGINT to the child process if it is sent more than once or the child process group differs from uv's.

On Windows, these concepts do not apply and uv ignores Ctrl-C events, deferring handling to the child process so it can exit cleanly.

## Locking and Syncing

Locking is the process of resolving your project's dependencies into a lockfile. Syncing is the process of installing a subset of packages from the lockfile into the project environment.

### Automatic Lock and Sync

Locking and syncing are _automatic_ in uv. For example, when `uv run` is used, the project is locked and synced before invoking the requested command. This ensures the project environment is always up-to-date. Similarly, commands which read the lockfile, such as `uv tree`, will automatically update it before running.

To disable automatic locking, use the `--locked` option:

```console
$ uv run --locked ...
```

If the lockfile is not up-to-date, uv will raise an error instead of updating the lockfile.

To use the lockfile without checking if it is up-to-date, use the `--frozen` option:

```console
$ uv run --frozen ...
```

Similarly, to run a command without checking if the environment is up-to-date, use the `--no-sync` option:

```console
$ uv run --no-sync ...
```

### Checking the Lockfile

When considering if the lockfile is up-to-date, uv will check if it matches the project metadata. For example, if you add a dependency to your `pyproject.toml`, the lockfile will be considered outdated. Similarly, if you change the version constraints for a dependency such that the locked version is excluded, the lockfile will be considered outdated. However, if you change the version constraints such that the existing locked version is still included, the lockfile will still be considered up-to-date.

You can check if the lockfile is up-to-date by passing the `--check` flag to `uv lock`:

```console
$ uv lock --check
```

This is equivalent to the `--locked` flag for other commands.

**Important:** uv will not consider lockfiles outdated when new versions of packages are released -- the lockfile needs to be explicitly updated if you want to upgrade dependencies. See the section on upgrading locked package versions for details.

### Creating the Lockfile

While the lockfile is created automatically, the lockfile may also be explicitly created or updated using `uv lock`:

```console
$ uv lock
```

### Syncing the Environment

While the environment is synced automatically, it may also be explicitly synced using `uv sync`:

```console
$ uv sync
```

Syncing the environment manually is especially useful for ensuring your editor has the correct versions of dependencies.

#### Editable Installation

When the environment is synced, uv will install the project (and other workspace members) as _editable_ packages, such that re-syncing is not necessary for changes to be reflected in the environment.

To opt-out of this behavior, use the `--no-editable` option.

**Note:** If the project does not define a build system, it will not be installed.

#### Handling of Extraneous Packages

`uv sync` performs "exact" syncing by default, which means it will remove any packages that are not present in the lockfile.

To retain extraneous packages, use the `--inexact` flag:

```console
$ uv sync --inexact
```

In contrast, `uv run` uses "inexact" syncing by default, ensuring that all required packages are installed but not removing extraneous packages. To enable exact syncing with `uv run`, use the `--exact` flag:

```console
$ uv run --exact ...
```

#### Syncing Optional Dependencies

uv reads optional dependencies from the `[project.optional-dependencies]` table. These are frequently referred to as "extras".

uv does not sync extras by default. Use the `--extra` option to include an extra.

```console
$ uv sync --extra foo
```

To quickly enable all extras, use the `--all-extras` option.

#### Syncing Development Dependencies

uv reads development dependencies from the `[dependency-groups]` table (as defined in PEP 735).

The `dev` group is special-cased and synced by default.

The `--no-dev` flag can be used to exclude the `dev` group.

The `--only-dev` flag can be used to install the `dev` group _without_ the project and its dependencies.

Additional groups can be included or excluded with the `--all-groups`, `--no-default-groups`, `--group <name>`, `--only-group <name>`, and `--no-group <name>` options. The semantics of `--only-group` are the same as `--only-dev`, the project will not be included. However, `--only-group` will also exclude default groups.

Group exclusions always take precedence over inclusions, so given the command:

```console
$ uv sync --no-group foo --group foo
```

The `foo` group would not be installed.

### Upgrading Locked Package Versions

With an existing `uv.lock` file, uv will prefer the previously locked versions of packages when running `uv sync` and `uv lock`. Package versions will only change if the project's dependency constraints exclude the previous, locked version.

To upgrade all packages:

```console
$ uv lock --upgrade
```

To upgrade a single package to the latest version, while retaining the locked versions of all other packages:

```console
$ uv lock --upgrade-package <package>
```

To upgrade a single package to a specific version:

```console
$ uv lock --upgrade-package <package>==<version>
```

In all cases, upgrades are limited to the project's dependency constraints. For example, if the project defines an upper bound for a package then an upgrade will not go beyond that version.

**Note:** uv applies similar logic to Git dependencies. For example, if a Git dependency references the `main` branch, uv will prefer the locked commit SHA in an existing `uv.lock` file over the latest commit on the `main` branch, unless the `--upgrade` or `--upgrade-package` flags are used.

These flags can also be provided to `uv sync` or `uv run` to update the lockfile _and_ the environment.

### Exporting the Lockfile

If you need to integrate uv with other tools or workflows, you can export `uv.lock` to different formats including `requirements.txt`, `pylock.toml` (PEP 751), and CycloneDX SBOM.

```console
$ uv export --format requirements.txt
$ uv export --format pylock.toml
$ uv export --format cyclonedx1.5
```

### Partial Installations

Sometimes it's helpful to perform installations in multiple steps, e.g., for optimal layer caching while building a Docker image (see `13-docker.md`). `uv sync` has several flags for this purpose.

- `--no-install-project`: Do not install the current project
- `--no-install-workspace`: Do not install any workspace members, including the root project
- `--no-install-package <NO_INSTALL_PACKAGE>`: Do not install the given package(s)

When these options are used, all the dependencies of the target are still installed. For example, `--no-install-project` will omit the _project_ but not any of its dependencies.

If used improperly, these flags can result in a broken environment since a package can be missing its dependencies.

## Managing Dependencies

You can add dependencies to your `pyproject.toml` with the `uv add` command. This will also update the lockfile and project environment:

```console
$ uv add requests
```

You can also specify version constraints or alternative sources:

```console
$ # Specify a version constraint
$ uv add 'requests==2.31.0'

$ # Add a git dependency
$ uv add git+https://github.com/psf/requests
```

If you're migrating from a `requirements.txt` file, you can use `uv add` with the `-r` flag to add all dependencies from the file:

```console
$ # Add all dependencies from `requirements.txt`.
$ uv add -r requirements.txt -c constraints.txt
```

To remove a package, you can use `uv remove`:

```console
$ uv remove requests
```

To upgrade a package, run `uv lock` with the `--upgrade-package` flag:

```console
$ uv lock --upgrade-package requests
```

The `--upgrade-package` flag will attempt to update the specified package to the latest compatible version, while keeping the rest of the lockfile intact.

## Viewing Your Version

The `uv version` command can be used to read your package's version.

To get the version of your package, run `uv version`:

```console
$ uv version
hello-world 0.7.0
```

To get the version without the package name, use the `--short` option:

```console
$ uv version --short
0.7.0
```

To get version information in a JSON format, use the `--output-format json` option:

```console
$ uv version --output-format json
{
    "package_name": "hello-world",
    "version": "0.7.0",
    "commit_info": null
}
```

## Building Distributions

`uv build` can be used to build source distributions and binary distributions (wheel) for your project.

By default, `uv build` will build the project in the current directory, and place the built artifacts in a `dist/` subdirectory:

```console
$ uv build
$ ls dist/
hello-world-0.1.0-py3-none-any.whl
hello-world-0.1.0.tar.gz
```

## See Also

- `03-project-config.md` - pyproject.toml configuration details
- `04-dependencies.md` - Dependency management, groups, and sources
- `05-resolution.md` - Resolution strategies and overrides
- `06-python-versions.md` - Python version management
- `08-building-and-publishing.md` - Building and publishing packages
- `12-workspaces.md` - Monorepo workspaces
