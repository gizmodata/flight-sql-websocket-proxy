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
                 action: str,
                 client: "Client",
                 sql: str,
                 parameters: Optional[List[str]] = None,
                 ):
        self.action = action
        self.client = client
        self.query_id = uuid.uuid4()
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
                                responseTo=self.action,
                                success=False,
                                error=error_message
                                )
            await self.client.websocket_connection.send(json.dumps(message_dict))
        else:
            self.executed = True
            self.end_time = datetime.now(tz=UTC).isoformat()
            success_message = f"Query: '{self.query_id}' - execution elapsed time: {str(datetime.fromisoformat(self.end_time) - datetime.fromisoformat(self.start_time))}"

            message_dict = dict(kind="queryResult",
                                responseTo=self.action,
                                success=True,
                                message=success_message,
                                query_id=str(self.query_id)
                                )
            await self.client.websocket_connection.send(json.dumps(message_dict))

    @classmethod
    def fetch_results(cls,
                      record_batch_reader: RecordBatchReader
                      ) -> tuple[None, int] | tuple[str, int]:
        try:
            arrow_table: pyarrow.Table = pyarrow.Table.from_batches(batches=[record_batch_reader.read_next_batch()])

            return get_dataframe_results_as_ipc_base64_str(df=arrow_table), arrow_table.num_rows
        except StopIteration:
            return None, int(0)

    async def fetch_results_async(self):
        await self.client.check_if_authenticated()

        if not self.executed:
            error_message = f"Query: '{self.query_id}' - has not been executed yet - cannot fetch results..."
            message_dict = dict(kind="fetchResult",
                                responseTo=self.action,
                                success=False,
                                error=error_message,
                                data=None
                                )
            await self.client.websocket_connection.send(json.dumps(message_dict))
            return
        elif self.all_rows_fetched:
            message_dict = dict(kind="fetchResult",
                                responseTo=self.action,
                                success=True,
                                message=f"Query: '{self.query_id}' - all rows have already been fetched...",
                                batch_rows_fetched=0,
                                total_rows_fetched=self.rows_fetched,
                                all_rows_fetched=True,
                                data=None
                                )
            await self.client.websocket_connection.send(json.dumps(message_dict))
            return

        message_dict = dict()
        try:
            partial_fetch_results = functools.partial(self.fetch_results,
                                                      record_batch_reader=self.record_batch_reader,
                                                      )

            result_base64_str, batch_rows_fetched = await self.client.server.event_loop.run_in_executor(
                executor=self.client.server.thread_pool,
                func=partial_fetch_results
            )

            self.rows_fetched += batch_rows_fetched

        except Exception as e:
            error_message = f"Fetch for Query ID: {self.query_id} - FAILED on the server - with error: '{str(e)}'"
            message_dict = dict(kind="fetchResult",
                                responseTo=self.action,
                                success=False,
                                error=error_message,
                                data=None
                                )
        else:
            if batch_rows_fetched > 0:
                success_message = f"Query: '{self.query_id}' - fetched {batch_rows_fetched} row(s) - total fetched thus far: {self.rows_fetched}"
                message_dict = dict(kind="fetchResult",
                                    responseTo=self.action,
                                    success=True,
                                    message=success_message,
                                    batch_rows_fetched=batch_rows_fetched,
                                    total_rows_fetched=self.rows_fetched,
                                    all_rows_fetched=False,
                                    data=result_base64_str
                                    )
            else:
                self.all_rows_fetched = True
                message_dict = dict(kind="fetchResult",
                                    responseTo=self.action,
                                    success=True,
                                    message=f"Query: '{self.query_id}' - no more rows to fetch - total fetched: {self.rows_fetched}",
                                    batch_rows_fetched=0,
                                    total_rows_fetched=self.rows_fetched,
                                    all_rows_fetched=True,
                                    data=None
                                    )
                await self.close_cursor()
        finally:
            await self.client.websocket_connection.send(json.dumps(message_dict))
            logger.info(
                msg=f"Sent Query: '{self.query_id}' Fetch results (size: {getsizeof(message_dict)}) to SQL "
                    f"Client: '{self.client.client_id}'"
            )
