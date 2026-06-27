# CI/CD Integration

## GitHub Actions

### Installation

For use with GitHub Actions, the official [`astral-sh/setup-uv`](https://github.com/astral-sh/setup-uv) action is recommended. It installs uv, adds it to PATH, (optionally) persists the cache, and more, with support for all uv-supported platforms.

To install the latest version of uv:

```yaml
name: Example

jobs:
  uv-example:
    name: python
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7
```

It is considered best practice to pin to a specific uv version, e.g., with:

```yaml
name: Example

jobs:
  uv-example:
    name: python
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          # Install a specific version of uv.
          version: "0.10.2"
```

### Setting up Python

Python can be installed with the `python install` command:

```yaml
name: Example

jobs:
  uv-example:
    name: python
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Set up Python
        run: uv python install
```

This will respect the Python version pinned in the project.

Alternatively, the official GitHub `setup-python` action can be used. This can be faster, because GitHub caches the Python versions alongside the runner.

Set the `python-version-file` option to use the pinned version for the project:

```yaml
name: Example

jobs:
  uv-example:
    name: python
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6

      - name: "Set up Python"
        uses: actions/setup-python@v6
        with:
          python-version-file: ".python-version"

      - name: Install uv
        uses: astral-sh/setup-uv@v7
```

Or, specify the `pyproject.toml` file to ignore the pin and use the latest version compatible with the project's `requires-python` constraint:

```yaml
name: Example

jobs:
  uv-example:
    name: python
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6

      - name: "Set up Python"
        uses: actions/setup-python@v6
        with:
          python-version-file: "pyproject.toml"

      - name: Install uv
        uses: astral-sh/setup-uv@v7
```

### Multiple Python versions

When using a matrix to test multiple Python versions, set the Python version using `astral-sh/setup-uv`, which will override the Python version specification in the `pyproject.toml` or `.python-version` files:

```yaml
jobs:
  build:
    name: continuous-integration
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version:
          - "3.10"
          - "3.11"
          - "3.12"

    steps:
      - uses: actions/checkout@v6

      - name: Install uv and set the Python version
        uses: astral-sh/setup-uv@v7
        with:
          python-version: ${{ matrix.python-version }}
```

If not using the `setup-uv` action, you can set the `UV_PYTHON` environment variable:

```yaml
jobs:
  build:
    name: continuous-integration
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version:
          - "3.10"
          - "3.11"
          - "3.12"
    env:
      UV_PYTHON: ${{ matrix.python-version }}
    steps:
      - uses: actions/checkout@v6
```

### Syncing and running

Once uv and Python are installed, the project can be installed with `uv sync` and commands can be run in the environment with `uv run`. For more on project workflows, see `02-projects.md`.

```yaml
name: Example

jobs:
  uv-example:
    name: python
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Install the project
        run: uv sync --locked --all-extras --dev

      - name: Run tests
        # For example, using `pytest`
        run: uv run pytest tests
```

**Tip:** The `UV_PROJECT_ENVIRONMENT` setting can be used to install to the system Python environment instead of creating a virtual environment.

### Caching

It may improve CI times to store uv's cache across workflow runs.

The [`astral-sh/setup-uv`](https://github.com/astral-sh/setup-uv) has built-in support for persisting the cache:

```yaml
- name: Enable caching
  uses: astral-sh/setup-uv@v7
  with:
    enable-cache: true
```

Alternatively, you can manage the cache manually with the `actions/cache` action:

```yaml
jobs:
  install_job:
    env:
      # Configure a constant location for the uv cache
      UV_CACHE_DIR: /tmp/.uv-cache

    steps:
      # ... setup up Python and uv ...

      - name: Restore uv cache
        uses: actions/cache@v5
        with:
          path: /tmp/.uv-cache
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
            uv-${{ runner.os }}

      # ... install packages, run tests, etc ...

      - name: Minimize uv cache
        run: uv cache prune --ci
```

The `uv cache prune --ci` command is used to reduce the size of the cache and is optimized for CI. Its effect on performance is dependent on the packages being installed.

**Tip:** If using `uv pip`, use `requirements.txt` instead of `uv.lock` in the cache key.

**Note:** When using non-ephemeral, self-hosted runners the default cache directory can grow unbounded. In this case, it may not be optimal to share the cache between jobs. Instead, move the cache inside the GitHub Workspace and remove it once the job finishes using a [Post Job Hook](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/running-scripts-before-or-after-a-job).

```yaml
install_job:
  env:
    # Configure a relative location for the uv cache
    UV_CACHE_DIR: ${{ github.workspace }}/.cache/uv
```

Using a post job hook requires setting the `ACTIONS_RUNNER_HOOK_JOB_STARTED` environment variable on the self-hosted runner to the path of a cleanup script such as the one shown below.

```sh
#!/usr/bin/env sh
uv cache clean
```

### Using `uv pip`

If using the `uv pip` interface instead of the uv project interface, uv requires a virtual environment by default. To allow installing packages into the system environment, use the `--system` flag on all `uv` invocations or set the `UV_SYSTEM_PYTHON` variable.

The `UV_SYSTEM_PYTHON` variable can be defined at different scopes.

Opt-in for the entire workflow by defining it at the top level:

```yaml
env:
  UV_SYSTEM_PYTHON: 1

jobs: ...
```

Or, opt-in for a specific job in the workflow:

```yaml
jobs:
  install_job:
    env:
      UV_SYSTEM_PYTHON: 1
    ...
```

Or, opt-in for a specific step in a job:

```yaml
steps:
  - name: Install requirements
    run: uv pip install -r requirements.txt
    env:
      UV_SYSTEM_PYTHON: 1
```

To opt-out again, the `--no-system` flag can be used in any uv invocation.

### Private repos

If your project has dependencies on private GitHub repositories, you will need to configure a [personal access token (PAT)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) to allow uv to fetch them.

After creating a PAT that has read access to the private repositories, add it as a [repository secret](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions#creating-secrets-for-a-repository).

Then, you can use the `gh` CLI (which is installed in GitHub Actions runners by default) to configure a credential helper for Git to use the PAT for queries to repositories hosted on `github.com`.

For example, if you called your repository secret `MY_PAT`:

```yaml
steps:
  - name: Register the personal access token
    run: echo "${{ secrets.MY_PAT }}" | gh auth login --with-token
  - name: Configure the Git credential helper
    run: gh auth setup-git
```

### Publishing to PyPI

uv can be used to build and publish your package to PyPI from GitHub Actions. For details on building and publishing, see `08-building-and-publishing.md`. A standalone example is available in [astral-sh/trusted-publishing-examples](https://github.com/astral-sh/trusted-publishing-examples). The workflow uses [trusted publishing](https://docs.pypi.org/trusted-publishers/), so no credentials need to be configured.

In the example workflow, a script is used to test that the source distribution and the wheel are both functional and no files were missed. This step is recommended, but optional.

First, add a release workflow to your project:

```yaml
name: "Publish"

on:
  push:
    tags:
      # Publish on any tag starting with a `v`, e.g., v0.1.0
      - v*

jobs:
  run:
    runs-on: ubuntu-latest
    environment:
      name: pypi
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Checkout
        uses: actions/checkout@v6
      - name: Install uv
        uses: astral-sh/setup-uv@v7
      - name: Install Python 3.13
        run: uv python install 3.13
      - name: Build
        run: uv build
      # Check that basic features work and we didn't miss to include crucial files
      - name: Smoke test (wheel)
        run: uv run --isolated --no-project --with dist/*.whl tests/smoke_test.py
      - name: Smoke test (source distribution)
        run: uv run --isolated --no-project --with dist/*.tar.gz tests/smoke_test.py
      - name: Publish
        run: uv publish
```

Then, create the environment defined in the workflow in the GitHub repository under "Settings" -> "Environments".

Add a [trusted publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/) to your PyPI project in the project settings under "Publishing". Ensure that all fields match with your GitHub configuration.

Finally, tag a release and push it. Make sure it starts with `v` to match the pattern in the workflow.

```console
$ git tag -a v0.1.0 -m v0.1.0
$ git push --tags
```

## GitLab CI/CD

### Using the uv image

Astral provides Docker images with uv preinstalled. Select a variant that is suitable for your workflow. For details on available images and Docker best practices, see `13-docker.md`.

```yaml
variables:
  UV_VERSION: "0.10.2"
  PYTHON_VERSION: "3.12"
  BASE_LAYER: bookworm-slim
  # GitLab CI creates a separate mountpoint for the build directory,
  # so we need to copy instead of using hard links.
  UV_LINK_MODE: copy

uv:
  image: ghcr.io/astral-sh/uv:$UV_VERSION-python$PYTHON_VERSION-$BASE_LAYER
  script:
    # your `uv` commands
```

**Note:** If you are using a distroless image, you have to specify the entrypoint:

```yaml
uv:
  image:
    name: ghcr.io/astral-sh/uv:$UV_VERSION
    entrypoint: [""]
  # ...
```

### Caching

Persisting the uv cache between workflow runs can improve performance.

```yaml
uv-install:
  variables:
    UV_CACHE_DIR: .uv-cache
  cache:
    - key:
        files:
          - uv.lock
      paths:
        - $UV_CACHE_DIR
  script:
    # Your `uv` commands
    - uv cache prune --ci
```

See the [GitLab caching documentation](https://docs.gitlab.com/ee/ci/caching/) for more details on configuring caching.

Using `uv cache prune --ci` at the end of the job is recommended to reduce cache size.

### Using `uv pip`

If using the `uv pip` interface instead of the uv project interface, uv requires a virtual environment by default. To allow installing packages into the system environment, use the `--system` flag on all uv invocations or set the `UV_SYSTEM_PYTHON` variable.

The `UV_SYSTEM_PYTHON` variable can be defined at different scopes. You can read more about how variables and their precedence works in GitLab in the [GitLab documentation](https://docs.gitlab.com/ee/ci/variables/).

Opt-in for the entire workflow by defining it at the top level:

```yaml
variables:
  UV_SYSTEM_PYTHON: 1

# [...]
```

To opt-out again, the `--no-system` flag can be used in any uv invocation.

When persisting the cache, you may want to use `requirements.txt` or `pyproject.toml` as your cache key files instead of `uv.lock`.

## See Also

- `02-projects.md` - Project creation, running, and syncing
- `06-python-versions.md` - Python version management
- `08-building-and-publishing.md` - Building and publishing packages
- `10-configuration.md` - Config files, environment variables, cache, and storage
- `13-docker.md` - Docker integration
