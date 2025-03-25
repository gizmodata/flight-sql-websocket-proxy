# Gizmo Edge - Copyright 2024 - Gizmo Data LLC 

[<img src="https://img.shields.io/badge/GitHub-gizmodata%2Fgizmo--edge-blue.svg?logo=Github">](https://github.com/gizmodata/gizmo-edge)
[<img src="https://img.shields.io/badge/github--package-container--image-green.svg?logo=Docker">](https://github.com/gizmodata/gizmo-edge/pkgs/container/gizmo-edge)
[![gizmo-edge-ci](https://github.com/gizmodata/gizmo-edge/actions/workflows/ci.yml/badge.svg)](https://github.com/gizmodata/gizmo-edge/actions/workflows/ci.yml)

Python-based Distributed Database

### Note: Gizmo Edge is experimental - and is not yet intended for Production workloads. 

Gizmo Edge is a [Python](https://python.org)-based (with [asyncio](https://docs.python.org/3/library/asyncio.html)) Proof-of-Concept Distributed Database that distributes shards of data from the server to a number of workers to "divide and conquer" OLAP database workloads.

It consists of a server, workers, and a client (where you can run interactive SQL commands).

Gizmo Edge will NOT distribute queries which do not contain aggregates - it will run those on the server side. 

Gizmo Edge uses [Apache Arrow](https://arrow.apache.org) with [Websockets](https://websockets.readthedocs.io/en/stable/) with TLS for secure communication between the server, worker(s), and client(s).  

It uses [DuckDB](https://duckdb.org) as its SQL execution engine - and the PostgreSQL parser to understand how to combine results from distributed workers.

# Setup (to run locally)

## Install package
You can install `gizmo-edge` from PyPi or from source.

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
                https://api.github.com/repos/gizmodata/gizmo-edge/releases \
                | jq --raw-output '.[0].assets[] | select(.name | test("^gizmo_edge\\S+\\.whl$"))'
          )

ASSET_ID=$(echo ${ASSET_JSON} | jq --raw-output '.id')
WHEEL_FILE="/tmp/$(echo ${ASSET_JSON} | jq --raw-output '.name')"

curl --location \
   --header "Accept: application/octet-stream" \
   --header "Authorization: Bearer ${GITHUB_ACCESS_TOKEN}" \
   --silent \
   --output ${WHEEL_FILE} \
   https://api.github.com/repos/gizmodata/gizmo-edge/releases/assets/${ASSET_ID}

# Install the wheel   
pip install ${WHEEL_FILE}
```

### Option 2 - from source - for development
```shell
git clone https://github.com/gizmodata/gizmo-edge

cd gizmo-edge

# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment
. .venv/bin/activate

# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# Install Gizmo Edge - in editable mode with dev dependencies
pip install --editable .[dev]
```

### Note
For the following commands - if you running from source and using `--editable` mode (for development purposes) - you will need to set the PYTHONPATH environment variable as follows:
```shell
export PYTHONPATH=$(pwd)/src
```

## Bootstrap the environment by creating a security user list (password file), TLS certificate keypair, and a sample TPC-H dataset with 11 shards
### (The passwords shown are just examples, it is recommended that you use more secure passwords)
```shell
. .venv/bin/activate
gizmo-edge-bootstrap \
    --client-username=scott \
    --client-password=tiger \
    --worker-password=united \
    --tpch-scale-factor=1 \
    --shard-count=11
```

## Run gizmo-edge locally - from root of repo (use --help option on the executables below for option details)


### 1) Server:
#### Open a terminal, then:
```bash
. .venv/bin/activate
gizmo-edge-server
```

### 2) Worker:
#### Open another terminal, then start a single worker (using the same worker password you used in the bootstrap command above) with command:
```bash
. .venv/bin/activate
gizmo-edge-worker --tls-roots=tls/server.crt --password=united
```
##### Note: you can run up to 11 workers for this example configuration, to do that do this instead of starting a single-worker:
```bash
. .venv/bin/activate
for x in {1..11}:
do
  gizmo-edge-worker --tls-roots=tls/server.crt --password=united &
done
```

To kill the workers later - run:
```bash
kill $(jobs -p)
```

### 3) Client:
#### Open another terminal, then connect with the client - using the same client username/password you used in the bootstrap command above:
```
. .venv/bin/activate
gizmo-edge-client --tls-roots=tls/server.crt --username=scott --password=tiger
```

##### Then - while in the client - you can run a sample query that will distribute to the worker(s) (if you have at least one running) - example:
```SELECT COUNT(*) FROM lineitem;```
##### Note: if you are running less than 11 workers - your answer will only reflect n/11 of the data (where n is the worker count).  We will add delta processing at a later point...

##### A query that won't distribute (because it does not contain aggregates) - would be:
```SELECT * FROM region;```
##### or:
```SELECT * FROM lineitem LIMIT 5;```

##### Note: there are TPC-H queries in the [tpc-h_queries](tpc-h_queries) folder you can run...

##### To turn distributed mode OFF in the client:
```.set distributed = false;```

##### To turn summarization mode OFF in the client (so that gizmo-edge does NOT summarize the workers' results - this only applies to distributed mode):
```.set summarize = false;```

### Optional DuckDB CLI (use for data QA purposes, etc.)
Install DuckDB CLI version [1.1.3](https://github.com/duckdb/duckdb/releases/tag/v1.1.3) - and make sure the executable is on your PATH.

Platform Downloads:   
[Linux x86-64](https://github.com/duckdb/duckdb/releases/download/v1.1.3/duckdb_cli-linux-amd64.zip)   
[Linux arm64 (aarch64)](https://github.com/duckdb/duckdb/releases/download/v1.1.3/duckdb_cli-linux-aarch64.zip)   
[MacOS Universal](https://github.com/duckdb/duckdb/releases/download/v1.1.3/duckdb_cli-osx-universal.zip)   

### Running the Docker image
You can optionally run the Gizmo Edge Docker image:

**Note** - this assumes that you have your Github Access Token stored as an env var named `{GITHUB_ACCESS_TOKEN}`.  See: [Creating a personal access token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) for more information.

Open a terminal, then pull and run the published Docker image which has everything setup - with command:

```bash
# Authenticate to Github Docker Registry - replace USERNAME with your Github username
echo ${GITHUB_ACCESS_TOKEN} | docker login ghcr.io -u USERNAME --password-stdin

# Pull and run the Docker image 
docker run --name gizmo-edge \
           --interactive \
           --rm \
           --tty \
           --init \
           --publish 8765:8765 \
           --pull missing \
           --entrypoint /bin/bash \
           ghcr.io/gizmodata/gizmo-edge:latest
```

### Handy development commands

#### Version management

##### Bump the version of the application - (you must have installed from source with the [dev] extras)
```bash
bumpver update --patch
```
