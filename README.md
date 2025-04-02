# Flight SQL WebSocket Proxy Server
### Copyright © 2025 GizmoData LLC - All Rights Reserved 

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

### Running the Docker image
You can optionally run the Flight SQL WebSocket Proxy Server image:

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

### Handy development commands

#### Version management

##### Bump the version of the application - (you must have installed from source with the [dev] extras)
```bash
bumpver update --patch
```
