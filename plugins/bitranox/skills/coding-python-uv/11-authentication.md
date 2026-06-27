# Authentication

## HTTP Credentials

uv supports credentials over HTTP when querying package registries.

Authentication can come from the following sources, in order of precedence:

- The URL, e.g., `https://<user>:<password>@<hostname>/...`
- A netrc configuration file
- The uv credentials store
- A keyring provider (off by default)

Authentication may be used for hosts specified in the following contexts:

- `[index]`
- `index-url`
- `extra-index-url`
- `find-links`
- `package @ https://...`

### netrc files

`.netrc` files are a long-standing plain text format for storing credentials on a system.

Reading credentials from `.netrc` files is always enabled. The target file path will be loaded from the `NETRC` environment variable if defined, falling back to `~/.netrc` if not.

### The uv credentials store

uv can read and write credentials from a store using the `uv auth` commands.

Credentials are stored in a plaintext file in uv's state directory, e.g., `~/.local/share/uv/credentials/credentials.toml` on Unix. This file is currently not intended to be edited manually.

**Note:** A secure, system native storage mechanism is in preview -- it is still experimental and being actively developed. In the future, this will become the default storage mechanism.

When enabled, uv will use the secret storage mechanism native to your operating system. On macOS, it uses the Keychain Services. On Windows, it uses the Windows Credential Manager. On Linux, it uses the DBus-based Secret Service API.

Currently, uv only searches the native store for credentials it has added to the secret store -- it will not retrieve credentials persisted by other applications.

Set `UV_PREVIEW_FEATURES=native-auth` to use this storage mechanism.

### Keyring providers

A keyring provider is a concept from `pip` allowing retrieval of credentials from an interface matching the popular keyring Python package.

The "subprocess" keyring provider invokes the `keyring` command to fetch credentials. uv does not support additional keyring provider types at this time.

Set `--keyring-provider subprocess`, `UV_KEYRING_PROVIDER=subprocess`, or `tool.uv.keyring-provider = "subprocess"` to use the provider.

### Persistence of credentials

If authentication is found for a single index URL or net location (scheme, host, and port), it will be cached for the duration of the command and used for other queries to that index or net location. Authentication is not cached across invocations of uv.

When using `uv add`, uv _will not_ persist index credentials to the `pyproject.toml` or `uv.lock`. These files are often included in source control and distributions, so it is generally unsafe to include credentials in them. However, uv _will_ persist credentials for direct URLs, i.e., `package @ https://username:password:example.com/foo.whl`, as there is not currently a way to otherwise provide those credentials.

If credentials were attached to an index URL during `uv add`, uv may fail to fetch dependencies from indexes which require authentication on subsequent operations. See `10-configuration.md` for details on persistent authentication for indexes.

## Git Credentials

uv allows packages to be installed from private Git repositories using SSH or HTTP authentication.

### SSH authentication

To authenticate using an SSH key, use the `ssh://` protocol:

- `git+ssh://git@<hostname>/...` (e.g., `git+ssh://git@github.com/astral-sh/uv`)
- `git+ssh://git@<host>/...` (e.g., `git+ssh://git@github.com-key-2/astral-sh/uv`)

SSH authentication requires using the username `git`.

See the GitHub SSH documentation for more details on how to configure SSH.

### HTTP authentication

To authenticate over HTTP Basic authentication using a password or token:

- `git+https://<user>:<token>@<hostname>/...` (e.g., `git+https://git:github_pat_asdf@github.com/astral-sh/uv`)
- `git+https://<token>@<hostname>/...` (e.g., `git+https://github_pat_asdf@github.com/astral-sh/uv`)
- `git+https://<user>@<hostname>/...` (e.g., `git+https://git@github.com/astral-sh/uv`)

**Note:** When using a GitHub personal access token, the username is arbitrary. GitHub doesn't allow you to use your account name and password in URLs like this, although other hosts may.

If there are no credentials present in the URL and authentication is needed, the Git credential helper will be queried.

### Persistence of Git credentials

When using `uv add`, uv _will not_ persist Git credentials to the `pyproject.toml` or `uv.lock`. These files are often included in source control and distributions, so it is generally unsafe to include credentials in them.

If you have a Git credential helper configured, your credentials may be automatically persisted, resulting in successful subsequent fetches of the dependency. However, if you do not have a Git credential helper or the project is used on a machine without credentials seeded, uv will fail to fetch the dependency.

You _may_ force uv to persist Git credentials by passing the `--raw` option to `uv add`. However, we strongly recommend setting up a credential helper instead.

### Git credential helpers

Git credential helpers are used to store and retrieve Git credentials. See the Git documentation at https://git-scm.com/doc/credential-helpers to learn more.

If you're using GitHub, the simplest way to set up a credential helper is to install the `gh` CLI and use:

```console
$ gh auth login
```

**Note:** When using `gh auth login` interactively, the credential helper will be configured automatically. But when using `gh auth login --with-token`, as in CI environments, the `gh auth setup-git` command will need to be run afterwards to configure the credential helper.

## The `uv auth` CLI

uv provides a high-level interface for storing and retrieving credentials from services.

### Logging in to a service

To add credentials for service, use the `uv auth login` command:

```console
$ uv auth login example.com
```

This will prompt for the credentials.

The credentials can also be provided using the `--username` and `--password` options, or the `--token` option for services which use a `__token__` or arbitrary username.

**Note:** We recommend providing the secret via stdin. Use `-` to indicate the value should be read from stdin, e.g., for `--password`:

```console
$ echo 'my-password' | uv auth login example.com --password -
```

The same pattern can be used with `--token`.

Once credentials are added, uv will use them for packaging operations that require fetching content from the given service. At this time, only HTTPS Basic authentication is supported. The credentials will not yet be used for Git requests.

**Note:** The credentials will not be validated, i.e., incorrect credentials will not fail.

### Logging out of a service

To remove credentials, use the `uv auth logout` command:

```console
$ uv auth logout example.com
```

**Note:** The credentials will not be invalidated with the remote server, i.e., they will only be removed from local storage not rendered unusable.

### Showing credentials for a service

To show the credential stored for a given URL, use the `uv auth token` command:

```console
$ uv auth token example.com
```

If a username was used to log in, it will need to be provided as well, e.g.:

```console
$ uv auth token --username foo example.com
```

### Configuring the storage backend

Credentials are persisted to the uv credentials store.

By default, credentials are written to a plaintext file. An encrypted system-native storage backend can be enabled with `UV_PREVIEW_FEATURES=native-auth`.

## TLS Certificates

By default, uv loads certificates from the bundled `webpki-roots` crate. The `webpki-roots` are a reliable set of trust roots from Mozilla, and including them in uv improves portability and performance (especially on macOS, where reading the system trust store incurs a significant delay).

### System certificates

In some cases, you may want to use the platform's native certificate store, especially if you're relying on a corporate trust root (e.g., for a mandatory proxy) that's included in your system's certificate store. To instruct uv to use the system's trust store, run uv with the `--native-tls` command-line flag, or set the `UV_NATIVE_TLS` environment variable to `true`.

### Custom certificates

If a direct path to the certificate is required (e.g., in CI), set the `SSL_CERT_FILE` environment variable to the path of the certificate bundle, to instruct uv to use that file instead of the system's trust store.

If client certificate authentication (mTLS) is desired, set the `SSL_CLIENT_CERT` environment variable to the path of the PEM formatted file containing the certificate followed by the private key.

### Insecure hosts

If you're using a setup in which you want to trust a self-signed certificate or otherwise disable certificate verification, you can instruct uv to allow insecure connections to dedicated hosts via the `allow-insecure-host` configuration option. For example, adding the following to `pyproject.toml` will allow insecure connections to `example.com`:

```toml
[tool.uv]
allow-insecure-host = ["example.com"]
```

`allow-insecure-host` expects to receive a hostname (e.g., `localhost`) or hostname-port pair (e.g., `localhost:8080`), and is only applicable to HTTPS connections, as HTTP connections are inherently insecure.

Use `allow-insecure-host` with caution and only in trusted environments, as it can expose you to security risks due to the lack of certificate verification.

## Third-Party Services

### Hugging Face

uv supports automatic authentication for the Hugging Face Hub. Specifically, if the `HF_TOKEN` environment variable is set, uv will propagate it to requests to `huggingface.co`.

This is particularly useful for accessing private scripts in Hugging Face Datasets. For example, you can run the following command to execute the script `main.py` from a private dataset:

```console
$ HF_TOKEN=hf_... uv run https://huggingface.co/datasets/<user>/<name>/resolve/<branch>/main.py
```

You can disable automatic Hugging Face authentication by setting the `UV_NO_HF_TOKEN=1` environment variable.

### Azure Artifacts

uv can install packages from Azure Artifacts, either by using a Personal Access Token (PAT), or using the `keyring` package.

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

If you also want to publish your own packages to Azure Artifacts, you can use `uv publish`. For general publishing details, see `08-building-and-publishing.md`.

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

uv can install packages from Google Artifact Registry, either by using an access token, or using the `keyring` package.

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

uv can install packages from AWS CodeArtifact, either by using an access token, or using the `keyring` package.

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

The `keyrings.codeartifact` plugin wraps `boto3` to generate short-lived access tokens, securely store them in system keyring, and refresh them when they are expired.

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

## See Also

- `08-building-and-publishing.md` - Building and publishing packages
- `10-configuration.md` - Package indexes, index authentication, and configuration
- `14-ci-cd.md` - CI/CD integration with trusted publishers
