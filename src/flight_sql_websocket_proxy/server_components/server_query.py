import functools
import json
import uuid
from datetime import datetime, UTC
from sys import getsizeof
from typing import List, Optional
from typing import TYPE_CHECKING

import pyarrow
from adbc_driver_manager.dbapi import Cursor
from pyarrow import RecordBatchReader

from ..config import logger
from ..utils import get_dataframe_results_as_ipc_base64_str

if TYPE_CHECKING:
    from .server_client import Client


class Query:
    def __init__(self,
                 client: "Client",
                 sql: str,
                 parameters: Optional[List[str]] = None,
                 ):
        self.client = client
        self.query_id = str(uuid.uuid4())
        self.cursor: Cursor = self.client.database_connection.cursor()
        self.record_batch_reader: RecordBatchReader = None
        self.results = None
        self.sql = sql
        self.parameters = parameters
        self.start_time = datetime.now(tz=UTC).isoformat()
        self.end_time = None
        self.rows_fetched: int = 0
        self.executed: bool = False
        self.all_rows_fetched: bool = False

    def __del__(self):
        if self.cursor:
            self.cursor.close()

    async def close_cursor(self):
        if self.cursor:
            self.cursor.close()

        if self.query_id in self.client.queries:
            del self.client.queries[self.query_id]

    @classmethod
    def run_query(cls,
                  cursor: Cursor,
                  sql: str,
                  parameters: Optional[List[str]] = None
                  ):
        cursor.execute(operation=sql,
                       parameters=parameters
                       )

        return cursor.fetch_record_batch()

    async def run_query_async(self):
        await self.client.check_if_authenticated()

        try:
            partial_run_query = functools.partial(self.run_query,
                                                  cursor=self.cursor,
                                                  sql=self.sql,
                                                  parameters=self.parameters
                                                  )

            self.record_batch_reader = await self.client.server.event_loop.run_in_executor(
                executor=self.client.server.thread_pool,
                func=partial_run_query
            )
        except Exception as e:
            error_message = f"Query: {self.sql} - FAILED on the server - with error: '{str(e)}'"
            message_dict = dict(kind="queryResult",
                                responseTo="query",
                                success=False,
                                error=error_message,
                                query_id=self.query_id
                                )
            await self.client.websocket_connection.send(json.dumps(message_dict))
        else:
            self.executed = True
            self.end_time = datetime.now(tz=UTC).isoformat()
            success_message = f"Query: '{self.query_id}' - execution elapsed time: {str(datetime.fromisoformat(self.end_time) - datetime.fromisoformat(self.start_time))}"

            message_dict = dict(kind="queryResult",
                                responseTo="query",
                                success=True,
                                message=success_message,
                                query_id=self.query_id
                                )
            await self.client.websocket_connection.send(json.dumps(message_dict))

    @classmethod
    def fetch_results(cls,
                      record_batch_reader: RecordBatchReader,
                      fetch_mode: str
                      ) -> tuple[None, int, bool] | tuple[str, int, bool]:
        try:
            if fetch_mode == "all":
                arrow_table: pyarrow.Table = record_batch_reader.read_all()
                all_rows_fetched = True
            elif fetch_mode == "batch":
                arrow_table: pyarrow.Table = pyarrow.Table.from_batches(batches=[record_batch_reader.read_next_batch()])
                all_rows_fetched = (arrow_table.num_rows == 0)
            else:
                raise ValueError(f"Invalid fetch mode: '{fetch_mode}' - must be one of: 'all' or 'batch'")

            return get_dataframe_results_as_ipc_base64_str(df=arrow_table), arrow_table.num_rows, all_rows_fetched
        except StopIteration:
            return None, int(0), True

    async def fetch_results_async(self,
                                  fetch_mode: str
                                  ):
        await self.client.check_if_authenticated()

        if not self.executed:
            error_message = f"Query: '{self.query_id}' - has not been executed yet - cannot fetch results..."
            message_dict = dict(kind="fetchResult",
                                responseTo="fetch",
                                query_id=self.query_id,
                                success=False,
                                error=error_message,
                                data=None
                                )
            await self.client.websocket_connection.send(json.dumps(message_dict))
            return

        message_dict = dict()
        try:
            partial_fetch_results = functools.partial(self.fetch_results,
                                                      record_batch_reader=self.record_batch_reader,
                                                      fetch_mode=fetch_mode
                                                      )

            result_base64_str, batch_rows_fetched, self.all_rows_fetched = await self.client.server.event_loop.run_in_executor(
                executor=self.client.server.thread_pool,
                func=partial_fetch_results
            )

            self.rows_fetched += batch_rows_fetched

        except Exception as e:
            error_message = f"Fetch for Query ID: {self.query_id} - FAILED on the server - with error: '{str(e)}'"
            message_dict = dict(kind="fetchResult",
                                responseTo="fetch",
                                query_id=self.query_id,
                                success=False,
                                error=error_message,
                                data=None
                                )
        else:
            success_message = f"Query: '{self.query_id}' - fetched {batch_rows_fetched} row(s) - total fetched thus far: {self.rows_fetched}"
            message_dict = dict(kind="fetchResult",
                                responseTo="fetch",
                                query_id=self.query_id,
                                success=True,
                                message=success_message,
                                batch_rows_fetched=batch_rows_fetched,
                                total_rows_fetched=self.rows_fetched,
                                all_rows_fetched=self.all_rows_fetched,
                                data=result_base64_str
                                )

            if self.all_rows_fetched:
                await self.close_cursor()
        finally:
            await self.client.websocket_connection.send(json.dumps(message_dict))
            logger.info(
                msg=f"Sent Query: '{self.query_id}' Fetch results (size: {getsizeof(message_dict)}) to SQL "
                    f"Client: '{self.client.client_id}'"
            )
