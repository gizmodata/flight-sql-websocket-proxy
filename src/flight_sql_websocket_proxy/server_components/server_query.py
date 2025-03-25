import functools
import json
import uuid
from datetime import datetime, UTC
from typing import List, Optional
from typing import TYPE_CHECKING

from adbc_driver_manager.dbapi import Connection

from ..config import logger
from ..utils import get_dataframe_results_as_ipc_base64_str

if TYPE_CHECKING:
    from .server_client import Client


class Query:
    def __init__(self,
                 action: str,
                 client: "Client",
                 sql: str,
                 parameters: Optional[List[str]] = None,
                 ):
        self.action = action
        self.client = client
        self.query_id = uuid.uuid4()
        self.sql = sql
        self.parameters = parameters
        self.start_time = datetime.now(tz=UTC).isoformat()
        self.end_time = None

    async def send_results_to_client(self, result_base64_str):
        self.end_time = datetime.now(tz=UTC).isoformat()
        success_message = f"Query: '{self.query_id}' - execution elapsed time: {str(datetime.fromisoformat(self.end_time) - datetime.fromisoformat(self.start_time))}"
        message_dict = dict(kind="queryResult",
                            responseTo=self.action,
                            success=True,
                            message=success_message,
                            data=result_base64_str
                            )
        await self.client.websocket_connection.send(json.dumps(message_dict))
        logger.info(
            msg=f"Sent Query: '{self.query_id}' results (size: {len(result_base64_str)}) to SQL "
                f"Client: '{self.client.client_id}'"
        )

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
            return get_dataframe_results_as_ipc_base64_str(df=results)

    async def run_query_async(self):
        await self.client.check_if_authenticated()

        try:
            partial_run_query = functools.partial(self.run_query,
                                                  database_connection=self.client.database_connection,
                                                  sql=self.sql,
                                                  parameters=self.parameters
                                                  )

            result_base64_str = await self.client.server.event_loop.run_in_executor(
                executor=self.client.server.thread_pool,
                func=partial_run_query
            )
        except Exception as e:
            error_message = f"Query: {self.sql} - FAILED on the server - with error: '{str(e)}'"
            message_dict = dict(kind="queryResult",
                                responseTo=self.action,
                                success=False,
                                error=error_message,
                                data=None
                                )
            await self.client.websocket_connection.send(json.dumps(message_dict))
        else:
            await self.send_results_to_client(result_base64_str)

    async def process_query(self):
        await self.run_query_async()
