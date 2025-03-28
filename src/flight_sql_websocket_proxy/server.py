import os
from pathlib import Path

import click
from dotenv import load_dotenv

from . import __version__ as arrow_flight_sql_websocket_proxy_server_version
from .constants import DEFAULT_MAX_WEBSOCKET_MESSAGE_SIZE, DEFAULT_CLIENT_FETCH_SIZE, \
    SERVER_PORT
from .server_components.server_class import Server
from .setup.tls_utilities import DEFAULT_CERT_FILE, DEFAULT_KEY_FILE
from .utils import coro, get_cpu_count, \
    get_memory_limit

# Load our environment file if it is present
load_dotenv(dotenv_path=".env")


@click.command()
@click.option(
    "--version/--no-version",
    type=bool,
    default=False,
    show_default=False,
    required=True,
    help="Prints the Arrow Flight SQL WebSocket Proxy Server version and exits."
)
@click.option(
    "--port",
    type=int,
    default=os.getenv("SERVER_PORT", SERVER_PORT),
    show_default=True,
    required=True,
    help="Run the websocket server on this port."
)
@click.option(
    "--tls",
    nargs=2,
    default=os.getenv("TLS").split(" ") if os.getenv("TLS") else [DEFAULT_CERT_FILE, DEFAULT_KEY_FILE],
    required=False,
    metavar=('CERTFILE', 'KEYFILE'),
    help="Enable transport-level security (TLS/SSL).  Provide a Certificate file path, and a Key file path - separated by a space.  Example: tls/server.crt tls/server.key"
)
@click.option(
    "--database-server-uri",
    type=str,
    default=os.getenv("DATABASE_SERVER_URI", "grpc+tls://localhost:31337"),
    show_default=True,
    required=True,
    help="The URI of the Arrow Flight SQL server."
)
@click.option(
    "--database-username",
    type=str,
    default=os.getenv("DATABASE_USERNAME", "gizmosql_username"),
    show_default=True,
    required=True,
    help="The username to authenticate with the Arrow Flight SQL server."
)
@click.option(
    "--database-password",
    type=str,
    default=os.getenv("DATABASE_PASSWORD"),
    show_default=False,
    required=True,
    help="The password to authenticate with the Arrow Flight SQL server."
)
@click.option(
    "--database-tls-skip-verify/--no-database-tls-skip-verify",
    type=bool,
    default=(os.getenv("DATABASE_TLS_SKIP_VERIFY").upper() == "TRUE"),
    show_default=True,
    required=True,
    help="Skip TLS verification of the Arrow Flight SQL server."
)
@click.option(
    "--clerk-api-url",
    type=str,
    default=os.getenv("CLERK_API_URL", "https://api.clerk.dev"),
    show_default=True,
    required=True,
    help="The CLERK API URL - for user authentication."
)
@click.option(
    "--clerk-secret-key",
    type=str,
    default=os.getenv("CLERK_SECRET_KEY"),
    show_default=False,
    required=True,
    help="The CLERK Secret Key - for user authentication."
)
@click.option(
    "--jwks-url",
    type=str,
    default=os.getenv("JWKS_URL"),
    show_default=True,
    required=True,
    help="The JWKS URL used for client session JWT token validation - for user authentication."
)
@click.option(
    "--session-token-issuer",
    type=str,
    default=os.getenv("SESSION_TOKEN_ISSUER"),
    show_default=True,
    required=True,
    help="The issuer used for client session JWT token validation - for user authentication."
)
@click.option(
    "--max-process-workers",
    type=int,
    default=os.getenv("MAX_PROCESS_WORKERS", get_cpu_count()),
    show_default=True,
    required=True,
    help="Max process workers"
)
@click.option(
    "--websocket-ping-timeout",
    type=int,
    default=os.getenv("PING_TIMEOUT", 60),
    show_default=True,
    required=True,
    help="Web-socket ping timeout"
)
@click.option(
    "--max-websocket-message-size",
    type=int,
    default=DEFAULT_MAX_WEBSOCKET_MESSAGE_SIZE,
    show_default=True,
    required=True,
    help="Maximum Websocket message size"
)
@click.option(
    "--client-default-fetch-size",
    type=int,
    default=DEFAULT_CLIENT_FETCH_SIZE,
    show_default=True,
    required=True,
    help="The default websocket client fetch size for queries."
)
@coro
async def main(version: bool,
               port: int,
               tls: list,
               database_server_uri: str,
               database_username: str,
               database_password: str,
               database_tls_skip_verify: bool,
               clerk_api_url: str,
               clerk_secret_key: str,
               jwks_url: str,
               session_token_issuer: str,
               max_process_workers: int,
               websocket_ping_timeout: int,
               max_websocket_message_size: int,
               client_default_fetch_size: int
               ):
    if version:
        print(f"Arrow Flight SQL Websocket Proxy Server - version: {arrow_flight_sql_websocket_proxy_server_version}")
        return

    tls_certfile = None
    tls_keyfile = None
    if tls:
        tls_certfile = Path(tls[0])
        tls_keyfile = Path(tls[1])

    await Server(port=port,
                 tls_certfile=tls_certfile,
                 tls_keyfile=tls_keyfile,
                 database_server_uri=database_server_uri,
                 database_username=database_username,
                 database_password=database_password,
                 database_tls_skip_verify=database_tls_skip_verify,
                 clerk_api_url=clerk_api_url,
                 clerk_secret_key=clerk_secret_key,
                 jwks_url=jwks_url,
                 session_token_issuer=session_token_issuer,
                 max_process_workers=max_process_workers,
                 websocket_ping_timeout=websocket_ping_timeout,
                 max_websocket_message_size=max_websocket_message_size,
                 client_default_fetch_size=client_default_fetch_size
                 ).run()


if __name__ == "__main__":
    main()
