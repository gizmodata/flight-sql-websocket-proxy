import json
import platform
from typing import TYPE_CHECKING

from munch import Munch
import websockets
from adbc_driver_flightsql import dbapi, DatabaseOptions
from websockets.frames import CloseCode

from .server_query import Query
from ..config import logger

if TYPE_CHECKING:
    from .server_class import Server


class Client:
    def __init__(self,
                 server: "Server",
                 websocket_connection,
                 user: str
                 ):
        self.server = server
        self.websocket_connection = websocket_connection
        self.user = user
        self.client_id = self.websocket_connection.id

        # Get a Database connection
        self.database_connection = None

    async def database_connect(self):
        try:
            self.database_connection = dbapi.connect(uri=self.server.database_server_uri,
                                                     db_kwargs={"username": self.server.database_username,
                                                                "password": self.server.database_password,
                                                                DatabaseOptions.TLS_SKIP_VERIFY.value: str(
                                                                    self.server.database_tls_skip_verify).upper()
                                                                }
                                                     )
        except Exception as e:
            error_message = f"SQL Client Websocket connection: '{self.websocket_connection.id}' - from user: {self.user} - failed to connect to database URI: {self.server.database_server_uri} - error: {str(e)}"
            logger.error(error_message)
            await self.websocket_connection.close(code=CloseCode.INTERNAL_ERROR,
                                                  reason=error_message
                                                  )
        else:
            logger.info(
                f"SQL Client Websocket connection: '{self.websocket_connection.id}' - from user: {self.user} - connected successfully to database URI: {self.server.database_server_uri}")

    async def connect(self):
        logger.info(
            msg=f"SQL Client Websocket connection: '{self.websocket_connection.id}' - from user: {self.user} - connected")

        await self.database_connect()

        await self.websocket_connection.send(
            (f"Client - successfully connected to the Arrow Flight SQL Websocket Proxy server "
             f"\n- version: {self.server.version} "
             f"\n- CPU platform: {platform.machine()} "
             f"\n- TLS: {'Enabled' if self.server.ssl_context else 'Disabled'}"
             f"\n- Websocket client connection ID: '{self.websocket_connection.id}' "
             f"\n- Connection proxied to database server: '{self.database_connection.connection_id}'."
             )
            )

        await self.process_client_commands()

    async def process_client_commands(self):
        try:
            async for message in self.websocket_connection:
                if message:
                    logger.info(msg=f"Message received from client: '{self.client_id}' - '{message}'")

                    query_munch = Munch.munchify(x=json.loads(message))
                    query = Query(sql=query_munch.sql,
                                  parameters=query_munch.parameters,
                                  client=self
                                  )
                    await query.process_query()

        except websockets.exceptions.ConnectionClosedError:
            pass
