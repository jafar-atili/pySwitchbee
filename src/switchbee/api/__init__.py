from __future__ import annotations

__all__ = ["polling", "wsrpc", "central_unit"]

from .polling import CentralUnitPolling
from .wsrpc import (
    CentralUnitWsRPC,
    DeviceConnectionError,
    InvalidMessage,
    ConnectionClosed,
    CU_WSRPC_VERSION,
    CU_WSRPC_VERSION_A,
)
from .central_unit import (
    SwitchBeeError,
    SwitchBeeTokenError,
    SwitchBeeDeviceOfflineError,
)


def is_wsrpc_api(api: CentralUnitPolling | CentralUnitWsRPC) -> bool:
    assert isinstance(api.version, str)
    if CU_WSRPC_VERSION in api.version or CU_WSRPC_VERSION_A in api.version:
        return True
    return False
