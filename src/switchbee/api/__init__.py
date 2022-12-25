__all__ = ["polling", "wsrpc", "central_unit"]

from .polling import CentralUnitPolling
from .wsrpc import (
    CentralUnitWsRPC,
    DeviceConnectionError,
    InvalidMessage,
    ConnectionClosed,
    CU_WSRPC_VERSION,
)
from .central_unit import (
    SwitchBeeError,
    SwitchBeeTokenError,
    SwitchBeeDeviceOfflineError,
)


def is_wsrpc_api(api: CentralUnitPolling | CentralUnitWsRPC) -> bool:
    assert isinstance(api.version, str)
    if CU_WSRPC_VERSION in api.version:
        return True
    return False
