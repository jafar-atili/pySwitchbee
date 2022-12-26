from __future__ import annotations

from asyncio import Future, TimeoutError, create_task, tasks
from dataclasses import dataclass
from logging import getLogger
from typing import Any, Callable
from .central_unit import CentralUnitAPI, SwitchBeeError

import async_timeout
from aiohttp import ClientSession, ClientWebSocketResponse, WSMessage, WSMsgType
from aiohttp.client_exceptions import ClientError, WSServerHandshakeError
from switchbee.const import ApiAttribute, ApiCommand


logger = getLogger(__name__)


class DeviceConnectionError(Exception):
    pass


class InvalidMessage(Exception):
    pass


class ConnectionClosed(Exception):
    pass


async def receive_json_or_raise(msg: WSMessage) -> dict[str, Any]:
    """Receive json or raise."""
    if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
        raise ConnectionClosed("Connection was closed.")

    if msg.type == WSMsgType.ERROR:
        raise InvalidMessage("Received message error")

    if msg.type != WSMsgType.TEXT:
        raise InvalidMessage(f"Received non-Text message: {msg.type}")

    try:
        data: dict[str, Any] = msg.json()
    except ValueError as err:
        raise InvalidMessage(f"Received invalid JSON: {msg.data}") from err

    if status := data.get("status") == "ERROR":
        raise SwitchBeeError("Response Error: %s", data)

    return data


@dataclass
class SessionData:
    """SessionData (src/dst/auth) class."""

    src: str | None
    dst: str | None
    auth: dict[str, Any] | None


class RPCCall:
    """RPCCall class."""

    def __init__(
        self,
        call_id: int,
        command: str | None,
        params: dict[str, Any] | int | list | None,
        token: str | None,
        session: SessionData,
    ):
        """Initialize RPC class."""
        self.auth = session.auth
        self.call_id = call_id
        self.command = command
        self.params = params
        self.token = token
        self.src = session.src
        self.dst = session.dst
        self.resolve: Future = Future()

    @property
    def request_frame(self) -> dict[str, Any]:
        """Request frame."""
        msg: dict[str, Any] = {"commandId": self.call_id, "command": self.command}

        if self.params:
            msg["params"] = self.params

        if self.token:
            msg["token"] = self.token

        return msg


class CentralUnitWsRPC(CentralUnitAPI):
    def __init__(
        self,
        ip_address: str,
        user_name: str,
        password: str,
        aiohttp_session: ClientSession,
        on_notification: Callable | None = None,
    ) -> None:
        super().__init__(ip_address, user_name, password, aiohttp_session)

        self._client: ClientWebSocketResponse | None = None
        self._receive_task: tasks.Task[None] | None = None
        self._calls: dict[int, RPCCall] = {}
        self._on_notification = on_notification
        self._call_id = 0
        self._session = SessionData(f"swb-{id(self)}", None, None)

    @property
    def connected(self) -> bool:
        """Return if we're currently connected."""
        return self._client is not None and not self._client.closed

    @property
    def _next_id(self) -> int:
        self._call_id += 1
        return self._call_id

    def subscribe_updates(self, callback: Callable) -> None:
        self._on_notification = callback

    async def connect(self) -> None:
        if self.connected:
            raise RuntimeError("Already connected")

        logger.debug("Trying to connect to device at %s", self._ip_address)
        try:
            self._client = await self._aiohttp_session.ws_connect(
                f"http://{self._ip_address}:7891"
            )
        except (
            WSServerHandshakeError,
            ClientError,
        ) as err:
            raise DeviceConnectionError(err) from err

        except TimeoutError as err:
            raise DeviceConnectionError(err) from err

        self._receive_task = create_task(self._rx_msgs())
        await self._login()
        await self.fetch_configuration()
        await self.fetch_states()
        logger.info("Connected to %s", self._ip_address)

    async def _send_json(self, data: dict[str, Any]) -> None:
        """Send json frame to device."""
        logger.debug("send(%s): %s", self._ip_address, data)
        assert self._client
        await self._client.send_json(data)

    async def _rx_msgs(self) -> None:
        assert self._client

        while not self._client.closed:
            try:
                msg = await self._client.receive()
                frame = await receive_json_or_raise(msg)
                logger.debug("recv(%s): %s", self._ip_address, frame)
            except InvalidMessage as err:
                logger.error(
                    "Invalid Message from central unit %s: %s", self._ip_address, err
                )
            except ConnectionClosed:
                break

            except SwitchBeeError as err:
                logger.error(
                    "Response error from central unit %s: %s", self._ip_address, err
                )

            if not self._client.closed:
                self.handle_frame(frame)

        logger.debug("Websocket client connection from %s closed", self._ip_address)

        for call_item in self._calls.values():
            call_item.resolve.cancel()
        self._calls.clear()

        if not self._client.closed:
            await self._client.close()

        self._client = None

    def handle_frame(self, frame: dict[str, Any]) -> None:
        """Handle RPC frame."""

        if command_id := frame.get("commandId"):
            # looks like a response
            if command_id not in self._calls:
                logger.warning("Response for an unknown request id: %s", command_id)
                return

            call = self._calls.pop(command_id)
            if not call.resolve.cancelled():
                call.resolve.set_result(frame)

        else:
            if notification_type := frame.get("notificationType"):
                # this is a notification
                logger.debug("Notification %s %s", notification_type, frame)
                # update the devices states based on the event
                self.update_device_state_from_event(frame)
                if self._on_notification:
                    self._on_notification(frame)
            else:
                logger.warning("Invalid frame: %s", frame)

    async def call(
        self,
        command: str | None = None,
        params: dict[str, Any] | int | list | None = None,
        timeout: int = 10,
    ) -> dict[str, Any]:
        """Websocket RPC call."""

        if self._client is None:
            raise RuntimeError("Not connected")

        call = RPCCall(self._next_id, command, params, self._token, self._session)
        self._calls[call.call_id] = call

        try:
            async with async_timeout.timeout(timeout):
                await self._send_json(call.request_frame)
                resp: dict[str, Any] = await call.resolve
        except TimeoutError as exc:
            raise DeviceConnectionError(call) from exc

        logger.debug("%s -> %s", call.params, resp)
        return resp

    async def _send_request(
        self, command: str, params: dict[str, Any] | int | list | None = None
    ) -> dict:
        if not self.connected:
            await self.connect()

        return await self.call(command, params)

    async def _login(self) -> None:

        resp = await self.call(
            ApiCommand.LOGIN,
            {
                ApiAttribute.USER: self._username,
                ApiAttribute.PASS: self._password,
            },
        )

        super()._update_login(resp)

    def update_device_state_from_event(self, push_data: dict) -> None:
        """Update device state from notification data."""

        if ApiAttribute.ID not in push_data:
            logger.error("Received update with no device id: %s", push_data)
            return

        self.update_device_state(
            push_data[ApiAttribute.ID], push_data[ApiAttribute.NEW_VALUE]
        )
