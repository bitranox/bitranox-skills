# Building and Publishing

uv supports building Python packages into source and binary distributions via `uv build` and uploading them to a registry with `uv publish`.

## Preparing Your Project

Before attempting to publish your project, you'll want to make sure it's ready to be packaged for distribution.

If your project does not include a `[build-system]` definition in the `pyproject.toml`, uv will not build it during `uv sync` operations in the project, but will fall back to the legacy setuptools build system during `uv build`.

It is strongly recommended to configure a build system explicitly. For details on `pyproject.toml` configuration, see `03-project-config.md`.

Python projects are typically distributed as both source distributions (sdists) and binary distributions (wheels). The former is typically a `.tar.gz` or `.zip` file containing the project's source code along with some additional metadata, while the latter is a `.whl` file containing pre-built artifacts that can be installed directly.

**Important:** When using `uv build`, uv acts as a [build frontend](https://peps.python.org/pep-0517/#terminology-and-goals) and only determines the Python version to use and invokes the build backend. The details of the builds, such as the included files and the distribution filenames, are determined by the build backend, as defined in `[build-system]`. Information about build configuration can be found in the respective tool's documentation.

## Using `uv build`

`uv build` can be used to build both source distributions and binary distributions for your project. By default, `uv build` will build the project in the current directory, and place the built artifacts in a `dist/` subdirectory:

```console
$ uv build
$ ls dist/
example-0.1.0-py3-none-any.whl
example-0.1.0.tar.gz
```

You can build the project in a different directory by providing a path to `uv build`, e.g., `uv build path/to/project`.

Alternatively, `uv build <SRC>` will build the package in the specified directory, while `uv build --package <PACKAGE>` will build the specified package within the current workspace.

`uv build` will first build a source distribution, and then build a binary distribution (wheel) from that source distribution.

You can limit `uv build` to building a source distribution with `uv build --sdist`, a binary distribution with `uv build --wheel`, or build both distributions from source with `uv build --sdist --wheel`.

**Note:** By default, `uv build` respects `tool.uv.sources` when resolving build dependencies from the `build-system.requires` section of the `pyproject.toml`. When publishing a package, it is recommended to run `uv build --no-sources` to ensure that the package builds correctly when `tool.uv.sources` is disabled, as is the case when using other build tools, like `pypa/build`.

### Build Constraints

`uv build` accepts `--build-constraint`, which can be used to constrain the versions of any build requirements during the build process. When coupled with `--require-hashes`, uv will enforce that the requirement used to build the project match specific, known hashes, for reproducibility.

For example, given the following `constraints.txt`:

```text
setuptools==68.2.2 --hash=sha256:b454a35605876da60632df1a60f736524eb73cc47bbc9f3f1ef1b644de74fd2a
```

Running the following would build the project with the specified version of `setuptools`, and verify that the downloaded `setuptools` distribution matches the specified hash:

```console
$ uv build --build-constraint constraints.txt --require-hashes
```

### Preventing Publish to PyPI

If you have internal packages that you do not want to be published, you can mark them as private:

```toml
[project]
classifiers = ["Private :: Do Not Upload"]
```

This setting makes PyPI reject your uploaded package from publishing. It does not affect security or privacy settings on alternative registries.

It is also recommended to only generate per-project PyPI API tokens: without a PyPI token matching the project, it can't be accidentally published.

## The uv Build Backend

A build backend transforms a source tree (i.e., a directory) into a source distribution or a wheel.

uv supports all build backends (as specified by [PEP 517](https://peps.python.org/pep-0517/)), but also provides a native build backend (`uv_build`) that integrates tightly with uv to improve performance and user experience.

### Choosing a Build Backend

The uv build backend is a great choice for most Python projects. It has reasonable defaults, with the goal of requiring zero configuration for most users, but provides flexible configuration to accommodate most Python project structures. It integrates tightly with uv, to improve messaging and user experience. It validates project metadata and structures, preventing common mistakes. And, finally, it's very fast.

The uv build backend currently **only supports pure Python code**. An alternative backend is required to build a library with extension modules.

**Tip:** While the backend supports a number of options for configuring your project structure, when build scripts or a more flexible project layout are required, consider using the [hatchling](https://hatch.pypa.io/latest/config/build/#build-system) build backend instead.

### Configuring the uv Build Backend

To use uv as a build backend in an existing project, add `uv_build` to the `[build-system]` section in your `pyproject.toml`:

```toml
[build-system]
requires = ["uv_build>=0.10.2,<0.11.0"]
build-backend = "uv_build"
```

**Note:** The uv build backend follows the same versioning policy as uv. Including an upper bound on the `uv_build` version ensures that your package continues to build correctly as new versions are released.

To create a new project that uses the uv build backend, use `uv init`:

```console
$ uv init
```

When the project is built, e.g., with `uv build`, the uv build backend will be used to create the source distribution and wheel.

### Bundled Build Backend

The build backend is published as a separate package (`uv_build`) that is optimized for portability and small binary size. However, the `uv` executable also includes a copy of the build backend, which will be used during builds performed by uv, e.g., during `uv build`, if its version is compatible with the `uv_build` requirement. If it's not compatible, a compatible version of the `uv_build` package will be used. Other build frontends, such as `python -m build`, will always use the `uv_build` package, typically choosing the latest compatible version.

### Modules

Python packages are expected to contain one or more Python modules, which are directories containing an `__init__.py`. By default, a single root module is expected at `src/<package_name>/__init__.py`.

For example, the structure for a project named `foo` would be:

```text
pyproject.toml
src
└── foo
    └── __init__.py
```

uv normalizes the package name to determine the default module name: the package name is lowercased and dots and dashes are replaced with underscores, e.g., `Foo-Bar` would be converted to `foo_bar`.

The `src/` directory is the default directory for module discovery.

These defaults can be changed with the `module-name` and `module-root` settings. For example, to use a `FOO` module in the root directory, as in the project structure:

```text
pyproject.toml
FOO
└── __init__.py
```

The correct build configuration would be:

```toml
[tool.uv.build-backend]
module-name = "FOO"
module-root = ""
```

### Namespace Packages

Namespace packages are intended for use-cases where multiple packages write modules into a shared namespace.

Namespace package modules are identified by a `.` in the `module-name`. For example, to package the module `bar` in the shared namespace `foo`, the project structure would be:

```text
pyproject.toml
src
└── foo
    └── bar
        └── __init__.py
```

And the `module-name` configuration would be:

```toml
[tool.uv.build-backend]
module-name = "foo.bar"
```

**Important:** The `__init__.py` file is not included in `foo`, since it's the shared namespace module.

It's also possible to have a complex namespace package with more than one root module, e.g., with the project structure:

```text
pyproject.toml
src
├── foo
│   └── __init__.py
└── bar
    └── __init__.py
```

While it is not recommended (use a workspace with multiple packages instead -- see `12-workspaces.md`), it is supported by setting `module-name` to a list of names:

```toml
[tool.uv.build-backend]
module-name = ["foo", "bar"]
```

For packages with many modules or complex namespaces, the `namespace = true` option can be used to avoid explicitly declaring each module name, e.g.:

```toml
[tool.uv.build-backend]
namespace = true
```

**Warning:** Using `namespace = true` disables safety checks. Using an explicit list of module names is strongly recommended outside of legacy projects.

The `namespace` option can also be used with `module-name` to explicitly declare the root, e.g., for the project structure:

```text
pyproject.toml
src
└── foo
    ├── bar
    │   └── __init__.py
    └── baz
        └── __init__.py
```

The recommended configuration would be:

```toml
[tool.uv.build-backend]
module-name = "foo"
namespace = true
```

### Stub Packages

The build backend also supports building type stub packages, which are identified by the `-stubs` suffix on the package or module name, e.g., `foo-stubs`. The module name for type stub packages must end in `-stubs`, so uv will not normalize the `-` to an underscore. Additionally, uv will search for a `__init__.pyi` file. For example, the project structure would be:

```text
pyproject.toml
src
└── foo-stubs
    └── __init__.pyi
```

Type stub modules are also supported for namespace packages.

### File Inclusion and Exclusion

The build backend is responsible for determining which files in a source tree should be packaged into the distributions.

To determine which files to include in a source distribution, uv first adds the included files and directories, then removes the excluded files and directories. This means that exclusions always take precedence over inclusions.

By default, uv excludes `__pycache__`, `*.pyc`, and `*.pyo`.

When building a source distribution, the following files and directories are included:

- The `pyproject.toml`
- The module under `tool.uv.build-backend.module-root`
- The files referenced by `project.license-files` and `project.readme`
- All directories under `tool.uv.build-backend.data`
- All files matching patterns from `tool.uv.build-backend.source-include`

From these, items matching `tool.uv.build-backend.source-exclude` and the default excludes are removed.

When building a wheel, the following files and directories are included:

- The module under `tool.uv.build-backend.module-root`
- The files referenced by `project.license-files`, which are copied into the `.dist-info` directory
- The `project.readme`, which is copied into the project metadata
- All directories under `tool.uv.build-backend.data`, which are copied into the `.data` directory

From these, `tool.uv.build-backend.source-exclude`, `tool.uv.build-backend.wheel-exclude` and the default excludes are removed. The source dist excludes are applied to avoid source tree to wheel builds including more files than source tree to source distribution to wheel build.

There are no specific wheel includes. There must only be one top level module, and all data files must either be under the module root or in the appropriate data directory. Most packages store small data in the module root alongside the source code.

**Tip:** When using the uv build backend through a frontend that is not uv, such as pip or `python -m build`, debug logging can be enabled through environment variables with `RUST_LOG=uv=debug` or `RUST_LOG=uv=verbose`. When used through uv, the uv build backend shares the verbosity level of uv.

#### Include and Exclude Syntax

Includes are anchored, which means that `pyproject.toml` includes only `<root>/pyproject.toml` and not `<root>/bar/pyproject.toml`. To recursively include all files under a directory, use a `/**` suffix, e.g. `src/**`. Recursive inclusions are also anchored, e.g., `assets/**/sample.csv` includes all `sample.csv` files in `<root>/assets` or any of its children.

**Note:** For performance and reproducibility, avoid patterns without an anchor such as `**/sample.csv`.

Excludes are not anchored, which means that `__pycache__` excludes all directories named `__pycache__` regardless of its parent directory. All children of an exclusion are excluded as well. To anchor a directory, use a `/` prefix, e.g., `/dist` will exclude only `<root>/dist`.

All fields accepting patterns use the reduced portable glob syntax from [PEP 639](https://peps.python.org/pep-0639/#add-license-FILES-key), with the addition that characters can be escaped with a backslash.

## Updating Your Version

The `uv version` command provides conveniences for updating the version of your package before you publish it.

To update to an exact version, provide it as a positional argument:

```console
$ uv version 1.0.0
hello-world 0.7.0 => 1.0.0
```

To preview the change without updating the `pyproject.toml`, use the `--dry-run` flag:

```console
$ uv version 2.0.0 --dry-run
hello-world 1.0.0 => 2.0.0
$ uv version
hello-world 1.0.0
```

To increase the version of your package semantically, use the `--bump` option:

```console
$ uv version --bump minor
hello-world 1.2.3 => 1.3.0
```

The `--bump` option supports the following common version components: `major`, `minor`, `patch`, `stable`, `alpha`, `beta`, `rc`, `post`, and `dev`. When provided more than once, the components will be applied in order, from largest (`major`) to smallest (`dev`).

You can optionally provide a numeric value with `--bump <component>=<value>` to set the resulting component explicitly:

```console
$ uv version --bump patch --bump dev=66463664
hello-world 0.0.1 => 0.0.2.dev66463664
```

To move from a stable to pre-release version, bump one of the major, minor, or patch components in addition to the pre-release component:

```console
$ uv version --bump patch --bump beta
hello-world 1.3.0 => 1.3.1b1
$ uv version --bump major --bump alpha
hello-world 1.3.0 => 2.0.0a1
```

When moving from a pre-release to a new pre-release version, just bump the relevant pre-release component:

```console
$ uv version --bump beta
hello-world 1.3.0b1 => 1.3.0b2
```

When moving from a pre-release to a stable version, the `stable` option can be used to clear the pre-release component:

```console
$ uv version --bump stable
hello-world 1.3.1b2 => 1.3.1
```

**Note:** By default, when `uv version` modifies the project it will perform a lock and sync. To prevent locking and syncing, use `--frozen`, or, to just prevent syncing, use `--no-sync`.

## Publishing Your Package

Publish your package with `uv publish`:

```console
$ uv publish
```

Set a PyPI token with `--token` or `UV_PUBLISH_TOKEN`, or set a username with `--username` or `UV_PUBLISH_USERNAME` and password with `--password` or `UV_PUBLISH_PASSWORD`. For publishing to PyPI from GitHub Actions or another Trusted Publisher, you don't need to set any credentials. Instead, add a trusted publisher to the PyPI project. For CI/CD setup details, see `14-ci-cd.md`.

**Note:** PyPI does not support publishing with username and password anymore, instead you need to generate a token. Using a token is equivalent to setting `--username __token__` and using the token as password.

If you're using a custom index through `[[tool.uv.index]]`, add `publish-url` and use `uv publish --index <name>`. For details on configuring indexes, see `10-configuration.md`. For example:

```toml
[[tool.uv.index]]
name = "testpypi"
url = "https://test.pypi.org/simple/"
publish-url = "https://test.pypi.org/legacy/"
explicit = true
```

**Note:** When using `uv publish --index <name>`, the `pyproject.toml` must be present, i.e., you need to have a checkout step in a publish CI job.

Even though `uv publish` retries failed uploads, it can happen that publishing fails in the middle, with some files uploaded and some files still missing. With PyPI, you can retry the exact same command, existing identical files will be ignored. With other registries, use `--check-url <index url>` with the index URL (not the publishing URL) the packages belong to. When using `--index`, the index URL is used as check URL. uv will skip uploading files that are identical to files in the registry, and it will also handle raced parallel uploads. Note that existing files need to match exactly with those previously uploaded to the registry, this avoids accidentally publishing source distribution and wheels with different contents for the same version.

### Uploading Attestations

**Note:** Some third-party package indexes may not support attestations, and may reject uploads that include them (rather than silently ignoring them). If you encounter issues when uploading, you can use `--no-attestations` or `UV_PUBLISH_NO_ATTESTATIONS` to disable uv's default behavior.

**Tip:** `uv publish` does not currently generate attestations; attestations must be created separately before publishing.

`uv publish` supports uploading [attestations](https://peps.python.org/pep-0740/) to registries that support them, like PyPI.

uv will automatically discover and match attestations. For example, given the following `dist/` directory, `uv publish` will upload the attestations along with their corresponding distributions:

```console
$ ls dist/
hello_world-1.0.0-py3-none-any.whl
hello_world-1.0.0-py3-none-any.whl.publish.attestation
hello_world-1.0.0.tar.gz
hello_world-1.0.0.tar.gz.publish.attestation
```

## Verifying Your Package

Test that the package can be installed and imported with `uv run`:

```console
$ uv run --with <PACKAGE> --no-project -- python -c "import <PACKAGE>"
```

The `--no-project` flag is used to avoid installing the package from your local project directory.

**Tip:** If you have recently installed the package, you may need to include the `--refresh-package <PACKAGE>` option to avoid using a cached version of the package.

## See Also

- `03-project-config.md` - pyproject.toml configuration and build systems
- `10-configuration.md` - Package indexes and publishing configuration
- `11-authentication.md` - Authenticating with registries for publishing
- `12-workspaces.md` - Monorepo workspaces with multiple packages
- `14-ci-cd.md` - CI/CD integration for automated publishing
