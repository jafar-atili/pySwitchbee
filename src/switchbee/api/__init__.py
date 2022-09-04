from asyncio import TimeoutError
from datetime import timedelta
from json import JSONDecodeError
from logging import getLogger
from typing import List, Type, Union

from aiohttp import ClientSession

from switchbee.const import (
    ApiAttribute,
    ApiCommand,
    ApiStatus,
)
from switchbee.device import (
    DeviceType,
    HardwareType,
    SwitchBeeDimmer,
    SwitchBeeGroupSwitch,
    SwitchBeeRollingScenario,
    SwitchBeeScenario,
    SwitchBeeShutter,
    SwitchBeeSwitch,
    SwitchBeeThermostat,
    SwitchBeeTimedSwitch,
    SwitchBeeTimerSwitch,
    SwitchBeeTwoWay,
)

from .utils import timestamp_now

logger = getLogger(__name__)


class SwitchBeeError(Exception):
    pass


class SwitchBeeTokenError(Exception):
    pass


class SwitchBeeDeviceOfflineError(Exception):
    pass


TOKEN_EXPIRATION = int(timedelta(minutes=55).total_seconds()) * 1000

STATE_MAP = [
    DeviceType.Switch,
    DeviceType.GroupSwitch,
    DeviceType.Dimmer,
    DeviceType.Shutter,
    DeviceType.TimedPowerSwitch,
    DeviceType.Thermostat,
    DeviceType.TimedSwitch,
]


class CentralUnitAPI:
    def __init__(
        self, central_unit: str, user: str, password: str, websession: ClientSession
    ) -> None:
        self._cunit_ip: str = central_unit
        self._user: str = user
        self._password: str = password
        self._session: ClientSession = websession
        self._token: str = None
        self._token_expiration: int = 0
        self._login_count: int = -1  # we don't count the first login
        self._mac = str
        self._version = str
        self._name = str
        self._last_conf_change = int
        self._devices_map: dict[
            int,
            Union[
                SwitchBeeDimmer,
                SwitchBeeSwitch,
                SwitchBeeShutter,
                SwitchBeeScenario,
                SwitchBeeTimerSwitch,
                SwitchBeeGroupSwitch,
                SwitchBeeThermostat,
            ],
        ] = {}

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
            SwitchBeeRollingScenario,
            SwitchBeeGroupSwitch,
            SwitchBeeThermostat,
        ]
    ]:
        return self._devices_map.values()

    @property
    def reconnect_count(self) -> int:
        return self._login_count

    async def login_if_needed(self) -> None:
        if not self._token or (timestamp_now() >= self._token_expiration):
            logger.info(
                "Logging into the Central Unit due to %s",
                "invalid token" if not self._token else " expiry",
            )
            await self._login()

    async def connect(self) -> None:
        await self.fetch_configuration(None)
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
        except TimeoutError:
            raise SwitchBeeError(
                f"Timed out while waiting for the Central Unit to reply"
            )

    async def _send_request(self, command: ApiCommand, params: dict = {}) -> dict:

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
        await self.login_if_needed()
        return await self._send_request(ApiCommand.GET_CONF)

    async def get_multiple_states(self, ids: list):
        """returns JSON {'status': 'OK', 'data': [{'id': 212, 'state': 'OFF'}, {'id': 343, 'state': 'OFF'}]}"""
        await self.login_if_needed()
        return await self._send_request(ApiCommand.GET_MULTI_STATES, ids)

    async def get_state(self, id: int):
        """returns JSON {'status': 'OK', 'data': 'OFF'}"""
        await self.login_if_needed()
        return await self._send_request(ApiCommand.GET_STATE, id)

    async def set_state(self, id: int, state):
        """returns JSON {'status': 'OK', 'data': 'OFF/ON'}"""
        await self.login_if_needed()
        return await self._send_request(
            ApiCommand.OPERATE, {"directive": "SET", "itemId": id, "value": state}
        )

    async def get_stats(self):
        """returns {'status': 'OK', 'data': {}} on my unit"""
        await self.login_if_needed()
        return await self._send_request(ApiCommand.STATS)

    async def fetch_configuration(
        self,
        include: list[DeviceType] = [],
    ):
        await self.login_if_needed()
        data = await self.get_configuration()
        if data[ApiAttribute.STATUS] != ApiStatus.OK:
            raise SwitchBeeError

        # clear the old fetched devices
        self._devices_map.clear()

        self._name = data[ApiAttribute.DATA][ApiAttribute.NAME]
        self._version = data[ApiAttribute.DATA][ApiAttribute.VERSION]
        self._mac = data[ApiAttribute.DATA][ApiAttribute.MAC]

        if include is None:
            return

        for zone in data[ApiAttribute.DATA][ApiAttribute.ZONES]:
            for item in zone[ApiAttribute.ITEMS]:

                try:
                    device_type = DeviceType(item[ApiAttribute.TYPE])
                except ValueError:
                    logger.warning(
                        "Unknown device type %s (%s), Skipping",
                        item[ApiAttribute.TYPE],
                        item[ApiAttribute.NAME],
                    )
                    continue

                try:
                    device_hw = HardwareType(item[ApiAttribute.HARDWARE])
                except ValueError:
                    logger.warning(
                        "Unknown hardware type %s (%s), Skipping",
                        item[ApiAttribute.HARDWARE],
                        item[ApiAttribute.NAME],
                    )
                    continue

                if include and device_type not in include:
                    logger.info(
                        "Skipping %s (%s)", device_type.value, item[ApiAttribute.NAME]
                    )
                    continue

                # add switch type device
                if device_type == DeviceType.Switch:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeSwitch(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add dimmer (light) device
                elif device_type == DeviceType.Dimmer:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeDimmer(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add shutter device
                elif device_type == DeviceType.Shutter:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeShutter(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add timed power switch device
                elif device_type == DeviceType.TimedPowerSwitch:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeTimerSwitch(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add scenario
                elif device_type == DeviceType.Scenario:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeScenario(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add group switch only of hardware type != VIRTUAL as we can't read their statuses
                elif (
                    device_type == DeviceType.GroupSwitch
                    and device_hw != HardwareType.Virtual
                ):
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeGroupSwitch(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )

                elif device_type == DeviceType.Thermostat:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeThermostat(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                        modes=item[ApiAttribute.MODES],
                        unit=item[ApiAttribute.TEMPERATURE_UNITS],
                    )

                # add rolling scenario
                elif device_type == DeviceType.RollingScenario:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeRollingScenario(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )

                # add timed switch
                elif device_type == DeviceType.TimedSwitch:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeTimedSwitch(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add two way
                elif device_type == DeviceType.TwoWay:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeTwoWay(
                        id=item[ApiAttribute.ID],
                        name=item[ApiAttribute.NAME],
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                else:
                    logger.warning(
                        f"Unsupported Type {item[ApiAttribute.TYPE]} {item[ApiAttribute.HARDWARE]}"
                    )

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
                    DeviceType.Thermostat,
                    DeviceType.TimedSwitch,
                ]
            ]
        )

        for device in states[ApiAttribute.DATA]:
            device_id = device[ApiAttribute.ID]
            if self._devices_map[device_id].type == DeviceType.Dimmer:
                self._devices_map[device_id].brightness = device[ApiAttribute.STATE]
            elif self._devices_map[device_id].type == DeviceType.Shutter:
                self._devices_map[device_id].position = device[ApiAttribute.STATE]
            elif self._devices_map[device_id].type in [
                DeviceType.Switch,
                DeviceType.GroupSwitch,
                DeviceType.TimedSwitch,
                DeviceType.TimedPowerSwitch,
            ]:
                self._devices_map[device_id].state = device[ApiAttribute.STATE]
            elif self._devices_map[device_id].type == DeviceType.Thermostat:
                try:
                    self._devices_map[device_id].state = device[ApiAttribute.STATE][
                        ApiAttribute.POWER
                    ]
                except TypeError:
                    logger.error(
                        "%s: Recieved invalid state from CU, keeping the old one: %s",
                        self._devices_map[device_id].name,
                        device,
                    )
                    continue

                self._devices_map[device_id].mode = device[ApiAttribute.STATE][
                    ApiAttribute.MODE
                ]

                self._devices_map[device_id].fan = device[ApiAttribute.STATE][
                    ApiAttribute.FAN
                ]

                self._devices_map[device_id].target_temperature = device[
                    ApiAttribute.STATE
                ][ApiAttribute.CONFIGURED_TEMPERATURE]
                self._devices_map[device_id].temperature = device[ApiAttribute.STATE][
                    ApiAttribute.ROOM_TEMPERATURE
                ]
