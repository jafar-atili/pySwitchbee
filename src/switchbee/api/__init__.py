from __future__ import annotations

__all__ = ["polling", "wsrpc", "central_unit"]

from .polling import CentralUnitPolling
from .wsrpc import (
    CentralUnitWsRPC,
    DeviceConnectionError,
    InvalidMessage,
    ConnectionClosed,
)

from .central_unit import (
    SwitchBeeError,
    SwitchBeeTokenError,
    SwitchBeeDeviceOfflineError,
    CUVersion,
)


def is_wsrpc_api(api: CentralUnitPolling | CentralUnitWsRPC) -> bool:
    assert isinstance(api.version, CUVersion)
    if api.version.minor >= 4 and api.version.revision >= 6:
        return True
    return False
