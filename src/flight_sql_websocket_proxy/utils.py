import asyncio
import base64
import hashlib
import os
import re
import shutil
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import List, Tuple

import psutil
import pyarrow
from codetiming import Timer
from dotenv import load_dotenv
from munch import Munch
from pyarrow import parquet as pq

from .config import logger

# Load our environment file if it is present
load_dotenv(dotenv_path=".env")

# taken from: https://donghao.org/2022/01/20/how-to-get-the-number-of-cpu-cores-inside-a-container/
def get_cpu_count():
    if os.path.isfile("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"):
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us") as fp:
            cfs_quota_us = int(fp.read())
        with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us") as fp:
            cfs_period_us = int(fp.read())
        container_cpus = cfs_quota_us // cfs_period_us
        # For physical machine, the `cfs_quota_us` could be '-1'
        cpus = os.cpu_count() if container_cpus < 1 else container_cpus
    else:
        cpus = os.cpu_count()

    return cpus


def get_memory_limit():
    if os.path.isfile('/sys/fs/cgroup/memory/memory.limit_in_bytes'):
        with open('/sys/fs/cgroup/memory/memory.limit_in_bytes') as limit:
            memory_limit = int(limit.read())
    else:
        memory_limit = psutil.virtual_memory().total

    return memory_limit


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def get_dataframe_from_ipc_bytes(bytes_value: bytes) -> pyarrow.Table:
    return pyarrow.ipc.open_stream(bytes_value).read_all()

def get_dataframe_from_ipc_base64_str(base64_str: str) -> pyarrow.Table:
    return get_dataframe_from_ipc_bytes(base64.b64decode(base64_str))

def get_dataframe_from_parquet_bytes(bytes_value: bytes) -> pyarrow.Table:
    return pq.read_table(source=pyarrow.BufferReader(pyarrow.py_buffer(bytes_value)))


def get_dataframe_ipc_bytes(df: pyarrow.Table) -> bytes:
    sink = pyarrow.BufferOutputStream()
    with pyarrow.ipc.new_stream(sink, df.schema) as writer:
        writer.write(df)
    buf = sink.getvalue()
    return buf.to_pybytes()


def get_dataframe_results_as_ipc_base64_str(df: pyarrow.Table) -> str:
    return base64.b64encode(get_dataframe_ipc_bytes(df)).decode()
