import json
import platform
from typing import TYPE_CHECKING

import websockets
from adbc_driver_flightsql import dbapi, DatabaseOptions
from munch import munchify, Munch
from websockets.frames import CloseCode

from .server_query import Query
from ..config import logger
from ..security import authenticate_user

if TYPE_CHECKING:
    from .server_class import Server


class Client:
    def __init__(self,
                 server: "Server",
                 websocket_connection
                 ):
        self.server = server
        self.websocket_connection = websocket_connection
        self.client_id = self.websocket_connection.id
        self.authenticated = False
        self.user = None
        self.database_connection = None
        self.queries = {}

    async def get_user(self, token: str):
        try:
            # Verify the token - and get the username
            authenticated_user = await authenticate_user(oauth2_secret_key=self.server.clerk_secret_key,
                                                         jwks_url=self.server.jwks_url,
                                                         session_token_issuer=self.server.session_token_issuer,
                                                         user_token=token
                                                         )
            return authenticated_user, None
        except Exception as e:
            logger.exception(msg=str(e))
            return None, str(e)

    async def authenticate_client(self,
                                  message: Munch
                                  ):
        user, auth_error_message = await self.get_user(message.token)
        if user is None:
            error_message = f"Authentication failed for websocket: '{self.websocket_connection.id}' - error: {auth_error_message}"
            logger.warning(msg=error_message)
            message_dict = dict(kind="error",
                                responseTo=message.action,
                                success=False,
                                error=error_message
                                )
            await self.websocket_connection.send(json.dumps(message_dict))
            try:
                await self.websocket_connection.close(code=CloseCode.INTERNAL_ERROR,
                                                      reason=error_message
                                                      )
            except:
                pass

            return
        else:
            success_message = f"User: '{user}' successfully authenticated for websocket: '{self.websocket_connection.id}'"
            self.user = user
            self.authenticated = True
            await self.database_connect(autocommit=message.autocommit)
            message_dict = dict(kind="message",
                                responseTo=message.action,
                                success=True,
                                message=success_message
                                )
            logger.info(msg=success_message)
            await self.websocket_connection.send(json.dumps(message_dict))

    async def check_if_authenticated(self):
        if not self.authenticated:
            error_message = f"SQL Client Websocket connection: '{self.websocket_connection.id}' - is NOT authenticated!"
            logger.error(error_message)
            try:
                await self.websocket_connection.close(code=CloseCode.POLICY_VIOLATION,
                                                      reason=error_message
                                                      )
            except:
                pass

    async def database_connect(self,
                               autocommit: bool
                               ):
        await self.check_if_authenticated()
        try:
            self.database_connection = dbapi.connect(uri=self.server.database_server_uri,
                                                     db_kwargs={"username": self.server.database_username,
                                                                "password": self.server.database_password,
                                                                DatabaseOptions.TLS_SKIP_VERIFY.value: str(
                                                                    self.server.database_tls_skip_verify).lower()
                                                                },
                                                     autocommit=autocommit
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
            msg=f"SQL Client Websocket connection: '{self.websocket_connection.id}' - initiated...")

        message_dict = dict(kind="message",
                            success=True,
                            message=(f"Client - successfully connected to the Arrow Flight SQL Websocket Proxy server "
                                     f"\n- version: {self.server.version} "
                                     f"\n- CPU platform: {platform.machine()} "
                                     f"\n- TLS: {'Enabled' if self.server.ssl_context else 'Disabled'}"
                                     f"\n- Websocket client connection ID: '{self.websocket_connection.id}' "
                                     f"\n- Connection proxied to database server: '{self.server.database_server_uri}'"
                                     )
                            )
        await self.websocket_connection.send(json.dumps(message_dict))

        await self.process_client_commands()

    async def process_client_commands(self):
        try:
            async for raw_message in self.websocket_connection:
                if raw_message:
                    logger.info(msg=f"Message received from client: '{self.client_id}' (User: {self.user or '(not authenticated)'}) - '{raw_message}'")

                    message = munchify(x=json.loads(raw_message))

                    if message.action == "authenticate":
                        await self.authenticate_client(message)
                    elif message.action == "query":
                        query = Query(sql=message.sql,
                                      parameters=message.parameters,
                                      client=self
                                      )
                        await query.run_query_async()
                        self.queries[query.query_id] = query
                    elif message.action in ["fetch", "closeCursor"]:
                        if message.query_id not in self.queries:
                            error_message = f"Query ID: '{message.query_id}' - does NOT exist for client: '{self.client_id}'"
                            logger.error(error_message)
                            message_dict = dict(kind="error",
                                                responseTo=message.action,
                                                success=False,
                                                error=error_message
                                                )
                            await self.websocket_connection.send(json.dumps(message_dict))
                        if message.action == "fetch":
                            await self.queries[message.query_id].fetch_results_async(fetch_mode=message.fetch_mode,
                                                                                     fetch_size=message.get("fetch_size", self.server.client_default_fetch_size)
                                                                                     )
                        elif message.action == "closeCursor":
                            await self.queries[message.query_id].close_cursor()

        except websockets.exceptions.ConnectionClosedError:
            pass
