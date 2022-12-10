from __future__ import annotations

from asyncio import TimeoutError
from datetime import timedelta
from json import JSONDecodeError
from logging import getLogger
from typing import Any
from .central_unit import (
    CentralUnitAPI,
    SwitchBeeError,
    SwitchBeeTokenError,
    SwitchBeeDeviceOfflineError,
)
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError
from switchbee.const import ApiAttribute, ApiCommand, ApiStatus


logger = getLogger(__name__)


class CentralUnitPolling(CentralUnitAPI):
    def __init__(
        self,
        ip_address: str,
        username: str,
        password: str,
        aiohttp_session: ClientSession,
    ) -> None:
        super().__init__(ip_address, username, password, aiohttp_session)

    async def connect(self) -> None:
        await self.fetch_configuration(None)
        await self.fetch_states()

    async def call(
        self,
        command: str | None = None,
        params: dict[str, Any] | int | list | None = None,
        timeout: int = 10,
    ) -> dict[str, Any]:
        """Websocket RPC call."""

        body = {
            ApiAttribute.COMMAND: command,
            ApiAttribute.PARAMS: params,
            ApiAttribute.TOKEN: self._token,
        }

        try:
            async with self._aiohttp_session.post(
                url=f"https://{self._ip_address}/commands", json=body
            ) as response:
                if response.status == 200:
                    try:
                        json_result: dict = await response.json(
                            content_type=None, encoding="utf8"
                        )
                        if json_result[ApiAttribute.STATUS] != ApiStatus.OK:
                            # check if invalid token or token expired
                            if json_result[ApiAttribute.STATUS] in [
                                ApiStatus.INVALID_TOKEN,
                                ApiStatus.TOKEN_EXPIRED,
                            ]:
                                self._token = None
                                raise SwitchBeeTokenError(
                                    json_result[ApiAttribute.STATUS]
                                )

                            if json_result[ApiAttribute.STATUS] == ApiStatus.OFFLINE:
                                raise SwitchBeeDeviceOfflineError(
                                    f"Central Unit replied with bad status ({json_result[ApiAttribute.STATUS]}): {json_result}"
                                )

                            raise SwitchBeeError(
                                f"Central Unit replied with bad status ({json_result[ApiAttribute.STATUS]}): {json_result}"
                            )
                        else:
                            return json_result
                    except JSONDecodeError:
                        raise SwitchBeeError(f"Unexpected response: {response.read()}")
                else:
                    raise SwitchBeeError(
                        f"Request to the Central Unit failed with status={response.status}"
                    )
        except TimeoutError as exp:
            raise SwitchBeeError(
                "Timed out while waiting for the Central Unit to reply"
            ) from exp

        except ClientConnectorError as exp:
            raise SwitchBeeError("Failed to communicate with the Central Unit") from exp

    async def _login(self) -> None:
        try:
            resp = await self.call(
                ApiCommand.LOGIN,
                {
                    ApiAttribute.USER: self._username,
                    ApiAttribute.PASS: self._password,
                },
            )

        except SwitchBeeError:
            self._token = None
            self._token_expiration = 0
            raise

        super()._update_login(resp)

    async def _send_request(self, command: str, params: Any = {}) -> dict:
        return await self.call(command, params)
