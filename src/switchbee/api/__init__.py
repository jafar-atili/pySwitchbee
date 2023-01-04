from __future__ import annotations
from packaging.version import parse as parse_version

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
    if parse_version(str(CUVersion)) >= parse_version("1.4.6.1"):
        return True
    return False
