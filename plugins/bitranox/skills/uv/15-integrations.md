# Integrations

## FastAPI

[FastAPI](https://github.com/fastapi/fastapi) is a modern, high-performance Python web framework. You can use uv to manage your FastAPI project, including installing dependencies, managing environments, running FastAPI applications, and more.

**Note:** You can view the source code for this guide in the [uv-fastapi-example](https://github.com/astral-sh/uv-fastapi-example) repository.

### Migrating an existing FastAPI project

As an example, consider the sample application defined in the [FastAPI documentation](https://fastapi.tiangolo.com/tutorial/bigger-applications/), structured as follows:

```plaintext
project
└── app
    ├── __init__.py
    ├── main.py
    ├── dependencies.py
    ├── routers
    │   ├── __init__.py
    │   ├── items.py
    │   └── users.py
    └── internal
        ├── __init__.py
        └── admin.py
```

To use uv with this application, inside the `project` directory run:

```console
$ uv init --app
```

This creates a project with an application layout and a `pyproject.toml` file.

Then, add a dependency on FastAPI:

```console
$ uv add fastapi --extra standard
```

You should now have the following structure:

```plaintext
project
├── pyproject.toml
└── app
    ├── __init__.py
    ├── main.py
    ├── dependencies.py
    ├── routers
    │   ├── __init__.py
    │   ├── items.py
    │   └── users.py
    └── internal
        ├── __init__.py
        └── admin.py
```

And the contents of the `pyproject.toml` file should look something like this:

```toml
[project]
name = "uv-fastapi-example"
version = "0.1.0"
description = "FastAPI project"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]",
]
```

From there, you can run the FastAPI application with:

```console
$ uv run fastapi dev
```

`uv run` will automatically resolve and lock the project dependencies (i.e., create a `uv.lock` alongside the `pyproject.toml`), create a virtual environment, and run the command in that environment.

Test the app by opening http://127.0.0.1:8000/?token=jessica in a web browser.

### Deployment

To deploy the FastAPI application with Docker, you can use the following `Dockerfile`. For more Docker best practices, see `13-docker.md`.

```dockerfile
FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Run the application.
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--port", "80", "--host", "0.0.0.0"]
```

Build the Docker image with:

```console
$ docker build -t fastapi-app .
```

Run the Docker container locally with:

```console
$ docker run -p 8000:80 fastapi-app
```

Navigate to http://127.0.0.1:8000/?token=jessica in your browser to verify that the app is running correctly.

## Jupyter

The [Jupyter](https://jupyter.org/) notebook is a popular tool for interactive computing, data analysis, and visualization. You can use Jupyter with uv in a few different ways, either to interact with a project, or as a standalone tool.

### Using Jupyter within a project

If you're working within a project, you can start a Jupyter server with access to the project's virtual environment via the following:

```console
$ uv run --with jupyter jupyter lab
```

By default, `jupyter lab` will start the server at http://localhost:8888/lab.

Within a notebook, you can import your project's modules as you would in any other file in the project. For example, if your project depends on `requests`, `import requests` will import `requests` from the project's virtual environment.

If you're looking for read-only access to the project's virtual environment, then there's nothing more to it. However, if you need to install additional packages from within the notebook, there are a few extra details to consider.

### Creating a kernel

If you need to install packages from within the notebook, creating a dedicated kernel for your project is recommended. Kernels enable the Jupyter server to run in one environment, with individual notebooks running in their own, separate environments.

In the context of uv, you can create a kernel for a project while installing Jupyter itself in an isolated environment, as in `uv run --with jupyter jupyter lab`. Creating a kernel for the project ensures that the notebook is hooked up to the correct environment, and that any packages installed from within the notebook are installed into the project's virtual environment.

To create a kernel, you'll need to install `ipykernel` as a development dependency:

```console
$ uv add --dev ipykernel
```

Then, you can create the kernel for `project` with:

```console
$ uv run ipython kernel install --user --env VIRTUAL_ENV $(pwd)/.venv --name=project
```

From there, start the server with:

```console
$ uv run --with jupyter jupyter lab
```

When creating a notebook, select the `project` kernel from the dropdown. Then use `!uv add pydantic` to add `pydantic` to the project's dependencies, or `!uv pip install pydantic` to install `pydantic` into the project's virtual environment without persisting the change to the project `pyproject.toml` or `uv.lock` files. Either command will make `import pydantic` work within the notebook.

### Installing packages without a kernel

If you don't want to create a kernel, you can still install packages from within the notebook. However, there are a few caveats to consider.

Though `uv run --with jupyter` runs in an isolated environment, within the notebook itself, `!uv add` and related commands will modify the _project's_ environment, even without a kernel.

For example, running `!uv add pydantic` from within a notebook will add `pydantic` to the project's dependencies and virtual environment, such that `import pydantic` will work immediately, without further configuration or a server restart.

However, since the Jupyter server is the "active" environment, `!uv pip install` will install package's into _Jupyter's_ environment, not the project environment. Such dependencies will persist for the lifetime of the Jupyter server, but may disappear on subsequent `jupyter` invocations.

If you're working with a notebook that relies on pip (e.g., via the `%pip` magic), you can include pip in your project's virtual environment by running `uv venv --seed` prior to starting the Jupyter server. For example, given:

```console
$ uv venv --seed
$ uv run --with jupyter jupyter lab
```

Subsequent `%pip install` invocations within the notebook will install packages into the project's virtual environment. However, such modifications will _not_ be reflected in the project's `pyproject.toml` or `uv.lock` files.

### Using Jupyter as a standalone tool

If you ever need ad hoc access to a notebook (i.e., to run a Python snippet interactively), you can start a Jupyter server at any time with `uv tool run jupyter lab`. This will run a Jupyter server in an isolated environment.

### Using Jupyter with a non-project environment

If you need to run Jupyter in a virtual environment that isn't associated with a project (e.g., has no `pyproject.toml` or `uv.lock`), you can do so by adding Jupyter to the environment directly.

#### macOS and Linux

```console
$ uv venv --seed
$ uv pip install pydantic
$ uv pip install jupyterlab
$ .venv/bin/jupyter lab
```

#### Windows

```pwsh-session
PS> uv venv --seed
PS> uv pip install pydantic
PS> uv pip install jupyterlab
PS> .venv\Scripts\jupyter lab
```

From here, `import pydantic` will work within the notebook, and you can install additional packages via `!uv pip install`, or even `!pip install`.

### Using Jupyter from VS Code

You can also engage with Jupyter notebooks from within an editor like VS Code. To connect a uv-managed project to a Jupyter notebook within VS Code, creating a kernel for the project is recommended:

```console
# Create a project.
$ uv init project

# Move into the project directory.
$ cd project

# Add ipykernel as a dev dependency.
$ uv add --dev ipykernel

# Open the project in VS Code.
$ code .
```

Once the project directory is open in VS Code, you can create a new Jupyter notebook by selecting "Create: New Jupyter Notebook" from the command palette. When prompted to select a kernel, choose "Python Environments" and select the virtual environment you created earlier (e.g., `.venv/bin/python` on macOS and Linux, or `.venv\Scripts\python` on Windows).

**Note:** VS Code requires `ipykernel` to be present in the project environment. If you'd prefer to avoid adding `ipykernel` as a dev dependency, you can install it directly into the project environment with `uv pip install ipykernel`.

If you need to manipulate the project's environment from within the notebook, you may need to add `uv` as an explicit development dependency:

```console
$ uv add --dev uv
```

From there, you can use `!uv add pydantic` to add `pydantic` to the project's dependencies, or `!uv pip install pydantic` to install `pydantic` into the project's virtual environment without updating the project's `pyproject.toml` or `uv.lock` files.

## Marimo

[marimo](https://github.com/marimo-team/marimo) is an open-source Python notebook that blends interactive computing with the reproducibility and reusability of traditional software, letting you version with Git, run as scripts, and share as apps. Because marimo notebooks are stored as pure Python scripts, they are able to integrate tightly with uv.

You can readily use marimo as a standalone tool, as self-contained scripts, in projects, and in non-project environments.

### Using marimo as a standalone tool

For ad-hoc access to marimo notebooks, start a marimo server at any time in an isolated environment with:

```console
$ uvx marimo edit
```

Start a specific notebook with:

```console
$ uvx marimo edit my_notebook.py
```

### Using marimo with inline script metadata

Because marimo notebooks are stored as Python scripts, they can encapsulate their own dependencies using inline script metadata (see `07-tools-and-scripts.md` for details on scripts with inline metadata). For example, to add `numpy` as a dependency to your notebook, use this command:

```console
$ uv add --script my_notebook.py numpy
```

To interactively edit a notebook containing inline script metadata, use:

```console
$ uvx marimo edit --sandbox my_notebook.py
```

marimo will automatically use uv to start your notebook in an isolated virtual environment with your script's dependencies. Packages installed from the marimo UI will automatically be added to the notebook's script metadata.

You can optionally run these notebooks as Python scripts, without opening an interactive session:

```console
$ uv run my_notebook.py
```

### Using marimo within a project

If you're working within a project, you can start a marimo notebook with access to the project's virtual environment via the following command (assuming marimo is a project dependency):

```console
$ uv run marimo edit my_notebook.py
```

To make additional packages available to your notebook, either add them to your project with `uv add`, or use marimo's built-in package installation UI, which will invoke `uv add` on your behalf.

If marimo is not a project dependency, you can still run a notebook with the following command:

```console
$ uv run --with marimo marimo edit my_notebook.py
```

This will let you import your project's modules while editing your notebook. However, packages installed via marimo's UI when running in this way will not be added to your project, and may disappear on subsequent marimo invocations.

### Using marimo in a non-project environment

To run marimo in a virtual environment that isn't associated with a project, add marimo to the environment directly:

```console
$ uv venv
$ uv pip install numpy
$ uv pip install marimo
$ uv run marimo edit
```

From here, `import numpy` will work within the notebook, and marimo's UI installer will add packages to the environment with `uv pip install` on your behalf.

### Running marimo notebooks as scripts

Regardless of how your dependencies are managed (with inline script metadata, within a project, or with a non-project environment), you can run marimo notebooks as scripts with:

```console
$ uv run my_notebook.py
```

This executes your notebook as a Python script, without opening an interactive session in your browser.

## pre-commit

An official pre-commit hook is provided at [`astral-sh/uv-pre-commit`](https://github.com/astral-sh/uv-pre-commit).

To use uv with pre-commit, add one of the following examples to the `repos` list in the `.pre-commit-config.yaml`.

To make sure your `uv.lock` file is up to date even if your `pyproject.toml` file was changed:

```yaml
repos:
  - repo: https://github.com/astral-sh/uv-pre-commit
    # uv version.
    rev: 0.10.2
    hooks:
      - id: uv-lock
```

To keep a `requirements.txt` file in sync with your `uv.lock` file:

```yaml
repos:
  - repo: https://github.com/astral-sh/uv-pre-commit
    # uv version.
    rev: 0.10.2
    hooks:
      - id: uv-export
```

To compile requirements files:

```yaml
repos:
  - repo: https://github.com/astral-sh/uv-pre-commit
    # uv version.
    rev: 0.10.2
    hooks:
      # Compile requirements
      - id: pip-compile
        args: [requirements.in, -o, requirements.txt]
```

To compile alternative requirements files, modify `args` and `files`:

```yaml
repos:
  - repo: https://github.com/astral-sh/uv-pre-commit
    # uv version.
    rev: 0.10.2
    hooks:
      # Compile requirements
      - id: pip-compile
        args: [requirements-dev.in, -o, requirements-dev.txt]
        files: ^requirements-dev\.(in|txt)$
```

To run the hook over multiple files at the same time, add additional entries:

```yaml
repos:
  - repo: https://github.com/astral-sh/uv-pre-commit
    # uv version.
    rev: 0.10.2
    hooks:
      # Compile requirements
      - id: pip-compile
        name: pip-compile requirements.in
        args: [requirements.in, -o, requirements.txt]
      - id: pip-compile
        name: pip-compile requirements-dev.in
        args: [requirements-dev.in, -o, requirements-dev.txt]
        files: ^requirements-dev\.(in|txt)$
```

## PyTorch

The [PyTorch](https://pytorch.org/) ecosystem is a popular choice for deep learning research and development. You can use uv to manage PyTorch projects and PyTorch dependencies across different Python versions and environments, even controlling for the choice of accelerator (e.g., CPU-only vs. CUDA).

**Note:** Some of the features outlined in this section require uv version 0.5.3 or later. Upgrading prior to configuring PyTorch is recommended.

### Installing PyTorch

From a packaging perspective, PyTorch has a few uncommon characteristics:

- Many PyTorch wheels are hosted on a dedicated index, rather than the Python Package Index (PyPI). As such, installing PyTorch often requires configuring a project to use the PyTorch index.
- PyTorch produces distinct builds for each accelerator (e.g., CPU-only, CUDA). Since there's no standardized mechanism for specifying these accelerators when publishing or installing, PyTorch encodes them in the local version specifier. As such, PyTorch versions will often look like `2.5.1+cpu`, `2.5.1+cu121`, etc.
- Builds for different accelerators are published to different indexes. For example, the `+cpu` builds are published on https://download.pytorch.org/whl/cpu, while the `+cu121` builds are published on https://download.pytorch.org/whl/cu121.

As such, the necessary packaging configuration will vary depending on both the platforms you need to support and the accelerators you want to enable.

To start, consider the following (default) configuration, which would be generated by running `uv init --python 3.14` followed by `uv add torch torchvision`.

In this case, PyTorch would be installed from PyPI, which hosts CPU-only wheels for Windows and macOS, and GPU-accelerated wheels on Linux (targeting CUDA 12.8, as of PyTorch 2.9.1):

```toml
[project]
name = "project"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
  "torch>=2.9.1",
  "torchvision>=0.24.1",
]
```

This is a valid configuration for projects that want to use CPU builds on Windows and macOS, and CUDA-enabled builds on Linux. However, if you need to support different platforms or accelerators, you'll need to configure the project accordingly.

### Using a PyTorch index

In some cases, you may want to use a specific PyTorch variant across all platforms. For example, you may want to use the CPU-only builds on Linux too.

In such cases, the first step is to add the relevant PyTorch index to your `pyproject.toml`:

#### CPU-only

```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true
```

#### CUDA 11.8

```toml
[[tool.uv.index]]
name = "pytorch-cu118"
url = "https://download.pytorch.org/whl/cu118"
explicit = true
```

#### CUDA 12.6

```toml
[[tool.uv.index]]
name = "pytorch-cu126"
url = "https://download.pytorch.org/whl/cu126"
explicit = true
```

#### CUDA 12.8

```toml
[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true
```

#### CUDA 13.0

```toml
[[tool.uv.index]]
name = "pytorch-cu130"
url = "https://download.pytorch.org/whl/cu130"
explicit = true
```

#### ROCm6

```toml
[[tool.uv.index]]
name = "pytorch-rocm"
url = "https://download.pytorch.org/whl/rocm6.4"
explicit = true
```

#### Intel GPUs

```toml
[[tool.uv.index]]
name = "pytorch-xpu"
url = "https://download.pytorch.org/whl/xpu"
explicit = true
```

The use of `explicit = true` is recommended to ensure that the index is _only_ used for `torch`, `torchvision`, and other PyTorch-related packages, as opposed to generic dependencies like `jinja2`, which should continue to be sourced from the default index (PyPI). For more on index configuration, see `10-configuration.md`.

Next, update the `pyproject.toml` to point `torch` and `torchvision` to the desired index.

#### CPU-only sources

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-cpu" },
]
torchvision = [
  { index = "pytorch-cpu" },
]
```

#### CUDA 11.8 sources

PyTorch doesn't publish CUDA builds for macOS. As such, gate on `sys_platform` to instruct uv to use the PyTorch index on Linux and Windows, but fall back to PyPI on macOS:

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-cu118", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
torchvision = [
  { index = "pytorch-cu118", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
```

#### CUDA 12.6 sources

PyTorch doesn't publish CUDA builds for macOS. As such, gate on `sys_platform` to limit the PyTorch index to Linux and Windows, falling back to PyPI on macOS:

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-cu126", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
torchvision = [
  { index = "pytorch-cu126", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
```

#### CUDA 12.8 sources

PyTorch doesn't publish CUDA builds for macOS. As such, gate on `sys_platform` to limit the PyTorch index to Linux and Windows, falling back to PyPI on macOS:

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-cu128", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
torchvision = [
  { index = "pytorch-cu128", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
```

#### CUDA 13.0 sources

PyTorch doesn't publish CUDA builds for macOS. As such, gate on `sys_platform` to limit the PyTorch index to Linux and Windows, falling back to PyPI on macOS:

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-cu130", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
torchvision = [
  { index = "pytorch-cu130", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
```

#### ROCm6 sources

PyTorch doesn't publish ROCm6 builds for macOS or Windows. As such, gate on `sys_platform` to limit the PyTorch index to Linux, falling back to PyPI on macOS and Windows:

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-rocm", marker = "sys_platform == 'linux'" },
]
torchvision = [
  { index = "pytorch-rocm", marker = "sys_platform == 'linux'" },
]
# ROCm6 support relies on `pytorch-triton-rocm`, which should also be installed from the PyTorch index
# (and included in `project.dependencies`).
pytorch-triton-rocm = [
  { index = "pytorch-rocm", marker = "sys_platform == 'linux'" },
]
```

#### Intel GPU sources

PyTorch doesn't publish Intel GPU builds for macOS. As such, gate on `sys_platform` to limit the PyTorch index to Linux and Windows, falling back to PyPI on macOS:

```toml
[tool.uv.sources]
torch = [
  { index = "pytorch-xpu", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
torchvision = [
  { index = "pytorch-xpu", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
# Intel GPU support relies on `pytorch-triton-xpu`, which should also be installed from the PyTorch index
# (and included in `project.dependencies`).
pytorch-triton-xpu = [
  { index = "pytorch-xpu", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
```

As a complete example, the following project would use PyTorch's CPU-only builds on all platforms:

```toml
[project]
name = "project"
version = "0.1.0"
requires-python = ">=3.14.0"
dependencies = [
  "torch>=2.9.1",
  "torchvision>=0.24.1",
]

[tool.uv.sources]
torch = [
    { index = "pytorch-cpu" },
]
torchvision = [
    { index = "pytorch-cpu" },
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true
```

### Configuring accelerators with environment markers

In some cases, you may want to use CPU-only builds in one environment (e.g., macOS and Windows), and CUDA-enabled builds in another (e.g., Linux).

With `tool.uv.sources`, you can use environment markers to specify the desired index for each platform. For example, the following configuration would use PyTorch's CUDA-enabled builds on Linux, and CPU-only builds on all other platforms (e.g., macOS and Windows):

```toml
[project]
name = "project"
version = "0.1.0"
requires-python = ">=3.14.0"
dependencies = [
  "torch>=2.9.1",
  "torchvision>=0.24.1",
]

[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", marker = "sys_platform != 'linux'" },
  { index = "pytorch-cu128", marker = "sys_platform == 'linux'" },
]
torchvision = [
  { index = "pytorch-cpu", marker = "sys_platform != 'linux'" },
  { index = "pytorch-cu128", marker = "sys_platform == 'linux'" },
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true
```

Similarly, the following configuration would use PyTorch's AMD GPU builds on Linux, and CPU-only builds on Windows and macOS (by way of falling back to PyPI):

```toml
[project]
name = "project"
version = "0.1.0"
requires-python = ">=3.14.0"
dependencies = [
  "torch>=2.9.1",
  "torchvision>=0.24.1",
  "pytorch-triton-rocm>=3.5.1 ; sys_platform == 'linux'",
]

[tool.uv.sources]
torch = [
  { index = "pytorch-rocm", marker = "sys_platform == 'linux'" },
]
torchvision = [
  { index = "pytorch-rocm", marker = "sys_platform == 'linux'" },
]
pytorch-triton-rocm = [
  { index = "pytorch-rocm", marker = "sys_platform == 'linux'" },
]

[[tool.uv.index]]
name = "pytorch-rocm"
url = "https://download.pytorch.org/whl/rocm6.4"
explicit = true
```

Or, for Intel GPU builds:

```toml
[project]
name = "project"
version = "0.1.0"
requires-python = ">=3.14.0"
dependencies = [
  "torch>=2.9.1",
  "torchvision>=0.24.1",
  "pytorch-triton-xpu>=3.5.0 ; sys_platform == 'win32' or sys_platform == 'linux'",
]

[tool.uv.sources]
torch = [
  { index = "pytorch-xpu", marker = "sys_platform == 'win32' or sys_platform == 'linux'" },
]
torchvision = [
  { index = "pytorch-xpu", marker = "sys_platform == 'win32' or sys_platform == 'linux'" },
]
pytorch-triton-xpu = [
  { index = "pytorch-xpu", marker = "sys_platform == 'win32' or sys_platform == 'linux'" },
]

[[tool.uv.index]]
name = "pytorch-xpu"
url = "https://download.pytorch.org/whl/xpu"
explicit = true
```

### Configuring accelerators with optional dependencies

In some cases, you may want to use CPU-only builds in some cases, but CUDA-enabled builds in others, with the choice toggled by a user-provided extra (e.g., `uv sync --extra cpu` vs. `uv sync --extra cu128`).

With `tool.uv.sources`, you can use extra markers to specify the desired index for each enabled extra. For example, the following configuration would use PyTorch's CPU-only for `uv sync --extra cpu` and CUDA-enabled builds for `uv sync --extra cu128`:

```toml
[project]
name = "project"
version = "0.1.0"
requires-python = ">=3.14.0"
dependencies = []

[project.optional-dependencies]
cpu = [
  "torch>=2.9.1",
  "torchvision>=0.24.1",
]
cu128 = [
  "torch>=2.9.1",
  "torchvision>=0.24.1",
]

[tool.uv]
conflicts = [
  [
    { extra = "cpu" },
    { extra = "cu128" },
  ],
]

[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", extra = "cpu" },
  { index = "pytorch-cu128", extra = "cu128" },
]
torchvision = [
  { index = "pytorch-cpu", extra = "cpu" },
  { index = "pytorch-cu128", extra = "cu128" },
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true
```

**Note:** Since GPU-accelerated builds aren't available on macOS, the above configuration will fail to install on macOS when the `cu128` extra is enabled.

### The `uv pip` interface

While the above examples are focused on uv's project interface (`uv lock`, `uv sync`, `uv run`, etc.), PyTorch can also be installed via the `uv pip` interface.

PyTorch itself offers a [dedicated interface](https://pytorch.org/get-started/locally/) to determine the appropriate pip command to run for a given target configuration. For example, you can install stable, CPU-only PyTorch on Linux with:

```shell
$ pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

To use the same workflow with uv, replace `pip3` with `uv pip`:

```shell
$ uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Automatic backend selection

uv supports automatic selection of the appropriate PyTorch index via the `--torch-backend=auto` command-line argument (or the `UV_TORCH_BACKEND=auto` environment variable), as in:

```shell
$ # With a command-line argument.
$ uv pip install torch --torch-backend=auto

$ # With an environment variable.
$ UV_TORCH_BACKEND=auto uv pip install torch
```

When enabled, uv will query for the installed CUDA driver, AMD GPU versions, and Intel GPU presence, then use the most-compatible PyTorch index for all relevant packages (e.g., `torch`, `torchvision`, etc.). If no such GPU is found, uv will fall back to the CPU-only index. uv will continue to respect existing index configuration for any packages outside the PyTorch ecosystem.

You can also select a specific backend (e.g., CUDA 12.8) with `--torch-backend=cu126` (or `UV_TORCH_BACKEND=cu126`):

```shell
$ # With a command-line argument.
$ uv pip install torch torchvision --torch-backend=cu126

$ # With an environment variable.
$ UV_TORCH_BACKEND=cu128 uv pip install torch torchvision
```

At present, `--torch-backend` is only available in the `uv pip` interface.

## AWS Lambda

[AWS Lambda](https://aws.amazon.com/lambda/) is a serverless computing service that lets you run code without provisioning or managing servers.

You can use uv with AWS Lambda to manage your Python dependencies, build your deployment package, and deploy your Lambda functions.

**Tip:** Check out the [`uv-aws-lambda-example`](https://github.com/astral-sh/uv-aws-lambda-example) project for an example of best practices when using uv to deploy an application to AWS Lambda.

### Getting started

To start, assume a minimal FastAPI application with the following structure:

```plaintext
project
├── pyproject.toml
└── app
    ├── __init__.py
    └── main.py
```

Where the `pyproject.toml` contains:

```toml
[project]
name = "uv-aws-lambda-example"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    # FastAPI is a modern web framework for building APIs with Python.
    "fastapi",
    # Mangum is a library that adapts ASGI applications to AWS Lambda and API Gateway.
    "mangum",
]

[dependency-groups]
dev = [
    # In development mode, include the FastAPI development server.
    "fastapi[standard]>=0.115",
]
```

And the `main.py` file contains:

```python
import logging

from fastapi import FastAPI
from mangum import Mangum

logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = FastAPI()
handler = Mangum(app)


@app.get("/")
async def root() -> str:
    return "Hello, world!"
```

Run this application locally with:

```console
$ uv run fastapi dev
```

From there, opening http://127.0.0.1:8000/ in a web browser will display "Hello, world!"

### Deploying a Docker image

To deploy to AWS Lambda, build a container image that includes the application code and dependencies in a single output directory.

Following the principles of multi-stage builds ensures that the final image is as small and cache-friendly as possible.

In the first stage, populate a single directory with all application code and dependencies. In the second stage, copy this directory over to the final image, omitting the build tools and other unnecessary files.

```dockerfile
FROM ghcr.io/astral-sh/uv:0.10.2 AS uv

# First, bundle the dependencies into the task root.
FROM public.ecr.aws/lambda/python:3.13 AS builder

# Enable bytecode compilation, to improve cold-start performance.
ENV UV_COMPILE_BYTECODE=1

# Disable installer metadata, to create a deterministic layer.
ENV UV_NO_INSTALLER_METADATA=1

# Enable copy mode to support bind mount caching.
ENV UV_LINK_MODE=copy

# Bundle the dependencies into the Lambda task root via `uv pip install --target`.
#
# Omit any local packages (`--no-emit-workspace`) and development dependencies (`--no-dev`).
# This ensures that the Docker layer cache is only invalidated when the `pyproject.toml` or `uv.lock`
# files change, but remains robust to changes in the application code.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --frozen --no-emit-workspace --no-dev --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

FROM public.ecr.aws/lambda/python:3.13

# Copy the runtime dependencies from the builder stage.
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copy the application code.
COPY ./app ${LAMBDA_TASK_ROOT}/app

# Set the AWS Lambda handler.
CMD ["app.main.handler"]
```

**Tip:** To deploy to ARM-based AWS Lambda runtimes, replace `public.ecr.aws/lambda/python:3.13` with `public.ecr.aws/lambda/python:3.13-arm64`.

Build the image with, e.g.:

```console
$ uv lock
$ docker build -t fastapi-app .
```

The core benefits of this Dockerfile structure are:

1. **Minimal image size.** By using a multi-stage build, the final image only includes the application code and dependencies. For example, the uv binary itself is not included in the final image.
2. **Maximal cache reuse.** By installing application dependencies separately from the application code, the Docker layer cache is only invalidated when the dependencies change.

After building, push the image to Elastic Container Registry (ECR) with, e.g.:

```console
$ aws ecr get-login-password --region region | docker login --username AWS --password-stdin aws_account_id.dkr.ecr.region.amazonaws.com
$ docker tag fastapi-app:latest aws_account_id.dkr.ecr.region.amazonaws.com/fastapi-app:latest
$ docker push aws_account_id.dkr.ecr.region.amazonaws.com/fastapi-app:latest
```

Deploy the image to AWS Lambda using the AWS Management Console or the AWS CLI, e.g.:

```console
$ aws lambda create-function \
   --function-name myFunction \
   --package-type Image \
   --code ImageUri=aws_account_id.dkr.ecr.region.amazonaws.com/fastapi-app:latest \
   --role arn:aws:iam::111122223333:role/my-lambda-role
```

Where the execution role is created via:

```console
$ aws iam create-role \
   --role-name my-lambda-role \
   --assume-role-policy-document '{"Version": "2012-10-17", "Statement": [{ "Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}'
```

Or, update an existing function with:

```console
$ aws lambda update-function-code \
   --function-name myFunction \
   --image-uri aws_account_id.dkr.ecr.region.amazonaws.com/fastapi-app:latest \
   --publish
```

To test the Lambda, invoke it via the AWS Management Console or the AWS CLI, e.g.:

```console
$ aws lambda invoke \
   --function-name myFunction \
   --payload file://event.json \
   --cli-binary-format raw-in-base64-out \
   response.json
{
  "StatusCode": 200,
  "ExecutedVersion": "$LATEST"
}
```

Where `event.json` contains the event payload to pass to the Lambda function:

```json
{
  "httpMethod": "GET",
  "path": "/",
  "requestContext": {},
  "version": "1.0"
}
```

And `response.json` contains the response from the Lambda function:

```json
{
  "statusCode": 200,
  "headers": {
    "content-length": "14",
    "content-type": "application/json"
  },
  "multiValueHeaders": {},
  "body": "\"Hello, world!\"",
  "isBase64Encoded": false
}
```

### Workspace support

If a project includes local dependencies (e.g., via Workspaces), those too must be included in the deployment package.

Extend the above example to include a dependency on a locally-developed library named `library`.

First, create the library itself:

```console
$ uv init --lib library
$ uv add ./library
```

Running `uv init` within the `project` directory will automatically convert `project` to a workspace and add `library` as a workspace member:

```toml
[project]
name = "uv-aws-lambda-example"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    # FastAPI is a modern web framework for building APIs with Python.
    "fastapi",
    # A local library.
    "library",
    # Mangum is a library that adapts ASGI applications to AWS Lambda and API Gateway.
    "mangum",
]

[dependency-groups]
dev = [
    # In development mode, include the FastAPI development server.
    "fastapi[standard]",
]

[tool.uv.workspace]
members = ["library"]

[tool.uv.sources]
lib = { workspace = true }
```

By default, `uv init --lib` will create a package that exports a `hello` function. Modify the application source code to call that function:

```python
import logging

from fastapi import FastAPI
from mangum import Mangum

from library import hello

logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = FastAPI()
handler = Mangum(app)


@app.get("/")
async def root() -> str:
    return hello()
```

Run the modified application locally with:

```console
$ uv run fastapi dev
```

And confirm that opening http://127.0.0.1:8000/ in a web browser displays, "Hello from library!" (instead of "Hello, World!")

Update the Dockerfile to include the local library in the deployment package:

```dockerfile
FROM ghcr.io/astral-sh/uv:0.10.2 AS uv

# First, bundle the dependencies into the task root.
FROM public.ecr.aws/lambda/python:3.13 AS builder

# Enable bytecode compilation, to improve cold-start performance.
ENV UV_COMPILE_BYTECODE=1

# Disable installer metadata, to create a deterministic layer.
ENV UV_NO_INSTALLER_METADATA=1

# Enable copy mode to support bind mount caching.
ENV UV_LINK_MODE=copy

# Bundle the dependencies into the Lambda task root via `uv pip install --target`.
#
# Omit any local packages (`--no-emit-workspace`) and development dependencies (`--no-dev`).
# This ensures that the Docker layer cache is only invalidated when the `pyproject.toml` or `uv.lock`
# files change, but remains robust to changes in the application code.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --frozen --no-emit-workspace --no-dev --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# If you have a workspace, copy it over and install it too.
#
# By omitting `--no-emit-workspace`, `library` will be copied into the task root. Using a separate
# `RUN` command ensures that all third-party dependencies are cached separately and remain
# robust to changes in the workspace.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=library,target=library \
    uv export --frozen --no-dev --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

FROM public.ecr.aws/lambda/python:3.13

# Copy the runtime dependencies from the builder stage.
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copy the application code.
COPY ./app ${LAMBDA_TASK_ROOT}/app

# Set the AWS Lambda handler.
CMD ["app.main.handler"]
```

**Tip:** To deploy to ARM-based AWS Lambda runtimes, replace `public.ecr.aws/lambda/python:3.13` with `public.ecr.aws/lambda/python:3.13-arm64`.

From there, build and deploy the updated image as before.

### Deploying a zip archive

AWS Lambda also supports deployment via zip archives. For simple applications, zip archives can be a more straightforward and efficient deployment method than Docker images; however, zip archives are limited to 250 MB in size.

Returning to the FastAPI example, bundle the application dependencies into a local directory for AWS Lambda via:

```console
$ uv export --frozen --no-dev --no-editable -o requirements.txt
$ uv pip install \
   --no-installer-metadata \
   --no-compile-bytecode \
   --python-platform x86_64-manylinux2014 \
   --python 3.13 \
   --target packages \
   -r requirements.txt
```

**Tip:** To deploy to ARM-based AWS Lambda runtimes, replace `x86_64-manylinux2014` with `aarch64-manylinux2014`.

Following the AWS Lambda documentation, bundle these dependencies into a zip as follows:

```console
$ cd packages
$ zip -r ../package.zip .
$ cd ..
```

Add the application code to the zip archive:

```console
$ zip -r package.zip app
```

Deploy the zip archive to AWS Lambda via the AWS Management Console or the AWS CLI, e.g.:

```console
$ aws lambda create-function \
   --function-name myFunction \
   --runtime python3.13 \
   --zip-file fileb://package.zip \
   --handler app.main.handler \
   --role arn:aws:iam::111122223333:role/service-role/my-lambda-role
```

Where the execution role is created via:

```console
$ aws iam create-role \
   --role-name my-lambda-role \
   --assume-role-policy-document '{"Version": "2012-10-17", "Statement": [{ "Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}'
```

Or, update an existing function with:

```console
$ aws lambda update-function-code \
   --function-name myFunction \
   --zip-file fileb://package.zip
```

**Note:** By default, the AWS Management Console assumes a Lambda entrypoint of `lambda_function.lambda_handler`. If your application uses a different entrypoint, you'll need to modify it in the AWS Management Console. For example, the above FastAPI application uses `app.main.handler`.

To test the Lambda, invoke it via the AWS Management Console or the AWS CLI, e.g.:

```console
$ aws lambda invoke \
   --function-name myFunction \
   --payload file://event.json \
   --cli-binary-format raw-in-base64-out \
   response.json
{
  "StatusCode": 200,
  "ExecutedVersion": "$LATEST"
}
```

Where `event.json` contains the event payload to pass to the Lambda function:

```json
{
  "httpMethod": "GET",
  "path": "/",
  "requestContext": {},
  "version": "1.0"
}
```

And `response.json` contains the response from the Lambda function:

```json
{
  "statusCode": 200,
  "headers": {
    "content-length": "14",
    "content-type": "application/json"
  },
  "multiValueHeaders": {},
  "body": "\"Hello, world!\"",
  "isBase64Encoded": false
}
```

### Using a Lambda layer

AWS Lambda also supports the deployment of multiple composed Lambda layers when working with zip archives. These layers are conceptually similar to layers in a Docker image, allowing you to separate application code from dependencies.

In particular, you can create a lambda layer for application dependencies and attach it to the Lambda function, separate from the application code itself. This setup can improve cold-start performance for application updates, as the dependencies layer can be reused across deployments.

To create a Lambda layer, follow similar steps, but create two separate zip archives: one for the application code and one for the application dependencies.

First, create the dependency layer. Lambda layers are expected to follow a slightly different structure, so use `--prefix` rather than `--target`:

```console
$ uv export --frozen --no-dev --no-editable -o requirements.txt
$ uv pip install \
   --no-installer-metadata \
   --no-compile-bytecode \
   --python-platform x86_64-manylinux2014 \
   --python 3.13 \
   --prefix packages \
   -r requirements.txt
```

Then zip the dependencies in adherence with the expected layout for Lambda layers:

```console
$ mkdir python
$ cp -r packages/lib python/
$ zip -r layer_content.zip python
```

**Tip:** To generate deterministic zip archives, consider passing the `-X` flag to `zip` to exclude extended attributes and file system metadata.

And publish the Lambda layer:

```console
$ aws lambda publish-layer-version --layer-name dependencies-layer \
   --zip-file fileb://layer_content.zip \
   --compatible-runtimes python3.13 \
   --compatible-architectures "x86_64"
```

Then create the Lambda function, omitting the dependencies:

```console
$ # Zip the application code.
$ zip -r app.zip app

$ # Create the Lambda function.
$ aws lambda create-function \
   --function-name myFunction \
   --runtime python3.13 \
   --zip-file fileb://app.zip \
   --handler app.main.handler \
   --role arn:aws:iam::111122223333:role/service-role/my-lambda-role
```

Attach the dependencies layer to the Lambda function, using the ARN returned by the `publish-layer-version` step:

```console
$ aws lambda update-function-configuration --function-name myFunction \
    --cli-binary-format raw-in-base64-out \
    --layers "arn:aws:lambda:region:111122223333:layer:dependencies-layer:1"
```

When the application dependencies change, the layer can be updated independently of the application by republishing the layer and updating the Lambda function configuration:

```console
$ # Update the dependencies in the layer.
$ aws lambda publish-layer-version --layer-name dependencies-layer \
   --zip-file fileb://layer_content.zip \
   --compatible-runtimes python3.13 \
   --compatible-architectures "x86_64"

$ # Update the Lambda function configuration.
$ aws lambda update-function-configuration --function-name myFunction \
    --cli-binary-format raw-in-base64-out \
    --layers "arn:aws:lambda:region:111122223333:layer:dependencies-layer:2"
```

## Alternative Indexes

While uv uses the official Python Package Index (PyPI) by default, it also supports alternative package indexes. Most alternative indexes require various forms of authentication, which require some initial setup.

**Important:** If using the pip interface, the default behavior is different from pip to prevent dependency confusion attacks, but this means that uv may not find the versions of a package as you'd expect. For authentication details, see `11-authentication.md`.

### Azure Artifacts

uv can install packages from [Azure Artifacts](https://learn.microsoft.com/en-us/azure/devops/artifacts/start-using-azure-artifacts), either by using a Personal Access Token (PAT), or using the `keyring` package.

To use Azure Artifacts, add the index to your project:

```toml
[[tool.uv.index]]
name = "private-registry"
url = "https://pkgs.dev.azure.com/<ORGANIZATION>/<PROJECT>/_packaging/<FEED>/pypi/simple/"
```

#### Authenticate with an Azure access token

If there is a personal access token (PAT) available (e.g., `$(System.AccessToken)` in an Azure pipeline), credentials can be provided via "Basic" HTTP authentication scheme. Include the PAT in the password field of the URL. A username must be included as well, but can be any string.

For example, with the token stored in the `$AZURE_ARTIFACTS_TOKEN` environment variable, set credentials for the index with:

```bash
export UV_INDEX_PRIVATE_REGISTRY_USERNAME=dummy
export UV_INDEX_PRIVATE_REGISTRY_PASSWORD="$AZURE_ARTIFACTS_TOKEN"
```

**Note:** `PRIVATE_REGISTRY` should match the name of the index defined in your `pyproject.toml`.

#### Authenticate with `keyring` and `artifacts-keyring`

You can also authenticate to Artifacts using the `keyring` package with the `artifacts-keyring` plugin. Because these two packages are required to authenticate to Azure Artifacts, they must be pre-installed from a source other than Artifacts.

The `artifacts-keyring` plugin wraps the Azure Artifacts Credential Provider tool. The credential provider supports a few different authentication modes including interactive login -- see the tool's documentation for information on configuration.

uv only supports using the `keyring` package in subprocess mode. The `keyring` executable must be in the `PATH`, i.e., installed globally or in the active environment. The `keyring` CLI requires a username in the URL, and it must be `VssSessionToken`.

```bash
# Pre-install keyring and the Artifacts plugin from the public PyPI
uv tool install keyring --with artifacts-keyring

# Enable keyring authentication
export UV_KEYRING_PROVIDER=subprocess

# Set the username for the index
export UV_INDEX_PRIVATE_REGISTRY_USERNAME=VssSessionToken
```

**Note:** The `tool.uv.keyring-provider` setting can be used to enable keyring in your `uv.toml` or `pyproject.toml`. Similarly, the username for the index can be added directly to the index URL.

#### Publishing packages to Azure Artifacts

If you also want to publish your own packages to Azure Artifacts, you can use `uv publish`.

First, add a `publish-url` to the index you want to publish packages to. For example:

```toml
[[tool.uv.index]]
name = "private-registry"
url = "https://pkgs.dev.azure.com/<ORGANIZATION>/<PROJECT>/_packaging/<FEED>/pypi/simple/"
publish-url = "https://pkgs.dev.azure.com/<ORGANIZATION>/<PROJECT>/_packaging/<FEED>/pypi/upload/"
```

Then, configure credentials (if not using keyring):

```console
$ export UV_PUBLISH_USERNAME=dummy
$ export UV_PUBLISH_PASSWORD="$AZURE_ARTIFACTS_TOKEN"
```

And publish the package:

```console
$ uv publish --index private-registry
```

To use `uv publish` without adding the `publish-url` to the project, you can set `UV_PUBLISH_URL`:

```console
$ export UV_PUBLISH_URL=https://pkgs.dev.azure.com/<ORGANIZATION>/<PROJECT>/_packaging/<FEED>/pypi/upload/
$ uv publish
```

Note this method is not preferable because uv cannot check if the package is already published before uploading artifacts.

### Google Artifact Registry

uv can install packages from [Google Artifact Registry](https://cloud.google.com/artifact-registry/docs), either by using an access token, or using the `keyring` package.

**Note:** This section assumes that `gcloud` CLI is installed and authenticated.

To use Google Artifact Registry, add the index to your project:

```toml
[[tool.uv.index]]
name = "private-registry"
url = "https://<REGION>-python.pkg.dev/<PROJECT>/<REPOSITORY>/simple/"
```

#### Authenticate with a Google access token

Credentials can be provided via "Basic" HTTP authentication scheme. Include access token in the password field of the URL. Username must be `oauth2accesstoken`, otherwise authentication will fail.

Generate a token with `gcloud`:

```bash
export ARTIFACT_REGISTRY_TOKEN=$(
    gcloud auth application-default print-access-token
)
```

**Note:** You might need to pass extra parameters to properly generate the token (like `--project`), this is a basic example.

Then set credentials for the index with:

```bash
export UV_INDEX_PRIVATE_REGISTRY_USERNAME=oauth2accesstoken
export UV_INDEX_PRIVATE_REGISTRY_PASSWORD="$ARTIFACT_REGISTRY_TOKEN"
```

**Note:** `PRIVATE_REGISTRY` should match the name of the index defined in your `pyproject.toml`.

#### Authenticate with `keyring` and `keyrings.google-artifactregistry-auth`

You can also authenticate to Artifact Registry using the `keyring` package with the `keyrings.google-artifactregistry-auth` plugin. Because these two packages are required to authenticate to Artifact Registry, they must be pre-installed from a source other than Artifact Registry.

The `keyrings.google-artifactregistry-auth` plugin wraps `gcloud` CLI to generate short-lived access tokens, securely store them in system keyring, and refresh them when they are expired.

uv only supports using the `keyring` package in subprocess mode. The `keyring` executable must be in the `PATH`, i.e., installed globally or in the active environment. The `keyring` CLI requires a username in the URL and it must be `oauth2accesstoken`.

```bash
# Pre-install keyring and Artifact Registry plugin from the public PyPI
uv tool install keyring --with keyrings.google-artifactregistry-auth

# Enable keyring authentication
export UV_KEYRING_PROVIDER=subprocess

# Set the username for the index
export UV_INDEX_PRIVATE_REGISTRY_USERNAME=oauth2accesstoken
```

**Note:** The `tool.uv.keyring-provider` setting can be used to enable keyring in your `uv.toml` or `pyproject.toml`. Similarly, the username for the index can be added directly to the index URL.

#### Publishing packages to Google Artifact Registry

If you also want to publish your own packages to Google Artifact Registry, you can use `uv publish`.

First, add a `publish-url` to the index you want to publish packages to. For example:

```toml
[[tool.uv.index]]
name = "private-registry"
url = "https://<REGION>-python.pkg.dev/<PROJECT>/<REPOSITORY>/simple/"
publish-url = "https://<REGION>-python.pkg.dev/<PROJECT>/<REPOSITORY>/"
```

Then, configure credentials (if not using keyring):

```console
$ export UV_PUBLISH_USERNAME=oauth2accesstoken
$ export UV_PUBLISH_PASSWORD="$ARTIFACT_REGISTRY_TOKEN"
```

And publish the package:

```console
$ uv publish --index private-registry
```

To use `uv publish` without adding the `publish-url` to the project, you can set `UV_PUBLISH_URL`:

```console
$ export UV_PUBLISH_URL=https://<REGION>-python.pkg.dev/<PROJECT>/<REPOSITORY>/
$ uv publish
```

Note this method is not preferable because uv cannot check if the package is already published before uploading artifacts.

### AWS CodeArtifact

uv can install packages from [AWS CodeArtifact](https://docs.aws.amazon.com/codeartifact/latest/ug/using-python.html), either by using an access token, or using the `keyring` package.

**Note:** This section assumes that `awscli` is installed and authenticated.

The index can be declared like so:

```toml
[[tool.uv.index]]
name = "private-registry"
url = "https://<DOMAIN>-<ACCOUNT_ID>.d.codeartifact.<REGION>.amazonaws.com/pypi/<REPOSITORY>/simple/"
```

#### Authenticate with an AWS access token

Credentials can be provided via "Basic" HTTP authentication scheme. Include access token in the password field of the URL. Username must be `aws`, otherwise authentication will fail.

Generate a token with `awscli`:

```bash
export AWS_CODEARTIFACT_TOKEN="$(
    aws codeartifact get-authorization-token \
    --domain <DOMAIN> \
    --domain-owner <ACCOUNT_ID> \
    --query authorizationToken \
    --output text
)"
```

**Note:** You might need to pass extra parameters to properly generate the token (like `--region`), this is a basic example.

Then set credentials for the index with:

```bash
export UV_INDEX_PRIVATE_REGISTRY_USERNAME=aws
export UV_INDEX_PRIVATE_REGISTRY_PASSWORD="$AWS_CODEARTIFACT_TOKEN"
```

**Note:** `PRIVATE_REGISTRY` should match the name of the index defined in your `pyproject.toml`.

#### Authenticate with `keyring` and `keyrings.codeartifact`

You can also authenticate to Artifact Registry using the `keyring` package with the `keyrings.codeartifact` plugin. Because these two packages are required to authenticate to Artifact Registry, they must be pre-installed from a source other than Artifact Registry.

The `keyrings.codeartifact` plugin wraps boto3 to generate short-lived access tokens, securely store them in system keyring, and refresh them when they are expired.

uv only supports using the `keyring` package in subprocess mode. The `keyring` executable must be in the `PATH`, i.e., installed globally or in the active environment. The `keyring` CLI requires a username in the URL and it must be `aws`.

```bash
# Pre-install keyring and AWS CodeArtifact plugin from the public PyPI
uv tool install keyring --with keyrings.codeartifact

# Enable keyring authentication
export UV_KEYRING_PROVIDER=subprocess

# Set the username for the index
export UV_INDEX_PRIVATE_REGISTRY_USERNAME=aws
```

**Note:** The `tool.uv.keyring-provider` setting can be used to enable keyring in your `uv.toml` or `pyproject.toml`. Similarly, the username for the index can be added directly to the index URL.

#### Publishing packages to AWS CodeArtifact

If you also want to publish your own packages to AWS CodeArtifact, you can use `uv publish`.

First, add a `publish-url` to the index you want to publish packages to. For example:

```toml
[[tool.uv.index]]
name = "private-registry"
url = "https://<DOMAIN>-<ACCOUNT_ID>.d.codeartifact.<REGION>.amazonaws.com/pypi/<REPOSITORY>/simple/"
publish-url = "https://<DOMAIN>-<ACCOUNT_ID>.d.codeartifact.<REGION>.amazonaws.com/pypi/<REPOSITORY>/"
```

Then, configure credentials (if not using keyring):

```console
$ export UV_PUBLISH_USERNAME=aws
$ export UV_PUBLISH_PASSWORD="$AWS_CODEARTIFACT_TOKEN"
```

And publish the package:

```console
$ uv publish --index private-registry
```

To use `uv publish` without adding the `publish-url` to the project, you can set `UV_PUBLISH_URL`:

```console
$ export UV_PUBLISH_URL=https://<DOMAIN>-<ACCOUNT_ID>.d.codeartifact.<REGION>.amazonaws.com/pypi/<REPOSITORY>/
$ uv publish
```

Note this method is not preferable because uv cannot check if the package is already published before uploading artifacts.

### JFrog Artifactory

uv can install packages from JFrog Artifactory, either by using a username and password or a JWT token.

To use it, add the index to your project:

```toml
[[tool.uv.index]]
name = "private-registry"
url = "https://<organization>.jfrog.io/artifactory/api/pypi/<repository>/simple"
```

#### Authenticate with username and password

```console
$ export UV_INDEX_PRIVATE_REGISTRY_USERNAME="<username>"
$ export UV_INDEX_PRIVATE_REGISTRY_PASSWORD="<password>"
```

#### Authenticate with JWT token

```console
$ export UV_INDEX_PRIVATE_REGISTRY_USERNAME=""
$ export UV_INDEX_PRIVATE_REGISTRY_PASSWORD="$JFROG_JWT_TOKEN"
```

**Note:** Replace `PRIVATE_REGISTRY` in the environment variable names with the actual index name defined in your `pyproject.toml`.

#### Publishing packages to JFrog Artifactory

Add a `publish-url` to your index definition:

```toml
[[tool.uv.index]]
name = "private-registry"
url = "https://<organization>.jfrog.io/artifactory/api/pypi/<repository>/simple"
publish-url = "https://<organization>.jfrog.io/artifactory/api/pypi/<repository>"
```

**Important:** If you use `--token "$JFROG_TOKEN"` or `UV_PUBLISH_TOKEN` with JFrog, you will receive a 401 Unauthorized error as JFrog requires an empty username but uv passes `__token__` as the username when `--token` is used.

To authenticate, pass your token as the password and set the username to an empty string:

```console
$ uv publish --index <index_name> -u "" -p "$JFROG_TOKEN"
```

Alternatively, you can set environment variables:

```console
$ export UV_PUBLISH_USERNAME=""
$ export UV_PUBLISH_PASSWORD="$JFROG_TOKEN"
$ uv publish --index private-registry
```

**Note:** The publish environment variables (`UV_PUBLISH_USERNAME` and `UV_PUBLISH_PASSWORD`) do not include the index name.

## Dependency Bots

It is considered best practice to regularly update dependencies, to avoid being exposed to vulnerabilities, limit incompatibilities between dependencies, and avoid complex upgrades when upgrading from a too old version. A variety of tools can help staying up-to-date by creating automated pull requests. Several of them support uv, or have work underway to support it.

### Renovate

uv is supported by [Renovate](https://github.com/renovatebot/renovate).

#### `uv.lock` output

Renovate uses the presence of a `uv.lock` file to determine that uv is used for managing dependencies, and will suggest upgrades to project dependencies, optional dependencies, and development dependencies. Renovate will update both the `pyproject.toml` and `uv.lock` files.

The lockfile can also be refreshed on a regular basis (for instance to update transitive dependencies) by enabling the `lockFileMaintenance` option:

```json5
{
  $schema: "https://docs.renovatebot.com/renovate-schema.json",
  lockFileMaintenance: {
    enabled: true,
  },
}
```

#### Inline script metadata

Renovate supports updating dependencies defined using script inline metadata.

Since it cannot automatically detect which Python files use script inline metadata, their locations need to be explicitly defined using `fileMatch`, like so:

```json5
{
  $schema: "https://docs.renovatebot.com/renovate-schema.json",
  pep723: {
    fileMatch: [
      "scripts/generate_docs\\.py",
      "scripts/run_server\\.py",
    ],
  },
}
```

### Dependabot

Dependabot has announced support for uv, but there are some use cases that are not yet working. See [astral-sh/uv#2512](https://github.com/astral-sh/uv/issues/2512) for updates.

Dependabot supports updating `uv.lock` files. To enable it, add the uv `package-ecosystem` to your `updates` list in the `dependabot.yml`:

```yaml
version: 2

updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
```

## Coiled

[Coiled](https://coiled.io) is a serverless, UX-focused cloud computing platform that makes it easy to run code on cloud hardware (AWS, GCP, and Azure).

This section shows how to run Python scripts on the cloud using uv for dependency management and Coiled for cloud deployment.

### Managing script dependencies with uv

The following script is used as an example throughout this section, but any Python script can be used with uv and Coiled.

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pandas",
#   "pyarrow",
#   "s3fs",
# ]
# ///

import pandas as pd

df = pd.read_parquet(
    "s3://coiled-data/uber/part.0.parquet",
    storage_options={"anon": True},
)
print(df.head())
```

The script uses `pandas` to load a Parquet file hosted in a public bucket on S3, then prints the first few rows. It uses inline script metadata to enumerate its dependencies.

When running this script locally, e.g., with:

```bash
$ uv run process.py
```

uv will automatically create a virtual environment and install its dependencies.

### Running scripts on the cloud with Coiled

Using inline script metadata makes the script fully self-contained: it includes the information that is needed to run it. This makes it easier to run on other machines, like a machine in the cloud.

There are many use cases where resources beyond what's available on a local workstation are needed, e.g.:

- Processing large amounts of cloud-hosted data
- Needing accelerated hardware like GPUs or a big machine with more memory
- Running the same script with hundreds or thousands of different inputs, in parallel

Coiled makes it simple to run code on cloud hardware.

First, authenticate with Coiled using `coiled login`:

```bash
$ uvx coiled login
```

You'll be prompted to create a Coiled account if you don't already have one -- it's free to start using Coiled.

To instruct Coiled to run the script on a virtual machine on AWS, add two comments to the top:

```python
# COILED container ghcr.io/astral-sh/uv:debian-slim
# COILED region us-east-2

# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pandas",
#   "pyarrow",
#   "s3fs",
# ]
# ///

import pandas as pd

df = pd.read_parquet(
    "s3://coiled-data/uber/part.0.parquet",
    storage_options={"anon": True},
)
print(df.head())
```

**Tip:** While Coiled supports AWS, GCP, and Azure, this example assumes AWS is being used (see the `region` option above). If you're new to Coiled, you'll automatically have access to a free account running on AWS. If you're not running on AWS, you can either use a valid `region` for your cloud provider or remove the `region` line above.

The comments tell Coiled to use the official uv Docker image when running the script (ensuring uv is available) and to run in the `us-east-2` region on AWS (where this example data file happens to live) to avoid any data egress.

To submit a batch job for Coiled to run, use `coiled batch run` to execute the `uv run` command in the cloud:

```bash
$ uvx coiled batch run \
    uv run process.py
```

The same process that previously ran locally is now running on a remote cloud VM on AWS.

You can monitor the progress of the batch job in the UI at cloud.coiled.io or from the terminal using the `coiled batch status`, `coiled batch wait`, and `coiled batch logs` commands.

Note there's additional configuration that could be specified, e.g., the instance type (the default is a 4-core virtual machine with 16 GiB of memory), disk size, whether to use spot instance, and more. See the [Coiled Batch documentation](https://docs.coiled.io/user_guide/batch.html) for more details.

## See Also

- `03-project-config.md` - pyproject.toml configuration
- `04-dependencies.md` - Dependency management, groups, and sources
- `07-tools-and-scripts.md` - Tools (uvx) and scripts (PEP 723)
- `10-configuration.md` - Config files, indexes, cache, and storage
- `11-authentication.md` - Authentication for private indexes
- `13-docker.md` - Docker integration
