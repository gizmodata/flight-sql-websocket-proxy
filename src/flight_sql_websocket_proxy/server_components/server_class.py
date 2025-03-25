from __future__ import annotations

import asyncio
import functools
import platform
import re
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path

import websockets
from munch import Munch
from websockets.frames import CloseCode
import adbc_driver_flightsql

from .server_client import Client
from .common import ARROW_FLIGHT_SQL_WEBSOCKET_PROXY_SERVER_VERSION
from ..config import logger


class Server:
    def __init__(self,
                 port: int,
                 tls_certfile: Path,
                 tls_keyfile: Path,
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
                 max_websocket_message_size: int
                 ):
        self.port = port
        self.tls_certfile = tls_certfile
        self.tls_keyfile = tls_keyfile
        self.database_server_uri = database_server_uri
        self.database_username = database_username
        self.database_password = database_password
        self.database_tls_skip_verify = database_tls_skip_verify
        self.clerk_api_url = clerk_api_url
        self.clerk_secret_key = clerk_secret_key
        self.jwks_url = jwks_url
        self.session_token_issuer = session_token_issuer
        self.max_process_workers = max_process_workers
        self.websocket_ping_timeout = websocket_ping_timeout
        self.max_websocket_message_size = max_websocket_message_size

        self.lock = asyncio.Lock()
        self.client_connections = Munch()
        self.version = ARROW_FLIGHT_SQL_WEBSOCKET_PROXY_SERVER_VERSION

        # Setup TLS/SSL
        self.ssl_context = None
        if self.tls_certfile and self.tls_keyfile:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.load_cert_chain(certfile=self.tls_certfile, keyfile=self.tls_keyfile)

        # Asynch stuff
        self.event_loop = asyncio.get_event_loop()
        self.event_loop.set_default_executor(ThreadPoolExecutor())
        self.process_pool = ProcessPoolExecutor(max_workers=self.max_process_workers)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_process_workers)
        self.bound_handler = functools.partial(self.connection_handler)

    async def run(self):
        logger.info(
            msg=(f"Starting Arrow Flight SQL Websocket Proxy Server - version: {self.version} - (\n"
                 f" port: {self.port},\n"
                 f" tls_certfile: {self.tls_certfile.as_posix() if self.tls_certfile else 'None'},\n"
                 f" tls_keyfile: {self.tls_keyfile.as_posix() if self.tls_keyfile else 'None'},\n"
                 f" database_server_uri: {self.database_server_uri},\n"
                 f" database_tls_skip_verify: {self.database_tls_skip_verify},\n"
                 f" clerk_api_url: {self.clerk_api_url},\n"
                 f" max_process_workers: {self.max_process_workers},\n"
                 f" websocket_ping_timeout: {self.websocket_ping_timeout},\n"
                 f" max_websocket_message_size: {self.max_websocket_message_size}\n"
                 f")"
                 )
        )
        logger.info(f"Running on CPU Platform: {platform.machine()}")
        logger.info(f"Using Python version: {sys.version}")
        logger.info(f"Using Websockets version: {websockets.__version__}")
        logger.info(f"Using ADBC Flight SQL driver version: {adbc_driver_flightsql.__version__}")
        logger.info(f"TLS: {'Enabled' if self.ssl_context else 'Disabled'}")

        async with websockets.serve(handler=self.bound_handler,
                                    host="0.0.0.0",
                                    port=self.port,
                                    max_size=self.max_websocket_message_size,
                                    ping_timeout=self.websocket_ping_timeout,
                                    ssl=self.ssl_context
                                    ):
            await asyncio.Future()  # run forever

    async def connection_handler(self, websocket):
        if websocket.request.path == "/client":
            await self.client_handler(client_websocket=websocket)
        else:
            # No handler for this path; close the connection.
            return

    async def client_handler(self, client_websocket):
        client = Client(server=self,
                        websocket_connection=client_websocket
                        )
        self.client_connections[client.client_id] = client
        await client.connect()
