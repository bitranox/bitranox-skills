# Troubleshooting

## Build Failures

uv needs to build packages when there is not a compatible wheel (a pre-built distribution of the package) available. Building packages can fail for many reasons, some of which may be unrelated to uv itself.

### Recognizing a build failure

An example build failure can be produced by trying to install an old version of numpy on a new, unsupported version of Python:

```console
$ uv pip install -p 3.13 'numpy<1.20'
Resolved 1 package in 62ms
  x Failed to build `numpy==1.19.5`
  |-- The build backend returned an error
  \-- Call to `setuptools.build_meta:__legacy__.build_wheel()` failed (exit status: 1)

      [stderr]
      Traceback (most recent call last):
        File "<string>", line 8, in <module>
          from setuptools.build_meta import __legacy__ as backend
        File "/home/konsti/.cache/uv/builds-v0/.tmpi4bgKb/lib/python3.13/site-packages/setuptools/__init__.py", line 9, in <module>
          import distutils.core
      ModuleNotFoundError: No module named 'distutils'

      hint: `distutils` was removed from the standard library in Python 3.12. Consider adding a constraint (like `numpy >1.19.5`) to avoid building a version of `numpy` that depends
      on `distutils`.
```

Notice that the error message is prefaced by "The build backend returned an error".

The build failure includes the `[stderr]` (and `[stdout]`, if present) from the build backend that was used for the build. The error logs are not from uv itself.

The message following the last arrow is a hint provided by uv, to help resolve common build failures. A hint will not be available for all build failures.

### Confirming that a build failure is specific to uv

Build failures are usually related to your system and the build backend. It is rare that a build failure is specific to uv. You can confirm that the build failure is not related to uv by attempting to reproduce it with pip:

```console
$ uv venv -p 3.13 --seed
$ source .venv/bin/activate
$ pip install --use-pep517 --no-cache --force-reinstall 'numpy==1.19.5'
```

**Important:** The `--use-pep517` flag should be included with the `pip install` invocation to ensure the same build isolation behavior. uv always uses build isolation by default. We also recommend including the `--force-reinstall` and `--no-cache` options when reproducing failures.

Since this build failure occurs in pip too, it is not likely to be a bug with uv.

If a build failure is reproducible with another installer, you should investigate upstream (in this example, `numpy` or `setuptools`), find a way to avoid building the package in the first place, or make the necessary adjustments to your system for the build to succeed.

### Why does uv build a package?

When generating the cross-platform lockfile, uv needs to determine the dependencies of all packages, even those only installed on other platforms. uv tries to avoid package builds during resolution. It uses any wheel if one exists for that version, then tries to find static metadata in the source distribution (mainly pyproject.toml with static `project.version`, `project.dependencies` and `project.optional-dependencies` or METADATA v2.2+). Only if all of that fails, it builds the package.

When installing, uv needs to have a wheel for the current platform for each package. If no matching wheel exists in the index, uv tries to build the source distribution.

You can check which wheels exist for a PyPI project under "Download Files", e.g. on the numpy PyPI page. Wheels with `...-py3-none-any.whl` filenames work everywhere, others have the operating system and platform in the filename.

### Common build failures

#### Command is not found

If the build error mentions a missing command, for example, `gcc`:

```text
x Failed to build `pysha3==1.0.2`
|-- The build backend returned an error
\-- Call to `setuptools.build_meta:__legacy__.build_wheel` failed (exit status: 1)

    [stdout]
    running bdist_wheel
    running build
    running build_py
    creating build/lib.linux-x86_64-cpython-310
    copying sha3.py -> build/lib.linux-x86_64-cpython-310
    running build_ext
    building '_pysha3' extension
    creating build/temp.linux-x86_64-cpython-310/Modules/_sha3
    gcc -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O3 -Wall -fPIC -DPY_WITH_KECCAK=1 -I/root/.cache/uv/builds-v0/.tmp8V4iEk/include -I/usr/local/include/python3.10 -c
    Modules/_sha3/sha3module.c -o build/temp.linux-x86_64-cpython-310/Modules/_sha3/sha3module.o

    [stderr]
    error: command 'gcc' failed: No such file or directory
```

Then, you'll need to install it with your system package manager, e.g., to resolve the error above:

```console
$ apt install gcc
```

**Tip:** When using the uv-managed Python versions, it's common to need `clang` installed instead of `gcc`. Many Linux distributions provide a package that includes all the common build dependencies. You can address most build requirements by installing it, e.g., for Debian or Ubuntu:

```console
$ apt install build-essential
```

#### Header or library is missing

If the build error mentions a missing header or library, e.g., a `.h` file, then you'll need to install it with your system package manager.

For example, installing `pygraphviz` requires Graphviz to be installed:

```text
x Failed to build `pygraphviz==1.14`
|-- The build backend returned an error
\-- Call to `setuptools.build_meta.build_wheel` failed (exit status: 1)

  [stdout]
  running bdist_wheel
  running build
  running build_py
  ...
  gcc -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall -fPIC -DSWIG_PYTHON_STRICT_BYTE_CHAR -I/root/.cache/uv/builds-v0/.tmpgLYPe0/include -I/usr/local/include/python3.12 -c pygraphviz/graphviz_wrap.c -o
  build/temp.linux-x86_64-cpython-312/pygraphviz/graphviz_wrap.o

  [stderr]
  ...
  pygraphviz/graphviz_wrap.c:9: warning: "SWIG_PYTHON_STRICT_BYTE_CHAR" redefined
      9 | #define SWIG_PYTHON_STRICT_BYTE_CHAR
        |
  <command-line>: note: this is the location of the previous definition
  pygraphviz/graphviz_wrap.c:3023:10: fatal error: graphviz/cgraph.h: No such file or directory
    3023 | #include "graphviz/cgraph.h"
        |          ^~~~~~~~~~~~~~~~~~~
  compilation terminated.
  error: command '/usr/bin/gcc' failed with exit code 1

  hint: This error likely indicates that you need to install a library that provides "graphviz/cgraph.h" for `pygraphviz@1.14`
```

To resolve this error on Debian, you'd install the `libgraphviz-dev` package:

```console
$ apt install libgraphviz-dev
```

Note that installing the `graphviz` package is not sufficient, the development headers need to be installed.

**Tip:** To resolve an error where `Python.h` is missing, install the `python3-dev` package.

#### Module is missing or cannot be imported

If the build error mentions a failing import, consider disabling build isolation.

For example, some packages assume that `pip` is available without declaring it as a build dependency:

```text
  x Failed to build `chumpy==0.70`
  |-- The build backend returned an error
  \-- Call to `setuptools.build_meta:__legacy__.build_wheel` failed (exit status: 1)

    [stderr]
    Traceback (most recent call last):
      File "<string>", line 9, in <module>
    ModuleNotFoundError: No module named 'pip'

    During handling of the above exception, another exception occurred:

    Traceback (most recent call last):
      File "<string>", line 14, in <module>
      ...
    ModuleNotFoundError: No module named 'pip'
```

To resolve this error, pre-install the build dependencies then disable build isolation for the package:

```console
$ uv pip install pip setuptools
$ uv pip install chumpy --no-build-isolation-package chumpy
```

Note you will need to install the missing package, e.g., `pip`, _and_ all the other build dependencies of the package, e.g, `setuptools`.

#### Old version of the package is built

If a package fails to build during resolution and the version that failed to build is older than the version you want to use, try adding a constraint with a lower bound (e.g., `numpy>=1.17`). Sometimes, due to algorithmic limitations, the uv resolver tries to find a fitting version using unreasonably old packages, which can be prevented by using lower bounds.

For example, when resolving the following dependencies on Python 3.10, uv attempts to build an old version of `apache-beam`.

**`requirements.txt`:**

```text
dill<0.3.9,>=0.2.2
apache-beam<=2.49.0
```

```text
x Failed to build `apache-beam==2.0.0`
|-- The build backend returned an error
\-- Call to `setuptools.build_meta:__legacy__.build_wheel` failed (exit status: 1)

    [stderr]
    ...
```

Adding a lower bound constraint, e.g., `apache-beam<=2.49.0,>2.30.0`, resolves this build failure as uv will avoid using an old version of `apache-beam`.

Constraints can also be defined for indirect dependencies using `constraints.txt` files or the `constraint-dependencies` setting. For details on resolution strategies, see `05-resolution.md`.

#### Old version of a build dependency is used

If a package fails to build because `uv` selects an incompatible or outdated version of a build-time dependency, you can enforce constraints specifically for build dependencies. The `build-constraint-dependencies` setting (or an analogous `build-constraints.txt` file) can be used to ensure that `uv` selects an appropriate version of a given build requirement.

For example, the issue described in #5551 could be addressed by specifying a build constraint that excludes `setuptools` version `72.0.0`:

**`pyproject.toml`:**

```toml
[tool.uv]
# Prevent setuptools version 72.0.0 from being used as a build dependency.
build-constraint-dependencies = ["setuptools!=72.0.0"]
```

The build constraint will thus ensure that any package requiring `setuptools` during the build process will avoid using the problematic version, preventing build failures caused by incompatible build dependencies.

#### Package is only needed for an unused platform

If locking fails due to building a package from a platform you do not need to support, consider limiting resolution to your supported platforms. See the `tool.uv.environments` setting in `10-configuration.md`.

#### Package does not support all Python versions

If you support a large range of Python versions, consider using markers to use older versions for older Python versions and newer versions for newer Python version. For example, `numpy` only supports four Python minor version at a time, so to support a wider range of Python versions, e.g., Python 3.8 to 3.13, the `numpy` requirement needs to be split:

```
numpy>=1.23; python_version >= "3.10"
numpy<1.23; python_version < "3.10"
```

#### Package is only usable on a specific platform

If locking fails due to building a package that is only usable on another platform, you can provide dependency metadata manually to skip the build. uv cannot verify this information, so it is important to specify correct metadata when using this override.

## Reproducible Examples

### Why reproducible examples are important

A minimal reproducible example (MRE) is essential for fixing bugs. Without an example that can be used to reproduce the problem, a maintainer cannot debug it or test if it is fixed. If the example is not minimal, i.e., if it includes lots of content which is not related to the issue, it can take a maintainer much longer to identify the root cause of the problem.

### How to write a reproducible example

When writing a reproducible example, the goal is to provide all the context necessary for someone else to reproduce your example. This includes:

- The platform you're using (e.g., the operating system and architecture)
- Any relevant system state (e.g., explicitly set environment variables)
- The version of uv
- The version of other relevant tools
- The relevant files (the `uv.lock`, `pyproject.toml`, etc.)
- The commands to run

To ensure your reproduction is minimal, remove as many dependencies, settings, and files as possible. Be sure to test your reproduction before sharing it. We recommend including verbose logs from your reproduction; they may differ on your machine in a critical way. Using a Gist can be helpful for very long logs.

**Tip:** There's a great guide to the basics of creating MREs on Stack Overflow.

### Strategies for reproducible examples

#### Docker image

Writing a Docker image is often the best way to share a reproducible example because it is entirely self-contained. This means that the state from the reproducer's system does not affect the problem.

**Note:** Using a Docker image is only feasible if the issue is reproducible on Linux. When using macOS, it's prudent to ensure your image is not reproducible on Linux but some bugs _are_ specific to the operating system. While using Docker to run Windows containers is feasible, it's not commonplace. These sorts of bugs are expected to be reported as a script instead.

When writing a Docker MRE with uv, it's best to start with one of uv's Docker images (see `13-docker.md` for available images). When doing so, be sure to pin to a specific version of uv.

```dockerfile
FROM ghcr.io/astral-sh/uv:0.5.24-debian-slim
```

While Docker images are isolated from the system, the build will use your system's architecture by default. When sharing a reproduction, you can explicitly set the platform to ensure a reproducer gets the expected behavior. uv publishes images for `linux/amd64` (e.g., Intel or AMD) and `linux/arm64` (e.g., Apple M Series or ARM).

```dockerfile
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:0.5.24-debian-slim
```

Docker images are best for reproducing issues that can be constructed with commands, e.g.:

```dockerfile
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:0.5.24-debian-slim

RUN uv init /mre
WORKDIR /mre
RUN uv add pydantic
RUN uv sync
RUN uv run -v python -c "import pydantic"
```

However, you can also write files into the image inline:

```dockerfile
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:0.5.24-debian-slim

COPY <<EOF /mre/pyproject.toml
[project]
name = "example"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = ["pydantic"]
EOF

WORKDIR /mre
RUN uv lock
```

If you need to write many files, it's better to create and publish a Git repository. You can combine these approaches and include a `Dockerfile` in the repository.

When sharing a Docker reproduction, it's helpful to include the build logs. You can see more output from the build steps by disabling caching and the fancy output:

```console
docker build . --progress plain --no-cache
```

#### Script

When reporting platform-specific bugs that cannot be reproduced in a container, it's best practice to include a script showing the commands that can be used to reproduce the bug, e.g.:

```bash
uv init
uv add pydantic
uv sync
uv run -v python -c "import pydantic"
```

If your reproduction requires many files, use a Git repository to share them.

In addition to the script, include _verbose_ logs (i.e., with the `-v` flag) of the failure and the complete error message.

Whenever a script relies on external state, be sure to share that information. For example, if you wrote the script on Windows, and it uses a Python version that you installed with `choco` and runs on PowerShell 6.2, please include that in the report.

#### Git repository

When sharing a Git repository reproduction, include a script that reproduces the problem or, even better, a Dockerfile. The first step of the script should be to clone the repository and checkout a specific commit:

```console
$ git clone https://github.com/<user>/<project>.git
$ cd <project>
$ git checkout <commit>
$ <commands to produce error>
```

You can quickly create a new repository in the GitHub UI or with the `gh` CLI:

```console
$ gh repo create uv-mre-1234 --clone
```

When using a Git repository for a reproduction, please remember to _minimize_ the contents by excluding files or settings that are not required to reproduce your problem.

## Platform Support

uv has Tier 1 support for the following platforms:

- macOS (Apple Silicon)
- macOS (x86_64)
- Linux (x86_64)
- Windows (x86_64)

uv is continuously built, tested, and developed against its Tier 1 platforms. Inspired by the Rust project, Tier 1 can be thought of as "guaranteed to work".

uv has Tier 2 support ("guaranteed to build") for the following platforms:

- Linux (PPC64LE)
- Linux (RISC-V64)
- Linux (aarch64)
- Linux (armv7)
- Linux (i686)
- Linux (s390x)
- Windows (arm64)

uv ships pre-built wheels to PyPI for its Tier 1 and Tier 2 platforms. However, while Tier 2 platforms are continuously built, they are not continuously tested or developed against, and so stability may vary in practice.

Beyond the Tier 1 and Tier 2 platforms, uv is known to build on i686 Windows, and known _not_ to build on aarch64 Windows, but does not consider either platform to be supported at this time. The minimum supported Windows versions are Windows 10 and Windows Server 2016, following Rust's own Tier 1 support.

### macOS versions

uv supports macOS 13+ (Ventura).

uv is known to work on macOS 12, but requires installation of a `realpath` executable.

### Python version support

uv supports and is tested against the following Python versions:

- 3.8
- 3.9
- 3.10
- 3.11
- 3.12
- 3.13
- 3.14

### Python implementation support

uv has Tier 1 support for the following Python implementations:

- CPython

As with platforms, Tier 1 support can be thought of "guaranteed to work". uv supports managed installations of these implementations, and the builds are maintained by Astral.

uv has Tier 2 support for:

- PyPy
- GraalPy

uv is "expected to work" with these implementations. uv also supports managed installations of these Python implementations, but the builds are not maintained by Astral.

uv has Tier 3 support for:

- Pyston
- Pyodide

uv "should work" with these implementations, but stability may vary.

### Minimum supported Rust version

The minimum supported Rust version required to compile uv is listed in the `rust-version` key of the `[workspace.package]` section in `Cargo.toml`. It may change in any release (minor or patch). It will never be newer than N-2 Rust versions, where N is the latest stable version. For example, if the latest stable Rust version is 1.85, uv's minimum supported Rust version will be at most 1.83.

This is only relevant to users who build uv from source. Installing uv from the Python package index usually installs a pre-built binary and does not require Rust compilation.

## See Also

- `05-resolution.md` - Resolution strategies, overrides, and constraints
- `06-python-versions.md` - Python version management
- `10-configuration.md` - Config files, environment variables, and storage
- `13-docker.md` - Docker integration
- `16-migration.md` - Migrating from pip
