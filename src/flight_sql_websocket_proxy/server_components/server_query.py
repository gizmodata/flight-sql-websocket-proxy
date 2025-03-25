import functools
import uuid
from datetime import datetime, UTC
from typing import List, Optional
from typing import TYPE_CHECKING

import pyarrow
from adbc_driver_manager.dbapi import Connection

from ..utils import get_dataframe_ipc_bytes
from ..config import logger

if TYPE_CHECKING:
    from .server_client import Client


class Query:
    def __init__(self,
                 client: "Client",
                 sql: str,
                 parameters: Optional[List[str]] = None,
                 ):
        self.client = client
        self.query_id = uuid.uuid4()
        self.sql = sql
        self.parameters = parameters
        self.start_time = datetime.now(tz=UTC).isoformat()
        self.end_time = None

    async def send_results_to_client(self, result_bytes):
        await self.client.websocket_connection.send(result_bytes)
        self.end_time = datetime.now(tz=UTC).isoformat()
        await self.client.websocket_connection.send(
            f"Query: '{self.query_id}' - execution elapsed time: {str(datetime.fromisoformat(self.end_time) - datetime.fromisoformat(self.start_time))}"
        )
        logger.info(
            msg=f"Sent Query: '{self.query_id}' results (size: {len(result_bytes)}) to SQL "
                f"Client: '{self.client.client_id}'")

    @classmethod
    def run_query(cls,
                  database_connection: Connection,
                  sql: str,
                  parameters: Optional[List[str]] = None
                  ):
        with database_connection.cursor() as cursor:
            cursor.execute(operation=sql,
                           parameters=parameters
                           )

            results = cursor.fetch_arrow_table()
            return get_dataframe_ipc_bytes(df=results)

    async def run_query_async(self):
        try:
            partial_run_query = functools.partial(self.run_query,
                                                  database_connection=self.client.database_connection,
                                                  sql=self.sql,
                                                  parameters=self.parameters
                                                  )

            result_bytes = await self.client.server.event_loop.run_in_executor(
                executor=self.client.server.process_pool,
                func=partial_run_query
            )
        except Exception as e:
            error_message = str(e)
            await self.client.websocket_connection.send(
                f"Query: {self.sql} - FAILED on the server - with error: '{error_message}'")
        else:
            await self.send_results_to_client(result_bytes)

    async def process_query(self):
        await self.run_query_async()
