from __future__ import annotations

import re
from datetime import timedelta
from logging import getLogger
from typing import Any, List
from abc import ABC, abstractmethod

from aiohttp import ClientSession
from switchbee.const import ApiAttribute, ApiCommand, ApiStatus
from switchbee.device import (
    DeviceType,
    HardwareType,
    SwitchBeeBaseDevice,
    SwitchBeeDimmer,
    SwitchBeeGroupSwitch,
    SwitchBeeRollingScenario,
    SwitchBeeScenario,
    SwitchBeeShutter,
    SwitchBeeSomfy,
    SwitchBeeSwitch,
    SwitchBeeThermostat,
    SwitchBeeTimedSwitch,
    SwitchBeeTimerSwitch,
    SwitchBeeTwoWay,
)

from ..utils import timestamp_now

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


class CUVersion:
    def __init__(self, version: str) -> None:
        self.major: int | str = 0
        self.minor: int = 0
        self.revision: int = 0
        self.build: int = 0

        self._initialize(version)

    def _initialize(self, version) -> None:
        if match := re.match(r"(\d+|\S)\.(\d+)\.(\d+)\((\d+)\)$", version):
            self.major = match.group(1)
            self.minor = int(match.group(2))
            self.revision = int(match.group(3))
            self.build = int(match.group(4))

    def __repr__(self) -> str:
        return f"{self.major}.{self.minor}.{self.revision}.{self.build}"


class CentralUnitAPI(ABC):
    _login_count: int = -1  # we don't count the first login
    _token: str | None = None
    _token_expiration: int = 0

    def __init__(
        self, ip_address: str, user: str, password: str, aiohttp_session: ClientSession
    ) -> None:
        self._ip_address: str = ip_address
        self._username: str = user
        self._password: str = password
        self._aiohttp_session: ClientSession = aiohttp_session

        self._mac: str | None = None
        self._unique_id: str | None = None
        self._version: CUVersion | None = None
        self._name: str | None = None
        self._last_conf_change: int = 0
        self._devices_map: dict[
            int,
            SwitchBeeSwitch
            | SwitchBeeGroupSwitch
            | SwitchBeeTimedSwitch
            | SwitchBeeShutter
            | SwitchBeeSomfy
            | SwitchBeeDimmer
            | SwitchBeeThermostat
            | SwitchBeeScenario
            | SwitchBeeRollingScenario
            | SwitchBeeTimerSwitch
            | SwitchBeeTwoWay,
        ] = {}

        self._modules_map: dict[int, set] = {}

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def version(self) -> CUVersion | None:
        return self._version

    @property
    def mac(self) -> str | None:
        return self._mac

    @property
    def unique_id(self) -> str | None:
        return self._unique_id

    @property
    def devices(
        self,
    ) -> dict[
        int,
        SwitchBeeSwitch
        | SwitchBeeGroupSwitch
        | SwitchBeeTimedSwitch
        | SwitchBeeShutter
        | SwitchBeeSomfy
        | SwitchBeeDimmer
        | SwitchBeeThermostat
        | SwitchBeeScenario
        | SwitchBeeRollingScenario
        | SwitchBeeTimerSwitch
        | SwitchBeeTwoWay,
    ]:
        return self._devices_map

    @property
    def last_conf_change(self) -> int:
        return self._last_conf_change

    @property
    def devices_list(
        self,
    ) -> List[SwitchBeeBaseDevice]:
        return list(self._devices_map.values())

    @property
    def reconnect_count(self) -> int:
        return self._login_count

    def module_display(self, unit_id: int) -> str:
        return " and ".join(list(self._modules_map[unit_id]))

    async def login_if_needed(self) -> None:
        if not self._token or (timestamp_now() >= self._token_expiration):
            logger.info(
                "Logging into the Central Unit due to %s",
                "invalid token" if not self._token else " expiry",
            )
            await self._login()

    @abstractmethod
    async def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def call(
        self,
        command: str | None = None,
        params: dict[str, Any] | int | list | None = None,
        timeout: int = 10,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def _send_request(self, command: str, params: Any = {}) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def _login(self) -> None:
        raise NotImplementedError

    def _update_login(self, resp: dict[str, Any]) -> None:

        self._login_count += 1
        self._token = resp[ApiAttribute.DATA][ApiAttribute.TOKEN]
        # instead of dealing with time synchronization issue, we
        # calculate one hour from now and set it to be the expiration time of the token
        # self._token_expiration = resp[ApiAttribute.DATA][ApiAttribute.EXPIRATION]
        self._token_expiration = timestamp_now() + TOKEN_EXPIRATION

    async def get_configuration(self) -> dict:
        await self.login_if_needed()
        return await self._send_request(ApiCommand.GET_CONF)

    async def get_multiple_states(self, ids: list) -> dict:
        """returns JSON {'status': 'OK', 'data': [{'id': 212, 'state': 'OFF'}, {'id': 343, 'state': 'OFF'}]}"""
        await self.login_if_needed()
        return await self._send_request(ApiCommand.GET_MULTI_STATES, ids)

    async def get_state(self, id: int) -> dict:
        """returns JSON {'status': 'OK', 'data': 'OFF'}"""
        await self.login_if_needed()
        return await self._send_request(ApiCommand.GET_STATE, id)

    async def set_state(self, id: int, state: str | int | dict[str, int | str]) -> dict:
        """returns JSON {'status': 'OK', 'data': 'OFF/ON'}"""
        await self.login_if_needed()
        return await self._send_request(
            ApiCommand.OPERATE, {"directive": "SET", "itemId": id, "value": state}
        )

    async def get_stats(self) -> dict:
        """returns {'status': 'OK', 'data': {}} on my unit"""
        await self.login_if_needed()
        return await self._send_request(ApiCommand.STATS)

    async def fetch_configuration(
        self,
        include: list[DeviceType] | None = [],
    ) -> None:
        await self.login_if_needed()
        data = await self.get_configuration()
        if data[ApiAttribute.STATUS] != ApiStatus.OK:
            raise SwitchBeeError

        # clear the old fetched devices
        self._devices_map.clear()
        self._modules_map.clear()
        self._name = data[ApiAttribute.DATA][ApiAttribute.NAME]
        self._version = CUVersion(data[ApiAttribute.DATA][ApiAttribute.VERSION])
        self._mac = data[ApiAttribute.DATA][ApiAttribute.MAC]
        self._unique_id = (
            None
            if ApiAttribute.CU_CODE not in data[ApiAttribute.DATA]
            else data[ApiAttribute.DATA][ApiAttribute.CU_CODE]
        )
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
                except KeyError:
                    logger.error(
                        "device %s missing type attribute, Skipping",
                        item[ApiAttribute.NAME],
                    )
                    continue

                if include and device_type not in include:
                    logger.info(
                        "Skipping %s (%s)", device_type.value, item[ApiAttribute.NAME]
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
                except KeyError:
                    logger.error(
                        "device %s missing hardware attribute, Skipping",
                        item[ApiAttribute.NAME],
                    )
                    continue

                try:
                    device_id = item[ApiAttribute.ID]
                except KeyError:
                    logger.error(
                        "device %s missing id attribute, Skipping",
                        item,
                    )
                    continue

                try:
                    device_name = item[ApiAttribute.NAME]
                except KeyError:
                    logger.error(
                        "device %s missing name attribute, Skipping",
                        item,
                    )
                    device_name = "Unknown"

                # add switch type device
                if device_type == DeviceType.Switch:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeSwitch(
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add dimmer (light) device
                elif device_type == DeviceType.Dimmer:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeDimmer(
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add shutter device
                elif device_type == DeviceType.Shutter:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeShutter(
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add timed power switch device
                elif device_type == DeviceType.TimedPowerSwitch:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeTimerSwitch(
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add scenario
                elif device_type == DeviceType.Scenario:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeScenario(
                        id=device_id,
                        name=device_name,
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
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )

                elif device_type == DeviceType.Thermostat:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeThermostat(
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                        modes=item[ApiAttribute.MODES],
                        unit=item[ApiAttribute.TEMPERATURE_UNITS],
                    )

                # add rolling scenario
                elif device_type == DeviceType.RollingScenario:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeRollingScenario(
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )

                # add timed switch
                elif device_type == DeviceType.TimedSwitch:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeTimedSwitch(
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add two way
                elif device_type == DeviceType.TwoWay:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeTwoWay(
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )

                # add somfy
                elif device_type == DeviceType.Somfy:
                    self._devices_map[item[ApiAttribute.ID]] = SwitchBeeSomfy(
                        id=device_id,
                        name=device_name,
                        zone=zone[ApiAttribute.NAME],
                        hardware=device_hw,
                        type=device_type,
                    )
                # add gro

                else:
                    logger.warning(
                        f"Unsupported Type {item[ApiAttribute.TYPE]} {item[ApiAttribute.HARDWARE]}"
                    )
                    continue

                unit_id = self._devices_map[item[ApiAttribute.ID]].unit_id
                if unit_id not in self._modules_map:
                    self._modules_map[unit_id] = set()

                self._modules_map[unit_id].add(
                    self._devices_map[item[ApiAttribute.ID]].hardware.display
                )

    async def fetch_states(
        self,
    ) -> None:

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

        for device_state in states[ApiAttribute.DATA]:
            device_id = device_state[ApiAttribute.ID]

            self.update_device_state(device_id, device_state[ApiAttribute.STATE])

    def update_device_state(self, device_id: int, new_state: str | int | dict) -> bool:
        """Update device state."""

        if device_id not in self._devices_map:
            logger.debug("Device id %d is not tracked", device_id)
            return False

        device = self._devices_map[device_id]

        if isinstance(device, SwitchBeeDimmer):
            assert isinstance(new_state, (str, int))
            device.brightness = new_state  # type: ignore

        elif isinstance(device, SwitchBeeShutter):
            assert isinstance(new_state, (str, int))
            device.position = new_state  # type: ignore

        elif isinstance(
            device,
            (
                SwitchBeeSwitch,
                SwitchBeeGroupSwitch,
                SwitchBeeTimedSwitch,
                SwitchBeeTimerSwitch,
            ),
        ):

            assert isinstance(new_state, (int, str))
            device.state = new_state

        elif isinstance(device, SwitchBeeThermostat):
            try:
                assert isinstance(new_state, dict)
                device.state = new_state[ApiAttribute.POWER]
            except TypeError:
                logger.error(
                    "%s: Received invalid state from CU, keeping the old one: %s",
                    device.name,
                    new_state,
                )
                return False

            device.mode = new_state[ApiAttribute.MODE]
            device.fan = new_state[ApiAttribute.FAN]

            device.target_temperature = new_state[ApiAttribute.CONFIGURED_TEMPERATURE]
            device.temperature = new_state[ApiAttribute.ROOM_TEMPERATURE]

        else:
            return False

        return True
