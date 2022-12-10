from __future__ import annotations

import socket
from asyncio import BaseTransport, DatagramProtocol, DatagramTransport, get_running_loop
from dataclasses import dataclass
from json import loads
from logging import getLogger
from types import TracebackType
from typing import Any, Callable, Optional, Type, cast

_LOGGER = getLogger(__name__)


PORT = 8872


@dataclass
class CentralUnit:
    """Central Unit data class."""

    name: str
    version: str
    mac_address: str
    switches: int
    ip_address: str
    external_ip_address: str
    port: int
    timezone: int
    timezone_name: str
    time_str: str
    no_users: bool


class UdpClientProtocol(DatagramProtocol):
    def __init__(self, on_datagram: Callable[[CentralUnit], Any]):
        self.message = "FIND"
        self.transport: DatagramTransport | None = None
        self._on_datagram = on_datagram

    def connection_made(self, transport: BaseTransport) -> None:
        self.transport = cast(DatagramTransport, transport)
        sock = transport.get_extra_info("socket")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broadcast()

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        _LOGGER.debug("Received:", data.decode())
        if data:
            json_data = loads(data.decode())
            json_data["internalIp"] = addr[0]
            self._on_datagram(
                CentralUnit(
                    json_data["name"],
                    json_data["CUVersion"],
                    str(json_data["mac"]).replace("-", ":"),
                    json_data["switches"],
                    addr[0],
                    json_data["ip"],
                    json_data["port"],
                    json_data["timeZone"],
                    json_data["timeZoneName"],
                    json_data["timeStr"],
                    json_data["NoUsers"],
                )
            )

    def error_received(self, exc: Optional[Exception]) -> None:
        _LOGGER.error("Error received:", exc)

    def broadcast(self) -> None:
        _LOGGER.debug("sending:", self.message)
        assert self.transport
        self.transport.sendto(self.message.encode(), ("255.255.255.255", PORT))

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            _LOGGER.critical(f"udp bridge lost its connection {exc}")
        else:
            _LOGGER.info("udp connection stopped")


class CentralUnitFinder:
    def __init__(
        self,
        on_device: Callable[[CentralUnit], Any],
    ) -> None:
        self._on_device = on_device
        self._central_units: dict[str, Any] = {}
        self._transport: BaseTransport | None = None
        self._is_running = False

    async def __aenter__(self) -> "CentralUnitFinder":
        """Enter CentralUnitFinder asynchronous context manager."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Exit the CentralUnitFinder asynchronous context manager."""
        await self.stop()

    async def start(self) -> None:
        """Create an asynchronous listener and start the bridge."""

        _LOGGER.info("starting the udp bridge on port %s", PORT)

        transport, protocol = await get_running_loop().create_datagram_endpoint(
            lambda: UdpClientProtocol(self._on_device),
            family=socket.AF_INET,
        )
        self._transport = transport
        _LOGGER.debug("udp bridge on port %s started", PORT)

        self._is_running = True

    async def stop(self) -> None:
        """Stop the asynchronous bridge."""

        if self._transport and not self._transport.is_closing():
            _LOGGER.info("stopping the udp bridge on port %s", PORT)
            self._transport.close()
        else:
            _LOGGER.info("udp bridge on port %s not started", PORT)

        self._is_running = False
