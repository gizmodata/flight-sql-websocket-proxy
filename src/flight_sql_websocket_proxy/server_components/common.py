from enum import StrEnum, auto

from .. import __version__ as arrow_flight_sql_websocket_proxy_server_version

# Misc. Constants
ARROW_FLIGHT_SQL_WEBSOCKET_PROXY_SERVER_VERSION = arrow_flight_sql_websocket_proxy_server_version


class DistributeMode(StrEnum):
    TRUE = auto()
    FALSE = auto()
    FORCE = auto()
