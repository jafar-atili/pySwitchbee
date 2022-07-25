from asyncio import TimeoutError
from datetime import timedelta
from json import JSONDecodeError
from logging import getLogger
from typing import List, Union

from aiohttp import ClientError, ClientSession
from switchbee.device import SwitchBeeGroupSwitch
from switchbee.device import (
    DeviceType,
    HardwareType,
    SwitchBeeDimmer,
    SwitchBeeScenario,
    SwitchBeeShutter,
    SwitchBeeSwitch,
    SwitchBeeTimerSwitch,
)

from switchbee.const import ApiAttribute, ApiCommand, ApiStatus
from .utils import timestamp_now

logger = getLogger(__name__)


class SwitchBeeError(Exception):
    pass


class SwitchBeeTokenError(Exception):
    pass


class SwitchBeeDeviceOfflineError(Exception):
    pass


TOKEN_EXPIRATION = int(timedelta(minutes=50).total_seconds()) * 1000


class CentralUnitAPI:
    def __init__(
        self, central_unit: str, user: str, password: str, websession: ClientSession
    ) -> None:
        self._cunit_ip: str = central_unit
        self._user: str = user
        self._password: str = password
        self._session: ClientSession = websession
        self._token: str = ""
        self._token_expiration: int = 0
        self._login_count: int = -1  # we don't count the first login
        self._devices_map: dict[
            int,
            Union[
                SwitchBeeDimmer,
                SwitchBeeSwitch,
                SwitchBeeShutter,
                SwitchBeeScenario,
                SwitchBeeTimerSwitch,
            ],
        ] = {}
        self._mac = str
        self._version = str
        self._name = str
        self._last_conf_change = int

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def mac(self) -> str:
        return self._mac

    @property
    def devices(self) -> dict:
        return self._devices_map

    @property
    def last_conf_change(self) -> str:
        return self._last_conf_change

    @property
    def devices_list(
        self,
    ) -> List[
        Union[
            SwitchBeeSwitch,
            SwitchBeeDimmer,
            SwitchBeeShutter,
            SwitchBeeTimerSwitch,
            SwitchBeeScenario,
        ]
    ]:
        return self._devices_map.values()

    @property
    def reconnect_count(self) -> int:
        return self._login_count

    async def connect(self):
        await self.fetch_configuration()
        await self.fetch_states()

    async def _post(self, body: dict) -> dict:
        try:
            async with self._session.post(
                url=f"https://{self._cunit_ip}/commands", json=body
            ) as response:
                if response.status == 200:
                    try:
                        json_result = await response.json(
                            content_type=None, encoding="utf8"
                        )
                        if json_result[ApiAttribute.STATUS] != ApiStatus.OK:
                            # check if invalid token or token expired
                            if json_result[ApiAttribute.STATUS] in [
                                ApiStatus.INVALID_TOKEN,
                                ApiStatus.TOKEN_EXPIRED,
                            ]:
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

        except TimeoutError:
            raise SwitchBeeError(f"Timeout error: {response}")
        except ClientError as e:
            raise SwitchBeeError(f"Client error: {e}")

    async def _send_request(self, command: ApiCommand, params: dict = {}) -> dict:
        if not self._token or (
            self._token and timestamp_now() >= self._token_expiration
        ):
            logger.info(
                "Logging into the Central Unit %s",
                "for the first time." if not self._token else " due to Token expiry.",
            )
            await self._login()

        return await self._post(
            {
                ApiAttribute.TOKEN: self._token,
                ApiAttribute.COMMAND: command,
                ApiAttribute.PARAMS: params,
            }
        )

    async def _login(self) -> str:
        try:
            resp = await self._post(
                {
                    ApiAttribute.COMMAND: ApiCommand.LOGIN,
                    ApiAttribute.PARAMS: {
                        ApiAttribute.USER: self._user,
                        ApiAttribute.PASS: self._password,
                    },
                }
            )

        except SwitchBeeError:
            self._token = None
            self._token_expiration = 0
            raise

        self._login_count += 1
        self._token = resp[ApiAttribute.DATA][ApiAttribute.TOKEN]
        # instead of dealing with time synchronization issue, we
        # calculate one hour from now and set it to be the expiration time of the token
        # self._token_expiration = resp[ApiAttribute.DATA][ApiAttribute.EXPIRATION]
        self._token_expiration = timestamp_now() + TOKEN_EXPIRATION

        return self._token

    async def get_configuration(self):
        return await self._send_request(ApiCommand.GET_CONF)

    async def get_multiple_states(self, ids: list):
        """returns JSON {'status': 'OK', 'data': [{'id': 212, 'state': 'OFF'}, {'id': 343, 'state': 'OFF'}]}"""
        return await self._send_request(ApiCommand.GET_MULTI_STATES, ids)

    async def get_state(self, id: int):
        """returns JSON {'status': 'OK', 'data': 'OFF'}"""
        return await self._send_request(ApiCommand.GET_STATE, id)

    async def set_state(self, id: int, state):
        """returns JSON {'status': 'OK', 'data': 'OFF/ON'}"""
        return await self._send_request(
            ApiCommand.OPERATE, {"directive": "SET", "itemId": id, "value": state}
        )

    async def get_stats(self):
        """returns {'status': 'OK', 'data': {}} on my unit"""
        return await self._send_request(ApiCommand.STATS)

    async def fetch_configuration(
        self,
        include: list[DeviceType] = [
            DeviceType.Switch,
            DeviceType.Dimmer,
            DeviceType.TimedPowerSwitch,
            DeviceType.Shutter,
        ],
    ):
        data = await self.get_configuration()
        if data[ApiAttribute.STATUS] != ApiStatus.OK:
            raise SwitchBeeError

        self._name = data[ApiAttribute.DATA][ApiAttribute.NAME]
        self._version = data[ApiAttribute.DATA][ApiAttribute.VERSION]
        self._mac = data[ApiAttribute.DATA][ApiAttribute.MAC]

        for zone in data[ApiAttribute.DATA][ApiAttribute.ZONES]:
            for item in zone[ApiAttribute.ITEMS]:
                device_type = item[ApiAttribute.TYPE]
                device_hw = item[ApiAttribute.HARDWARE]
                if DeviceType(device_type) not in include:
                    continue

                # add switch type device
                if device_type == DeviceType.Switch.value:

                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeSwitch(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=HardwareType(device_hw),
                        type=DeviceType.Switch,
                    )
                # add dimmer (light) device
                elif device_type == DeviceType.Dimmer.value:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeDimmer(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=HardwareType(device_hw),
                        type=DeviceType.Dimmer,
                    )
                # add shutter device
                elif device_type == DeviceType.Shutter.value:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeShutter(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=HardwareType(device_hw),
                        type=DeviceType.Shutter,
                    )
                # add timed power switch device
                elif device_type == DeviceType.TimedPowerSwitch.value:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeTimerSwitch(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=HardwareType(device_hw),
                        type=DeviceType.TimedPowerSwitch,
                    )
                # add scenario
                elif device_type == DeviceType.Scenario.value:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeScenario(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=HardwareType(device_hw),
                        type=DeviceType.Scenario,
                    )
                # add group scenario only of type != VIRTUAL
                elif (
                    device_type == DeviceType.GroupSwitch.value
                    and device_hw != HardwareType.Virtual.value
                ):
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeGroupSwitch(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=HardwareType(device_hw),
                        type=DeviceType.GroupSwitch,
                    )

                else:
                    logger.warning(f"Unknown Type {item[ApiAttribute.TYPE]}")

    async def fetch_states(
        self,
    ):

        states = await self.get_multiple_states(
            [
                dev
                for dev in self._devices_map.keys()
                if self._devices_map[dev].hardware != HardwareType.Virtual
                and self._devices_map[dev].type
                in [
                    DeviceType.Switch,
                    DeviceType.GroupSwitch,
                    DeviceType.Dimmer,
                    DeviceType.Shutter,
                    DeviceType.TimedPowerSwitch,
                ]
            ]
        )

        for device_state in states[ApiAttribute.DATA]:
            device_id = device_state[ApiAttribute.ID]
            if self._devices_map[device_id].type == DeviceType.Dimmer:
                self._devices_map[device_id].brightness = device_state[
                    ApiAttribute.STATE
                ]
            elif self._devices_map[device_id].type == DeviceType.Switch:
                self._devices_map[device_id].state = device_state[ApiAttribute.STATE]
            elif self._devices_map[device_id].type == DeviceType.Shutter:
                self._devices_map[device_id].position = device_state[ApiAttribute.STATE]
            elif self._devices_map[device_id].type == DeviceType.TimedPowerSwitch:
                self._devices_map[device_id].state = device_state[ApiAttribute.STATE]
            elif self._devices_map[device_id].type == DeviceType.GroupSwitch:
                self._devices_map[device_id].state = device_state[ApiAttribute.STATE]
