# Getting Started with uv

uv provides essential features for Python development -- from installing Python and hacking on simple scripts to working on large projects that support multiple Python versions and platforms.

uv's interface can be broken down into sections, which are usable independently or together.

## Feature Overview

### Python versions

Installing and managing Python itself. For details, see `06-python-versions.md`.

- `uv python install`: Install Python versions.
- `uv python list`: View available Python versions.
- `uv python find`: Find an installed Python version.
- `uv python pin`: Pin the current project to use a specific Python version.
- `uv python uninstall`: Uninstall a Python version.

### Scripts

Executing standalone Python scripts, e.g., `example.py`.

- `uv run`: Run a script.
- `uv add --script`: Add a dependency to a script.
- `uv remove --script`: Remove a dependency from a script.

### Projects

Creating and working on Python projects, i.e., with a `pyproject.toml`. For details, see `02-projects.md` and `03-project-config.md`.

- `uv init`: Create a new Python project.
- `uv add`: Add a dependency to the project.
- `uv remove`: Remove a dependency from the project.
- `uv sync`: Sync the project's dependencies with the environment.
- `uv lock`: Create a lockfile for the project's dependencies.
- `uv run`: Run a command in the project environment.
- `uv tree`: View the dependency tree for the project.
- `uv build`: Build the project into distribution archives.
- `uv publish`: Publish the project to a package index.

### Tools

Running and installing tools published to Python package indexes, e.g., `ruff` or `black`. For details, see `07-tools-and-scripts.md`.

- `uvx` / `uv tool run`: Run a tool in a temporary environment.
- `uv tool install`: Install a tool user-wide.
- `uv tool uninstall`: Uninstall a tool.
- `uv tool list`: List installed tools.
- `uv tool update-shell`: Update the shell to include tool executables.

### The pip interface

Manually managing environments and packages -- intended to be used in legacy workflows or cases where the high-level commands do not provide enough control. For details, see `09-pip-interface.md`.

Creating virtual environments (replacing `venv` and `virtualenv`):

- `uv venv`: Create a new virtual environment.

Managing packages in an environment (replacing `pip` and `pipdeptree`):

- `uv pip install`: Install packages into the current environment.
- `uv pip show`: Show details about an installed package.
- `uv pip freeze`: List installed packages and their versions.
- `uv pip check`: Check that the current environment has compatible packages.
- `uv pip list`: List installed packages.
- `uv pip uninstall`: Uninstall packages.
- `uv pip tree`: View the dependency tree for the environment.

Locking packages in an environment (replacing `pip-tools`):

- `uv pip compile`: Compile requirements into a lockfile.
- `uv pip sync`: Sync an environment with a lockfile.

**Important:** These commands do not exactly implement the interfaces and behavior of the tools they are based on. The further you stray from common workflows, the more likely you are to encounter differences.

### Utility

Managing and inspecting uv's state, such as the cache, storage directories, or performing a self-update:

- `uv cache clean`: Remove cache entries.
- `uv cache prune`: Remove outdated cache entries.
- `uv cache dir`: Show the uv cache directory path.
- `uv tool dir`: Show the uv tool directory path.
- `uv python dir`: Show the uv installed Python versions path.
- `uv self update`: Update uv to the latest version.

## Installation

Install uv with the standalone installers or your package manager of choice.

### Standalone installer

uv provides a standalone installer to download and install uv.

#### macOS and Linux

Use `curl` to download the script and execute it with `sh`:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

If your system doesn't have `curl`, you can use `wget`:

```console
$ wget -qO- https://astral.sh/uv/install.sh | sh
```

Request a specific version by including it in the URL:

```console
$ curl -LsSf https://astral.sh/uv/0.10.2/install.sh | sh
```

#### Windows

Use `irm` to download the script and execute it with `iex`:

```pwsh-session
PS> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Changing the execution policy allows running a script from the internet.

Request a specific version by including it in the URL:

```pwsh-session
PS> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/0.10.2/install.ps1 | iex"
```

**Tip:** The installation script may be inspected before use:

On macOS and Linux:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | less
```

On Windows:

```pwsh-session
PS> powershell -c "irm https://astral.sh/uv/install.ps1 | more"
```

Alternatively, the installer or binaries can be downloaded directly from GitHub Releases.

### Installer Configuration

#### Changing the installation path

By default, uv is installed in the user executable directory. To change the installation path, use `UV_INSTALL_DIR`:

On macOS and Linux:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/custom/path" sh
```

On Windows:

```pwsh-session
PS> powershell -ExecutionPolicy ByPass -c {$env:UV_INSTALL_DIR = "C:\Custom\Path";irm https://astral.sh/uv/install.ps1 | iex}
```

**Note:** Changing the installation path only affects where the uv binary is installed. uv will still store its data (cache, Python installations, tools, etc.) in the default locations.

#### Disabling shell modifications

The installer may also update your shell profiles to ensure the uv binary is on your `PATH`. To disable this behavior, use `UV_NO_MODIFY_PATH`. For example:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
```

If installed with `UV_NO_MODIFY_PATH`, subsequent operations, like `uv self update`, will not modify your shell profiles.

#### Unmanaged installations

In ephemeral environments like CI, use `UV_UNMANAGED_INSTALL` to install uv to a specific path while preventing the installer from modifying shell profiles or environment variables:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="/custom/path" sh
```

The use of `UV_UNMANAGED_INSTALL` will also disable self-updates (via `uv self update`).

#### Passing options to the installation script

Using environment variables is recommended because they are consistent across platforms. However, options can be passed directly to the installation script. For example, to see the available options:

```console
$ curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --help
```

### PyPI

For convenience, uv is published to PyPI.

If installing from PyPI, we recommend installing uv into an isolated environment, e.g., with `pipx`:

```console
$ pipx install uv
```

However, `pip` can also be used:

```console
$ pip install uv
```

**Note:** uv ships with prebuilt distributions (wheels) for many platforms; if a wheel is not available for a given platform, uv will be built from source, which requires a Rust toolchain.

### Homebrew

uv is available in the core Homebrew packages.

```console
$ brew install uv
```

### MacPorts

uv is available via MacPorts.

```console
$ sudo port install uv
```

### WinGet

uv is available via WinGet.

```console
$ winget install --id=astral-sh.uv  -e
```

### Scoop

uv is available via Scoop.

```console
$ scoop install main/uv
```

### Docker

uv provides a Docker image at `ghcr.io/astral-sh/uv`. For Docker usage details, see `13-docker.md`.

### GitHub Releases

uv release artifacts can be downloaded directly from GitHub Releases. Each release page includes binaries for all supported platforms as well as instructions for using the standalone installer via `github.com` instead of `astral.sh`.

### Cargo

uv is available via crates.io.

```console
$ cargo install --locked uv
```

**Note:** This method builds uv from source, which requires a compatible Rust toolchain.

## Upgrading uv

When uv is installed via the standalone installer, it can update itself on-demand:

```console
$ uv self update
```

**Tip:** Updating uv will re-run the installer and can modify your shell profiles. To disable this behavior, set `UV_NO_MODIFY_PATH=1`.

When another installation method is used, self-updates are disabled. Use the package manager's upgrade method instead. For example, with `pip`:

```console
$ pip install --upgrade uv
```

## Shell Autocompletion

**Tip:** You can run `echo $SHELL` to help you determine your shell.

To enable shell autocompletion for uv commands, run one of the following:

#### Bash

```bash
echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
```

#### Zsh

```bash
echo 'eval "$(uv generate-shell-completion zsh)"' >> ~/.zshrc
```

#### fish

```bash
echo 'uv generate-shell-completion fish | source' > ~/.config/fish/completions/uv.fish
```

#### Elvish

```bash
echo 'eval (uv generate-shell-completion elvish | slurp)' >> ~/.elvish/rc.elv
```

#### PowerShell / pwsh

```powershell
if (!(Test-Path -Path $PROFILE)) {
  New-Item -ItemType File -Path $PROFILE -Force
}
Add-Content -Path $PROFILE -Value '(& uv generate-shell-completion powershell) | Out-String | Invoke-Expression'
```

To enable shell autocompletion for uvx, run one of the following:

#### Bash

```bash
echo 'eval "$(uvx --generate-shell-completion bash)"' >> ~/.bashrc
```

#### Zsh

```bash
echo 'eval "$(uvx --generate-shell-completion zsh)"' >> ~/.zshrc
```

#### fish

```bash
echo 'uvx --generate-shell-completion fish | source' > ~/.config/fish/completions/uvx.fish
```

#### Elvish

```bash
echo 'eval (uvx --generate-shell-completion elvish | slurp)' >> ~/.elvish/rc.elv
```

#### PowerShell / pwsh

```powershell
if (!(Test-Path -Path $PROFILE)) {
  New-Item -ItemType File -Path $PROFILE -Force
}
Add-Content -Path $PROFILE -Value '(& uvx --generate-shell-completion powershell) | Out-String | Invoke-Expression'
```

Then restart the shell or source the shell config file.

## Uninstallation

If you need to remove uv from your system, follow these steps:

1. Clean up stored data (optional):

```console
$ uv cache clean
$ rm -r "$(uv python dir)"
$ rm -r "$(uv tool dir)"
```

**Tip:** Before removing the binaries, you may want to remove any data that uv has stored.

2. Remove the uv, uvx, and uvw binaries:

On macOS and Linux:

```console
$ rm ~/.local/bin/uv ~/.local/bin/uvx
```

On Windows:

```pwsh-session
PS> rm $HOME\.local\bin\uv.exe
PS> rm $HOME\.local\bin\uvx.exe
PS> rm $HOME\.local\bin\uvw.exe
```

**Note:** Prior to 0.5.0, uv was installed into `~/.cargo/bin`. The binaries can be removed from there to uninstall. Upgrading from an older version will not automatically remove the binaries from `~/.cargo/bin`.

## First Steps

After installing uv, you can check that uv is available by running the `uv` command:

```console
$ uv
An extremely fast Python package manager.

Usage: uv [OPTIONS] <COMMAND>

...
```

You should see a help menu listing the available commands.

## Getting Help

### Help menus

The `--help` flag can be used to view the help menu for a command, e.g., for `uv`:

```console
$ uv --help
```

To view the help menu for a specific command, e.g., for `uv init`:

```console
$ uv init --help
```

When using the `--help` flag, uv displays a condensed help menu. To view a longer help menu for a command, use `uv help`:

```console
$ uv help
```

To view the long help menu for a specific command, e.g., for `uv init`:

```console
$ uv help init
```

When using the long help menu, uv will attempt to use `less` or `more` to "page" the output so it is not all displayed at once. To exit the pager, press `q`.

### Displaying verbose output

The `-v` flag can be used to display verbose output for a command, e.g., for `uv sync`:

```console
$ uv sync -v
```

The `-v` flag can be repeated to increase verbosity, e.g.:

```console
$ uv sync -vv
```

Often, the verbose output will include additional information about why uv is behaving in a certain way.

### Viewing the version

When seeking help, it's important to determine the version of uv that you're using -- sometimes the problem is already solved in a newer version.

To check the installed version:

```console
$ uv self version
```

The following are also valid:

```console
$ uv --version      # Same output as `uv self version`
$ uv -V             # Will not include the build commit and date
```

**Note:** Before uv 0.7.0, `uv version` was used instead of `uv self version`.

### Open an issue on GitHub

The issue tracker on GitHub is a good place to report bugs and request features. Make sure to search for similar issues first, as it is common for someone else to encounter the same problem.

### Chat on Discord

Astral has a Discord server, which is a great place to ask questions, learn more about uv, and engage with other community members.

## See Also

- `02-projects.md` - Project creation, running, and syncing
- `06-python-versions.md` - Python version management
- `07-tools-and-scripts.md` - Tools (uvx) and scripts (PEP 723)
- `10-configuration.md` - Config files, indexes, cache, and storage
- `17-troubleshooting.md` - Build failures and platform issues
