# Flight SQL WebSocket Proxy Server - by [GizmoData](https://gizmodata.com)™

[<img src="https://img.shields.io/badge/GitHub-gizmodata%2Fflight--sql--websocket--proxy-blue.svg?logo=Github">](https://github.com/gizmodata/flight-sql-websocket-proxy)
[<img src="https://img.shields.io/badge/github--package-container--image-green.svg?logo=Docker">](https://github.com/gizmodata/flight-sql-websocket-proxy/pkgs/container/flight-sql-websocket-proxy)
[![flight-sql-websocket-proxy-ci](https://github.com/gizmodata/flight-sql-websocket-proxy/actions/workflows/ci.yml/badge.svg)](https://github.com/gizmodata/flight-sql-websocket-proxy/actions/workflows/ci.yml)

An Arrow Flight SQL WebSocket Proxy Server

# Setup (to run locally)

## Install package
You can install `flight-sql-websocket-proxy` from PyPi or from source.

### Option 1 - from the latest Github release artifact (recommended) 

This is more complicated than installing from PyPi because the Github repo is private - and you will need to use a Github Access Token to download the wheel artifact.

**Note** - this assumes that you have your Github Access Token stored as an env var named `GITHUB_ACCESS_TOKEN`.  See: [Creating a personal access token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) for more information.

```shell
# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment
. .venv/bin/activate

# List the latest Github release - and get the wheel artifact url
ASSET_JSON=$(curl --silent --location \
                --header "Accept: application/vnd.github+json" \
                --header "Authorization: Bearer ${GITHUB_ACCESS_TOKEN}" \
                https://api.github.com/repos/gizmodata/flight-sql-websocket-proxy/releases \
                | jq --raw-output '.[0].assets[] | select(.name | test("^flight_sql_websocket_proxy\\S+\\.whl$"))'
          )

ASSET_ID=$(echo ${ASSET_JSON} | jq --raw-output '.id')
WHEEL_FILE="/tmp/$(echo ${ASSET_JSON} | jq --raw-output '.name')"

curl --location \
   --header "Accept: application/octet-stream" \
   --header "Authorization: Bearer ${GITHUB_ACCESS_TOKEN}" \
   --silent \
   --output ${WHEEL_FILE} \
   https://api.github.com/repos/gizmodata/flight-sql-websocket-proxy/releases/assets/${ASSET_ID}

# Install the wheel   
pip install ${WHEEL_FILE}
```

### Option 2 - from source - for development
```shell
git clone https://github.com/gizmodata/flight-sql-websocket-proxy

cd flight-sql-websocket-proxy

# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment
. .venv/bin/activate

# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# Install the Python package - in editable mode with dev dependencies
pip install --editable .[dev]
```

### Note
For the following commands - if you running from source and using `--editable` mode (for development purposes) - you will need to set the PYTHONPATH environment variable as follows:
```shell
export PYTHONPATH=$(pwd)/src
```

### Setting up your .env (environment) file
Create a text file named `.env` in the root of the project directory.  This file will contain the environment variables needed to run the application.   

Example:
```text
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxx
CLERK_SECRET_KEY=XXXXXXXXX
CLERK_API_URL=https://api.clerk.dev
JWKS_URL=https://something.clerk.accounts.dev/.well-known/jwks.json
SESSION_TOKEN_ISSUER=https://something.clerk.accounts.dev
DATABASE_SERVER_URI=grpc+tls://localhost:31337
DATABASE_USERNAME=gizmosql_username
DATABASE_PASSWORD=gizmosql_password
DATABASE_TLS_SKIP_VERIFY=TRUE
```

### Running the server locally
You can run the Flight SQL WebSocket Proxy Server executable locally - here is the help output:
```shell
flight-sql-websocket-proxy-server  --help
Usage: flight-sql-websocket-proxy-server [OPTIONS]

Options:
  --version / --no-version        Prints the Arrow Flight SQL WebSocket Proxy
                                  Server version and exits.  [required]
  --port INTEGER                  Run the websocket server on this port.
                                  Defaults to environment variable SERVER_PORT
                                  if set, or 8765 if not set.  [default: 8765;
                                  required]
  --tls ('CERTFILE', 'KEYFILE')   Enable transport-level security (TLS/SSL).
                                  Provide a Certificate file path, and a Key
                                  file path - separated by a space.  Defaults
                                  to environment variable TLS if set.
                                  Example: tls/server.crt tls/server.key
  --database-server-uri TEXT      The URI of the Arrow Flight SQL server.
                                  Defaults to environment variable
                                  DATABASE_SERVER_URI if set, or
                                  grpc+tls://localhost:31337 if not set.
                                  [required]
  --database-username TEXT        The username to authenticate with the Arrow
                                  Flight SQL server.  Defaults to environment
                                  variable DATABASE_USERNAME if set.
                                  [required]
  --database-password TEXT        The password to authenticate with the Arrow
                                  Flight SQL server.  Defaults to environment
                                  variable DATABASE_PASSWORD if set.
                                  [required]
  --database-tls-skip-verify / --no-database-tls-skip-verify
                                  Skip TLS verification of the Arrow Flight
                                  SQL server.  Defaults to environment
                                  variable DATABASE_TLS_SKIP_VERIFY if set, or
                                  FALSE if not set.  [default: database-tls-
                                  skip-verify; required]
  --clerk-api-url TEXT            The CLERK API URL - for user authentication.
                                  Defaults to environment variable
                                  CLERK_API_URL if set, or
                                  https://api.clerk.dev if not set.
                                  [required]
  --clerk-secret-key TEXT         The CLERK Secret Key - for user
                                  authentication.  Defaults to environment
                                  variable CLERK_SECRET_KEY if set.
                                  [required]
  --jwks-url TEXT                 The JWKS URL used for client session JWT
                                  token validation - for user authentication.
                                  Defaults to environment variable JWKS_URL if
                                  set.  Example: https://wise-
                                  cattle-777.clerk.accounts.dev/.well-
                                  known/jwks.json  [required]
  --session-token-issuer TEXT     The issuer used for client session JWT token
                                  validation - for user authentication.
                                  Defaults to environment variable
                                  SESSION_TOKEN_ISSUER if set.  Example:
                                  https://wise-cattle-777.clerk.accounts.dev
                                  [required]
  --max-process-workers INTEGER   Max process workers.  Defaults to
                                  environment variable MAX_PROCESS_WORKERS if
                                  set.  [default: 10; required]
  --websocket-ping-timeout INTEGER
                                  Web-socket ping timeout.  Defaults to
                                  environment variable PING_TIMEOUT if set.
                                  [default: 60; required]
  --max-websocket-message-size INTEGER
                                  Maximum Websocket message size  [default:
                                  1073741824; required]
  --client-default-fetch-size INTEGER
                                  The default websocket client fetch size for
                                  queries.  [default: 50; required]
  --help                          Show this message and exit.
```

### Running the server via Docker
You can optionally run the Flight SQL WebSocket Proxy Server via Docker:

**Note** - this assumes that you have your Github Access Token stored as an env var named `{GITHUB_ACCESS_TOKEN}`.  See: [Creating a personal access token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) for more information.

Open a terminal, then pull and run the published Docker image which has everything setup - with command:

```bash
# Authenticate to Github Docker Registry - replace USERNAME with your Github username
echo ${GITHUB_ACCESS_TOKEN} | docker login ghcr.io -u USERNAME --password-stdin

# Pull and run the Docker image 
docker run --name flight-sql-websocket-proxy \
           --interactive \
           --rm \
           --tty \
           --init \
           --publish 8765:8765 \
           --pull missing \
           --env-file .env \
           ghcr.io/gizmodata/flight-sql-websocket-proxy:latest
```

### Running the client
You can run the Flight SQL WebSocket Proxy Client executable locally - here is the help output:
```bash
flight-sql-websocket-proxy-client --help
Usage: flight-sql-websocket-proxy-client [OPTIONS]

Options:
  --version / --no-version        Prints the Arrow Flight SQL Websocket Proxy
                                  Client version and exits.  [required]
  --server-protocol [wss|ws]      The protocol of the Arrow Flight SQL
                                  Websocket Proxy server.  Defaults to
                                  environment variable SERVER_PROTOCOL if set,
                                  or wss if not set.  [required]
  --server-hostname TEXT          The hostname of the Arrow Flight SQL
                                  Websocket Proxy server.  Defaults to
                                  environment variable SERVER_HOSTNAME if set,
                                  or localhost if not set.  [required]
  --server-port INTEGER           The port of the Arrow Flight SQL Websocket
                                  Proxy server.  Defaults to environment
                                  variable SERVER_PORT if set, or 8765 if not
                                  set.  [required]
  --server-base-path TEXT         The base path of the Arrow Flight SQL
                                  Websocket Proxy server.  Defaults to
                                  environment variable SERVER_BASE_PATH if
                                  set, or / if not set.  [required]
  --tls-verify / --no-tls-verify  Verify the server's TLS certificate hostname
                                  and signature.  Using --no-tls-verify is
                                  insecure, only use for development purposes!
                                  [default: tls-verify]
  --tls-roots TEXT                'Path to trusted TLS certificate(s).
                                  Defaults to environment variable TLS_ROOTS
                                  if set.  If not set, the system default
                                  trusted certificates will be used.
  --token TEXT                    The client clerk JWT token to authenticate
                                  with.  Defaults to environment variable
                                  TOKEN if set.  [required]
  --max-result-set-rows INTEGER   The maximum number of rows to show in result
                                  sets.  A value of 0 means no limit.
                                  [default: 100; required]
  --autocommit / --no-autocommit  Enable autocommit mode.  [default:
                                  autocommit]
  --help                          Show this message and exit.
```

### Handy development commands

#### Version management

##### Bump the version of the application - (you must have installed from source with the [dev] extras)
```bash
bumpver update --patch
```
