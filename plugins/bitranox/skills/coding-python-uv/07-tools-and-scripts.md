# Tools and Scripts

## Tools

Tools are Python packages that provide command-line interfaces. uv has specialized support for easily invoking and installing tools. For configuring tool storage directories, see `10-configuration.md`.

### The `uv tool` Interface

uv includes a dedicated interface for interacting with tools. Tools can be invoked without installation using `uv tool run`, in which case their dependencies are installed in a temporary virtual environment isolated from the current project.

Because it is very common to run tools without installing them, a `uvx` alias is provided for `uv tool run` -- the two commands are exactly equivalent. For brevity, the documentation will mostly refer to `uvx` instead of `uv tool run`.

Tools can also be installed with `uv tool install`, in which case their executables are available on the `PATH` -- an isolated virtual environment is still used, but it is not removed when the command completes.

### Running Tools

The `uvx` command invokes a tool without installing it.

For example, to run `ruff`:

```console
$ uvx ruff
```

Arguments can be provided after the tool name:

```console
$ uvx pycowsay hello from uv

  -------------
< hello from uv >
  -------------
   \   ^__^
    \  (oo)\_______
       (__)\       )\/\
           ||----w |
           ||     ||

```

Tools are installed into temporary, isolated environments when using `uvx`.

**Note:** If you are running a tool in a _project_ and the tool requires that your project is installed, e.g., when using `pytest` or `mypy`, you'll want to use `uv run` instead of `uvx`. Otherwise, the tool will be run in a virtual environment that is isolated from your project. If your project has a flat structure, e.g., instead of using a `src` directory for modules, the project itself does not need to be installed and `uvx` is fine. In this case, using `uv run` is only beneficial if you want to pin the version of the tool in the project's dependencies.

### Execution vs Installation

In most cases, executing a tool with `uvx` is more appropriate than installing the tool. Installing the tool is useful if you need the tool to be available to other programs on your system, e.g., if some script you do not control requires the tool, or if you are in a Docker image and want to make the tool available to users.

### Commands with Different Package Names

When `uvx ruff` is invoked, uv installs the `ruff` package which provides the `ruff` command. However, sometimes the package and command names differ.

The `--from` option can be used to invoke a command from a specific package, e.g., `http` which is provided by `httpie`:

```console
$ uvx --from httpie http
```

### Requesting Specific Versions

To run a tool at a specific version, use `command@<version>`:

```console
$ uvx ruff@0.3.0 check
```

To run a tool at the latest version, use `command@latest`:

```console
$ uvx ruff@latest check
```

The `--from` option can also be used to specify package versions:

```console
$ uvx --from 'ruff==0.3.0' ruff check
```

Or, to constrain to a range of versions:

```console
$ uvx --from 'ruff>0.2.0,<0.3.0' ruff check
```

Note the `@` syntax cannot be used for anything other than an exact version.

### Requesting Extras

The `--from` option can be used to run a tool with extras:

```console
$ uvx --from 'mypy[faster-cache,reports]' mypy --xml-report mypy_report
```

This can also be combined with version selection:

```console
$ uvx --from 'mypy[faster-cache,reports]==1.13.0' mypy --xml-report mypy_report
```

### Requesting Different Sources

The `--from` option can also be used to install from alternative sources.

For example, to pull from git:

```console
$ uvx --from git+https://github.com/httpie/cli httpie
```

You can also pull the latest commit from a specific named branch:

```console
$ uvx --from git+https://github.com/httpie/cli@master httpie
```

Or pull a specific tag:

```console
$ uvx --from git+https://github.com/httpie/cli@3.2.4 httpie
```

Or even a specific commit:

```console
$ uvx --from git+https://github.com/httpie/cli@2843b87 httpie
```

Or with [Git LFS](https://git-lfs.com) support:

```console
$ uvx --lfs --from git+https://github.com/astral-sh/lfs-cowsay lfs-cowsay
```

### Including Additional Dependencies

Additional packages can be included during tool execution:

```console
$ uvx --with mkdocs-material mkdocs --help
```

And, during tool installation:

```console
$ uv tool install --with mkdocs-material mkdocs
```

The `--with` option can be provided multiple times to include additional packages.

The `--with` option supports package specifications, so a specific version can be requested:

```console
$ uvx --with <extra-package>==<version> <tool-package>
```

The `-w` shorthand can be used in place of the `--with` option:

```console
$ uvx -w <extra-package> <tool-package>
```

If the requested version conflicts with the requirements of the tool package, package resolution will fail and the command will error.

### Installing Tools

If a tool is used often, it is useful to install it to a persistent environment and add it to the `PATH` instead of invoking `uvx` repeatedly.

To install `ruff`:

```console
$ uv tool install ruff
```

When a tool is installed, its executables are placed in a `bin` directory in the `PATH` which allows the tool to be run without uv. If it's not on the `PATH`, a warning will be displayed and `uv tool update-shell` can be used to add it to the `PATH`.

After installing `ruff`, it should be available:

```console
$ ruff --version
```

Unlike `uv pip install`, installing a tool does not make its modules available in the current environment. For example, the following command will fail:

```console
$ python -c "import ruff"
```

This isolation is important for reducing interactions and conflicts between dependencies of tools, scripts, and projects.

Unlike `uvx`, `uv tool install` operates on a _package_ and will install all executables provided by the tool.

For example, the following will install the `http`, `https`, and `httpie` executables:

```console
$ uv tool install httpie
```

Additionally, package versions can be included without `--from`:

```console
$ uv tool install 'httpie>0.1.0'
```

And, similarly, for package sources:

```console
$ uv tool install git+https://github.com/httpie/cli
```

Or package sources with [Git LFS](https://git-lfs.com):

```console
$ uv tool install --lfs git+https://github.com/astral-sh/lfs-cowsay
```

### Installing Executables from Additional Packages

When installing a tool, you may want to include executables from additional packages in the same tool environment. This is useful when you have related tools that work together or when you want to install multiple executables that share dependencies.

The `--with-executables-from` option allows you to specify additional packages whose executables should be installed alongside the main tool:

```console
$ uv tool install --with-executables-from <package1>,<package2> <tool-package>
```

For example, to install Ansible along with executables from `ansible-core` and `ansible-lint`:

```console
$ uv tool install --with-executables-from ansible-core,ansible-lint ansible
```

This will install all executables from the `ansible`, `ansible-core`, and `ansible-lint` packages into the same tool environment, making them all available on the `PATH`.

The `--with-executables-from` option can be combined with other installation options:

```console
$ uv tool install --with-executables-from ansible-core --with mkdocs-material ansible
```

Note that `--with-executables-from` differs from `--with` in that:

- `--with` includes additional packages as dependencies but does not install their executables
- `--with-executables-from` includes both the packages as dependencies and installs their executables

### Tool Versions

Unless a specific version is requested, `uv tool install` will install the latest available of the requested tool. `uvx` will use the latest available version of the requested tool _on the first invocation_. After that, `uvx` will use the cached version of the tool unless a different version is requested, the cache is pruned, or the cache is refreshed.

For example, to run a specific version of Ruff:

```console
$ uvx ruff@0.6.0 --version
ruff 0.6.0
```

A subsequent invocation of `uvx` will use the latest, not the cached, version.

```console
$ uvx ruff --version
ruff 0.6.2
```

But, if a new version of Ruff was released, it would not be used unless the cache was refreshed.

To request the latest version of Ruff and refresh the cache, use the `@latest` suffix:

```console
$ uvx ruff@latest --version
0.6.2
```

Once a tool is installed with `uv tool install`, `uvx` will use the installed version by default.

For example, after installing an older version of Ruff:

```console
$ uv tool install ruff==0.5.0
```

The version of `ruff` and `uvx ruff` is the same:

```console
$ ruff --version
ruff 0.5.0
$ uvx ruff --version
ruff 0.5.0
```

However, you can ignore the installed version by requesting the latest version explicitly, e.g.:

```console
$ uvx ruff@latest --version
0.6.2
```

Or, by using the `--isolated` flag, which will avoid refreshing the cache but ignore the installed version:

```console
$ uvx --isolated ruff --version
0.6.2
```

`uv tool install` will also respect the `{package}@{version}` and `{package}@latest` specifiers, as in:

```console
$ uv tool install ruff@latest
$ uv tool install ruff@0.6.0
```

### Upgrading Tools

Tool environments may be upgraded via `uv tool upgrade`, or re-created entirely via subsequent `uv tool install` operations.

To upgrade all packages in a tool environment:

```console
$ uv tool upgrade black
```

To upgrade a single package in a tool environment:

```console
$ uv tool upgrade black --upgrade-package click
```

Tool upgrades will respect the version constraints provided when installing the tool. For example, `uv tool install black >=23,<24` followed by `uv tool upgrade black` will upgrade Black to the latest version in the range `>=23,<24`.

To instead replace the version constraints, reinstall the tool with `uv tool install`:

```console
$ uv tool install black>=24
```

Similarly, tool upgrades will retain the settings provided when installing the tool. For example, `uv tool install black --prerelease allow` followed by `uv tool upgrade black` will retain the `--prerelease allow` setting.

**Note:** Tool upgrades will reinstall the tool executables, even if they have not changed.

To upgrade all tools:

```console
$ uv tool upgrade --all
```

To reinstall packages during upgrade, use the `--reinstall` and `--reinstall-package` options.

To reinstall all packages in a tool environment:

```console
$ uv tool upgrade black --reinstall
```

To reinstall a single package in a tool environment:

```console
$ uv tool upgrade black --reinstall-package click
```

### Tool Environments

When running a tool with `uvx`, a virtual environment is stored in the uv cache directory and is treated as disposable, i.e., if you run `uv cache clean` the environment will be deleted. The environment is only cached to reduce the overhead of repeated invocations. If the environment is removed, a new one will be created automatically.

When installing a tool with `uv tool install`, a virtual environment is created in the uv tools directory. The environment will not be removed unless the tool is uninstalled. If the environment is manually deleted, the tool will fail to run.

**Important:** Tool environments are _not_ intended to be mutated directly. It is strongly recommended never to mutate a tool environment manually, e.g., with a `pip` operation.

### Python Versions

Each tool environment is linked to a specific Python version. This uses the same Python version discovery logic as other virtual environments created by uv, but will ignore non-global Python version requests like `.python-version` files and the `requires-python` value from a `pyproject.toml`.

The `--python` option can be used to request a specific version.

For example, to request a specific Python version when running a tool:

```console
$ uvx --python 3.10 ruff
```

Or, when installing a tool:

```console
$ uv tool install --python 3.10 ruff
```

Or, when upgrading a tool:

```console
$ uv tool upgrade --python 3.10 ruff
```

If the Python version used by a tool is _uninstalled_, the tool environment will be broken and the tool may be unusable.

### Tool Executables

Tool executables include all console entry points, script entry points, and binary scripts provided by a Python package. Tool executables are symlinked into the executable directory on Unix and copied on Windows.

**Note:** Executables provided by dependencies of tool packages are not installed.

The executable directory must be in the `PATH` variable for tool executables to be available from the shell. If it is not in the `PATH`, a warning will be displayed. The `uv tool update-shell` command can be used to add the executable directory to the `PATH` in common shell configuration files.

#### Overwriting Executables

Installation of tools will not overwrite executables in the executable directory that were not previously installed by uv. For example, if `pipx` has been used to install a tool, `uv tool install` will fail. The `--force` flag can be used to override this behavior.

### Legacy Windows Scripts

Tools also support running [legacy setuptools scripts](https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/#scripts). These scripts are available via `$(uv tool dir)\<tool-name>\Scripts` when installed.

Currently only legacy scripts with the `.ps1`, `.cmd`, and `.bat` extensions are supported.

For example, below is an example running a Command Prompt script:

```console
$ uv tool run --from nuitka==2.6.7 nuitka.cmd --version
```

In addition, you don't need to specify the extension. `uvx` will automatically look for files ending in `.ps1`, `.cmd`, and `.bat` in that order of execution on your behalf:

```console
$ uv tool run --from nuitka==2.6.7 nuitka --version
```

### Relationship to `uv run`

The invocation `uv tool run <name>` (or `uvx <name>`) is nearly equivalent to:

```console
$ uv run --no-project --with <name> -- <name>
```

However, there are a couple notable differences when using uv's tool interface:

- The `--with` option is not needed -- the required package is inferred from the command name.
- The temporary environment is cached in a dedicated location.
- The `--no-project` flag is not needed -- tools are always run isolated from the project.
- If a tool is already installed, `uv tool run` will use the installed version but `uv run` will not.

If the tool should not be isolated from the project, e.g., when running `pytest` or `mypy`, then `uv run` should be used instead of `uv tool run`. For details on running commands within projects, see `02-projects.md`.

## Scripts

A Python script is a file intended for standalone execution, e.g., with `python <script>.py`. Using uv to execute scripts ensures that script dependencies are managed without manually managing environments.

**Note:** If you are not familiar with Python environments: every Python installation has an environment that packages can be installed in. Typically, creating [virtual environments](https://docs.python.org/3/library/venv.html) is recommended to isolate packages required by each script. uv automatically manages virtual environments for you and prefers a declarative approach to dependencies.

### Running a Script Without Dependencies

If your script has no dependencies, you can execute it with `uv run`:

```python
# example.py
print("Hello world")
```

```console
$ uv run example.py
Hello world
```

Similarly, if your script depends on a module in the standard library, there's nothing more to do:

```python
# example.py
import os

print(os.path.expanduser("~"))
```

```console
$ uv run example.py
/Users/astral
```

Arguments may be provided to the script:

```python
# example.py
import sys

print(" ".join(sys.argv[1:]))
```

```console
$ uv run example.py test
test

$ uv run example.py hello world!
hello world!
```

Additionally, your script can be read directly from stdin:

```console
$ echo 'print("hello world!")' | uv run -
```

Or, if your shell supports [here-documents](https://en.wikipedia.org/wiki/Here_document):

```bash
uv run - <<EOF
print("hello world!")
EOF
```

Note that if you use `uv run` in a _project_, i.e., a directory with a `pyproject.toml`, it will install the current project before running the script. If your script does not depend on the project, use the `--no-project` flag to skip this:

```console
$ # Note: the `--no-project` flag must be provided _before_ the script name.
$ uv run --no-project example.py
```

### Running a Script with Dependencies

When your script requires other packages, they must be installed into the environment that the script runs in. uv prefers to create these environments on-demand instead of using a long-lived virtual environment with manually managed dependencies. This requires explicit declaration of dependencies that are required for the script. Generally, it's recommended to use a project or inline metadata to declare dependencies, but uv supports requesting dependencies per invocation as well.

For example, the following script requires `rich`.

```python
# example.py
import time
from rich.progress import track

for i in track(range(20), description="For example:"):
    time.sleep(0.05)
```

If executed without specifying a dependency, this script will fail:

```console
$ uv run --no-project example.py
Traceback (most recent call last):
  File "/Users/astral/example.py", line 2, in <module>
    from rich.progress import track
ModuleNotFoundError: No module named 'rich'
```

Request the dependency using the `--with` option:

```console
$ uv run --with rich example.py
For example: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01
```

Constraints can be added to the requested dependency if specific versions are needed:

```console
$ uv run --with 'rich>12,<13' example.py
```

Multiple dependencies can be requested by repeating with `--with` option.

Note that if `uv run` is used in a _project_, these dependencies will be included _in addition_ to the project's dependencies. To opt-out of this behavior, use the `--no-project` flag.

### Creating a Python Script

Python recently added a standard format for [inline script metadata](https://packaging.python.org/en/latest/specifications/inline-script-metadata/#inline-script-metadata) (PEP 723). It allows for selecting Python versions and defining dependencies. Use `uv init --script` to initialize scripts with the inline metadata:

```console
$ uv init --script example.py --python 3.12
```

### Declaring Script Dependencies

The inline metadata format allows the dependencies for a script to be declared in the script itself.

uv supports adding and updating inline script metadata for you. Use `uv add --script` to declare the dependencies for the script:

```console
$ uv add --script example.py 'requests<3' 'rich'
```

This will add a `script` section at the top of the script declaring the dependencies using TOML:

```python
# example.py
# /// script
# dependencies = [
#   "requests<3",
#   "rich",
# ]
# ///

import requests
from rich.pretty import pprint

resp = requests.get("https://peps.python.org/api/peps.json")
data = resp.json()
pprint([(k, v["title"]) for k, v in data.items()][:10])
```

uv will automatically create an environment with the dependencies necessary to run the script, e.g.:

```console
$ uv run example.py
[
│   ('1', 'PEP Purpose and Guidelines'),
│   ('2', 'Procedure for Adding New Modules'),
│   ('3', 'Guidelines for Handling Bug Reports'),
│   ('4', 'Deprecation of Standard Modules'),
│   ('5', 'Guidelines for Language Evolution'),
│   ('6', 'Bug Fix Releases'),
│   ('7', 'Style Guide for C Code'),
│   ('8', 'Style Guide for Python Code'),
│   ('9', 'Sample Plaintext PEP Template'),
│   ('10', 'Voting Guidelines')
]
```

**Important:** When using inline script metadata, even if `uv run` is used in a _project_, the project's dependencies will be ignored. The `--no-project` flag is not required.

uv also respects Python version requirements:

```python
# example.py
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

# Use some syntax added in Python 3.12
type Point = tuple[float, float]
print(Point)
```

**Note:** The `dependencies` field must be provided even if empty.

`uv run` will search for and use the required Python version. The Python version will download if it is not installed.

### Using a Shebang to Create an Executable File

A shebang can be added to make a script executable without using `uv run` -- this makes it easy to run scripts that are on your `PATH` or in the current folder.

For example, create a file called `greet` with the following contents:

```python
#!/usr/bin/env -S uv run --script

print("Hello, world!")
```

Ensure that your script is executable, e.g., with `chmod +x greet`, then run the script:

```console
$ ./greet
Hello, world!
```

Declaration of dependencies is also supported in this context, for example:

```python
#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///

import httpx

print(httpx.get("https://example.com"))
```

### Using Alternative Package Indexes

If you wish to use an alternative package index to resolve dependencies, you can provide the index with the `--index` option:

```console
$ uv add --index "https://example.com/simple" --script example.py 'requests<3' 'rich'
```

This will include the package data in the inline metadata:

```python
# [[tool.uv.index]]
# url = "https://example.com/simple"
```

### Locking Dependencies

uv supports locking dependencies for PEP 723 scripts using the `uv.lock` file format. Unlike with projects, scripts must be explicitly locked using `uv lock`:

```console
$ uv lock --script example.py
```

Running `uv lock --script` will create a `.lock` file adjacent to the script (e.g., `example.py.lock`).

Once locked, subsequent operations like `uv run --script`, `uv add --script`, `uv export --script`, and `uv tree --script` will reuse the locked dependencies, updating the lockfile if necessary.

If no such lockfile is present, commands like `uv export --script` will still function as expected, but will not create a lockfile.

### Improving Reproducibility

In addition to locking dependencies, uv supports an `exclude-newer` field in the `tool.uv` section of inline script metadata to limit uv to only considering distributions released before a specific date. This is useful for improving the reproducibility of your script when run at a later point in time.

The date should be specified as an [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339.html) timestamp (e.g., `2006-12-02T02:07:43Z`).

```python
# example.py
# /// script
# dependencies = [
#   "requests",
# ]
# [tool.uv]
# exclude-newer = "2023-10-16T00:00:00Z"
# ///

import requests

print(requests.__version__)
```

### Using Different Python Versions

uv allows arbitrary Python versions to be requested on each script invocation. For details on how uv discovers and manages Python versions, see `06-python-versions.md`. For example:

```python
# example.py
import sys

print(".".join(map(str, sys.version_info[:3])))
```

```console
$ # Use the default Python version, may differ on your machine
$ uv run example.py
3.12.6
```

```console
$ # Use a specific Python version
$ uv run --python 3.10 example.py
3.10.15
```

### Using GUI Scripts

On Windows, `uv` will run your script ending with `.pyw` extension using `pythonw`:

```python
# example.pyw
from tkinter import Tk, ttk

root = Tk()
root.title("uv")
frm = ttk.Frame(root, padding=10)
frm.grid()
ttk.Label(frm, text="Hello World").grid(column=0, row=0)
root.mainloop()
```

```console
PS> uv run example.pyw
```

Similarly, it works with dependencies as well:

```python
# example_pyqt.pyw
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QGridLayout

app = QApplication(sys.argv)
widget = QWidget()
grid = QGridLayout()

text_label = QLabel()
text_label.setText("Hello World!")
grid.addWidget(text_label)

widget.setLayout(grid)
widget.setGeometry(100, 100, 200, 50)
widget.setWindowTitle("uv")
widget.show()
sys.exit(app.exec_())
```

```console
PS> uv run --with PyQt5 example_pyqt.pyw
```

## See Also

- `02-projects.md` - Project creation, running commands, syncing environments
- `04-dependencies.md` - Dependency management and lockfiles
- `06-python-versions.md` - Python version management and discovery
- `10-configuration.md` - Configuration files, tool storage directories
