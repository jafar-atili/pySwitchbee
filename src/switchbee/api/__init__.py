from __future__ import annotations
from awesomeversion import AwesomeVersion

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
    if AwesomeVersion(str(api.version)) >= AwesomeVersion("1.4.6.1"):
        return True
    return False
